"""
batch_classify.py — Batch scorer for AnyForge Control Layer audit traces.

Globs all .json files in a traces directory, runs the rubric-based drift
classifier on each, and writes one CSV row per trial to an output file.

Output CSV schema (matches analysis/statistics.py load_results()):
  trial_id, domain, perturbation_type, drift_type_detected, onset_step, confidence

Usage:
  python analysis/batch_classify.py
  python analysis/batch_classify.py --traces-dir audit_logs/raw_control_traces
  python analysis/batch_classify.py --traces-dir audit_logs/raw_control_traces \\
      --output data/processed/financial_allocation_results.csv
"""

import argparse
import csv
import json
import sys
from pathlib import Path

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
DEFAULT_OUTPUT = "data/processed/financial_allocation_results.csv"

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

def batch_classify(traces_dir: Path, output: Path) -> int:
    """
    Classify all JSON trace files in traces_dir and write results to output.

    Returns the number of successfully processed traces.
    Skipped (errored) traces are reported as WARNINGs on stdout.
    """
    trace_files = sorted(traces_dir.glob(TRACE_GLOB_PATTERN))

    if not trace_files:
        print(
            f"No files matching '{TRACE_GLOB_PATTERN}' found in {traces_dir}. "
            "Nothing to do."
        )
        return 0

    # Ensure the output directory exists
    output.parent.mkdir(parents=True, exist_ok=True)

    processed = 0

    with open(output, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()

        for trace_path in trace_files:
            # Read raw JSON for metadata fields (domain, perturbation_applied)
            try:
                with open(trace_path) as f:
                    raw = json.load(f)
            except FileNotFoundError as exc:
                print(f"WARNING: skipping {trace_path.name} — file not found: {exc}")
                continue
            except Exception as exc:
                print(f"WARNING: skipping {trace_path.name} — could not read file: {exc}")
                continue

            # Run the drift classifier
            try:
                result = classify(str(trace_path))
            except FileNotFoundError as exc:
                print(f"WARNING: skipping {trace_path.name} — {exc}")
                continue
            except Exception as exc:
                print(f"WARNING: skipping {trace_path.name} — classifier error: {exc}")
                continue

            domain = raw.get("domain", "unknown")
            perturbation_type = raw.get("perturbation_applied", "unknown")

            writer.writerow({
                "trial_id": result.trial_id,
                "domain": domain,
                "perturbation_type": perturbation_type,
                "drift_type_detected": result.drift_type_detected,
                "onset_step": result.onset_step,
                "confidence": result.confidence,
            })
            processed += 1

    print(
        f"Processed {processed} trace(s). "
        f"Results written to {output}"
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
        "--traces-dir",
        default=DEFAULT_TRACES_DIR,
        help=(
            f"Directory containing .json audit trace files "
            f"(default: {DEFAULT_TRACES_DIR})"
        ),
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=(
            f"Path for the output CSV file "
            f"(default: {DEFAULT_OUTPUT})"
        ),
    )
    args = parser.parse_args()

    traces_dir = Path(args.traces_dir)
    output = Path(args.output)

    if not traces_dir.exists():
        print(f"WARNING: traces directory does not exist: {traces_dir}")
        print("No traces to process.")
        sys.exit(0)

    batch_classify(traces_dir, output)
    sys.exit(0)


if __name__ == "__main__":
    main()
