"""
Question Structure Pipeline
Post-processes raw extracted JSON files to create structured question JSON files
Following the jee_question_schema.json format
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from components.question_parser import QuestionParser

logger = logging.getLogger(__name__)


class QuestionStructurePipeline:
    """
    Post-processing pipeline that converts raw extracted JSON
    to structured question JSON files
    
    Input:  01_text_images_extraction.json (raw text blocks and images)
    Output: 02_structured_questions.json (parsed questions per schema)
    """

    def __init__(self, output_dir: str = "extraction_output"):
        self.output_dir = output_dir
        self.parser = QuestionParser()
        
    def process_all_extractions(self):
        """
        Process all extracted PDFs to create structured question files
        
        Walks through extraction_output/ and processes each 01_text_images_extraction.json
        """
        processed_count = 0
        error_count = 0
        
        logger.info("Starting question structure post-processing...")
        
        # Find all extraction directories
        output_path = Path(self.output_dir)
        if not output_path.exists():
            logger.error(f"Output directory not found: {self.output_dir}")
            return
        
        # Process each PDF's extraction
        for pdf_dir in sorted(output_path.iterdir()):
            if not pdf_dir.is_dir():
                continue
            
            try:
                self.process_extraction_directory(pdf_dir)
                processed_count += 1
                logger.info(f"✅ Processed: {pdf_dir.name}")
                
            except Exception as e:
                error_count += 1
                logger.error(f"❌ Error processing {pdf_dir.name}: {str(e)}")
                continue
        
        logger.info(f"\n📊 Summary: {processed_count} processed, {error_count} errors")
        return {
            "processed": processed_count,
            "errors": error_count,
            "timestamp": datetime.now().isoformat()
        }

    def process_extraction_directory(self, pdf_dir: Path):
        """
        Process a single PDF's extraction directory
        
        Reads 01_text_images_extraction.json and creates 02_structured_questions.json
        """
        # Read raw extraction
        raw_file = pdf_dir / "01_text_images_extraction.json"
        if not raw_file.exists():
            logger.warning(f"No extraction file found in {pdf_dir.name}")
            return
        
        logger.debug(f"Processing: {raw_file}")
        
        with open(raw_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Parse questions from raw data
        structured_paper = self.parser.parse_paper(raw_data)
        
        # Save structured questions
        output_file = pdf_dir / "02_structured_questions.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(structured_paper, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Created: {output_file}")
        logger.info(f"Questions parsed: {len(structured_paper.get('questions', []))}")
        
        # Also save individual question files for easy access
        self._save_individual_questions(pdf_dir, structured_paper)
        
    def _save_individual_questions(self, pdf_dir: Path, structured_paper: Dict):
        """
        Save each question as individual JSON file
        
        Useful for database import, vector embedding, etc.
        """
        questions = structured_paper.get("questions", [])
        
        # Create subdirectory for individual questions
        questions_dir = pdf_dir / "questions"
        questions_dir.mkdir(exist_ok=True)
        
        for question in questions:
            q_id = question["question_id"]
            q_file = questions_dir / f"{q_id}.json"
            
            with open(q_file, 'w', encoding='utf-8') as f:
                json.dump(question, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Saved {len(questions)} individual question files")

    def get_statistics(self) -> Dict:
        """Get statistics about processed extractions"""
        stats = {
            "total_pdfs": 0,
            "total_questions": 0,
            "by_subject": {},
            "by_type": {},
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        output_path = Path(self.output_dir)
        
        for pdf_dir in output_path.iterdir():
            if not pdf_dir.is_dir():
                continue
            
            structured_file = pdf_dir / "02_structured_questions.json"
            if structured_file.exists():
                stats["total_pdfs"] += 1
                
                with open(structured_file, 'r', encoding='utf-8') as f:
                    paper = json.load(f)
                
                questions = paper.get("questions", [])
                stats["total_questions"] += len(questions)
                
                # Count by subject
                for q in questions:
                    subject = q.get("subject", "Unknown")
                    q_type = q.get("question_type", "Unknown")
                    
                    stats["by_subject"][subject] = stats["by_subject"].get(subject, 0) + 1
                    stats["by_type"][q_type] = stats["by_type"].get(q_type, 0) + 1
        
        return stats


def run_post_processing(output_dir: str = "extraction_output"):
    """
    Convenience function to run post-processing on all extractions
    
    Usage:
        from pipeline.question_structure_pipeline import run_post_processing
        run_post_processing()
    """
    # Set up logging
    log_file = f"logs/question_structure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    pipeline = QuestionStructurePipeline(output_dir)
    results = pipeline.process_all_extractions()
    
    logger.info("\n" + "="*60)
    logger.info("POST-PROCESSING COMPLETE")
    logger.info("="*60)
    
    stats = pipeline.get_statistics()
    logger.info(f"\n📊 STATISTICS:")
    logger.info(f"Total PDFs Processed: {stats['total_pdfs']}")
    logger.info(f"Total Questions Parsed: {stats['total_questions']}")
    logger.info(f"By Subject: {stats['by_subject']}")
    logger.info(f"By Type: {stats['by_type']}")
    
    return results


if __name__ == "__main__":
    # Run post-processing
    run_post_processing()
