#!/usr/bin/env python3
"""
Comprehensive test runner for the Tattoo Studio System.

This script provides various test execution options including:
- Running all tests
- Running tests by category (unit, integration, security, auth)
- Running tests with coverage reports
- Running tests with detailed output options
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"🔬 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(command)}")
    print()

    result = subprocess.run(command, capture_output=False, text=True)

    if result.returncode == 0:
        print(f"\n✅ {description} - SUCCESS")
    else:
        print(f"\n❌ {description} - FAILED (exit code: {result.returncode})")

    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for Tattoo Studio System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit             # Run only unit tests
  python run_tests.py --integration      # Run only integration tests
  python run_tests.py --security         # Run only security tests
  python run_tests.py --auth             # Run only auth tests
  python run_tests.py --coverage         # Run all tests with coverage
  python run_tests.py --verbose          # Run tests with verbose output
  python run_tests.py --quick            # Run tests with minimal output
        """,
    )

    # Test category options
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument(
        "--integration", action="store_true", help="Run only integration tests"
    )
    parser.add_argument(
        "--security", action="store_true", help="Run only security-related tests"
    )
    parser.add_argument(
        "--auth", action="store_true", help="Run only authentication tests"
    )

    # Output options
    parser.add_argument(
        "--coverage", action="store_true", help="Run tests with coverage report"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Run tests with verbose output"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Run tests with minimal output"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Run tests with quick feedback (fail fast)"
    )

    # File/pattern options
    parser.add_argument("--file", type=str, help="Run tests from specific file")
    parser.add_argument("--pattern", type=str, help="Run tests matching pattern")

    args = parser.parse_args()

    # Build pytest command
    base_cmd = [sys.executable, "-m", "pytest"]

    # Determine test scope
    test_paths = []
    markers = []

    if args.unit:
        markers.append("unit")
    if args.integration:
        markers.append("integration")
    if args.security:
        markers.append("security")
    if args.auth:
        markers.append("auth")

    if args.file:
        test_paths.append(args.file)
    elif not any([args.unit, args.integration, args.security, args.auth]):
        # Default: run all tests
        test_paths.append("tests/")

    # Add markers if specified
    if markers:
        base_cmd.extend(["-m", " or ".join(markers)])

    # Add test paths
    if test_paths:
        base_cmd.extend(test_paths)
    else:
        base_cmd.append("tests/")

    # Add pattern matching
    if args.pattern:
        base_cmd.extend(["-k", args.pattern])

    # Add output options
    if args.verbose:
        base_cmd.append("-v")
    elif args.quiet:
        base_cmd.append("-q")

    if args.quick:
        base_cmd.append("-x")  # fail fast

    # Coverage options
    if args.coverage:
        coverage_cmd = [
            sys.executable,
            "-m",
            "pytest",
            "--cov=app",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml",
        ]

        # Add the same test selection options to coverage
        if markers:
            coverage_cmd.extend(["-m", " or ".join(markers)])

        if test_paths:
            coverage_cmd.extend(test_paths)
        else:
            coverage_cmd.append("tests/")

        if args.pattern:
            coverage_cmd.extend(["-k", args.pattern])

        if args.verbose:
            coverage_cmd.append("-v")
        elif args.quiet:
            coverage_cmd.append("-q")

        return_code = run_command(coverage_cmd, "Running tests with coverage")

        if return_code == 0:
            print(f"\n📊 Coverage report generated:")
            print(f"   - HTML: htmlcov/index.html")
            print(f"   - XML:  coverage.xml")
    else:
        return_code = run_command(base_cmd, "Running tests")

    # Summary
    print(f"\n{'='*60}")
    if return_code == 0:
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
    else:
        print("💥 SOME TESTS FAILED!")
        print("Check the output above for details.")
    print(f"{'='*60}")

    return return_code


if __name__ == "__main__":
    # Ensure we're in the backend directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    exit_code = main()
    sys.exit(exit_code)
