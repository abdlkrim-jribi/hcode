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
        """Test that planning handler builds proper unified planning prompts."""
        handler = PlanningPhaseHandler(
            artifact_manager=artifact_manager,
            provider=None,
            tool_executor=None,
            context_manager=None,
        )

        # Test the unified planning prompt (5-Phase protocol)
        prompt = handler._build_unified_planning_prompt(complex_context, "file_index_placeholder")

        # Verify thinking protocol is included
        assert "<thinking>" in prompt
        assert "PROBLEM SPACE EXPLORATION" in prompt
        assert "DEEP CODE INVESTIGATION" in prompt
        assert "SOLUTION CRYSTALLIZATION" in prompt

        # Verify key instructions
        assert "Senior Software Architect" in prompt
        assert "5-Phase Iterative Reasoning Protocol" in prompt
        assert "task.md" in prompt
        assert "implementation_plan.md" in prompt

        # Anti-hallucination guidance
        assert "READ" in prompt or "Read" in prompt
        assert "BLOCK" in prompt or "claim must trace back" in prompt

    def test_planning_handler_creates_task_template(self, artifact_manager, complex_context):
        """Test that planning handler provides proper task.md guidance."""
        handler = PlanningPhaseHandler(
            artifact_manager=artifact_manager,
            provider=None,
            tool_executor=None,
            context_manager=None,
        )

        # Test the task template guide
        guide = handler._get_task_template_guide()

        # Verify guidance includes proper formatting instructions
        assert "task" in guide.lower()
        assert "- [ ]" in guide
        assert "<!-- id:" in guide

        # Verify it provides usage guidance
        assert "Task" in guide or "task" in guide
        assert "Format" in guide or "format" in guide

    def test_execution_handler_enhanced_prompt(self, artifact_manager, complex_context):
        """Test that execution handler builds 4-phase protocol prompts."""
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

        # Verify 4-Phase protocol structure
        assert "EXECUTION PHASE" in prompt
        assert "4-Phase Protocol" in prompt
        assert "Phase 0: Task Selection" in prompt or "Phase 0" in prompt

        # Verify execution rules
        assert "READ BEFORE WRITE" in prompt
        assert "ONE TASK AT A TIME" in prompt
        assert "TRACK PROGRESS" in prompt
        assert "USE TOOLS" in prompt

        # Verify plan content is embedded
        assert "String Manipulation Module" in prompt
        assert "reverse_words" in prompt

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
        """Test that planning phase provides guidance for both required artifacts."""
        handler = PlanningPhaseHandler(
            artifact_manager=artifact_manager,
            provider=None,
            tool_executor=None,
            context_manager=None,
        )

        # Verify both guidance methods exist and return content
        task_guide = handler._get_task_template_guide()
        plan_guide = handler._get_plan_template_guide()

        # Verify task guide has essential content
        assert len(task_guide) > 100
        assert "task" in task_guide.lower()
        assert "- [ ]" in task_guide

        # Verify plan guide has essential content
        assert len(plan_guide) > 100
        assert "implementation" in plan_guide.lower() or "plan" in plan_guide.lower()
        assert "[MODIFY]" in plan_guide or "[NEW]" in plan_guide

        # Verify required artifacts are declared
        required = handler.get_required_artifacts()
        assert "task.md" in required
        assert "implementation_plan.md" in required

    def test_base_handler_thinking_instructions(self, artifact_manager, complex_context):
        """Test that planning handler provides proper thinking instructions."""
        handler = PlanningPhaseHandler(
            artifact_manager=artifact_manager,
            provider=None,
            tool_executor=None,
            context_manager=None,
        )

        instructions = handler._get_thinking_instructions()

        # Verify thinking protocol structure (DEEP REASONING PROTOCOL)
        assert "REASONING PROTOCOL" in instructions
        assert "<thinking>" in instructions
        assert "COMPREHENSION" in instructions
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

            # Verify format contains essential guidance
            assert "Task" in guide or "task" in guide
            assert "- [ ]" in guide
            assert "<!-- id:" in guide
            assert "Format" in guide or "format" in guide

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


class TestE2EPEVWorkflow:
    """
    End-to-end tests for full PEV workflow with multi-round AI mocking.

    Task #17: E2E PEV test with real multi-round loop

    These tests validate the entire Planning → Execution → Verification
    workflow with realistic multi-round AI interactions to ensure all
    bug fixes and optimizations work together correctly.
    """

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace with necessary structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directory structure
            workspace = Path(tmpdir)
            (workspace / ".hcode").mkdir(exist_ok=True)
            (workspace / "src").mkdir(exist_ok=True)
            (workspace / "tests").mkdir(exist_ok=True)

            # Create a simple existing file for context
            (workspace / "src" / "__init__.py").write_text("")
            (workspace / "README.md").write_text("# Test Project\n")

            yield str(workspace)

    @pytest.fixture
    def mock_provider(self):
        """Create a mock AI provider that simulates multi-round interactions."""
        from unittest.mock import AsyncMock, MagicMock
        from hcode.providers.base import Message

        provider = AsyncMock()

        def generate_completion_side_effect(*args, **kwargs):
            """Generate realistic multi-round responses based on conversation history."""
            messages = kwargs.get("messages", [])
            if not messages:
                messages = args[0] if args else []

            # Analyze conversation history to determine what to do next
            conversation = []
            for msg in messages:
                if isinstance(msg, Message):
                    conversation.append({"role": msg.role, "content": msg.content})
                elif isinstance(msg, dict):
                    conversation.append(msg)

            # Check what has happened so far by looking at ASSISTANT messages only
            assistant_messages = [msg.get("content", "") for msg in conversation if msg.get("role") == "assistant"]
            task_md_written = any(".hcode/task.md" in content and '"tool": "Write"' in content for content in assistant_messages)
            plan_md_written = any(".hcode/implementation_plan.md" in content and '"tool": "Write"' in content for content in assistant_messages)
            calc_written = any("src/calculator.py" in content and '"tool": "Write"' in content for content in assistant_messages)
            test_written = any("tests/test_calculator.py" in content and '"tool": "Write"' in content for content in assistant_messages)

            # Determine current phase based on the first message
            first_content = conversation[0].get("content", "").lower() if conversation else ""

            # Generate appropriate response based on conversation state
            response_content = ""

            if "5-phase" in first_content or "planning phase" in first_content:
                # PLANNING PHASE
                if not task_md_written:
                    # First round: Create task.md
                    response_content = """<thinking>
I need to create a task breakdown for the calculator module.
</thinking>

<output>
Creating task breakdown
</output>

```json
{"tool": "Write", "arguments": {"TargetFile": ".hcode/task.md", "Content": "# Task: Create Calculator Module\\n\\n## Subtasks\\n\\n- [ ] Create calculator.py with basic operations <!-- id: 0 -->\\n- [ ] Add unit tests <!-- id: 1 -->\\n- [ ] Update README.md <!-- id: 2 -->"}}
```"""
                elif not plan_md_written:
                    # Second round: Create implementation_plan.md
                    response_content = """<thinking>
Now I'll create the detailed implementation plan.
</thinking>

<output>
Creating implementation plan
</output>

```json
{"tool": "Write", "arguments": {"TargetFile": ".hcode/implementation_plan.md", "Content": "# Implementation Plan\\n\\n## Proposed Changes\\n\\n### [NEW] src/calculator.py\\n- Add function for addition\\n- Add function for subtraction\\n- Add type hints and docstrings\\n\\n### [NEW] tests/test_calculator.py\\n- Test addition function\\n- Test subtraction function\\n- Test edge cases\\n\\n### [MODIFY] README.md\\n- Add calculator module documentation\\n\\n## Verification Plan\\n\\n### Automated Tests\\n- Run pytest tests/test_calculator.py\\n- Verify all tests pass\\n\\n### Manual Verification\\n- Import calculator module\\n- Test basic operations"}}
```"""
                else:
                    # Both artifacts created - planning complete
                    response_content = """<thinking>
Both artifacts created successfully.
</thinking>

<output>
Planning complete.
</output>"""

            elif "4-phase" in first_content or "execution phase" in first_content:
                # EXECUTION PHASE
                if not calc_written:
                    # First round: Create calculator.py
                    response_content = """<thinking>
I'll implement the calculator module now.
</thinking>

<output>
Creating calculator module
</output>

```json
{"tool": "Write", "arguments": {"TargetFile": "src/calculator.py", "Content": "def add(a: float, b: float) -> float:\\n    \\\"\\\"\\\"Add two numbers.\\\"\\\"\\\"\\n    return a + b\\n\\ndef subtract(a: float, b: float) -> float:\\n    \\\"\\\"\\\"Subtract b from a.\\\"\\\"\\\"\\n    return a - b"}}
```

```json
{"tool": "Edit", "arguments": {"TargetFile": ".hcode/task.md", "old_string": "- [ ] Create calculator.py with basic operations <!-- id: 0 -->", "new_string": "- [x] Create calculator.py with basic operations <!-- id: 0 -->"}}
```"""
                elif not test_written:
                    # Second round: Add tests
                    response_content = """<thinking>
Now I'll add unit tests.
</thinking>

<output>
Adding unit tests
</output>

```json
{"tool": "Write", "arguments": {"TargetFile": "tests/test_calculator.py", "Content": "import pytest\\nfrom src.calculator import add, subtract\\n\\ndef test_add():\\n    assert add(2, 3) == 5\\n    assert add(-1, 1) == 0\\n\\ndef test_subtract():\\n    assert subtract(5, 3) == 2\\n    assert subtract(0, 0) == 0"}}
```

```json
{"tool": "Edit", "arguments": {"TargetFile": ".hcode/task.md", "old_string": "- [ ] Add unit tests <!-- id: 1 -->", "new_string": "- [x] Add unit tests <!-- id: 1 -->"}}
```"""
                else:
                    # Both files created - execution complete
                    response_content = """<thinking>
Implementation complete.
</thinking>

<output>
Execution complete.
</output>"""

            elif "verification phase" in first_content or "5-phase verification" in first_content:
                # VERIFICATION PHASE
                response_content = """<thinking>
Verification phase. Analyzing implementation quality and test results.
</thinking>

<output>
## Verification Analysis

Implementation quality: HIGH
- All required functions implemented with type hints
- Comprehensive test coverage
- Code follows best practices

Test results: ALL PASSED
- test_add: PASS
- test_subtract: PASS

Verdict: APPROVED
</output>"""
            else:
                # Default fallback
                response_content = "<output>Proceeding</output>"

            # Create mock response
            mock_response = MagicMock()
            mock_response.content = response_content
            return mock_response

        provider.generate_completion.side_effect = generate_completion_side_effect
        return provider

    @pytest.fixture
    def mock_tool_executor(self, temp_workspace):
        """Create a mock tool executor that simulates file operations."""
        from unittest.mock import AsyncMock
        from pathlib import Path

        executor = AsyncMock()
        workspace = Path(temp_workspace)

        async def execute_tool_side_effect(tool_name, max_retries=2, **arguments):
            """Simulate tool execution with realistic results."""
            from hcode.core.execution.tool_executor import ToolResult

            success = True
            output = ""

            if tool_name.lower() in ("read", "readtool"):
                target = arguments.get("TargetFile", "")
                file_path = workspace / target
                if file_path.exists():
                    content = file_path.read_text()
                    output = f"File content:\n{content}"
                else:
                    output = f"File {target} exists"

            elif tool_name.lower() in ("write", "writetool"):
                target = arguments.get("TargetFile", "")
                content = arguments.get("Content", "")
                file_path = workspace / target
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                output = f"Created {target}"

            elif tool_name.lower() in ("edit", "edittool"):
                target = arguments.get("TargetFile", "")
                old_str = arguments.get("old_string", "")
                new_str = arguments.get("new_string", "")
                file_path = workspace / target
                if file_path.exists():
                    content = file_path.read_text()
                    new_content = content.replace(old_str, new_str)
                    file_path.write_text(new_content)
                    output = f"Edited {target}"
                else:
                    success = False
                    output = f"File {target} not found"

            elif tool_name.lower() in ("bash", "bashtool"):
                # Simulate pytest output
                output = "===== test session starts =====\ncollected 2 items\n\ntest_calculator.py::test_add PASSED\ntest_calculator.py::test_subtract PASSED\n\n===== 2 passed in 0.01s ====="

            return ToolResult(success=success, output=output, error=None if success else output)

        executor.execute_tool.side_effect = execute_tool_side_effect
        return executor

    @pytest.mark.asyncio
    async def test_full_pev_workflow_with_multi_round(
        self, temp_workspace, mock_provider, mock_tool_executor
    ):
        """
        Task #17: End-to-end test of full PEV workflow with multi-round AI interaction.

        This test validates:
        1. Planning phase creates task.md and implementation_plan.md through multi-round loop
        2. Execution phase implements the plan with multiple tool calls
        3. Verification phase validates results and creates walkthrough
        4. All artifacts are created correctly
        5. Phase transitions work properly
        6. Multi-round loops execute correctly in each phase
        """
        from hcode.core.phases.planning_handler import PlanningPhaseHandler
        from hcode.core.phases.execution_handler import ExecutionPhaseHandler
        from hcode.core.phases.verification_handler import VerificationPhaseHandler
        from hcode.core.services.artifact_manager import ArtifactManager
        from hcode.core.orchestration.phase_manager import PhaseManager
        from hcode.core.orchestration.agent_orchestrator import AgentOrchestrator
        from hcode.core.classification.task_classifier import TaskClassifier
        from hcode.core.protocols import AgentContext
        from pathlib import Path

        # Setup components
        artifact_manager = ArtifactManager()  # Uses default ".hcode" subdirectory
        task_classifier = TaskClassifier()

        # Create phase handlers with mocked dependencies
        handlers = {
            "planning": PlanningPhaseHandler(
                artifact_manager=artifact_manager,
                provider=mock_provider,
                tool_executor=mock_tool_executor,
                context_manager=None,
            ),
            "execution": ExecutionPhaseHandler(
                artifact_manager=artifact_manager,
                provider=mock_provider,
                tool_executor=mock_tool_executor,
                context_manager=None,
            ),
            "verification": VerificationPhaseHandler(
                artifact_manager=artifact_manager,
                provider=mock_provider,
                tool_executor=mock_tool_executor,
                context_manager=None,
            ),
        }

        # Create phase manager
        phase_manager = PhaseManager(handlers)

        # Create orchestrator
        orchestrator = AgentOrchestrator(
            phase_manager=phase_manager,
            task_classifier=task_classifier,
            working_dir=temp_workspace,
            max_iterations=20,
            console=None,
            debug_mode=False,
        )

        # Execute full PEV workflow
        task = "Create a calculator module with add and subtract functions, including tests"
        session_id = "test-e2e-pev-workflow"

        results = await orchestrator.execute_task(task, session_id)

        # Validate results
        assert results["success"] is True, f"Workflow should succeed. Error: {results.get('error', 'None')}"
        assert results["final_phase"] == "verification", "Should complete at verification phase"
        assert len(results["phase_results"]) >= 3, "Should have results from all 3 phases"

        # Validate artifacts were created
        workspace = Path(temp_workspace)
        hcode_dir = workspace / ".hcode"

        # Check task.md
        task_md = hcode_dir / "task.md"
        assert task_md.exists(), "task.md should be created"
        task_content = task_md.read_text()
        assert "# Task:" in task_content or "Task" in task_content
        assert "<!-- id:" in task_content, "Should have task IDs"

        # Check implementation_plan.md
        plan_md = hcode_dir / "implementation_plan.md"
        assert plan_md.exists(), "implementation_plan.md should be created"
        plan_content = plan_md.read_text()
        assert "[NEW]" in plan_content or "[MODIFY]" in plan_content
        assert "calculator" in plan_content.lower()

        # Check implementation files were created
        calc_file = workspace / "src" / "calculator.py"
        assert calc_file.exists(), "calculator.py should be created"
        calc_content = calc_file.read_text()
        assert "def add" in calc_content
        assert "def subtract" in calc_content

        # Check test file was created
        test_file = workspace / "tests" / "test_calculator.py"
        assert test_file.exists(), "test_calculator.py should be created"
        test_content = test_file.read_text()
        assert "test_add" in test_content
        assert "test_subtract" in test_content

        # Validate multi-round behavior
        # Provider should have been called multiple times per phase
        assert mock_provider.generate_completion.call_count >= 6, \
            f"Should have multiple AI rounds (got {mock_provider.generate_completion.call_count})"

        # Validate tool executor was used
        assert mock_tool_executor.execute_tool.call_count >= 4, \
            f"Should have multiple tool executions (got {mock_tool_executor.execute_tool.call_count})"

    @pytest.mark.asyncio
    async def test_pev_workflow_phase_transitions(self, temp_workspace, mock_provider, mock_tool_executor):
        """
        Test that phase transitions work correctly in PEV workflow.

        Validates:
        - Planning → Execution transition when artifacts are complete
        - Execution → Verification transition when tasks are done
        - Verification marks workflow as complete
        """
        from hcode.core.phases.planning_handler import PlanningPhaseHandler
        from hcode.core.phases.execution_handler import ExecutionPhaseHandler
        from hcode.core.phases.verification_handler import VerificationPhaseHandler
        from hcode.core.services.artifact_manager import ArtifactManager
        from hcode.core.orchestration.phase_manager import PhaseManager
        from hcode.core.protocols import AgentContext

        # Setup
        artifact_manager = ArtifactManager()  # Uses default ".hcode" subdirectory

        handlers = {
            "planning": PlanningPhaseHandler(
                artifact_manager=artifact_manager,
                provider=mock_provider,
                tool_executor=mock_tool_executor,
                context_manager=None,
            ),
            "execution": ExecutionPhaseHandler(
                artifact_manager=artifact_manager,
                provider=mock_provider,
                tool_executor=mock_tool_executor,
                context_manager=None,
            ),
            "verification": VerificationPhaseHandler(
                artifact_manager=artifact_manager,
                provider=mock_provider,
                tool_executor=mock_tool_executor,
                context_manager=None,
            ),
        }

        phase_manager = PhaseManager(handlers)

        # Start in planning
        assert phase_manager.get_current_phase() == "planning"

        # Create context
        context = AgentContext(
            task="Create a simple module",
            session_id="test-transitions",
            working_dir=temp_workspace,
            iteration=0,
        )

        # Execute planning phase
        result = await phase_manager.execute_current_phase(context, loop_controller=None)

        # Should be able to transition to execution
        assert result.can_transition, "Planning should allow transition when artifacts are created"
        transitioned = phase_manager.transition_to_next_phase(context)
        assert transitioned, "Should successfully transition to execution"
        assert phase_manager.get_current_phase() == "execution"

        # Execute execution phase
        result = await phase_manager.execute_current_phase(context, loop_controller=None)

        # Should be able to transition to verification
        assert result.can_transition, "Execution should allow transition when tasks are complete"
        transitioned = phase_manager.transition_to_next_phase(context)
        assert transitioned, "Should successfully transition to verification"
        assert phase_manager.get_current_phase() == "verification"

        # Execute verification phase
        result = await phase_manager.execute_current_phase(context, loop_controller=None)

        # Verification should indicate completion
        assert result.success, "Verification should succeed"

        # Should not be able to transition further (workflow complete)
        transitioned = phase_manager.transition_to_next_phase(context)
        assert not transitioned, "Should not transition after verification"
        assert phase_manager.can_complete(context), "Workflow should be complete"
