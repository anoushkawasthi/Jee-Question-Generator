#!/usr/bin/env python3
"""
Wrapper script to run question structure pipeline with proper paths
"""
import sys
import os
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Now import and run
from pipeline.question_structure_pipeline import run_post_processing

if __name__ == "__main__":
    run_post_processing()
