"""
batch_classify.py — Batch scorer for AnyForge Control Layer audit traces.

Globs all .json files in a traces directory (optionally filtered to a single
domain), runs the rubric-based drift classifier on each, and writes one CSV
row per trial to an output file in the processed-data directory.

Output CSV schema (matches analysis/statistics.py required_fields):
  trial_id, domain, perturbation_type, drift_type_detected, onset_step, confidence

Usage:
  python analysis/batch_classify.py
  python analysis/batch_classify.py --traces-dir audit_logs/raw_control_traces
  python analysis/batch_classify.py --domain financial_allocation
  python analysis/batch_classify.py --domain financial_allocation \\
      --traces-dir audit_logs/raw_control_traces --output-dir data/processed
"""

import argparse
import csv
import json
import logging
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Import the classifier from the same package directory
# ---------------------------------------------------------------------------

# Allow running as `python analysis/batch_classify.py` from the repo root
# by ensuring the repo root is on sys.path so `analysis.drift_classifier`
# can be imported; also allow running from inside the analysis/ directory.
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from analysis.drift_classifier import classify  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TRACES_DIR = "audit_logs/raw_control_traces"
DEFAULT_OUTPUT_DIR = "data/processed"

# Glob pattern for trace files to process.
TRACE_GLOB_PATTERN = "*.json"

CSV_FIELDNAMES = [
    "trial_id",
    "domain",
    "perturbation_type",
    "drift_type_detected",
    "onset_step",
    "confidence",
]


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def batch_classify(traces_dir: Path, output_dir: Path, domain: str | None = None) -> int:
    """
    Classify all JSON trace files in traces_dir and write results to output_dir.

    If domain is given, only traces whose JSON contains a matching 'domain'
    field are classified; all others are silently counted as filtered.
    Traces that are unreadable, malformed, or missing a 'domain' field are
    skipped with a log.warning and do not abort the batch.

    Returns the number of successfully processed traces.
    """
    trace_files = sorted(traces_dir.glob(TRACE_GLOB_PATTERN))

    if not trace_files:
        log.warning(
            "No files matching '%s' found in %s. Nothing to do.",
            TRACE_GLOB_PATTERN,
            traces_dir,
        )
        return 0

    # Determine output filename
    if domain:
        output_filename = f"{domain}_results.csv"
    else:
        output_filename = "all_results.csv"

    output = output_dir / output_filename

    # Ensure the output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    filtered = 0

    with open(output, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()

        for trace_path in trace_files:
            # Read raw JSON for metadata fields (domain, perturbation_applied)
            try:
                with open(trace_path) as f:
                    raw = json.load(f)
            except json.JSONDecodeError as exc:
                log.warning(
                    "Skipping %s — malformed JSON: %s", trace_path.name, exc
                )
                continue
            except Exception as exc:
                log.warning(
                    "Skipping %s — could not read file: %s", trace_path.name, exc
                )
                continue

            # Require the 'domain' field to be present in the trace
            trace_domain = raw.get("domain")
            if trace_domain is None:
                log.warning(
                    "Skipping %s — 'domain' field absent in trace JSON.",
                    trace_path.name,
                )
                continue

            # Apply domain filter if requested
            if domain is not None and trace_domain != domain:
                filtered += 1
                continue

            # Run the drift classifier
            try:
                result = classify(str(trace_path))
            except FileNotFoundError as exc:
                log.warning("Skipping %s — %s", trace_path.name, exc)
                continue
            except Exception as exc:
                log.warning(
                    "Skipping %s — classifier error: %s", trace_path.name, exc
                )
                continue

            perturbation_type = raw.get("perturbation_applied", "unknown")

            writer.writerow(
                {
                    "trial_id": result.trial_id,
                    "domain": trace_domain,
                    "perturbation_type": perturbation_type,
                    "drift_type_detected": result.drift_type_detected,
                    "onset_step": result.onset_step,
                    "confidence": result.confidence,
                }
            )
            processed += 1

    if processed == 0 and domain is not None:
        log.warning(
            "0 traces matched domain filter '%s'. CSV written with header only: %s",
            domain,
            output,
        )
    else:
        log.info(
            "Processed %d trace(s). Results written to %s", processed, output
        )

    return processed


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Batch-classify AnyForge audit traces and write results to a CSV. "
            "Output schema is compatible with analysis/statistics.py load_results()."
        )
    )
    parser.add_argument(
        "--domain",
        default=None,
        help=(
            "If given, only process traces whose JSON 'domain' field matches "
            "this value (e.g. financial_allocation). "
            "Output file will be named {domain}_results.csv. "
            "Omit to process all traces; output file will be all_results.csv."
        ),
    )
    parser.add_argument(
        "--traces-dir",
        default=DEFAULT_TRACES_DIR,
        help=(
            f"Directory containing .json audit trace files "
            f"(default: {DEFAULT_TRACES_DIR})"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=(
            f"Directory to write the output CSV file into "
            f"(default: {DEFAULT_OUTPUT_DIR})"
        ),
    )
    args = parser.parse_args()

    traces_dir = Path(args.traces_dir)
    output_dir = Path(args.output_dir)

    if not traces_dir.exists():
        log.warning("Traces directory does not exist: %s", traces_dir)
        log.warning("No traces to process.")
        sys.exit(0)

    batch_classify(traces_dir, output_dir, domain=args.domain)
    sys.exit(0)


if __name__ == "__main__":
    main()
