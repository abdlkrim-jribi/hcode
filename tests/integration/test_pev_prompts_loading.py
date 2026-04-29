"""
Integration test for PEV prompts loading from pev_prompts directory.

Verifies all PEV prompts are loaded successfully from the new directory structure.
"""
import pytest
from pathlib import Path

from hcode.config.core_prompts.core.loader import CorePromptLoader, get_prompt_loader


class TestPEVPromptsLoading:
    """Test that all PEV prompts load correctly from pev_prompts directory."""

    def test_loader_singleton(self):
        """Should return same instance."""
        loader1 = CorePromptLoader()
        loader2 = CorePromptLoader()
        loader3 = get_prompt_loader()

        assert loader1 is loader2
        assert loader1 is loader3

    def test_core_prompts_loaded(self):
        """Should load core infrastructure prompts."""
        loader = get_prompt_loader()

        # Core prompts that should exist
        assert loader.get_identity() != ""
        assert loader.get_tool_format() != ""

        # Verify content
        identity = loader.get_identity()
        assert "Hcode" in identity or "hcode" in identity

    def test_pev_planning_prompts_loaded(self):
        """Should load planning phase PEV prompts."""
        loader = get_prompt_loader()

        # Planning mode protocol
        planning_mode = loader.get_planning_mode()
        assert planning_mode != ""
        assert "planning" in planning_mode.lower() or "PLANNING" in planning_mode

        # Task guidance
        task_guidance = loader.get_task_guidance()
        assert task_guidance != ""
        assert "task" in task_guidance.lower()

        # Implementation plan guidance
        impl_plan = loader.get_implementation_plan_guidance()
        assert impl_plan != ""
        assert "implementation" in impl_plan.lower()

    def test_pev_execution_prompts_loaded(self):
        """Should load execution phase PEV prompts."""
        loader = get_prompt_loader()

        # Execution mode
        exec_mode = loader.get_execution_mode()
        assert exec_mode != ""
        assert "execution" in exec_mode.lower() or "EXECUTION" in exec_mode

        # Check if execution_handler exists
        exec_handler = loader._prompts.get("execution_handler", "")
        assert exec_handler != ""
        assert "execution" in exec_handler.lower()

    def test_pev_verification_prompts_loaded(self):
        """Should load verification phase PEV prompts."""
        loader = get_prompt_loader()

        # Verification handler
        verif_handler = loader._prompts.get("verification_handler", "")
        assert verif_handler != ""
        assert "verification" in verif_handler.lower()

        # Walkthrough protocol
        walkthrough = loader.get_walkthrough_protocol()
        assert walkthrough != ""
        assert "walkthrough" in walkthrough.lower()

    def test_pev_init_prompts_loaded(self):
        """Should load init phase PEV prompts."""
        loader = get_prompt_loader()

        # Init analysis prompt
        init_analysis = loader._prompts.get("init_analysis_prompt", "")
        assert init_analysis != ""
        assert "init" in init_analysis.lower() or "analysis" in init_analysis.lower()

    def test_pev_integration_strategy_loaded(self):
        """Should load integration strategy documentation."""
        loader = get_prompt_loader()

        # Integration strategy
        integration = loader._prompts.get("integration_strategy", "")
        assert integration != ""
        assert "integration" in integration.lower() or "strategy" in integration.lower()

    def test_all_pev_prompts_count(self):
        """Should have loaded all expected PEV prompts."""
        loader = get_prompt_loader()

        # Expected PEV prompts from pev_prompts directory
        expected_pev_prompts = [
            "planning_mode",
            "execution_handler",
            "execution_mode",
            "verification_handler",
            "walkthrough",
            "implementation_plan",
            "task",
            "init_analysis_prompt",
            "integration_strategy",
        ]

        # Verify all are loaded
        for prompt_key in expected_pev_prompts:
            assert prompt_key in loader._prompts, f"PEV prompt '{prompt_key}' not loaded"
            assert loader._prompts[prompt_key] != "", f"PEV prompt '{prompt_key}' is empty"

    def test_pev_prompts_directory_structure(self):
        """Should have correct directory structure."""
        prompts_dir = Path(__file__).parent.parent.parent / "src" / "hcode" / "config" / "core_prompts" / "core"
        pev_dir = prompts_dir / "pev_prompts"

        # Verify pev_prompts directory exists
        assert pev_dir.exists(), "pev_prompts directory does not exist"
        assert pev_dir.is_dir(), "pev_prompts is not a directory"

        # Verify expected files exist
        expected_files = [
            "planning_mode.md",
            "execution_handler.md",
            "execution_mode.md",
            "verification_handler.md",
            "walkthrough.md",
            "implementation_plan.md",
            "task.md",
            "init_analysis_prompt.md",
            "integration_strategy.md",
        ]

        for filename in expected_files:
            file_path = pev_dir / filename
            assert file_path.exists(), f"PEV prompt file '{filename}' does not exist"
            assert file_path.is_file(), f"'{filename}' is not a file"

    def test_gpt_oss_120b_optimization_markers(self):
        """Should contain GPT OSS 120B optimization markers in PEV prompts."""
        loader = get_prompt_loader()

        # Check key prompts for GPT OSS 120B markers
        prompts_to_check = [
            ("planning_mode", ["thinking", "output", "evidence"]),
            ("execution_handler", ["thinking", "output", "phase"]),
            ("verification_handler", ["thinking", "output", "protocol"]),
            ("walkthrough", ["thinking", "output", "evidence"]),
        ]

        for prompt_key, expected_markers in prompts_to_check:
            content = loader._prompts.get(prompt_key, "")
            assert content != "", f"{prompt_key} is empty"

            # Check for at least some markers (case insensitive)
            content_lower = content.lower()
            found_markers = [marker for marker in expected_markers if marker in content_lower]
            assert len(found_markers) > 0, f"{prompt_key} missing GPT OSS 120B markers: {expected_markers}"

    def test_prompts_have_evidence_citation_format(self):
        """Should document evidence citation format in prompts."""
        loader = get_prompt_loader()

        # Prompts that should mention evidence citations
        # Note: Some prompts may reference evidence implicitly
        prompts_with_citations = ["verification_handler", "walkthrough"]

        for prompt_key in prompts_with_citations:
            content = loader._prompts.get(prompt_key, "")
            # Check for citation format mention (case insensitive)
            has_citation_format = (
                "file.py:line" in content.lower() or
                "[evidence:" in content.lower() or
                "evidence citation" in content.lower() or
                "evidence" in content.lower()  # At least mentions evidence
            )
            assert has_citation_format, f"{prompt_key} missing evidence references"

    def test_loader_reload_functionality(self):
        """Should be able to reload prompts."""
        loader = get_prompt_loader()

        # Get initial count
        initial_count = len(loader._prompts)
        assert initial_count > 0

        # Reload
        loader.reload()

        # Should have same count after reload
        reloaded_count = len(loader._prompts)
        assert reloaded_count == initial_count
        assert reloaded_count > 10  # Should have at least 10 prompts loaded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
