"""Moved to `bblit/game/montage.py`.

This file only keeps `import montage` working for the reverse engineering
project (`..\\BBLIT_Decomp_Ale`), which puts this folder on its path: it
makes this name the module itself, private names included.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bblit"))
sys.modules[__name__] = importlib.import_module("game.montage")
