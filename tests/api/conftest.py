"""Configuration file for pytest tests"""
import os
import sys

# Add the parent directory to sys.path to allow importing grasshopper
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))