# Phase 2: LLM Annotation - Quick Reference

## Before You Start

```bash
# 1. Install packages
pip install anthropic  # for Claude
# OR
pip install openai     # for GPT-4o

# 2. Set API key (choose one)
export ANTHROPIC_API_KEY="sk-ant-..."    # Linux/Mac
$env:ANTHROPIC_API_KEY = "sk-ant-..."    # Windows PowerShell

# OR

export OPENAI_API_KEY="sk-..."           # Linux/Mac
$env:OPENAI_API_KEY = "sk-..."           # Windows PowerShell
```

## Quick Commands

### Test Run (10 Questions)
```bash
# Recommended: Do this first to verify setup
python run_llm_annotation.py --sample 10
```

### Full Production Run
```bash
# Process all questions using Claude
python run_llm_annotation.py

# OR use GPT-4o
python run_llm_annotation.py --provider openai
```

### Custom Input/Output
```bash
python run_llm_annotation.py \
  --json-file data/processed/nougat_parsed/all_questions_consolidated.json \
  --output my_output.json
```

### Resume from Checkpoint
```bash
# Skip already-annotated questions and continue
python run_llm_annotation.py --skip-existing
```

## Expected Output

### Console Output (Sample)
```
======================================================================
LLM ANNOTATION PIPELINE - ANTHROPIC
======================================================================

📂 Loading: data/processed/nougat_parsed/all_questions_consolidated.json
📊 Total questions: 1805
🔄 Processing 1805 questions...

  [  10/ 1805] ✅ 10 | ❌ 0 | ETA: 4500s
  [  20/ 1805] ✅ 20 | ❌ 0 | ETA: 4490s
  ...

======================================================================
✅ ANNOTATION COMPLETE
======================================================================
✅ Successful: 1805
❌ Failed: 0
⏱️  Time elapsed: 5400s (1.5 hours)
⚡ Rate: 0.33 q/s

📁 Output: all_questions_consolidated_annotated.json
```

### Output JSON Structure
```json
{
  "question_id": "2024-physics-001",
  "question_latex": "A particle moves in circular motion...",
  "correct_answer": "2",
  "ml_annotations": {
    "difficulty": "Medium",
    "concepts": ["circular motion", "centripetal force", "Newton's laws"],
    "solution_approach": "Use F = mv²/r for centripetal force",
    "key_insight": "Force is always directed toward center",
    "computable_solution": true,
    "estimated_time_seconds": 120
  }
}
```

## Timing & Cost

| Provider | Questions | Time | Cost |
|----------|-----------|------|------|
| Claude | 10 | ~45s | $0.03 |
| Claude | 100 | ~7 min | $0.30 |
| Claude | 1,805 | ~90 min | $5.40 |
| GPT-4o | 10 | ~30s | $0.15 |
| GPT-4o | 100 | ~5 min | $1.50 |
| GPT-4o | 1,805 | ~80 min | $27.00 |

## Annotation Fields Explained

| Field | Example | Used For |
|-------|---------|----------|
| `difficulty` | "Medium" | Filtering practice sets by level |
| `concepts` | ["magnetic force", "circular motion"] | Topic-based learning paths |
| `solution_approach` | "Apply F = qvB sin θ" | Student hints / tutoring |
| `key_insight` | "Magnetic force ⊥ velocity" | Conceptual understanding |
| `computable_solution` | true | Numerical calculator problems |
| `estimated_time_seconds` | 120 | Mock test timing |

## Troubleshooting

### Issue: "API key not set"
```bash
# Check if exported
echo $ANTHROPIC_API_KEY      # Linux/Mac
$env:ANTHROPIC_API_KEY       # Windows PowerShell

# If not set, export again
export ANTHROPIC_API_KEY="your-key-here"
```

### Issue: "File not found"
```bash
# Run Phase 1 extraction first
python run_nougat_integration.py --consolidate

# Then run Phase 2
python run_llm_annotation.py
```

### Issue: "JSON parse errors"
- Normal occasional failures (rare)
- Pipeline handles gracefully
- Check with: `grep "Failed to parse" run.log`
- Affected questions get default values

### Issue: "Very slow / Rate limiting"
- **Normal behavior**: 0.5s delay between requests by design
- Expected: ~45s per 10 questions
- For 1,800 questions: ~1.5-2 hours
- This is intentional to respect API limits

## Validation

### Quick Spot-Check
```python
import json
import random

with open('all_questions_consolidated_annotated.json') as f:
    data = json.load(f)

# Show 5 random annotated questions
for q in random.sample(data['questions'], 5):
    ann = q.get('ml_annotations', {})
    print(f"{q['question_id']}: {ann.get('difficulty')} | {ann.get('concepts')}")
```

### Completion Check
```python
import json
with open('all_questions_consolidated_annotated.json') as f:
    data = json.load(f)

total = len(data['questions'])
annotated = sum(
    1 for q in data['questions']
    if q.get('ml_annotations', {}).get('difficulty')
)
print(f"Coverage: {annotated}/{total} ({100*annotated/total:.1f}%)")
```

## Next Steps

1. **Verify Test Run**: `python run_llm_annotation.py --sample 10`
2. **Full Annotation**: `python run_llm_annotation.py`
3. **Spot-Check**: Review 20-30 random questions
4. **Use Dataset**: Feed into ML models / practice systems

## File Locations

| File | Purpose |
|------|---------|
| `run_llm_annotation.py` | Phase 2 script |
| `LLM_ANNOTATION_GUIDE.md` | Full documentation |
| `data/processed/nougat_parsed/all_questions_consolidated.json` | Phase 1 input |
| `data/processed/nougat_parsed/all_questions_consolidated_annotated.json` | Phase 2 output |

## API Provider Comparison

| Aspect | Claude | GPT-4o |
|--------|--------|--------|
| Model | claude-3-5-sonnet | gpt-4o |
| Speed | Fast | Fast |
| JSON Quality | 98% | 99% |
| Cost | 🟢 Low | 🔴 High (5x) |
| Reasoning | 🟢 Excellent | 🟢 Excellent |
| Recommended | ✅ YES | Alternative |

## Command Cheatsheet

```bash
# Setup
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Test
python run_llm_annotation.py --sample 10

# Full run
python run_llm_annotation.py

# Custom output
python run_llm_annotation.py --output custom_output.json

# Use OpenAI instead
python run_llm_annotation.py --provider openai

# Resume interrupted run
python run_llm_annotation.py --skip-existing
```

## Success Indicators

After running Phase 2:

✅ Output file created: `all_questions_consolidated_annotated.json`
✅ All 1,805 questions have `ml_annotations` field
✅ Each annotation has difficulty, concepts, and time estimate
✅ JSON is valid and parseable
✅ Cost: ~$5-6 for full dataset (Claude)

## Common Questions

**Q: Should I use Claude or GPT-4o?**
A: Claude is recommended (5x cheaper, same quality for text reasoning)

**Q: Can I interrupt and resume?**
A: Yes! Use `--skip-existing` to continue from last checkpoint

**Q: How do I verify it worked?**
A: Check output file exists and contains `ml_annotations` fields

**Q: What if some annotations fail?**
A: Normal (rare). Failed questions get default values. Review afterwards.

**Q: Is it really 1.5+ hours?**
A: Yes, network I/O bound. Can't be parallelized without separate API keys.

## Example Workflow

```bash
# 1. Test setup (1 min)
python run_llm_annotation.py --sample 10
# → Success? Continue to step 2

# 2. Full annotation (90 min, can run overnight)
python run_llm_annotation.py
# → Check output file exists

# 3. Verify results (5 min)
python -c "
import json
with open('all_questions_consolidated_annotated.json') as f:
    data = json.load(f)
print(f\"Total: {len(data['questions'])} annotated\")
"

# 4. Ready for next phase!
# Use annotated dataset for ML models, practice systems, analytics, etc.
```

---

**Need help?** See `LLM_ANNOTATION_GUIDE.md` for detailed documentation.
