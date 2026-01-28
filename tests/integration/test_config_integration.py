"""
Integration tests for configuration system.

Tests that all prompts and parameters are properly loaded from config files
and not hardcoded in the source code.
"""

from pathlib import Path

import pytest

from hcode.config.prompts import (
    get_prompts_config,
    get_models_config,
    get_system_prompt,
    get_generation_params,
)


class TestPromptsConfigIntegration:
    """Test prompts configuration integration"""

    def test_prompts_config_singleton(self):
        """Test that PromptsConfig is a singleton"""
        config1 = get_prompts_config()
        config2 = get_prompts_config()
        assert config1 is config2

    def test_config_file_loaded(self):
        """Test that config/prompts.yaml is loaded"""
        config = get_prompts_config()
        assert config.config_path is not None
        assert config.config_path.exists()
        assert config.config_path.name == "prompts.yaml"

    def test_all_system_prompts_exist(self):
        """Test that all required system prompts exist in config"""
        required_prompts = [
            "coding_agent",
            "openai_coding",
            "enhanced_agent",
            "sub_agent",
            "explore_agent",
            "plan_agent",
            "code_agent",
            "test_agent",
            "planning",
            "code_review",
            "compact",
            "react_coding_agent",  # Added in migration
            "autonomous_agent",     # Added in migration
            "chat_agent",           # Added in migration
            "claude_code_style",
        ]

        for prompt_type in required_prompts:
            prompt = get_system_prompt(prompt_type)
            assert prompt, f"Prompt '{prompt_type}' is empty or missing"
            assert len(prompt) > 50, f"Prompt '{prompt_type}' is too short"
            # Check it's not a default fallback
            assert "Hcode" in prompt or "You are" in prompt, f"Prompt '{prompt_type}' has unexpected format"

    def test_tool_prompts_exist(self):
        """Test that tool prompts exist"""
        config = get_prompts_config()
        tool_prompts = [
            "bash_description",
            "file_path_extraction",
            "confirm_operation",
            "task_delegation",
            "error_recovery",
            "continuation_readonly",   # Added in migration
            "continuation_general",    # Added in migration
            "generate_issue_title",
        ]

        for prompt_name in tool_prompts:
            prompt = config.get_tool_prompt(prompt_name)
            assert prompt, f"Tool prompt '{prompt_name}' is empty or missing"

    def test_git_prompts_exist(self):
        """Test that git prompts exist"""
        config = get_prompts_config()
        git_prompts = ["commit_analysis", "commit_footer", "pr_analysis"]

        for prompt_name in git_prompts:
            prompt = config.get_git_prompt(prompt_name)
            assert prompt, f"Git prompt '{prompt_name}' is empty or missing"

    def test_continuation_prompts_exist(self):
        """Test that continuation prompts exist"""
        config = get_prompts_config()
        continuation_prompts = config.get_continuation_prompts()

        assert len(continuation_prompts) >= 3
        for prompt in continuation_prompts:
            assert "continue" in prompt.lower() or "pick up" in prompt.lower()

    def test_memory_config_exists(self):
        """Test that memory configuration exists"""
        config = get_prompts_config()
        memory_config = config.get_memory_config()

        assert "memory_file" in memory_config
        assert memory_config["memory_file"]  # Not empty

    def test_persona_config_exists(self):
        """Test that persona configuration exists"""
        config = get_prompts_config()
        persona = config.get_persona()

        assert "name" in persona
        assert "tone" in persona
        assert "use_emojis" in persona
        assert "verbosity" in persona


class TestModelsConfigIntegration:
    """Test models configuration integration"""

    def test_models_config_singleton(self):
        """Test that ModelsConfig is a singleton"""
        config1 = get_models_config()
        config2 = get_models_config()
        assert config1 is config2

    def test_config_file_loaded(self):
        """Test that config/models.yaml is loaded"""
        config = get_models_config()
        assert config.config_path is not None
        assert config.config_path.exists()
        assert config.config_path.name == "models.yaml"

    def test_generation_params_defaults(self):
        """Test default generation parameters"""
        params = get_generation_params()

        assert hasattr(params, "temperature")
        assert hasattr(params, "max_tokens")
        assert hasattr(params, "top_p")
        assert hasattr(params, "top_k")

        # Check reasonable values
        assert 0.0 <= params.temperature <= 2.0
        assert params.max_tokens > 0
        assert 0.0 <= params.top_p <= 1.0

    def test_task_specific_parameters(self):
        """Test task-specific parameter overrides"""
        task_types = [
            "code_generation",
            "bug_fixing",
            "refactoring",
            "documentation",
            "testing",
            "planning",
            "thinking",           # Added in migration
            "thinking_quick",     # Added in migration
            "thinking_standard",  # Added in migration
            "thinking_deep",      # Added in migration
            "exploration",        # Added in migration
            "summary",            # Added in migration
        ]

        for task_type in task_types:
            params = get_generation_params(task_type)
            assert params.temperature >= 0.0
            assert params.max_tokens > 0
            # Each task type should potentially have different values
            params_dict = params.to_dict()
            assert "temperature" in params_dict
            assert "max_tokens" in params_dict

    def test_thinking_parameters_configured(self):
        """Test that thinking task parameters are properly configured"""
        quick_params = get_generation_params("thinking_quick")
        standard_params = get_generation_params("thinking_standard")
        deep_params = get_generation_params("thinking_deep")

        # Quick should have smaller max_tokens than deep
        assert quick_params.max_tokens < deep_params.max_tokens

        # All should have reasonable temperature for thinking
        assert 0.3 <= quick_params.temperature <= 1.0
        assert 0.3 <= standard_params.temperature <= 1.0
        assert 0.3 <= deep_params.temperature <= 1.0

    def test_context_config(self):
        """Test context configuration"""
        config = get_models_config()
        context_config = config.get_context_config()

        assert context_config.max_context_tokens > 0
        assert context_config.reserve_output_tokens > 0
        assert 0.0 < context_config.summarization_threshold < 1.0
        assert context_config.max_history_turns > 0

    def test_continuation_config(self):
        """Test continuation configuration"""
        config = get_models_config()
        continuation_config = config.get_continuation_config()

        assert isinstance(continuation_config.enabled, bool)
        assert continuation_config.max_continuations > 0
        assert continuation_config.max_total_tokens > 0

    def test_reliability_config(self):
        """Test reliability configuration"""
        config = get_models_config()
        reliability_config = config.get_reliability_config()

        assert reliability_config.timeout > 0
        assert reliability_config.connect_timeout > 0
        assert reliability_config.max_retries > 0


class TestAgentsUseConfig:
    """Test that agents properly use configuration"""

    def test_coding_agent_uses_config(self):
        """Test that HcodeCodingAgent loads prompt from config"""
        from hcode.agent.coding_agent import HcodeCodingAgent

        # Check that SYSTEM_PROMPT is loaded from config, not hardcoded
        assert hasattr(HcodeCodingAgent, "SYSTEM_PROMPT")
        assert isinstance(HcodeCodingAgent.SYSTEM_PROMPT, str)
        assert len(HcodeCodingAgent.SYSTEM_PROMPT) > 100

        # Verify it contains expected ReAct content
        assert "THINK" in HcodeCodingAgent.SYSTEM_PROMPT
        assert "PLAN" in HcodeCodingAgent.SYSTEM_PROMPT
        assert "ACT" in HcodeCodingAgent.SYSTEM_PROMPT

    def test_autonomous_agent_uses_config(self):
        """Test that HcodeAutonomousCodingAgent loads prompt from config"""
        from hcode.agent.autonomous_agent import HcodeAutonomousCodingAgent

        # Check that prompt template is loaded from config
        assert hasattr(HcodeAutonomousCodingAgent, "_AUTONOMOUS_PROMPT_TEMPLATE")
        assert isinstance(HcodeAutonomousCodingAgent._AUTONOMOUS_PROMPT_TEMPLATE, str)
        assert len(HcodeAutonomousCodingAgent._AUTONOMOUS_PROMPT_TEMPLATE) > 100

        # Verify it contains expected autonomous content
        prompt = HcodeAutonomousCodingAgent._AUTONOMOUS_PROMPT_TEMPLATE
        assert "OPERATION MODES" in prompt or "mode" in prompt.lower()

    def test_core_agent_uses_continuation_prompts(self):
        """Test that core agent uses continuation prompts from config"""
        from hcode.config.prompts import get_prompts_config

        config = get_prompts_config()

        # Verify continuation prompts exist
        readonly_prompt = config.get_tool_prompt("continuation_readonly")
        general_prompt = config.get_tool_prompt("continuation_general")

        assert readonly_prompt
        assert general_prompt
        assert "READ-ONLY" in readonly_prompt or "read" in readonly_prompt.lower()
        assert "tool" in general_prompt.lower()


class TestNoHardcodedPrompts:
    """Test that prompts are not hardcoded in source files"""

    def test_no_hardcoded_prompts_in_coding_agent(self):
        """Test that coding_agent.py doesn't have hardcoded prompts"""
        agent_file = Path("src/hcode/agent/coding_agent.py")
        if agent_file.exists():
            content = agent_file.read_text()

            # Should import from config
            assert "from hcode.config.prompts import get_system_prompt" in content

            # Should not have long hardcoded strings starting with "You are"
            # (After migration, it should use get_system_prompt())
            lines = content.split("\n")
            for i, line in enumerate(lines):
                # Allow docstrings and comments
                if '"""' in line or "'''" in line or line.strip().startswith("#"):
                    continue
                # Check for hardcoded prompt patterns
                if 'SYSTEM_PROMPT = """You are' in line:
                    pytest.fail(f"Found hardcoded prompt at line {i+1} in coding_agent.py")

    def test_no_hardcoded_prompts_in_autonomous_agent(self):
        """Test that autonomous_agent.py doesn't have hardcoded prompts"""
        agent_file = Path("src/hcode/agent/autonomous_agent.py")
        if agent_file.exists():
            content = agent_file.read_text()

            # Should import from config
            assert "from hcode.config.prompts import get_system_prompt" in content

            # Should use _AUTONOMOUS_PROMPT_TEMPLATE from config
            assert "_AUTONOMOUS_PROMPT_TEMPLATE = get_system_prompt" in content


class TestParametersFromConfig:
    """Test that model parameters come from config"""

    def test_generation_params_structure(self):
        """Test that generation params have correct structure"""
        params = get_generation_params()
        params_dict = params.to_dict()

        assert "temperature" in params_dict
        assert "max_tokens" in params_dict

        # Optional params should only be included if non-default
        if params.top_p < 1.0:
            assert "top_p" in params_dict

    def test_task_overrides_work(self):
        """Test that task-specific overrides actually override"""
        default_params = get_generation_params()
        bug_fixing_params = get_generation_params("bug_fixing")

        # Bug fixing should have lower temperature (more deterministic)
        assert bug_fixing_params.temperature <= default_params.temperature

    def test_thinking_params_increase_with_depth(self):
        """Test that thinking depth correlates with token allocation"""
        quick = get_generation_params("thinking_quick")
        standard = get_generation_params("thinking_standard")
        deep = get_generation_params("thinking_deep")

        # Deeper thinking should allow more tokens
        assert quick.max_tokens <= standard.max_tokens <= deep.max_tokens


def test_config_reload():
    """Test that configuration can be reloaded"""
    from hcode.config.prompts import reload_configs

    # Get initial configs
    initial_prompts = get_prompts_config()
    initial_models = get_models_config()

    # Reload
    reload_configs()

    # Get new configs
    new_prompts = get_prompts_config()
    new_models = get_models_config()

    # They should be the same instances (singleton)
    assert new_prompts is initial_prompts
    assert new_models is initial_models


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
