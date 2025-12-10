#!/usr/bin/env python3
"""Refactored HCode Protected Build Script.

This script builds an obfuscated Python package and executable using PyArmor and PyInstaller.
It replaces ad‑hoc prints with structured logging, removes unsafe shell usage, and adds type hints.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
HCODE_SRC = SRC_DIR / "hcode"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
PROTECTED_DIR = BUILD_DIR / "protected"


def run_command(cmd: List[str], description: str, cwd: Path | None = None) -> None:
    """Execute a command, logging its progress.

    Args:
        cmd: Command and arguments as a list.
        description: Human‑readable description for logging.
        cwd: Working directory for the command.
    """
    logger.info("%s", description)
    logger.debug("Running command: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.debug("stdout: %s", result.stdout)
        logger.debug("stderr: %s", result.stderr)
        logger.info("%s succeeded", description)
    except subprocess.CalledProcessError as e:
        logger.error("%s failed (exit %s)", description, e.returncode)
        logger.error("stderr: %s", e.stderr.strip())
        raise


def clean_build_artifacts() -> None:
    """Remove all generated build directories and temporary files."""
    logger.info("Cleaning build artifacts...")
    dirs_to_clean = [BUILD_DIR, DIST_DIR, PROJECT_ROOT / "hcode.egg-info", PROJECT_ROOT / ".pyarmor"]
    for d in dirs_to_clean:
        if d.exists():
            shutil.rmtree(d)
            logger.debug("Removed directory: %s", d)
    # Remove .spec files
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()
        logger.debug("Removed spec file: %s", spec)
    # Remove __pycache__ (excluding virtual env)
    for cache in PROJECT_ROOT.rglob("__pycache__"):
        if ".venv" not in str(cache):
            shutil.rmtree(cache)
            logger.debug("Removed __pycache__: %s", cache)
    logger.info("Clean complete.")


def check_pyarmor() -> bool:
    """Verify that PyArmor is installed and callable."""
    try:
        result = subprocess.run(
            ["pyarmor", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        version_line = result.stdout.strip().split("\n")[0]
        logger.info("PyArmor detected: %s", version_line)
        return True
    except Exception as e:
        logger.error("PyArmor check failed: %s", e)
        return False


def obfuscate_code() -> bool:
    """Obfuscate the HCode source using PyArmor."""
    PROTECTED_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Obfuscating source: %s -> %s", HCODE_SRC, PROTECTED_DIR)
    cmd = [
        "pyarmor",
        "gen",
        "--output",
        str(PROTECTED_DIR),
        "--recursive",
        str(HCODE_SRC),
    ]
    try:
        run_command(cmd, "Obfuscating with PyArmor")
        return True
    except Exception:
        logger.error("Obfuscation failed. Trial version may have limits.")
        return False


def build_protected_package() -> bool:
    """Create a wheel/tarball from the obfuscated code."""
    temp_src = BUILD_DIR / "pkg_src" / "src"
    temp_src.mkdir(parents=True, exist_ok=True)
    protected_hcode = PROTECTED_DIR / "hcode"
    if not protected_hcode.exists():
        logger.error("Obfuscated code not found; run obfuscation first.")
        return False
    dest_hcode = temp_src / "hcode"
    if dest_hcode.exists():
        shutil.rmtree(dest_hcode)
    shutil.copytree(protected_hcode, dest_hcode)
    # Copy supporting files
    shutil.copy(PROJECT_ROOT / "pyproject.toml", BUILD_DIR / "pkg_src" / "pyproject.toml")
    readme = PROJECT_ROOT / "README.md"
    if readme.exists():
        shutil.copy(readme, BUILD_DIR / "pkg_src" / "README.md")
    # Build package using the `build` module
    cmd = [sys.executable, "-m", "build", "--outdir", str(DIST_DIR / "protected")]
    try:
        run_command(cmd, "Building protected package", cwd=BUILD_DIR / "pkg_src")
        return True
    except Exception:
        return False


def build_protected_exe() -> bool:
    """Package the obfuscated code into a standalone executable via PyInstaller."""
    import platform

    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "windows":
        exe_name = "hcode.exe"
    else:
        exe_name = "hcode"
    protected_hcode = PROTECTED_DIR / "hcode"
    if not protected_hcode.exists():
        logger.error("Obfuscated code not found; run obfuscation first.")
        return False
    exe_build_dir = BUILD_DIR / "exe_build"
    exe_build_dir.mkdir(parents=True, exist_ok=True)
    # Copy source
    exe_src = exe_build_dir / "hcode"
    if exe_src.exists():
        shutil.rmtree(exe_src)
    shutil.copytree(protected_hcode, exe_src)
    # Create entry point script
    entry_point = exe_build_dir / "hcode_main.py"
    entry_point.write_text(
        """#!/usr/bin/env python3
# HCode entry point for PyInstaller.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hcode.cli_enhanced import main
if __name__ == '__main__':
    main()
"""
    )
    # PyInstaller command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name",
        exe_name,
        str(entry_point),
    ]
    try:
        run_command(cmd, "Building protected executable", cwd=exe_build_dir)
        # Move the generated exe to dist
        dist_path = DIST_DIR / "protected"
        dist_path.mkdir(parents=True, exist_ok=True)
        built_exe = exe_build_dir / "dist" / exe_name
        if built_exe.exists():
            shutil.move(str(built_exe), str(dist_path / exe_name))
            logger.info("Executable moved to %s", dist_path / exe_name)
        return True
    except Exception:
        return False


def verify_builds() -> bool:
    """Run basic sanity checks on the produced artifacts."""
    all_passed = True
    # Verify executable
    exe_path = DIST_DIR / "protected" / ("hcode.exe" if os.name == "nt" else "hcode")
    if exe_path.exists():
        logger.info("Verifying executable %s", exe_path)
        try:
            result = subprocess.run([str(exe_path), "--version"], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info("Executable version: %s", result.stdout.strip())
            else:
                logger.error("Executable returned error code %s", result.returncode)
                all_passed = False
        except Exception as e:
            logger.error("Executable verification failed: %s", e)
            all_passed = False
    else:
        logger.warning("Executable not found for verification.")
        all_passed = False
    # Verify package
    pkg_dir = DIST_DIR / "protected"
    if pkg_dir.exists():
        wheels = list(pkg_dir.glob("*.whl"))
        if wheels:
            logger.info("Found wheel package: %s (size %.2f KB)", wheels[0].name, wheels[0].stat().st_size / 1024)
        else:
            logger.warning("No wheel package found.")
            all_passed = False
    else:
        logger.warning("Package directory missing.")
        all_passed = False
    return all_passed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build protected HCode package and executable")
    parser.add_argument("--pkg", action="store_true", help="Build only Python package")
    parser.add_argument("--exe", action="store_true", help="Build only executable")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts only")
    parser.add_argument("--no-verify", action="store_true", help="Skip verification step")
    parser.add_argument("--no-obfuscate", action="store_true", help="Skip obfuscation (use existing)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger.info("=== HCode Protected Build ===")
    if args.clean:
        clean_build_artifacts()
        return 0
    # Determine targets
    build_pkg = args.pkg or (not args.pkg and not args.exe)
    build_exe = args.exe or (not args.pkg and not args.exe)
    # Ensure PyArmor is available
    if not check_pyarmor():
        logger.error("PyArmor not available. Install with: pip install pyarmor pyarmor.cli.core")
        return 1
    # Clean previous outputs
    clean_build_artifacts()
    # Obfuscate if requested
    if not args.no_obfuscate:
        if not obfuscate_code():
            logger.error("Obfuscation failed.")
            return 1
    # Build package
    if build_pkg:
        try:
            import build  # noqa: F401
        except ImportError:
            logger.info("Installing build module...")
            run_command([sys.executable, "-m", "pip", "install", "build"], "Installing build module")
        if not build_protected_package():
            logger.error("Package build failed.")
            return 1
    # Build executable
    if build_exe:
        try:
            import PyInstaller  # noqa: F401
        except ImportError:
            logger.info("Installing PyInstaller...")
            run_command([sys.executable, "-m", "pip", "install", "pyinstaller"], "Installing PyInstaller")
        if not build_protected_exe():
            logger.error("Executable build failed.")
            return 1
    # Verification
    if not args.no_verify:
        if not verify_builds():
            logger.error("Verification failed.")
            return 1
    logger.info("BUILD SUCCESSFUL!")
    logger.info("Output directory: %s", DIST_DIR / "protected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
