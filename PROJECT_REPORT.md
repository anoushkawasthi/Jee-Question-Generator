# JEE Question Generator – Project Report

## 1. Overall Goal

The project’s goal is to build a full JEE Main practice-paper generator that:

- Uses real previous-year papers as the base source of questions.
- Cleans and standardizes those questions into a high‑quality dataset.
- Optionally uses LLMs to rephrase/change numbers so each generated paper feels new.
- Outputs professional, exam‑style PDFs with consistent formatting and answer keys.
- Exposes all of this via a simple Streamlit web UI where you choose difficulty and options.

---

## 2. High‑Level Architecture

At a high level, the repo is organized around four layers:

1. **Data Acquisition & Parsing**
   - Raw PDFs of JEE papers in `raw_pdfs/`.
   - Extraction/cleaning scripts:
     - `nougat_pipeline_integration.py`, `run_nougat_integration.py`
     - `answer_key_extractor.py`
     - `extraction_main.py`, `consolidate_*` scripts
     - OSRA attempts for images-equations (then mostly dropped).

2. **Dataset Construction & Tagging**
   - Consolidated dataset in `dataset_v2/`:
     - `all_papers_clean.jsonl`
     - `all_papers_tagged.jsonl`
     - `extraction_stats.json`
   - Cleaning/filtering:
     - Remove biology/statistics and image‑based questions.
     - Normalize question/option/answer fields.
   - Tagging/annotation:
     - Subject, topic, difficulty tagging (via LLM and/or rules).
   - Supporting scripts:
     - `build_full_dataset.py`
     - `build_mcq_dataset_single_paper.py`
     - `clean_single_paper_dataset.py`
     - `tag_questions.py`
     - `run_llm_annotation.py`

3. **Question Paper Generation & LLM Transformation**
   - Core generator:
     - `generate_paper.py` – main CLI to produce LaTeX + PDF.
   - LLM transformation:
     - `llm_transform.py` – classification + transformation of questions.
   - Validation & tooling:
     - `validate_nougat_poc.py`, `test_nougat_parser.py`, `validation_results.json`
     - `fix_unicode_for_latex` and LaTeX formatting helpers inside generator/LLM modules.

4. **User Interface & Runtime**
   - Streamlit web UI:
     - `streamlit_app.py` – difficulty selection, AI transform toggle, answer key, and inline PDF display.
   - CLI / scripts:
     - `run_question_pipeline.py`
     - `run_server.ps1`
   - Packaging / requirements:
     - `requirements.txt`
     - `setup.py`

---

## 3. Implementation Timeline & Evolution

This is the story of how the project evolved.

### 3.1 Phase 1 – Raw PDF Parsing and Early Experiments

**Objective:** Extract questions from original JEE PDF papers.

- We collected original JEE Main papers (2024–2025) and placed them under `raw_pdfs/`.
- Initial extraction pipeline:
  - **Nougat** for PDF → structured text:
    - `nougat_pipeline_integration.py`, `run_nougat_integration.py`.
  - **OSRA** (for images containing equations) was explored:
    - Attempted to convert formula snapshots into LaTeX.
    - Quickly ran into reliability / noise problems, especially with complex equation rendering.
- We wrote one‑off and PoC scripts to sanity‑check extract quality:
  - `demo_simple_parser.py`
  - `test_nougat_parser.py`
  - `validate_nougat_poc.py`

**Key Findings:**

- For “pure text” PDFs, Nougat worked reasonably well, but:
  - Formatting varied heavily between papers.
  - Math formulas and subscripts/superscripts often came out inconsistent.
- OSRA‑based workflows for images were unstable and produced noisy LaTeX.
- End result: image‑heavy / formula‑in‑images questions were unreliable; we decided to **focus on textual questions** only.

---

### 3.2 Phase 2 – Building a Clean, Structured Dataset

**Objective:** Build a single clean JSONL dataset of questions across all papers.

- Using outputs from Nougat and earlier scripts, we consolidated into:
  - `extraction_output/` for per‑paper outputs.
  - `consolidate_extraction.py`, `consolidate_main.py`, `consolidate_final_with_nougat.py`, `consolidate_with_nougat_fix.py` to join everything.
- From there we created `dataset_v2/all_papers_clean.jsonl`, then `all_papers_tagged.jsonl`.

**Key Steps:**

1. **Question Normalization**
   - Standardized fields:
     - `paper_id`, `year`, `date`, `shift`.
     - `subject` (Physics, Chemistry, Mathematics).
     - `question_type` (MCQ / integer).
     - `question_text`, `options`, `correct_index` or `correct_answer`.
   - Fixed mis‑splits between question text and options.
   - Stripped artifacts and weird tokens from parsing.

2. **Filtering**
   - Removed questions outside the JEE Main scope:
     - Biology / Statistics and any stray subjects.
   - Dropped image‑based questions:
     - Empirically, these caused poor downstream LaTeX and were hard to fix without robust OCR/OSRA.
   - Dropped incomplete questions:
     - Missing statements, broken match‑the‑following, or truncated texts.

3. **Aggregation & Stats**
   - End result (approximate numbers you reached):
     - ~1324 final clean questions.
     - Subject breakdown:
       - Physics: MCQ + Integer
       - Chemistry: MCQ + Integer
       - Mathematics: MCQ + Integer
     - Summary stored in `extraction_stats.json` and documented in remarks like `PROJECT_STATUS_ANALYSIS.md`.

---

### 3.3 Phase 3 – Tagging by Subject, Topic, and Difficulty

**Objective:** Annotate questions for smarter selection.

- We added subject/topic/difficulty tags to each question entry in `all_papers_tagged.jsonl`:
  - Subject was mostly determined by paper section or original labeling.
  - Topic and difficulty were assigned using a combination of:
    - Heuristics.
    - LLM‑based annotation runs (`run_llm_annotation.py`).
- Scripts:
  - `tag_questions.py` – drive tagging.
  - `build_full_dataset.py` – unify everything into one big JSONL with tags.

**Outcome:**

- You could now **filter by difficulty**, subject, and topic when generating a paper.
- This tagging layer is what later powered the `--difficulty` CLI flag and Streamlit difficulty dropdown.

---

### 3.4 Phase 4 – First LaTeX Paper Generator

**Objective:** Generate full JEE‑style PDFs from the dataset.

- Core script: `generate_paper.py`.

**Key Features:**

- Reads from `dataset_v2/all_papers_tagged.jsonl`.
- Selects a fixed pattern of questions:
  - E.g., 30 per subject (20 MCQ + 10 integer), total 90 questions.
- Difficulty‑aware sampling:
  - `--difficulty easy|medium|hard` chooses questions biased by tagged difficulty.
- LaTeX generation:
  - Uses the `exam` document class (or similar) to format:
    - Section headings by subject.
    - `\question` for each question, `choices` environment for MCQs.
  - Created helper to sanitize/convert Unicode to LaTeX:
    - `fix_unicode_for_latex()` maps:
      - Greek letters (α → `$\alpha$`).
      - Math letters and special characters.
      - Degree symbols (° → `$^{\circ}$`), plus/minus, etc.
- PDF compilation:
  - Uses MiKTeX (`pdflatex`) on Windows:
    - Verified via the configured path:
      `C:\Users\aahil\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe`.

**First Working Milestone:**

- You successfully produced:
  - Valid JEE‑style PDFs.
  - Accompanying LaTeX sources in `generated_papers/`.
- At this point, the generator **did not** use LLMs; it just shuffled existing questions according to filters.

---

### 3.5 Phase 5 – Prototype LLM Transformation (Single Paper)

**Objective:** Make questions look “new” by rephrasing / changing numbers.

- You didn’t want just shuffled original questions; you wanted **unique variants** while preserving core concepts.
- First attempt: run LLM on a **single paper’s questions**:
  - `generate_questions_prototype.py` or similar experimental scripts.
  - Basic prompt: rephrase or change numbers, keep answer consistent.
- Key problems discovered:
  - LLM sometimes:
    - Broke LaTeX syntax (missing `$`, broken `\frac`, etc.).
    - Changed the correct answer inadvertently.
    - Over‑edited chemistry equations (undesirable).
  - Manual fixes were tedious.

This prototype proved the **idea** but showed you needed:

1. A more structured pipeline (classify what to do with each question).
2. Strong LaTeX instructions and post‑processing.
3. Fallback when LLM‑generated LaTeX is unsafe.

---

### 3.6 Phase 6 – Structured LLM Pipeline (`llm_transform.py`)

**Objective:** Build a robust, scalable LLM transformation pipeline.

`llm_transform.py` became the core of the LLM layer, with two main steps:

#### 6.1 Step 1 – Classification

- Model: `gpt-4o-mini` (cheaper) for classification.
- For each question, classify an **action**:
  - `change_numbers` – change numerical values, recompute answer; preserve concept.
  - `rephrase` – reword text but keep numbers/formulas and meaning.
  - `fix_incomplete` – reconstruct missing statements/match‑the following.
  - `discard` – hopeless or too broken; replace from pool.
- Batched prompting with `CLASSIFY_SYSTEM_PROMPT` and `CLASSIFY_USER_TEMPLATE`.

**Discard handling:**

- If a question is classified as `discard`, you:
  - Replace it with another question from the same subject/pool.
  - Default classification for replacements: `rephrase`.

#### 6.2 Step 2 – Transformation

- Model: initially `gpt-4o`, later switched to `gpt-4o-mini` for cost.
- Actions:
  - `change_numbers`:
    - Change numeric constants, recompute correct answer and options.
  - `rephrase`:
    - Keep numbers/formulas exactly the same; only adjust wording.
  - `fix_incomplete`:
    - Add missing statements/lists but preserve answer.
- Prompts embed **very explicit LaTeX rules**:
  - All math in `$...$`.
  - Use `\times`, not Unicode ×.
  - Proper exponent/subscript notation, fractions, roots, trig functions, etc.
  - Examples of correct vs incorrect formatting.

#### 6.3 LaTeX Fixing & Validation

To combat broken LLM LaTeX, you implemented:

1. **Post‑processing function** `fix_latex_formatting(text)`:
   - Replaces Unicode math / symbols with LaTeX:
     - × → `$\\times$`, √ → `$\\sqrt{}$`, degree, Greek letters, etc.
   - Converts certain Unicode math italic characters to plain letters in `$...$`.
   - Cleans up double `$$`, `\textasciicircum`, bare exponents like `10^-3` → `10^{-3}`.
   - Makes sure various ranges and powers look consistent.

2. **Validation functions**:
   - `validate_latex(text)`:
     - Check balanced `$` and `{}`.
     - Reject some forbidden Unicode that would break LaTeX.
     - Guard against obviously broken patterns like fragmented `$a$ $b$ $c$` math.
   - `validate_transformed_question(question)`:
     - Applies `validate_latex` to question text and each option.
     - Ensures MCQs still have 4 options.

3. **Fallback Strategy**:
   - `transform_single_question`:
     - Calls LLM, parses JSON.
     - Applies `fix_latex_formatting`.
     - Validates result.
     - If validation fails or parsing/errors occur:
       - Mark `transform_action` as `fallback_original` / `error_fallback`.
       - Return the **original question** instead of broken LLM output.

This approach shifted emphasis from “reject aggressively” to “fix as much as possible and fall back only when necessary.”

---

### 3.7 Phase 7 – Scaling LLM Transformation to Full Papers

**Objective:** Run the full LLM pipeline across 90‑question papers.

- `generate_paper.py` gained a `--transform` flag:
  - Without `--transform`: uses original questions (only cleaned).
  - With `--transform`: passes the selected question set to `llm_transform.transform_questions`.
- The transformation pipeline:
  1. Classifies all selected questions.
  2. Replaces discarded ones from the pool.
  3. Transforms each question based on its action.
  4. Applies LaTeX fixing, validates, and logs counts for:
     - `rephrase`, `change_numbers`, `fix_incomplete`, `fallback_original`, etc.

**Issues & Fixes During Scaling:**

- Early runs:
  - LaTeX validation too strict → many fallbacks, little actual transformation.
  - Certain regex validation used variable‑width lookbehind → runtime errors.
  - Some options got fragmented, messing up the `exam` environment structure (choices stacked incorrectly).
- You tuned:
  - Validation to avoid over‑rejecting.
  - `fix_latex_formatting` to handle non‑string inputs (e.g., integer answers).
  - Prompts to emphasize:
    - Do NOT split single math expressions into many `$...$` chunks.
    - Preserve structure of “choices” so LaTeX stays consistent.

By the end of this phase, you had:

- Full‑paper, LLM‑transformed LaTeX compiling successfully most of the time.
- A robust fallback path when the LLM produced brittle LaTeX.

---

### 3.8 Phase 8 – Streamlit Web UI

**Objective:** Make generation accessible via a browser.

- File: `streamlit_app.py`.

**Key UI Features:**

- **Sidebar Config:**
  - Difficulty select:
    - Easy / Medium / Hard.
  - AI Transformation toggle:
    - On: run full `llm_transform` pipeline.
    - Off: use original cleaned questions only.
  - Answer key toggle:
    - Include or omit solutions at the end.

- **Main Panel:**
  - Display of selected options (difficulty, AI, answer key).
  - “Generate Paper” button.
  - Real‑time console output of `generate_paper.py`:
    - Uses `subprocess.Popen` with unbuffered `-u` and line‑by‑line reading.
    - Shows last N lines in a `st.code` block, so you can debug timeouts & errors.
  - Embedded PDF preview:
    - Renders the generated PDF in an iframe directly in the page.
  - Download button:
    - Download the generated PDF file.
  - Optional LaTeX source viewer:
    - Expandable panel to show the `.tex` file (nice for debugging LaTeX issues).

**Tech Details:**

- The app calls:
  - `sys.executable generate_paper.py ...` to ensure it uses the same venv Python.
  - Passes `env=os.environ.copy()` so `OPENAI_API_KEY` is available in the subprocess.
- Session state:
  - Tracks `generated_pdf` and `pdf_path` so the PDF persists across reruns.
- Error handling:
  - Shows truncated error output (last ~2000 chars) when a run fails.
  - Shows “Generation timed out” with last lines of output on timeout.

This UI made it easy to:

- Switch difficulty.
- Toggle LLM usage to compare formatting differences.
- Quickly iterate on LaTeX / validation fixes with immediate visual feedback.

---

## 4. Current Status & Known Issues

- **Working well:**
  - Base generation without LLM: stable, uniform formatting, consistent numbering.
  - Difficulty‑based selection: uses tagged properties effectively.
  - Streamlit UI: stable for non‑LLM runs, mostly stable for LLM runs.
  - LLM transformation:
    - Works for many questions; rephrases and changes numbers.
    - Validations and fallback prevent catastrophic LaTeX breakage.

- **Ongoing pain points:**
  - For some LLM outputs:
    - Fragmented math still appears (though reduced).
    - Some option formatting remains slightly off (line breaks, spacing).
    - In a few edge cases, question numbers / choices appear misaligned in LaTeX (often due to stray LaTeX commands or missing `\item`/`\choice` alignment).
  - Strict validation vs. reusability:
    - Too strict → everything falls back to original; defeats the purpose.
    - Too loose → risk of LaTeX errors.

---

## 5. Possible Next Approaches / Improvements

Since you may iterate further, here are concrete options:

1. **Template‑Based LaTeX Wrapping**
   - Instead of trusting the LLM to emit full LaTeX, you:
     - Ask for **plain text and structured math tokens**, e.g. a JSON with fields like:
       - `{"question_text_plain": "...", "math_expressions": [...], "options_plain": [...]}`.
     - You then insert those into a **strict LaTeX template** in Python, controlling where `$...$` appear.
   - Benefit: you fully own LaTeX structure; LLM only controls text/math “content”.

2. **Post‑Transformation Structural Normalization**
   - Parse the transformed text into a small internal representation:
     - Identify sentences, enumerations, and equations.
   - Regenerate a uniform LaTeX question format from that representation.
   - Essentially: “compiler front‑end” for LLM text to your LaTeX format.

3. **Use a Second LLM Pass Just for LaTeX Repair**
   - After the first transformation, run a small, cheaper model with a prompt:
     - “Here is a LaTeX snippet that failed compilation; fix only syntax, don’t change semantics.”
   - Combine with a quick dry‑run LaTeX check (e.g., string‑based heuristics or a fast LaTeX run).

4. **Stronger Segmentation of Responsibilities in Prompts**
   - For MCQs:
     - Freeze options and only let LLM modify wording of the question stem.
   - For `change_numbers`:
     - Get LLM to produce **only** the new numbers and new correct answer, then:
       - Use your own logic to recompute options or to apply numbers into a known formula pattern.

5. **Heuristic Post‑Processors for Choices**
   - After LLM:
     - Enforce:
       - Exactly one `\CorrectChoice` per MCQ, or exactly one correct index in metadata.
       - Exactly four `\choice` lines for each MCQ question.
     - If structure deviates:
       - Rebuild the `choices` block from content lines while preserving order.

6. **Partial Transformation Policy**
   - Instead of transforming all 90 questions:
     - Transform, say, 30–40% of them (easier to keep error‑rate low).
     - Rest stay original but shuffled.
   - Gains uniqueness without needing every single question to pass LLM LaTeX perfectly.

---

## 6. Summary

You’ve built a complete pipeline from raw JEE PDFs to:

- A clean, tagged dataset of >1300 questions.
- A production‑style JEE paper generator in LaTeX/PDF.
- An LLM transformation layer that:
  - Classifies per‑question actions.
  - Rephrases/changes numbers/fixes incomplete questions.
  - Fixes most LaTeX issues and falls back gracefully when it can’t.
- A Streamlit UI to control difficulty, AI transformation, and view PDFs instantly.

The remaining work is mostly about **incrementally hardening** the LLM + LaTeX interaction:

- Tighten/focus prompts.
- Improve the LaTeX repair pipeline.
- Decide a good trade‑off between “strict correctness” and “useful transformation coverage.”
