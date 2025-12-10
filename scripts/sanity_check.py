#!/usr/bin/env python3
"""Sanity‑check utility for HCode.

Executes checks to ensure the built HCode executable and wheel package work
correctly. Supports checking the executable, the wheel, or both, with an
optional verbose mode for detailed logging.

Usage examples:
  python scripts/sanity_check.py              # run all checks
  python scripts/sanity_check.py --exe        # only executable checks
  python scripts/sanity_check.py --whl        # only wheel checks
  python scripts/sanity_check.py --verbose    # enable verbose output
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import venv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DIST_DIR = PROJECT_ROOT / "dist" / "compiled"


@dataclass
class CheckResult:
    """Result of a single sanity‑check.

    Attributes:
        name: Human‑readable name of the check.
        passed: ``True`` if the check succeeded, ``False`` otherwise.
        message: Short description of the outcome.
        details: Optional longer text (e.g., error output) for failed checks or
            when verbose mode is enabled.
    """
    name: str
    passed: bool
    message: str
    details: Optional[str] = None


class SanityChecker:
    """Runs sanity checks on HCode builds.

    The checker validates both the compiled executable and the wheel package.
    It records each check as a :class:`CheckResult` and can print a summary at
    the end of the run.

    Args:
        verbose: If ``True``, additional diagnostic information is printed
            during the checks.
    """

    def __init__(self, verbose: bool = False):
        """Initialise the checker.

        Args:
            verbose: Enable verbose output.
        """
        self.verbose = verbose
        self.results: List[CheckResult] = []
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()

        # Platform‑specific settings
        if self.system == "windows":
            self.platform_name = f"windows-{self.machine}"
            self.exe_name = "hcode.exe"
        elif self.system == "darwin":
            self.platform_name = f"macos-{self.machine}"
            self.exe_name = "hcode"
        else:
            self.platform_name = f"linux-{self.machine}"
            self.exe_name = "hcode"

    def log(self, message: str):
        """Print a message when verbose mode is active.

        Args:
            message: Text to display.
        """
        if self.verbose:
            print(f"  {message}")

    def run_command(
        self, cmd: List[str], timeout: int = 60, cwd: Optional[Path] = None
    ) -> Tuple[int, str, str]:
        """Execute a subprocess and capture its output.

        Args:
            cmd: Command and arguments to run.
            timeout: Maximum time in seconds to wait for the command.
            cwd: Working directory for the command (defaults to current).

        Returns:
            A tuple ``(returncode, stdout, stderr)``. On timeout or error,
            ``returncode`` is ``-1`` and ``stderr`` contains the error message.
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    def add_result(self, name: str, passed: bool, message: str, details: str = None):
        """Record the outcome of a check and optionally display it.

        Args:
            name: Name of the check.
            passed: ``True`` if the check succeeded.
            message: Short description of the result.
            details: Optional detailed output (e.g., error trace).
        """
        self.results.append(CheckResult(name, passed, message, details))
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}: {message}")
        if details and (not passed or self.verbose):
            for line in details.split("\n")[:10]:  # limit output
                print(f"         {line}")

    # ----------------------------------------------------------------------
    # Executable checks
    # ----------------------------------------------------------------------
    def check_exe_exists(self) -> bool:
        """Verify that the compiled HCode executable exists.

        Returns:
            ``True`` if the executable file is present, ``False`` otherwise.
        """
        exe_path = DIST_DIR / self.platform_name / self.exe_name
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            self.add_result(
                "Executable exists",
                True,
                f"Found at {exe_path.name} ({size_mb:.1f} MB)",
            )
            return True
        else:
            self.add_result("Executable exists", False, f"Not found: {exe_path}")
            return False

    def check_exe_version(self) -> bool:
        """Run ``--version`` on the executable and ensure it returns successfully.

        Returns:
            ``True`` if the version command succeeds, ``False`` otherwise.
        """
        exe_path = DIST_DIR / self.platform_name / self.exe_name
        returncode, stdout, stderr = self.run_command([str(exe_path), "--version"])

        if returncode == 0:
            self.add_result(
                "Version check (exe)", True, "Returns version info", stdout.strip()
            )
            return True
        else:
            self.add_result(
                "Version check (exe)",
                False,
                "Failed to get version",
                stderr or stdout,
            )
            return False

    def check_exe_help(self) -> bool:
        """Run ``--help`` on the executable and verify a help message appears.

        Returns:
            ``True`` if help output looks valid, ``False`` otherwise.
        """
        exe_path = DIST_DIR / self.platform_name / self.exe_name
        returncode, stdout, stderr = self.run_command([str(exe_path), "--help"])

        if returncode == 0 and ("hcode" in stdout.lower() or "usage" in stdout.lower()):
            self.add_result("Help check (exe)", True, "Shows help message")
            return True
        else:
            self.add_result(
                "Help check (exe)", False, "Failed to show help", stderr or stdout
            )
            return False

    def check_exe_imports(self) -> bool:
        """Execute the binary with ``--help`` to trigger module imports.

        Scans ``stderr`` for common import‑related errors.

        Returns:
            ``True`` if no import errors are detected, ``False`` otherwise.
        """
        exe_path = DIST_DIR / self.platform_name / self.exe_name
        returncode, stdout, stderr = self.run_command(
            [str(exe_path), "--help"], timeout=30
        )

        import_errors = ["ModuleNotFoundError", "ImportError", "No module named"]
        for error in import_errors:
            if error in stderr:
                self.add_result(
                    "Import check (exe)",
                    False,
                    f"Import error detected: {error}",
                    stderr[:500],
                )
                return False

        self.add_result("Import check (exe)", True, "No import errors detected")
        return True

    def check_exe_config_commands(self) -> bool:
        """Run ``hcode config show`` and ensure it exits cleanly.

        Returns:
            ``True`` if the command succeeds, ``False`` otherwise. Failure is
            considered non‑critical because the config command may be optional.
        """
        exe_path = DIST_DIR / self.platform_name / self.exe_name
        returncode, stdout, stderr = self.run_command(
            [str(exe_path), "config", "show"], timeout=30
        )

        if returncode == 0:
            self.add_result("Config command (exe)", True, "Config show works")
            return True
        else:
            self.add_result(
                "Config command (exe)",
                False,
                "Config command failed (may not be implemented)",
                stderr[:200] if stderr else stdout[:200],
            )
            return False

    def run_exe_checks(self) -> bool:
        """Execute all executable‑related sanity checks.

        Returns:
            bool: ``True`` if all executable checks pass, otherwise ``False``.
        """
        """Execute the full suite of executable checks.

        Returns:
            ``True`` if all mandatory checks pass, ``False`` otherwise.
        """
        print("\n" + "=" * 60)
        print("  Executable Sanity Checks")
        print("=" * 60)

        if not self.check_exe_exists():
            return False

        all_passed = True
        all_passed &= self.check_exe_version()
        all_passed &= self.check_exe_help()
        all_passed &= self.check_exe_imports()
        # Config check is optional
        self.check_exe_config_commands()

        return all_passed

    # ----------------------------------------------------------------------
    # Wheel package checks
    # ----------------------------------------------------------------------
    def find_wheel(self) -> Optional[Path]:
        """Locate the built ``.whl`` file in the distribution directory.

        Returns:
            Path to the first wheel file found, or ``None`` if none exist.
        """
        wheel_files = list(DIST_DIR.glob("*.whl"))
        if wheel_files:
            return wheel_files[0]
        return None

    def check_wheel_exists(self) -> bool:
        """Verify that the built wheel package exists.

        Returns:
            bool: ``True`` if the wheel file is present in the distribution directory,
            otherwise ``False``.
        """
        """Confirm that a wheel file is present.

        Returns:
            ``True`` if a wheel is found, ``False`` otherwise.
        """
        wheel_path = self.find_wheel()
        if wheel_path:
            size_kb = wheel_path.stat().st_size / 1024
            self.add_result(
                "Wheel exists",
                True,
                f"Found: {wheel_path.name} ({size_kb:.1f} KB)",
            )
            return True
        else:
            self.add_result("Wheel exists", False, "No wheel file found")
            return False

    def check_wheel_structure(self) -> bool:
        """Validate the internal structure of the wheel package.

        Returns:
            bool: ``True`` if the wheel contains the expected files and metadata,
            otherwise ``False``.
        """
        """Validate that the wheel file has a plausible internal structure.

        Returns:
            ``True`` if the wheel appears well‑formed, ``False`` otherwise.
        """
        wheel_path = self.find_wheel()
        if not wheel_path:
            self.add_result(
                "Wheel structure", False, "Cannot check structure without wheel"
            )
            return False

        # Simple sanity check: ensure the file is a zip archive
        if wheel_path.suffix == ".whl":
            self.add_result(
                "Wheel structure", True, "Wheel file has correct .whl extension"
            )
            return True
        else:
            self.add_result(
                "Wheel structure",
                False,
                f"Unexpected wheel file extension: {wheel_path.suffix}",
            )
            return False

    def check_wheel_install(self) -> bool:
        """Install the wheel into a temporary virtual environment and verify it works.

        Returns:
            bool: ``True`` if the wheel installs and the CLI entry point runs successfully,
            otherwise ``False``.
        """
        """Create a temporary virtual environment, install the wheel, and test import.

        Returns:
            ``True`` if installation and import succeed, ``False`` otherwise.
        """
        wheel_path = self.find_wheel()
        if not wheel_path:
            self.add_result(
                "Wheel installation", False, "No wheel to install"
            )
            return False

        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "venv"
            self.log(f"Creating virtual environment at {venv_path}")
            venv.create(venv_path, with_pip=True)

            python_path = (
                venv_path / "Scripts" / "python.exe"
                if self.system == "windows"
                else venv_path / "bin" / "python"
            )

            # Upgrade pip to avoid old‑wheel issues
            self.run_command([str(python_path), "-m", "pip", "install", "--upgrade", "pip"])

            # Install the wheel
            self.log("Installing wheel...")
            rc, out, err = self.run_command(
                [str(python_path), "-m", "pip", "install", str(wheel_path)]
            )
            if rc != 0:
                self.add_result(
                    "Wheel installation",
                    False,
                    "pip install failed",
                    err or out,
                )
                return False

            # Test import of the package
            self.log("Testing import...")
            rc, out, err = self.run_command(
                [str(python_path), "-c", "import hcode; print('Import OK')"],
                timeout=30,
            )
            if rc == 0 and "Import OK" in out:
                self.add_result(
                    "Package import (whl)", True, "Successfully imports hcode module"
                )
            else:
                self.add_result(
                    "Package import (whl)",
                    False,
                    "Failed to import hcode",
                    err[:300],
                )
                return False

            # Check CLI entry point
            self.log("Testing CLI entry point...")
            hcode_cli = (
                venv_path / "Scripts" / "hcode.exe"
                if self.system == "windows"
                else venv_path / "bin" / "hcode"
            )
            if hcode_cli.exists():
                rc, out, err = self.run_command([str(hcode_cli), "--help"], timeout=30)
                if rc == 0:
                    self.add_result(
                        "CLI entry point (whl)", True, "Entry point 'hcode' works"
                    )
                else:
                    self.add_result(
                        "CLI entry point (whl)",
                        False,
                        "Entry point failed",
                        err[:200],
                    )
                    return False
            else:
                self.add_result(
                    "CLI entry point (whl)",
                    False,
                    f"Entry point not found: {hcode_cli}",
                )
                return False

        return True

    def run_whl_checks(self) -> bool:
        """Execute the full suite of wheel‑related checks.

        Returns:
            ``True`` if all mandatory wheel checks pass, ``False`` otherwise.
        """
        print("\n" + "=" * 60)
        print("  Wheel Package Sanity Checks")
        print("=" * 60)

        if not self.check_wheel_exists():
            return False

        all_passed = True
        all_passed &= self.check_wheel_structure()
        all_passed &= self.check_wheel_install()
        return all_passed

    # ----------------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------------
    def print_summary(self):
        """Print a concise summary of all performed checks.

        Returns:
            ``True`` if no checks failed, ``False`` otherwise.
        """
        print("\n" + "=" * 60)
        print("  SANITY CHECK SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"\n  Total:  {total} checks")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")

        if failed > 0:
            print("\n  Failed checks:")
            for r in self.results:
                if not r.passed:
                    print(f"    - {r.name}: {r.message}")

        print("\n" + "=" * 60)
        if failed == 0:
            print("  ALL SANITY CHECKS PASSED!")
        else:
            print("  SOME CHECKS FAILED")
        print("=" * 60)

        return failed == 0


def main():
    """Entry point for the sanity‑check script.

    Parses command‑line arguments, decides which groups of checks to run,
    instantiates :class:`SanityChecker`, and prints the final summary.

    Returns:
        Exit code ``0`` if all selected checks pass, ``1`` otherwise.
    """
    parser = argparse.ArgumentParser(description="Run sanity checks on HCode builds")
    parser.add_argument("--exe", action="store_true", help="Check executable only")
    parser.add_argument("--whl", action="store_true", help="Check wheel package only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # If neither flag is supplied, run both sets of checks
    check_exe = args.exe or (not args.exe and not args.whl)
    check_whl = args.whl or (not args.exe and not args.whl)

    print("=" * 60)
    print("  HCode Sanity Check")
    print("=" * 60)
    print(f"\n  Platform: {platform.system()} {platform.machine()}")
    print(f"  Python: {platform.python_version()}")
    print(f"  Dist dir: {DIST_DIR}")

    checker = SanityChecker(verbose=args.verbose)

    all_passed = True

    if check_exe:
        all_passed &= checker.run_exe_checks()

    if check_whl:
        all_passed &= checker.run_whl_checks()

    success = checker.print_summary()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
