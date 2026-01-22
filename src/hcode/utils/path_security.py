"""
Path Security Utilities for HCode.

Provides path validation and sanitization to prevent directory traversal attacks
and ensure file operations stay within the project root.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List


@dataclass
class PathValidationResult:
    """Result of path validation."""
    is_valid: bool
    error: Optional[str] = None
    canonical_path: Optional[Path] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


# Patterns that indicate potential directory traversal attempts
TRAVERSAL_PATTERNS = [
    r'\.\.',  # Parent directory reference
    r'\.\./',  # Unix parent traversal
    r'\.\.\\',  # Windows parent traversal
    r'/\.\./',  # Embedded traversal
    r'\\\.\.\\',  # Embedded Windows traversal
]

# Dangerous file paths that should always be blocked
DANGEROUS_PATHS = [
    '/etc/passwd',
    '/etc/shadow',
    '/etc/hosts',
    '/etc/sudoers',
    '/root/',
    '/var/log/',
    '/proc/',
    '/sys/',
    '/dev/',
    'C:\\Windows\\System32',
    'C:\\Windows\\system.ini',
    'C:\\boot.ini',
]


def detect_traversal_attempt(path: str) -> bool:
    """
    Detect if a path contains directory traversal patterns.
    
    Args:
        path: The path string to check
        
    Returns:
        True if traversal attempt detected
    """
    for pattern in TRAVERSAL_PATTERNS:
        if re.search(pattern, path):
            return True
    return False


def is_dangerous_path(path: str) -> bool:
    """
    Check if a path points to a known dangerous location.
    
    Args:
        path: The path string to check
        
    Returns:
        True if path is dangerous
    """
    normalized = path.replace('\\', '/').lower()
    for dangerous in DANGEROUS_PATHS:
        if normalized.startswith(dangerous.lower()) or normalized == dangerous.lower():
            return True
    return False


def canonicalize_path(path: str, root_dir: Path) -> Path:
    """
    Resolve a path to its canonical (absolute, normalized) form.
    
    This function:
    1. Resolves relative paths against root_dir
    2. Normalizes path separators
    3. Resolves symlinks
    4. Removes any . or .. components
    
    Args:
        path: The path to canonicalize
        root_dir: The root directory for relative path resolution
        
    Returns:
        Canonical Path object
    """
    input_path = Path(path)

    # If path is relative, resolve against root_dir
    if not input_path.is_absolute():
        input_path = root_dir / input_path

    # Resolve to canonical form (handles .., symlinks, etc.)
    try:
        canonical = input_path.resolve()
    except (OSError, ValueError):
        # If resolve fails, fall back to absolute()
        canonical = input_path.absolute()

    return canonical


def is_within_root(path: Path, root_dir: Path) -> bool:
    """
    Check if a path is within the allowed root directory.
    
    Args:
        path: The canonical path to check
        root_dir: The root directory that constrains operations
        
    Returns:
        True if path is within root_dir
    """
    try:
        # Resolve both to canonical form for comparison
        canonical_path = path.resolve()
        canonical_root = root_dir.resolve()

        # Check if path starts with root
        # Using str comparison because Path.is_relative_to() was added in Python 3.9
        return str(canonical_path).startswith(str(canonical_root))
    except (OSError, ValueError):
        return False


def validate_path(
        path: str,
        root_dir: Path,
        allow_absolute: bool = True,
        allow_creation: bool = True
) -> PathValidationResult:
    """
    Comprehensive path validation for security.
    
    This function performs multiple security checks:
    1. Detects directory traversal attempts (../)
    2. Checks for dangerous system paths
    3. Ensures path is within allowed root directory
    4. Validates path characters and format
    
    Args:
        path: The path to validate
        root_dir: The root directory that constrains operations
        allow_absolute: Whether absolute paths are allowed
        allow_creation: Whether the path can be for a non-existent file
        
    Returns:
        PathValidationResult with validation status and details
    """
    warnings = []

    # Empty path check
    if not path or not path.strip():
        return PathValidationResult(
            is_valid=False,
            error="Path cannot be empty"
        )

    # Detect explicit traversal attempts in the input
    if detect_traversal_attempt(path):
        return PathValidationResult(
            is_valid=False,
            error=f"Path contains directory traversal attempt: {path}"
        )

    # Check for dangerous system paths
    if is_dangerous_path(path):
        return PathValidationResult(
            is_valid=False,
            error=f"Access to system path is not allowed: {path}"
        )

    # Check absolute path policy
    input_path = Path(path)
    if input_path.is_absolute() and not allow_absolute:
        return PathValidationResult(
            is_valid=False,
            error="Absolute paths are not allowed"
        )

    # Canonicalize the path
    try:
        canonical = canonicalize_path(path, root_dir)
    except Exception as e:
        return PathValidationResult(
            is_valid=False,
            error=f"Failed to resolve path: {e}"
        )

    # Check if path is within root directory
    if not is_within_root(canonical, root_dir):
        return PathValidationResult(
            is_valid=False,
            error=f"Path escapes project root. Path must be within: {root_dir}"
        )

    # For existing file validation
    if not allow_creation and not canonical.exists():
        return PathValidationResult(
            is_valid=False,
            error=f"File does not exist: {canonical}"
        )

    # Check for suspicious path components even if they resolve within root
    path_str = str(canonical)
    if '..' in path_str:
        warnings.append("Path contains '..' after resolution - verify intent")

    return PathValidationResult(
        is_valid=True,
        canonical_path=canonical,
        warnings=warnings
    )


def safe_join(root_dir: Path, *path_parts: str) -> Optional[Path]:
    """
    Safely join path parts, ensuring result stays within root.
    
    This is a convenience function for building paths that
    are guaranteed to be within the root directory.
    
    Args:
        root_dir: The root directory
        *path_parts: Path components to join
        
    Returns:
        Safe Path or None if resulting path would escape root
    """
    try:
        # Build path
        result = root_dir
        for part in path_parts:
            # Skip any part that is an absolute path
            if Path(part).is_absolute():
                return None
            # Skip any part with traversal
            if '..' in part:
                return None
            result = result / part

        # Canonicalize and validate
        canonical = result.resolve()
        if is_within_root(canonical, root_dir):
            return canonical
        return None
    except Exception:
        return None


def validate_file_path_for_tool(
        path: str,
        root_dir: Path,
        operation: str = "read"
) -> PathValidationResult:
    """
    Validate a file path for use in tool operations.
    
    Convenience wrapper with sensible defaults for tool operations.
    
    Args:
        path: The path to validate
        root_dir: The root directory
        operation: Type of operation ("read", "write", "edit")
        
    Returns:
        PathValidationResult
    """
    allow_creation = operation in ("write", "edit", "create")

    result = validate_path(
        path=path,
        root_dir=root_dir,
        allow_absolute=True,
        allow_creation=allow_creation
    )

    # Add operation-specific checks
    if result.is_valid and result.canonical_path:
        # For read operations, file must exist
        if operation == "read" and not result.canonical_path.exists():
            return PathValidationResult(
                is_valid=False,
                error=f"File not found: {result.canonical_path}"
            )

        # For write/edit, parent directory must exist or be creatable
        if operation in ("write", "edit", "create"):
            parent = result.canonical_path.parent
            if not parent.exists():
                # Check if we can create the parent directory
                if not is_within_root(parent, root_dir):
                    return PathValidationResult(
                        is_valid=False,
                        error=f"Cannot create directory outside project root: {parent}"
                    )

    return result
