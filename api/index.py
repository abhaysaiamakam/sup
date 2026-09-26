import os
import sys

# Ensure repository root is on sys.path for importing main.py and app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
