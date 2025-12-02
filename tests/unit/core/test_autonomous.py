"""
Tests for the autonomous operation system.

These tests cover the various agent modes, safety checks, action proposals,
engine callbacks, and integration scenarios. They serve both as verification
of the public API and as examples of how the autonomous engine should be used.
"""

import asyncio
import os

# Standard library imports
import sys

# Third‑party imports
import pytest

# Ensure the source package is on the import path when tests run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import objects under test
from hcode.agent.modes import (
    AgentMode,
    RiskLevel,
    ModeConfig,
    SafetyConfig,
    get_mode_config,
)
from hcode.agent.autonomous import (
    ExecutionDecision,
    ActionProposal,
    AutonomousEngine,
    create_read_action,
    create_edit_action,
    create_write_action,
    create_bash_action,
    create_search_action,
)


class TestAgentModes:
    """Test suite for the :class:`AgentMode` enumeration and its configuration.

    The tests verify that each enum value matches the expected string and that the
    helper functions return a valid :class:`ModeConfig` instance with the correct
    defaults for each mode.
    """

    def test_mode_values(self):
        """Validate the string values of the ``AgentMode`` enum members."""
        assert AgentMode.INTERACTIVE.value == "interactive"
        assert AgentMode.AUTO.value == "auto"
        assert AgentMode.PLAN.value == "plan"
        assert AgentMode.REVIEW.value == "review"

    def test_risk_levels(self):
        """Validate the string values of the ``RiskLevel`` enum members."""
        assert RiskLevel.SAFE.value == "safe"
        assert RiskLevel.CAUTION.value == "caution"
        assert RiskLevel.DANGEROUS.value == "dangerous"

    def test_mode_configs_exist(self):
        """Every ``AgentMode`` must have an associated ``ModeConfig`` object."""
        for mode in AgentMode:
            config = get_mode_config(mode)
            assert isinstance(config, ModeConfig)

    def test_interactive_mode_config(self):
        """Check the default configuration for the interactive mode.

        Interactive mode should request permission for every action and require
        confirmation for dangerous operations.
        """
        config = get_mode_config(AgentMode.INTERACTIVE)
        assert config.ask_permission is True
        assert config.confirm_dangerous is True
        assert config.max_actions_without_confirm == 1

    def test_auto_mode_config(self):
        """Check the default configuration for the auto mode.

        Auto mode runs without asking permission but still confirms dangerous
        actions. ``max_actions_without_confirm`` is set to a very high number to
        effectively disable the limit.
        """
        config = get_mode_config(AgentMode.AUTO)
        assert config.ask_permission is False
        assert config.confirm_dangerous is True  # Still confirms dangerous
        assert config.max_actions_without_confirm == 999

    def test_plan_mode_config(self):
        """Validate the configuration for the planning mode.

        Planning mode shows the generated plan and executes it automatically.
        """
        config = get_mode_config(AgentMode.PLAN)
        assert config.show_plan is True
        assert config.execute_after_plan is True
        assert config.require_approval is False

    def test_review_mode_config(self):
        """Validate the configuration for the review mode.

        Review mode displays the plan and requires explicit approval before any
        action is taken.
        """
        config = get_mode_config(AgentMode.REVIEW)
        assert config.show_plan is True
        assert config.require_approval is True


class TestSafetyConfig:
    """Tests for the :class:`SafetyConfig` helper class.

    ``SafetyConfig`` encapsulates logic for detecting dangerous commands,
    protected files/directories, and assessing risk levels for file operations.
    """

    def test_dangerous_commands(self):
        """Detect obviously dangerous shell commands."""
        safety = SafetyConfig()
        # Dangerous commands should be flagged
        assert safety.is_dangerous_command("rm -rf /")
        assert safety.is_dangerous_command("sudo apt-get remove")
        assert safety.is_dangerous_command("git push --force")
        assert safety.is_dangerous_command("DROP TABLE users")
        # Safe commands should not be flagged
        assert not safety.is_dangerous_command("ls -la")
        assert not safety.is_dangerous_command("cat file.txt")
        assert not safety.is_dangerous_command("git status")

    def test_dangerous_patterns(self):
        """Pattern‑based detection for commands that contain risky substrings."""
        safety = SafetyConfig()
        assert safety.is_dangerous_command("rm -rf /home/user")
        assert safety.is_dangerous_command("rm *.py")
        assert safety.is_dangerous_command("git push origin main -f")

    def test_protected_files(self):
        """Identify files that are considered protected and should not be edited lightly."""
        safety = SafetyConfig()
        # Protected files
        assert safety.is_protected_file(".env")
        assert safety.is_protected_file("/path/to/.env")
        assert safety.is_protected_file("package.json")
        assert safety.is_protected_file("requirements.txt")
        # Non‑protected files
        assert not safety.is_protected_file("main.py")
        assert not safety.is_protected_file("src/utils.py")

    def test_protected_directories(self):
        """Identify directories that are protected (e.g., version‑control metadata)."""
        safety = SafetyConfig()
        assert safety.is_protected_directory(".git")
        assert safety.is_protected_directory("node_modules")
        assert safety.is_protected_directory(".venv")
        # Regular source directories are not protected
        assert not safety.is_protected_directory("src")
        assert not safety.is_protected_directory("tests")

    def test_sensitive_paths(self):
        """Paths that contain sensitive information should be flagged as risky."""
        safety = SafetyConfig()
        assert safety.is_sensitive_path("/etc/passwd")
        assert safety.is_sensitive_path("C:\Windows\System32")
        assert safety.is_sensitive_path("~/.ssh/id_rsa")
        # Any path under /home is considered sensitive in this implementation
        assert safety.is_sensitive_path("/home/user/project")
        # Non‑sensitive locations
        assert not safety.is_sensitive_path("D:\projects\myapp")
        assert not safety.is_sensitive_path("/tmp/test.txt")

    def test_file_risk_assessment(self):
        """Assess risk levels for file operations based on protection status.

        - Protected files → ``CAUTION`` for read/edit, ``DANGEROUS`` for delete.
        - Normal files → ``SAFE``.
        """
        safety = SafetyConfig()
        # Protected files are ``CAUTION`` for edit
        assert safety.assess_file_risk(".env", "edit") == RiskLevel.CAUTION
        assert safety.assess_file_risk("package.json", "edit") == RiskLevel.CAUTION
        # Deleting a protected file is ``DANGEROUS``
        assert safety.assess_file_risk(".git", "delete") == RiskLevel.DANGEROUS
        # Reading a protected file is still ``CAUTION``
        assert safety.assess_file_risk(".env", "read") == RiskLevel.CAUTION
        # Normal files are ``SAFE`` for read and edit
        assert safety.assess_file_risk("main.py", "read") == RiskLevel.SAFE
        assert safety.assess_file_risk("main.py", "edit") == RiskLevel.SAFE

    def test_command_risk_assessment(self):
        """Assess risk levels for arbitrary shell commands.

        The mapping mirrors :meth:`SafetyConfig.is_dangerous_command` and
        ``is_caution_command`` heuristics.
        """
        safety = SafetyConfig()
        # Dangerous commands
        assert safety.assess_command_risk("sudo rm -rf") == RiskLevel.DANGEROUS
        assert safety.assess_command_risk("git push --force") == RiskLevel.DANGEROUS
        # Caution‑level commands
        assert safety.assess_command_risk("pip install flask") == RiskLevel.CAUTION
        assert safety.assess_command_risk("git commit -m 'msg'") == RiskLevel.CAUTION
        # Safe commands
        assert safety.assess_command_risk("ls -la") == RiskLevel.SAFE
        assert safety.assess_command_risk("python main.py") == RiskLevel.SAFE


class TestActionProposal:
    """Tests for the helper functions that create :class:`ActionProposal` objects.

    Each ``create_*_action`` function returns a fully‑populated proposal that the
    engine can later evaluate.
    """

    def test_create_read_action(self):
        """Read‑action proposals should contain the correct tool name and risk level."""
        action = create_read_action("src/main.py", "Read main file")
        assert action.tool_name == "Read"
        assert action.risk_level == "safe"
        assert "src/main.py" in action.affects_files

    def test_create_edit_action(self):
        """Edit‑action proposals must capture old/new code snippets and a reason."""
        action = create_edit_action("src/main.py", "old_code", "new_code", "Fix bug")
        assert action.tool_name == "Edit"
        assert "src/main.py" in action.affects_files

    def test_create_bash_action(self):
        """Bash‑action proposals should store the command string and be marked safe."""
        action = create_bash_action("ls -la", "List files")
        assert action.tool_name == "Bash"
        assert action.risk_level == "safe"
        assert action.arguments["command"] == "ls -la"

    def test_create_write_action(self):
        """Write‑action proposals create or overwrite a file with given content."""
        action = create_write_action("output.txt", "some data", "Generate report")
        assert action.tool_name == "Write"
        assert action.risk_level == "safe"
        assert action.arguments["file_path"] == "output.txt"

    def test_create_search_action(self):
        """Search‑action proposals look for a pattern across the code base."""
        action = create_search_action("TODO")
        assert action.tool_name == "Search"
        assert action.risk_level == "safe"
        assert action.arguments["pattern"] == "TODO"


class TestConfirmationMessages:
    """Tests that the engine builds user‑facing confirmation messages correctly.

    The messages include risk indicators, affected files, and any special notes.
    """

    def test_safe_action_message(self):
        """A safe action should show a neutral ``[OK]`` indicator."""
        engine = AutonomousEngine()
        action = create_read_action("main.py", "Read the main file")
        message = engine._build_confirmation_message(action)
        assert "[OK]" in message
        assert "Read" in message
        assert "main.py" in message

    def test_dangerous_action_message(self):
        """Dangerous actions must warn the user that the operation cannot be undone."""
        engine = AutonomousEngine()
        action = ActionProposal(
            tool_name="Bash",
            arguments={"command": "rm -rf /tmp/data"},
            reason="Delete temp data",
            risk_level="dangerous",
            reversible=False,
        )
        message = engine._build_confirmation_message(action)
        assert "[!!]" in message
        assert "cannot be undone" in message

    def test_action_affects_display(self):
        """When many files are affected, the message should truncate and indicate the remainder."""
        engine = AutonomousEngine()
        action = ActionProposal(
            tool_name="Edit",
            arguments={"file_path": "main.py"},
            reason="Fix bug",
            affects_files=["main.py", "utils.py", "tests.py", "extra.py"],
        )
        message = engine._build_confirmation_message(action)
        assert "Affects:" in message
        # The implementation shows the first three files and then "and X more"
        assert "and 1 more" in message or "more" in message


class TestCallbacks:
    """Verify that the engine correctly invokes user‑provided callbacks.

    Callbacks are used for confirmation prompts and progress reporting.
    """

    def test_confirmation_callback(self):
        """The confirmation callback should be called exactly once per action."""
        engine = AutonomousEngine()
        confirmed = []

        def callback(msg):
            confirmed.append(msg)
            return True

        engine.set_confirmation_callback(callback)
        action = create_read_action("test.py")
        asyncio.get_event_loop().run_until_complete(engine.confirm_action(action))
        assert len(confirmed) == 1

    def test_progress_callback(self):
        """Progress updates should be forwarded to the registered callback."""
        engine = AutonomousEngine()
        progress_updates = []

        def callback(msg, pct):
            progress_updates.append((msg, pct))

        engine.set_progress_callback(callback)
        engine.update_progress("Working...", 0.5)
        assert len(progress_updates) == 1
        assert progress_updates[0] == ("Working...", 0.5)


class TestIntegration:
    """Higher‑level integration tests that exercise the full autonomous workflow.

    These tests simulate realistic usage scenarios across different agent modes.
    """

    @pytest.mark.asyncio
    async def test_full_auto_execution_flow(self):
        """Run a series of actions in AUTO mode and ensure they all execute."""
        engine = AutonomousEngine(mode=AgentMode.AUTO)
        actions = [
            create_read_action("main.py"),
            create_search_action("TODO"),
            create_edit_action("main.py", "old", "new"),
        ]
        executed = []
        skipped = []
        for action in actions:
            decision = engine.decide_execution(action)
            if decision == ExecutionDecision.EXECUTE:
                executed.append(action)
                engine.track_action(action, True)
            elif decision == ExecutionDecision.SKIP:
                skipped.append(action)
        assert len(executed) == 3
        assert len(skipped) == 0

    @pytest.mark.asyncio
    async def test_plan_mode_flow(self):
        """Validate planning mode: build a plan, approve it, and execute each step."""
        engine = AutonomousEngine(mode=AgentMode.PLAN)
        # Build the plan
        engine.add_to_plan(create_read_action("main.py"))
        engine.add_to_plan(create_edit_action("main.py", "a", "b"))
        # Verify the plan display contains the correct count
        display = engine.format_plan_display()
        assert "2 actions" in display
        # Approve and run the plan
        engine.approve_plan()
        for action in engine.get_plan():
            decision = engine.decide_execution(action)
            assert decision == ExecutionDecision.EXECUTE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
