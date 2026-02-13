import shutil
import tempfile
from pathlib import Path
import pytest

@pytest.fixture(scope="function")
def temp_dir():
    """Create a temporary directory for a test and clean it up afterwards.

    Returns a ``pathlib.Path`` object pointing to the temporary directory.
    The directory is removed recursively after the test finishes.
    """
    dir_path = Path(tempfile.mkdtemp())
    try:
        yield dir_path
    finally:
        # Ensure the temporary directory is removed even if the test fails
        shutil.rmtree(dir_path, ignore_errors=True)
