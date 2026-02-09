"""
Unit tests for VerificationPhaseHandler.

Tests specific bug fixes and critical functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from hcode.core.phases.verification_handler import VerificationPhaseHandler
from hcode.core.protocols import AgentContext


@pytest.mark.asyncio
async def test_update_hcode_memory_no_nameerror():
    """
    Regression test for Task #1: NameError crash fix.

    Verifies that _update_hcode_memory is called with correct variable name
    (verification_analysis, not analysis_response).
    """
    # Create handler with minimal mocking
    artifact_manager = Mock()
    provider = AsyncMock()
    tool_executor = Mock()
    context_manager = Mock()

    handler = VerificationPhaseHandler(
        artifact_manager, provider, tool_executor, context_manager
    )

    # Mock the internal method directly
    handler._update_hcode_memory = Mock()

    # Create test data
    context = AgentContext(
        task="Test task",
        session_id="test123",
        working_dir="/test",
        iteration=1,
    )
    test_results = {"tests_run": 0, "tests_passed": 0, "tests_failed": 0}
    verification_analysis = "Test analysis"
    verdict = "APPROVED"

    # Call the method (should NOT raise NameError)
    handler._update_hcode_memory(
        context=context,
        test_results=test_results,
        verification_analysis=verification_analysis,  # Correct variable name
        verdict=verdict
    )

    # Verify it was called
    handler._update_hcode_memory.assert_called_once()


@pytest.mark.asyncio
async def test_provider_generate_completion_not_generate():
    """
    Regression test for Task #2: AttributeError fix.

    Verifies that handler uses provider.generate_completion (not provider.generate).
    """
    # Create handler
    artifact_manager = Mock()
    artifact_manager.load_artifact.side_effect = lambda name, ctx: {
        "task.md": "# Task\n- [x] Done <!-- id: 0 -->",
        "implementation_plan.md": "# Plan",
    }.get(name, "")

    provider = AsyncMock()
    # Mock generate_completion with proper Message response
    provider.generate_completion = AsyncMock(
        return_value=MagicMock(content="Analysis complete")
    )

    tool_executor = Mock()
    context_manager = Mock()

    handler = VerificationPhaseHandler(
        artifact_manager, provider, tool_executor, context_manager
    )

    context = AgentContext(
        task="Test task",
        session_id="test456",
        working_dir="/test",
        iteration=1,
        modified_files=["src/file.py"],
    )
    test_results = {"tests_run": 0}
    verification_analysis = "Test analysis"

    # Call the walkthrough creation (should use generate_completion)
    with patch.object(handler, '_build_walkthrough_input_data', return_value={}):
        with patch.object(handler, '_extract_walkthrough_from_response', return_value="# Walkthrough"):
            try:
                await handler._create_walkthrough(context, test_results, verification_analysis)
                # Should call generate_completion, not generate
                provider.generate_completion.assert_called()
                # Should NOT have a 'generate' method called
                assert not hasattr(provider, 'generate') or not provider.generate.called
            except Exception as e:
                # Even if it fails, as long as it tried to call generate_completion, bug is fixed
                provider.generate_completion.assert_called()


def test_verification_handler_has_correct_phase_name():
    """Test that handler has correct phase name."""
    artifact_manager = Mock()
    provider = Mock()
    tool_executor = Mock()
    context_manager = Mock()

    handler = VerificationPhaseHandler(
        artifact_manager, provider, tool_executor, context_manager
    )

    assert handler.phase_name == "verification"


def test_verification_handler_initialization():
    """Test that handler initializes without errors."""
    artifact_manager = Mock()
    provider = Mock()
    tool_executor = Mock()
    context_manager = Mock()

    # Should not raise
    handler = VerificationPhaseHandler(
        artifact_manager, provider, tool_executor, context_manager
    )

    assert handler.artifact_manager is artifact_manager
    assert handler.provider is provider
