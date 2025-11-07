"""
Answer Merger Component
Merges structured questions with raw answer data to create final consolidated JSON
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class AnswerMerger:
    """
    Merges structured questions with raw_questions.json answer data
    
    This creates a final consolidated JSON file with:
    - All question details from structured extraction
    - Answer mappings from raw_questions.json
    - Confidence scores and validation
    """

    def __init__(self, raw_answers_path: str = "data/processed/raw_questions.json"):
        self.raw_answers_path = raw_answers_path
        self.raw_answers_map = {}
        self._load_raw_answers()

    def _load_raw_answers(self):
        """Load raw answers from raw_questions.json"""
        try:
            with open(self.raw_answers_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Build a map: (pdf_file, question_number) -> correct_answer
            for paper in raw_data:
                source_file = paper.get("source_file", "")
                for q in paper.get("questions", []):
                    q_num = int(q.get("question_number", 0))
                    answer = q.get("correct_answer", "")
                    
                    # Key: (filename, question_number)
                    key = (source_file, q_num)
                    self.raw_answers_map[key] = answer
            
            logger.info(f"Loaded {len(self.raw_answers_map)} answer mappings from raw_questions.json")
            
        except Exception as e:
            logger.warning(f"Could not load raw answers: {str(e)}")
            self.raw_answers_map = {}

    def merge_paper(self, pdf_dir: Path, pdf_filename: str) -> Dict:
        """
        Merge structured questions with raw answers for a single PDF
        
        Args:
            pdf_dir: Path to PDF extraction directory
            pdf_filename: Original PDF filename
            
        Returns:
            Merged paper with enhanced answer data
        """
        # Load structured questions
        structured_file = pdf_dir / "02_structured_questions.json"
        if not structured_file.exists():
            logger.warning(f"No structured questions found in {pdf_dir.name}")
            return {}
        
        with open(structured_file, 'r', encoding='utf-8') as f:
            paper = json.load(f)
        
        # Enhance with raw answers
        questions = paper.get("questions", [])
        enhanced_questions = []
        
        for q in questions:
            q_num = q.get("question_number", 0)
            
            # Look up raw answer
            key = (pdf_filename, q_num)
            raw_answer = self.raw_answers_map.get(key)
            
            if raw_answer:
                # Validate and map answer
                validation = self._validate_answer(q, raw_answer)
                q["verified_answer"] = raw_answer
                q["answer_confidence"] = validation["confidence"]
                q["answer_validation"] = validation["status"]
                q["answer_notes"] = validation["notes"]
            else:
                # No raw answer found, use extracted answer
                q["verified_answer"] = q.get("correct_answer", "")
                q["answer_confidence"] = 0.7  # Lower confidence for extracted
                q["answer_validation"] = "extracted_only"
                q["answer_notes"] = "Answer from PDF extraction, not verified against raw data"
            
            enhanced_questions.append(q)
        
        paper["questions"] = enhanced_questions
        
        # Add merge metadata
        paper["merge_metadata"] = {
            "merged_at": datetime.now().isoformat(),
            "raw_answers_used": sum(1 for q in enhanced_questions 
                                   if q.get("answer_validation") == "verified"),
            "extracted_only": sum(1 for q in enhanced_questions 
                                 if q.get("answer_validation") == "extracted_only"),
            "verification_rate": round(
                sum(1 for q in enhanced_questions if q.get("answer_validation") == "verified") 
                / len(enhanced_questions) * 100, 2
            ) if enhanced_questions else 0
        }
        
        return paper

    def _validate_answer(self, question: Dict, raw_answer: str) -> Dict:
        """
        Validate extracted answer against raw answer
        
        Returns validation status and confidence
        """
        extracted_answer = question.get("correct_answer", "")
        
        # Map option IDs to numeric answers
        extracted_mapped = self._map_option_to_answer(question, extracted_answer)
        
        # Compare
        match = extracted_mapped.lower().strip() == str(raw_answer).lower().strip()
        
        return {
            "status": "verified" if match else "mismatch",
            "confidence": 0.95 if match else 0.5,
            "notes": f"Verified match: extracted='{extracted_answer}' vs raw='{raw_answer}'" 
                    if match 
                    else f"Mismatch: extracted='{extracted_answer}' vs raw='{raw_answer}'"
        }

    def _map_option_to_answer(self, question: Dict, option_id: str) -> str:
        """
        Map option ID (A, B, C, D, 1, 2, 3, 4) to standard format
        """
        # If already numeric, return as is
        if option_id and option_id[0].isdigit():
            return option_id[0]
        
        # Convert letter to number
        letter_to_num = {'A': '1', 'B': '2', 'C': '3', 'D': '4'}
        if option_id and option_id[0].upper() in letter_to_num:
            return letter_to_num[option_id[0].upper()]
        
        return option_id

    def consolidate_all(self, extraction_output_dir: str = "extraction_output") -> Dict:
        """
        Consolidate all PDFs into single final JSON file
        
        Returns consolidated data with statistics
        """
        consolidated = {
            "metadata": {
                "title": "JEE Main Question Bank - Final Consolidated",
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "total_papers": 0,
                "total_questions": 0,
                "verification_stats": {
                    "verified": 0,
                    "extracted_only": 0,
                    "verification_rate": 0.0
                }
            },
            "papers": []
        }
        
        output_path = Path(extraction_output_dir)
        if not output_path.exists():
            logger.error(f"Output directory not found: {extraction_output_dir}")
            return consolidated
        
        # Process each PDF directory
        for pdf_dir in sorted(output_path.iterdir()):
            if not pdf_dir.is_dir():
                continue
            
            try:
                # Extract original PDF filename from directory name
                pdf_filename = pdf_dir.name + ".pdf"
                
                # Merge answers
                merged_paper = self.merge_paper(pdf_dir, pdf_filename)
                
                if merged_paper:
                    consolidated["papers"].append(merged_paper)
                    consolidated["metadata"]["total_papers"] += 1
                    
                    # Update statistics
                    questions = merged_paper.get("questions", [])
                    consolidated["metadata"]["total_questions"] += len(questions)
                    
                    verified = sum(1 for q in questions 
                                 if q.get("answer_validation") == "verified")
                    consolidated["metadata"]["verification_stats"]["verified"] += verified
                    consolidated["metadata"]["verification_stats"]["extracted_only"] += (len(questions) - verified)
                    
                    logger.info(f"✅ Merged: {pdf_dir.name} ({len(questions)} questions, {verified}/{len(questions)} verified)")
                    
            except Exception as e:
                logger.error(f"❌ Error processing {pdf_dir.name}: {str(e)}")
                continue
        
        # Calculate final verification rate
        total_q = consolidated["metadata"]["total_questions"]
        if total_q > 0:
            verified_q = consolidated["metadata"]["verification_stats"]["verified"]
            consolidated["metadata"]["verification_stats"]["verification_rate"] = round(
                verified_q / total_q * 100, 2
            )
        
        return consolidated

    def save_final_json(self, consolidated_data: Dict, output_file: str) -> str:
        """
        Save final consolidated JSON to file
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(consolidated_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved consolidated JSON to: {output_path}")
        return str(output_path)


def create_final_consolidated_json(
    extraction_output_dir: str = "extraction_output",
    raw_answers_path: str = "data/processed/raw_questions.json",
    output_file: str = "data/processed/jee_questions_final_consolidated.json"
) -> str:
    """
    Create final consolidated JSON with answer verification
    
    Usage:
        output_path = create_final_consolidated_json()
        print(f"Final JSON created at: {output_path}")
    """
    logger.info("🔄 Creating final consolidated JSON with answer verification...")
    logger.info("="*70)
    
    merger = AnswerMerger(raw_answers_path)
    consolidated = merger.consolidate_all(extraction_output_dir)
    output_path = merger.save_final_json(consolidated, output_file)
    
    # Log statistics
    logger.info("\n📊 CONSOLIDATION COMPLETE")
    logger.info("="*70)
    logger.info(f"Total Papers: {consolidated['metadata']['total_papers']}")
    logger.info(f"Total Questions: {consolidated['metadata']['total_questions']}")
    logger.info(f"Verified Answers: {consolidated['metadata']['verification_stats']['verified']}")
    logger.info(f"Extracted Only: {consolidated['metadata']['verification_stats']['extracted_only']}")
    logger.info(f"Verification Rate: {consolidated['metadata']['verification_stats']['verification_rate']}%")
    logger.info(f"\n✅ Output: {output_file}")
    
    return output_path
