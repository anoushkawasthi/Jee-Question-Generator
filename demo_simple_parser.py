"""Demo script to run SimpleTextQuestionParser on one JEE paper.

Usage (from project root):

    source .venv/Scripts/activate
    python demo_simple_parser.py
"""

import json
from pathlib import Path

from src.components.simple_text_question_parser import MarkerBasedQuestionParser
from src.components.text_normalizer import normalize_question_and_options


def main() -> None:
    base_dir = Path(__file__).parent
    paper_dir = base_dir / "extraction_output" / "JEE Main 2024 (01 Feb Shift 1) Previous Year Paper with Answer Keys - MathonGo"
    json_path = paper_dir / "01_text_images_extraction.json"

    if not json_path.exists():
        print(f"JSON file not found: {json_path}")
        return

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    text_blocks = data.get("text_blocks", [])
    paper_id = data.get("paper_id", json_path.stem)

    parser = MarkerBasedQuestionParser(paper_id=paper_id)
    questions = parser.parse(text_blocks)

    print(f"Parsed {len(questions)} questions from {paper_id}\n")

    # Print first 5 questions for manual inspection
    for q in questions[:5]:
        print("=" * 80)
        stem, opts = normalize_question_and_options(q.question_text, q.options)
        print(f"Q{q.question_number} (pages {q.page_start}-{q.page_end})")
        print("-- Question text --")
        print(stem)
        if opts:
            print("-- Options --")
            for i, opt in enumerate(opts, start=1):
                print(f"  ({i}) {opt}")
        else:
            print("-- Options -- none detected")
        print()


if __name__ == "__main__":
    main()
