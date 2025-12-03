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

def fix_unicode_for_latex(text: str) -> str:
    """Convert Unicode symbols to proper LaTeX before output."""
    import re
    
    if not text:
        return text
    
    # Replace Unicode math symbols with LaTeX
    replacements = [
        ('×', r'$\times$'),
        ('−', '-'),
        ('–', '-'),
        ('—', '-'),
        ('√', r'$\sqrt{}$'),
        ('α', r'$\alpha$'),
        ('β', r'$\beta$'),
        ('γ', r'$\gamma$'),
        ('δ', r'$\delta$'),
        ('Δ', r'$\Delta$'),
        ('θ', r'$\theta$'),
        ('λ', r'$\lambda$'),
        ('μ', r'$\mu$'),
        ('π', r'$\pi$'),
        ('ρ', r'$\rho$'),
        ('σ', r'$\sigma$'),
        ('τ', r'$\tau$'),
        ('φ', r'$\varphi$'),
        ('ψ', r'$\psi$'),
        ('ω', r'$\omega$'),
        ('Ω', r'$\Omega$'),
        ('ε', r'$\varepsilon$'),
        ('η', r'$\eta$'),
        ('ν', r'$\nu$'),
        ('°', r'$^\circ$'),
        ('±', r'$\pm$'),
        ('≠', r'$\neq$'),
        ('≤', r'$\leq$'),
        ('≥', r'$\geq$'),
        ('≈', r'$\approx$'),
        ('→', r'$\rightarrow$'),
        ('←', r'$\leftarrow$'),
        ('↔', r'$\leftrightarrow$'),
        ('∞', r'$\infty$'),
        ('∑', r'$\sum$'),
        ('∫', r'$\int$'),
        ('∂', r'$\partial$'),
        ('∇', r'$\nabla$'),
        ('·', r'$\cdot$'),
        ('′', r"'"),
        ('″', r"''"),
        # Mathematical Greek variants (U+1D6xx range)
        ('𝛥', r'$\Delta$'),
        ('𝛼', r'$\alpha$'),
        ('𝛽', r'$\beta$'),
        ('𝛾', r'$\gamma$'),
        ('𝛿', r'$\delta$'),
        ('𝜀', r'$\varepsilon$'),
        ('𝜃', r'$\theta$'),
        ('𝜆', r'$\lambda$'),
        ('𝜇', r'$\mu$'),
        ('𝜋', r'$\pi$'),
        ('𝜌', r'$\rho$'),
        ('𝜎', r'$\sigma$'),
        ('𝜏', r'$\tau$'),
        ('𝜑', r'$\varphi$'),
        ('𝜔', r'$\omega$'),
    ]
    
    for old, new in replacements:
        text = text.replace(old, new)
    
    # Fix Unicode math italic letters (𝐴, 𝐵, 𝑃, 𝑉, etc.)
    def replace_math_unicode(match):
        char = match.group(0)
        code = ord(char)
        # Math bold uppercase (U+1D400-U+1D419)
        if 0x1D400 <= code <= 0x1D419:
            letter = chr(ord('A') + (code - 0x1D400))
            return f'$\\mathbf{{{letter}}}$'
        # Math bold lowercase (U+1D41A-U+1D433)
        elif 0x1D41A <= code <= 0x1D433:
            letter = chr(ord('a') + (code - 0x1D41A))
            return f'$\\mathbf{{{letter}}}$'
        # Math italic uppercase (U+1D434-U+1D44D)
        elif 0x1D434 <= code <= 0x1D44D:
            letter = chr(ord('A') + (code - 0x1D434))
            return f'${letter}$'
        # Math italic lowercase (U+1D44E-U+1D467)
        elif 0x1D44E <= code <= 0x1D467:
            letter = chr(ord('a') + (code - 0x1D44E))
            return f'${letter}$'
        # Math italic small epsilon (U+1D700)
        elif code == 0x1D700:
            return r'$\varepsilon$'
        # Math Greek uppercase (U+1D6A8-U+1D6E1) - Alpha to Omega
        elif 0x1D6A8 <= code <= 0x1D6E1:
            greek_upper = ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta', 'Eta', 'Theta',
                          'Iota', 'Kappa', 'Lambda', 'Mu', 'Nu', 'Xi', 'Omicron', 'Pi',
                          'Rho', 'Theta', 'Sigma', 'Tau', 'Upsilon', 'Phi', 'Chi', 'Psi', 'Omega']
            idx = code - 0x1D6A8
            if idx < len(greek_upper):
                return f'$\\{greek_upper[idx]}$'
        # Math Greek lowercase (U+1D6C2-U+1D6DA) - alpha to omega  
        elif 0x1D6C2 <= code <= 0x1D6FB:
            greek_lower = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta',
                          'iota', 'kappa', 'lambda', 'mu', 'nu', 'xi', 'omicron', 'pi',
                          'rho', 'sigma', 'sigma', 'tau', 'upsilon', 'phi', 'chi', 'psi', 'omega']
            idx = code - 0x1D6C2
            if idx < len(greek_lower):
                return f'$\\{greek_lower[idx]}$'
        # Fallback for any remaining math symbols - just return empty or generic
        return char
    
    text = re.sub(r'[\U0001D400-\U0001D7FF]', replace_math_unicode, text)
    
    # Fix \textasciicircum to proper power notation
    text = re.sub(r'\\textasciicircum\{\}(-?\d+)', r'$^{\1}$', text)
    text = re.sub(r'\\textasciicircum\{\}', '^', text)
    
    # Fix bare powers like 10^-3 to $10^{-3}$
    text = re.sub(r'(\d+)\^(-?\d+)(?![}])', r'$\1^{\2}$', text)
    
    # Wrap unprotected LaTeX math commands in $...$
    # Find LaTeX commands that should be in math mode but aren't
    math_commands = [
        r'\\frac\{[^}]+\}\{[^}]+\}',  # \frac{...}{...}
        r'\\sqrt\{[^}]*\}',            # \sqrt{...}
        r'\\vec\{[^}]+\}',             # \vec{...}
        r'\\hat\{[^}]+\}',             # \hat{...}
        r'\\bar\{[^}]+\}',             # \bar{...}
        r'\\sin\b',                    # \sin
        r'\\cos\b',                    # \cos
        r'\\tan\b',                    # \tan
        r'\\log\b',                    # \log
        r'\\ln\b',                     # \ln
        r'\\exp\b',                    # \exp
    ]
    
    for pattern in math_commands:
        # Find instances not already in math mode
        def wrap_if_not_in_math(match):
            # Check if already wrapped in $
            start = match.start()
            end = match.end()
            before = text[:start]
            # Count $ signs before - if odd, we're in math mode
            dollar_count = before.count('$') - before.count('\\$')
            if dollar_count % 2 == 1:
                return match.group(0)  # Already in math mode
            return '$' + match.group(0) + '$'
        
        text = re.sub(pattern, wrap_if_not_in_math, text)
    
    return text


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters in plain text."""
    # First fix Unicode
    text = fix_unicode_for_latex(text)
    
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
    
    # Simple question format without difficulty markers
    latex = f"\\question\n"
    latex += f"{question_text}\n"
    
    if q.question_type == "mcq" and q.options:
        latex += "\\begin{choices}\n"
        for i, opt in enumerate(q.options[:4], 1):
            opt_text = escape_latex(opt)
            # Use \choice for all options (no highlighting of correct answer)
            latex += f"  \\choice {opt_text}\n"
        latex += "\\end{choices}\n"
    # For integer type, no extra text needed - just the question
    
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
\usepackage{xcolor}
\usepackage{tikz}
\usepackage{enumitem}
\usepackage{multicol}
\usepackage{newunicodechar}

% Unicode math character mappings
\newunicodechar{𝜀}{$\varepsilon$}
\newunicodechar{𝑃}{$P$}
\newunicodechar{𝑉}{$V$}
\newunicodechar{𝐾}{$K$}
\newunicodechar{𝐴}{$A$}
\newunicodechar{𝐵}{$B$}
\newunicodechar{𝐶}{$C$}
\newunicodechar{𝐷}{$D$}
\newunicodechar{𝐸}{$E$}
\newunicodechar{𝑇}{$T$}
\newunicodechar{𝑅}{$R$}
\newunicodechar{𝐼}{$I$}
\newunicodechar{𝑁}{$N$}
\newunicodechar{𝑀}{$M$}
\newunicodechar{𝐿}{$L$}
\newunicodechar{𝑎}{$a$}
\newunicodechar{𝑏}{$b$}
\newunicodechar{𝑐}{$c$}
\newunicodechar{𝑑}{$d$}
\newunicodechar{𝑒}{$e$}
\newunicodechar{𝑓}{$f$}
\newunicodechar{𝑔}{$g$}
\newunicodechar{𝑛}{$n$}
\newunicodechar{𝑚}{$m$}
\newunicodechar{𝑟}{$r$}
\newunicodechar{𝑠}{$s$}
\newunicodechar{𝑡}{$t$}
\newunicodechar{𝑥}{$x$}
\newunicodechar{𝑦}{$y$}
\newunicodechar{𝑧}{$z$}
\newunicodechar{α}{$\alpha$}
\newunicodechar{β}{$\beta$}
\newunicodechar{γ}{$\gamma$}
\newunicodechar{δ}{$\delta$}
\newunicodechar{ε}{$\varepsilon$}
\newunicodechar{θ}{$\theta$}
\newunicodechar{λ}{$\lambda$}
\newunicodechar{μ}{$\mu$}
\newunicodechar{π}{$\pi$}
\newunicodechar{ρ}{$\rho$}
\newunicodechar{σ}{$\sigma$}
\newunicodechar{τ}{$\tau$}
\newunicodechar{φ}{$\varphi$}
\newunicodechar{ω}{$\omega$}
\newunicodechar{Ω}{$\Omega$}
\newunicodechar{°}{$^\circ$}
\newunicodechar{±}{$\pm$}
\newunicodechar{×}{$\times$}
\newunicodechar{÷}{$\div$}
\newunicodechar{√}{$\sqrt{}$}
\newunicodechar{∞}{$\infty$}
\newunicodechar{≠}{$\neq$}
\newunicodechar{≤}{$\leq$}
\newunicodechar{≥}{$\geq$}
\newunicodechar{→}{$\rightarrow$}
\newunicodechar{←}{$\leftarrow$}
\newunicodechar{↔}{$\leftrightarrow$}

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

% Header/Footer using exam class commands
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

% Hide answers in questions (they go in answer key)
\noprintanswers

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

"""
    
    for subject in ["Physics", "Chemistry", "Mathematics"]:
        questions = selected.get(subject, [])
        if not questions:
            continue
            
        # Separate MCQ and Integer for this subject
        mcqs = [q for q in questions if q.question_type == "mcq"][:20]
        integers = [q for q in questions if q.question_type == "integer"][:10]
        
        latex += f"\n\\textbf{{{subject}}}\\\\[0.5em]\n"
        
        # Calculate starting question number for this subject
        subj_idx = ["Physics", "Chemistry", "Mathematics"].index(subject)
        start_num = subj_idx * 30 + 1
        
        # MCQ answers in a nice table
        if mcqs:
            latex += "\\textit{Section A (MCQ):}\\\\[0.3em]\n"
            latex += "\\begin{tabular}{|" + "c|" * 10 + "}\n\\hline\n"
            
            # Row 1: Q1-Q10
            q_nums = " & ".join([f"Q{start_num + i}" for i in range(min(10, len(mcqs)))])
            latex += q_nums + " \\\\\\hline\n"
            answers = " & ".join([f"({q.correct_index})" if q.correct_index else "--" for q in mcqs[:10]])
            latex += answers + " \\\\\\hline\n"
            
            # Row 2: Q11-Q20 (if exists)
            if len(mcqs) > 10:
                q_nums = " & ".join([f"Q{start_num + i}" for i in range(10, min(20, len(mcqs)))])
                latex += q_nums + " \\\\\\hline\n"
                answers = " & ".join([f"({q.correct_index})" if q.correct_index else "--" for q in mcqs[10:20]])
                latex += answers + " \\\\\\hline\n"
            
            latex += "\\end{tabular}\\\\[0.8em]\n"
        
        # Integer answers in a table
        if integers:
            int_start = start_num + len(mcqs)
            latex += "\\textit{Section B (Integer):}\\\\[0.3em]\n"
            latex += "\\begin{tabular}{|" + "c|" * min(10, len(integers)) + "}\n\\hline\n"
            
            q_nums = " & ".join([f"Q{int_start + i}" for i in range(len(integers))])
            latex += q_nums + " \\\\\\hline\n"
            answers = " & ".join([str(q.correct_answer) if q.correct_answer is not None else "--" for q in integers])
            latex += answers + " \\\\\\hline\n"
            
            latex += "\\end{tabular}\\\\[1em]\n"
        
        latex += "\n"
    
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
        
        # Find pdflatex - check MiKTeX path first
        miktex_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/MiKTeX/miktex/bin/x64/pdflatex.exe"
        pdflatex_cmd = str(miktex_path) if miktex_path.exists() else "pdflatex"
        
        # Run pdflatex (twice for references)
        for run_num in range(2):
            try:
                result = subprocess.run(
                    [pdflatex_cmd, "-interaction=nonstopmode", "-output-directory", tmpdir, str(tex_file)],
                    capture_output=True,
                    cwd=tmpdir,
                    timeout=120,
                )
                
                if run_num == 1 and result.returncode != 0:
                    print(f"LaTeX compilation warning (may still succeed)")
                    # Try to read log file for errors
                    log_file = Path(tmpdir) / "paper.log"
                    if log_file.exists():
                        log_content = log_file.read_text(encoding="utf-8", errors="ignore")
                        errors = [l for l in log_content.split("\n") if l.startswith("!")]
                        for e in errors[:5]:
                            # Sanitize for console output
                            print(f"  {e.encode('ascii', 'replace').decode()}")
            except subprocess.TimeoutExpired:
                print("LaTeX compilation timed out")
                return False
            except FileNotFoundError:
                print(f"pdflatex not found: {pdflatex_cmd}")
                return False
        
        # Check if PDF was created
        pdf_file = Path(tmpdir) / "paper.pdf"
        if pdf_file.exists():
            # Copy to output location
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(pdf_file, output_path)
            return True
        else:
            print("Error: PDF file was not created")
            # Show log errors
            log_file = Path(tmpdir) / "paper.log"
            if log_file.exists():
                log_content = log_file.read_text(encoding="utf-8", errors="ignore")
                errors = [l for l in log_content.split("\n") if l.startswith("!")]
                for e in errors[:10]:
                    print(f"  {e.encode('ascii', 'replace').decode()}")
            return False


def check_latex_installed() -> Tuple[bool, str]:
    """Check if LaTeX (pdflatex) is installed and accessible. Returns (found, path)."""
    # Check MiKTeX path first (Windows)
    miktex_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/MiKTeX/miktex/bin/x64/pdflatex.exe"
    if miktex_path.exists():
        return True, str(miktex_path)
    
    # Check system PATH
    try:
        result = subprocess.run(
            ["pdflatex", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return True, "pdflatex"
    except FileNotFoundError:
        pass
    
    return False, ""


# ============================================================================
# Main Pipeline
# ============================================================================

def generate_paper(config: PaperConfig, generate_solutions: bool = False, transform_questions_flag: bool = False) -> Optional[Path]:
    """Main entry point for paper generation."""
    
    print("=" * 60)
    print("JEE Paper Generator")
    print("=" * 60)
    
    # Check LaTeX installation
    latex_found, pdflatex_path = check_latex_installed()
    if not latex_found:
        print("\nError: LaTeX (pdflatex) not found!")
        print("Please install MiKTeX or TeX Live and ensure pdflatex is in PATH.")
        print("\nAfter installing MiKTeX, you may need to:")
        print("  1. Restart your terminal/VS Code")
        print("  2. Or add MiKTeX to PATH manually")
        return None
    
    print(f"[OK] LaTeX installation found: {pdflatex_path}")
    
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
    
    # LLM Transformation (if enabled)
    if transform_questions_flag:
        from llm_transform import transform_questions as llm_transform
        
        # Build full pool for replacements
        all_pool = []
        for subj in ["Physics", "Chemistry", "Mathematics"]:
            for qtype in ["mcq", "integer"]:
                for diff in ["easy", "medium", "hard"]:
                    all_pool.extend(organized[subj][qtype][diff])
        
        # Transform each subject
        for subject in ["Physics", "Chemistry", "Mathematics"]:
            subj_questions = selected.get(subject, [])
            if subj_questions:
                print(f"\nTransforming {subject} questions...")
                # Convert Question objects to dicts for transform
                subj_dicts = [q.__dict__ if hasattr(q, '__dict__') else 
                             {"question_text": q.question_text, "options": q.options, 
                              "question_type": q.question_type, "subject": q.subject,
                              "correct_index": q.correct_index, "correct_answer": q.correct_answer,
                              "topic": q.topic, "difficulty": q.difficulty} 
                             for q in subj_questions]
                
                pool_dicts = [{"question_text": q.question_text, "options": q.options,
                              "question_type": q.question_type, "subject": q.subject,
                              "correct_index": q.correct_index, "correct_answer": q.correct_answer,
                              "topic": q.topic, "difficulty": q.difficulty}
                             for q in all_pool if q.subject == subject]
                
                transformed = llm_transform(subj_dicts, pool_dicts, target_count=len(subj_questions))
                
                # Convert back to Question objects
                from generate_paper import Question
                selected[subject] = [Question.from_dict(t) for t in transformed]
    
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
        print(f"\n[OK] Paper generated successfully!")
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
    parser.add_argument(
        "--transform",
        action="store_true",
        help="Enable LLM transformation (rephrase, change numbers, etc.)"
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
    
    generate_paper(config, generate_solutions=args.generate_solutions, transform_questions_flag=args.transform)


if __name__ == "__main__":
    main()
