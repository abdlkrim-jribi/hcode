"""
Agent operation modes matching Claude Code behavior.

Defines modes, safety configuration, and confirmation levels.
"""

import re
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Set, Dict, Any, Optional


class AgentMode(Enum):
    """
    Agent operation modes.

    Matches Claude Code's exact behavior:
    - INTERACTIVE: Ask before each action (default, safest)
    - AUTO: Execute without asking (dangerous commands still prompt)
    - PLAN: Show plan first, then auto-execute
    - REVIEW: Show plan, require approval, then auto-execute
    """

    INTERACTIVE = "interactive"  # Ask before each action
    AUTO = "auto"  # Execute without asking (except dangerous)
    PLAN = "plan"  # Create plan first, then auto
    REVIEW = "review"  # Show plan, get approval, then auto


class ConfirmationLevel(Enum):
    """How much confirmation to require"""

    NONE = "none"  # Never ask
    DANGEROUS_ONLY = "dangerous_only"  # Ask only for dangerous ops
    ALL = "all"  # Ask for everything
    FIRST_ONLY = "first_only"  # Ask once per task


class RiskLevel(Enum):
    """Risk levels for actions"""

    SAFE = "safe"  # No risk, execute freely
    CAUTION = "caution"  # Some risk, may need attention
    DANGEROUS = "dangerous"  # High risk, requires confirmation


@dataclass
class ModeConfig:
    """Configuration for each mode"""

    # Whether to ask permission before actions
    ask_permission: bool = True

    # Whether to show plan before starting
    show_plan: bool = False

    # Whether to confirm dangerous operations
    confirm_dangerous: bool = True

    # Whether to execute automatically after plan
    execute_after_plan: bool = False

    # Whether approval is required to start
    require_approval: bool = False

    # Maximum actions without confirmation
    max_actions_without_confirm: int = 10

    # Description of the mode
    description: str = ""


# Predefined mode configurations matching Claude Code
MODE_CONFIGS: Dict[AgentMode, ModeConfig] = {
    # Interactive: Ask before each action
    AgentMode.INTERACTIVE: ModeConfig(
        ask_permission=True,
        show_plan=False,
        confirm_dangerous=True,
        execute_after_plan=False,
        require_approval=False,
        max_actions_without_confirm=1,
        description="Asks permission for each action (safest)",
    ),
    # Auto: Execute freely, only confirm dangerous
    AgentMode.AUTO: ModeConfig(
        ask_permission=False,
        show_plan=False,
        confirm_dangerous=True,  # Still ask for dangerous!
        execute_after_plan=True,
        require_approval=False,
        max_actions_without_confirm=999,
        description="Executes automatically (asks for dangerous operations)",
    ),
    # Plan: Show plan, then execute automatically
    AgentMode.PLAN: ModeConfig(
        ask_permission=False,
        show_plan=True,
        confirm_dangerous=True,
        execute_after_plan=True,
        require_approval=False,
        max_actions_without_confirm=999,
        description="Shows plan first, then executes automatically",
    ),
    # Review: Show plan, get approval, then execute
    AgentMode.REVIEW: ModeConfig(
        ask_permission=False,
        show_plan=True,
        confirm_dangerous=True,
        execute_after_plan=True,
        require_approval=True,
        max_actions_without_confirm=999,
        description="Shows plan and requires approval before execution",
    ),
}


@dataclass
class SafetyConfig:
    """
    Safety configuration for autonomous operation.

    Defines what operations are considered dangerous and require
    explicit confirmation even in auto mode.
    """

    # Commands that always require confirmation
    dangerous_commands: Set[str] = field(
        default_factory=lambda: {
            # Destructive file operations
            "rm",
            "rm -rf",
            "del",
            "rmdir",
            "rd",
            # System operations
            "shutdown",
            "reboot",
            "halt",
            "poweroff",
            "sudo",
            "su",
            "format",
            # Package management (uninstall)
            "apt-get remove",
            "apt remove",
            "apt-get purge",
            "npm uninstall -g",
            "pip uninstall",
            "cargo uninstall",
            # Git operations
            "git push --force",
            "git push -f",
            "git reset --hard",
            "git clean -fd",
            "git clean -f",
            "git checkout --force",
            # Database operations
            "drop database",
            "drop table",
            "truncate",
            "delete from",
            # Docker operations
            "docker rm",
            "docker rmi",
            "docker system prune",
            "docker volume rm",
            # Windows-specific
            "del /f",
            "rmdir /s",
        }
    )

    # Command patterns that require confirmation (regex)
    dangerous_patterns: List[str] = field(
        default_factory=lambda: [
            r"rm\s+-rf\s+[/\\]",  # Delete from root
            r"rm\s+.*\*",  # Wildcard delete
            r"del\s+.*\*",  # Windows wildcard delete
            r"DROP\s+(DATABASE|TABLE)",  # SQL drops
            r"TRUNCATE\s+TABLE",  # SQL truncate
            r"DELETE\s+FROM\s+\w+\s*;",  # DELETE without WHERE
            r"git\s+push.*--force",  # Force push
            r"git\s+push.*-f\b",  # Force push short
            r"chmod\s+777",  # Overly permissive
            r">\s*/dev/sd[a-z]",  # Write to disk
            r"mkfs\.",  # Format filesystem
            r":>{1,2}\s*/",  # Redirect to system paths
        ]
    )

    # Files that should never be modified without confirmation
    protected_files: Set[str] = field(
        default_factory=lambda: {
            ".env",
            ".env.local",
            ".env.production",
            ".env.development",
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "requirements.txt",
            "Pipfile",
            "Pipfile.lock",
            "poetry.lock",
            "pyproject.toml",
            "Cargo.toml",
            "Cargo.lock",
            "go.mod",
            "go.sum",
            ".gitignore",
            ".dockerignore",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "Makefile",
            "makefile",
            "CMakeLists.txt",
            ".github",
            ".gitlab-ci.yml",
            "Jenkinsfile",
        }
    )

    # Directories that should never be deleted
    protected_directories: Set[str] = field(
        default_factory=lambda: {
            ".git",
            ".svn",
            ".hg",
            "node_modules",
            ".venv",
            "venv",
            "env",
            "__pycache__",
            ".idea",
            ".vscode",
            "dist",
            "build",
            "target",
            ".next",
            ".nuxt",
            "vendor",
        }
    )

    # Operations that require backup first
    backup_before: Set[str] = field(
        default_factory=lambda: {
            "database_migration",
            "schema_change",
            "config_update",
            "major_refactor",
        }
    )

    # Maximum file size to modify without confirmation (bytes)
    max_file_size_auto: int = 50_000  # 50KB

    # Maximum number of files to modify without confirmation
    max_files_auto: int = 10

    # Require confirmation for operations affecting these paths
    sensitive_paths: Set[str] = field(
        default_factory=lambda: {
            "/etc",
            "/usr",
            "/bin",
            "/sbin",
            "/var",
            "/home",
            "~/.ssh",
            "~/.config",
            "C:\\Windows",
            "C:\\Program Files",
        }
    )

    def is_dangerous_command(self, command: str) -> bool:
        """Check if command is dangerous"""
        command_lower = command.lower().strip()

        # Check exact matches
        for dangerous in self.dangerous_commands:
            if dangerous.lower() in command_lower:
                return True

        # Check patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True

        return False

    def is_protected_file(self, filepath: str) -> bool:
        """Check if file is protected"""
        filename = os.path.basename(filepath)
        return filename.lower() in {f.lower() for f in self.protected_files}

    def is_protected_directory(self, dirpath: str) -> bool:
        """Check if directory is protected"""
        dirname = os.path.basename(dirpath.rstrip("/\\"))
        return dirname.lower() in {d.lower() for d in self.protected_directories}

    def is_sensitive_path(self, filepath: str) -> bool:
        """Check if path is in sensitive location"""
        filepath_normalized = filepath.replace("\\", "/").lower()

        for sensitive in self.sensitive_paths:
            sensitive_normalized = sensitive.replace("\\", "/").lower()
            if filepath_normalized.startswith(sensitive_normalized):
                return True

        return False

    def requires_backup(self, operation: str) -> bool:
        """Check if operation requires backup"""
        return operation.lower() in self.backup_before

    def assess_file_risk(self, filepath: str, operation: str = "edit") -> RiskLevel:
        """
        Assess risk level for file operation.

        Args:
            filepath: Path to the file
            operation: Type of operation (read, edit, write, delete)

        Returns:
            RiskLevel
        """
        # Delete is always dangerous for protected files/dirs
        if operation == "delete":
            if self.is_protected_file(filepath) or self.is_protected_directory(filepath):
                return RiskLevel.DANGEROUS
            return RiskLevel.CAUTION

        # Check if protected
        if self.is_protected_file(filepath):
            return RiskLevel.CAUTION

        # Check if sensitive path
        if self.is_sensitive_path(filepath):
            return RiskLevel.CAUTION

        # Check file size if exists
        if os.path.exists(filepath):
            try:
                size = os.path.getsize(filepath)
                if size > self.max_file_size_auto:
                    return RiskLevel.CAUTION
            except OSError:
                pass

        # Read is always safe
        if operation == "read":
            return RiskLevel.SAFE

        return RiskLevel.SAFE

    def assess_command_risk(self, command: str) -> RiskLevel:
        """
        Assess risk level for bash command.

        Args:
            command: The command to assess

        Returns:
            RiskLevel
        """
        if self.is_dangerous_command(command):
            return RiskLevel.DANGEROUS

        # Check for sudo or elevated privileges
        command_lower = command.lower()
        if "sudo" in command_lower or "runas" in command_lower:
            return RiskLevel.DANGEROUS

        # Check for package installation (caution, not dangerous)
        if any(pkg in command_lower for pkg in ["pip install", "npm install", "apt install"]):
            return RiskLevel.CAUTION

        # Check for git operations (some are caution)
        if "git" in command_lower:
            if any(op in command_lower for op in ["push", "commit", "merge", "rebase"]):
                return RiskLevel.CAUTION

        return RiskLevel.SAFE


def get_mode_config(mode: AgentMode) -> ModeConfig:
    """Get configuration for a mode"""
    return MODE_CONFIGS.get(mode, MODE_CONFIGS[AgentMode.INTERACTIVE])


def get_mode_description(mode: AgentMode) -> str:
    """Get description of a mode"""
    config = get_mode_config(mode)
    return config.description
