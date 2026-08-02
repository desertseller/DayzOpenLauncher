import os
import sys
import runpy

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(ROOT_DIR, "Source")
sys.path.insert(0, SOURCE_DIR)

if __name__ == "__main__":
    runpy.run_path(os.path.join(SOURCE_DIR, "main.py"), run_name="__main__")
