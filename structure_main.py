"""
Question Structure Main
CLI entry point for post-processing extracted questions

Usage:
    python structure_main.py --input extraction_output --output extraction_output
    python structure_main.py --stats
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pipeline.question_structure_pipeline import QuestionStructurePipeline, run_post_processing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Post-process extracted questions to structured JSON format"
    )
    
    parser.add_argument(
        "--input",
        type=str,
        default="extraction_output",
        help="Input directory containing raw extraction files (default: extraction_output)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="extraction_output",
        help="Output directory for structured questions (default: extraction_output)"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics about processed extractions"
    )
    
    parser.add_argument(
        "--single",
        type=str,
        help="Process a single PDF directory (path)"
    )
    
    args = parser.parse_args()
    
    try:
        pipeline = QuestionStructurePipeline(output_dir=args.output)
        
        if args.stats:
            # Show statistics
            logger.info("📊 Processing Statistics\n" + "="*60)
            stats = pipeline.get_statistics()
            logger.info(f"Total PDFs: {stats['total_pdfs']}")
            logger.info(f"Total Questions: {stats['total_questions']}")
            logger.info(f"\nBy Subject:")
            for subject, count in stats['by_subject'].items():
                logger.info(f"  {subject}: {count}")
            logger.info(f"\nBy Type:")
            for q_type, count in stats['by_type'].items():
                logger.info(f"  {q_type}: {count}")
            
        elif args.single:
            # Process single directory
            pdf_path = Path(args.single)
            if pdf_path.is_dir():
                logger.info(f"Processing: {pdf_path.name}")
                pipeline.process_extraction_directory(pdf_path)
                logger.info("✅ Done!")
            else:
                logger.error(f"Directory not found: {args.single}")
                sys.exit(1)
                
        else:
            # Process all
            logger.info("🔄 Starting question structure post-processing...\n" + "="*60)
            results = pipeline.process_all_extractions()
            logger.info(f"\n✅ Processing complete!")
            logger.info(f"Processed: {results['processed']}")
            logger.info(f"Errors: {results['errors']}")
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
