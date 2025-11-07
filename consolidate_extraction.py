"""
Consolidate Extraction Pipeline Results
Combines all extracted JSON files into a single final consolidated JSON
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_final_extractions(extraction_output_dir: str = "extraction_output") -> List[Path]:
    """Find all final_extraction.json files in the extraction output directory"""
    extraction_dir = Path(extraction_output_dir)
    
    if not extraction_dir.exists():
        raise FileNotFoundError(f"Extraction output directory not found: {extraction_output_dir}")
    
    final_files = list(extraction_dir.rglob("final_extraction.json"))
    logger.info(f"Found {len(final_files)} final_extraction.json files")
    
    return sorted(final_files)


def load_extraction(file_path: Path) -> Dict[str, Any]:
    """Load a single extraction JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {file_path}: {str(e)}")
        return None


def consolidate_extractions(extraction_files: List[Path]) -> Dict[str, Any]:
    """Consolidate all extraction files into a single JSON"""
    
    consolidated = {
        "metadata": {
            "title": "JEE Main Complete Question Bank - Extraction Pipeline",
            "version": "1.0",
            "extraction_method": "combined_pipeline_extraction",
            "consolidated_at": datetime.now().isoformat(),
            "total_papers": len(extraction_files),
            "total_questions": 0,
            "papers": []
        },
        "questions": []
    }
    
    total_questions = 0
    papers_with_errors = []
    
    logger.info(f"Consolidating {len(extraction_files)} extraction files...")
    
    for idx, file_path in enumerate(extraction_files):
        logger.info(f"[{idx + 1}/{len(extraction_files)}] Processing: {file_path.parent.name}")
        
        data = load_extraction(file_path)
        if not data:
            papers_with_errors.append(file_path.parent.name)
            continue
        
        # Extract paper metadata
        paper_meta = data.get("paper_metadata", {})
        questions = data.get("questions", [])
        
        if questions:
            total_questions += len(questions)
            
            # Add paper info
            consolidated["metadata"]["papers"].append({
                "name": paper_meta.get("exam_name", "Unknown"),
                "date_shift": paper_meta.get("exam_date_shift", "Unknown"),
                "question_count": len(questions),
                "has_answers": len([q for q in questions if q.get("correct_answer")]) if questions else 0
            })
            
            # Add questions
            consolidated["questions"].extend(questions)
            
            logger.info(f"  ✅ Loaded {len(questions)} questions")
        else:
            logger.warning(f"  ⚠️  No questions found in extraction")
            papers_with_errors.append(paper_meta.get("exam_date_shift", "Unknown"))
    
    # Update summary
    consolidated["metadata"]["total_questions"] = total_questions
    consolidated["metadata"]["papers_processed"] = len(extraction_files) - len(papers_with_errors)
    consolidated["metadata"]["papers_with_errors"] = papers_with_errors
    
    # Add statistics
    questions_with_answers = len([q for q in consolidated["questions"] if q.get("correct_answer")])
    consolidated["metadata"]["statistics"] = {
        "total_questions": total_questions,
        "questions_with_answers": questions_with_answers,
        "questions_missing_answers": total_questions - questions_with_answers,
        "data_quality_percentage": round(100 * questions_with_answers / total_questions, 1) if total_questions > 0 else 0
    }
    
    return consolidated


def save_consolidated_json(consolidated_data: Dict[str, Any], 
                          output_path: str = "final_consolidated_extraction.json") -> str:
    """Save consolidated JSON to file"""
    
    output_file = Path(output_path)
    
    # Create parent directory if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated_data, f, indent=2, ensure_ascii=False)
    
    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    logger.info(f"✅ Consolidated JSON saved to: {output_file}")
    logger.info(f"   File size: {file_size_mb:.2f} MB")
    
    return str(output_file)


def print_summary(consolidated_data: Dict[str, Any]):
    """Print extraction summary"""
    
    meta = consolidated_data["metadata"]
    stats = meta.get("statistics", {})
    
    print("\n" + "="*70)
    print("EXTRACTION PIPELINE - CONSOLIDATION SUMMARY")
    print("="*70)
    print(f"\n📊 OVERALL STATISTICS")
    print(f"  Total Papers Processed: {meta['papers_processed']}")
    print(f"  Total Questions Extracted: {stats.get('total_questions', 0)}")
    print(f"  Questions with Answers: {stats.get('questions_with_answers', 0)}")
    print(f"  Questions Missing Answers: {stats.get('questions_missing_answers', 0)}")
    print(f"  Data Quality: {stats.get('data_quality_percentage', 0)}%")
    
    print(f"\n📋 PAPERS PROCESSED")
    for paper in meta.get("papers", []):
        print(f"  • {paper['name']} ({paper['date_shift'][:10]})")
        print(f"    Questions: {paper['question_count']}, With Answers: {paper['has_answers']}")
    
    if meta.get("papers_with_errors"):
        print(f"\n⚠️  PAPERS WITH ERRORS ({len(meta['papers_with_errors'])})")
        for paper in meta["papers_with_errors"]:
            print(f"  • {paper}")
    
    print(f"\n💾 OUTPUT FILE")
    print(f"  Location: final_consolidated_extraction.json")
    print(f"  Format: JSON")
    print(f"  Encoding: UTF-8")
    
    print("\n" + "="*70)
    print("✅ CONSOLIDATION COMPLETE")
    print("="*70 + "\n")


def main():
    """Main consolidation function"""
    
    logger.info("Starting extraction consolidation pipeline...")
    
    try:
        # Find all extraction files
        extraction_files = find_final_extractions()
        
        if not extraction_files:
            logger.error("No extraction files found!")
            return
        
        # Consolidate data
        consolidated_data = consolidate_extractions(extraction_files)
        
        # Save to file
        output_path = save_consolidated_json(consolidated_data)
        
        # Print summary
        print_summary(consolidated_data)
        
        logger.info("✅ Consolidation pipeline completed successfully!")
        
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Consolidation failed: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
