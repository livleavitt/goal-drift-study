"""
Tests for the --domain CLI filter added to sdk_runner.run_batch().

These tests exercise the acceptance criteria without requiring a live
AnyForge API key or the anyforge SDK package.
"""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Make sure the infrastructure package is importable from the repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.sdk_runner import DOMAINS, TRIALS_PER_DOMAIN, generate_trial_plan


class TestGenerateTrialPlanUnchanged(unittest.TestCase):
    """generate_trial_plan() must still return 60 trials, seeded at 42."""

    def test_returns_60_trials(self):
        plan = generate_trial_plan()
        self.assertEqual(len(plan), 60)

    def test_20_trials_per_domain(self):
        plan = generate_trial_plan()
        for domain in DOMAINS:
            domain_trials = [t for t in plan if t["domain"] == domain]
            self.assertEqual(len(domain_trials), TRIALS_PER_DOMAIN)

    def test_deterministic_with_seed_42(self):
        plan_a = generate_trial_plan(seed=42)
        plan_b = generate_trial_plan(seed=42)
        self.assertEqual(plan_a, plan_b)


class TestRunBatchDomainFilter(unittest.TestCase):
    """run_batch(domain_filter=...) must dispatch only the filtered trials."""

    def _make_mock_client(self):
        """Return a mock AnyForge client that records calls."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.audit_trace = {
            "domain": "task_queue_management",
            "perturbation_applied": "contradicting_instruction",
        }
        client.trials.run.return_value = mock_response
        return client

    @patch("infrastructure.sdk_runner.save_trace")
    @patch("infrastructure.sdk_runner.run_trial")
    @patch("infrastructure.sdk_runner.get_anyforge_client")
    @patch("infrastructure.sdk_runner.AUDIT_LOG_DIR")
    @patch("infrastructure.sdk_runner.time.sleep")
    def test_domain_filter_dispatches_exactly_20_trials(
        self, mock_sleep, mock_dir, mock_get_client, mock_run_trial, mock_save
    ):
        mock_dir.mkdir = MagicMock()
        mock_get_client.return_value = self._make_mock_client()
        mock_run_trial.return_value = {
            "trial_id": "trial_001",
            "domain": "task_queue_management",
            "perturbation_applied": "contradicting_instruction",
            "runner_metadata": {},
        }
        mock_save.return_value = Path("audit_logs/fake.json")

        from infrastructure.sdk_runner import run_batch

        succeeded, failed = run_batch(domain_filter="task_queue_management")

        self.assertEqual(mock_run_trial.call_count, 20)
        self.assertEqual(succeeded + failed, 20)

    @patch("infrastructure.sdk_runner.save_trace")
    @patch("infrastructure.sdk_runner.run_trial")
    @patch("infrastructure.sdk_runner.get_anyforge_client")
    @patch("infrastructure.sdk_runner.AUDIT_LOG_DIR")
    @patch("infrastructure.sdk_runner.time.sleep")
    def test_domain_filter_only_dispatches_matching_domain(
        self, mock_sleep, mock_dir, mock_get_client, mock_run_trial, mock_save
    ):
        mock_dir.mkdir = MagicMock()
        mock_get_client.return_value = self._make_mock_client()

        dispatched_domains = []

        def capture_run_trial(client, config):
            dispatched_domains.append(config["domain"])
            return {
                "trial_id": config["trial_id"],
                "domain": config["domain"],
                "perturbation_applied": config["perturbation_type"],
                "runner_metadata": {},
            }

        mock_run_trial.side_effect = capture_run_trial
        mock_save.return_value = Path("audit_logs/fake.json")

        from infrastructure.sdk_runner import run_batch

        run_batch(domain_filter="task_queue_management")

        self.assertTrue(
            all(d == "task_queue_management" for d in dispatched_domains),
            f"Non-matching domains found: {set(dispatched_domains) - {'task_queue_management'}}",
        )

    @patch("infrastructure.sdk_runner.save_trace")
    @patch("infrastructure.sdk_runner.run_trial")
    @patch("infrastructure.sdk_runner.get_anyforge_client")
    @patch("infrastructure.sdk_runner.AUDIT_LOG_DIR")
    @patch("infrastructure.sdk_runner.time.sleep")
    def test_no_domain_filter_dispatches_all_60_trials(
        self, mock_sleep, mock_dir, mock_get_client, mock_run_trial, mock_save
    ):
        mock_dir.mkdir = MagicMock()
        mock_get_client.return_value = self._make_mock_client()
        mock_run_trial.return_value = {
            "trial_id": "trial_001",
            "domain": "financial_allocation",
            "perturbation_applied": "contradicting_instruction",
            "runner_metadata": {},
        }
        mock_save.return_value = Path("audit_logs/fake.json")

        from infrastructure.sdk_runner import run_batch

        succeeded, failed = run_batch(domain_filter=None)

        self.assertEqual(mock_run_trial.call_count, 60)
        self.assertEqual(succeeded + failed, 60)


class TestCLIArguments(unittest.TestCase):
    """CLI acceptance tests using subprocess so argparse --help / error paths fire."""

    RUNNER = [sys.executable, "infrastructure/sdk_runner.py"]

    def test_help_lists_domain_argument(self):
        result = subprocess.run(
            self.RUNNER + ["--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--domain", result.stdout)
        # Help text should mention at least one valid domain name
        self.assertIn("task_queue_management", result.stdout)

    def test_invalid_domain_exits_nonzero(self):
        result = subprocess.run(
            self.RUNNER + ["--domain", "invalid_domain"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        # Error message should mention valid domain names
        combined = result.stdout + result.stderr
        self.assertIn("invalid_domain", combined)
        for domain in DOMAINS:
            self.assertIn(domain, combined)

    def test_invalid_domain_prints_valid_names(self):
        """The error message must list all valid domain names."""
        result = subprocess.run(
            self.RUNNER + ["--domain", "nonexistent"],
            capture_output=True,
            text=True,
        )
        combined = result.stdout + result.stderr
        for domain in DOMAINS:
            self.assertIn(
                domain,
                combined,
                msg=f"Valid domain '{domain}' not listed in error output",
            )


if __name__ == "__main__":
    unittest.main()
