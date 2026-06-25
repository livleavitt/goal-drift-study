"""
Acceptance-criteria test for generate_financial_allocation_plan.
Run: python infrastructure/test_fa_plan.py
"""
import re
import sys
import random
from collections import Counter
from pathlib import Path

# --------------- minimal inline copy so we don't need the anyforge SDK ------

PERTURBATION_TYPES = [
    "contradicting_instruction",
    "new_salient_information",
    "distraction_sub_task",
    "partial_completion_signal",
]
TRIALS_PER_DOMAIN = 20
RANDOM_SEED = 42


def _generate_financial_allocation_plan(seed=RANDOM_SEED):
    """Inline copy that mirrors the implementation exactly."""
    rng = random.Random(seed)
    domain = "financial_allocation"
    injection_step_choices = [4, 6, 8]
    perturbations = PERTURBATION_TYPES * (TRIALS_PER_DOMAIN // len(PERTURBATION_TYPES))
    rng.shuffle(perturbations)
    plan = []
    for i, perturbation_type in enumerate(perturbations, start=1):
        trial_id = f"fa_{i:03d}"
        injection_step = rng.choice(injection_step_choices)
        plan.append({
            "trial_id": trial_id,
            "domain": domain,
            "perturbation_type": perturbation_type,
            "injection_step": injection_step,
        })
    return plan


# --------------- import the real function from sdk_runner -------------------

sys.path.insert(0, str(Path(__file__).parent))

# We need to import generate_financial_allocation_plan without triggering the
# anyforge SDK import (which only happens inside get_anyforge_client, called at
# runtime, not at import time).
import importlib.util

spec = importlib.util.spec_from_file_location(
    "sdk_runner", Path(__file__).parent / "sdk_runner.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

generate_financial_allocation_plan = mod.generate_financial_allocation_plan
generate_trial_plan = mod.generate_trial_plan
run_batch = mod.run_batch

# --------------- run tests --------------------------------------------------

def test_length():
    plan = generate_financial_allocation_plan()
    assert len(plan) == 20, f"Expected 20, got {len(plan)}"
    print("PASS test_length")

def test_keys():
    plan = generate_financial_allocation_plan()
    required = {"trial_id", "domain", "perturbation_type", "injection_step"}
    for d in plan:
        assert set(d.keys()) == required, f"Keys mismatch: {set(d.keys())}"
    print("PASS test_keys")

def test_domain():
    plan = generate_financial_allocation_plan()
    bad = [d for d in plan if d["domain"] != "financial_allocation"]
    assert not bad, f"Wrong domain in: {bad}"
    print("PASS test_domain")

def test_injection_steps():
    plan = generate_financial_allocation_plan()
    valid = {4, 6, 8}
    bad = [d["injection_step"] for d in plan if d["injection_step"] not in valid]
    assert not bad, f"Invalid injection steps: {bad}"
    print("PASS test_injection_steps")

def test_perturbation_distribution():
    plan = generate_financial_allocation_plan()
    counts = Counter(d["perturbation_type"] for d in plan)
    assert set(counts.keys()) == set(PERTURBATION_TYPES), f"Missing types: {counts}"
    bad = {k: v for k, v in counts.items() if v != 5}
    assert not bad, f"Uneven distribution: {bad}"
    print("PASS test_perturbation_distribution")

def test_deterministic():
    plan_a = generate_financial_allocation_plan()
    plan_b = generate_financial_allocation_plan(seed=42)
    assert plan_a == plan_b, "seed=42 default != explicit seed=42"
    plan_c = generate_financial_allocation_plan(seed=42)
    assert plan_a == plan_c, "Second call differs from first"
    print("PASS test_deterministic")

def test_default_seed_42():
    plan_default = generate_financial_allocation_plan()
    plan_42 = generate_financial_allocation_plan(seed=42)
    assert plan_default == plan_42, "default != seed=42"
    print("PASS test_default_seed_42")

def test_trial_id_format():
    plan = generate_financial_allocation_plan()
    ids = [d["trial_id"] for d in plan]
    for tid in ids:
        assert re.match(r"^fa_\d{3}$", tid), f"Bad format: {tid}"
    assert len(set(ids)) == 20, f"Non-unique IDs: {ids}"
    expected_ids = [f"fa_{i:03d}" for i in range(1, 21)]
    assert ids == expected_ids, f"IDs not sequential: {ids}"
    print("PASS test_trial_id_format")

def test_generate_trial_plan_unchanged():
    """generate_trial_plan must still produce 60 trials across 3 domains."""
    plan = generate_trial_plan()
    assert len(plan) == 60, f"Expected 60, got {len(plan)}"
    for d in plan:
        assert d["trial_id"].startswith("trial_"), f"Unexpected id: {d['trial_id']}"
    print("PASS test_generate_trial_plan_unchanged")

def test_run_batch_callable():
    """run_batch must exist and be callable (identity check)."""
    assert callable(run_batch), "run_batch is not callable"
    print("PASS test_run_batch_callable")


if __name__ == "__main__":
    tests = [
        test_length,
        test_keys,
        test_domain,
        test_injection_steps,
        test_perturbation_distribution,
        test_deterministic,
        test_default_seed_42,
        test_trial_id_format,
        test_generate_trial_plan_unchanged,
        test_run_batch_callable,
    ]
    failures = []
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failures.append(t.__name__)
        except Exception as e:
            print(f"ERROR {t.__name__}: {e}")
            failures.append(t.__name__)

    print()
    if failures:
        print(f"FAILED: {failures}")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
