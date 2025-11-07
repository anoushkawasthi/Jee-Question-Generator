"""
Batch Processing Module

Processes multiple PDF files through the extraction pipeline with:
- Sequential or parallel processing modes
- Error handling and recovery
- Progress tracking and logging
- Summary statistics and reports
"""

import os
import logging
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import threading

from pipeline.extraction_pipeline import ExtractionPipeline

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Processes multiple PDF files through the extraction pipeline.
    
    Attributes:
        pdf_directory: Directory containing PDF files
        output_base_dir: Base directory for all output
        schema_path: Path to JSON schema
        max_workers: Maximum parallel workers (for parallel mode)
    """
    
    def __init__(self,
                 pdf_directory: str,
                 output_base_dir: str = "batch_extraction_output",
                 schema_path: str = "schemas/jee_question_schema.json",
                 max_workers: int = 2):
        """Initialize batch processor"""
        self.pdf_directory = Path(pdf_directory)
        self.output_base_dir = Path(output_base_dir)
        self.schema_path = Path(schema_path)
        self.max_workers = max_workers
        
        # Ensure directories exist
        self.pdf_directory.mkdir(parents=True, exist_ok=True)
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            'total_pdfs': 0,
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None,
            'failed_files': []
        }
        
        # Lock for thread-safe stats updates
        self.stats_lock = threading.Lock()
        
        logger.info(f"Batch processor initialized: {self.pdf_directory}")
    
    def discover_pdfs(self) -> List[Path]:
        """
        Discover all PDF files in the directory.
        
        Returns:
            List of PDF file paths
        """
        pdf_files = sorted(list(self.pdf_directory.glob("**/*.pdf")))
        logger.info(f"Discovered {len(pdf_files)} PDF files")
        return pdf_files
    
    def process_single_pdf(self, pdf_path: Path) -> Dict:
        """
        Process a single PDF through the extraction pipeline.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with processing result
        """
        result = {
            'pdf_file': pdf_path.name,
            'status': 'unknown',
            'output_dir': None,
            'questions_extracted': 0,
            'error': None,
            'duration': 0
        }
        
        start_time = datetime.now()
        
        try:
            # Create output directory for this PDF
            output_dir = self.output_base_dir / pdf_path.stem
            
            logger.info(f"Processing: {pdf_path.name}")
            
            # Run extraction pipeline
            pipeline = ExtractionPipeline(
                str(pdf_path),
                output_dir=str(output_dir),
                schema_path=str(self.schema_path)
            )
            
            extraction_data = pipeline.run()
            
            # Update result
            result['status'] = 'success'
            result['output_dir'] = str(output_dir)
            result['questions_extracted'] = len(extraction_data.get('questions', []))
            
            logger.info(f"✓ Completed: {pdf_path.name} "
                       f"({result['questions_extracted']} questions)")
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            logger.error(f"✗ Failed: {pdf_path.name} - {str(e)}")
        
        finally:
            result['duration'] = (datetime.now() - start_time).total_seconds()
        
        return result
    
    def process_sequential(self) -> List[Dict]:
        """
        Process PDFs sequentially (one at a time).
        
        Returns:
            List of processing results
        """
        logger.info("Starting sequential processing...")
        
        pdf_files = self.discover_pdfs()
        self.stats['total_pdfs'] = len(pdf_files)
        self.stats['start_time'] = datetime.now()
        
        results = []
        
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"[{i}/{len(pdf_files)}] Processing {pdf_file.name}")
            
            result = self.process_single_pdf(pdf_file)
            results.append(result)
            
            # Update statistics
            with self.stats_lock:
                self.stats['processed'] += 1
                if result['status'] == 'success':
                    self.stats['successful'] += 1
                else:
                    self.stats['failed'] += 1
                    self.stats['failed_files'].append(pdf_file.name)
        
        self.stats['end_time'] = datetime.now()
        return results
    
    def process_parallel(self) -> List[Dict]:
        """
        Process PDFs in parallel using ThreadPoolExecutor.
        
        Returns:
            List of processing results
        """
        logger.info(f"Starting parallel processing (max_workers={self.max_workers})...")
        
        pdf_files = self.discover_pdfs()
        self.stats['total_pdfs'] = len(pdf_files)
        self.stats['start_time'] = datetime.now()
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.process_single_pdf, pdf_file): pdf_file
                for pdf_file in pdf_files
            }
            
            # Process completed tasks
            for i, future in enumerate(as_completed(futures), 1):
                pdf_file = futures[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update statistics
                    with self.stats_lock:
                        self.stats['processed'] += 1
                        if result['status'] == 'success':
                            self.stats['successful'] += 1
                        else:
                            self.stats['failed'] += 1
                            self.stats['failed_files'].append(pdf_file.name)
                    
                    logger.debug(f"[{i}/{len(pdf_files)}] Completed: {pdf_file.name}")
                    
                except Exception as e:
                    logger.error(f"Error processing {pdf_file.name}: {str(e)}")
                    
                    with self.stats_lock:
                        self.stats['processed'] += 1
                        self.stats['failed'] += 1
                        self.stats['failed_files'].append(pdf_file.name)
        
        self.stats['end_time'] = datetime.now()
        return results
    
    def run(self, parallel: bool = False) -> Dict:
        """
        Execute batch processing.
        
        Args:
            parallel: Whether to use parallel processing
            
        Returns:
            Dictionary with batch processing summary
        """
        logger.info("=" * 70)
        logger.info("JEE Question Extraction - Batch Processing Started")
        logger.info(f"PDF Directory: {self.pdf_directory}")
        logger.info(f"Mode: {'Parallel' if parallel else 'Sequential'}")
        logger.info("=" * 70)
        
        try:
            # Process PDFs
            if parallel:
                results = self.process_parallel()
            else:
                results = self.process_sequential()
            
            # Generate summary report
            summary = self._generate_summary(results)
            
            # Save results
            self._save_batch_results(results, summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            raise
    
    def _generate_summary(self, results: List[Dict]) -> Dict:
        """Generate batch processing summary"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds() \
                   if self.stats['end_time'] and self.stats['start_time'] else 0
        
        total_questions = sum(r.get('questions_extracted', 0) for r in results)
        avg_duration = duration / max(self.stats['processed'], 1)
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'statistics': {
                'total_pdfs': self.stats['total_pdfs'],
                'processed': self.stats['processed'],
                'successful': self.stats['successful'],
                'failed': self.stats['failed'],
                'success_rate': (self.stats['successful'] / max(self.stats['processed'], 1)) * 100,
                'total_duration_seconds': round(duration, 2),
                'avg_duration_per_pdf': round(avg_duration, 2),
                'total_questions_extracted': total_questions
            },
            'failed_files': self.stats['failed_files'],
            'results': results
        }
        
        return summary
    
    def _save_batch_results(self, results: List[Dict], summary: Dict) -> None:
        """Save batch processing results to files"""
        # Save summary report
        summary_file = self.output_base_dir / "batch_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Batch summary saved to: {summary_file}")
        
        # Print summary report
        self._print_summary(summary)
    
    def _print_summary(self, summary: Dict) -> None:
        """Print summary report to logger"""
        stats = summary['statistics']
        
        logger.info("=" * 70)
        logger.info("BATCH PROCESSING SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total PDFs: {stats['total_pdfs']}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Successful: {stats['successful']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Success Rate: {stats['success_rate']:.1f}%")
        logger.info(f"Total Duration: {stats['total_duration_seconds']:.2f}s")
        logger.info(f"Avg per PDF: {stats['avg_duration_per_pdf']:.2f}s")
        logger.info(f"Total Questions Extracted: {stats['total_questions_extracted']}")
        
        if summary['failed_files']:
            logger.info("\nFailed Files:")
            for filename in summary['failed_files']:
                logger.info(f"  - {filename}")
        
        logger.info("=" * 70)


def process_pdf_batch(pdf_directory: str,
                     output_dir: str = "batch_extraction_output",
                     schema_path: str = "schemas/jee_question_schema.json",
                     parallel: bool = False,
                     max_workers: int = 2) -> Dict:
    """
    Convenience function for batch processing.
    
    Args:
        pdf_directory: Directory containing PDFs
        output_dir: Output directory
        schema_path: Path to JSON schema
        parallel: Whether to use parallel processing
        max_workers: Maximum parallel workers
        
    Returns:
        Batch processing summary
    """
    processor = BatchProcessor(
        pdf_directory,
        output_dir,
        schema_path,
        max_workers
    )
    
    return processor.run(parallel=parallel)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example: Run batch processing
    pdf_dir = "data/raw_pdfs/2024"
    
    try:
        summary = process_pdf_batch(pdf_dir, parallel=False)
        print(f"\nBatch processing completed!")
        print(f"Successful: {summary['statistics']['successful']}")
        print(f"Failed: {summary['statistics']['failed']}")
    except Exception as e:
        print(f"Batch processing failed: {str(e)}")
