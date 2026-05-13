"""
Unit tests for CorePromptLoader.

Tests the centralized prompt loading system.
"""

import pytest
from hcode.config.core_prompts.core import CorePromptLoader, get_prompt_loader


class TestCorePromptLoader:
    """Tests for CorePromptLoader."""

    @pytest.fixture
    def loader(self):
        """Create a fresh loader instance."""
        # Clear singleton for testing
        CorePromptLoader._instance = None
        return CorePromptLoader()

    def test_singleton_pattern(self, loader):
        """Test that CorePromptLoader is a singleton."""
        loader2 = CorePromptLoader()
        assert loader is loader2

    def test_get_prompt_loader_function(self):
        """Test the global get_prompt_loader function."""
        loader1 = get_prompt_loader()
        loader2 = get_prompt_loader()
        assert loader1 is loader2

    def test_get_system_prompt(self, loader):
        """Test getting system prompts."""
        prompt = loader.get_system_prompt("default")
        assert "Hcode" in prompt or "AI" in prompt
        assert len(prompt) > 50

    def test_get_phase_prompt_planning(self, loader):
        """Test getting planning phase prompt."""
        prompt = loader.get_phase_prompt("planning", "instruction")
        assert "PLANNING" in prompt
        assert "task.md" in prompt
        assert "implementation_plan.md" in prompt

    def test_get_phase_prompt_execution(self, loader):
        """Test getting execution phase prompt."""
        prompt = loader.get_phase_prompt("execution", "instruction")
        assert "EXECUTION" in prompt
        assert "implement" in prompt.lower()

    def test_get_phase_prompt_verification(self, loader):
        """Test getting verification phase prompt."""
        prompt = loader.get_phase_prompt("verification", "workflow")
        assert "VERIFICATION" in prompt
        assert "test" in prompt.lower()

    def test_get_thinking_template_quick(self, loader):
        """Test getting quick thinking template."""
        template = loader.get_thinking_template("quick")
        assert "understand" in template.lower()
        assert "tool" in template.lower()

    def test_get_thinking_template_standard(self, loader):
        """Test getting standard thinking template."""
        template = loader.get_thinking_template("standard")
        assert "breaking this down" in template.lower() or "understand" in template.lower()
        assert "context" in template.lower()
        assert "approach" in template.lower()

    def test_get_thinking_template_deep(self, loader):
        """Test getting deep thinking template."""
        template = loader.get_thinking_template("deep")
        assert "analyze" in template.lower()
        assert "hypothesis" in template.lower()
        assert "alternative" in template.lower()
        assert "verify" in template.lower()

    def test_get_output_format(self, loader):
        """Test getting output format instructions."""
        output_format = loader.get_output_format("default")
        assert "output_format" in output_format.lower() or "tool" in output_format.lower()

    def test_get_continuation_prompt(self, loader):
        """Test getting continuation prompts."""
        prompt = loader.get_continuation_prompt("default")
        # Prompt may have "continue" or "proceed" or similar
        assert "proceed" in prompt.lower() or "continue" in prompt.lower() or "next" in prompt.lower()

    def test_get_template_task_md(self, loader):
        """Test getting task.md guidance."""
        # Note: task.md is not template-based, it uses guidance
        guidance = loader.get_task_guidance()
        assert "task" in guidance.lower()
        # Check for format guidance
        assert "- [ ]" in guidance
        assert "<!-- id:" in guidance

    def test_get_template_implementation_plan(self, loader):
        """Test getting implementation_plan.md guidance."""
        # Note: implementation_plan.md is not template-based, it uses guidance
        guidance = loader.get_implementation_plan_guidance()
        assert "implementation" in guidance.lower() or "plan" in guidance.lower()
        # Check for plan structure guidance
        assert "[MODIFY]" in guidance or "[NEW]" in guidance
        assert "test" in guidance.lower() or "verif" in guidance.lower()

    def test_get_template_walkthrough(self, loader):
        """Test getting walkthrough.md template."""
        template = loader.get_template("walkthrough_md")
        assert "Walkthrough" in template
        assert "modified_files_section" in template
        assert "test_section" in template

    def test_build_planning_prompt(self, loader):
        """Test building planning prompt with task substitution."""
        task = "Fix the authentication bug"
        prompt = loader.build_planning_prompt(task=task)
        assert task in prompt
        assert "PLANNING" in prompt

    def test_build_execution_prompt(self, loader):
        """Test building execution prompt with context."""
        prompt = loader.build_execution_prompt(
            plan_content="Step 1: Fix bug\nStep 2: Test",
            modified_files_count=3,
            completed_actions_count=5,
            iteration=2,
        )
        assert "EXECUTION" in prompt
        assert "3" in prompt  # modified files count
        assert "5" in prompt  # completed actions count

    def test_build_task_md(self, loader):
        """Test task.md guidance is available."""
        # Note: task.md is not built from a template, the AI uses guidance
        guidance = loader.get_task_guidance()
        assert len(guidance) > 0
        assert "task" in guidance.lower()
        assert "- [ ]" in guidance

    def test_build_walkthrough_md(self, loader):
        """Test building walkthrough.md content."""
        content = loader.build_walkthrough_md(
            task="Fix bug",
            modified_files_section="- file1.py\n- file2.py",
            changes_details="Updated logic",
            test_section="All tests pass",
        )
        assert "Fix bug" in content
        assert "file1.py" in content
        assert "All tests pass" in content

    def test_build_user_context(self, loader):
        """Test building user context."""
        context = loader.build_user_context(
            os_name="Windows",
            root_dir="D:/projects/myproject",
        )
        assert "Windows" in context
        assert "D:/projects/myproject" in context

    def test_build_refinement_prompt(self, loader):
        """Test building refinement prompt."""
        prompt = loader.build_refinement_prompt(
            original_reasoning="I thought X was the issue",
            feedback="X was not the root cause",
            outcome="Error still occurs",
        )
        assert "refinement" in prompt.lower() or "refine" in prompt.lower()
        assert "I thought X was the issue" in prompt
        assert "X was not the root cause" in prompt

    def test_list_prompts(self, loader):
        """Test listing all available prompts."""
        prompts = loader.list_prompts()
        assert len(prompts) > 0
        # Should have phase prompts
        assert any("planning" in p for p in prompts)
        assert any("execution" in p for p in prompts)

    def test_list_prompts_by_category(self, loader):
        """Test listing prompts filtered by category."""
        phase_prompts = loader.list_prompts(category="phases")
        assert all("phases" in p for p in phase_prompts)

    def test_get_raw_prompt(self, loader):
        """Test getting raw prompt without substitution."""
        raw = loader.get_raw("phases.planning.instruction")
        # Should have placeholder
        assert "{task}" in raw

    def test_format_prompt_alias(self, loader):
        """Test format_prompt as alias for get with kwargs."""
        prompt = loader.format_prompt(
            "phases.planning.instruction",
            task="My test task"
        )
        assert "My test task" in prompt

    def test_invalid_path_raises_error(self, loader):
        """Test that invalid paths raise KeyError."""
        with pytest.raises(KeyError):
            loader.get("nonexistent.path.here")

    def test_invalid_category_raises_error(self, loader):
        """Test that invalid categories raise KeyError."""
        with pytest.raises(KeyError):
            loader.get_category("nonexistent_category")

    def test_reload_prompts(self, loader):
        """Test reloading prompts from files."""
        # Should not raise
        loader.reload()
        # Prompts should still be accessible
        prompt = loader.get_system_prompt("default")
        assert len(prompt) > 0


class TestPromptIntegration:
    """Integration tests for prompt loading in core components."""

    def test_planning_handler_uses_loader(self):
        """Test that PlanningPhaseHandler uses CorePromptLoader."""
        from hcode.core.phases.planning_handler import PlanningPhaseHandler
        from hcode.core.services.artifact_manager import ArtifactManager
        from hcode.core.protocols import AgentContext
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_manager = ArtifactManager(tmpdir)
            handler = PlanningPhaseHandler(
                artifact_manager=artifact_manager,
                provider=None,
                tool_executor=None,
                context_manager=None,
            )

            context = AgentContext(
                task="Test task",
                session_id="test",
                working_dir=tmpdir,
                iteration=0,
            )

            # Build unified planning prompt should work
            prompt = handler._build_unified_planning_prompt(context)
            assert "Test task" in prompt
            assert "PLANNING" in prompt or "5-Phase" in prompt

    def test_execution_handler_uses_loader(self):
        """Test that ExecutionPhaseHandler builds execution prompt."""
        from hcode.core.phases.execution_handler import ExecutionPhaseHandler
        from hcode.core.services.artifact_manager import ArtifactManager
        from hcode.core.protocols import AgentContext
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_manager = ArtifactManager(tmpdir)
            handler = ExecutionPhaseHandler(
                artifact_manager=artifact_manager,
                provider=None,
                tool_executor=None,
                context_manager=None,
            )

            context = AgentContext(
                task="Test task",
                session_id="test",
                working_dir=tmpdir,
                iteration=1,
                modified_files=["file1.py"],
                completed_actions=[{"tool": "Read"}],
            )

            # Build prompt should work
            prompt = handler._build_execution_prompt(context, "Step 1: Do X")
            assert "EXECUTION" in prompt
            assert "Step 1: Do X" in prompt
