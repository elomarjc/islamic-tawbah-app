#!/usr/bin/env python3
"""
Standalone CLI Test Runner for Islamic Tawbah App (Feature #38).
Zero external test framework dependencies (uses standard library unittest).
Compatible with pytest discovery.
"""

import os
import sys
import time
import argparse
import unittest
from typing import List, Optional

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ANSI Color Codes
USE_COLOR = sys.stdout.isatty() or os.environ.get("FORCE_COLOR") == "1" or os.name != "nt" or "TERM" in os.environ

def _color(code: str, text: str) -> str:
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

GREEN = lambda t: _color("92", t)
RED = lambda t: _color("91", t)
YELLOW = lambda t: _color("93", t)
CYAN = lambda t: _color("96", t)
BOLD = lambda t: _color("1", t)
GRAY = lambda t: _color("90", t)


class TawbahTestResult(unittest.TestResult):
    """Custom TestResult formatting with ANSI color badges and tier reporting."""

    def __init__(self, stream=None, descriptions=None, verbosity=1):
        super().__init__(stream, descriptions, verbosity)
        self.verbosity = verbosity
        self.stream = stream or sys.stdout
        self.tier_stats = {1: {"passed": 0, "failed": 0, "skipped": 0},
                           2: {"passed": 0, "failed": 0, "skipped": 0},
                           3: {"passed": 0, "failed": 0, "skipped": 0},
                           4: {"passed": 0, "failed": 0, "skipped": 0},
                           0: {"passed": 0, "failed": 0, "skipped": 0}}
        self.start_times = {}

    def _get_tier(self, test) -> int:
        test_method = getattr(test, test._testMethodName, None)
        if test_method and hasattr(test_method, "_test_tier"):
            return getattr(test_method, "_test_tier")
        if hasattr(test, "_test_tier"):
            return getattr(test, "_test_tier")
        # Heuristic from class or module name
        name = f"{test.__class__.__module__}.{test.__class__.__name__}"
        if "scenario" in name.lower():
            return 4
        if "boundary" in name.lower():
            return 2
        if "interaction" in name.lower() or "isolation" in name.lower():
            return 3
        return 1

    def startTest(self, test):
        super().startTest(test)
        self.start_times[test.id()] = time.time()
        if self.verbosity > 1:
            tier_num = self._get_tier(test)
            doc = test.shortDescription() or test.id().split(".")[-1]
            self.stream.write(f"  {CYAN(f'[Tier {tier_num}]')} {doc} ... ")
            self.stream.flush()

    def addSuccess(self, test):
        super().addSuccess(test)
        tier_num = self._get_tier(test)
        self.tier_stats[tier_num]["passed"] += 1
        elapsed = time.time() - self.start_times.get(test.id(), time.time())
        if self.verbosity > 1:
            self.stream.write(f"{GREEN('PASS')} {GRAY(f'({elapsed:.3f}s)')}\n")
        else:
            self.stream.write(GREEN("."))
            self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        tier_num = self._get_tier(test)
        self.tier_stats[tier_num]["failed"] += 1
        if self.verbosity > 1:
            self.stream.write(f"{RED('FAIL')}\n")
        else:
            self.stream.write(RED("F"))
            self.stream.flush()

    def addError(self, test, err):
        super().addError(test, err)
        tier_num = self._get_tier(test)
        self.tier_stats[tier_num]["failed"] += 1
        if self.verbosity > 1:
            self.stream.write(f"{RED('ERROR')}\n")
        else:
            self.stream.write(RED("E"))
            self.stream.flush()

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        tier_num = self._get_tier(test)
        self.tier_stats[tier_num]["skipped"] += 1
        if self.verbosity > 1:
            self.stream.write(f"{YELLOW('SKIP')} {GRAY(f'({reason})')}\n")
        else:
            self.stream.write(YELLOW("S"))
            self.stream.flush()


def filter_suite_by_tier(suite: unittest.TestSuite, target_tier: Optional[int]) -> unittest.TestSuite:
    """Filter test suite by assigned test tier."""
    if target_tier is None:
        return suite

    filtered = unittest.TestSuite()
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            sub = filter_suite_by_tier(item, target_tier)
            if sub.countTestCases() > 0:
                filtered.addTest(sub)
        elif isinstance(item, unittest.TestCase):
            test_method = getattr(item, item._testMethodName, None)
            item_tier = None
            if test_method and hasattr(test_method, "_test_tier"):
                item_tier = getattr(test_method, "_test_tier")
            elif hasattr(item, "_test_tier"):
                item_tier = getattr(item, "_test_tier")
            else:
                # Heuristic fallback
                if "scenario" in item.__class__.__name__.lower():
                    item_tier = 4
                else:
                    item_tier = 1

            if item_tier == target_tier:
                filtered.addTest(item)
    return filtered


def run_tests(tier_filter: Optional[int] = None,
              scenarios_only: bool = False,
              verbose: bool = False,
              failfast: bool = False,
              pattern: str = "test_*.py") -> int:
    """
    Main test runner orchestration function.
    Returns standard exit code (0 = success, 1 = failure).
    """
    if scenarios_only:
        tier_filter = 4

    tests_dir = os.path.dirname(os.path.abspath(__file__))

    print(BOLD("=" * 72))
    print(BOLD(CYAN("  ISLAMIC TAWBAH APP — AUTOMATED TEST RUNNER (4-TIER SUITE)")))
    print(BOLD("=" * 72))
    print(f"  Root Directory : {PROJECT_ROOT}")
    print(f"  Tests Directory: {tests_dir}")
    print(f"  Tier Filter    : {f'Tier {tier_filter}' if tier_filter else 'All Tiers (1-4)'}")
    print(f"  Pattern Filter : {pattern}")
    print(BOLD("-" * 72))

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=tests_dir, pattern=pattern)

    if tier_filter is not None:
        suite = filter_suite_by_tier(suite, tier_filter)

    total_tests = suite.countTestCases()
    print(f"  Discovered {BOLD(str(total_tests))} test cases to execute.\n")

    if total_tests == 0:
        print(YELLOW("  [WARN] No test cases matched the specified criteria."))
        return 0

    verbosity_level = 2 if verbose else 1
    result = TawbahTestResult(verbosity=verbosity_level)
    suite._cleanup = False

    start_time = time.time()
    suite.run(result)
    total_time = time.time() - start_time

    if verbosity_level == 1:
        print("\n")

    # Print Failures & Errors Detailed Output
    if result.failures:
        print(BOLD(RED("\n" + "=" * 72)))
        print(BOLD(RED("  FAILURES")))
        print(BOLD(RED("=" * 72)))
        for test, err in result.failures:
            print(f"\n{RED('FAIL:')} {test.id()}")
            print(err)

    if result.errors:
        print(BOLD(RED("\n" + "=" * 72)))
        print(BOLD(RED("  ERRORS")))
        print(BOLD(RED("=" * 72)))
        for test, err in result.errors:
            print(f"\n{RED('ERROR:')} {test.id()}")
            print(err)

    # Summary Report
    print(BOLD("\n" + "=" * 72))
    print(BOLD(CYAN("  EXECUTION BREAKDOWN BY TIER")))
    print(BOLD("=" * 72))
    tier_names = {
        1: "Tier 1: Feature Isolation",
        2: "Tier 2: Boundary & Corner Cases",
        3: "Tier 3: Cross-Feature Interactions",
        4: "Tier 4: 10 Confession Scenarios (R5)",
    }
    for t_idx in [1, 2, 3, 4]:
        stats = result.tier_stats.get(t_idx, {"passed": 0, "failed": 0, "skipped": 0})
        t_total = stats["passed"] + stats["failed"] + stats["skipped"]
        if t_total > 0:
            print(f"  {CYAN(tier_names[t_idx]):<38} Total: {t_total:<4} "
                  f"Pass: {GREEN(str(stats['passed'])):<10} "
                  f"Fail: {RED(str(stats['failed'])):<10} "
                  f"Skip: {YELLOW(str(stats['skipped']))}")

    passed_count = len(result.failures) == 0 and len(result.errors) == 0
    total_run = result.testsRun
    failed_count = len(result.failures) + len(result.errors)
    skipped_count = len(result.skipped)
    actual_passed = total_run - failed_count - skipped_count

    print(BOLD("-" * 72))
    print(f"  Total Run    : {total_run}")
    print(f"  Passed       : {GREEN(str(actual_passed))}")
    print(f"  Failed/Errors: {RED(str(failed_count)) if failed_count > 0 else '0'}")
    print(f"  Skipped      : {YELLOW(str(skipped_count))}")
    print(f"  Duration     : {total_time:.3f} seconds")
    print(BOLD("=" * 72))

    if passed_count:
        print(BOLD(GREEN("  ✔ ALL TESTS COMPLETED SUCCESSFULLY! [STATUS: PASS]")))
        print(BOLD("=" * 72) + "\n")
        return 0
    else:
        print(BOLD(RED(f"  ✖ TEST SUITE FAILED WITH {failed_count} FAILURES/ERRORS. [STATUS: FAIL]")))
        print(BOLD("=" * 72) + "\n")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Islamic Tawbah App Automated Test Runner")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], default=None,
                        help="Filter execution to specific test tier (1, 2, 3, or 4)")
    parser.add_argument("--scenarios-only", action="store_true",
                        help="Shortcut to execute only the 10 required confession scenarios (Tier 4)")
    parser.add_argument("-v", "--verbose", action="store_true", default=True,
                        help="Verbose output displaying each test method and execution duration")
    parser.add_argument("--failfast", action="store_true",
                        help="Stop the test run on the first failure or error")
    parser.add_argument("--pattern", type=str, default="test_*.py",
                        help="Test filename discovery pattern (default: test_*.py)")

    args = parser.parse_args()
    exit_code = run_tests(
        tier_filter=args.tier,
        scenarios_only=args.scenarios_only,
        verbose=args.verbose,
        failfast=args.failfast,
        pattern=args.pattern
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
