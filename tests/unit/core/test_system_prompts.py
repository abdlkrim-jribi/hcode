"""
Tests for system prompts, modes, and safety configuration.

Tests autonomous prompt generation, mode configurations, and safety checks.
"""

import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hcode.agent.modes import (
    AgentMode,
    ConfirmationLevel,
    RiskLevel,
    ModeConfig,
    SafetyConfig,
    MODE_CONFIGS,
    get_mode_config,
    get_mode_description,
)
from hcode.agent.autonomous_prompt import (
    BASE_AUTONOMOUS_PROMPT,
    MODE_INSTRUCTIONS,
    CONFIRMATION_PROMPTS,
    get_autonomous_prompt,
    get_mode_transition_prompt,
    get_confirmation_prompt,
    get_error_recovery_prompt,
)


class TestAgentMode:
    """Tests for AgentMode enum"""

    def test_all_modes_defined(self):
        """Test all expected modes are defined"""
        assert AgentMode.INTERACTIVE.value == "interactive"
        assert AgentMode.AUTO.value == "auto"
        assert AgentMode.PLAN.value == "plan"
        assert AgentMode.REVIEW.value == "review"

    def test_mode_count(self):
        """Test correct number of modes"""
        assert len(AgentMode) == 4

    def test_mode_from_string(self):
        """Test creating mode from string"""
        assert AgentMode("interactive") == AgentMode.INTERACTIVE
        assert AgentMode("auto") == AgentMode.AUTO
        assert AgentMode("plan") == AgentMode.PLAN
        assert AgentMode("review") == AgentMode.REVIEW

    def test_invalid_mode(self):
        """Test invalid mode raises error"""
        with pytest.raises(ValueError):
            AgentMode("invalid_mode")


class TestConfirmationLevel:
    """Tests for ConfirmationLevel enum"""

    def test_all_levels_defined(self):
        """Test all confirmation levels defined"""
        assert ConfirmationLevel.NONE.value == "none"
        assert ConfirmationLevel.DANGEROUS_ONLY.value == "dangerous_only"
        assert ConfirmationLevel.ALL.value == "all"
        assert ConfirmationLevel.FIRST_ONLY.value == "first_only"


class TestRiskLevel:
    """Tests for RiskLevel enum"""

    def test_all_levels_defined(self):
        """Test all risk levels defined"""
        assert RiskLevel.SAFE.value == "safe"
        assert RiskLevel.CAUTION.value == "caution"
        assert RiskLevel.DANGEROUS.value == "dangerous"


class TestModeConfig:
    """Tests for ModeConfig dataclass"""

    def test_default_values(self):
        """Test default configuration values"""
        config = ModeConfig()

        assert config.ask_permission == True
        assert config.show_plan == False
        assert config.confirm_dangerous == True
        assert config.execute_after_plan == False
        assert config.require_approval == False
        assert config.max_actions_without_confirm == 10

    def test_custom_values(self):
        """Test custom configuration"""
        config = ModeConfig(
            ask_permission=False, show_plan=True, confirm_dangerous=False, description="Custom mode"
        )

        assert config.ask_permission == False
        assert config.show_plan == True
        assert config.confirm_dangerous == False
        assert config.description == "Custom mode"


class TestModeConfigs:
    """Tests for predefined mode configurations"""

    def test_interactive_config(self):
        """Test INTERACTIVE mode config"""
        config = MODE_CONFIGS[AgentMode.INTERACTIVE]

        assert config.ask_permission == True
        assert config.show_plan == False
        assert config.confirm_dangerous == True
        assert config.max_actions_without_confirm == 1
        assert "ask" in config.description.lower()

    def test_auto_config(self):
        """Test AUTO mode config"""
        config = MODE_CONFIGS[AgentMode.AUTO]

        assert config.ask_permission == False
        assert config.show_plan == False
        assert config.confirm_dangerous == True  # Still confirm dangerous!
        assert config.execute_after_plan == True
        assert "automatic" in config.description.lower()

    def test_plan_config(self):
        """Test PLAN mode config"""
        config = MODE_CONFIGS[AgentMode.PLAN]

        assert config.ask_permission == False
        assert config.show_plan == True
        assert config.execute_after_plan == True
        assert config.require_approval == False
        assert "plan" in config.description.lower()

    def test_review_config(self):
        """Test REVIEW mode config"""
        config = MODE_CONFIGS[AgentMode.REVIEW]

        assert config.ask_permission == False
        assert config.show_plan == True
        assert config.execute_after_plan == True
        assert config.require_approval == True  # Key difference from PLAN
        assert "approval" in config.description.lower()

    def test_get_mode_config(self):
        """Test get_mode_config function"""
        config = get_mode_config(AgentMode.AUTO)
        assert config == MODE_CONFIGS[AgentMode.AUTO]

    def test_get_mode_description(self):
        """Test get_mode_description function"""
        desc = get_mode_description(AgentMode.INTERACTIVE)
        assert "ask" in desc.lower()


class TestSafetyConfig:
    """Tests for SafetyConfig"""

    def test_initialization(self):
        """Test default safety config"""
        config = SafetyConfig()

        assert len(config.dangerous_commands) > 0
        assert len(config.dangerous_patterns) > 0
        assert len(config.protected_files) > 0
        assert len(config.protected_directories) > 0

    def test_dangerous_commands(self):
        """Test dangerous commands are identified"""
        config = SafetyConfig()

        # Test destructive commands
        assert config.is_dangerous_command("rm -rf /")
        assert config.is_dangerous_command("rm file.txt")
        assert config.is_dangerous_command("del file.txt")
        assert config.is_dangerous_command("sudo apt remove")

        # Test non-dangerous commands
        assert not config.is_dangerous_command("ls -la")
        assert not config.is_dangerous_command("cat file.txt")
        assert not config.is_dangerous_command("echo hello")
        assert not config.is_dangerous_command("pwd")

    def test_dangerous_git_commands(self):
        """Test dangerous git commands"""
        config = SafetyConfig()

        assert config.is_dangerous_command("git push --force")
        assert config.is_dangerous_command("git push -f origin main")
        assert config.is_dangerous_command("git reset --hard HEAD~1")
        assert config.is_dangerous_command("git clean -fd")

        # These should not be dangerous
        assert not config.is_dangerous_command("git status")
        assert not config.is_dangerous_command("git diff")
        assert not config.is_dangerous_command("git log")
        assert not config.is_dangerous_command("git add .")

    def test_dangerous_database_commands(self):
        """Test dangerous database commands"""
        config = SafetyConfig()

        assert config.is_dangerous_command("DROP TABLE users;")
        assert config.is_dangerous_command("drop database test")
        assert config.is_dangerous_command("TRUNCATE TABLE logs")

    def test_dangerous_patterns(self):
        """Test dangerous patterns detection"""
        config = SafetyConfig()

        # Wildcard deletes
        assert config.is_dangerous_command("rm -rf *.py")
        assert config.is_dangerous_command("del *.txt")

        # SQL without WHERE
        assert config.is_dangerous_command("DELETE FROM users;")

    def test_protected_files(self):
        """Test protected file detection"""
        config = SafetyConfig()

        assert config.is_protected_file(".env")
        assert config.is_protected_file(".env.local")
        assert config.is_protected_file("package.json")
        assert config.is_protected_file("requirements.txt")
        assert config.is_protected_file("pyproject.toml")
        assert config.is_protected_file("Dockerfile")
        assert config.is_protected_file(".gitignore")

        # Not protected
        assert not config.is_protected_file("main.py")
        assert not config.is_protected_file("test_file.txt")
        assert not config.is_protected_file("README.md")

    def test_protected_directories(self):
        """Test protected directory detection"""
        config = SafetyConfig()

        assert config.is_protected_directory(".git")
        assert config.is_protected_directory("node_modules")
        assert config.is_protected_directory(".venv")
        assert config.is_protected_directory("__pycache__")
        assert config.is_protected_directory(".idea")

        # Not protected
        assert not config.is_protected_directory("src")
        assert not config.is_protected_directory("tests")

    def test_sensitive_paths(self):
        """Test sensitive path detection"""
        config = SafetyConfig()

        assert config.is_sensitive_path("/etc/passwd")
        assert config.is_sensitive_path("/usr/bin/python")
        assert config.is_sensitive_path("C:\\Windows\\System32")
        assert config.is_sensitive_path("~/.ssh/id_rsa")

        # Not sensitive
        assert not config.is_sensitive_path("/tmp/test.txt")

    def test_assess_file_risk_safe(self):
        """Test file risk assessment for safe files"""
        config = SafetyConfig()

        assert config.assess_file_risk("src/main.py", "read") == RiskLevel.SAFE
        assert config.assess_file_risk("test.txt", "edit") == RiskLevel.SAFE

    def test_assess_file_risk_caution(self):
        """Test file risk assessment for caution files"""
        config = SafetyConfig()

        assert config.assess_file_risk(".env", "edit") == RiskLevel.CAUTION
        assert config.assess_file_risk("package.json", "edit") == RiskLevel.CAUTION

    def test_assess_file_risk_dangerous(self):
        """Test file risk assessment for dangerous operations"""
        config = SafetyConfig()

        assert config.assess_file_risk(".env", "delete") == RiskLevel.DANGEROUS
        assert config.assess_file_risk(".git", "delete") == RiskLevel.DANGEROUS

    def test_assess_command_risk_safe(self):
        """Test command risk assessment for safe commands"""
        config = SafetyConfig()

        assert config.assess_command_risk("ls -la") == RiskLevel.SAFE
        assert config.assess_command_risk("cat file.txt") == RiskLevel.SAFE
        assert config.assess_command_risk("echo hello") == RiskLevel.SAFE

    def test_assess_command_risk_caution(self):
        """Test command risk assessment for caution commands"""
        config = SafetyConfig()

        assert config.assess_command_risk("pip install requests") == RiskLevel.CAUTION
        assert config.assess_command_risk("npm install express") == RiskLevel.CAUTION
        assert config.assess_command_risk("git push origin main") == RiskLevel.CAUTION
        assert config.assess_command_risk("git commit -m 'message'") == RiskLevel.CAUTION

    def test_assess_command_risk_dangerous(self):
        """Test command risk assessment for dangerous commands"""
        config = SafetyConfig()

        assert config.assess_command_risk("rm -rf /") == RiskLevel.DANGEROUS
        assert config.assess_command_risk("sudo rm file") == RiskLevel.DANGEROUS
        assert config.assess_command_risk("git push --force") == RiskLevel.DANGEROUS


class TestBaseAutonomousPrompt:
    """Tests for base autonomous prompt"""

    def test_prompt_contains_core_principles(self):
        """Test prompt contains core principles"""
        assert "CORE PRINCIPLES" in BASE_AUTONOMOUS_PROMPT
        assert "Efficiency" in BASE_AUTONOMOUS_PROMPT
        assert "Safety" in BASE_AUTONOMOUS_PROMPT
        assert "Transparency" in BASE_AUTONOMOUS_PROMPT

    def test_prompt_contains_react_loop(self):
        """Test prompt contains ReAct loop"""
        assert "ReAct" in BASE_AUTONOMOUS_PROMPT or "REASONING" in BASE_AUTONOMOUS_PROMPT
        assert "THINK" in BASE_AUTONOMOUS_PROMPT
        assert "PLAN" in BASE_AUTONOMOUS_PROMPT
        assert "ACT" in BASE_AUTONOMOUS_PROMPT
        assert "OBSERVE" in BASE_AUTONOMOUS_PROMPT

    def test_prompt_contains_todo_management(self):
        """Test prompt contains todo management instructions"""
        assert "TODO" in BASE_AUTONOMOUS_PROMPT
        assert "TodoWrite" in BASE_AUTONOMOUS_PROMPT
        assert "in_progress" in BASE_AUTONOMOUS_PROMPT

    def test_prompt_contains_tool_usage(self):
        """Test prompt contains tool usage guidelines"""
        assert "TOOL" in BASE_AUTONOMOUS_PROMPT
        assert "Safe Operations" in BASE_AUTONOMOUS_PROMPT
        assert "Dangerous Operations" in BASE_AUTONOMOUS_PROMPT

    def test_prompt_contains_safety_rules(self):
        """Test prompt contains safety rules"""
        assert "SAFETY RULES" in BASE_AUTONOMOUS_PROMPT
        assert "NEVER" in BASE_AUTONOMOUS_PROMPT
        assert "delete" in BASE_AUTONOMOUS_PROMPT.lower()
        assert "confirmation" in BASE_AUTONOMOUS_PROMPT.lower()

    def test_prompt_has_mode_placeholder(self):
        """Test prompt has placeholder for mode-specific instructions"""
        assert "{mode_specific_instructions}" in BASE_AUTONOMOUS_PROMPT


class TestModeInstructions:
    """Tests for mode-specific instructions"""

    def test_all_modes_have_instructions(self):
        """Test all modes have instructions defined"""
        assert AgentMode.INTERACTIVE in MODE_INSTRUCTIONS
        assert AgentMode.AUTO in MODE_INSTRUCTIONS
        assert AgentMode.PLAN in MODE_INSTRUCTIONS
        assert AgentMode.REVIEW in MODE_INSTRUCTIONS

    def test_interactive_instructions(self):
        """Test INTERACTIVE mode instructions"""
        instructions = MODE_INSTRUCTIONS[AgentMode.INTERACTIVE]

        assert "INTERACTIVE" in instructions
        assert "ASK" in instructions or "ask" in instructions.lower()
        assert "permission" in instructions.lower()
        assert "confirmation" in instructions.lower() or "confirm" in instructions.lower()

    def test_auto_instructions(self):
        """Test AUTO mode instructions"""
        instructions = MODE_INSTRUCTIONS[AgentMode.AUTO]

        assert "AUTO" in instructions
        assert "automatically" in instructions.lower() or "automatic" in instructions.lower()
        assert "dangerous" in instructions.lower()

    def test_plan_instructions(self):
        """Test PLAN mode instructions"""
        instructions = MODE_INSTRUCTIONS[AgentMode.PLAN]

        assert "PLAN" in instructions
        assert "Phase 1" in instructions or "Planning" in instructions
        assert "Execute" in instructions

    def test_review_instructions(self):
        """Test REVIEW mode instructions"""
        instructions = MODE_INSTRUCTIONS[AgentMode.REVIEW]

        assert "REVIEW" in instructions
        assert "approval" in instructions.lower() or "approve" in instructions.lower()
        assert "NEVER execute without" in instructions or "wait" in instructions.lower()


class TestGetAutonomousPrompt:
    """Tests for get_autonomous_prompt function"""

    def test_returns_prompt_for_interactive(self):
        """Test returns prompt for INTERACTIVE mode"""
        prompt = get_autonomous_prompt(AgentMode.INTERACTIVE)

        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "INTERACTIVE" in prompt
        assert "CORE PRINCIPLES" in prompt

    def test_returns_prompt_for_auto(self):
        """Test returns prompt for AUTO mode"""
        prompt = get_autonomous_prompt(AgentMode.AUTO)

        assert "AUTO" in prompt
        assert "automatically" in prompt.lower()

    def test_returns_prompt_for_plan(self):
        """Test returns prompt for PLAN mode"""
        prompt = get_autonomous_prompt(AgentMode.PLAN)

        assert "PLAN" in prompt

    def test_returns_prompt_for_review(self):
        """Test returns prompt for REVIEW mode"""
        prompt = get_autonomous_prompt(AgentMode.REVIEW)

        assert "REVIEW" in prompt
        assert "approval" in prompt.lower()

    def test_with_additional_context(self):
        """Test prompt with additional context"""
        context = {
            "project_type": "Python",
            "working_directory": "/home/user/project",
            "recent_files": ["main.py", "utils.py", "test.py"],
        }

        prompt = get_autonomous_prompt(AgentMode.AUTO, additional_context=context)

        assert "CONTEXT" in prompt
        assert "Python" in prompt
        assert "main.py" in prompt

    def test_mode_specific_instructions_included(self):
        """Test mode-specific instructions are included"""
        prompt = get_autonomous_prompt(AgentMode.INTERACTIVE)

        # Should not have placeholder
        assert "{mode_specific_instructions}" not in prompt

        # Should have the mode instructions
        assert "permission" in prompt.lower()


class TestGetModeTransitionPrompt:
    """Tests for get_mode_transition_prompt function"""

    def test_interactive_to_auto(self):
        """Test transition from INTERACTIVE to AUTO"""
        prompt = get_mode_transition_prompt(AgentMode.INTERACTIVE, AgentMode.AUTO)

        assert "AUTO" in prompt
        assert "automatic" in prompt.lower() or "automatically" in prompt.lower()

    def test_auto_to_interactive(self):
        """Test transition from AUTO to INTERACTIVE"""
        prompt = get_mode_transition_prompt(AgentMode.AUTO, AgentMode.INTERACTIVE)

        assert "INTERACTIVE" in prompt
        assert "permission" in prompt.lower() or "ask" in prompt.lower()

    def test_interactive_to_plan(self):
        """Test transition from INTERACTIVE to PLAN"""
        prompt = get_mode_transition_prompt(AgentMode.INTERACTIVE, AgentMode.PLAN)

        assert "PLAN" in prompt

    def test_plan_to_review(self):
        """Test transition from PLAN to REVIEW"""
        prompt = get_mode_transition_prompt(AgentMode.PLAN, AgentMode.REVIEW)

        assert "REVIEW" in prompt
        assert "approval" in prompt.lower()

    def test_fallback_for_undefined_transition(self):
        """Test fallback for undefined transitions"""
        prompt = get_mode_transition_prompt(AgentMode.REVIEW, AgentMode.INTERACTIVE)

        assert "review" in prompt.lower()
        assert "interactive" in prompt.lower()


class TestConfirmationPrompts:
    """Tests for confirmation prompt templates"""

    def test_dangerous_command_template(self):
        """Test dangerous command template"""
        template = CONFIRMATION_PROMPTS["dangerous_command"]

        assert "DANGEROUS" in template
        assert "{command}" in template
        assert "confirm" in template.lower()

    def test_protected_file_template(self):
        """Test protected file template"""
        template = CONFIRMATION_PROMPTS["protected_file"]

        assert "PROTECTED" in template
        assert "{file_path}" in template

    def test_multiple_files_template(self):
        """Test multiple files template"""
        template = CONFIRMATION_PROMPTS["multiple_files"]

        assert "{count}" in template
        assert "{file_list}" in template

    def test_git_push_template(self):
        """Test git push template"""
        template = CONFIRMATION_PROMPTS["git_push"]

        assert "{branch}" in template
        assert "{remote}" in template


class TestGetConfirmationPrompt:
    """Tests for get_confirmation_prompt function"""

    def test_dangerous_command(self):
        """Test getting dangerous command prompt"""
        prompt = get_confirmation_prompt(
            "dangerous_command",
            command="rm -rf /",
            risk_description="Will delete all files",
            affected_items="Entire filesystem",
        )

        assert "rm -rf /" in prompt
        assert "delete all files" in prompt

    def test_protected_file(self):
        """Test getting protected file prompt"""
        prompt = get_confirmation_prompt(
            "protected_file", file_path=".env", preview="SECRET_KEY=xxx"
        )

        assert ".env" in prompt
        assert "SECRET_KEY" in prompt

    def test_unknown_type_returns_default(self):
        """Test unknown confirmation type returns default"""
        prompt = get_confirmation_prompt("unknown_type")

        assert "confirm" in prompt.lower()


class TestGetErrorRecoveryPrompt:
    """Tests for get_error_recovery_prompt function"""

    def test_basic_error_prompt(self):
        """Test basic error recovery prompt"""
        prompt = get_error_recovery_prompt(
            operation="File read", error="File not found", retry_count=1, max_retries=3
        )

        assert "ERROR" in prompt
        assert "File read" in prompt
        assert "File not found" in prompt
        assert "1/3" in prompt or "1" in prompt

    def test_contains_options(self):
        """Test error prompt contains recovery options"""
        prompt = get_error_recovery_prompt(
            operation="Test", error="Error", retry_count=0, max_retries=3
        )

        assert "Retry" in prompt or "retry" in prompt
        assert "Skip" in prompt or "skip" in prompt


class TestSafetyConfigEdgeCases:
    """Tests for edge cases in SafetyConfig"""

    def test_case_insensitive_commands(self):
        """Test command matching is case insensitive"""
        config = SafetyConfig()

        assert config.is_dangerous_command("RM -RF /")
        assert config.is_dangerous_command("Sudo apt remove")
        assert config.is_dangerous_command("GIT PUSH --FORCE")

    def test_command_with_extra_whitespace(self):
        """Test command matching with extra whitespace"""
        config = SafetyConfig()

        assert config.is_dangerous_command("  rm  -rf  /  ")

    def test_protected_file_path_normalization(self):
        """Test protected file detection with paths"""
        config = SafetyConfig()

        assert config.is_protected_file("/path/to/.env")
        assert config.is_protected_file("./package.json")
        assert config.is_protected_file("project\\requirements.txt")

    def test_protected_directory_trailing_slash(self):
        """Test protected directory with trailing slash"""
        config = SafetyConfig()

        assert config.is_protected_directory(".git/")
        assert config.is_protected_directory("node_modules\\")

    def test_sensitive_path_normalization(self):
        """Test sensitive path with different separators"""
        config = SafetyConfig()

        assert config.is_sensitive_path("/etc/passwd")
        assert config.is_sensitive_path("C:\\Windows\\System32\\config")


class TestPromptIntegration:
    """Integration tests for prompt system"""

    def test_full_prompt_generation(self):
        """Test full prompt generation workflow"""
        # Generate prompt for each mode
        for mode in AgentMode:
            prompt = get_autonomous_prompt(mode)

            assert len(prompt) > 500  # Substantial prompt
            assert "CORE PRINCIPLES" in prompt
            assert "TODO" in prompt
            assert mode.value.upper() in prompt or mode.name in prompt

    def test_prompt_consistency(self):
        """Test prompts are consistent across calls"""
        prompt1 = get_autonomous_prompt(AgentMode.AUTO)
        prompt2 = get_autonomous_prompt(AgentMode.AUTO)

        assert prompt1 == prompt2

    def test_all_transitions_work(self):
        """Test all mode transitions return prompts"""
        modes = list(AgentMode)

        for old_mode in modes:
            for new_mode in modes:
                if old_mode != new_mode:
                    prompt = get_mode_transition_prompt(old_mode, new_mode)
                    assert isinstance(prompt, str)
                    assert len(prompt) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
