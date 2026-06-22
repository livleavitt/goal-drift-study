"""
statistics.py — Summary statistics for goal-drift-study trial results.

Reads all scored CSV files from data/processed/, computes drift frequency
and onset metrics, and writes a plain-text summary table to results/.

Expected CSV schema (one row per trial):
  trial_id, domain, perturbation_type, drift_type_detected,
  onset_step, confidence

Usage:
  python analysis/statistics.py
  python analysis/statistics.py --processed-dir data/processed --results-dir results
"""

import argparse
import csv
import os
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DRIFT_TYPES = ["goal_substitution", "goal_forgetting", "goal_narrowing", "none"]

DOMAINS = [
    "financial_allocation",
    "research_synthesis",
    "task_queue_management",
]

PERTURBATION_TYPES = [
    "contradicting_instruction",
    "new_salient_information",
    "distraction_sub_task",
    "partial_completion_signal",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_results(processed_dir: Path) -> list[dict]:
    """
    Load and concatenate all CSV files in processed_dir.

    Each CSV must have a header row matching the expected schema.
    Rows with missing required fields are skipped with a warning.
    """
    required_fields = {
        "trial_id", "domain", "perturbation_type",
        "drift_type_detected", "onset_step", "confidence",
    }

    rows = []
    csv_files = sorted(processed_dir.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {processed_dir}. "
            "Run the classifier over your audit traces first."
        )

    for csv_path in csv_files:
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, start=2):  # start=2 accounts for header
                missing = required_fields - set(row.keys())
                if missing:
                    print(f"  WARNING: {csv_path.name} row {i} missing fields {missing} — skipped")
                    continue
                # Coerce numeric fields
                try:
                    row["onset_step"] = int(row["onset_step"])
                    row["confidence"] = float(row["confidence"])
                except ValueError:
                    print(f"  WARNING: {csv_path.name} row {i} has non-numeric onset_step or confidence — skipped")
                    continue
                rows.append(row)

    print(f"Loaded {len(rows)} trials from {len(csv_files)} file(s) in {processed_dir}\n")
    return rows


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def drift_frequency_by_type(rows: list[dict]) -> dict:
    """
    Count how many trials were classified as each drift type.

    Returns a dict: drift_type -> {"count": int, "rate": float}
    Rate is relative to all trials (including "none").
    """
    total = len(rows)
    counts = defaultdict(int)
    for row in rows:
        counts[row["drift_type_detected"]] += 1

    return {
        dt: {
            "count": counts[dt],
            "rate": counts[dt] / total if total else 0.0,
        }
        for dt in DRIFT_TYPES
    }


def avg_onset_by_drift_type(rows: list[dict]) -> dict:
    """
    Calculate the average onset step for each drift type.

    Only includes rows where drift was detected (onset_step != -1).
    Returns a dict: drift_type -> average onset step, or None if no detections.
    """
    onset_accumulator = defaultdict(list)
    for row in rows:
        dt = row["drift_type_detected"]
        onset = row["onset_step"]
        if dt != "none" and onset != -1:
            onset_accumulator[dt].append(onset)

    return {
        dt: (sum(v) / len(v) if v else None)
        for dt, v in onset_accumulator.items()
    }


def drift_rate_by_perturbation(rows: list[dict]) -> dict:
    """
    Calculate what fraction of trials produced a drift detection,
    broken down by the perturbation type that was injected.

    Returns a dict: perturbation_type -> {"trials": int, "drifted": int, "rate": float}
    """
    buckets = {p: {"trials": 0, "drifted": 0} for p in PERTURBATION_TYPES}

    for row in rows:
        pt = row["perturbation_type"]
        if pt not in buckets:
            buckets[pt] = {"trials": 0, "drifted": 0}
        buckets[pt]["trials"] += 1
        if row["drift_type_detected"] != "none":
            buckets[pt]["drifted"] += 1

    return {
        pt: {
            **v,
            "rate": v["drifted"] / v["trials"] if v["trials"] else 0.0,
        }
        for pt, v in buckets.items()
    }


def drift_rate_by_domain(rows: list[dict]) -> dict:
    """
    Calculate what fraction of trials produced a drift detection,
    broken down by task domain.

    Returns a dict: domain -> {"trials": int, "drifted": int, "rate": float}
    """
    buckets = {d: {"trials": 0, "drifted": 0} for d in DOMAINS}

    for row in rows:
        domain = row["domain"]
        if domain not in buckets:
            buckets[domain] = {"trials": 0, "drifted": 0}
        buckets[domain]["trials"] += 1
        if row["drift_type_detected"] != "none":
            buckets[domain]["drifted"] += 1

    return {
        d: {
            **v,
            "rate": v["drifted"] / v["trials"] if v["trials"] else 0.0,
        }
        for d, v in buckets.items()
    }


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _hline(width: int) -> str:
    return "─" * width


def format_summary(
    total_trials: int,
    freq: dict,
    onset: dict,
    by_perturbation: dict,
    by_domain: dict,
) -> str:
    """Render all statistics as a single plain-text summary table."""

    lines = []
    W = 72  # table width

    def section(title: str):
        lines.append("")
        lines.append(_hline(W))
        lines.append(f"  {title}")
        lines.append(_hline(W))

    lines.append(_hline(W))
    lines.append("  GOAL DRIFT STUDY — STATISTICAL SUMMARY")
    lines.append(f"  Total trials analysed: {total_trials}")
    lines.append(_hline(W))

    # --- Drift frequency by type ---
    section("1. Drift Frequency by Type")
    lines.append(f"  {'Drift Type':<30}  {'Count':>6}  {'Rate':>8}  {'Avg Onset Step':>14}")
    lines.append(f"  {'─'*30}  {'─'*6}  {'─'*8}  {'─'*14}")
    for dt in DRIFT_TYPES:
        stats = freq.get(dt, {"count": 0, "rate": 0.0})
        avg = onset.get(dt)
        avg_str = f"{avg:.1f}" if avg is not None else "—"
        lines.append(
            f"  {dt:<30}  {stats['count']:>6}  {stats['rate']:>7.1%}  {avg_str:>14}"
        )

    # --- Drift rate by perturbation ---
    section("2. Drift Rate by Perturbation Type")
    lines.append(f"  {'Perturbation Type':<34}  {'Trials':>6}  {'Drifted':>7}  {'Rate':>7}")
    lines.append(f"  {'─'*34}  {'─'*6}  {'─'*7}  {'─'*7}")
    for pt in PERTURBATION_TYPES:
        s = by_perturbation.get(pt, {"trials": 0, "drifted": 0, "rate": 0.0})
        lines.append(
            f"  {pt:<34}  {s['trials']:>6}  {s['drifted']:>7}  {s['rate']:>7.1%}"
        )

    # --- Drift rate by domain ---
    section("3. Drift Rate by Task Domain")
    lines.append(f"  {'Domain':<34}  {'Trials':>6}  {'Drifted':>7}  {'Rate':>7}")
    lines.append(f"  {'─'*34}  {'─'*6}  {'─'*7}  {'─'*7}")
    for d in DOMAINS:
        s = by_domain.get(d, {"trials": 0, "drifted": 0, "rate": 0.0})
        lines.append(
            f"  {d:<34}  {s['trials']:>6}  {s['drifted']:>7}  {s['rate']:>7.1%}"
        )

    lines.append("")
    lines.append(_hline(W))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_summary(summary: str, results_dir: Path) -> Path:
    """Write the summary text to results/drift_summary.txt."""
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / "drift_summary.txt"
    with open(output_path, "w") as f:
        f.write(summary)
        f.write("\n")
    return output_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compute drift frequency and onset statistics from processed trial CSVs."
    )
    parser.add_argument(
        "--processed-dir",
        default="data/processed",
        help="Directory containing scored CSV files (default: data/processed)",
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Directory to write summary output (default: results)",
    )
    args = parser.parse_args()

    processed_dir = Path(args.processed_dir)
    results_dir = Path(args.results_dir)

    rows = load_results(processed_dir)
    total = len(rows)

    freq = drift_frequency_by_type(rows)
    onset = avg_onset_by_drift_type(rows)
    by_perturbation = drift_rate_by_perturbation(rows)
    by_domain = drift_rate_by_domain(rows)

    summary = format_summary(total, freq, onset, by_perturbation, by_domain)

    print(summary)

    output_path = write_summary(summary, results_dir)
    print(f"\nSummary written to {output_path}")


if __name__ == "__main__":
    main()
