#!/usr/bin/env python3
"""
HCode PyInstaller Build Script.

Builds standalone executables for Windows, macOS, and Linux.

Usage:
    python scripts/build_exe.py           # Build for current platform
    python scripts/build_exe.py --debug   # Build with debug symbols
    python scripts/build_exe.py --onedir  # Build as directory instead of single file
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
ENTRY_POINT = SRC_DIR / "hcode" / "__main__.py"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"


def get_platform_info() -> dict:
    """Get platform-specific build information."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    info = {
        "system": system,
        "machine": machine,
        "exe_extension": ".exe" if system == "windows" else "",
        "icon_extension": (
            ".ico" if system == "windows" else ".icns" if system == "darwin" else ".png"
        ),
    }

    # Determine output name
    if system == "windows":
        info["platform_name"] = f"windows-{machine}"
    elif system == "darwin":
        info["platform_name"] = f"macos-{machine}"
    else:
        info["platform_name"] = f"linux-{machine}"

    return info


def check_pyinstaller() -> bool:
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller

        print(f"PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("ERROR: PyInstaller not installed.")
        print("Install with: pip install pyinstaller")
        return False


def clean_build_artifacts() -> None:
    """Clean previous build artifacts."""
    print("Cleaning previous build artifacts...")

    dirs_to_clean = [BUILD_DIR, DIST_DIR]
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  Removed: {dir_path}")

    # Clean .spec files
    for spec_file in PROJECT_ROOT.glob("*.spec"):
        spec_file.unlink()
        print(f"  Removed: {spec_file}")


def get_hidden_imports() -> list[str]:
    """Get list of hidden imports needed for the build."""
    return [
        # Tiktoken extensions
        "tiktoken_ext.openai_public",
        "tiktoken_ext",
        # Anthropic
        "anthropic",
        "anthropic._streaming",
        "anthropic._client",
        # OpenAI
        "openai",
        "openai._streaming",
        # Rich
        "rich",
        "rich.console",
        "rich.markdown",
        "rich.syntax",
        "rich.panel",
        "rich.table",
        "rich.progress",
        # Pydantic
        "pydantic",
        "pydantic_settings",
        "pydantic.fields",
        # HTTPX
        "httpx",
        "httpx._transports",
        "httpcore",
        # Other dependencies
        "yaml",
        "dotenv",
        "click",
        "pygments",
        "prompt_toolkit",
        "tenacity",
        "aiofiles",
        # Encodings
        "encodings",
        "encodings.utf_8",
        "encodings.ascii",
    ]


def get_collect_packages() -> list[str]:
    """Get packages to fully collect."""
    return [
        "anthropic",
        "openai",
        "tiktoken",
        "tiktoken_ext",
        "rich",
        "pydantic",
        "pydantic_settings",
        "pygments",
        "httpx",
        "httpcore",
    ]


def build_executable(
    debug: bool = False,
    onedir: bool = False,
    console: bool = True,
) -> bool:
    """
    Build the executable using PyInstaller.

    Args:
        debug: Include debug symbols
        onedir: Build as directory instead of single file
        console: Show console window (Windows)

    Returns:
        True if build succeeded
    """
    platform_info = get_platform_info()

    print(f"\nBuilding HCode for {platform_info['platform_name']}...")
    print(f"  Entry point: {ENTRY_POINT}")
    print(f"  Output: dist/{platform_info['platform_name']}/")

    # Build PyInstaller command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(ENTRY_POINT),
        f"--name=hcode",
        f"--distpath={DIST_DIR / platform_info['platform_name']}",
        f"--workpath={BUILD_DIR}",
        "--clean",
        "--noconfirm",
    ]

    # One file or one directory
    if onedir:
        cmd.append("--onedir")
    else:
        cmd.append("--onefile")

    # Console or windowed
    if console:
        cmd.append("--console")
    else:
        cmd.append("--windowed")

    # Debug symbols
    if debug:
        cmd.append("--debug=all")

    # Hidden imports
    for hidden_import in get_hidden_imports():
        cmd.extend(["--hidden-import", hidden_import])

    # Collect packages
    for package in get_collect_packages():
        cmd.extend(["--collect-all", package])

    # Add data files
    data_files = [
        (str(SRC_DIR / "hcode" / "config"), "hcode/config"),
    ]
    for src, dest in data_files:
        if Path(src).exists():
            separator = ";" if platform_info["system"] == "windows" else ":"
            cmd.extend(["--add-data", f"{src}{separator}{dest}"])

    # Platform-specific options
    if platform_info["system"] == "windows":
        icon_path = PROJECT_ROOT / "assets" / "icon.ico"
        if icon_path.exists():
            cmd.extend(["--icon", str(icon_path)])
    elif platform_info["system"] == "darwin":
        icon_path = PROJECT_ROOT / "assets" / "icon.icns"
        if icon_path.exists():
            cmd.extend(["--icon", str(icon_path)])

    # Run PyInstaller
    print("\nRunning PyInstaller...")
    print(f"Command: {' '.join(cmd[:10])}...")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"ERROR: PyInstaller failed with code {e.returncode}")
        return False


def verify_build(platform_info: dict) -> bool:
    """Verify the built executable."""
    exe_name = f"hcode{platform_info['exe_extension']}"
    exe_path = DIST_DIR / platform_info["platform_name"] / exe_name

    if not exe_path.exists():
        print(f"ERROR: Executable not found: {exe_path}")
        return False

    print(f"\nVerifying build: {exe_path}")
    print(f"  Size: {exe_path.stat().st_size / (1024*1024):.2f} MB")

    # Try running --version
    try:
        result = subprocess.run(
            [str(exe_path), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print(f"  Version check: OK")
            print(f"  Output: {result.stdout.strip()}")
            return True
        else:
            print(f"  Version check: FAILED")
            print(f"  Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("  Version check: TIMEOUT")
        return False
    except Exception as e:
        print(f"  Version check: ERROR - {e}")
        return False


def create_release_archive(platform_info: dict) -> Path | None:
    """Create a release archive."""
    import zipfile
    import tarfile

    exe_name = f"hcode{platform_info['exe_extension']}"
    exe_path = DIST_DIR / platform_info["platform_name"] / exe_name

    if not exe_path.exists():
        return None

    # Archive name
    version = "1.0.0"  # TODO: Get from package
    archive_name = f"hcode-{version}-{platform_info['platform_name']}"

    if platform_info["system"] == "windows":
        # Create ZIP for Windows
        archive_path = DIST_DIR / f"{archive_name}.zip"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(exe_path, exe_name)
            # Add README if exists
            readme = PROJECT_ROOT / "README.md"
            if readme.exists():
                zf.write(readme, "README.md")
    else:
        # Create tar.gz for Unix
        archive_path = DIST_DIR / f"{archive_name}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tf:
            tf.add(exe_path, exe_name)
            readme = PROJECT_ROOT / "README.md"
            if readme.exists():
                tf.add(readme, "README.md")

    print(f"\nCreated release archive: {archive_path}")
    print(f"  Size: {archive_path.stat().st_size / (1024*1024):.2f} MB")

    return archive_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build HCode executable")
    parser.add_argument("--debug", action="store_true", help="Include debug symbols")
    parser.add_argument("--onedir", action="store_true", help="Build as directory")
    parser.add_argument("--no-clean", action="store_true", help="Skip cleaning")
    parser.add_argument("--no-verify", action="store_true", help="Skip verification")
    parser.add_argument("--no-archive", action="store_true", help="Skip archive creation")
    args = parser.parse_args()

    print("=" * 60)
    print("HCode Build Script")
    print("=" * 60)

    # Check requirements
    if not check_pyinstaller():
        return 1

    if not ENTRY_POINT.exists():
        print(f"ERROR: Entry point not found: {ENTRY_POINT}")
        return 1

    platform_info = get_platform_info()
    print(f"\nPlatform: {platform_info['platform_name']}")

    # Clean
    if not args.no_clean:
        clean_build_artifacts()

    # Build
    if not build_executable(debug=args.debug, onedir=args.onedir):
        print("\nBuild FAILED!")
        return 1

    print("\nBuild completed successfully!")

    # Verify
    if not args.no_verify:
        if not verify_build(platform_info):
            print("\nVerification FAILED!")
            return 1

    # Archive
    if not args.no_archive:
        create_release_archive(platform_info)

    print("\n" + "=" * 60)
    print("BUILD SUCCESSFUL!")
    print("=" * 60)
    print(
        f"\nExecutable: dist/{platform_info['platform_name']}/hcode{platform_info['exe_extension']}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
