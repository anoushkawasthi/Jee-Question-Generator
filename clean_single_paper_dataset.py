from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Dict, Any


PAPER_ID = "JEE Main 2024 (01 Feb Shift 1) Previous Year Paper with Answer Keys - MathonGo"
BASE_DIR = Path("extraction_output")
RAW_DATASET = BASE_DIR / f"{PAPER_ID}__mcq_dataset.jsonl"
CLEAN_DATASET = BASE_DIR / f"{PAPER_ID}__mcq_dataset_clean.jsonl"

# Phrases that strongly suggest dependence on a missing figure/diagram.
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
]


def _looks_image_dependent(stem: str) -> bool:
    text = stem.lower()
    return any(hint in text for hint in FIGURE_HINTS)


def _has_good_options(rec: Dict[str, Any]) -> bool:
    """Check if the record has valid options for an MCQ."""
    options = rec.get("options") or []
    if len(options) != 4:
        return False
    return all(isinstance(o, str) and o.strip() for o in options)


def _is_integer_type(rec: Dict[str, Any]) -> bool:
    """Check if the question is an integer/blank-answer type (no MCQ options)."""
    stem = rec.get("question_text", "")
    # Integer-type questions have blanks like "_________" or "______"
    return "_____" in stem


def iter_raw_records() -> Iterable[Dict[str, Any]]:
    if not RAW_DATASET.exists():
        raise FileNotFoundError(f"Raw dataset not found: {RAW_DATASET}")

    with RAW_DATASET.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def build_clean_dataset() -> None:
    kept_mcq = 0
    kept_integer = 0
    dropped = 0

    CLEAN_DATASET.parent.mkdir(parents=True, exist_ok=True)
    with CLEAN_DATASET.open("w", encoding="utf-8") as out_f:
        for rec in iter_raw_records():
            stem = rec.get("question_text", "")

            # Drop questions that clearly depend on a missing figure.
            if _looks_image_dependent(stem):
                dropped += 1
                continue

            # Check if it's an integer/blank-type question
            if _is_integer_type(rec):
                # Integer type: we keep it even without MCQ options
                rec["question_type"] = "integer"
                json.dump(rec, out_f, ensure_ascii=False)
                out_f.write("\n")
                kept_integer += 1
                continue

            # For MCQ: need correct_index and 4 good options
            if rec.get("correct_index") is None:
                dropped += 1
                continue
            if not _has_good_options(rec):
                dropped += 1
                continue

            rec["question_type"] = "mcq"
            json.dump(rec, out_f, ensure_ascii=False)
            out_f.write("\n")
            kept_mcq += 1

    print(f"Clean dataset written to: {CLEAN_DATASET}")
    print(f"Kept {kept_mcq} MCQ + {kept_integer} integer = {kept_mcq + kept_integer} total, dropped {dropped} questions.")


if __name__ == "__main__":
    build_clean_dataset()
