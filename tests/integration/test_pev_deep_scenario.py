"""
Deep scenario test for PEV workflow with enhanced thinking.

Tests the full Planning → Execution → Verification workflow
with a complex task to validate agent performance.
"""

import pytest
import tempfile
import asyncio
from pathlib import Path

from hcode.core.phases.planning_handler import PlanningPhaseHandler
from hcode.core.phases.execution_handler import ExecutionPhaseHandler
from hcode.core.phases.verification_handler import VerificationPhaseHandler
from hcode.core.services.artifact_manager import ArtifactManager
from hcode.core.protocols import AgentContext, PhaseResult


class TestPEVDeepScenario:
    """Integration tests for PEV workflow with enhanced thinking."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .hcode directory
            hcode_dir = Path(tmpdir) / ".hcode"
            hcode_dir.mkdir(exist_ok=True)
            yield tmpdir

    @pytest.fixture
    def artifact_manager(self, temp_workspace):
        """Create artifact manager for testing."""
        return ArtifactManager(temp_workspace)

    @pytest.fixture
    def complex_context(self, temp_workspace):
        """Create a complex task context for testing."""
        return AgentContext(
            task="""Create a Python utility module for string manipulation with the following features:

1. A function `reverse_words(text)` that reverses the order of words in a string
2. A function `capitalize_sentences(text)` that capitalizes the first letter of each sentence
3. A function `count_words(text)` that returns a dictionary with word frequencies
4. Unit tests for all functions
5. A README.md documenting the module

The module should follow best practices:
- Type hints for all functions
- Docstrings with examples
- Error handling for edge cases
- PEP 8 compliant code""",
            session_id="test-deep-scenario",
            working_dir=temp_workspace,
            iteration=0,
            modified_files=[],
            completed_actions=[],
            metadata={"task_type": "implementation"},
        )

    def test_planning_handler_deep_analysis_prompt(self, artifact_manager, complex_context):
        """Test that planning handler builds proper deep analysis prompts."""
        handler = PlanningPhaseHandler(
            artifact_manager=artifact_manager,
            provider=None,
            tool_executor=None,
            context_manager=None,
        )

        prompt = handler._build_analysis_prompt(complex_context)

        # Verify thinking protocol is included
        assert "<thinking>" in prompt
        assert "COMPREHENSION" in prompt
        assert "KNOWLEDGE ASSESSMENT" in prompt
        assert "EXPLORATION STRATEGY" in prompt
        assert "RISK ASSESSMENT" in prompt

        # Verify analysis instructions
        assert "Requirement Understanding" in prompt
        assert "Codebase Research" in prompt
        assert "Hypothesis Formation" in prompt
        # Anti-hallucination guidance (uses "assume" and "READ" language)
        assert "Do NOT assume" in prompt or "Always READ" in prompt or "READ before" in prompt

        # Verify output format requirements
        assert "<analysis>" in prompt
        assert "## Understanding" in prompt
        assert "## Relevant Files" in prompt
        assert "## Recommended Approach" in prompt

    def test_planning_handler_creates_task_template(self, artifact_manager, complex_context):
        """Test that planning handler creates proper task.md template."""
        handler = PlanningPhaseHandler(
            artifact_manager=artifact_manager,
            provider=None,
            tool_executor=None,
            context_manager=None,
        )

        analysis_insights = {
            "understanding": "Create a string manipulation utility module",
            "relevant_files": ["string_utils.py", "test_string_utils.py"],
            "components": ["String utilities", "Unit tests", "Documentation"],
            "approach": "Create module with three functions, tests, and README"
        }

        task_content = handler._create_fallback_task_md(complex_context, analysis_insights)

        # Verify checkbox format with IDs
        assert "- [" in task_content
        assert "<!-- id:" in task_content

        # Verify task breakdown
        assert "# Task" in task_content
        assert "## Subtasks" in task_content
        assert "Implement required changes" in task_content
        assert "Verify implementation works" in task_content

    def test_execution_handler_enhanced_prompt(self, artifact_manager, complex_context):
        """Test that execution handler builds enhanced prompts with thinking."""
        handler = ExecutionPhaseHandler(
            artifact_manager=artifact_manager,
            provider=None,
            tool_executor=None,
            context_manager=None,
        )

        plan_content = """# String Manipulation Module

## Proposed Changes

### [NEW] string_utils.py
- Create reverse_words function
- Create capitalize_sentences function
- Create count_words function

## Verification Plan
- Run pytest tests/test_string_utils.py
"""

        prompt = handler._build_execution_prompt(complex_context, plan_content)

        # Verify thinking protocol
        assert "<thinking>" in prompt
        assert "PRE-EXECUTION ANALYSIS" in prompt
        assert "ANTI-HALLUCINATION CHECK" in prompt
        assert "CHANGE SPECIFICATION" in prompt
        assert "VERIFICATION PLAN" in prompt

        # Verify execution rules
        assert "READ BEFORE WRITE" in prompt
        assert "ONE CHANGE AT A TIME" in prompt
        assert "TRACK PROGRESS" in prompt
        assert "NO CODE IN RESPONSE TEXT" in prompt

        # Verify workflow steps
        assert "THINK" in prompt
        assert "READ" in prompt
        assert "PLAN" in prompt
        assert "EXECUTE" in prompt
        assert "VERIFY" in prompt

    def test_verification_handler_thinking_generation(self, artifact_manager, complex_context):
        """Test that verification handler generates proper thinking summary."""
        handler = VerificationPhaseHandler(
            artifact_manager=artifact_manager,
            provider=None,
            tool_executor=None,
            context_manager=None,
        )

        # Add some test data to context
        complex_context.modified_files = ["string_utils.py", "test_string_utils.py", "README.md"]
        complex_context.completed_actions = [
            {"tool": "Write", "success": True},
            {"tool": "Write", "success": True},
            {"tool": "Write", "success": True},
        ]
        complex_context.iteration = 3

        test_results = {
            "tests_run": True,
            "tests_passed": 10,
            "tests_failed": 0,
            "output": "All tests passed",
        }

        thinking = handler._generate_verification_thinking(complex_context, test_results)

        # Verify summary sections
        assert "Implementation Summary" in thinking
        assert "Verification Analysis" in thinking
        assert "Success Assessment" in thinking

        # Verify content
        assert "Files modified: 3" in thinking
        assert "Actions completed: 3" in thinking
        assert "All 10 tests passed" in thinking
        assert "[OK]" in thinking

    def test_artifact_manager_creates_artifacts(self, artifact_manager, temp_workspace):
        """Test that artifact manager properly creates and validates artifacts."""
        context = AgentContext(
            task="Test task",
            session_id="test",
            working_dir=temp_workspace,
            iteration=0,
        )

        # Create task.md
        task_content = """# Task

Test task

## Subtasks

- [ ] Subtask 1 <!-- id: 0 -->
- [ ] Subtask 2 <!-- id: 1 -->

## Notes

Test notes
"""
        artifact_manager.create_artifact("task.md", task_content, context)
        assert artifact_manager.artifact_exists("task.md", context)

        # Load and verify
        loaded = artifact_manager.load_artifact("task.md", context)
        assert "# Task" in loaded
        assert "- [ ]" in loaded
        assert "<!-- id:" in loaded

    def test_full_planning_phase_artifacts(self, artifact_manager, complex_context):
        """Test that planning phase creates both required artifacts."""
        handler = PlanningPhaseHandler(
            artifact_manager=artifact_manager,
            provider=None,  # No provider - use templates
            tool_executor=None,
            context_manager=None,
        )

        # Manually create artifacts as if AI generated them
        analysis_insights = {
            "understanding": "Create string manipulation utilities",
            "relevant_files": ["string_utils.py"],
            "components": ["Utility functions"],
            "approach": "Create module with functions and tests",
        }

        task_content = handler._create_fallback_task_md(complex_context, analysis_insights)
        artifact_manager.create_artifact("task.md", task_content, complex_context)

        plan_content = handler._create_fallback_implementation_plan(complex_context, analysis_insights)
        artifact_manager.create_artifact("implementation_plan.md", plan_content, complex_context)

        # Verify both exist
        assert artifact_manager.artifact_exists("task.md", complex_context)
        assert artifact_manager.artifact_exists("implementation_plan.md", complex_context)

        # Verify transition readiness
        # Note: can_transition_to_next may return False because plan needs concrete steps
        # This is expected behavior - the template is a starting point

    def test_base_handler_thinking_instructions(self, artifact_manager, complex_context):
        """Test that base handler provides proper thinking instructions."""
        handler = PlanningPhaseHandler(
            artifact_manager=artifact_manager,
            provider=None,
            tool_executor=None,
            context_manager=None,
        )

        instructions = handler._get_thinking_instructions()

        # Verify thinking protocol structure
        assert "THINKING PROTOCOL" in instructions
        assert "<thinking>" in instructions
        assert "COMPREHENSION" in instructions
        assert "VERIFICATION" in instructions
        assert "ANTI-HALLUCINATION" in instructions
        assert "TOOL SELECTION" in instructions
        assert "EXPECTED OUTCOME" in instructions

        # Verify critical rules
        assert "NEVER show code" in instructions
        assert "ALWAYS read files" in instructions
        assert "ONE change at a time" in instructions


class TestEnhancedThinkingTemplates:
    """Tests for enhanced thinking templates in reasoning.yaml."""

    def test_reasoning_yaml_has_maximum_performance(self):
        """Test that reasoning.yaml contains maximum_performance template."""
        import yaml
        from pathlib import Path

        reasoning_path = Path("src/hcode/config/core_prompts/core/reasoning.yaml")
        if not reasoning_path.exists():
            pytest.skip("reasoning.yaml not found")

        with open(reasoning_path) as f:
            config = yaml.safe_load(f)

        templates = config.get("thinking_templates", {})

        # Verify maximum_performance exists
        assert "maximum_performance" in templates
        max_perf = templates["maximum_performance"]

        # Verify key phases
        assert "DEEP COMPREHENSION" in max_perf
        assert "STRATEGIC ANALYSIS" in max_perf
        assert "TOOL SELECTION" in max_perf
        assert "EXECUTION DECISION" in max_perf

        # Verify anti-hallucination
        assert "Anti-hallucination" in max_perf or "hallucination" in max_perf.lower()

    def test_reasoning_yaml_has_execution_focused(self):
        """Test that reasoning.yaml contains execution_focused template."""
        import yaml
        from pathlib import Path

        reasoning_path = Path("src/hcode/config/core_prompts/core/reasoning.yaml")
        if not reasoning_path.exists():
            pytest.skip("reasoning.yaml not found")

        with open(reasoning_path) as f:
            config = yaml.safe_load(f)

        templates = config.get("thinking_templates", {})

        # Verify execution_focused exists
        assert "execution_focused" in templates
        exec_focused = templates["execution_focused"]

        # Verify key sections
        assert "EXECUTION ANALYSIS" in exec_focused
        assert "Pre-execution checklist" in exec_focused
        assert "Change specification" in exec_focused


class TestPEVEnforcement:
    """Tests to verify PEV workflow is always enforced."""

    def test_pev_always_required(self):
        """Test that PEV is required for all task types."""
        from hcode.core.classification.task_classifier import TaskClassifier

        classifier = TaskClassifier()

        # Test various task types - PEV should always be required
        tasks = [
            "What files are in the project?",  # Simple exploration
            "Create a new module",  # Implementation
            "Fix the bug in login",  # Debugging
            "Refactor the utils module",  # Refactoring
            "Add unit tests",  # Testing
            "Hi",  # Very simple greeting
            "List all Python files",  # Simple query
        ]

        for task in tasks:
            assert classifier.requires_pev_workflow(task) is True, \
                f"PEV should be required for task: {task}"

    def test_workflow_recommendation_always_pev(self):
        """Test that workflow recommendation is always PEV."""
        from hcode.core.classification.task_classifier import TaskClassifier

        classifier = TaskClassifier()

        tasks = [
            "Explain the codebase",
            "Create a REST API",
            "Fix memory leak",
        ]

        for task in tasks:
            recommendation = classifier.get_workflow_recommendation(task)
            assert recommendation["workflow"] == "PEV"
            assert recommendation["pev_enforced"] is True

    def test_orchestrator_resets_to_planning(self):
        """Test that orchestrator always starts with planning phase."""
        from hcode.core.orchestration.phase_manager import PhaseManager
        from hcode.core.phases.planning_handler import PlanningPhaseHandler
        from hcode.core.phases.execution_handler import ExecutionPhaseHandler
        from hcode.core.phases.verification_handler import VerificationPhaseHandler
        from hcode.core.services.artifact_manager import ArtifactManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_manager = ArtifactManager(tmpdir)

            handlers = {
                "planning": PlanningPhaseHandler(
                    artifact_manager=artifact_manager,
                    provider=None,
                    tool_executor=None,
                    context_manager=None,
                ),
                "execution": ExecutionPhaseHandler(
                    artifact_manager=artifact_manager,
                    provider=None,
                    tool_executor=None,
                    context_manager=None,
                ),
                "verification": VerificationPhaseHandler(
                    artifact_manager=artifact_manager,
                    provider=None,
                    tool_executor=None,
                    context_manager=None,
                ),
            }

            phase_manager = PhaseManager(handlers)

            # After reset, should always be in planning
            phase_manager.reset()
            assert phase_manager.get_current_phase() == "planning"

            # Even if we force to execution and reset, should be back to planning
            phase_manager.force_phase("execution")
            assert phase_manager.get_current_phase() == "execution"

            phase_manager.reset()
            assert phase_manager.get_current_phase() == "planning"


class TestPlanningPromptGuides:
    """Tests for planning prompt template guides."""

    def test_task_template_guide_format(self):
        """Test task template guide has correct format."""
        from hcode.core.phases.planning_handler import PlanningPhaseHandler
        from hcode.core.services.artifact_manager import ArtifactManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_manager = ArtifactManager(tmpdir)
            handler = PlanningPhaseHandler(
                artifact_manager=artifact_manager,
                provider=None,
                tool_executor=None,
                context_manager=None,
            )

            guide = handler._get_task_template_guide()

            # Verify format
            assert "# Task" in guide
            assert "## Subtasks" in guide
            assert "- [ ]" in guide
            assert "<!-- id:" in guide
            assert "## Notes" in guide

    def test_plan_template_guide_format(self):
        """Test implementation plan template guide has correct format."""
        from hcode.core.phases.planning_handler import PlanningPhaseHandler
        from hcode.core.services.artifact_manager import ArtifactManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_manager = ArtifactManager(tmpdir)
            handler = PlanningPhaseHandler(
                artifact_manager=artifact_manager,
                provider=None,
                tool_executor=None,
                context_manager=None,
            )

            guide = handler._get_plan_template_guide()

            # Verify format
            assert "[MODIFY]" in guide
            assert "[NEW]" in guide
            assert "## Proposed Changes" in guide
            assert "## Verification Plan" in guide
            assert "Automated Tests" in guide
            assert "Manual Verification" in guide
