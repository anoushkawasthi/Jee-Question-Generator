"""
Final Consolidation Main
Creates the final consolidated JSON with answer verification

Usage:
    python consolidate_main.py
    python consolidate_main.py --output data/processed/my_final_questions.json
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from components.answer_merger import create_final_consolidated_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Create final consolidated JSON with answer verification"
    )
    
    parser.add_argument(
        "--extraction-output",
        type=str,
        default="extraction_output",
        help="Path to extraction output directory (default: extraction_output)"
    )
    
    parser.add_argument(
        "--raw-answers",
        type=str,
        default="data/processed/raw_questions.json",
        help="Path to raw answers file (default: data/processed/raw_questions.json)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/jee_questions_final_consolidated.json",
        help="Output file path (default: data/processed/jee_questions_final_consolidated.json)"
    )
    
    args = parser.parse_args()
    
    try:
        logger.info("🎯 Starting final consolidation...")
        output_path = create_final_consolidated_json(
            extraction_output_dir=args.extraction_output,
            raw_answers_path=args.raw_answers,
            output_file=args.output
        )
        
        logger.info(f"\n✅ SUCCESS: {output_path}")
        
        # Verify file exists and show size
        file_size_mb = Path(output_path).stat().st_size / (1024*1024)
        logger.info(f"📦 File size: {file_size_mb:.2f} MB")
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
