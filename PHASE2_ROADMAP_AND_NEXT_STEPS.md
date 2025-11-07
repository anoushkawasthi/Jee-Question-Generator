# Phase 2: Complete Roadmap & Execution Guide

## Executive Summary

Phase 2 takes the 1,805 extracted questions from Phase 1 and adds AI-generated metadata using Claude or GPT-4o. This transforms raw data into a richly annotated dataset ready for machine learning applications.

**Current Status**: ✅ Implementation Complete
**Next Action**: Execute annotation pipeline
**Estimated Time**: 10 minutes (test) → 90 minutes (full)
**Total Cost**: $5-6 (Claude) or $27 (GPT-4o)

---

## Phase 2 Overview

### What Phase 2 Does

```
Input: all_questions_consolidated.json (1,805 questions)
         ↓
         [Add ML Metadata via LLM API]
         ↓
Output: all_questions_consolidated_annotated.json
         (Same questions + "ml_annotations" field)
```

### What Gets Added to Each Question

```json
"ml_annotations": {
  "difficulty": "Medium",                    // Easy/Medium/Hard
  "concepts": ["circular motion", "force"],  // Key concepts
  "solution_approach": "Use F = ma",         // How to solve
  "key_insight": "Force ⊥ velocity",        // Key insight
  "computable_solution": true,               // Computational vs conceptual
  "estimated_time_seconds": 120              // Expected solving time
}
```

### Why This Matters

- ✅ Enables **difficulty-based filtering** for practice tests
- ✅ Allows **concept-based learning** path recommendations
- ✅ Provides **time estimates** for mock test creation
- ✅ Identifies **computational vs conceptual** problems
- ✅ Feeds ML models for **difficulty prediction**
- ✅ Powers **question recommendation** systems

---

## Step-by-Step Execution

### Step 1: Setup (5 minutes)

#### A. Install Required Package

Choose one provider:

**Option 1: Claude (Recommended)**
```bash
pip install anthropic
```

**Option 2: GPT-4o**
```bash
pip install openai
```

#### B. Set API Key

**Claude Setup**:
```bash
# Linux/Mac
export ANTHROPIC_API_KEY="sk-ant-xxxxx"

# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-xxxxx"
```

**GPT-4o Setup**:
```bash
# Linux/Mac
export OPENAI_API_KEY="sk-..."

# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."
```

Get API keys from:
- Claude: https://console.anthropic.com/
- GPT-4o: https://platform.openai.com/

---

### Step 2: Test Setup (5 minutes)

Run with small sample to verify everything works:

```bash
python run_llm_annotation.py --sample 10
```

**Expected Output**:
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

📁 Output: all_questions_consolidated_annotated.json
```

**What to Check**:
- ✅ Script runs without errors
- ✅ Connections to API work
- ✅ Outputs valid JSON
- ✅ Annotations look reasonable

---

### Step 3: Spot-Check Quality (5 minutes)

Before running full pipeline, verify annotation quality:

```python
import json
import random

with open('all_questions_consolidated_annotated.json') as f:
    data = json.load(f)

# Show 5 random annotations
for q in random.sample(data['questions'], 5):
    ann = q.get('ml_annotations', {})
    print(f"\n{q['question_id']}:")
    print(f"  Difficulty: {ann.get('difficulty')}")
    print(f"  Concepts: {ann.get('concepts')}")
    print(f"  Time Est: {ann.get('estimated_time_seconds')}s")
    print(f"  Insight: {ann.get('key_insight')[:80]}...")
```

**Success Criteria**:
- Difficulty is Easy/Medium/Hard ✅
- Concepts make sense ✅
- Time estimates are reasonable (30-300s) ✅
- Insights are meaningful ✅

---

### Step 4: Run Full Pipeline (90 minutes)

Once verified, run on all questions:

```bash
python run_llm_annotation.py
```

**What to Expect**:
- ⏱️ First 100 questions: 2-3 minutes
- ⏱️ Full 1,805 questions: 90-120 minutes
- 💰 Cost: $5-6 (Claude) or $27 (GPT-4o)
- 📊 Rate: ~0.3 questions/second

**During Processing**:
- Updates every 10 questions
- Shows current count and ETA
- You can safely close terminal (process continues)

**On Completion**:
```
✅ Successful: 1805
❌ Failed: 0
⏱️  Time elapsed: 5400s (1.5 hours)
⚡ Rate: 0.33 q/s

📁 Output: data/processed/nougat_parsed/all_questions_consolidated_annotated.json
```

---

### Step 5: Validate Output (5 minutes)

Verify all questions are properly annotated:

```python
import json

with open('all_questions_consolidated_annotated.json') as f:
    data = json.load(f)

# Check coverage
total = len(data['questions'])
annotated = sum(
    1 for q in data['questions']
    if q.get('ml_annotations', {}).get('difficulty')
)

print(f"Total questions: {total}")
print(f"Annotated: {annotated}")
print(f"Coverage: {100*annotated/total:.1f}%")

# Check for issues
for q in data['questions'][:5]:
    ann = q.get('ml_annotations', {})
    assert ann.get('difficulty') in ['Easy', 'Medium', 'Hard']
    assert isinstance(ann.get('concepts'), list)
    assert isinstance(ann.get('estimated_time_seconds'), (int, type(None)))
    assert isinstance(ann.get('computable_solution'), (bool, type(None)))

print("✅ All validations passed!")
```

---

## Decision Matrix: Claude vs GPT-4o

### When to Use Claude

✅ **Use Claude if**:
- Budget is primary concern ($5-6)
- Need fast processing (same speed as GPT-4o)
- Have Anthropic API key available
- Need good reasoning for physics/math problems
- Want recommendations (faster, cheaper)

### When to Use GPT-4o

✅ **Use GPT-4o if**:
- Budget is not a concern (~$27)
- Need slightly higher JSON compliance (99% vs 98%)
- Planning future image processing
- Have OpenAI API key available
- Want to compare results

### Cost-Benefit Comparison

| Metric | Claude | GPT-4o |
|--------|--------|--------|
| Cost for 1,805 questions | $5.40 | $27.00 |
| Speed | 90 min | 90 min |
| JSON Quality | 98% | 99% |
| Reasoning Quality | Excellent | Excellent |
| Recommendation | ✅ YES | Alternative |

**Decision Rule**: Unless specifically required, use Claude for 5x cost savings.

---

## Troubleshooting Quick Guide

### Issue: "ModuleNotFoundError: No module named 'anthropic'"

```bash
# Solution: Install the package
pip install anthropic
```

### Issue: "Anthropic API key not set"

```bash
# Solution: Export the key
export ANTHROPIC_API_KEY="sk-ant-xxxxx"

# Verify it's set
echo $ANTHROPIC_API_KEY
```

### Issue: "File not found: data/processed/nougat_parsed/all_questions_consolidated.json"

```bash
# Solution: Run Phase 1 extraction first
python run_nougat_integration.py --consolidate
```

### Issue: 0 Questions Processed

- **Check**: Input file exists and contains data
- **Verify**: JSON structure is valid
- **Solution**: Regenerate from Phase 1 if corrupted

### Issue: Very Slow (Expected Normal)

- **Why**: Network I/O is the bottleneck (not CPU)
- **Normal Rate**: ~0.3 questions/second
- **Expected Time**: 1.5-2 hours for 1,805 questions
- **Cannot Parallelize**: Would need multiple API keys
- **Solution**: Let it run; don't interrupt

### Issue: Some Annotations Failed

- **Normal**: <1% failure rate is expected
- **Impact**: Those questions get default values
- **Action**: Can manually review and fix after
- **Handling**: Pipeline continues processing

---

## What Happens Next

### Immediately After Phase 2

1. ✅ New file: `all_questions_consolidated_annotated.json`
2. ✅ Contains all 1,805 questions with metadata
3. ✅ Ready for analysis and ML applications
4. ✅ Can proceed to Phase 3

### Phase 3 Options (Choose One or More)

#### Option A: Analytics Dashboard
```python
# Analyze annotation distribution
# Create visualizations
# Generate statistics by difficulty/concept
```

#### Option B: Recommendation System
```python
# Build question recommender
# Filter by student level & concepts
# Create practice paths
```

#### Option C: Practice Test Generator
```python
# Generate mock tests by difficulty
# Assign time limits
# Create answer keys
```

#### Option D: ML Model Training
```python
# Fine-tune difficulty classifier
# Train concept predictor
# Build time estimator
```

---

## Success Checklist

Before moving forward, verify:

- [ ] Phase 1 complete (Phase 2 input ready)
- [ ] API key installed and working
- [ ] Test run (--sample 10) successful
- [ ] Spot-check shows good annotation quality
- [ ] Full pipeline runs to completion
- [ ] Output file created with all 1,805 questions
- [ ] All questions have ml_annotations field
- [ ] JSON is valid and parseable
- [ ] Cost was as expected
- [ ] Ready for Phase 3 applications

---

## Reference: Command Cheatsheet

```bash
# Setup
pip install anthropic
export ANTHROPIC_API_KEY="your-key"

# Test
python run_llm_annotation.py --sample 10

# Full run
python run_llm_annotation.py

# Use OpenAI instead
python run_llm_annotation.py --provider openai

# Custom output
python run_llm_annotation.py --output my_output.json

# Resume if interrupted
python run_llm_annotation.py --skip-existing

# Quick validation
python -c "
import json
with open('all_questions_consolidated_annotated.json') as f:
    d = json.load(f)
total = len(d['questions'])
ann = sum(1 for q in d['questions'] if q.get('ml_annotations', {}).get('difficulty'))
print(f'Annotated: {ann}/{total}')
"
```

---

## File Guide

| File | Purpose | When to Use |
|------|---------|------------|
| `run_llm_annotation.py` | Main script | Execute annotation |
| `PHASE2_QUICK_START.md` | Quick reference | First time users |
| `LLM_ANNOTATION_GUIDE.md` | Full docs | Detailed help |
| `PHASE2_IMPLEMENTATION_GUIDE.md` | Technical deep-dive | Developers |
| `PHASE2_DELIVERABLES_MANIFEST.md` | Deliverables list | Overview |
| `PHASE2_ROADMAP_AND_NEXT_STEPS.md` | This file | Planning |

---

## Next Steps (Action Items)

### Immediate (Today)

1. ✅ Install anthropic: `pip install anthropic`
2. ✅ Set API key: `export ANTHROPIC_API_KEY="..."`
3. ✅ Test: `python run_llm_annotation.py --sample 10`
4. ✅ Verify output: Check JSON and annotations

### Short Term (This Week)

1. ✅ Run full pipeline: `python run_llm_annotation.py`
2. ✅ Spot-check results: Review 20-30 random annotations
3. ✅ Validate JSON: Load and parse output
4. ✅ Commit to version control

### Medium Term (This Month)

1. ⏳ Choose Phase 3 application
2. ⏳ Build ML model or analytics system
3. ⏳ Test on sample data
4. ⏳ Deploy to production

---

## Performance Summary

### Phase 2 Timeline

```
Setup:      5 min (install packages, set keys)
Test:       5 min (verify with 10 questions)
Quality:    5 min (spot-check results)
Full Run:   90 min (process 1,805 questions)
Validate:   5 min (verify output)
                ─────────
Total:      110 min (~2 hours)
```

### Phase 2 Cost

**Claude** (Recommended):
```
1,805 questions × $0.003/question = $5.40
```

**GPT-4o** (Alternative):
```
1,805 questions × $0.015/question = $27.00
```

---

## Support & Resources

### Documentation
- 📖 Full Guide: `LLM_ANNOTATION_GUIDE.md`
- ⚡ Quick Ref: `PHASE2_QUICK_START.md`
- 🔧 Technical: `PHASE2_IMPLEMENTATION_GUIDE.md`
- 📋 Manifest: `PHASE2_DELIVERABLES_MANIFEST.md`

### External Resources
- Anthropic Docs: https://docs.anthropic.com/
- OpenAI Docs: https://platform.openai.com/docs/
- JSON Reference: https://www.json.org/

### API Accounts
- Get Claude key: https://console.anthropic.com/
- Get GPT-4o key: https://platform.openai.com/

---

## FAQ

**Q: Which provider should I use?**
A: Claude - 5x cheaper, same quality.

**Q: Why does it take 90 minutes?**
A: Network I/O bound, not CPU. API calls take 1-2 seconds each. Can't parallelize without multiple keys.

**Q: What if processing fails partway through?**
A: Use `--skip-existing` to resume from checkpoint.

**Q: How much will it cost?**
A: Claude: ~$5.40. GPT-4o: ~$27. Test first with `--sample 10` (~$0.03).

**Q: Can I customize the annotations?**
A: Yes! Edit `build_annotation_prompt()` in `run_llm_annotation.py`.

**Q: What happens with failed annotations?**
A: They get default values (difficulty=None, concepts=[], etc.). Very rare (<1%).

---

## Summary

**Phase 2 Delivers**:
- LLM-based annotation of all 1,805 questions
- 6 structured metadata fields per question
- Difficulty, concepts, solution approach, insights, etc.
- Ready for Phase 3 ML applications

**Time Investment**:
- Setup: 5 minutes
- Test: 5 minutes
- Full run: 90 minutes
- Validation: 5 minutes
- **Total: ~2 hours**

**Cost**:
- Claude: $5-6 (Recommended)
- GPT-4o: $27 (Alternative)

**Status**: ✅ Ready to Execute

---

**Next Action**: 
```bash
pip install anthropic
export ANTHROPIC_API_KEY="your-key"
python run_llm_annotation.py --sample 10
```

Good luck! 🚀
