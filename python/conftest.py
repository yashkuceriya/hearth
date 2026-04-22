"""Root conftest for pytest. Ensures src is on the path."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
