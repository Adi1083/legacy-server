"""
Master QA Verification Suite Runner for Free Fire 1.39 Luck Royale.
Executes all 8 automated test modules, captures granular results,
and outputs the definitive QA Verification Matrix.
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path

# Ensure server root is in sys.path
SERVER_DIR = str(Path(__file__).resolve().parent.parent)
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

# Test modules to run in logical order
TEST_MODULES = [
    ("Machine Config", "tests.test_machine_config"),
    ("Spin Execution", "tests.test_spin_execution"),
    ("Economy & Balance", "tests.test_economy"),
    ("Reward & Gacha Logic", "tests.test_reward_gacha"),
    ("Incubator Forge", "tests.test_incubator_forge"),
    ("Admin API & Dashboard", "tests.test_admin_api"),
    ("Persistence & Recovery", "tests.test_persistence"),
    ("Core Regression", "tests.test_regression"),
]


def run_master_test_suite() -> int:
    print("=" * 78)
    print("  FREE FIRE 1.39 LUCK ROYALE RESTORATION - MASTER QA TEST RUNNER")
    print("=" * 78)

    loader = unittest.TestLoader()
    suite_results = []
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0

    overall_start = time.perf_counter()

    for name, module_path in TEST_MODULES:
        print(f"\n[RUNNING] Suite: {name} ({module_path})...")
        suite_start = time.perf_counter()
        suite = loader.loadTestsFromName(module_path)
        
        # Run suite with quiet runner to aggregate cleanly
        runner = unittest.TextTestRunner(verbosity=1)
        result = runner.run(suite)
        suite_duration = time.perf_counter() - suite_start

        passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
        suite_results.append({
            "name": name,
            "module": module_path,
            "run": result.testsRun,
            "passed": passed,
            "failed": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "duration": suite_duration,
            "status": "PASS" if result.wasSuccessful() else "FAIL",
            "failures_detail": result.failures,
            "errors_detail": result.errors,
        })

        total_tests += result.testsRun
        total_failures += len(result.failures)
        total_errors += len(result.errors)
        total_skipped += len(result.skipped)

    overall_duration = time.perf_counter() - overall_start

    # Print Summary Table
    print("\n" + "=" * 78)
    print("                      QA TEST EXECUTION SUMMARY MATRIX")
    print("=" * 78)
    print(f"{'#':<3} {'Test Suite Name':<28} {'Tests':<7} {'Passed':<8} {'Fail':<6} {'Err':<5} {'Time':<7} {'Status'}")
    print("-" * 78)

    for idx, r in enumerate(suite_results, 1):
        status_str = "PASS" if r["status"] == "PASS" else "**FAIL**"
        print(f"{idx:<3} {r['name']:<28} {r['run']:<7} {r['passed']:<8} {r['failed']:<6} {r['errors']:<5} {r['duration']:<6.3f}s {status_str}")

    print("-" * 78)
    total_passed = total_tests - total_failures - total_errors - total_skipped
    print(f"TOTAL: {total_tests} tests executed in {overall_duration:.3f}s | Passed: {total_passed} | Failures: {total_failures} | Errors: {total_errors} | Skipped: {total_skipped}")
    print("=" * 78)

    if total_failures == 0 and total_errors == 0:
        print("\n>>> ALL TEST SUITES PASSED PERFECTLY (100% SUCCESS RATE) <<<\n")
        return 0
    else:
        print(f"\n>>> TEST SUITE FAILED: {total_failures} failure(s), {total_errors} error(s) <<<\n")
        return 1


if __name__ == "__main__":
    exit_code = run_master_test_suite()
    sys.exit(exit_code)
