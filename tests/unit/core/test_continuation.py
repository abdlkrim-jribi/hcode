"""Tests for continuation system — ContinuationManager and ContextWindowManager."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture()
def mock_continuation_config():
    cfg = MagicMock()
    cfg.max_continuations = 20
    cfg.max_total_tokens = 200000
    with patch("hcode.config.prompts.get_models_config") as mock_fn:
        mock_fn.return_value.get_continuation_config.return_value = cfg
        yield cfg


def _make_manager(mock_cfg, max_continuations=20, max_total_tokens=200000):
    from hcode.core.response.continuation import ContinuationManager
    return ContinuationManager(max_continuations=max_continuations, max_total_tokens=max_total_tokens)


def test_should_continue_on_length(mock_continuation_config):
    manager = _make_manager(mock_continuation_config)
    assert manager.should_continue("length", "any text") is True


def test_should_continue_stop_complete_sentence(mock_continuation_config):
    manager = _make_manager(mock_continuation_config)
    assert manager.should_continue("stop", "This is complete.") is False
    assert manager.should_continue("stop", "Done!") is False


def test_should_continue_unclosed_code_block(mock_continuation_config):
    manager = _make_manager(mock_continuation_config)
    assert manager.should_continue("stop", "```python\ndef foo():") is True


def test_should_continue_closed_code_block(mock_continuation_config):
    manager = _make_manager(mock_continuation_config)
    assert manager.should_continue("stop", "```python\ndef foo():\n    pass\n```") is False


def test_should_continue_truncation_patterns(mock_continuation_config):
    manager = _make_manager(mock_continuation_config)
    assert manager.should_continue("stop", "The function takes a") is True
    assert manager.should_continue("stop", "We need to and") is True
    assert manager.should_continue("stop", "Let me explain:") is True


def test_continuation_manager_attributes(mock_continuation_config):
    manager = _make_manager(mock_continuation_config, max_continuations=5, max_total_tokens=100000)
    assert manager.max_continuations == 5
    assert manager.max_total_tokens == 100000


def test_context_window_manager_defaults():
    from hcode.core.response.continuation import ContextWindowManager
    manager = ContextWindowManager()
    assert manager.max_context_tokens == 128000
    assert manager.reserve_output_tokens == 4096
    assert manager.summarization_threshold == 0.8


def test_context_window_manager_custom_values():
    from hcode.core.response.continuation import ContextWindowManager
    manager = ContextWindowManager(
        max_context_tokens=50000,
        reserve_output_tokens=2000,
        summarization_threshold=0.9,
    )
    assert manager.max_context_tokens == 50000
    assert manager.reserve_output_tokens == 2000
    assert manager.summarization_threshold == 0.9
