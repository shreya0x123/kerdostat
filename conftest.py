"""
Root conftest.py — ensures the project root is on sys.path
so that `from ml.indicators...`, `from data.loaders...`, etc.
resolve correctly when running pytest from any directory.
"""

import os
import sys

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
