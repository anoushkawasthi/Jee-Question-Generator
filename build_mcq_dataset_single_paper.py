from __future__ import annotations

import json
from pathlib import Path

from answer_key_extractor import AnswerKeyExtractor
from src.components.simple_text_question_parser import MarkerBasedQuestionParser
from src.components.text_normalizer import normalize_question_and_options


JUNK_SUBSTRINGS = [
    "JEE Main 2024",
    "MathonGo",
    "https://",
]


def _strip_junk(text: str) -> str:
    """Remove obvious footer/marketing artifacts from text."""

    cleaned = text
    for junk in JUNK_SUBSTRINGS:
        idx = cleaned.find(junk)
        if idx != -1:
            cleaned = cleaned[:idx].rstrip()
    return cleaned


def _is_complex_math(text: str, options: list[str]) -> bool:
    """Heuristic flag for questions with more involved equations.

    We treat a question as complex math if either the stem or any option
    contains typical math tokens (trig, pi, exponents) *and* has a fair
    amount of non-space characters, to avoid matching tiny fragments.
    """

    candidates = [text, *options]
    math_tokens = ("sin", "cos", "tan", "cot", "sec", "cosec", "π", "^", "theta", "θ")

    for s in candidates:
        s_norm = s.strip()
        if len(s_norm) < 10:
            continue
        lowered = s_norm.lower()
        if any(tok in lowered for tok in math_tokens):
            return True
    return False


def _is_clean_textual(record: dict) -> bool:
    """Conservative flag for generally clean textual MCQs.

    Criteria (can be tightened later):
    - 4 non-empty options.
    - Has a correct_index.
    - Stem and options do not contain obvious junk substrings.
    """

    if record.get("correct_index") is None:
        return False

    options = record.get("options") or []
    if len(options) != 4:
        return False
    if any(not (opt and opt.strip()) for opt in options):
        return False

    text_fields = [record.get("question_text", ""), *options]
    for txt in text_fields:
        lowered = txt.lower()
        for junk in JUNK_SUBSTRINGS:
            if junk.lower() in lowered:
                return False

    return True


PAPER_ID = "JEE Main 2024 (01 Feb Shift 1) Previous Year Paper with Answer Keys - MathonGo"
PAPER_DIR = Path("extraction_output") / PAPER_ID
INPUT_JSON = PAPER_DIR / "01_text_images_extraction.json"
OUTPUT_JSONL = Path("extraction_output") / f"{PAPER_ID}__mcq_dataset.jsonl"


def build_dataset_for_paper() -> None:
    if not INPUT_JSON.exists():
        raise FileNotFoundError(f"Input JSON not found: {INPUT_JSON}")

    with INPUT_JSON.open("r", encoding="utf-8") as f:
        data = json.load(f)

    text_blocks = data.get("text_blocks", [])

    # Parse questions (structure only)
    parser = MarkerBasedQuestionParser(PAPER_ID)
    questions = parser.parse(text_blocks)

    # Extract answer keys
    extractor = AnswerKeyExtractor()
    answer_map = extractor.extract_from_json_file(str(INPUT_JSON))

    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSONL.open("w", encoding="utf-8") as out_f:
        for q in questions:
            stem, options = normalize_question_and_options(q.question_text, q.options)

            # Strip footer/marketing junk from stem and options first.
            stem = _strip_junk(stem)
            options = [_strip_junk(o) for o in options]

            record = {
                "paper_id": q.paper_id,
                "question_number": q.question_number,
                "page_start": q.page_start,
                "page_end": q.page_end,
                "question_text": stem,
                "options": options,
            }

            # Lightweight metadata flags
            record["complex_math"] = _is_complex_math(stem, options)
            record["clean_textual"] = _is_clean_textual(record)

            # Attach correct answer if available
            # For MCQs (4 options), this is the option index (1-4)
            # For integer questions (no options), this is the actual integer answer
            ans = answer_map.get(q.question_number)
            if ans is not None:
                try:
                    record["correct_index"] = int(ans)
                except ValueError:
                    record["correct_index"] = ans

            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote dataset for {PAPER_ID} to {OUTPUT_JSONL}")


if __name__ == "__main__":
    build_dataset_for_paper()
