"""
Main Entry Point for JEE Question PDF Extraction Pipeline

This script provides a CLI interface for running the extraction pipeline
on single PDFs or batches of PDFs.

Usage:
    python extraction_main.py --pdf <path> --output <dir>
    python extraction_main.py --batch <dir> --output <dir> --parallel
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from extraction_config import get_config
from pipeline.extraction_pipeline import ExtractionPipeline, run_extraction_pipeline
from pipeline.batch_processor import BatchProcessor, process_pdf_batch


def setup_logging(log_dir: str, log_level: str = 'INFO') -> None:
    """
    Setup logging configuration
    
    Args:
        log_dir: Directory to save log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    log_file = log_path / f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_file}")


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description='JEE Question PDF Extraction Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract single PDF
  python extraction_main.py --pdf data/sample.pdf --output output/
  
  # Batch processing (sequential)
  python extraction_main.py --batch data/pdfs/ --output output/
  
  # Batch processing (parallel with 4 workers)
  python extraction_main.py --batch data/pdfs/ --output output/ --parallel --workers 4
  
  # With custom schema
  python extraction_main.py --pdf data/sample.pdf --schema schemas/custom_schema.json
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--pdf',
        type=str,
        help='Path to a single PDF file to extract'
    )
    mode_group.add_argument(
        '--batch',
        type=str,
        help='Path to directory containing PDF files for batch processing'
    )
    
    # Output options
    parser.add_argument(
        '--output',
        type=str,
        default='extraction_output',
        help='Output directory (default: extraction_output)'
    )
    
    # Schema
    parser.add_argument(
        '--schema',
        type=str,
        default='schemas/jee_question_schema.json',
        help='Path to JSON schema file (default: schemas/jee_question_schema.json)'
    )
    
    # Batch options
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Use parallel processing for batch mode'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=2,
        help='Number of parallel workers (default: 2)'
    )
    
    # Other options
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='Directory for log files (default: logs)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration JSON file'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_dir, args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = get_config()
        logger.info("Configuration loaded")
        logger.debug(f"Configuration: {config}")
        
        # Verify schema exists
        if not Path(args.schema).exists():
            logger.error(f"Schema file not found: {args.schema}")
            return 1
        
        if args.pdf:
            # Single PDF extraction
            logger.info("=" * 70)
            logger.info("Single PDF Extraction Mode")
            logger.info("=" * 70)
            
            pdf_path = Path(args.pdf)
            if not pdf_path.exists():
                logger.error(f"PDF file not found: {args.pdf}")
                return 1
            
            try:
                logger.info(f"Extracting: {pdf_path.name}")
                results = run_extraction_pipeline(
                    pdf_path=str(pdf_path),
                    output_dir=args.output,
                    schema_path=args.schema
                )
                
                logger.info("=" * 70)
                logger.info("Extraction Completed Successfully")
                logger.info(f"Questions extracted: {len(results.get('questions', []))}")
                logger.info(f"Output directory: {args.output}")
                logger.info("=" * 70)
                
                return 0
                
            except Exception as e:
                logger.error(f"Extraction failed: {str(e)}", exc_info=True)
                return 1
        
        elif args.batch:
            # Batch processing
            logger.info("=" * 70)
            logger.info("Batch Processing Mode")
            logger.info(f"Parallel: {args.parallel}")
            if args.parallel:
                logger.info(f"Workers: {args.workers}")
            logger.info("=" * 70)
            
            batch_dir = Path(args.batch)
            if not batch_dir.exists():
                logger.error(f"Batch directory not found: {args.batch}")
                return 1
            
            try:
                summary = process_pdf_batch(
                    pdf_directory=str(batch_dir),
                    output_dir=args.output,
                    schema_path=args.schema,
                    parallel=args.parallel,
                    max_workers=args.workers
                )
                
                logger.info("=" * 70)
                logger.info("Batch Processing Completed")
                stats = summary['statistics']
                logger.info(f"Total PDFs: {stats['total_pdfs']}")
                logger.info(f"Successful: {stats['successful']}")
                logger.info(f"Failed: {stats['failed']}")
                logger.info(f"Success Rate: {stats['success_rate']:.1f}%")
                logger.info(f"Total Questions: {stats['total_questions_extracted']}")
                logger.info(f"Output directory: {args.output}")
                logger.info("=" * 70)
                
                # Print summary to console
                print("\n" + "=" * 70)
                print("BATCH PROCESSING SUMMARY")
                print("=" * 70)
                print(f"Total PDFs: {stats['total_pdfs']}")
                print(f"Successful: {stats['successful']}")
                print(f"Failed: {stats['failed']}")
                print(f"Success Rate: {stats['success_rate']:.1f}%")
                print(f"Total Duration: {stats['total_duration_seconds']:.2f}s")
                print(f"Total Questions: {stats['total_questions_extracted']}")
                print("=" * 70 + "\n")
                
                return 0 if stats['failed'] == 0 else 1
                
            except Exception as e:
                logger.error(f"Batch processing failed: {str(e)}", exc_info=True)
                return 1
        
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
