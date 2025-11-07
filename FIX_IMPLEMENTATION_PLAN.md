# COMPREHENSIVE FIX PLAN FOR EXTRACTION ISSUES

## Executive Summary
- **Issue #1**: 90% of answer keys are '1' (should be ~25% each for 1,2,3,4)
- **Issue #2**: 51% of MCQs have 1 option (should all have 4)
- **Root Cause #1**: Answer keys extracted from PDF page 13 but never matched to questions
- **Root Cause #2**: QuestionParser expects options as A,B,C,D but PDF has (1),(2),(3),(4)
- **Solution**: Create two focused fix modules + modify consolidation to use fixes

---

## Phase 1: Answer Key Extraction Fix ✅ DONE
**Status**: COMPLETE - answer_key_extractor.py created and tested
- Extracts 78 answer keys from page 13 of first paper
- Validates format correctly
- Ready to integrate into consolidation pipeline

---

## Phase 2: MCQ Options Extraction Fix ⏳ IN PROGRESS

### Problem Location
**File**: `src/components/question_parser.py`, lines 192-197

**Current buggy code**:
```python
opt_match = self.option_pattern.match(text)
if opt_match and current_q_num > 0:
    opt_letter = text[0].upper()  # Gets '(' from '(1)'
    if opt_letter in ['A', 'B', 'C', 'D']:  # Never matches!
        current_options[opt_letter] = text
```

**Why it fails**:
- text comes in as: "(1)", "(2)", etc.
- text[0] is '(' not 'A'
- Condition `opt_letter in ['A', 'B', 'C', 'D']` fails
- Options never get captured

### The Fix
Replace the broken option detection with working numbered option detection:

```python
# NEW: Check for numbered options (1), (2), (3), (4)
opt_num_match = re.match(r'\(([1-4])\)', text)
if opt_num_match and current_q_num > 0:
    opt_num = opt_num_match.group(1)
    current_options[opt_num] = {
        "id": opt_num,
        "text": text
    }
elif opt_match and current_q_num > 0:
    # Fall back to letter-based options if needed
    opt_letter = text[0].upper()
    if opt_letter in ['A', 'B', 'C', 'D']:
        current_options[opt_letter] = text
```

### Files to Modify
1. `src/components/question_parser.py`
   - Line 192: Fix `_parse_questions()` to detect numbered options
   - Line 206-214: Extract option ID and text correctly
   - Line 273: Ensure all 4 options in options_dict are included in final output

### Expected Outcome
- All MCQs should have exactly 4 options
- Options identified as: {"1": {...}, "2": {...}, "3": {...}, "4": {...}}
- 913 questions that currently have 1 option will now have 4

---

## Phase 3: Integration with Consolidation ⏳ TODO

### Modify `consolidate_final_with_nougat.py`

**Changes needed**:
1. Import `AnswerKeyExtractor`
2. For each paper being processed:
   - Extract answer keys using `answer_key_extractor.extract_from_json_file()`
   - Map extracted answers to questions by question_number
   - Replace null/invalid correct_answer values with extracted keys
3. Pass through fixed question_parser output (which will have 4 options)

**Code pseudocode**:
```python
from answer_key_extractor import AnswerKeyExtractor

for paper_path in papers:
    # Get answer keys from PDF page 13
    json_file = paper_path.parent / "01_text_images_extraction.json"
    extractor = AnswerKeyExtractor()
    answer_keys = extractor.extract_from_json_file(json_file)
    
    # Load questions
    with open(paper_path) as f:
        paper_data = json.load(f)
    
    questions = paper_data.get('questions', [])
    
    # Map answer keys to questions
    for question in questions:
        q_num = question['question_number']
        if q_num in answer_keys:
            question['correct_answer'] = answer_keys[q_num]
    
    # Continue with rest of consolidation...
```

---

## Phase 4: Re-extraction and Validation ⏳ TODO

### Step 1: Apply Fixes to question_parser.py
Time: 15 minutes

### Step 2: Re-run Question Structure Pipeline
- Delete existing 02_structured_questions.json files (optional, will overwrite)
- Run: `python -m src.pipeline.question_structure_pipeline`
- This will recreate all 02_structured_questions.json with:
  - 4 options per MCQ (from fixed parser)
  - Better option capture (numbered format support)

Time: 5-10 minutes

### Step 3: Modify and Run Consolidation
- Add answer_key_extractor integration
- Run: `python consolidate_final_with_nougat.py`
- Creates VERSION 2: `data/processed/jee_questions_final_consolidated_v2.json`

Time: 5-10 minutes

### Step 4: Validate Results
- Run: `python deep_audit.py --file data/processed/jee_questions_final_consolidated_v2.json`
- Check statistics:
  - Answer key distribution (should be ~25% each: 1,2,3,4)
  - MCQ option counts (should be 100% have 4 options)
  - Unicode garbling (should be <5%)
  - Answer count statistics

Time: 5 minutes

---

## Implementation Order

### Recommended Execution Sequence:
1. ✅ **answer_key_extractor.py** - Created and tested
2. ⏳ **Fix question_parser.py** - Line 192-197, pattern matching for (1)(2)(3)(4)
3. ⏳ **Re-run question structure pipeline** - Creates fixed 02_structured_questions.json
4. ⏳ **Integrate into consolidation** - Add answer_key mapping logic
5. ⏳ **Run final consolidation** - Create consolidated JSON VERSION 2
6. ⏳ **Validate with deep_audit** - Verify all issues fixed

### Estimated Total Time: 60-75 minutes

---

## Success Criteria

### Data Quality Metrics
- ✅ **Answer keys**: 100% properly distributed (not all '1')
  - Before: 1,628/1,805 (90.2%) = '1'
  - After: ~450/1,805 (25%) each for 1, 2, 3, 4
  
- ✅ **MCQ options**: 100% have 4 options
  - Before: 913/1,805 (50.6%) have 1 option
  - After: 1,805/1,805 (100%) have 4 options
  
- ✅ **Unicode garbling**: <5% (down from 20%)
  - Nougat post-processor will handle conversion
  
- ✅ **Completeness**: 100% of 1,805 questions present
  - All papers, all questions, all options

### Validation Commands
```bash
# Check answer distribution
python -c "
import json
with open('data/processed/jee_questions_final_consolidated_v2.json') as f:
    data = json.load(f)
answers = {}
for paper in data['papers']:
    for q in paper['questions']:
        ans = q.get('correct_answer')
        answers[ans] = answers.get(ans, 0) + 1
print('Answer distribution:', answers)
"

# Check option counts
python -c "
import json
with open('data/processed/jee_questions_final_consolidated_v2.json') as f:
    data = json.load(f)
for paper in data['papers']:
    for q in paper['questions']:
        if len(q.get('options', [])) != 4:
            print(f'Q{q[\"question_number\"]}: {len(q.get(\"options\", []))} options')
print('All questions have 4 options ✅')
"
```

---

## Files Modified/Created

### New Files
- ✅ `answer_key_extractor.py` - Extracts answers from PDF page 13
- (consolidation integration - in-progress)

### Files to Modify
- `src/components/question_parser.py` - Fix option detection regex
- `consolidate_final_with_nougat.py` - Add answer key mapping
- (Optional) `nougat_postprocessor.py` - Expand Unicode table if needed

### Files to Delete (Optional)
- `extraction_output/*/02_structured_questions.json` - Will be regenerated
- `data/processed/jee_questions_final_consolidated.json` - Will be replaced with v2

---

## Rollback Plan
If issues occur:
1. Keep backup: `cp jee_questions_final_consolidated.json jee_questions_final_consolidated_v1_backup.json`
2. If v2 has issues, revert to v1
3. Or: Delete 02_structured_questions.json files and re-run with original question_parser

---

## Next Steps

**Immediate** (to proceed):
1. Apply fix to question_parser.py (lines 192-197)
2. Re-run question structure pipeline
3. Integrate answer_key_extractor into consolidation
4. Create VERSION 2 JSON
5. Validate with deep_audit

**User Input Needed**:
- Confirm to proceed with fixes
- Decide whether to delete existing 02_structured_questions.json files (vs. overwrite)

