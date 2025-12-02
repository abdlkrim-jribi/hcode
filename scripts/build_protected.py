#!/usr/bin/env python3
"""
HCode Protected Build Script.

Uses PyArmor for code obfuscation before building Python package and executable.

Usage:
    python scripts/build_protected.py           # Build both package and exe
    python scripts/build_protected.py --pkg     # Build only Python package
    python scripts/build_protected.py --exe     # Build only executable
    python scripts/build_protected.py --clean   # Clean build artifacts
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
HCODE_SRC = SRC_DIR / "hcode"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
PROTECTED_DIR = BUILD_DIR / "protected"


def run_command(cmd: list[str], description: str, cwd: Path | None = None) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd[:5])}...")

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            capture_output=False,
            text=True,
        )
        if result.returncode == 0:
            print(f"  [OK] {description}")
            return True
        else:
            print(f"  [FAILED] {description}")
            return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def clean_build_artifacts():
    """Clean all build artifacts."""
    print("\nCleaning build artifacts...")

    dirs_to_clean = [
        BUILD_DIR,
        DIST_DIR,
        PROJECT_ROOT / "hcode.egg-info",
        PROJECT_ROOT / ".pyarmor",
    ]

    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  Removed: {dir_path}")

    # Clean .spec files
    for spec_file in PROJECT_ROOT.glob("*.spec"):
        spec_file.unlink()
        print(f"  Removed: {spec_file}")

    # Clean __pycache__ directories
    for cache_dir in PROJECT_ROOT.rglob("__pycache__"):
        if ".venv" not in str(cache_dir):
            shutil.rmtree(cache_dir)
            print(f"  Removed: {cache_dir}")

    print("  Clean complete!")


def check_pyarmor():
    """Check if PyArmor is installed and working."""
    try:
        # PyArmor 9.x uses direct CLI command
        result = subprocess.run(
            ["pyarmor", "--version"],
            capture_output=True,
            text=True,
            shell=True,  # Required on Windows
        )
        if result.returncode == 0:
            # Extract just the version line
            version_line = result.stdout.strip().split('\n')[0]
            print(f"PyArmor: {version_line}")
            return True
        else:
            print("ERROR: PyArmor not working properly")
            print(f"Stderr: {result.stderr}")
            return False
    except Exception as e:
        print(f"ERROR: PyArmor check failed: {e}")
        return False


def obfuscate_code():
    """Obfuscate source code using PyArmor."""
    print("\n" + "="*60)
    print("  Obfuscating source code with PyArmor")
    print("="*60)

    # Create protected directory
    PROTECTED_DIR.mkdir(parents=True, exist_ok=True)

    # PyArmor 9.x uses 'pyarmor gen' command directly
    # Note: Trial version has limitations on big scripts

    print(f"Obfuscating: {HCODE_SRC}")
    print(f"Output: {PROTECTED_DIR}")

    # Obfuscate the hcode package
    # Using basic options compatible with trial version
    obfuscate_cmd = f'pyarmor gen --output "{PROTECTED_DIR}" --recursive "{HCODE_SRC}"'

    result = subprocess.run(
        obfuscate_cmd,
        cwd=PROJECT_ROOT,
        capture_output=False,
        shell=True,
    )

    if result.returncode != 0:
        print("ERROR: PyArmor obfuscation failed")
        print("Note: Trial version may have limitations with large scripts")
        return False

    print("  [OK] Code obfuscation complete")
    return True


def build_protected_package():
    """Build Python package from obfuscated code."""
    print("\n" + "="*60)
    print("  Building Protected Python Package")
    print("="*60)

    # Create a temporary src structure with obfuscated code
    temp_src = BUILD_DIR / "pkg_src" / "src"
    temp_src.mkdir(parents=True, exist_ok=True)

    # Copy obfuscated code
    protected_hcode = PROTECTED_DIR / "hcode"
    if not protected_hcode.exists():
        print("ERROR: Obfuscated code not found. Run obfuscation first.")
        return False

    dest_hcode = temp_src / "hcode"
    if dest_hcode.exists():
        shutil.rmtree(dest_hcode)
    shutil.copytree(protected_hcode, dest_hcode)

    # Copy pyproject.toml to temp location
    temp_pyproject = BUILD_DIR / "pkg_src" / "pyproject.toml"
    shutil.copy(PROJECT_ROOT / "pyproject.toml", temp_pyproject)

    # Copy README.md if exists
    readme = PROJECT_ROOT / "README.md"
    if readme.exists():
        shutil.copy(readme, BUILD_DIR / "pkg_src" / "README.md")

    # Build the package
    build_cmd = [
        sys.executable, "-m", "build",
        "--outdir", str(DIST_DIR / "protected"),
    ]

    result = subprocess.run(
        build_cmd,
        cwd=BUILD_DIR / "pkg_src",
        capture_output=False,
    )

    if result.returncode != 0:
        print("ERROR: Package build failed")
        return False

    print("  [OK] Protected package built successfully")
    print(f"  Output: {DIST_DIR / 'protected'}")
    return True


def build_protected_exe():
    """Build executable from obfuscated code using PyInstaller."""
    print("\n" + "="*60)
    print("  Building Protected Executable")
    print("="*60)

    import platform
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Platform info
    if system == "windows":
        platform_name = f"windows-{machine}"
        exe_name = "hcode.exe"
    elif system == "darwin":
        platform_name = f"macos-{machine}"
        exe_name = "hcode"
    else:
        platform_name = f"linux-{machine}"
        exe_name = "hcode"

    # Check if obfuscated code exists
    protected_hcode = PROTECTED_DIR / "hcode"
    if not protected_hcode.exists():
        print("ERROR: Obfuscated code not found. Run obfuscation first.")
        return False

    # Create temporary directory for PyInstaller
    exe_build_dir = BUILD_DIR / "exe_build"
    exe_build_dir.mkdir(parents=True, exist_ok=True)

    # Copy obfuscated code to build directory
    exe_src = exe_build_dir / "hcode"
    if exe_src.exists():
        shutil.rmtree(exe_src)
    shutil.copytree(protected_hcode, exe_src)

    # Create entry point script
    entry_point = exe_build_dir / "hcode_main.py"
    entry_point.write_text('''#!/usr/bin/env python3
"""HCode entry point for PyInstaller."""
import sys
import os

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hcode.cli_enhanced import main

if __name__ == "__main__":
    main()
''')

    # Hidden imports for PyInstaller
    hidden_imports = [
        "tiktoken_ext.openai_public",
        "tiktoken_ext",
        "anthropic",
        "anthropic._streaming",
        "openai",
        "openai._streaming",
        "rich",
        "rich.console",
        "rich.markdown",
        "rich.syntax",
        "pydantic",
        "pydantic_settings",
        "httpx",
        "httpcore",
        "yaml",
        "dotenv",
        "click",
        "pygments",
        "prompt_toolkit",
        "tenacity",
        "aiofiles",
        "encodings",
        "encodings.utf_8",
    ]

    collect_packages = [
        "anthropic",
        "openai",
        "tiktoken",
        "rich",
        "pydantic",
        "pygments",
        "httpx",
        "pyarmor_runtime",  # PyArmor runtime
    ]

    # Build PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(entry_point),
        f"--name=hcode",
        f"--distpath={DIST_DIR / 'protected' / platform_name}",
        f"--workpath={BUILD_DIR / 'pyinstaller'}",
        "--onefile",
        "--console",
        "--clean",
        "--noconfirm",
    ]

    # Add hidden imports
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Add collect-all for packages
    for pkg in collect_packages:
        cmd.extend(["--collect-all", pkg])

    # Add the obfuscated hcode package
    separator = ";" if system == "windows" else ":"
    cmd.extend(["--add-data", f"{exe_src}{separator}hcode"])

    print(f"Building executable for: {platform_name}")

    result = subprocess.run(
        cmd,
        cwd=exe_build_dir,
        capture_output=False,
    )

    if result.returncode != 0:
        print("ERROR: Executable build failed")
        return False

    print("  [OK] Protected executable built successfully")
    print(f"  Output: {DIST_DIR / 'protected' / platform_name / exe_name}")
    return True


def verify_builds():
    """Verify that the builds work correctly."""
    print("\n" + "="*60)
    print("  Verifying Builds")
    print("="*60)

    import platform
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        platform_name = f"windows-{machine}"
        exe_name = "hcode.exe"
    elif system == "darwin":
        platform_name = f"macos-{machine}"
        exe_name = "hcode"
    else:
        platform_name = f"linux-{machine}"
        exe_name = "hcode"

    all_passed = True

    # Verify executable
    exe_path = DIST_DIR / "protected" / platform_name / exe_name
    if exe_path.exists():
        print(f"\nVerifying executable: {exe_path}")
        print(f"  Size: {exe_path.stat().st_size / (1024*1024):.2f} MB")

        try:
            result = subprocess.run(
                [str(exe_path), "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                print(f"  Version check: [OK]")
                print(f"  Output: {result.stdout.strip()}")
            else:
                print(f"  Version check: [FAILED]")
                print(f"  Error: {result.stderr}")
                all_passed = False
        except subprocess.TimeoutExpired:
            print("  Version check: [TIMEOUT]")
            all_passed = False
        except Exception as e:
            print(f"  Version check: [ERROR] {e}")
            all_passed = False

        # Test --help
        try:
            result = subprocess.run(
                [str(exe_path), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and "hcode" in result.stdout.lower():
                print(f"  Help check: [OK]")
            else:
                print(f"  Help check: [FAILED]")
                all_passed = False
        except Exception as e:
            print(f"  Help check: [ERROR] {e}")
            all_passed = False
    else:
        print(f"  Executable not found: {exe_path}")
        all_passed = False

    # Verify package
    pkg_dir = DIST_DIR / "protected"
    if pkg_dir.exists():
        wheel_files = list(pkg_dir.glob("*.whl"))
        tar_files = list(pkg_dir.glob("*.tar.gz"))

        if wheel_files:
            print(f"\nVerifying package: {wheel_files[0].name}")
            print(f"  Size: {wheel_files[0].stat().st_size / 1024:.2f} KB")
            print(f"  Package check: [OK]")
        else:
            print("  No wheel package found")

        if tar_files:
            print(f"  Source dist: {tar_files[0].name}")

    return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build protected HCode package and executable")
    parser.add_argument("--pkg", action="store_true", help="Build only Python package")
    parser.add_argument("--exe", action="store_true", help="Build only executable")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts only")
    parser.add_argument("--no-verify", action="store_true", help="Skip verification")
    parser.add_argument("--no-obfuscate", action="store_true", help="Skip obfuscation (use existing)")
    args = parser.parse_args()

    print("="*60)
    print("  HCode Protected Build")
    print("="*60)

    # Clean only
    if args.clean:
        clean_build_artifacts()
        return 0

    # If no specific target, build both
    build_pkg = args.pkg or (not args.pkg and not args.exe)
    build_exe = args.exe or (not args.pkg and not args.exe)

    # Check PyArmor
    if not check_pyarmor():
        print("\nInstall PyArmor with: pip install pyarmor pyarmor.cli.core")
        return 1

    # Clean previous builds
    clean_build_artifacts()

    # Obfuscate code
    if not args.no_obfuscate:
        if not obfuscate_code():
            print("\nObfuscation failed!")
            return 1

    # Build package
    if build_pkg:
        # Check if build module is available
        try:
            import build
        except ImportError:
            print("Installing build module...")
            subprocess.run([sys.executable, "-m", "pip", "install", "build"], capture_output=True)

        if not build_protected_package():
            print("\nPackage build failed!")
            return 1

    # Build executable
    if build_exe:
        # Check if PyInstaller is available
        try:
            import PyInstaller
        except ImportError:
            print("Installing PyInstaller...")
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], capture_output=True)

        if not build_protected_exe():
            print("\nExecutable build failed!")
            return 1

    # Verify
    if not args.no_verify:
        if not verify_builds():
            print("\nVerification failed!")
            return 1

    print("\n" + "="*60)
    print("  BUILD SUCCESSFUL!")
    print("="*60)
    print(f"\nOutput directory: {DIST_DIR / 'protected'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
