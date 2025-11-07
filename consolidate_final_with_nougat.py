"""
FINAL Corrected Consolidation with Nougat Post-Processing AND Answer Key Extraction

This script:
1. Uses 02_structured_questions.json (better extracted data)
2. Extracts answer keys from PDF page 13 using answer_key_extractor
3. Maps extracted answer keys to questions
4. Applies Nougat post-processing to add LaTeX formatting
5. Fixes garbled math symbols
6. Creates the proper final consolidated JSON
"""

import json
import os
from pathlib import Path
from datetime import datetime
import logging
from nougat_postprocessor import apply_nougat_postprocessing
from answer_key_extractor import AnswerKeyExtractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def consolidate_with_nougat_postprocessing():
    """Consolidate using 02_structured_questions.json with Nougat post-processing"""
    
    extraction_output_dir = "extraction_output"
    
    print("\n" + "=" * 120)
    print("FINAL CONSOLIDATION - Using Nougat Post-Processing for LaTeX")
    print("=" * 120 + "\n")
    
    consolidated = {
        "metadata": {
            "title": "JEE Main Question Bank - Final Consolidated with Nougat",
            "version": "2.0",
            "created_at": datetime.now().isoformat(),
            "total_papers": 0,
            "total_questions": 0,
            "extraction_method": "pymupdf_with_nougat_postprocessing",
            "pipeline_stages": [
                "PyMuPDF (text/images extraction)",
                "Question parsing and structuring",
                "Nougat Post-Processing (LaTeX conversion)",
                "Final consolidation and merging"
            ],
            "verification_stats": {
                "verified": 0,
                "extracted_only": 0,
                "verification_rate": 0.0
            },
            "notes": "This is the corrected version using Nougat post-processing to add proper LaTeX formatting"
        },
        "papers": []
    }
    
    # Find all 02_structured_questions.json files
    nougat_files = []
    for root, dirs, files in os.walk(extraction_output_dir):
        if "02_structured_questions.json" in files:
            nougat_files.append(os.path.join(root, "02_structured_questions.json"))
    
    nougat_files.sort()
    
    print(f"Found {len(nougat_files)} papers with extraction data...\n")
    print("Processing papers:")
    print("-" * 120)
    
    total_questions = 0
    verified_count = 0
    extracted_only_count = 0
    papers_processed = 0
    answers_mapped = 0
    
    # Initialize answer key extractor
    answer_key_extractor = AnswerKeyExtractor()
    
    for idx, filepath in enumerate(nougat_files, 1):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            paper_meta = data.get("paper_metadata", {})
            questions = data.get("questions", [])
            
            if not questions:
                print(f"⏭️  [{idx:2d}/{len(nougat_files)}] {paper_meta.get('exam_date_shift', 'Unknown'):20s} - SKIPPED (no questions)")
                continue
            
            # EXTRACT ANSWER KEYS FROM PDF PAGE 13
            pdf_dir = Path(filepath).parent
            json_extraction_file = pdf_dir / "01_text_images_extraction.json"
            
            extracted_answers = {}
            if json_extraction_file.exists():
                try:
                    extracted_answers = answer_key_extractor.extract_from_json_file(str(json_extraction_file))
                    # Map answers to questions
                    for q in questions:
                        q_num = q.get('question_number')
                        if q_num in extracted_answers:
                            q['correct_answer'] = extracted_answers[q_num]
                            answers_mapped += 1
                except Exception as e:
                    logger.warning(f"Could not extract answers from {json_extraction_file}: {e}")
            
            # Count verification status BEFORE processing
            for q in questions:
                if q.get("answer_validation") == "verified":
                    verified_count += 1
                else:
                    extracted_only_count += 1
            
            # Add paper to consolidated
            paper_entry = {
                "paper_metadata": paper_meta,
                "questions": questions,
                "merge_metadata": {
                    "merged_at": datetime.now().isoformat(),
                    "raw_answers_used": len([q for q in questions if q.get("verified_answer")]),
                    "extracted_only": len([q for q in questions if not q.get("verified_answer")]),
                    "extracted_answer_keys": len(extracted_answers),
                    "verification_rate": len([q for q in questions if q.get("answer_validation") == "verified"]) / len(questions) * 100 if questions else 0
                }
            }
            
            consolidated["papers"].append(paper_entry)
            total_questions += len(questions)
            papers_processed += 1
            
            # Check for LaTeX in first question (before processing)
            first_q_latex_before = "NONE" if not questions[0].get("question_latex") else "exists"
            
            print(f"✅ [{idx:2d}/{len(nougat_files)}] {paper_meta.get('exam_date_shift', 'Unknown'):20s} - {len(questions):2d} Q's ({len(extracted_answers)} answers mapped)")
            
        except Exception as e:
            paper_name = os.path.basename(os.path.dirname(filepath))
            print(f"❌ [{idx:2d}/{len(nougat_files)}] {paper_name:30s} - ERROR: {e}")
    
    print("\n" + "-" * 120)
    print(f"\nApplying Nougat post-processing to all {papers_processed} papers...")
    print("This will convert math symbols to LaTeX and fix garbled text...\n")
    
    # Apply Nougat post-processing
    consolidated = apply_nougat_postprocessing(consolidated)
    
    # Update metadata
    consolidated["metadata"]["total_papers"] = papers_processed
    consolidated["metadata"]["total_questions"] = total_questions
    consolidated["metadata"]["verification_stats"]["verified"] = verified_count
    consolidated["metadata"]["verification_stats"]["extracted_only"] = extracted_only_count
    if total_questions > 0:
        consolidated["metadata"]["verification_stats"]["verification_rate"] = round(verified_count / total_questions * 100, 2)
    
    # Save consolidated file - OVERWRITE the old broken one
    output_file = "data/processed/jee_questions_final_consolidated.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 120)
    print("✅ CONSOLIDATION COMPLETE - WITH ANSWER KEY EXTRACTION & NOUGAT POST-PROCESSING")
    print("=" * 120)
    print(f"\n📊 Summary:")
    print(f"   ✅ Total papers consolidated: {consolidated['metadata']['total_papers']}")
    print(f"   ✅ Total questions: {total_questions}")
    print(f"   ✅ Answer keys mapped from PDFs: {answers_mapped}")
    print(f"   ✅ With verified answers: {verified_count}")
    print(f"   ✅ Extraction only: {extracted_only_count}")
    print(f"   ✅ Verification rate: {consolidated['metadata']['verification_stats']['verification_rate']}%")
    print(f"\n📁 Output file: {output_file}")
    print(f"📊 File size: {os.path.getsize(output_file) / (1024*1024):.2f} MB")
    print(f"\n🚀 Pipeline Stages Applied:")
    for idx, stage in enumerate(consolidated['metadata']['pipeline_stages'], 1):
        print(f"   {idx}. {stage}")
    print(f"\n✅ This file NOW INCLUDES Nougat LaTeX post-processing!")
    print(f"✅ Math symbols have been converted to LaTeX format")
    print(f"✅ Question text has been cleaned of garbled Unicode")
    
    # Verify a sample question
    print(f"\n" + "=" * 120)
    print("VERIFICATION: Sample Question After Processing")
    print("=" * 120)
    
    if consolidated["papers"] and consolidated["papers"][0]["questions"]:
        sample_q = consolidated["papers"][0]["questions"][0]
        print(f"\nQuestion ID: {sample_q.get('question_id')}")
        print(f"\nOriginal question_text (first 150 chars):")
        print(f"  {sample_q.get('question_text', 'N/A')[:150]}")
        print(f"\nGenerated question_latex (first 150 chars):")
        print(f"  {sample_q.get('question_latex', 'N/A')[:150]}")
        print(f"\n✅ LaTeX field populated: {'YES ✅' if sample_q.get('question_latex') else 'NO ❌'}")


if __name__ == "__main__":
    consolidate_with_nougat_postprocessing()
