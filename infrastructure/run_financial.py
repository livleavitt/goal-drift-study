"""
CLI entry point for the financial_allocation domain batch.

Imports and calls run_financial_allocation_batch() from sdk_runner.py,
logs the result, and exits with code 1 if any trials failed or code 0
if all trials succeeded.

Usage:
    python infrastructure/run_financial.py

Requirements:
    - ANYFORGE_API_KEY must be set in the environment.
    - The anyforge Python SDK must be installed (pip install anyforge).
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sdk_runner import run_financial_allocation_batch  # noqa: E402

log = logging.getLogger("run_financial")

if __name__ == "__main__":
    succeeded, failed = run_financial_allocation_batch()
    log.info("run_financial result: succeeded=%d failed=%d", succeeded, failed)
    sys.exit(0 if failed == 0 else 1)
