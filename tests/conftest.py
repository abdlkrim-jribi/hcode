import os
import sys

# Ensure required API keys are set for tests
os.environ.setdefault("OPENAI_API_KEY", "dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")

# Add the src directory to PYTHONPATH so that imports work correctly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import the Tester class from the correct package location
# Import the Tester class from the correct package location
from hcode._impl.tester import Tester
