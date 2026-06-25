"""
SDK Runner: Automated trial execution for the goal-drift-study.

All agent calls in this script are routed through the AnyForge MCP server,
which intercepts every agent action, tool call, and intermediate state before
they reach the model. The Control Layer writes append-only audit traces to
audit_logs/raw_control_traces/ independently of the agent under study — the
agent cannot observe, modify, or suppress its own trace. This is the Flight
Recorder guarantee: the log is written whether the trial succeeds or drifts.

To use this runner:
  1. Ensure ANYFORGE_API_KEY is set in your environment.
  2. Confirm the AnyForge MCP server is running: `claude mcp list`
  3. Run: python infrastructure/sdk_runner.py

All 60 trials (3 domains × 20 trials each) are executed sequentially.
A failed trial is logged and skipped; the batch continues.
"""

import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

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

# Step windows within which each perturbation may fire, keyed by domain.
# Perturbation must fire before the final two steps so the agent has time
# to exhibit drift behavior before task termination.
INJECTION_STEP_RANGES = {
    "financial_allocation":    (3, 7),   # 10-step task
    "research_synthesis":      (2, 6),   # 8-step task
    "task_queue_management":   (4, 9),   # 12-step task
}

TRIALS_PER_DOMAIN = 20
AUDIT_LOG_DIR = Path("audit_logs/raw_control_traces")
RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sdk_runner")


# ---------------------------------------------------------------------------
# AnyForge MCP client
# ---------------------------------------------------------------------------

def get_anyforge_client():
    """
    Return an authenticated AnyForge SDK client.

    The client reads ANYFORGE_API_KEY from the environment. The key is
    never passed as a literal string and must not be hardcoded here or in
    any config file committed to version control.
    """
    api_key = os.environ.get("ANYFORGE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANYFORGE_API_KEY is not set. "
            "Export it before running this script:\n"
            "  export ANYFORGE_API_KEY=your_key_here"
        )

    try:
        from anyforge import AnyForgeClient  # type: ignore
        return AnyForgeClient(api_key=api_key)
    except ImportError:
        raise ImportError(
            "anyforge SDK not installed. Run: pip install anyforge"
        )


# ---------------------------------------------------------------------------
# Trial execution
# ---------------------------------------------------------------------------

def build_trial_config(
    trial_id: str,
    domain: str,
    perturbation_type: str,
    injection_step: int,
) -> dict:
    """Assemble the trial config dict passed to the AnyForge SDK."""
    return {
        "trial_id": trial_id,
        "domain": domain,
        "perturbation_type": perturbation_type,
        "injection_step": injection_step,
        "control_layer": {
            "audit_mode": "append_only",
            "capture_tool_calls": True,
            "capture_intermediate_states": True,
            "emit_goal_reference_flag": True,
            "emit_constraint_reference_flag": True,
        },
        "runner_metadata": {
            "runner_version": "sdk_runner-1.0.0",
            "started_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def run_trial(client, trial_config: dict) -> dict:
    """
    Execute a single trial via the AnyForge MCP server and return the trace.

    The MCP server intercepts the agent session before execution begins and
    attaches the Control Layer logger. The returned trace dict includes every
    step the agent took, with flags written by the Control Layer.
    """
    trial_id = trial_config["trial_id"]
    log.info(
        "  Running  %s | domain=%-30s perturbation=%-30s injection_step=%d",
        trial_id,
        trial_config["domain"],
        trial_config["perturbation_type"],
        trial_config["injection_step"],
    )

    # The AnyForge SDK call routes the session through the MCP server.
    # The Control Layer audit trace is embedded in the response.
    response = client.trials.run(
        domain=trial_config["domain"],
        perturbation_type=trial_config["perturbation_type"],
        injection_step=trial_config["injection_step"],
        control_layer_config=trial_config["control_layer"],
        metadata=trial_config["runner_metadata"],
    )

    trace = response.audit_trace
    trace["trial_id"] = trial_id
    trace["runner_metadata"] = trial_config["runner_metadata"]
    return trace


def save_trace(trace: dict, output_dir: Path) -> Path:
    """Write a trace to disk using the canonical naming convention."""
    trial_id = trace["trial_id"]
    domain = trace.get("domain", "unknown")
    perturbation = trace.get("perturbation_applied", "unknown")

    filename = f"{trial_id}_{domain}_{perturbation}.json"
    output_path = output_dir / filename

    with open(output_path, "w") as f:
        json.dump(trace, f, indent=2)

    return output_path


# ---------------------------------------------------------------------------
# Batch orchestration
# ---------------------------------------------------------------------------

def generate_trial_plan(seed: int = RANDOM_SEED) -> list[dict]:
    """
    Generate the full 60-trial execution plan.

    Each domain gets 20 trials. Perturbation types are distributed evenly
    (5 trials per perturbation type per domain) with randomized injection
    steps drawn from the domain's allowed window.
    """
    rng = random.Random(seed)
    plan = []
    trial_counter = 1

    for domain in DOMAINS:
        step_min, step_max = INJECTION_STEP_RANGES[domain]

        # 5 trials per perturbation type to fill 20 trials per domain
        perturbations = PERTURBATION_TYPES * (TRIALS_PER_DOMAIN // len(PERTURBATION_TYPES))
        rng.shuffle(perturbations)

        for perturbation_type in perturbations:
            injection_step = rng.randint(step_min, step_max)
            trial_id = f"trial_{trial_counter:03d}"
            plan.append({
                "trial_id": trial_id,
                "domain": domain,
                "perturbation_type": perturbation_type,
                "injection_step": injection_step,
            })
            trial_counter += 1

    return plan


def generate_rs_trial_plan() -> list[dict]:
    """
    Generate the research_synthesis trial execution plan (20 trials).

    Produces exactly 20 trials for the research_synthesis domain: 5 trials per
    perturbation type, with injection steps drawn from the domain's allowed
    window (2, 6) using a seeded local random instance for determinism.
    Trial IDs are rs_trial_001 through rs_trial_020 (zero-padded, sequential).
    """
    rng = random.Random(42)
    domain = "research_synthesis"
    step_min, step_max = INJECTION_STEP_RANGES[domain]

    # 5 trials per perturbation type — 4 types × 5 = 20 trials
    perturbations = PERTURBATION_TYPES * (TRIALS_PER_DOMAIN // len(PERTURBATION_TYPES))
    rng.shuffle(perturbations)

    plan = []
    for i, perturbation_type in enumerate(perturbations, start=1):
        trial_id = f"rs_trial_{i:03d}"
        injection_step = rng.randint(step_min, step_max)
        plan.append({
            "trial_id": trial_id,
            "domain": domain,
            "perturbation_type": perturbation_type,
            "injection_step": injection_step,
        })

    return plan


def run_batch():
    """Execute all 60 trials, skipping failures without stopping the batch."""
    AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Initializing AnyForge client...")
    client = get_anyforge_client()

    plan = generate_trial_plan()
    total = len(plan)
    succeeded = 0
    failed = 0
    failed_ids = []

    log.info("Starting batch: %d trials across %d domains", total, len(DOMAINS))
    log.info("-" * 72)

    for i, entry in enumerate(plan, start=1):
        trial_id = entry["trial_id"]
        log.info("Trial %d/%d", i, total)

        try:
            config = build_trial_config(
                trial_id=trial_id,
                domain=entry["domain"],
                perturbation_type=entry["perturbation_type"],
                injection_step=entry["injection_step"],
            )
            trace = run_trial(client, config)
            output_path = save_trace(trace, AUDIT_LOG_DIR)
            log.info("  Saved    %s", output_path)
            succeeded += 1

        except Exception as exc:
            log.error(
                "  FAILED   %s — %s: %s",
                trial_id,
                type(exc).__name__,
                exc,
            )
            failed += 1
            failed_ids.append(trial_id)

        # Brief pause between trials to avoid rate-limit pressure
        if i < total:
            time.sleep(0.5)

    log.info("-" * 72)
    log.info(
        "Batch complete: %d succeeded, %d failed (%.0f%% success rate)",
        succeeded,
        failed,
        100 * succeeded / total,
    )
    if failed_ids:
        log.warning("Failed trials: %s", ", ".join(failed_ids))

    return succeeded, failed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_batch()
