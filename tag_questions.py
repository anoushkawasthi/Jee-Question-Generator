"""
LLM Meta-tagging for JEE Questions (v2)

Tags each question with:
- subject: Physics | Chemistry | Mathematics
- topic: Specific topic (e.g., "Kinematics", "Organic Chemistry", "Calculus")
- difficulty: easy | medium | hard

Uses GPT-4o-mini for cost efficiency.

Input: dataset_v2/all_papers_clean.jsonl
Output: dataset_v2/all_papers_tagged.jsonl

Usage:
    python tag_questions.py
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

INPUT_FILE = Path("dataset_v2/all_papers_clean.jsonl")
OUTPUT_FILE = Path("dataset_v2/all_papers_tagged.jsonl")
PROGRESS_FILE = Path("dataset_v2/tagging_progress.json")

MODEL = "gpt-4o-mini"
BATCH_SIZE = 10  # Process 10 questions per API call for efficiency

# ============================================================================
# Prompts
# ============================================================================

SYSTEM_PROMPT = """You are an expert JEE exam analyzer. Your task is to classify JEE Main questions.

For each question, determine:
1. **subject**: Exactly one of: "Physics", "Chemistry", "Mathematics"
2. **topic**: A specific topic within that subject (e.g., "Kinematics", "Thermodynamics", "Organic Chemistry - Reactions", "Matrices", "Calculus - Integration")
3. **difficulty**: One of: "easy", "medium", "hard"
   - easy: Direct formula application, single concept
   - medium: Multiple concepts, moderate calculations
   - hard: Complex multi-step reasoning, advanced concepts

Respond with ONLY valid JSON array. No markdown, no extra text."""

USER_PROMPT_TEMPLATE = """Classify these {count} JEE questions:

{questions_json}

Respond with a JSON array of {count} objects in the SAME ORDER:
[
  {{"id": <question_id>, "subject": "...", "topic": "...", "difficulty": "..."}},
  ...
]"""


# ============================================================================
# Helper Functions
# ============================================================================

def load_dataset() -> List[Dict[str, Any]]:
    """Load questions from JSONL file."""
    questions = []
    with INPUT_FILE.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if line:
                q = json.loads(line)
                q["_idx"] = i  # Add index for tracking
                questions.append(q)
    return questions


def load_progress() -> Dict[str, Any]:
    """Load progress from checkpoint file."""
    if PROGRESS_FILE.exists():
        with PROGRESS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_indices": [], "results": {}}


def save_progress(progress: Dict[str, Any]):
    """Save progress to checkpoint file."""
    with PROGRESS_FILE.open("w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)


def format_question_for_prompt(q: Dict[str, Any]) -> Dict[str, Any]:
    """Format a question for the LLM prompt."""
    result = {
        "id": q["_idx"],
        "question": q["question_text"][:500],  # Truncate long questions
        "type": q["question_type"],
    }
    if q.get("options"):
        result["options"] = q["options"][:4]  # First 4 options
    return result


def parse_llm_response(content: str, expected_count: int) -> List[Dict[str, Any]]:
    """Parse LLM response, handling potential issues."""
    content = content.strip()
    
    # Handle markdown code blocks
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    
    # Fix LaTeX backslashes for JSON parsing
    placeholder = "\x00DOUBLE_BACKSLASH\x00"
    fixed = content.replace("\\\\", placeholder)
    fixed = fixed.replace("\\", "\\\\")
    fixed = fixed.replace(placeholder, "\\\\")
    
    try:
        results = json.loads(fixed)
        if isinstance(results, list) and len(results) == expected_count:
            return results
    except json.JSONDecodeError:
        pass
    
    # Return empty results on parse failure
    return []


def tag_batch(client: OpenAI, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tag a batch of questions using the LLM."""
    
    # Format questions for prompt
    formatted = [format_question_for_prompt(q) for q in questions]
    questions_json = json.dumps(formatted, indent=2, ensure_ascii=False)
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        count=len(questions),
        questions_json=questions_json
    )
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,  # Lower temperature for more consistent classification
            max_tokens=2000,
        )
        
        content = response.choices[0].message.content.strip()
        results = parse_llm_response(content, len(questions))
        
        if results:
            return results
        else:
            print(f"    Warning: Failed to parse response, returning defaults")
            return [{"id": q["_idx"], "subject": "Unknown", "topic": "Unknown", "difficulty": "medium"} for q in questions]
            
    except Exception as e:
        print(f"    Error calling API: {e}")
        return [{"id": q["_idx"], "subject": "Unknown", "topic": "Unknown", "difficulty": "medium"} for q in questions]


# ============================================================================
# Main Pipeline
# ============================================================================

def run_tagging():
    """Main entry point for LLM tagging."""
    
    print("=" * 60)
    print("JEE Question Meta-Tagging (v2)")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment.")
        return
    
    client = OpenAI(api_key=api_key)
    
    # Load dataset
    print(f"\nLoading dataset from: {INPUT_FILE}")
    questions = load_dataset()
    print(f"Loaded {len(questions)} questions.")
    
    # Load progress
    progress = load_progress()
    completed = set(progress.get("completed_indices", []))
    results = progress.get("results", {})
    
    print(f"Already completed: {len(completed)} questions")
    
    # Filter to remaining questions
    remaining = [q for q in questions if q["_idx"] not in completed]
    print(f"Remaining to tag: {len(remaining)} questions")
    
    if not remaining:
        print("All questions already tagged!")
    else:
        # Process in batches
        total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_num in range(total_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(remaining))
            batch = remaining[start_idx:end_idx]
            
            print(f"\n[Batch {batch_num + 1}/{total_batches}] Processing {len(batch)} questions...")
            
            batch_results = tag_batch(client, batch)
            
            # Store results
            for result in batch_results:
                idx = result.get("id")
                if idx is not None:
                    results[str(idx)] = {
                        "subject": result.get("subject", "Unknown"),
                        "topic": result.get("topic", "Unknown"),
                        "difficulty": result.get("difficulty", "medium"),
                    }
                    completed.add(idx)
            
            # Save progress after each batch
            progress["completed_indices"] = list(completed)
            progress["results"] = results
            save_progress(progress)
            
            print(f"  Tagged {len(batch_results)} questions. Total: {len(completed)}/{len(questions)}")
            
            # Small delay to avoid rate limiting
            if batch_num < total_batches - 1:
                time.sleep(0.5)
    
    # Write final tagged dataset
    print(f"\n{'=' * 60}")
    print(f"Writing tagged dataset to: {OUTPUT_FILE}")
    
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for q in questions:
            idx = str(q["_idx"])
            if idx in results:
                q["subject"] = results[idx]["subject"]
                q["topic"] = results[idx]["topic"]
                q["difficulty"] = results[idx]["difficulty"]
            else:
                q["subject"] = "Unknown"
                q["topic"] = "Unknown"
                q["difficulty"] = "medium"
            
            # Remove internal tracking field
            del q["_idx"]
            
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    
    # Print summary
    subjects = {}
    difficulties = {}
    for idx, data in results.items():
        subj = data.get("subject", "Unknown")
        diff = data.get("difficulty", "medium")
        subjects[subj] = subjects.get(subj, 0) + 1
        difficulties[diff] = difficulties.get(diff, 0) + 1
    
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total questions tagged: {len(results)}")
    print(f"\nBy Subject:")
    for subj, count in sorted(subjects.items()):
        print(f"  {subj}: {count}")
    print(f"\nBy Difficulty:")
    for diff, count in sorted(difficulties.items()):
        print(f"  {diff}: {count}")
    
    print(f"\nOutput: {OUTPUT_FILE}")
    
    # Clean up progress file on completion
    if len(completed) == len(questions):
        print("\nTagging complete! Removing progress file.")
        PROGRESS_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    run_tagging()
