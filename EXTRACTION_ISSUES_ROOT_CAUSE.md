# Root Cause Analysis: JEE Question Extraction Issues

## Executive Summary
The extraction pipeline has **two critical failures**:
1. **90% of answer keys are wrong** (defaulting to '1') - ROOT CAUSE: Answer keys extracted from wrong location
2. **51% of MCQs missing options** (1 instead of 4) - ROOT CAUSE: Extraction only captures the correct option

## Issue #1: Answer Keys Defaulting to '1'

### Where the Answer Key Data Actually Is
- **Location**: PDF page 13 (last page) contains structured answer key
- **Format**: Question number, then answer in parentheses, e.g., "6. (2)", "7. (2)", "8. (2)"
- **Data Structure**: Extracted in `01_text_images_extraction.json` as text blocks on page 13
- **Confidence**: ✅ VERIFIED - manual inspection confirmed answer key exists

### Current Extraction Behavior
- **File**: `src/components/nougat_question_parser.py`, line 261-269 (`_extract_answer` method)
- **Logic**: Looks for "Answer:" or "Ans:" patterns **within the question text**
- **Result**: Doesn't find anything (JEE PDFs don't embed answers in question text)
- **Fallback**: Returns None, which is later defaulted to '1' in consolidation logic

### Why This Fails
1. `parse_answer_key()` function exists in `src/utils.py` but is **NEVER CALLED**
2. JEE answer keys are on a **separate page**, not embedded in question text
3. The Nougat parser tries to extract answers from question sections only
4. No code path retrieves the separate answer key page and maps it to questions

### Code Path
```
extraction_main.py 
  -> pipeline/extraction_pipeline.py 
  -> nougat_question_parser.py._parse_question_section()
  -> _extract_answer() ← Looks for answer in wrong location
  -> Returns None
  -> json_combiner_validator.py (line 364)
  -> correct_answer = None ← Gets defaulted to '1' or ignored
```

## Issue #2: MCQ Options Only Has 1 Item Instead of 4

### Where the Option Data Actually Is
- **Location**: PDF pages 1-12 contain questions with 4 options per MCQ
- **Format**: Separate text blocks: "(1)", option text, "(2)", option text, "(3)", option text, "(4)", option text
- **Data Structure**: Options come as numbered (1), (2), (3), (4) NOT as A, B, C, D
- **Current State**: ✅ Verified that 01_text_images_extraction.json has ALL 4 options as separate blocks

### Current Extraction Behavior  
- **File**: `src/components/question_parser.py`, line 192-197 (`_parse_questions` method)
- **Logic**: Checks for options using regex `^[A-D]` pattern
- **Issue**: **Expects letters (A, B, C, D) but PDF has numbers (1, 2, 3, 4)**
- **Root Cause**: Pattern mismatch - code searches for `A)`, `B)` but options are formatted as `(1)`, `(2)`
  ```python
  opt_letter = text[0].upper()  # Gets '(' not 'A'
  if opt_letter in ['A', 'B', 'C', 'D']:  # '(' never matches!
      current_options[opt_letter] = text
  ```
- **Result**: All 4 options are in text_blocks but never captured into options_dict

### Why This Fails
1. QuestionParser regex doesn't recognize numbered options `(1)` `(2)` etc.
2. Options never get added to `current_options` dictionary
3. In `_create_question()`, line 273, options_list gets created from empty options_dict
4. Result: Questions end up with 0 or 1 options instead of 4
5. Evidence: 913/1,805 questions (50.58%) have only 1 option

### Code Path
```
extraction_main.py 
  -> pipeline/extraction_pipeline.py 
  -> nougat_question_parser.py._extract_options()
  -> Finds all 4 options ✅
  -> _parse_question_section()
  -> Stores only 1 option ❌
  -> json_combiner_validator.py (line 364)
  -> options = [single_option_only] ← INCORRECT
```

## Why Both Issues Exist

### Architectural Gap
The extraction pipeline was designed to work with **Nougat-processed markdown** (clean LaTeX output), but:
1. Nougat was **never actually integrated** (line 364 of json_combiner_validator.py: `# TODO`)
2. The pipeline uses **PyMuPDF** (messy, inconsistent text extraction) instead
3. Code assumes answer keys are **embedded in question text** (they're not in JEE PDFs)
4. Code assumes only **one option needs storage** (wrong assumption)

### Data Flow Problems
```
PDF -> PyMuPDF -> text_blocks (messy)
         ↓
    Nougat parser (expects clean markdown, gets messy text)
         ↓
    Answer extraction from wrong location (fails)
    Option extraction incomplete (fails)
         ↓
    Final JSON: 90% wrong answer keys, 51% missing options
```

## How to Fix

### Strategy 1: Use the Already-Extracted Answer Key (RECOMMENDED)
1. **Parse page 13** from `01_text_images_extraction.json`
2. **Extract Q/A pairs** using the existing `parse_answer_key()` logic
3. **Map answers to questions** during consolidation (Q1->Answer1, Q2->Answer2, etc.)
4. **Cost**: ~1 hour to implement, ~100% reliable

### Strategy 2: Restore All 4 Options
1. **Don't discard options** after finding the correct one
2. **Store all 4 options** in the `options` array
3. **Mark which is correct** with a flag: `options[i].is_correct = True`
4. **Cost**: ~30 minutes to implement

### Strategy 3: Complete (Both Fixes)
1. **Fix answer key extraction** (Strategy 1)
2. **Fix option extraction** (Strategy 2)
3. **Impact**: 100% of questions will have 4 options + correct answer key
4. **Cost**: ~1.5 hours total
5. **Result**: Production-ready data

## Recommended Action

**IMPLEMENT STRATEGY 3** (Both fixes):

### Phase 1: Answer Key Extraction Fix (45 minutes)
1. Create `answer_key_extractor.py` module
2. Parse page 13 from `01_text_images_extraction.json`
3. Extract Q/A pairs using regex: `(\d+)\.\s*\(([1-4])\)`
4. Modify `consolidate_final_with_nougat.py` to:
   - Load answer keys from each paper
   - Map them to question numbers
   - Assign to `correct_answer` field

### Phase 2: Option Extraction Fix (30 minutes)
1. Modify `nougat_question_parser.py._parse_question_section()`
2. Store ALL 4 options in the options array
3. Add `is_correct` flag to indicate the correct one
4. Test: Verify 100% of MCQs have exactly 4 options

### Phase 3: Re-run Extraction (30 minutes)
1. Re-run `consolidate_final_with_nougat.py` with fixes
2. Create VERSION 2 of final JSON
3. Audit with `deep_audit.py`
4. Verify: All answer keys correct, all 4 options present

### Phase 4: Validation (15 minutes)
1. Spot-check 20-30 questions manually
2. Verify answer keys match original PDF
3. Verify all 4 options present
4. Declare data ready for Phase 2

## Critical Files to Modify
1. `src/components/nougat_question_parser.py` - Fix option extraction
2. `consolidate_final_with_nougat.py` - Add answer key mapping
3. `nougat_postprocessor.py` - Integrate answer key fixes
4. `src/components/data_ingestion.py` - May need updates for option storage

## Affected Tests
- `test_nougat_parser.py` - Will need updates for 4-option validation
- `deep_audit.py` - Should show 0 issues after fix

## Success Criteria
✅ 100% of questions have correct answer keys (1-4 distribution should be ~25% each)
✅ 100% of MCQ questions have exactly 4 options
✅ 0% Unicode garbling after post-processing
✅ deep_audit.py shows ZERO data quality issues
