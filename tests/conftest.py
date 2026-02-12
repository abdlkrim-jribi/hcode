import pytest
import os
import builtins
from hcode.utils import config, file_utils, formatting, validators

@pytest.fixture
def utils():
    """Provide a dictionary of utils modules for tests to import via the package.
    Each test can request this fixture to access the required symbols.
    """
    return {
        "config": config,
        "file_utils": file_utils,
        "formatting": formatting,
        "validators": validators,
    }

@pytest.fixture
def mock_fs(monkeypatch):
    """Patch filesystem‑related functions and environment variables for deterministic tests.
    - os.path.isfile returns True for any path unless overridden in a test.
    - builtins.open is replaced with a simple in‑memory file using io.StringIO.
    - os.makedirs becomes a no‑op.
    - os.walk returns an empty iterator by default.
    - os.environ is cleared and can be populated per‑test.
    """
    # os.path.isfile
    monkeypatch.setattr(os.path, "isfile", lambda path: True)
    # builtins.open – simple wrapper returning StringIO for read/write
    def fake_open(file, mode="r", encoding=None):
        if "r" in mode:
            # Return empty content for reads unless test overrides via monkeypatch
            return io.StringIO("")
        else:
            # For writes, capture written data in a dict for inspection if needed
            return io.StringIO()
    monkeypatch.setattr(builtins, "open", fake_open)
    # os.makedirs – no operation
    monkeypatch.setattr(os, "makedirs", lambda *args, **kwargs: None)
    # os.walk – empty by default
    monkeypatch.setattr(os, "walk", lambda root: [])
    # os.environ – start with empty dict
    monkeypatch.setattr(os, "environ", {}, raising=False)
