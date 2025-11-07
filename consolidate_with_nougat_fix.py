"""
CORRECTED Consolidation Script - Uses 02_structured_questions.json (with Nougat LaTeX)
Instead of final_extraction.json (PyMuPDF only)
"""

import json
import os
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def consolidate_with_nougat():
    """Consolidate using 02_structured_questions.json which contains Nougat LaTeX output"""
    
    extraction_output_dir = "extraction_output"
    
    print("\n" + "=" * 100)
    print("CORRECTED CONSOLIDATION - Using 02_structured_questions.json (Nougat)")
    print("=" * 100 + "\n")
    
    consolidated = {
        "metadata": {
            "title": "JEE Main Question Bank - Final Consolidated",
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "total_papers": 0,
            "total_questions": 0,
            "extraction_method": "nougat_enhanced_extraction",
            "pipeline_stages": ["PyMuPDF (text/images)", "Nougat (LaTeX conversion)", "OSRA (chemistry)", "JSON merge"],
            "verification_stats": {
                "verified": 0,
                "extracted_only": 0,
                "verification_rate": 0.0
            }
        },
        "papers": []
    }
    
    # Find all 02_structured_questions.json files (these have Nougat LaTeX)
    nougat_files = []
    for root, dirs, files in os.walk(extraction_output_dir):
        if "02_structured_questions.json" in files:
            nougat_files.append(os.path.join(root, "02_structured_questions.json"))
    
    nougat_files.sort()
    
    print(f"Found {len(nougat_files)} papers with Nougat processing...\n")
    
    total_questions = 0
    verified_count = 0
    extracted_only_count = 0
    
    for idx, filepath in enumerate(nougat_files, 1):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            paper_meta = data.get("paper_metadata", {})
            questions = data.get("questions", [])
            
            if not questions:
                print(f"⏭️  [{idx:2d}/{len(nougat_files)}] {paper_meta.get('exam_date_shift', 'Unknown'):20s} - SKIPPED (no questions)")
                continue
            
            # Count verification status
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
                    "verification_rate": len([q for q in questions if q.get("answer_validation") == "verified"]) / len(questions) * 100 if questions else 0
                }
            }
            
            consolidated["papers"].append(paper_entry)
            total_questions += len(questions)
            
            # Check for LaTeX in first question
            first_q_has_latex = False
            if questions and questions[0].get("question_latex"):
                first_q_has_latex = True
            
            print(f"✅ [{idx:2d}/{len(nougat_files)}] {paper_meta.get('exam_date_shift', 'Unknown'):20s} - {len(questions):2d} Q's | LaTeX: {'✅' if first_q_has_latex else '❌'}")
            
        except Exception as e:
            paper_name = os.path.basename(os.path.dirname(filepath))
            print(f"❌ [{idx:2d}/{len(nougat_files)}] {paper_name:30s} - ERROR: {e}")
    
    # Update metadata
    consolidated["metadata"]["total_papers"] = len(consolidated["papers"])
    consolidated["metadata"]["total_questions"] = total_questions
    consolidated["metadata"]["verification_stats"]["verified"] = verified_count
    consolidated["metadata"]["verification_stats"]["extracted_only"] = extracted_only_count
    if total_questions > 0:
        consolidated["metadata"]["verification_stats"]["verification_rate"] = round(verified_count / total_questions * 100, 2)
    
    # Save consolidated file
    output_file = "data/processed/jee_questions_final_consolidated_nougat.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated, f, indent=2, ensure_ascii=False)
    
    print(f"\n" + "=" * 100)
    print("CONSOLIDATION COMPLETE")
    print("=" * 100)
    print(f"\n📊 Summary:")
    print(f"   ✅ Total papers consolidated: {consolidated['metadata']['total_papers']}")
    print(f"   ✅ Total questions: {total_questions}")
    print(f"   ✅ With verified answers: {verified_count}")
    print(f"   ✅ Extraction only: {extracted_only_count}")
    print(f"   ✅ Verification rate: {consolidated['metadata']['verification_stats']['verification_rate']}%")
    print(f"\n📁 Output file: {output_file}")
    print(f"📊 File size: {os.path.getsize(output_file) / (1024*1024):.2f} MB")
    print(f"\n✅ This file INCLUDES Nougat LaTeX processing for proper math rendering!")

if __name__ == "__main__":
    consolidate_with_nougat()
