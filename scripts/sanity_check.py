#!/usr/bin/env python3
"""
HCode Sanity Check Script.

Verifies that both the executable and wheel package are working correctly.

Usage:
    python scripts/sanity_check.py              # Run all checks
    python scripts/sanity_check.py --exe        # Check executable only
    python scripts/sanity_check.py --whl        # Check wheel only
    python scripts/sanity_check.py --verbose    # Verbose output
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
    """Result of a sanity check."""

    name: str
    passed: bool
    message: str
    details: Optional[str] = None


class SanityChecker:
    """Runs sanity checks on HCode builds."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[CheckResult] = []
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()

        # Platform-specific settings
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
        """Print message if verbose."""
        if self.verbose:
            print(f"  {message}")

    def run_command(
        self, cmd: List[str], timeout: int = 60, cwd: Optional[Path] = None
    ) -> Tuple[int, str, str]:
        """Run a command and return (returncode, stdout, stderr)."""
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
        """Add a check result."""
        self.results.append(CheckResult(name, passed, message, details))
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}: {message}")
        if details and (not passed or self.verbose):
            for line in details.split("\n")[:10]:  # Limit output
                print(f"         {line}")

    # =========================================================================
    # EXECUTABLE CHECKS
    # =========================================================================

    def check_exe_exists(self) -> bool:
        """Check if executable exists."""
        exe_path = DIST_DIR / self.platform_name / self.exe_name
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            self.add_result(
                "Executable exists", True, f"Found at {exe_path.name} ({size_mb:.1f} MB)"
            )
            return True
        else:
            self.add_result("Executable exists", False, f"Not found: {exe_path}")
            return False

    def check_exe_version(self) -> bool:
        """Check --version flag."""
        exe_path = DIST_DIR / self.platform_name / self.exe_name
        returncode, stdout, stderr = self.run_command([str(exe_path), "--version"])

        if returncode == 0:
            self.add_result("Version check (exe)", True, "Returns version info", stdout.strip())
            return True
        else:
            self.add_result("Version check (exe)", False, "Failed to get version", stderr or stdout)
            return False

    def check_exe_help(self) -> bool:
        """Check --help flag."""
        exe_path = DIST_DIR / self.platform_name / self.exe_name
        returncode, stdout, stderr = self.run_command([str(exe_path), "--help"])

        if returncode == 0 and ("hcode" in stdout.lower() or "usage" in stdout.lower()):
            self.add_result("Help check (exe)", True, "Shows help message")
            return True
        else:
            self.add_result("Help check (exe)", False, "Failed to show help", stderr or stdout)
            return False

    def check_exe_imports(self) -> bool:
        """Check that critical imports work by running a quick command."""
        exe_path = DIST_DIR / self.platform_name / self.exe_name

        # Try running with --help which should load most modules
        returncode, stdout, stderr = self.run_command([str(exe_path), "--help"], timeout=30)

        # Check for import errors in stderr
        import_errors = [
            "ModuleNotFoundError",
            "ImportError",
            "No module named",
        ]

        for error in import_errors:
            if error in stderr:
                self.add_result(
                    "Import check (exe)", False, f"Import error detected: {error}", stderr[:500]
                )
                return False

        self.add_result("Import check (exe)", True, "No import errors detected")
        return True

    def check_exe_config_commands(self) -> bool:
        """Check config-related commands."""
        exe_path = DIST_DIR / self.platform_name / self.exe_name

        # Test 'config show' command
        returncode, stdout, stderr = self.run_command([str(exe_path), "config", "show"], timeout=30)

        if returncode == 0:
            self.add_result("Config command (exe)", True, "Config show works")
            return True
        else:
            # Not a critical failure if config isn't implemented
            self.add_result(
                "Config command (exe)",
                False,
                "Config command failed (may not be implemented)",
                stderr[:200] if stderr else stdout[:200],
            )
            return False

    def run_exe_checks(self) -> bool:
        """Run all executable checks."""
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

    # =========================================================================
    # WHEEL PACKAGE CHECKS
    # =========================================================================

    def find_wheel(self) -> Optional[Path]:
        """Find the wheel file."""
        wheel_files = list(DIST_DIR.glob("*.whl"))
        if wheel_files:
            return wheel_files[0]
        return None

    def check_wheel_exists(self) -> bool:
        """Check if wheel file exists."""
        wheel_path = self.find_wheel()
        if wheel_path:
            size_kb = wheel_path.stat().st_size / 1024
            self.add_result("Wheel exists", True, f"Found: {wheel_path.name} ({size_kb:.1f} KB)")
            return True
        else:
            self.add_result("Wheel exists", False, f"No .whl file found in {DIST_DIR}")
            return False

    def check_wheel_structure(self) -> bool:
        """Check wheel file structure."""
        import zipfile

        wheel_path = self.find_wheel()
        if not wheel_path:
            return False

        try:
            with zipfile.ZipFile(wheel_path, "r") as zf:
                names = zf.namelist()

                # Check for expected directories
                has_hcode = any(n.startswith("hcode/") for n in names)
                has_metadata = any("METADATA" in n for n in names)

                # Check for compiled extensions
                has_pyd = any(n.endswith(".pyd") for n in names)
                has_so = any(n.endswith(".so") for n in names)
                has_compiled = has_pyd or has_so

                if has_hcode and has_metadata:
                    details = f"Files: {len(names)}, Compiled extensions: {has_compiled}"
                    self.add_result("Wheel structure", True, "Valid wheel structure", details)
                    return True
                else:
                    self.add_result(
                        "Wheel structure",
                        False,
                        f"Invalid structure: hcode={has_hcode}, metadata={has_metadata}",
                    )
                    return False
        except Exception as e:
            self.add_result("Wheel structure", False, f"Error reading wheel: {e}")
            return False

    def check_wheel_install(self) -> bool:
        """Test installing the wheel in a virtual environment."""
        wheel_path = self.find_wheel()
        if not wheel_path:
            return False

        # Create temporary directory for venv
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "test_venv"

            self.log(f"Creating virtual environment at {venv_path}")

            try:
                # Create venv
                venv.create(venv_path, with_pip=True)

                # Get pip path
                if self.system == "windows":
                    pip_path = venv_path / "Scripts" / "pip.exe"
                    python_path = venv_path / "Scripts" / "python.exe"
                else:
                    pip_path = venv_path / "bin" / "pip"
                    python_path = venv_path / "bin" / "python"

                # Install the wheel
                self.log(f"Installing wheel: {wheel_path.name}")
                returncode, stdout, stderr = self.run_command(
                    [str(pip_path), "install", str(wheel_path)], timeout=120
                )

                if returncode != 0:
                    self.add_result(
                        "Wheel installation", False, "Failed to install wheel", stderr[:500]
                    )
                    return False

                self.add_result("Wheel installation", True, "Successfully installed in test venv")

                # Try importing hcode
                self.log("Testing import...")
                returncode, stdout, stderr = self.run_command(
                    [str(python_path), "-c", "import hcode; print('Import OK')"], timeout=30
                )

                if returncode == 0 and "Import OK" in stdout:
                    self.add_result(
                        "Package import (whl)", True, "Successfully imports hcode module"
                    )
                else:
                    self.add_result(
                        "Package import (whl)", False, "Failed to import hcode", stderr[:300]
                    )
                    return False

                # Check CLI entry point
                self.log("Testing CLI entry point...")
                if self.system == "windows":
                    hcode_cli = venv_path / "Scripts" / "hcode.exe"
                else:
                    hcode_cli = venv_path / "bin" / "hcode"

                if hcode_cli.exists():
                    returncode, stdout, stderr = self.run_command(
                        [str(hcode_cli), "--help"], timeout=30
                    )
                    if returncode == 0:
                        self.add_result("CLI entry point (whl)", True, "Entry point 'hcode' works")
                    else:
                        self.add_result(
                            "CLI entry point (whl)", False, "Entry point failed", stderr[:200]
                        )
                else:
                    self.add_result(
                        "CLI entry point (whl)", False, f"Entry point not found: {hcode_cli}"
                    )

                return True

            except Exception as e:
                self.add_result("Wheel installation", False, f"Error during installation test: {e}")
                return False

    def run_whl_checks(self) -> bool:
        """Run all wheel package checks."""
        print("\n" + "=" * 60)
        print("  Wheel Package Sanity Checks")
        print("=" * 60)

        if not self.check_wheel_exists():
            return False

        all_passed = True
        all_passed &= self.check_wheel_structure()
        all_passed &= self.check_wheel_install()

        return all_passed

    # =========================================================================
    # SUMMARY
    # =========================================================================

    def print_summary(self):
        """Print summary of all checks."""
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
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run sanity checks on HCode builds")
    parser.add_argument("--exe", action="store_true", help="Check executable only")
    parser.add_argument("--whl", action="store_true", help="Check wheel package only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # If neither specified, check both
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
