"""
Prototype: LLM-based JEE Question Generator

Reads from the clean single-paper dataset and uses GPT-4o-mini to generate
new similar questions with proper LaTeX formatting.

Usage:
    python generate_questions_prototype.py
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Configuration
PAPER_ID = "JEE Main 2024 (01 Feb Shift 1) Previous Year Paper with Answer Keys - MathonGo"
CLEAN_DATASET = Path("extraction_output") / f"{PAPER_ID}__mcq_dataset_clean.jsonl"
OUTPUT_FILE = Path("extraction_output") / "generated_questions_prototype.json"

MODEL = "gpt-4o-mini"
NUM_QUESTIONS = 5

SYSTEM_PROMPT = """You are an expert JEE Main question paper setter with deep knowledge of Physics, Chemistry, and Mathematics.

Your task is to create a VARIATION of a given JEE question. There are TWO strategies:

## STRATEGY 1: REPHRASE ONLY (for complex/computational questions)
- Change ONLY the wording and presentation
- DO NOT change ANY numbers, values, coefficients, or mathematical expressions
- DO NOT change the options - keep them EXACTLY the same
- The correct answer index stays the same
- Example: "Find the velocity..." → "Determine the speed..." (same numbers, same options)

## STRATEGY 2: CHANGE NUMBERS (ONLY for simple arithmetic questions)
- Only use this for questions with basic formulas (v=d/t, F=ma, simple ratios)
- When you change numbers, you MUST solve the problem yourself
- The new correct answer MUST be one of your 4 options
- Show your calculation in the explanation to verify correctness

## LaTeX Formatting (MANDATORY):
- Inline math: $...$ (e.g., $v = 10$ m/s)
- Fractions: $\\frac{a}{b}$
- Square roots: $\\sqrt{x}$
- Exponents: $x^{2}$, $10^{-2}$
- Greek letters: $\\theta$, $\\pi$, $\\alpha$, $\\lambda$
- Matrices: $\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}$
- Intervals: $\\left(-\\frac{1}{\\sqrt{5}}, 0\\right) \\cup \\left(\\frac{1}{\\sqrt{5}}, \\infty\\right)$

## CRITICAL RULES:
1. If using "rephrase_only": Options must be IDENTICAL to original (just add LaTeX formatting)
2. If using "rephrase_with_new_numbers": You must VERIFY your answer is correct
3. Output valid JSON only (no markdown, no extra text)"""

USER_PROMPT_TEMPLATE = """Here is an original JEE Main question:

**Question Type:** {question_type}
**Question:** {question_text}
{options_section}
**Correct Answer:** {correct_answer}

INSTRUCTIONS:
1. First, decide: Is this a simple arithmetic question where numbers can be changed? Or is it complex/computational?
2. If COMPLEX (differential equations, integrals, matrix operations, multi-step physics): Use "rephrase_only"
   - Keep ALL numbers, equations, and values EXACTLY the same
   - Keep ALL options EXACTLY the same (just format in LaTeX)
   - Only change the wording/presentation of the question
3. If SIMPLE (basic formulas, direct substitution): You MAY use "rephrase_with_new_numbers"
   - Change the numbers
   - SOLVE the problem yourself and verify the answer
   - Make sure your correct answer is one of your 4 options

Respond with ONLY valid JSON:
{{
    "generation_strategy": "rephrase_only" | "rephrase_with_new_numbers",
    "original_topic": "<topic>",
    "original_subject": "Physics" | "Chemistry" | "Mathematics",
    "generated_question": "<question with LaTeX>",
    "options": ["<opt1>", "<opt2>", "<opt3>", "<opt4>"],
    "correct_index": <1-4>,
    "explanation": "<explain why answer is correct, show calculation if numbers changed>",
    "difficulty_estimate": "easy" | "medium" | "hard"
}}

For INTEGER-TYPE questions (no options), use this format instead:
{{
    "generation_strategy": "rephrase_only",
    "original_topic": "<topic>",
    "original_subject": "Physics" | "Chemistry" | "Mathematics",
    "generated_question": "<question with LaTeX, ending with blank line for answer>",
    "correct_answer": <same integer as original>,
    "explanation": "<explanation>",
    "difficulty_estimate": "easy" | "medium" | "hard"
}}"""


def load_clean_dataset() -> List[Dict[str, Any]]:
    """Load all questions from the clean dataset."""
    questions = []
    with CLEAN_DATASET.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    return questions


def format_options_section(rec: Dict[str, Any]) -> str:
    """Format options for the prompt."""
    options = rec.get("options", [])
    if not options:
        return "**Type:** Integer/Numerical (no options)"
    
    lines = ["**Options:**"]
    for i, opt in enumerate(options, 1):
        lines.append(f"  ({i}) {opt}")
    return "\n".join(lines)


def format_correct_answer(rec: Dict[str, Any]) -> str:
    """Format the correct answer for the prompt."""
    correct_idx = rec.get("correct_index")
    options = rec.get("options", [])
    
    if rec.get("question_type") == "integer":
        return f"{correct_idx} (integer answer)"
    
    if correct_idx and options and 1 <= correct_idx <= len(options):
        return f"Option ({correct_idx}): {options[correct_idx - 1]}"
    
    return f"Option ({correct_idx})" if correct_idx else "Unknown"


def generate_new_question(client: OpenAI, rec: Dict[str, Any]) -> Dict[str, Any]:
    """Call GPT-4o-mini to generate a new question based on the original."""
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        question_type=rec.get("question_type", "mcq").upper(),
        question_text=rec.get("question_text", ""),
        options_section=format_options_section(rec),
        correct_answer=format_correct_answer(rec),
    )
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=1500,
    )
    
    content = response.choices[0].message.content.strip()
    
    # Try to parse JSON from the response
    try:
        # Handle potential markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        generated = json.loads(content)
        generated["_raw_response"] = content
        generated["_success"] = True
        return generated
    except json.JSONDecodeError as e:
        # LLM returns LaTeX with single backslashes (e.g., \frac, \pi, \sqrt)
        # These are invalid JSON escapes. We need to double all backslashes.
        try:
            import re
            # First, protect already-escaped sequences (\\) by replacing with placeholder
            placeholder = "\x00DOUBLE_BACKSLASH\x00"
            fixed = content.replace("\\\\", placeholder)
            # Now double all remaining single backslashes
            fixed = fixed.replace("\\", "\\\\")
            # Restore the original double backslashes (they become quadruple, so fix to double)
            fixed = fixed.replace(placeholder, "\\\\")
            
            generated = json.loads(fixed)
            generated["_raw_response"] = content
            generated["_success"] = True
            return generated
        except json.JSONDecodeError:
            pass
        
        return {
            "_success": False,
            "_error": str(e),
            "_raw_response": content,
        }


def main():
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment.")
        print("Please set it in .env file or environment variables.")
        return
    
    client = OpenAI(api_key=api_key)
    
    # Load dataset
    print(f"Loading dataset from: {CLEAN_DATASET}")
    questions = load_clean_dataset()
    print(f"Loaded {len(questions)} questions.")
    
    # Filter to MCQ only for this prototype (simpler)
    mcq_questions = [q for q in questions if q.get("question_type") == "mcq"]
    print(f"Found {len(mcq_questions)} MCQ questions.")
    
    # Random sample
    sample = random.sample(mcq_questions, min(NUM_QUESTIONS, len(mcq_questions)))
    print(f"\nSelected {len(sample)} questions for generation:\n")
    
    results = []
    
    for i, rec in enumerate(sample, 1):
        qnum = rec.get("question_number")
        print(f"[{i}/{len(sample)}] Processing Q{qnum}...")
        print(f"  Original: {rec.get('question_text', '')[:80]}...")
        
        generated = generate_new_question(client, rec)
        
        result = {
            "original": {
                "question_number": qnum,
                "question_text": rec.get("question_text"),
                "options": rec.get("options"),
                "correct_index": rec.get("correct_index"),
            },
            "generated": generated,
        }
        results.append(result)
        
        if generated.get("_success"):
            print(f"  ✓ Generated: {generated.get('generation_strategy', 'unknown')}")
            print(f"    Topic: {generated.get('original_topic', 'N/A')}")
            print(f"    Subject: {generated.get('original_subject', 'N/A')}")
        else:
            print(f"  ✗ Error: {generated.get('_error', 'unknown')}")
        print()
    
    # Save results
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {OUTPUT_FILE}")
    
    # Print summary
    successful = sum(1 for r in results if r["generated"].get("_success"))
    print(f"\nSummary: {successful}/{len(results)} questions generated successfully.")


if __name__ == "__main__":
    main()
