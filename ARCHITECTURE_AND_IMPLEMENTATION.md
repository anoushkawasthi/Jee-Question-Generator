# Nougat Parser - Complete Architecture & Implementation

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR PDF FILES                           │
│         (JEE Main 2024 01 Feb Shift 1, etc.)                   │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      NOUGAT OCR                                 │
│  (Vision Transformer - Meta)                                   │
│  - Reads PDFs with machine learning                            │
│  - Preserves layout and structure                              │
│  - Converts math to clean LaTeX                                │
│  - Outputs .mmd (Markdown) files                               │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    .MMD FILES (Markdown)                        │
│  Q1. A particle moving in a circle of radius $R$...            │
│  (1) $\sin^{-1}\left(\sqrt{\frac{2gT^2}{\pi^2 R}}\right)$      │
│  (2) $\sin^{-1}\left(\sqrt{\frac{\pi^2 R}{2gT^2}}\right)$      │
│  ...                                                            │
│  Answer: 1                                                      │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│         NOUGAT_QUESTION_PARSER.PY                              │
│  (This is your parsing engine)                                 │
│                                                                 │
│  NougatQuestionParser:                                         │
│  - _split_into_question_sections()  ← Break into Q1, Q2...   │
│  - _extract_options()               ← Find (1), (2), (3), (4) │
│  - _extract_question_text()         ← Get main question       │
│  - _extract_answer()                ← Find correct answer      │
│  - _detect_subject()                ← Physics/Chem/Math       │
│  - _detect_question_type()          ← MCQ/Numerical/etc       │
│                                                                 │
│  Returns: List[NougatQuestion]                                │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│      NOUGAT_PIPELINE_INTEGRATION.PY                            │
│  (This handles batch processing)                               │
│                                                                 │
│  NougatPipelineIntegration:                                    │
│  - process_single_mmd_file()    ← Parse one file              │
│  - process_all_mmd_files()      ← Batch process all           │
│  - create_consolidated_json()   ← Merge into one file         │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PARSED JSON OUTPUT                           │
│                                                                 │
│  data/processed/nougat_parsed/                                │
│  ├── file1_parsed.json                                        │
│  ├── file2_parsed.json                                        │
│  ├── ...                                                       │
│  └── all_questions_consolidated.json ← USE THIS              │
│                                                                 │
│  Structure:                                                     │
│  {                                                              │
│    "metadata": {...},                                          │
│    "questions": [                                              │
│      {                                                          │
│        "question_id": "...",                                   │
│        "question_latex": "$...$",                              │
│        "options": [{...}, {...}, {...}, {...}],               │
│        "correct_answer": "1",                                  │
│        "subject": "Physics",                                   │
│        "question_type": "MCQ"                                  │
│      }                                                          │
│    ]                                                            │
│  }                                                              │
└────────────────────────────────┬────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
  ┌────────────┐        ┌────────────────┐      ┌─────────────┐
  │   RAG/LLM  │        │ Study Platform │      │  Analytics  │
  │  (Embeddings)       │  (Search UI)   │      │  (Reports)  │
  └────────────┘        └────────────────┘      └─────────────┘
```

---

## Data Flow Through Parser

### Step 1: Input (Raw Markdown from Nougat)

```markdown
Q1. A particle moving in a circle of radius $R$ with uniform speed takes 
time $T$ to complete one revolution. If this particle is projected with the 
same speed at an angle $\theta$ to the horizontal, the maximum height attained 
by it is equal to $4R$. The angle of projection $\theta$ is then given by:

(1) $\sin^{-1}\left(\sqrt{\frac{2gT^2}{\pi^2 R}}\right)$

(2) $\sin^{-1}\left(\sqrt{\frac{\pi^2 R}{2gT^2}}\right)$

(3) $\cos^{-1}\left(\sqrt{\frac{2gT^2}{\pi^2 R}}\right)$

(4) $\cos^{-1}\left(\sqrt{\frac{\pi R}{2gT^2}}\right)$

Answer: 1

Q2. ...
```

### Step 2: Parsing Pipeline

```python
# 1. Split into sections
sections = [
    (1, "Q1. A particle moving... Answer: 1"),
    (2, "Q2. ... Answer: 2")
]

# 2. For each section, extract components
section = "Q1. A particle moving... Answer: 1"

# Extract question text
question_text = "A particle moving in a circle..."

# Extract options using regex
options = [
    {"id": "1", "latex": "$\\sin^{-1}\\left(...\\right)$"},
    {"id": "2", "latex": "$\\sin^{-1}\\left(...\\right)$"},
    {"id": "3", "latex": "$\\cos^{-1}\\left(...\\right)$"},
    {"id": "4", "latex": "$\\cos^{-1}\\left(...\\right)$"}
]

# Extract answer
answer = "1"

# Detect subject
subject = "Physics"  # Based on keywords

# Create object
question = NougatQuestion(
    question_id="Main_2024_01_Feb_Shift_1_q1",
    question_number=1,
    question_latex="A particle moving in a circle...",
    options=options,
    correct_answer="1",
    subject="Physics",
    question_type="MCQ"
)
```

### Step 3: Output (Structured JSON)

```json
{
  "question_id": "Main_2024_01_Feb_Shift_1_q1",
  "question_number": 1,
  "subject": "Physics",
  "question_type": "MCQ",
  "question_latex": "A particle moving in a circle of radius $R$ with uniform speed takes time $T$ to complete one revolution. If this particle is projected with the same speed at an angle $\\theta$ to the horizontal, the maximum height attained by it is equal to $4R$. The angle of projection $\\theta$ is then given by:",
  "options": [
    {
      "id": "1",
      "latex": "$\\sin^{-1}\\left(\\sqrt{\\frac{2gT^2}{\\pi^2 R}}\\right)$",
      "text": "$\\sin^{-1}\\left(\\sqrt{\\frac{2gT^2}{\\pi^2 R}}\\right)$"
    },
    {
      "id": "2",
      "latex": "$\\sin^{-1}\\left(\\sqrt{\\frac{\\pi^2 R}{2gT^2}}\\right)$",
      "text": "$\\sin^{-1}\\left(\\sqrt{\\frac{\\pi^2 R}{2gT^2}}\\right)$"
    },
    {
      "id": "3",
      "latex": "$\\cos^{-1}\\left(\\sqrt{\\frac{2gT^2}{\\pi^2 R}}\\right)$",
      "text": "$\\cos^{-1}\\left(\\sqrt{\\frac{2gT^2}{\\pi^2 R}}\\right)$"
    },
    {
      "id": "4",
      "latex": "$\\cos^{-1}\\left(\\sqrt{\\frac{\\pi R}{2gT^2}}\\right)$",
      "text": "$\\cos^{-1}\\left(\\sqrt{\\frac{\\pi R}{2gT^2}}\\right)$"
    }
  ],
  "correct_answer": "1"
}
```

---

## Regular Expressions Explained

### Regex 1: Question Start Detection

```python
r'^Q(\d+)\s*[.)\-:]?\s*'
```

**Breakdown:**
- `^Q` - Start with 'Q' at beginning of line
- `(\d+)` - Capture one or more digits (question number)
- `\s*` - Optional whitespace
- `[.)\-:]?` - Optional punctuation: dot, paren, dash, or colon
- `\s*` - Optional trailing whitespace

**Matches:**
- `Q1. ` ✅
- `Q2) ` ✅
- `Q3- ` ✅
- `Q4: ` ✅
- `Q5 ` ✅

---

### Regex 2: Option Detection

```python
r'\(([1-4])\)\s*(.+?)(?=\n\s*\([1-4]\)|\n\s*(?:Answer|Correct)|\Z)'
```

**Breakdown:**
- `\(([1-4])\)` - Match (1) through (4), capture number
- `\s*` - Optional whitespace after option marker
- `(.+?)` - Capture option text (non-greedy)
- `(?=...)` - Positive lookahead (stop here but don't consume):
  - `\n\s*\([1-4]\)` OR next option marker
  - `\n\s*(?:Answer|Correct)` OR answer key
  - `\Z` OR end of text

**Why This Works:**
- Non-greedy `(.+?)` prevents over-capturing
- Lookahead stops at next option without consuming it
- Handles variable spacing and line breaks

**Matches:**
```
(1) First option
(2) Second option

Answer: 1
```

Captures:
```
1. "First option"
2. "Second option"
```

---

### Regex 3: Answer Extraction

```python
r'(?:Answer|Correct\s*Answer)\s*[:=]?\s*\(?([1-4])\)?'
```

**Breakdown:**
- `(?:Answer|Correct\s*Answer)` - Non-capturing group for "Answer" or "Correct Answer"
- `\s*` - Optional whitespace
- `[:=]?` - Optional colon or equals sign
- `\s*` - Optional whitespace
- `\(?` - Optional opening paren
- `([1-4])` - Capture answer digit
- `\)?` - Optional closing paren

**Matches All These Formats:**
- `Answer: 1` ✅
- `Correct Answer: 2` ✅
- `Answer = 3` ✅
- `Answer(4)` ✅
- `Correct Answer 1` ✅

---

## Processing Pipeline Code

### Single File Processing

```python
# 1. Read markdown file
with open('nougat_output/file.mmd', 'r', encoding='utf-8') as f:
    markdown_content = f.read()

# 2. Parse questions
parser = NougatQuestionParser()
questions = parser.parse_markdown_content(
    markdown_content,
    paper_id="JEE Main 2024 01 Feb Shift 1"
)

# 3. Access parsed data
for q in questions:
    print(f"Q{q.question_number}: {q.subject}")
    print(f"  {q.question_latex[:100]}...")
    print(f"  {len(q.options)} options, Answer: {q.correct_answer}")
    print()
```

### Batch Processing

```python
# 1. Initialize integration
integration = NougatPipelineIntegration(
    nougat_output_dir="nougat_output",
    json_output_dir="data/processed/nougat_parsed"
)

# 2. Process all files
results = integration.process_all_mmd_files()

# 3. Create consolidated JSON
consolidated_path = integration.create_consolidated_json()

# 4. Print summary
integration.print_summary(results)

# Example output:
# ✅ Successful: 30
# ❌ Failed: 0
# ⚠️  Warnings: 0
# 📊 Total Questions Parsed: 1805
```

---

## Error Handling Flow

```
┌─ File Processing
│  │
│  ├─ File not found?  → Return error, continue
│  │
│  ├─ Markdown read error?  → Return error, continue
│  │
│  ├─ Parse questions  → Split into sections
│  │  │
│  │  └─ For each section:
│  │     │
│  │     ├─ Extract options
│  │     │  └─ < 2 options?  → Skip this question, log warning
│  │     │
│  │     ├─ Extract question text
│  │     │  └─ No text?  → Skip this question, log warning
│  │     │
│  │     ├─ Extract answer
│  │     │  └─ Not found?  → Set to None (allows manual review)
│  │     │
│  │     ├─ Detect subject
│  │     │  └─ Default to Mathematics if unclear
│  │     │
│  │     └─ Create NougatQuestion object
│  │
│  ├─ Save to JSON  → Success
│  │
│  └─ Return results
```

---

## Data Quality Checks

### Automatic Checks (Parser Level)

```python
# 1. Question must have question text
if not question_latex:
    logger.warning("No question text")
    return None

# 2. Must have at least 4 options
if len(options) < 4:
    logger.warning("Less than 4 options")
    return None

# 3. Options must be complete
for opt in options:
    if not opt.get('latex'):
        logger.warning("Empty option")
        return None
```

### Manual Checks (Application Level)

```python
# Find questions with problems
import json

with open('all_questions_consolidated.json', 'r') as f:
    data = json.load(f)

# Check 1: Missing answers
missing_answers = [
    q for q in data['questions'] 
    if q.get('correct_answer') is None
]

# Check 2: Incomplete options
incomplete = [
    q for q in data['questions']
    if len(q.get('options', [])) < 4
]

# Check 3: Missing LaTeX
no_latex = [
    q for q in data['questions']
    if not q.get('question_latex')
]

print(f"✅ Quality Report:")
print(f"   Total: {len(data['questions'])}")
print(f"   Missing answers: {len(missing_answers)}")
print(f"   Incomplete options: {len(incomplete)}")
print(f"   Missing LaTeX: {len(no_latex)}")
```

---

## Integration with Downstream Systems

### Integration with Vector Database

```python
from sentence_transformers import SentenceTransformer
import pinecone

# Load questions
with open('all_questions_consolidated.json', 'r') as f:
    data = json.load(f)

# Filter to valid questions
questions = [q for q in data['questions'] if q.get('correct_answer')]

# Initialize embedder
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize vector DB
pinecone.init(api_key="...", environment="...")
index = pinecone.Index("jee-questions")

# Embed and upload
for q in questions:
    embedding = model.encode(q['question_latex']).tolist()
    
    index.upsert([(
        q['question_id'],
        embedding,
        {
            'subject': q['subject'],
            'answer': q['correct_answer'],
            'question': q['question_latex']
        }
    )])
```

### Integration with LLM

```python
from openai import OpenAI

client = OpenAI()

# Load question
question = questions[0]

# Build prompt
prompt = f"""
Question: {question['question_latex']}

Options:
{chr(10).join([f"{opt['id']}. {opt['latex']}" for opt in question['options']])}

Correct Answer: {question['correct_answer']}

Explain why this is correct:
"""

# Call LLM
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)

print(response.choices[0].message.content)
```

---

## Performance Optimization

### Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def process_parallel(nougat_dir, num_workers=4):
    """Process .mmd files in parallel"""
    
    mmd_files = list(Path(nougat_dir).glob("*.mmd"))
    parser = NougatQuestionParser()
    
    def process_file(mmd_file):
        with open(mmd_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return parser.parse_markdown_content(content)
    
    all_questions = []
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        for questions in executor.map(process_file, mmd_files):
            all_questions.extend(questions)
    
    return all_questions

# Use with 8 cores:
questions = process_parallel("nougat_output", num_workers=8)
```

### Incremental Processing

```python
def process_with_checkpoint(nougat_dir, checkpoint='checkpoint.json'):
    """Process with save points"""
    
    import json
    
    # Load checkpoint
    try:
        with open(checkpoint, 'r') as f:
            processed = set(json.load(f))
    except:
        processed = set()
    
    parser = NougatQuestionParser()
    
    for mmd_file in Path(nougat_dir).glob("*.mmd"):
        if mmd_file.name in processed:
            continue
        
        with open(mmd_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        questions = parser.parse_markdown_content(content)
        
        # Save and checkpoint
        save_questions(questions)
        processed.add(mmd_file.name)
        
        with open(checkpoint, 'w') as f:
            json.dump(list(processed), f)
```

---

## Complete Example Workflow

```bash
#!/bin/bash

# 1. Install Nougat
pip install nougat-ocr

# 2. Convert PDFs to markdown
nougat data/raw_pdfs --out nougat_output --markdown

# 3. Parse questions
cd e:\jee-question-generator\JEE-Question-Generator

python -c "
from nougat_pipeline_integration import NougatPipelineIntegration

integration = NougatPipelineIntegration(
    'nougat_output',
    'data/processed/nougat_parsed'
)

results = integration.process_all_mmd_files()
consolidate_path = integration.create_consolidated_json()
integration.print_summary(results)

print(f'✅ Output: {consolidate_path}')
"

# 4. Validate output
python -c "
import json

with open('data/processed/nougat_parsed/all_questions_consolidated.json') as f:
    data = json.load(f)

total = len(data['questions'])
with_answers = sum(1 for q in data['questions'] if q.get('correct_answer'))

print(f'Total: {total}')
print(f'With answers: {with_answers}')
print(f'Quality: {100*with_answers/total:.1f}%')
"
```

---

This completes the architecture overview. The system is designed for:

✅ **Correctness** - Robust parsing with proper regex  
✅ **Performance** - Efficient single-pass processing  
✅ **Reliability** - Graceful error handling  
✅ **Maintainability** - Clean separation of concerns  
✅ **Extensibility** - Easy to add new features  

Ready for production use! 🚀
