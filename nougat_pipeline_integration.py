"""
Integration script for using Nougat parser with .mmd files
Processes all Nougat markdown files and creates clean JSON
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List
import argparse

from src.components.nougat_question_parser import NougatQuestionParser

logger = logging.getLogger(__name__)


class NougatPipelineIntegration:
    """
    Integrates Nougat output with question parsing
    Handles batch processing of .mmd files
    """
    
    def __init__(self, nougat_output_dir: str, json_output_dir: str):
        """
        Args:
            nougat_output_dir: Directory containing .mmd files from Nougat
            json_output_dir: Directory to save parsed JSON files
        """
        self.nougat_dir = Path(nougat_output_dir)
        self.output_dir = Path(json_output_dir)
        self.parser = NougatQuestionParser()
        
        # Create output directory if needed
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def process_single_mmd_file(self, mmd_file_path: str, paper_id: str = None) -> Dict:
        """
        Process a single .mmd file
        
        Args:
            mmd_file_path: Path to .mmd file
            paper_id: Optional paper identifier (extracted from filename if not provided)
            
        Returns:
            Dictionary with results
        """
        mmd_path = Path(mmd_file_path)
        
        if not mmd_path.exists():
            logger.error(f"File not found: {mmd_file_path}")
            return {"status": "error", "message": "File not found"}
        
        # Extract paper ID from filename if not provided
        if not paper_id:
            paper_id = mmd_path.stem  # filename without extension
        
        try:
            # Read markdown file
            with open(mmd_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            logger.info(f"Processing: {mmd_path.name}")
            
            # Save to JSON (returns parsed questions without re-parsing)
            output_filename = mmd_path.stem + "_parsed.json"
            output_path = self.output_dir / output_filename
            
            questions = self.parser.parse_and_save_json(
                markdown_content,
                str(output_path),
                paper_id
            )
            
            if not questions:
                logger.warning(f"No questions parsed from {mmd_path.name}")
                return {
                    "status": "warning",
                    "file": mmd_path.name,
                    "questions_count": 0
                }
            
            logger.info(f"✅ Saved {len(questions)} questions to {output_path}")
            
            return {
                "status": "success",
                "file": mmd_path.name,
                "questions_count": len(questions),
                "output_file": str(output_path)
            }
            
        except Exception as e:
            logger.error(f"Error processing {mmd_path.name}: {str(e)}")
            return {
                "status": "error",
                "file": mmd_path.name,
                "message": str(e)
            }

    def process_all_mmd_files(self, pattern: str = "*.mmd") -> List[Dict]:
        """
        Process all .mmd files in directory
        
        Args:
            pattern: Glob pattern for files to process
            
        Returns:
            List of result dictionaries
        """
        results = []
        
        mmd_files = list(self.nougat_dir.glob(pattern))
        
        if not mmd_files:
            logger.warning(f"No {pattern} files found in {self.nougat_dir}")
            return []
        
        logger.info(f"Found {len(mmd_files)} .mmd files to process")
        
        for mmd_file in sorted(mmd_files):
            result = self.process_single_mmd_file(str(mmd_file))
            results.append(result)
        
        return results

    def create_consolidated_json(self, output_file: str = None) -> str:
        """
        Create single consolidated JSON from all parsed questions
        
        Args:
            output_file: Path for consolidated file
            
        Returns:
            Path to consolidated file
        """
        if not output_file:
            output_file = str(self.output_dir / "all_questions_consolidated.json")
        
        all_questions = []
        paper_count = 0
        
        # Load all parsed JSON files
        json_files = list(self.output_dir.glob("*_parsed.json"))
        
        if not json_files:
            logger.warning("No parsed JSON files found")
            return None
        
        for json_file in sorted(json_files):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                all_questions.extend(data.get('questions', []))
                paper_count += 1
                
            except Exception as e:
                logger.error(f"Error reading {json_file}: {str(e)}")
                continue
        
        # Create consolidated structure
        consolidated = {
            "metadata": {
                "title": "JEE Main Question Bank - Nougat Parsed",
                "version": "1.0",
                "parsing_method": "nougat",
                "total_papers": paper_count,
                "total_questions": len(all_questions)
            },
            "questions": all_questions
        }
        
        # Save consolidated file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(consolidated, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Created consolidated JSON: {output_file}")
        logger.info(f"   Papers: {paper_count}, Questions: {len(all_questions)}")
        
        return output_file

    def print_summary(self, results: List[Dict]):
        """Print summary of processing results"""
        print("\n" + "="*70)
        print("NOUGAT PROCESSING SUMMARY")
        print("="*70)
        
        successful = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] == "error"]
        warnings = [r for r in results if r["status"] == "warning"]
        
        total_questions = sum(r.get("questions_count", 0) for r in successful)
        
        print(f"\n✅ Successful: {len(successful)}")
        print(f"❌ Failed: {len(failed)}")
        print(f"⚠️  Warnings: {len(warnings)}")
        print(f"\n📊 Total Questions Parsed: {total_questions}")
        
        if failed:
            print("\nFailed files:")
            for r in failed:
                print(f"  - {r['file']}: {r.get('message', 'Unknown error')}")
        
        print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(description="Process Nougat markdown files")
    parser.add_argument(
        "--nougat-dir",
        type=str,
        default="nougat_output",
        help="Directory containing .mmd files from Nougat"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed/nougat_parsed",
        help="Directory to save parsed JSON files"
    )
    parser.add_argument(
        "--consolidate",
        action="store_true",
        help="Create single consolidated JSON file"
    )
    parser.add_argument(
        "--consolidated-output",
        type=str,
        default=None,
        help="Path for consolidated JSON file"
    )
    
    args = parser.parse_args()
    
    # Initialize integration
    integration = NougatPipelineIntegration(args.nougat_dir, args.output_dir)
    
    # Process all .mmd files
    print(f"\n🔄 Processing Nougat markdown files from: {args.nougat_dir}")
    results = integration.process_all_mmd_files()
    
    # Print summary
    integration.print_summary(results)
    
    # Create consolidated file if requested
    if args.consolidate:
        print("\n🔄 Creating consolidated JSON...")
        consolidated_path = integration.create_consolidated_json(args.consolidated_output)
        if consolidated_path:
            print(f"✅ Consolidated file: {consolidated_path}")


if __name__ == "__main__":
    main()
