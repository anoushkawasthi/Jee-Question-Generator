"""
Full Dataset Builder for JEE Question Generator

Processes all JEE papers from existing extraction JSON files:
1. Reads from extraction_output/{paper_id}/01_text_images_extraction.json
2. Parses questions and answer keys (same as build_mcq_dataset_single_paper.py)
3. Normalizes text (decimals, fractions, exponents, units)
4. Filters to clean subset (drops image-dependent questions)
5. Adds metadata (year, date, shift, question_type)
6. Consolidates into a single dataset

Output: dataset_v2/all_papers_clean.jsonl

Usage:
    python build_full_dataset.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from answer_key_extractor import AnswerKeyExtractor
from src.components.simple_text_question_parser import MarkerBasedQuestionParser
from src.components.text_normalizer import normalize_question_and_options


# ============================================================================
# Configuration
# ============================================================================

EXTRACTION_OUTPUT_DIR = Path("extraction_output")
OUTPUT_DIR = Path("dataset_v2")
CONSOLIDATED_OUTPUT = OUTPUT_DIR / "all_papers_clean.jsonl"

# Junk substrings to strip from text
JUNK_SUBSTRINGS = [
    "JEE Main 2024",
    "JEE Main 2025",
    "MathonGo",
    "https://",
    "www.",
]

# Phrases indicating image-dependent questions (to be dropped)
FIGURE_HINTS = [
    "in the figure",
    "in figure",
    "in the following figure",
    "in the diagram",
    "shown in figure",
    "shown in the figure",
    "circuit diagram",
    "given circuit",
    "the circuit shown",
    "as shown",
    "figure shows",
    "diagram shows",
]


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class PaperMetadata:
    """Metadata extracted from paper folder name."""
    paper_id: str
    year: int
    date: str  # e.g., "01 Feb", "27 Jan"
    shift: int  # 1 or 2
    
    @classmethod
    def from_folder_name(cls, folder_name: str) -> "PaperMetadata":
        """Parse metadata from folder name like 'JEE Main 2024 (01 Feb Shift 1) ...'"""
        # Extract year
        year_match = re.search(r'JEE Main (\d{4})', folder_name)
        year = int(year_match.group(1)) if year_match else 0
        
        # Extract date and shift: "(01 Feb Shift 1)"
        date_shift_match = re.search(r'\((\d{2} \w+) Shift (\d)\)', folder_name)
        if date_shift_match:
            date = date_shift_match.group(1)
            shift = int(date_shift_match.group(2))
        else:
            date = "Unknown"
            shift = 0
        
        return cls(paper_id=folder_name, year=year, date=date, shift=shift)


# ============================================================================
# Text Processing Helpers
# ============================================================================

def strip_junk(text: str) -> str:
    """Remove obvious footer/marketing artifacts from text."""
    cleaned = text
    for junk in JUNK_SUBSTRINGS:
        idx = cleaned.lower().find(junk.lower())
        if idx != -1:
            cleaned = cleaned[:idx].rstrip()
    return cleaned


def looks_image_dependent(stem: str) -> bool:
    """Check if question depends on a missing figure/diagram."""
    text = stem.lower()
    return any(hint in text for hint in FIGURE_HINTS)


def is_integer_type(stem: str) -> bool:
    """Check if the question is an integer/numerical answer type."""
    # Integer-type questions have blanks like "_________"
    return "_____" in stem


def has_good_options(options: List[str]) -> bool:
    """Check if the record has valid 4 options for MCQ."""
    if len(options) != 4:
        return False
    return all(isinstance(o, str) and o.strip() for o in options)


# ============================================================================
# Paper Processing (same logic as build_mcq_dataset_single_paper.py)
# ============================================================================

def process_single_paper(paper_dir: Path, meta: PaperMetadata) -> List[Dict[str, Any]]:
    """Process a single paper and return list of clean question records.
    
    This uses the same logic as build_mcq_dataset_single_paper.py + clean_single_paper_dataset.py
    """
    
    input_json = paper_dir / "01_text_images_extraction.json"
    
    if not input_json.exists():
        print(f"  WARNING: {input_json} not found, skipping...")
        return []
    
    # Load extraction data
    with input_json.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    text_blocks = data.get("text_blocks", [])
    print(f"  Loaded {len(text_blocks)} text blocks")
    
    # Parse questions using MarkerBasedQuestionParser
    parser = MarkerBasedQuestionParser(meta.paper_id)
    questions = parser.parse(text_blocks)
    print(f"  Parsed {len(questions)} questions")
    
    # Extract answer keys
    extractor = AnswerKeyExtractor()
    answer_map = extractor.extract_from_json_file(str(input_json))
    print(f"  Extracted {len(answer_map)} answer keys")
    
    clean_records = []
    dropped = 0
    
    for q in questions:
        # Normalize text (same as build_mcq_dataset_single_paper.py)
        stem, options = normalize_question_and_options(q.question_text, q.options)
        
        # Strip junk
        stem = strip_junk(stem)
        options = [strip_junk(o) for o in options]
        
        # Check if image-dependent (drop these)
        if looks_image_dependent(stem):
            dropped += 1
            continue
        
        # Get answer
        ans = answer_map.get(q.question_number)
        
        # Determine question type and validate
        if is_integer_type(stem):
            # Integer type question
            if ans is None:
                dropped += 1
                continue  # Skip integer questions without answer
            
            record = {
                "paper_id": meta.paper_id,
                "year": meta.year,
                "date": meta.date,
                "shift": meta.shift,
                "question_number": q.question_number,
                "question_text": stem,
                "options": options,  # May be empty for integer type
                "question_type": "integer",
            }
            try:
                record["correct_answer"] = int(ans)
            except (ValueError, TypeError):
                record["correct_answer"] = ans
                
        else:
            # MCQ type question
            if not has_good_options(options):
                dropped += 1
                continue
            if ans is None:
                dropped += 1
                continue
            try:
                correct_idx = int(ans)
                if not (1 <= correct_idx <= 4):
                    dropped += 1
                    continue
            except (ValueError, TypeError):
                dropped += 1
                continue
            
            record = {
                "paper_id": meta.paper_id,
                "year": meta.year,
                "date": meta.date,
                "shift": meta.shift,
                "question_number": q.question_number,
                "question_text": stem,
                "options": options,
                "question_type": "mcq",
                "correct_index": correct_idx,
            }
        
        clean_records.append(record)
    
    print(f"  Kept {len(clean_records)}, dropped {dropped}")
    return clean_records


# ============================================================================
# Main Pipeline
# ============================================================================

def discover_all_papers() -> List[Path]:
    """Find all paper folders in extraction_output directory."""
    papers = []
    for item in EXTRACTION_OUTPUT_DIR.iterdir():
        if item.is_dir() and item.name.startswith("JEE Main"):
            # Check if it has the extraction JSON
            if (item / "01_text_images_extraction.json").exists():
                papers.append(item)
    return sorted(papers)


def build_full_dataset():
    """Main entry point: process all papers and create consolidated dataset."""
    
    print("=" * 60)
    print("JEE Question Dataset Builder v2")
    print("=" * 60)
    
    # Discover all papers
    papers = discover_all_papers()
    print(f"\nFound {len(papers)} papers with extraction data.\n")
    
    if not papers:
        print("No papers found in extraction_output/. Exiting.")
        return
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_records = []
    paper_stats = []
    
    for i, paper_dir in enumerate(papers, 1):
        print(f"\n[{i}/{len(papers)}] Processing: {paper_dir.name}")
        
        meta = PaperMetadata.from_folder_name(paper_dir.name)
        print(f"  Year: {meta.year}, Date: {meta.date}, Shift: {meta.shift}")
        
        try:
            records = process_single_paper(paper_dir, meta)
            all_records.extend(records)
            
            mcq_count = sum(1 for r in records if r["question_type"] == "mcq")
            int_count = sum(1 for r in records if r["question_type"] == "integer")
            paper_stats.append({
                "paper_id": meta.paper_id,
                "year": meta.year,
                "date": meta.date,
                "shift": meta.shift,
                "mcq": mcq_count,
                "integer": int_count,
                "total": len(records),
            })
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            paper_stats.append({
                "paper_id": meta.paper_id,
                "error": str(e),
            })
    
    # Write consolidated dataset
    print(f"\n{'=' * 60}")
    print(f"Writing consolidated dataset to: {CONSOLIDATED_OUTPUT}")
    
    with CONSOLIDATED_OUTPUT.open("w", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    # Write stats summary
    stats_file = OUTPUT_DIR / "extraction_stats.json"
    with stats_file.open("w", encoding="utf-8") as f:
        json.dump({
            "total_papers": len(papers),
            "total_questions": len(all_records),
            "mcq_count": sum(1 for r in all_records if r["question_type"] == "mcq"),
            "integer_count": sum(1 for r in all_records if r["question_type"] == "integer"),
            "papers": paper_stats,
        }, f, indent=2, ensure_ascii=False)
    
    print(f"Stats written to: {stats_file}")
    
    # Print summary
    total_mcq = sum(1 for r in all_records if r["question_type"] == "mcq")
    total_int = sum(1 for r in all_records if r["question_type"] == "integer")
    
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total papers processed: {len(papers)}")
    print(f"Total questions: {len(all_records)}")
    print(f"  - MCQ: {total_mcq}")
    print(f"  - Integer: {total_int}")
    print(f"\nOutput: {CONSOLIDATED_OUTPUT}")


if __name__ == "__main__":
    build_full_dataset()
