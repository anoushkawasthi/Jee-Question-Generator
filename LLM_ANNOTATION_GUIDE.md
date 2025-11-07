# LLM Annotation Pipeline - Phase 2 Guide

## Overview

The LLM Annotation Pipeline adds AI-generated metadata to extracted questions, enriching them with difficulty levels, key concepts, solution approaches, and time estimates. This transforms raw question data into a fully annotated dataset ready for ML applications.

**Status**: Phase 2 - Implementation Ready
**Input**: `all_questions_consolidated.json` (output from Phase 1)
**Output**: `all_questions_consolidated_annotated.json`
**Processing Time**: ~2-3 minutes per 100 questions (with API rate limiting)

---

## Quick Start

### Prerequisites

Install required packages:
```bash
# For Claude (Anthropic)
pip install anthropic

# For GPT-4 (OpenAI)
pip install openai
```

Set up API keys:
```bash
# Linux/Mac
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:OPENAI_API_KEY = "sk-..."
```

### Basic Usage

**Test with 10 questions (Claude)**:
```bash
python run_llm_annotation.py --sample 10
```

**Annotate all questions (Claude)**:
```bash
python run_llm_annotation.py \
  --json-file data/processed/nougat_parsed/all_questions_consolidated.json
```

**Use OpenAI's GPT-4o instead**:
```bash
python run_llm_annotation.py --provider openai --sample 10
```

**Custom output file**:
```bash
python run_llm_annotation.py \
  --json-file questions.json \
  --output my_annotated_output.json
```

---

## How It Works

### Pipeline Architecture

```
1. Load Questions
   ↓
2. For each question:
   - Build annotation prompt
   - Send to LLM API (Claude or GPT-4)
   - Parse JSON response
   - Add ml_annotations field
   ↓
3. Save enriched JSON
```

### Annotation Fields

Each question gets a new `ml_annotations` object:

```json
{
  "question_id": "2024-physics-001",
  "question_latex": "A charged particle...",
  "options": [...],
  "correct_answer": "2",
  
  "ml_annotations": {
    "difficulty": "Medium",
    "concepts": ["circular motion", "magnetic force", "Lorentz force"],
    "solution_approach": "Use F = qvB sin(θ) to find the force direction, then apply circular motion equations",
    "key_insight": "The magnetic force is always perpendicular to velocity, causing circular motion",
    "computable_solution": true,
    "estimated_time_seconds": 120
  }
}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `difficulty` | String | "Easy", "Medium", or "Hard" |
| `concepts` | Array | List of physics/chemistry/math concepts tested |
| `solution_approach` | String | Brief description of how to solve the problem |
| `key_insight` | String | Key insight or trick needed to solve efficiently |
| `computable_solution` | Boolean | True if solvable with direct computation, False if requires conceptual reasoning |
| `estimated_time_seconds` | Integer | Expected time to solve (30-300 seconds) |

---

## API Configuration

### Claude (Recommended)

**Model**: Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)
**Advantages**:
- Excellent reasoning for physics/math problems
- Good understanding of LaTeX notation
- Reasonable pricing (~$0.003 per question)
- JSON response quality: 98%+

**Cost Estimate**:
- 1,800 questions × $0.003 ≈ $5.40
- Processing time: ~30 minutes

**Setup**:
```bash
export ANTHROPIC_API_KEY="your-key-here"
python run_llm_annotation.py
```

### GPT-4o (Alternative)

**Model**: gpt-4o
**Advantages**:
- Superior image understanding if needed later
- Highest quality responses

**Cost Estimate**:
- 1,800 questions × $0.015 ≈ $27
- Processing time: ~40 minutes

**Setup**:
```bash
export OPENAI_API_KEY="your-key-here"
python run_llm_annotation.py --provider openai
```

### Comparing Providers

| Aspect | Claude | GPT-4o |
|--------|--------|--------|
| Cost per question | $0.003 | $0.015 |
| Speed | Fast | Fast |
| Reasoning quality | Excellent | Excellent |
| JSON compliance | 98% | 99% |
| Recommended | ✅ Yes | Alternative |

---

## Usage Patterns

### Pattern 1: Small Test (Recommended First Step)

Test with 10 questions to verify setup:
```bash
python run_llm_annotation.py --provider anthropic --sample 10
```

**Expected output**:
```
======================================================================
LLM ANNOTATION PIPELINE - ANTHROPIC
======================================================================

📂 Loading: data/processed/nougat_parsed/all_questions_consolidated.json
📊 Total questions: 1805
🎲 Processing sample of 10 questions...

  [   10/  10] ✅ 10 | ❌ 0 | ETA: 0s

======================================================================
✅ ANNOTATION COMPLETE
======================================================================
✅ Successful: 10
❌ Failed: 0
⏱️  Time elapsed: 45.3s
⚡ Rate: 0.22 q/s

📁 Output: data/processed/nougat_parsed/all_questions_consolidated_annotated.json
```

### Pattern 2: Full Production Run

After verifying with sample, run full pipeline:
```bash
python run_llm_annotation.py --provider anthropic
```

**Timeline**:
- 10 questions: ~45s
- 100 questions: ~7 minutes
- 1,800 questions: ~2 hours

**Cost**: ~$5-6 for full dataset

### Pattern 3: Resume from Checkpoint

If interrupted, restart and skip already-annotated questions:
```bash
python run_llm_annotation.py --skip-existing
```

This continues where you left off without re-processing.

### Pattern 4: Custom Output Location

For different project organization:
```bash
python run_llm_annotation.py \
  --json-file data/processed/nougat_parsed/all_questions_consolidated.json \
  --output artifacts/fully_annotated_questions.json
```

---

## Error Handling

### Common Issues

**1. API Key Not Found**
```
❌ Error: OpenAI API key not set
```
**Solution**: 
```bash
export OPENAI_API_KEY="sk-..."
# or
$env:OPENAI_API_KEY = "sk-..."
```

**2. JSON Parse Errors**
```
⚠️  Failed to parse JSON response: Expecting value: line 1 column 1
```
**Causes**: API returned malformed JSON (rare)
**Solution**: Increases `estimated_time_seconds` for that question; continues processing

**3. API Rate Limit Hit**
```
openai.error.RateLimitError: Rate limit exceeded
```
**Solution**: Built-in 0.5s delays between requests; occurs after ~10 min continuous use
**Workaround**: Let pipeline pause and retry automatically (built in)

**4. Input File Not Found**
```
❌ Error: File not found: questions.json
   First run: python run_nougat_integration.py --consolidate
```
**Solution**: Run Phase 1 extraction first

### Troubleshooting

**Questions fail to parse response**:
- LLM sometimes returns non-JSON text
- Handled gracefully: uses default annotations
- Check logs for pattern in failures

**Annotation quality seems poor**:
- Review generated annotations manually
- Adjust prompt in `build_annotation_prompt()` method
- Consider switching LLM provider

**Processing very slow**:
- API rate limiting (0.5s per request is intentional)
- CPU is not the bottleneck (it's network I/O)
- Plan for ~2-3 hours for 1,800 questions

---

## Understanding Outputs

### Output File Structure

```json
{
  "total_questions": 1805,
  "papers_processed": [
    "2024-physics-set-1",
    "2024-chemistry-set-1",
    ...
  ],
  "date_processed": "2025-01-15",
  "questions": [
    {
      "question_id": "2024-physics-001",
      "paper_id": "2024-physics-set-1",
      "subject": "Physics",
      "question_type": "MCQ",
      "question_latex": "A particle moves in a circular path...",
      "options": [
        {"id": "1", "latex": "..."},
        {"id": "2", "latex": "..."},
        {"id": "3", "latex": "..."},
        {"id": "4", "latex": "..."}
      ],
      "correct_answer": "2",
      "ml_annotations": {
        "difficulty": "Medium",
        "concepts": ["circular motion", "centripetal force"],
        "solution_approach": "...",
        "key_insight": "...",
        "computable_solution": true,
        "estimated_time_seconds": 120
      }
    },
    ...
  ]
}
```

### Analyzing Results

**Count questions by difficulty**:
```python
import json
with open('all_questions_consolidated_annotated.json') as f:
    data = json.load(f)

difficulties = {}
for q in data['questions']:
    d = q.get('ml_annotations', {}).get('difficulty', 'None')
    difficulties[d] = difficulties.get(d, 0) + 1

for diff, count in sorted(difficulties.items()):
    print(f"{diff}: {count}")
```

**Find questions by concept**:
```python
physics_questions = [
    q for q in data['questions']
    if 'circular motion' in q.get('ml_annotations', {}).get('concepts', [])
]
print(f"Questions about circular motion: {len(physics_questions)}")
```

**Statistics**:
```python
times = [
    q['ml_annotations']['estimated_time_seconds']
    for q in data['questions']
    if q['ml_annotations']['estimated_time_seconds']
]
print(f"Average time: {sum(times)/len(times):.0f}s")
print(f"Total time for all questions: {sum(times)/60:.0f} minutes")
```

---

## Advanced Configuration

### Modifying the Prompt

Edit `build_annotation_prompt()` to customize what LLM extracts:

```python
def build_annotation_prompt(self, question: Dict) -> str:
    # ... existing code ...
    
    prompt = f"""Your custom prompt here
    
    {question_text}
    
    Return JSON with your custom fields:
    {{
        "your_field": "value",
        ...
    }}"""
    
    return prompt
```

### Adjusting API Parameters

In `annotate_with_claude()` or `annotate_with_openai()`:

```python
# For more creative responses:
message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=800,  # Increase if responses truncated
    temperature=0.5,  # Increase for more variation (0.0 = deterministic)
    messages=[...]
)
```

### Batch Processing with Checkpoints

Modify script to save checkpoint every 100 questions:

```python
# After processing each question
if (i + 1) % 100 == 0:
    # Save checkpoint
    with open('checkpoint.json', 'w') as f:
        json.dump(data, f)
    print(f"💾 Checkpoint saved at question {i + 1}")
```

---

## Validation & Quality Control

### Manual Spot-Check (Recommended)

Review 20-30 random annotations:

```bash
python -c "
import json
import random
with open('all_questions_consolidated_annotated.json') as f:
    data = json.load(f)
for q in random.sample(data['questions'], 5):
    print(f'Q{q[\"question_id\"]}: {q[\"ml_annotations\"][\"difficulty\"]}')
    print(f'  Concepts: {q[\"ml_annotations\"][\"concepts\"]}')
    print(f'  Time: {q[\"ml_annotations\"][\"estimated_time_seconds\"]}s')
    print()
"
```

### Quality Metrics

Check for annotation completeness:

```python
import json
with open('all_questions_consolidated_annotated.json') as f:
    data = json.load(f)

total = len(data['questions'])
annotated = sum(
    1 for q in data['questions']
    if q.get('ml_annotations', {}).get('difficulty')
)

print(f"Annotation coverage: {annotated}/{total} ({100*annotated/total:.1f}%)")
```

---

## Next Steps After Annotation

### 1. Create Fine-Tuning Dataset

Use annotated questions to fine-tune a model:
```python
# Convert to standardized format for HuggingFace
# Include question_latex, options, difficulty, concepts
```

### 2. Build Question Recommendation System

Use concepts and difficulty for recommendation:
```python
def recommend_questions(student_weak_concepts, difficulty_level):
    # Filter by weak_concepts
    # Filter by difficulty_level
    # Sort by estimated_time_seconds
```

### 3. Generate Practice Tests

Group questions by difficulty/concepts:
```python
def create_practice_test(subject, difficulty, num_questions):
    # Filter questions by subject & difficulty
    # Sample num_questions randomly
    # Calculate total_time = sum(estimated_time_seconds)
```

### 4. Analytics Dashboard

Build visualizations:
- Distribution of difficulty levels
- Time estimates by subject
- Concept frequency heatmap
- Success rate predictions

---

## Performance Optimization

### Parallel Processing (Future Enhancement)

Currently sequential (rate-limited to respect API). For parallel:
```python
import concurrent.futures
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    # Process multiple questions in parallel
    # Note: Requires separate API keys or account upgrades
```

### Caching Responses

Cache identical questions:
```python
cache = {}
question_hash = hash(question_latex)
if question_hash in cache:
    annotation = cache[question_hash]
else:
    annotation = annotate_question(question)
    cache[question_hash] = annotation
```

### Incremental Updates

Only annotate new questions from Phase 1:
```bash
# Only processes unannotated questions
python run_llm_annotation.py --skip-existing
```

---

## Troubleshooting Guide

| Problem | Cause | Solution |
|---------|-------|----------|
| 0 questions processed | Input file empty or missing | Run Phase 1 first: `python run_nougat_integration.py --consolidate` |
| All annotations failed | API key not set | Export `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` |
| JSON parse errors | LLM response malformed | Rare; pipeline handles gracefully; check response format in logs |
| Very slow processing | Rate limiting (intentional) | Normal; expected ~2-3 hours for 1,800 questions |
| Memory error on large files | JSON too large for memory | Process in batches; modify script to load/save in chunks |
| Timeout errors | Network issues | Retry; built-in backoff exists |

---

## Architecture Details

### Class: `LLMAnnotationPipeline`

**Constructor**:
```python
pipeline = LLMAnnotationPipeline(
    json_file="path/to/questions.json",
    output_file="path/to/output.json",  # Optional
    api_provider="anthropic"  # or "openai"
)
```

**Key Methods**:
- `load_questions()` - Load consolidated JSON
- `build_annotation_prompt()` - Create LLM prompt
- `annotate_with_claude()` - Call Claude API
- `annotate_with_openai()` - Call OpenAI API
- `annotate_question()` - Process single question
- `run_annotation()` - Main processing loop

**Error Handling**:
- Failed annotations logged but don't stop pipeline
- Default values used for failed questions
- Summary report shows success/failure counts

---

## FAQ

**Q: Can I use both APIs?**
A: No, one per run. But you can combine results by merging JSONs.

**Q: How long does full annotation take?**
A: ~2-3 hours for 1,800 questions (network-bound, not CPU-bound).

**Q: What if annotation fails for some questions?**
A: They get default values (difficulty=None, concepts=[], etc.). You can manually review and fix these.

**Q: Can I cancel and resume?**
A: Yes! Use `--skip-existing` to continue from last checkpoint.

**Q: How much will it cost?**
A: Claude: ~$5-6 for 1,800 questions. GPT-4o: ~$25-30.

**Q: Why is processing rate-limited?**
A: Respect API rate limits and avoid overloading servers. 0.5s delay per request.

**Q: Can I customize the annotation fields?**
A: Yes! Edit `build_annotation_prompt()` method to request different fields.

---

## Summary

Phase 2 transforms extracted questions into a fully annotated dataset using AI:

✅ **Setup**: Install packages + set API key (2 min)
✅ **Test**: Run with `--sample 10` to verify (1 min)
✅ **Process**: Run full pipeline (2-3 hours)
✅ **Validate**: Spot-check 20-30 random questions
✅ **Use**: Feed into ML models, recommendation systems, analytics

**Next**: Phase 3 would be building ML applications using the enriched data!
