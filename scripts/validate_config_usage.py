#!/usr/bin/env python3
"""
Configuration Usage Validator

This script scans the codebase for hardcoded prompts and parameters
that should be loaded from configuration files instead.

Usage:
    python scripts/validate_config_usage.py
    python scripts/validate_config_usage.py --fix  # Auto-fix simple issues
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class Violation:
    """Represents a configuration violation"""

    file: Path
    line_number: int
    line_content: str
    violation_type: str
    severity: str  # 'error', 'warning', 'info'
    message: str
    suggestion: str = ""


class ConfigValidator:
    """Validates that configuration is properly used"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.violations: List[Violation] = []

        # Patterns that indicate hardcoded prompts
        self.prompt_patterns = [
            (
                r'SYSTEM_PROMPT\s*=\s*"""You are',
                "Hardcoded system prompt (use get_system_prompt() instead)",
            ),
            (
                r'PROMPT\s*=\s*"""You are',
                "Hardcoded prompt (use get_system_prompt() instead)",
            ),
            (
                r'return\s*"""You are.*?"""',
                "Hardcoded prompt in return statement",
            ),
            (
                r'return\s*f?"""You (have|must|should|are)',
                "Hardcoded prompt in return statement",
            ),
        ]

        # Patterns for hardcoded parameters
        self.parameter_patterns = [
            (
                r'temperature\s*=\s*([0-9.]+)',
                "Hardcoded temperature parameter",
            ),
            (
                r'max_tokens\s*=\s*([0-9]+)',
                "Hardcoded max_tokens parameter",
            ),
            (
                r'top_p\s*=\s*([0-9.]+)',
                "Hardcoded top_p parameter",
            ),
            (
                r'top_k\s*=\s*([0-9]+)',
                "Hardcoded top_k parameter",
            ),
        ]

        # Files to exclude from checking
        self.exclude_files = [
            "config/prompts.py",
            "config/defaults.py",
            "config/reasoning_prompts.py",
            "test_",  # Test files
            "validate_config_usage.py",  # This script
        ]

        # Files in config/ directory are allowed to have prompts
        self.allow_prompts_in_config = True

    def should_check_file(self, file_path: Path) -> bool:
        """Check if file should be validated"""
        # Only check Python files
        if file_path.suffix != ".py":
            return False

        # Check exclude list
        file_str = str(file_path.relative_to(self.root_dir))
        for exclude in self.exclude_files:
            if exclude in file_str:
                return False

        # Allow prompts in config directory
        if self.allow_prompts_in_config and "config" in file_path.parts:
            return False

        return True

    def validate_file(self, file_path: Path) -> List[Violation]:
        """Validate a single file"""
        violations = []

        try:
            # Try UTF-8 first, fallback to other encodings
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    content = file_path.read_text(encoding="latin-1")
                except UnicodeDecodeError:
                    content = file_path.read_text(encoding="cp1252", errors="ignore")

            lines = content.split("\n")

            for line_num, line in enumerate(lines, start=1):
                # Skip comments and docstrings
                stripped = line.strip()
                if stripped.startswith("#") or '"""' in line or "'''" in line:
                    continue

                # Check for hardcoded prompts
                for pattern, message in self.prompt_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append(
                            Violation(
                                file=file_path,
                                line_number=line_num,
                                line_content=line.strip(),
                                violation_type="hardcoded_prompt",
                                severity="error",
                                message=message,
                                suggestion="Import and use get_system_prompt() or get_prompts_config()",
                            )
                        )

                # Check for hardcoded parameters
                for pattern, message in self.parameter_patterns:
                    match = re.search(pattern, line)
                    if match:
                        # Allow some cases
                        # 1. Inside get_generation_params() or ModelsConfig
                        # 2. Test values (max_tokens=5 for testing)
                        if "get_generation_params" in line or "ModelsConfig" in line:
                            continue
                        if "test" in file_path.name.lower():
                            continue

                        # Check if it's a small test value
                        try:
                            value = float(match.group(1))
                            if "max_tokens" in line and value <= 10:
                                continue  # Likely a test
                        except (ValueError, IndexError):
                            pass

                        violations.append(
                            Violation(
                                file=file_path,
                                line_number=line_num,
                                line_content=line.strip(),
                                violation_type="hardcoded_parameter",
                                severity="warning",
                                message=f"{message}: {match.group(0)}",
                                suggestion="Use get_generation_params(task_type='...') from config",
                            )
                        )

        except Exception as e:
            violations.append(
                Violation(
                    file=file_path,
                    line_number=0,
                    line_content="",
                    violation_type="read_error",
                    severity="error",
                    message=f"Error reading file: {e}",
                )
            )

        return violations

    def validate_all(self) -> List[Violation]:
        """Validate all Python files in the project"""
        src_dir = self.root_dir / "src" / "hcode"

        all_violations = []
        for py_file in src_dir.rglob("*.py"):
            if self.should_check_file(py_file):
                violations = self.validate_file(py_file)
                all_violations.extend(violations)

        return all_violations

    def format_report(self, violations: List[Violation]) -> str:
        """Format violations into a readable report"""
        if not violations:
            return "[OK] No configuration violations found!\n"

        report = []
        report.append("=" * 80)
        report.append("CONFIGURATION USAGE VIOLATIONS")
        report.append("=" * 80)
        report.append("")

        # Group by file
        by_file: Dict[Path, List[Violation]] = {}
        for v in violations:
            if v.file not in by_file:
                by_file[v.file] = []
            by_file[v.file].append(v)

        # Count by severity
        errors = sum(1 for v in violations if v.severity == "error")
        warnings = sum(1 for v in violations if v.severity == "warning")

        for file_path, file_violations in sorted(by_file.items()):
            report.append(f"\nFile: {file_path.relative_to(self.root_dir)}")
            report.append("-" * 80)

            for v in file_violations:
                severity_icon = {
                    "error": "[ERROR]",
                    "warning": "[WARN]",
                    "info": "[INFO]",
                }[v.severity]

                report.append(f"  {severity_icon} Line {v.line_number}: {v.message}")
                if v.line_content:
                    report.append(f"          Code: {v.line_content[:100]}")
                if v.suggestion:
                    report.append(f"          Suggestion: {v.suggestion}")
                report.append("")

        report.append("=" * 80)
        report.append(f"SUMMARY: {errors} errors, {warnings} warnings")
        report.append("=" * 80)

        return "\n".join(report)

    def check_imports(self) -> List[Violation]:
        """Check that files import from config when needed"""
        violations = []
        src_dir = self.root_dir / "src" / "hcode"

        files_needing_config_import = [
            "agent/coding_agent.py",
            "agent/autonomous_agent.py",
            "hcode_chat.py",
            "core/agent.py",
        ]

        for file_rel_path in files_needing_config_import:
            file_path = src_dir / file_rel_path
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                try:
                    content = file_path.read_text(encoding="latin-1")
                except UnicodeDecodeError:
                    content = file_path.read_text(encoding="cp1252", errors="ignore")

            # Check for config imports
            has_prompts_import = (
                "from hcode.config.prompts import" in content
                or "from ..config.prompts import" in content
                or "import hcode.config.prompts" in content
            )

            if not has_prompts_import:
                violations.append(
                    Violation(
                        file=file_path,
                        line_number=0,
                        line_content="",
                        violation_type="missing_import",
                        severity="warning",
                        message="File should import from hcode.config.prompts",
                        suggestion="Add: from hcode.config.prompts import get_system_prompt",
                    )
                )

        return violations


def main():
    """Main entry point"""
    root_dir = Path(__file__).parent.parent

    print("Validating configuration usage...\n")

    validator = ConfigValidator(root_dir)

    # Run validation
    violations = validator.validate_all()
    import_violations = validator.check_imports()
    all_violations = violations + import_violations

    # Print report
    report = validator.format_report(all_violations)
    print(report)

    # Exit with error if there are errors
    errors = [v for v in all_violations if v.severity == "error"]
    if errors:
        sys.exit(1)
    else:
        print("\n[OK] Validation passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
