"""
Nougat-based Question Parser
Parses questions from Nougat Markdown output (.mmd files)
Handles mathematical formulas in LaTeX format correctly
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class QuestionOption:
    """Represents a single question option"""
    id: str
    latex: str
    text: Optional[str] = None


@dataclass
class NougatQuestion:
    """Represents a parsed question from Nougat output"""
    question_id: str
    question_number: int
    question_latex: str
    options: List[Dict]
    correct_answer: Optional[str]  # None if answer could not be extracted
    subject: str = "Mathematics"
    question_type: str = "MCQ"
    
    def to_dict(self):
        return {
            "question_id": self.question_id,
            "question_number": self.question_number,
            "question_latex": self.question_latex,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "subject": self.subject,
            "question_type": self.question_type
        }


class NougatQuestionParser:
    """
    Parses questions from Nougat Markdown output
    
    Nougat converts PDFs to clean Markdown with:
    - Proper LaTeX formatting for math
    - Clear structure and formatting
    - Better text preservation than PyMuPDF
    """

    def __init__(self):
        # Pattern to match question starts: Q1., Q2., etc.
        self.question_start_pattern = re.compile(
            r'^Q(\d+)\s*[.)\-:]?\s*',
            re.MULTILINE | re.IGNORECASE
        )
        
        # Pattern to match options: (1) ..., (2) ..., etc.
        self.option_pattern = re.compile(
            r'^\s*\(([1-4])\)\s*(.+?)(?=\n\s*\(|\n\s*Q\d|$)',
            re.MULTILINE | re.DOTALL
        )
        
        # Pattern to match answer indicators
        self.answer_pattern = re.compile(
            r'(?:Answer|Correct\s*Answer)\s*[:=]?\s*(?:\()?([1-4]|[A-D])',
            re.IGNORECASE
        )

    def parse_markdown_content(self, content: str, paper_id: str = "") -> List[NougatQuestion]:
        """
        Parse full Nougat markdown content into questions
        
        Args:
            content: Full markdown string from .mmd file
            paper_id: Paper identifier (e.g., "JEE Main 2024 01 Feb Shift 1")
            
        Returns:
            List of parsed NougatQuestion objects
        """
        questions = []
        
        # Split into question sections
        question_sections = self._split_into_question_sections(content)
        
        for q_num, section in question_sections:
            try:
                question = self._parse_question_section(section, q_num, paper_id)
                if question:
                    questions.append(question)
                    logger.debug(f"Parsed Q{q_num}")
            except Exception as e:
                logger.warning(f"Error parsing Q{q_num}: {str(e)}")
                continue
        
        logger.info(f"Successfully parsed {len(questions)} questions")
        return questions

    def _split_into_question_sections(self, content: str) -> List[Tuple[int, str]]:
        """
        Split content into individual question sections
        
        Returns list of (question_number, section_text) tuples
        """
        sections = []
        
        # Find all question starts
        matches = list(self.question_start_pattern.finditer(content))
        
        if not matches:
            logger.warning("No questions found in content")
            return []
        
        for i, match in enumerate(matches):
            q_num = int(match.group(1))
            start_pos = match.start()
            
            # End position is the start of next question or end of content
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            
            section_text = content[start_pos:end_pos]
            sections.append((q_num, section_text))
        
        return sections

    def _parse_question_section(self, section: str, q_num: int, 
                               paper_id: str) -> Optional[NougatQuestion]:
        """
        Parse a single question section
        
        Extracts question text, options, and answer
        """
        # Remove question number from beginning
        section = re.sub(r'^Q\d+\s*[.)\-:]?\s*', '', section, flags=re.IGNORECASE)
        
        # Extract options
        options, remaining_text = self._extract_options(section)
        
        if not options:
            logger.warning(f"Q{q_num}: No valid options found")
            return None
        
        if len(options) < 4:
            logger.warning(f"Q{q_num}: Less than 4 options found")
            return None
        
        # Question text is everything before options
        question_latex = self._extract_question_text(remaining_text, options)
        
        if not question_latex:
            logger.warning(f"Q{q_num}: No question text extracted")
            return None
        
        # Try to find answer
        correct_answer = self._extract_answer(section)
        
        # Detect subject
        subject = self._detect_subject(question_latex)
        
        # Detect question type
        question_type = self._detect_question_type(options)
        
        # Build question ID
        question_id = self._build_question_id(paper_id, q_num)
        
        return NougatQuestion(
            question_id=question_id,
            question_number=q_num,
            question_latex=question_latex.strip(),
            options=options,
            correct_answer=correct_answer,
            subject=subject,
            question_type=question_type
        )

    def _extract_options(self, text: str) -> Tuple[List[Dict], str]:
        """
        Extract options from text
        
        Returns (options_list, remaining_text)
        """
        options = []
        
        # More robust option pattern
        option_pattern = re.compile(
            r'\(([1-4])\)\s*(.+?)(?=\n\s*\([1-4]\)|\n\s*(?:Answer|Correct)|\Z)',
            re.MULTILINE | re.DOTALL
        )
        
        matches = list(option_pattern.finditer(text))
        
        if not matches:
            return [], text
        
        for match in matches:
            option_id = match.group(1)
            option_text = match.group(2).strip()
            
            # Clean up option text (remove extra whitespace, newlines)
            option_text = re.sub(r'\s+', ' ', option_text)
            option_text = option_text.strip('.,;\n')
            
            if option_text:
                options.append({
                    "id": option_id,
                    "latex": option_text,
                    "text": option_text
                })
        
        # Find where options start in original text
        if matches:
            first_option_pos = matches[0].start()
            remaining_text = text[:first_option_pos]
        else:
            remaining_text = text
        
        return options, remaining_text

    def _extract_question_text(self, text: str, options: List[Dict]) -> str:
        """
        Extract and clean question text
        
        Preserves LaTeX formatting, removes option references
        """
        # Remove trailing whitespace
        question_text = text.strip()
        
        # Remove common suffixes that might be before options
        question_text = re.sub(r'(?:Choose|Select|Find|The\s+value|is\s+given\s+by)?\s*:?\s*$', 
                              ':', question_text)
        
        # Ensure ends with colon if it doesn't
        if question_text and not question_text.endswith(':'):
            question_text += ':'
        
        return question_text

    def _extract_answer(self, text: str) -> Optional[str]:
        """
        Extract correct answer from text
        
        Looks for patterns like "Answer: 1" or "Correct Answer: (2)"
        Returns None if answer cannot be found (for manual review)
        """
        # Pattern 1: "Answer: 1" or "Answer: (1)"
        match = re.search(r'(?:Answer|Correct\s*Answer)\s*[:=]?\s*\(?([1-4])\)?', 
                         text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
        
        # Pattern 2: At end of last option "Ans: 2"
        match = re.search(r'(?:Ans|Answer)\s*[:=]?\s*\(?([1-4])\)?(?:\s|$)', 
                         text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Return None if not found - allows filtering for manual review
        logger.warning("Could not extract answer, returning None")
        return None

    def _detect_subject(self, question_text: str) -> str:
        """
        Detect subject based on question content
        """
        text_lower = question_text.lower()
        
        # Chemistry indicators
        chem_keywords = [
            'atom', 'molecule', 'bond', 'reaction', 'compound', 'element',
            'valency', 'oxidation', 'pH', 'acid', 'base', 'salt', 'organic',
            'inorganic', 'structure', 'smiles', 'chemical'
        ]
        
        # Physics indicators
        physics_keywords = [
            'force', 'velocity', 'acceleration', 'energy', 'momentum', 'wave',
            'field', 'charge', 'magnetic', 'electric', 'motion', 'particle',
            'temperature', 'pressure', 'optics', 'mechanics'
        ]
        
        chem_count = sum(1 for kw in chem_keywords if kw in text_lower)
        physics_count = sum(1 for kw in physics_keywords if kw in text_lower)
        
        if chem_count > physics_count:
            return "Chemistry"
        elif physics_count > 0:
            return "Physics"
        else:
            return "Mathematics"

    def _detect_question_type(self, options: List[Dict]) -> str:
        """
        Detect question type based on options
        """
        if not options:
            return "MCQ"
        
        # If options have LaTeX-like content with equals or equations
        first_option = options[0].get('latex', '').lower()
        
        if any(x in first_option for x in ['sin', 'cos', 'tan', 'log', 'sqrt', '^', '$']):
            return "MCQ"
        elif any(x in first_option for x in ['true', 'false', 'correct', 'incorrect']):
            return "MCQ"
        else:
            return "MCQ"  # Default to MCQ

    def _build_question_id(self, paper_id: str, q_num: int) -> str:
        """
        Build unique question ID
        """
        # Clean paper_id
        clean_id = paper_id.replace(' ', '_').replace('(', '').replace(')', '')
        clean_id = re.sub(r'[^a-zA-Z0-9_-]', '', clean_id)[:30]
        
        if clean_id:
            return f"{clean_id}_q{q_num}"
        else:
            return f"jee_question_q{q_num}"

    def parse_and_save_json(self, markdown_content: str, output_file: str, 
                           paper_id: str = "") -> List[NougatQuestion]:
        """
        Parse markdown and save directly to JSON file
        
        Args:
            markdown_content: Full markdown string from .mmd file
            output_file: Path to save JSON file
            paper_id: Paper identifier
            
        Returns:
            List of parsed NougatQuestion objects (allows reuse without re-parsing)
        """
        questions = self.parse_markdown_content(markdown_content, paper_id)
        
        # Convert to dict format
        questions_data = {
            "paper_id": paper_id,
            "total_questions": len(questions),
            "parsing_method": "nougat",
            "questions": [q.to_dict() for q in questions]
        }
        
        # Save to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(questions_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(questions)} questions to {output_file}")
        return questions  # Return parsed questions for reuse


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example markdown content (from Nougat)
    example_markdown = """
Q1. A particle moving in a circle of radius $R$ with uniform speed takes time $T$ to complete one revolution. If this particle is projected with the same speed at an angle $\\theta$ to the horizontal, the maximum height attained by it is equal to $4R$. The angle of projection $\\theta$ is then given by:

(1) $\\sin^{-1}\\left(\\sqrt{\\frac{2gT^2}{\\pi^2 R}}\\right)$

(2) $\\sin^{-1}\\left(\\sqrt{\\frac{\\pi^2 R}{2gT^2}}\\right)$

(3) $\\cos^{-1}\\left(\\sqrt{\\frac{2gT^2}{\\pi^2 R}}\\right)$

(4) $\\cos^{-1}\\left(\\sqrt{\\frac{\\pi R}{2gT^2}}\\right)$

Answer: 1

Q2. Consider a block and trolley system. The coefficient of kinetic friction between the trolley and surface is 0.04. Find the acceleration.

(1) 1.2 m/s²

(2) 2 m/s²

(3) 3 m/s²

(4) 4 m/s²

Answer: 3
"""
    
    parser = NougatQuestionParser()
    questions = parser.parse_markdown_content(
        example_markdown,
        paper_id="JEE Main 2024 01 Feb Shift 1"
    )
    
    print(f"\n✅ Parsed {len(questions)} questions\n")
    for q in questions:
        print(f"Q{q.question_number}: {q.subject} ({q.question_type})")
        print(f"  Answer: {q.correct_answer}")
        print(f"  Options: {len(q.options)}")
        print()
