"""
LLM-based Question Transformation (2-Step Process)

Step 1: Classification - Determine what to do with each question
Step 2: Transformation - Apply the appropriate transformation

Tags:
- change_numbers: Change numerical values, recompute answer, update options
- rephrase: Reword the question, keep values/answer same  
- fix_incomplete: LLM can fix missing parts
- discard: Unfixable, pick another question from pool

Usage:
    from llm_transform import transform_questions
    transformed = transform_questions(selected_questions, pool)
"""

from __future__ import annotations

import json
import os
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

MODEL = "gpt-4o-mini"
CLASSIFICATION_BATCH_SIZE = 10

# ============================================================================
# Step 1: Classification
# ============================================================================

CLASSIFY_SYSTEM_PROMPT = """You are a JEE exam question analyzer. Your task is to classify each question for transformation.

For each question, determine the best action:

1. **change_numbers**: The question has numerical values that can be changed while keeping the same concept. The answer can be recomputed. Good for physics calculations, math problems with specific numbers.
   - Example: "A ball is thrown at 20 m/s..." → can change to 25 m/s and recompute

2. **rephrase**: The question should be reworded but values/formulas must stay the same. Good for conceptual questions, chemistry reactions, complex derivations.
   - Example: "Which of the following is correct about..." → rephrase the wording only

3. **fix_incomplete**: The question has missing information (statements, lists, etc.) but you can reasonably reconstruct it from context.
   - Example: Missing "Statement A, B, C" but options reference them → can reconstruct

4. **discard**: The question is unfixable - references images, diagrams, graphs we don't have, or is too incomplete to reconstruct.
   - Example: "From the graph shown..." → cannot fix without the graph

Rules:
- Chemistry equations/reactions → always "rephrase" (don't change formulas)
- Math with specific numbers → "change_numbers" if computation is straightforward
- Physics with numerical values → "change_numbers" if formula is standard
- Conceptual/theory questions → "rephrase"
- Integer type questions with calculations → "change_numbers"

Respond with ONLY valid JSON array. No markdown."""

CLASSIFY_USER_TEMPLATE = """Classify these {count} JEE questions:

{questions_json}

Respond with a JSON array of {count} objects in the SAME ORDER:
[
  {{"id": <id>, "action": "change_numbers|rephrase|fix_incomplete|discard", "reason": "brief reason"}},
  ...
]"""


def classify_questions(
    client: OpenAI,
    questions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Step 1: Classify questions into action categories.
    Returns list of {id, action, reason} for each question.
    """
    results = []
    
    # Process in batches
    for i in range(0, len(questions), CLASSIFICATION_BATCH_SIZE):
        batch = questions[i:i + CLASSIFICATION_BATCH_SIZE]
        
        # Format questions for prompt
        questions_for_prompt = []
        for j, q in enumerate(batch):
            questions_for_prompt.append({
                "id": i + j,
                "subject": q.get("subject", ""),
                "question_type": q.get("question_type", "mcq"),
                "question_text": q.get("question_text", "")[:500],  # Truncate long questions
                "options": q.get("options", [])[:4],
            })
        
        user_prompt = CLASSIFY_USER_TEMPLATE.format(
            count=len(batch),
            questions_json=json.dumps(questions_for_prompt, indent=2)
        )
        
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            
            content = response.choices[0].message.content.strip()
            
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            batch_results = json.loads(content)
            results.extend(batch_results)
            
        except Exception as e:
            print(f"  Classification error: {e}")
            # Default to rephrase for failed batch
            for j in range(len(batch)):
                results.append({"id": i + j, "action": "rephrase", "reason": "classification failed"})
    
    return results


# ============================================================================
# Step 2: Transformation
# ============================================================================

# Use GPT-4o-mini for cost efficiency
TRANSFORM_MODEL = "gpt-4o-mini"

LATEX_RULES = """
CRITICAL LaTeX FORMATTING RULES (MUST FOLLOW):
1. EVERY math expression MUST be wrapped in $...$ (single dollar signs)
2. Powers/exponents: $10^{-3}$ or $x^{2}$ - ALWAYS use braces {} after ^
3. Subscripts: $v_{max}$ or $F_{net}$ - ALWAYS use braces {} after _
4. Fractions: $\\frac{numerator}{denominator}$
5. Greek letters: $\\alpha$, $\\beta$, $\\gamma$, $\\delta$, $\\theta$, $\\mu$, $\\lambda$, $\\omega$, $\\pi$, $\\varepsilon$
6. Scientific notation: $3 \\times 10^{-4}$ (use \\times, NOT ×)
7. Square root: $\\sqrt{expression}$
8. Units with powers: m/s or m s$^{-1}$, kg m$^{-3}$
9. Vectors: $\\vec{F}$ or $\\vec{v}$
10. Trigonometry: $\\sin\\theta$, $\\cos\\theta$, $\\tan\\theta$

MATH EXPRESSIONS MUST BE COMPLETE - NOT FRAGMENTED:
CORRECT: $T^{2} = 4\\pi^{2} \\frac{m}{k\\lambda q r^{3}}$
WRONG: T $^{2}$ = 4 $\\pi^{2}$ $m$ $k$ $\\lambda$ (broken math!)

CORRECT: $v = \\sqrt{\\frac{2gR}{5}}$
WRONG: v = $\\sqrt{}$ $\\frac{}{}$ 2 g R 5 (broken!)

CORRECT: $F = \\frac{kq_1 q_2}{r^{2}}$
WRONG: F = $\\frac{}{}$ $k$ $q_1$ $q_2$ $r^{2}$ (NO!)

FORBIDDEN (will cause compilation errors):
- Unicode symbols: × − √ α β γ θ (use LaTeX commands instead)
- Bare powers: 10^-3 (must be $10^{-3}$)
- Unclosed dollar signs: $x without closing $
- Unbalanced braces: $\\frac{a}{b$ (missing closing brace)
- Fragmented math: putting each variable/symbol in separate $...$ 
- textasciicircum: use ^ inside math mode instead

VALIDATION BEFORE RESPONDING:
✓ Each complete mathematical expression is in ONE $...$ pair
✓ Every $ has a matching closing $
✓ Every { has a matching }
✓ No Unicode math symbols
"""

CHANGE_NUMBERS_SYSTEM = """You are a JEE exam question creator. Modify numerical values and recompute the answer.

""" + LATEX_RULES + """

TASK:
1. Change the numerical values in the question (keep same order of magnitude, reasonable physics/chemistry/math values)
2. RECOMPUTE the correct answer based on the new values - this is critical!
3. Update ALL four options (correct answer should be at position A, B, C, or D randomly)
4. Keep the same concept and structure

Respond with ONLY a valid JSON object. No markdown code blocks."""

CHANGE_NUMBERS_USER = """Modify this {subject} question by changing numerical values:

Question: {question}
Type: {qtype}
Options: {options}
Current Answer: {answer}

REMEMBER:
- Wrap ALL math in $...$
- Use $\\times$ not ×
- Use $10^{{-3}}$ not 10^-3
- Recompute answer correctly with new values
- All 4 options must be complete

Respond with JSON only:
{{"question_text": "...", "options": ["A", "B", "C", "D"], "correct_answer": "A/B/C/D"}}"""


REPHRASE_SYSTEM = """You are a JEE exam question writer. Rephrase questions using different words while preserving meaning.

""" + LATEX_RULES + """

TASK:
1. Rephrase the question text using different words/sentence structure
2. DO NOT change any numbers, values, or formulas
3. Keep all 4 options EXACTLY the same (only fix LaTeX formatting if broken)
4. Keep the correct answer unchanged
5. Fix any Unicode symbols to proper LaTeX

Respond with ONLY a valid JSON object. No markdown code blocks."""

REPHRASE_USER = """Rephrase this {subject} question (fix any LaTeX issues):

Question: {question}
Options: {options}
Answer: {answer}

REMEMBER:
- Keep numbers/values identical
- Fix any Unicode to LaTeX
- All 4 options must be complete and unchanged
- Wrap math in $...$

Respond with JSON only:
{{"question_text": "...", "options": ["same as input", "...", "...", "..."], "correct_answer": "same as input"}}"""


FIX_INCOMPLETE_SYSTEM = """You are a JEE exam expert. Fix incomplete questions by reconstructing missing parts.

""" + LATEX_RULES + """

TASK:
1. If statements A, B, C, D, E are referenced but missing - CREATE appropriate statements based on the topic and options
2. If a "Match List I with List II" is incomplete - CREATE both lists logically
3. Make the question COMPLETE and SELF-CONTAINED
4. Preserve the correct answer

Respond with ONLY a valid JSON object. No markdown code blocks."""

FIX_INCOMPLETE_USER = """Fix this incomplete {subject} question by adding missing parts:

Question: {question}
Options: {options}
Answer: {answer}

The question seems incomplete. Reconstruct any missing parts.

Return JSON:
{{
  "question_text": "complete question with all parts...",
  "options": [...],
  "correct_answer": "..."
}}"""


def fix_latex_formatting(text) -> str:
    """Post-process to fix common LaTeX issues."""
    import re
    
    # Handle non-string types
    if text is None:
        return ""
    if not isinstance(text, str):
        return str(text)
    
    if not text:
        return text
    
    # Replace Unicode symbols with LaTeX
    replacements = [
        ('×', r' \times '),
        ('−', '-'),
        ('–', '-'),
        ('—', '-'),
        ('√', r'\sqrt'),
        ('α', r'\alpha'),
        ('β', r'\beta'),
        ('γ', r'\gamma'),
        ('δ', r'\delta'),
        ('θ', r'\theta'),
        ('λ', r'\lambda'),
        ('μ', r'\mu'),
        ('π', r'\pi'),
        ('ω', r'\omega'),
        ('Ω', r'\Omega'),
        ('ε', r'\varepsilon'),
        ('°', r'^{\circ}'),
        ('±', r'\pm'),
        ('≠', r'\neq'),
        ('≤', r'\leq'),
        ('≥', r'\geq'),
        ('→', r'\rightarrow'),
        ('∞', r'\infty'),
        ('ℎ', 'h'),  # Planck's constant Unicode
    ]
    
    for old, new in replacements:
        text = text.replace(old, new)
    
    # Fix Unicode math italic letters (𝐴, 𝐵, etc.)
    def replace_math_unicode(match):
        char = match.group(0)
        code = ord(char)
        # Math italic uppercase (U+1D434 onwards)
        if 0x1D434 <= code <= 0x1D44D:
            letter = chr(ord('A') + (code - 0x1D434))
            return letter
        # Math italic lowercase (U+1D44E onwards)
        elif 0x1D44E <= code <= 0x1D467:
            letter = chr(ord('a') + (code - 0x1D44E))
            return letter
        # Math bold uppercase
        elif 0x1D400 <= code <= 0x1D419:
            letter = chr(ord('A') + (code - 0x1D400))
            return letter
        # Math bold lowercase
        elif 0x1D41A <= code <= 0x1D433:
            letter = chr(ord('a') + (code - 0x1D41A))
            return letter
        return char
    
    text = re.sub(r'[\U0001D400-\U0001D7FF]', replace_math_unicode, text)
    
    # Fix \u escape sequences that weren't decoded
    text = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), text)
    
    # Fix textasciicircum to proper power notation
    text = re.sub(r'\\textasciicircum\{\}(-?\d+)', r'^{\1}', text)
    text = re.sub(r'\\textasciicircum\{\}', '^', text)
    
    # MERGE FRAGMENTED MATH: Convert "$a$ $b$ $c$" to "$a b c$"
    # This handles the common LLM mistake of fragmenting expressions
    def merge_adjacent_math(text):
        # Pattern: $...$ followed by space(s) and another $...$
        # Merge them into one block
        while True:
            new_text = re.sub(r'\$([^$]+)\$\s*\$([^$]+)\$', r'$\1 \2$', text)
            if new_text == text:
                break
            text = new_text
        return text
    
    text = merge_adjacent_math(text)
    
    # Fix bare powers like 10^-3 to 10^{-3} (inside math mode)
    text = re.sub(r'\^(-?\d+)(?![}\d])', r'^{\1}', text)
    
    # Fix bare subscripts like x_max to x_{max}
    text = re.sub(r'_([a-zA-Z]{2,})(?![}])', r'_{\1}', text)
    
    # Clean up double dollar signs
    text = text.replace('$$', '$')
    
    # Clean up spaces around operators inside math
    text = re.sub(r'\$\s+', '$', text)
    text = re.sub(r'\s+\$', '$', text)
    
    # Remove \mathbb which shouldn't be in JEE
    text = re.sub(r'\\mathbb\{([A-Z])\}', r'\1', text)
    
    return text


def validate_latex(text: str) -> Tuple[bool, str]:
    """
    Validate that LaTeX is properly formatted.
    Returns (is_valid, error_message).
    Only reject truly broken output - prefer fixing over rejecting.
    """
    if not text:
        return True, ""
    
    # Check for balanced $ signs - CRITICAL
    dollar_count = text.count('$')
    if dollar_count % 2 != 0:
        return False, "Unbalanced $ signs"
    
    # Check for balanced braces - CRITICAL
    brace_count = 0
    for char in text:
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        if brace_count < 0:
            return False, "Unbalanced braces (extra })"
    if brace_count != 0:
        return False, "Unbalanced braces (missing })"
    
    # Check for \mathbb which shouldn't be in JEE questions  
    if '\\mathbb' in text:
        return False, "Contains \\mathbb (broken output)"
    
    # Check for severely fragmented math: pattern like "$a$ $b$ $c$ $d$ $e$"
    # More than 5 tiny consecutive math blocks is a sign of broken output
    if re.search(r'(\$[^$]{1,2}\$\s*){5,}', text):
        return False, "Severely fragmented math"
    
    return True, ""


def validate_transformed_question(q: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate a transformed question has valid LaTeX."""
    
    # Check question text
    is_valid, error = validate_latex(q.get("question_text", ""))
    if not is_valid:
        return False, f"Question text: {error}"
    
    # Check each option
    for i, opt in enumerate(q.get("options", [])):
        is_valid, error = validate_latex(opt)
        if not is_valid:
            return False, f"Option {i+1}: {error}"
    
    # Check we have 4 options for MCQ
    if q.get("question_type") == "mcq":
        if len(q.get("options", [])) < 4:
            return False, "Less than 4 options"
    
    return True, ""


def transform_single_question(
    client: OpenAI,
    question: Dict[str, Any],
    action: str,
) -> Optional[Dict[str, Any]]:
    """Apply transformation to a single question based on action."""
    
    subject = question.get("subject", "")
    qtype = question.get("question_type", "mcq")
    q_text = question.get("question_text", "")
    options = question.get("options", [])
    
    # Get correct answer
    if qtype == "mcq":
        correct_idx = question.get("correct_index")
        if correct_idx and options:
            answer = f"Option {correct_idx}: {options[correct_idx-1] if correct_idx <= len(options) else '?'}"
        else:
            answer = "Unknown"
    else:
        answer = str(question.get("correct_answer", "Unknown"))
    
    options_str = json.dumps(options[:4]) if options else "[]"
    
    # Select prompt based on action
    if action == "change_numbers":
        system = CHANGE_NUMBERS_SYSTEM
        user = CHANGE_NUMBERS_USER.format(
            subject=subject,
            question=q_text,
            qtype=qtype,
            options=options_str,
            answer=answer
        )
    elif action == "rephrase":
        system = REPHRASE_SYSTEM
        user = REPHRASE_USER.format(
            subject=subject,
            question=q_text,
            options=options_str,
            answer=answer
        )
    elif action == "fix_incomplete":
        system = FIX_INCOMPLETE_SYSTEM
        user = FIX_INCOMPLETE_USER.format(
            subject=subject,
            question=q_text,
            options=options_str,
            answer=answer
        )
    else:
        return None  # discard
    
    try:
        response = client.chat.completions.create(
            model=TRANSFORM_MODEL,  # Use GPT-4o for better quality
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,  # Lower temperature for more consistent formatting
            max_tokens=2000,
        )
        
        content = response.choices[0].message.content.strip()
        
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
        
        result = json.loads(fixed)
        
        # Apply LaTeX post-processing
        processed_text = fix_latex_formatting(result.get("question_text", q_text))
        processed_options = [fix_latex_formatting(opt) for opt in result.get("options", options)]
        
        # Build transformed question
        transformed = {
            **question,  # Keep original metadata
            "question_text": processed_text,
            "options": processed_options,
            "transform_action": action,
        }
        
        # Handle answer
        new_answer = result.get("correct_answer", "")
        if qtype == "mcq":
            # Parse answer like "A", "B", "C", "D" or "Option 1", etc.
            if new_answer in ["A", "B", "C", "D"]:
                transformed["correct_index"] = ord(new_answer) - ord("A") + 1
            elif new_answer in ["1", "2", "3", "4"]:
                transformed["correct_index"] = int(new_answer)
            else:
                # Try to find answer in options
                for i, opt in enumerate(result.get("options", [])):
                    if new_answer in opt or opt in new_answer:
                        transformed["correct_index"] = i + 1
                        break
        else:
            # Integer type - extract number
            try:
                transformed["correct_answer"] = int(re.search(r'-?\d+', str(new_answer)).group())
            except:
                transformed["correct_answer"] = question.get("correct_answer")
        
        # VALIDATION: Check if the transformed question has valid LaTeX
        is_valid, error = validate_transformed_question(transformed)
        if not is_valid:
            print(f"    Validation failed ({action}): {error}")
            print(f"    -> Falling back to original question")
            # Return original with a note
            question["transform_action"] = "fallback_original"
            return question
        
        return transformed
        
    except Exception as e:
        print(f"    Transform error ({action}): {e}")
        # Fallback to original instead of returning None
        question["transform_action"] = "error_fallback"
        return question


# ============================================================================
# Main Pipeline
# ============================================================================

def transform_questions(
    selected: List[Dict[str, Any]],
    pool: List[Dict[str, Any]],
    target_count: int = 90,
) -> List[Dict[str, Any]]:
    """
    Main transformation pipeline.
    
    1. Classify all selected questions
    2. Discard unfixable ones, pick replacements from pool
    3. Transform each question according to its action
    
    Returns list of transformed questions.
    """
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not found, returning original questions")
        return selected
    
    client = OpenAI(api_key=api_key)
    
    print(f"\n{'='*60}")
    print("LLM Transformation Pipeline")
    print(f"{'='*60}")
    
    # Track what we're working with
    working_set = list(selected)
    pool_remaining = [q for q in pool if q not in selected]
    random.shuffle(pool_remaining)
    
    # Step 1: Classification
    print(f"\nStep 1: Classifying {len(working_set)} questions...")
    classifications = classify_questions(client, working_set)
    
    # Count actions
    action_counts = {}
    for c in classifications:
        action = c.get("action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
    print(f"  Classifications: {action_counts}")
    
    # Handle discards - replace with questions from pool
    discarded_indices = [c["id"] for c in classifications if c.get("action") == "discard"]
    
    if discarded_indices:
        print(f"\n  Replacing {len(discarded_indices)} discarded questions...")
        
        for idx in sorted(discarded_indices, reverse=True):
            if pool_remaining:
                replacement = pool_remaining.pop(0)
                working_set[idx] = replacement
                # Re-classify the replacement (default to rephrase for safety)
                classifications[idx] = {"id": idx, "action": "rephrase", "reason": "replacement"}
            else:
                print(f"    Warning: Pool exhausted, keeping original question")
                classifications[idx] = {"id": idx, "action": "rephrase", "reason": "no replacement available"}
    
    # Step 2: Transform each question
    print(f"\nStep 2: Transforming questions...")
    transformed = []
    
    for i, (q, c) in enumerate(zip(working_set, classifications)):
        action = c.get("action", "rephrase")
        
        if action == "discard":
            action = "rephrase"  # Fallback
        
        print(f"  [{i+1}/{len(working_set)}] {action}...", end="\r")
        
        result = transform_single_question(client, q, action)
        
        # transform_single_question now always returns a question (with fallback)
        transformed.append(result)
    
    print(f"  Transformed {len(transformed)} questions" + " " * 20)
    
    # Summary
    transform_counts = {}
    for q in transformed:
        action = q.get("transform_action", "unknown")
        transform_counts[action] = transform_counts.get(action, 0) + 1
    print(f"\n  Final: {transform_counts}")
    
    return transformed


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    import json
    from pathlib import Path
    
    # Load a few questions for testing
    questions = []
    with Path("dataset_v2/all_papers_tagged.jsonl").open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            if line.strip():
                questions.append(json.loads(line))
    
    print("Testing with 5 questions...")
    transformed = transform_questions(questions, [], target_count=5)
    
    print("\n" + "="*60)
    print("Results:")
    for q in transformed:
        print(f"\n[{q.get('transform_action', '?')}] {q.get('subject')}")
        print(f"  Q: {q.get('question_text', '')[:100]}...")
