"""
Code Verification Module

Provides utilities to verify that code changes were applied correctly and don't introduce errors.
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class VerificationResult:
    """Result of a code verification check."""

    def __init__(self, file_path: str, passed: bool, errors: Optional[List[str]] = None):
        self.file_path = file_path
        self.passed = passed
        self.errors = errors or []

    def __bool__(self) -> bool:
        return self.passed

    def __str__(self) -> str:
        if self.passed:
            return f"✓ {self.file_path}: Verification passed"
        else:
            errors_str = "\n  - ".join(self.errors)
            return f"✗ {self.file_path}: Verification failed\n  - {errors_str}"


class CodeVerifier:
    """
    Verifies that code changes were applied correctly.

    Performs checks like:
    - File exists and is not empty
    - Python files have valid syntax
    - No obvious errors introduced
    """

    @staticmethod
    def verify_file(file_path: str) -> VerificationResult:
        """
        Verify a single file after modifications.

        Args:
            file_path: Path to the file to verify

        Returns:
            VerificationResult with check status

        Example:
            >>> result = CodeVerifier.verify_file("src/main.py")
            >>> if result:
            ...     print("File verified successfully")
            ... else:
            ...     print(f"Verification failed: {result.errors}")
        """
        errors = []
        path = Path(file_path)

        # Check 1: File exists
        if not path.exists():
            errors.append(f"File does not exist: {file_path}")
            return VerificationResult(file_path, False, errors)

        # Check 2: File is not empty
        try:
            content = path.read_text(encoding='utf-8')
            if not content.strip():
                errors.append("File is empty after edit")
        except UnicodeDecodeError:
            # Try with alternative encodings
            try:
                content = path.read_text(encoding='latin-1')
            except Exception as e:
                errors.append(f"Cannot read file: {e}")
                return VerificationResult(file_path, False, errors)
        except Exception as e:
            errors.append(f"Cannot read file: {e}")
            return VerificationResult(file_path, False, errors)

        # Check 3: Python files must have valid syntax
        if file_path.endswith('.py'):
            try:
                ast.parse(content)
            except SyntaxError as e:
                errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
            except Exception as e:
                errors.append(f"Python parsing error: {e}")

        # Check 4: Basic sanity checks
        if file_path.endswith('.py'):
            # Check for common issues
            if content.count('(') != content.count(')'):
                errors.append("Mismatched parentheses")
            if content.count('[') != content.count(']'):
                errors.append("Mismatched brackets")
            if content.count('{') != content.count('}'):
                errors.append("Mismatched braces")

        # Return result
        passed = len(errors) == 0
        return VerificationResult(file_path, passed, errors)

    @staticmethod
    def verify_files(file_paths: List[str]) -> Dict[str, VerificationResult]:
        """
        Verify multiple files after modifications.

        Args:
            file_paths: List of file paths to verify

        Returns:
            Dict mapping file path to verification result

        Example:
            >>> files = ["src/main.py", "src/utils.py"]
            >>> results = CodeVerifier.verify_files(files)
            >>> all_passed = all(result.passed for result in results.values())
            >>> if all_passed:
            ...     print("All files verified successfully")
        """
        results = {}

        for file_path in file_paths:
            results[file_path] = CodeVerifier.verify_file(file_path)

        return results

    @staticmethod
    def print_verification_summary(results: Dict[str, VerificationResult]) -> bool:
        """
        Print a summary of verification results.

        Args:
            results: Dict of verification results from verify_files()

        Returns:
            True if all checks passed, False otherwise
        """
        all_passed = True

        for file_path, result in results.items():
            if result.passed:
                logger.info(f"✓ {file_path}: Verified")
            else:
                all_passed = False
                logger.error(f"✗ {file_path}: Failed verification")
                for error in result.errors:
                    logger.error(f"  - {error}")

        return all_passed


def verify_code_changes(modified_files: List[str], console=None) -> bool:
    """
    Convenience function to verify code changes and print results.

    Args:
        modified_files: List of file paths that were modified
        console: Optional Rich console for formatted output

    Returns:
        True if all files pass verification, False otherwise

    Example:
        >>> modified = ["src/main.py", "src/utils.py"]
        >>> if verify_code_changes(modified):
        ...     print("All changes verified successfully")
        ... else:
        ...     print("Some changes failed verification")
    """
    verifier = CodeVerifier()
    results = verifier.verify_files(modified_files)

    all_passed = True

    for file_path, result in results.items():
        if result.passed:
            if console:
                console.print(f"[green]✓[/green] {file_path}: Verified")
            else:
                print(f"✓ {file_path}: Verified")
        else:
            all_passed = False
            if console:
                console.print(f"[red]✗[/red] {file_path}: Failed verification")
                for error in result.errors:
                    console.print(f"  [red]- {error}[/red]")
            else:
                print(f"✗ {file_path}: Failed verification")
                for error in result.errors:
                    print(f"  - {error}")

    return all_passed
