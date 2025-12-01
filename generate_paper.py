"""
JEE Paper Generator with PDF Output

Generates JEE Main style papers with configurable parameters:
- Difficulty distribution (easy/medium/hard proportions)
- Topic coverage options
- Year filtering (use only 2024, 2025, or both)
- Output includes question paper, answer key, and solutions

Uses LaTeX for professional PDF rendering with proper math formatting.

Input: dataset_v2/all_papers_tagged.jsonl
Output: generated_papers/<paper_name>.pdf

Usage:
    python generate_paper.py
    python generate_paper.py --difficulty easy --year 2024
    python generate_paper.py --difficulty hard --topics "Kinematics,Calculus,Organic Chemistry"
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import tempfile
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Configuration
# ============================================================================

INPUT_FILE = Path("dataset_v2/all_papers_tagged.jsonl")
OUTPUT_DIR = Path("generated_papers")

# JEE Main Paper Structure
QUESTIONS_PER_SUBJECT = 30  # 20 MCQ + 10 Integer (5 mandatory)
MCQ_PER_SUBJECT = 20
INTEGER_PER_SUBJECT = 10

# Difficulty distributions (proportions must sum to 1.0)
DIFFICULTY_PRESETS = {
    "easy": {"easy": 0.4, "medium": 0.5, "hard": 0.1},
    "medium": {"easy": 0.2, "medium": 0.6, "hard": 0.2},
    "hard": {"easy": 0.1, "medium": 0.4, "hard": 0.5},
    "balanced": {"easy": 0.33, "medium": 0.34, "hard": 0.33},
}

# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Question:
    """Represents a single question."""
    paper_id: str
    year: int
    date: str
    shift: int
    question_number: int
    question_text: str
    question_type: str  # "mcq" or "integer"
    subject: str
    topic: str
    difficulty: str
    options: List[str] = field(default_factory=list)
    correct_index: Optional[int] = None  # 1-4 for MCQ
    correct_answer: Optional[int] = None  # For integer type
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Question":
        return cls(
            paper_id=d.get("paper_id", ""),
            year=d.get("year", 0),
            date=d.get("date", ""),
            shift=d.get("shift", 0),
            question_number=d.get("question_number", 0),
            question_text=d.get("question_text", ""),
            question_type=d.get("question_type", "mcq"),
            subject=d.get("subject", "Unknown"),
            topic=d.get("topic", "Unknown"),
            difficulty=d.get("difficulty", "medium"),
            options=d.get("options", []),
            correct_index=d.get("correct_index"),
            correct_answer=d.get("correct_answer"),
        )


@dataclass
class PaperConfig:
    """Configuration for paper generation."""
    difficulty: str = "medium"  # easy, medium, hard, balanced
    year_filter: Optional[List[int]] = None  # e.g., [2024], [2024, 2025]
    topic_filter: Optional[List[str]] = None  # Specific topics to include
    include_solutions: bool = True
    paper_title: str = "JEE Main Practice Paper"
    seed: Optional[int] = None  # For reproducibility


# ============================================================================
# Question Selection
# ============================================================================

def load_questions() -> List[Question]:
    """Load all questions from the tagged dataset."""
    questions = []
    with INPUT_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                q = Question.from_dict(json.loads(line))
                questions.append(q)
    return questions


def filter_questions(
    questions: List[Question],
    config: PaperConfig
) -> Dict[str, Dict[str, List[Question]]]:
    """
    Filter and organize questions by subject, type, and difficulty.
    
    Returns:
        {
            "Physics": {"mcq": {"easy": [...], "medium": [...], "hard": [...]}, "integer": {...}},
            "Chemistry": {...},
            "Mathematics": {...}
        }
    """
    organized = {
        subj: {
            qtype: {"easy": [], "medium": [], "hard": []}
            for qtype in ["mcq", "integer"]
        }
        for subj in ["Physics", "Chemistry", "Mathematics"]
    }
    
    for q in questions:
        # Apply year filter
        if config.year_filter and q.year not in config.year_filter:
            continue
        
        # Apply topic filter (partial match)
        if config.topic_filter:
            topic_match = any(
                t.lower() in q.topic.lower() 
                for t in config.topic_filter
            )
            if not topic_match:
                continue
        
        # Skip unknown subjects
        if q.subject not in organized:
            continue
        
        # Organize by subject, type, difficulty
        qtype = "mcq" if q.question_type == "mcq" else "integer"
        difficulty = q.difficulty if q.difficulty in ["easy", "medium", "hard"] else "medium"
        
        organized[q.subject][qtype][difficulty].append(q)
    
    return organized


def select_questions(
    organized: Dict[str, Dict[str, List[Question]]],
    config: PaperConfig
) -> Dict[str, List[Question]]:
    """
    Select questions for each subject based on difficulty distribution.
    
    Returns:
        {"Physics": [q1, q2, ...], "Chemistry": [...], "Mathematics": [...]}
    """
    if config.seed is not None:
        random.seed(config.seed)
    
    difficulty_dist = DIFFICULTY_PRESETS.get(config.difficulty, DIFFICULTY_PRESETS["medium"])
    selected = {"Physics": [], "Chemistry": [], "Mathematics": []}
    
    for subject in ["Physics", "Chemistry", "Mathematics"]:
        subj_questions = []
        
        # Select MCQs (20 questions)
        mcq_pool = organized[subject]["mcq"]
        mcq_counts = {
            "easy": int(MCQ_PER_SUBJECT * difficulty_dist["easy"]),
            "medium": int(MCQ_PER_SUBJECT * difficulty_dist["medium"]),
            "hard": int(MCQ_PER_SUBJECT * difficulty_dist["hard"]),
        }
        # Adjust for rounding
        total = sum(mcq_counts.values())
        if total < MCQ_PER_SUBJECT:
            mcq_counts["medium"] += MCQ_PER_SUBJECT - total
        
        for diff, count in mcq_counts.items():
            pool = mcq_pool[diff].copy()
            random.shuffle(pool)
            subj_questions.extend(pool[:count])
        
        # Select Integer questions (10 questions)
        int_pool = organized[subject]["integer"]
        int_counts = {
            "easy": int(INTEGER_PER_SUBJECT * difficulty_dist["easy"]),
            "medium": int(INTEGER_PER_SUBJECT * difficulty_dist["medium"]),
            "hard": int(INTEGER_PER_SUBJECT * difficulty_dist["hard"]),
        }
        total = sum(int_counts.values())
        if total < INTEGER_PER_SUBJECT:
            int_counts["medium"] += INTEGER_PER_SUBJECT - total
        
        for diff, count in int_counts.items():
            pool = int_pool[diff].copy()
            random.shuffle(pool)
            subj_questions.extend(pool[:count])
        
        # Shuffle within subject to mix difficulties
        random.shuffle(subj_questions)
        selected[subject] = subj_questions
    
    return selected


# ============================================================================
# Solution Generation (LLM)
# ============================================================================

def generate_solution(client: OpenAI, question: Question) -> str:
    """Generate a step-by-step solution for a question using LLM."""
    
    prompt = f"""Provide a concise step-by-step solution for this JEE Main question.

Question: {question.question_text}

"""
    if question.question_type == "mcq" and question.options:
        prompt += "Options:\n"
        for i, opt in enumerate(question.options[:4], 1):
            prompt += f"({i}) {opt}\n"
        prompt += f"\nCorrect Answer: Option ({question.correct_index})\n"
    else:
        prompt += f"\nCorrect Answer: {question.correct_answer}\n"
    
    prompt += """
Provide a clear, step-by-step solution with:
1. Key concepts/formulas used
2. Step-by-step working (use LaTeX for math)
3. Final answer verification

Keep it concise but complete. Use LaTeX math notation (e.g., $x^2$, \\frac{a}{b})."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a JEE Main expert. Provide clear, accurate solutions with proper LaTeX formatting."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Solution generation failed: {e}"


# ============================================================================
# LaTeX Generation
# ============================================================================

def escape_latex(text: str) -> str:
    """Escape special LaTeX characters in plain text."""
    # Don't escape if already contains LaTeX commands
    if "\\" in text or "$" in text:
        # Already has LaTeX, do minimal escaping
        text = text.replace("&", r"\&")
        text = text.replace("%", r"\%")
        text = text.replace("#", r"\#")
        return text
    
    # Full escaping for plain text
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def format_question_latex(q: Question, num: int) -> str:
    """Format a single question as LaTeX."""
    # Escape question text (preserve existing LaTeX)
    question_text = escape_latex(q.question_text)
    
    latex = f"\\question[{q.difficulty[0].upper()}] % {q.topic}\n"
    latex += f"{question_text}\n"
    
    if q.question_type == "mcq" and q.options:
        latex += "\\begin{choices}\n"
        for i, opt in enumerate(q.options[:4], 1):
            opt_text = escape_latex(opt)
            if i == q.correct_index:
                latex += f"  \\CorrectChoice {opt_text}\n"
            else:
                latex += f"  \\choice {opt_text}\n"
        latex += "\\end{choices}\n"
    else:
        latex += f"\\textbf{{Answer type: Integer}}\\\\[0.5em]\n"
        latex += f"\\fillin[{q.correct_answer}][1.5cm]\n"
    
    return latex


def generate_latex_document(
    selected: Dict[str, List[Question]],
    config: PaperConfig,
    solutions: Optional[Dict[str, List[str]]] = None
) -> str:
    """Generate complete LaTeX document for the paper."""
    
    timestamp = datetime.now().strftime("%B %d, %Y")
    
    latex = r"""\documentclass[12pt,a4paper]{exam}

% Packages
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{xcolor}
\usepackage{tikz}
\usepackage{enumitem}
\usepackage{multicol}

% Page geometry
\geometry{
    top=1.5cm,
    bottom=2cm,
    left=2cm,
    right=2cm,
    headheight=1.5cm
}

% Colors
\definecolor{headerblue}{RGB}{0, 51, 102}
\definecolor{sectiongreen}{RGB}{0, 102, 51}

% Header/Footer
\pagestyle{headandfoot}
\firstpageheader{}{}{}
\runningheader{\textsc{""" + escape_latex(config.paper_title) + r"""}}{}{\textsc{Page \thepage}}
\runningfooter{}{Generated: """ + timestamp + r"""}{}

% Custom commands
\newcommand{\sectiontitle}[1]{%
    \vspace{1em}
    \noindent\colorbox{headerblue}{\parbox{\dimexpr\textwidth-2\fboxsep}{%
        \centering\color{white}\Large\bfseries #1
    }}
    \vspace{0.5em}
}

% Question format
\renewcommand{\questionlabel}{\textbf{Q\thequestion.}}
\renewcommand{\choicelabel}{(\thechoice)}

% Print answers setting
\printanswers  % Comment this to hide answers

\begin{document}

% Title Page
\begin{center}
    {\Huge\bfseries\color{headerblue} """ + escape_latex(config.paper_title) + r"""}\\[0.5em]
    {\large Based on JEE Main Pattern}\\[1em]
    {\normalsize Generated: """ + timestamp + r""" | Difficulty: """ + config.difficulty.capitalize() + r"""}\\[0.5em]
    \rule{\textwidth}{1pt}
\end{center}

\vspace{0.5em}
\noindent\textbf{Instructions:}
\begin{itemize}[nosep,leftmargin=*]
    \item This paper contains 90 questions (30 per subject).
    \item Each subject has 20 MCQs and 10 Integer Type questions.
    \item MCQ: +4 for correct, -1 for incorrect.
    \item Integer: +4 for correct, 0 for incorrect.
    \item Time: 3 hours | Maximum Marks: 360
\end{itemize}
\rule{\textwidth}{0.5pt}

"""
    
    question_num = 1
    
    for subject in ["Physics", "Chemistry", "Mathematics"]:
        questions = selected.get(subject, [])
        if not questions:
            continue
        
        latex += f"\n\\sectiontitle{{{subject}}}\n\n"
        
        # Separate MCQ and Integer
        mcqs = [q for q in questions if q.question_type == "mcq"]
        integers = [q for q in questions if q.question_type == "integer"]
        
        if mcqs:
            latex += "\\subsection*{Section A: Multiple Choice Questions (MCQ)}\n"
            latex += "\\begin{questions}\n"
            latex += f"\\setcounter{{question}}{{{question_num - 1}}}\n"
            for q in mcqs[:20]:
                latex += format_question_latex(q, question_num)
                latex += "\n"
                question_num += 1
            latex += "\\end{questions}\n\n"
        
        if integers:
            latex += "\\subsection*{Section B: Integer Type Questions}\n"
            latex += "\\begin{questions}\n"
            latex += f"\\setcounter{{question}}{{{question_num - 1}}}\n"
            for q in integers[:10]:
                latex += format_question_latex(q, question_num)
                latex += "\n"
                question_num += 1
            latex += "\\end{questions}\n\n"
    
    # Answer Key Section
    latex += r"""
\newpage
\sectiontitle{Answer Key}

\begin{multicols}{3}
"""
    
    question_num = 1
    for subject in ["Physics", "Chemistry", "Mathematics"]:
        latex += f"\\textbf{{{subject}}}\\\\[0.5em]\n"
        questions = selected.get(subject, [])
        for q in questions[:30]:
            if q.question_type == "mcq":
                ans = f"({q.correct_index})" if q.correct_index else "(--)"
            else:
                ans = str(q.correct_answer) if q.correct_answer is not None else "--"
            latex += f"Q{question_num}: {ans}\\quad\n"
            if question_num % 5 == 0:
                latex += "\\\\[0.3em]\n"
            question_num += 1
        latex += "\\vspace{1em}\n\n"
    
    latex += r"""
\end{multicols}
"""
    
    # Solutions Section (if provided)
    if solutions and config.include_solutions:
        latex += r"""
\newpage
\sectiontitle{Solutions with Explanations}

"""
        question_num = 1
        for subject in ["Physics", "Chemistry", "Mathematics"]:
            latex += f"\\subsection*{{{subject}}}\n\n"
            questions = selected.get(subject, [])
            subj_solutions = solutions.get(subject, [])
            
            for i, q in enumerate(questions[:30]):
                sol = subj_solutions[i] if i < len(subj_solutions) else "Solution not available."
                latex += f"\\textbf{{Q{question_num}.}} ({q.topic} - {q.difficulty.capitalize()})\\\\[0.3em]\n"
                latex += f"{escape_latex(sol)}\\\\[1em]\n\n"
                question_num += 1
    
    latex += r"""
\end{document}
"""
    
    return latex


# ============================================================================
# PDF Compilation
# ============================================================================

def compile_latex_to_pdf(latex_content: str, output_path: Path) -> bool:
    """Compile LaTeX to PDF using pdflatex."""
    
    # Create temp directory for compilation
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = Path(tmpdir) / "paper.tex"
        
        # Write LaTeX file
        tex_file.write_text(latex_content, encoding="utf-8")
        
        # Run pdflatex (twice for references)
        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, str(tex_file)],
                capture_output=True,
                text=True,
                cwd=tmpdir
            )
            
            if result.returncode != 0:
                print(f"LaTeX compilation warning (may still succeed):")
                # Only show last 20 lines of error
                error_lines = result.stdout.split("\n")[-20:]
                for line in error_lines:
                    if line.strip():
                        print(f"  {line}")
        
        # Check if PDF was created
        pdf_file = Path(tmpdir) / "paper.pdf"
        if pdf_file.exists():
            # Copy to output location
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(pdf_file, output_path)
            return True
        else:
            print("Error: PDF file was not created")
            return False


def check_latex_installed() -> bool:
    """Check if LaTeX (pdflatex) is installed and accessible."""
    try:
        result = subprocess.run(
            ["pdflatex", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


# ============================================================================
# Main Pipeline
# ============================================================================

def generate_paper(config: PaperConfig, generate_solutions: bool = False) -> Optional[Path]:
    """Main entry point for paper generation."""
    
    print("=" * 60)
    print("JEE Paper Generator")
    print("=" * 60)
    
    # Check LaTeX installation
    if not check_latex_installed():
        print("\nError: LaTeX (pdflatex) not found!")
        print("Please install MiKTeX or TeX Live and ensure pdflatex is in PATH.")
        print("\nAfter installing MiKTeX, you may need to:")
        print("  1. Restart your terminal/VS Code")
        print("  2. Or add MiKTeX to PATH manually")
        return None
    
    print("✓ LaTeX installation found")
    
    # Load questions
    print(f"\nLoading questions from: {INPUT_FILE}")
    questions = load_questions()
    print(f"Loaded {len(questions)} questions")
    
    # Filter and organize
    print(f"\nApplying filters...")
    print(f"  Difficulty: {config.difficulty}")
    if config.year_filter:
        print(f"  Years: {config.year_filter}")
    if config.topic_filter:
        print(f"  Topics: {config.topic_filter}")
    
    organized = filter_questions(questions, config)
    
    # Show available counts
    print("\nAvailable questions:")
    for subj in ["Physics", "Chemistry", "Mathematics"]:
        mcq_count = sum(len(organized[subj]["mcq"][d]) for d in ["easy", "medium", "hard"])
        int_count = sum(len(organized[subj]["integer"][d]) for d in ["easy", "medium", "hard"])
        print(f"  {subj}: {mcq_count} MCQ, {int_count} Integer")
    
    # Select questions
    print(f"\nSelecting questions (difficulty: {config.difficulty})...")
    selected = select_questions(organized, config)
    
    total_selected = sum(len(qs) for qs in selected.values())
    print(f"Selected {total_selected} questions total")
    
    # Generate solutions if requested
    solutions = None
    if generate_solutions and config.include_solutions:
        print("\nGenerating solutions (this may take a few minutes)...")
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            client = OpenAI(api_key=api_key)
            solutions = {}
            for subject in ["Physics", "Chemistry", "Mathematics"]:
                solutions[subject] = []
                for i, q in enumerate(selected[subject][:30]):
                    print(f"  {subject} Q{i+1}/30...", end="\r")
                    sol = generate_solution(client, q)
                    solutions[subject].append(sol)
                print(f"  {subject}: Done!                ")
        else:
            print("  Warning: OPENAI_API_KEY not set, skipping solutions")
    
    # Generate LaTeX
    print("\nGenerating LaTeX document...")
    latex_content = generate_latex_document(selected, config, solutions)
    
    # Compile to PDF
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paper_name = f"{config.paper_title.replace(' ', '_')}_{config.difficulty}_{timestamp}"
    output_path = OUTPUT_DIR / f"{paper_name}.pdf"
    
    print(f"Compiling PDF: {output_path}")
    
    if compile_latex_to_pdf(latex_content, output_path):
        print(f"\n✓ Paper generated successfully!")
        print(f"  Output: {output_path}")
        
        # Also save the .tex file for debugging/customization
        tex_path = OUTPUT_DIR / f"{paper_name}.tex"
        tex_path.write_text(latex_content, encoding="utf-8")
        print(f"  LaTeX source: {tex_path}")
        
        return output_path
    else:
        # Save tex file even if PDF failed
        tex_path = OUTPUT_DIR / f"{paper_name}.tex"
        tex_path.write_text(latex_content, encoding="utf-8")
        print(f"\nPDF compilation failed, but LaTeX saved: {tex_path}")
        return None


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate JEE Main style practice papers with PDF output."
    )
    parser.add_argument(
        "--difficulty", "-d",
        choices=["easy", "medium", "hard", "balanced"],
        default="medium",
        help="Overall difficulty level (default: medium)"
    )
    parser.add_argument(
        "--years", "-y",
        type=str,
        default=None,
        help="Comma-separated years to include (e.g., '2024,2025')"
    )
    parser.add_argument(
        "--topics", "-t",
        type=str,
        default=None,
        help="Comma-separated topics to focus on (partial match)"
    )
    parser.add_argument(
        "--title",
        type=str,
        default="JEE Main Practice Paper",
        help="Title for the paper"
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--no-solutions",
        action="store_true",
        help="Skip solution generation (faster)"
    )
    parser.add_argument(
        "--generate-solutions",
        action="store_true",
        help="Generate step-by-step solutions using LLM (slower, uses API credits)"
    )
    
    args = parser.parse_args()
    
    # Parse arguments
    year_filter = None
    if args.years:
        year_filter = [int(y.strip()) for y in args.years.split(",")]
    
    topic_filter = None
    if args.topics:
        topic_filter = [t.strip() for t in args.topics.split(",")]
    
    config = PaperConfig(
        difficulty=args.difficulty,
        year_filter=year_filter,
        topic_filter=topic_filter,
        include_solutions=not args.no_solutions,
        paper_title=args.title,
        seed=args.seed,
    )
    
    generate_paper(config, generate_solutions=args.generate_solutions)


if __name__ == "__main__":
    main()
