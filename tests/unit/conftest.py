# conftest.py – shared fixtures for deterministic testing of utils
"""Pytest fixtures that mock filesystem interactions and environment variables.
These fixtures are optional; tests can import and use them or continue to monkeypatch
individually as they already do.
"""
import os
import builtins
import io
import copy
import pytest
from unittest import mock

@pytest.fixture
def mock_isfile(monkeypatch):
    """Patch ``os.path.isfile``.
    By default returns ``True``; the test can override the return value by calling the
    returned ``set_return`` function.
    """
    def _set(return_value: bool = True):
        monkeypatch.setattr(os.path, "isfile", lambda path: return_value)
        return return_value
    return _set

@pytest.fixture
def mock_open(monkeypatch):
    """Patch the built‑in ``open`` with a ``StringIO`` based mock.
    The fixture returns a helper that creates a mock file object with the given
    initial content.
    """
    def _mock(content: str = ""):
        file_obj = io.StringIO(content)
        # Ensure the mock supports the context manager protocol
        file_obj.__enter__ = lambda *args, **kwargs: file_obj
        file_obj.__exit__ = lambda *args, **kwargs: None
        monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: file_obj)
        return file_obj
    return _mock

@pytest.fixture
def mock_makedirs(monkeypatch):
    """Patch ``os.makedirs`` to be a no‑op.
    Returns the mock function so tests can assert calls if desired.
    """
    mock_fn = mock.Mock()
    monkeypatch.setattr(os, "makedirs", mock_fn)
    return mock_fn

@pytest.fixture
def mock_walk(monkeypatch):
    """Patch ``os.walk``.
    By default returns an empty iterator; tests can provide a custom structure.
    """
    def _set(structure=None):
        if structure is None:
            structure = []
        monkeypatch.setattr(os, "walk", lambda *args, **kwargs: structure)
        return structure
    return _set

@pytest.fixture
def mock_environ(monkeypatch):
    """Provide an isolated copy of ``os.environ``.
    Modifications affect only the copy and are discarded after the test.
    """
    env_copy = copy.deepcopy(os.environ)
    monkeypatch.setattr(os, "environ", env_copy)
    return env_copy
