"""
Question Parser Component
Parses raw extracted text blocks into structured question objects
"""

import json
import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Option:
    """Represents a single MCQ option"""
    id: str
    text: str
    latex: Optional[str] = None


@dataclass
class Question:
    """Represents a parsed JEE question"""
    question_id: str
    exam_name: str
    exam_date_shift: str
    subject: str
    question_number: int
    question_type: str
    question_text: str
    question_latex: Optional[str]
    question_images: List[str]
    chemical_smiles: List[str]
    options: List[Dict]
    correct_answer: str
    ml_annotations: Dict

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "question_id": self.question_id,
            "exam_name": self.exam_name,
            "exam_date_shift": self.exam_date_shift,
            "subject": self.subject,
            "question_number": self.question_number,
            "question_type": self.question_type,
            "question_text": self.question_text,
            "question_latex": self.question_latex,
            "question_images": self.question_images,
            "chemical_smiles": self.chemical_smiles,
            "options": [
                {
                    "id": opt["id"],
                    "text": opt["text"],
                    "latex": opt.get("latex")
                }
                for opt in self.options
            ],
            "correct_answer": self.correct_answer,
            "ml_annotations": self.ml_annotations
        }


class QuestionParser:
    """
    Parses raw text blocks from PDF extraction into structured questions
    
    Handles:
    - Question number detection (Q1, Q2, etc.)
    - Subject identification (Math, Physics, Chemistry)
    - MCQ option extraction (A, B, C, D)
    - Correct answer identification
    - LaTeX conversion for mathematical notation
    - Question type detection
    """

    def __init__(self):
        self.question_pattern = re.compile(r'^Q(\d+)', re.IGNORECASE)
        self.option_pattern = re.compile(r'^[A-D]\)?\s*(.+)', re.IGNORECASE)
        self.latex_pattern = re.compile(r'\$(.+?)\$')
        
    def parse_paper(self, raw_extraction: Dict) -> Dict:
        """
        Parse entire paper from raw extraction
        
        Args:
            raw_extraction: Output from text_images_extractor.py
            
        Returns:
            Structured paper with questions following jee_question_schema.json
        """
        try:
            # Extract paper metadata
            paper_id = raw_extraction.get("paper_id", "")
            exam_name, exam_date_shift, subject = self._extract_paper_info(paper_id)
            
            # Extract text blocks
            text_blocks = raw_extraction.get("text_blocks", [])
            
            # Parse questions from text blocks
            questions = self._parse_questions(
                text_blocks,
                exam_name,
                exam_date_shift
            )
            
            # Build paper structure
            paper = {
                "paper_metadata": {
                    "exam_name": exam_name,
                    "exam_date_shift": exam_date_shift,
                    "paper_id": paper_id,
                    "total_questions": len(questions),
                    "extraction_timestamp": raw_extraction.get("timestamp", datetime.now().isoformat()),
                    "extraction_method": "pymupdf"
                },
                "questions": [q.to_dict() for q in questions]
            }
            
            logger.info(f"Parsed {len(questions)} questions from paper {paper_id}")
            return paper
            
        except Exception as e:
            logger.error(f"Error parsing paper: {str(e)}")
            raise

    def _extract_paper_info(self, paper_id: str) -> Tuple[str, str, str]:
        """
        Extract exam name, date/shift, and subject from paper_id
        
        Example paper_id: "JEE Main 2024 (01 Feb Shift 1) Previous Year Paper"
        """
        try:
            # Extract exam name (JEE Main/Advanced YYYY)
            exam_match = re.search(r'JEE (Main|Advanced) (\d{4})', paper_id)
            exam_name = f"{exam_match.group(1)} {exam_match.group(2)}" if exam_match else "JEE Main 2024"
            
            # Extract date and shift
            shift_match = re.search(r'(\d{2}\s+\w+\s+Shift\s+\d)', paper_id)
            exam_date_shift = shift_match.group(1) if shift_match else "01 Jan Shift 1"
            
            # Subject detection (typically all three subjects per paper)
            subject = "Multi-subject"  # JEE Main has Math, Physics, Chemistry
            
            return exam_name, exam_date_shift, subject
            
        except Exception as e:
            logger.warning(f"Could not extract paper info from '{paper_id}': {str(e)}")
            return "JEE Main 2024", "01 Jan Shift 1", "Multi-subject"

    def _parse_questions(self, text_blocks: List[Dict], exam_name: str, 
                        exam_date_shift: str) -> List[Question]:
        """
        Parse individual questions from text blocks
        
        Algorithm:
        1. Group text blocks by question number (Q1, Q2, etc.)
        2. For each group, extract question text, options, and answer
        3. Detect subject from context
        4. Create Question objects
        """
        questions = []
        current_q_num = 0
        current_question_text = []
        current_options = {}
        current_answer = None
        current_subject = "Mathematics"  # Default
        current_images = []
        
        for block in text_blocks:
            text = block.get("text", {}).get("text", "").strip()
            if not text:
                continue
            
            # Check for question number marker (Q1, Q2, etc.)
            q_match = self.question_pattern.match(text)
            if q_match:
                # Save previous question if exists
                if current_q_num > 0 and current_question_text:
                    question = self._create_question(
                        current_q_num,
                        current_question_text,
                        current_options,
                        current_answer,
                        current_subject,
                        current_images,
                        exam_name,
                        exam_date_shift
                    )
                    if question:
                        questions.append(question)
                
                # Start new question
                current_q_num = int(q_match.group(1))
                current_question_text = [text]
                current_options = {}
                current_answer = None
                current_images = []
                
            else:
                # Check for numbered options (1), (2), (3), (4) - JEE format
                opt_num_match = re.match(r'\(([1-4])\)', text)
                if opt_num_match and current_q_num > 0:
                    # Extract option number and store option text
                    opt_num = opt_num_match.group(1)
                    current_options[opt_num] = text
                    
                # Check for lettered options (A), (B), (C), (D) - fallback format
                elif current_q_num > 0:
                    opt_match = self.option_pattern.match(text)
                    if opt_match:
                        # Extract option letter and text
                        opt_letter = text[0].upper()
                        if opt_letter in ['A', 'B', 'C', 'D']:
                            current_options[opt_letter] = text
                        else:
                            current_question_text.append(text)
                    # Check for answer indicator
                    elif "answer" in text.lower() or "correct" in text.lower():
                        # Try to extract correct answer
                        current_answer = self._extract_answer(text)
                    # Otherwise add to current question text
                    else:
                        current_question_text.append(text)
                
                # If no question number yet, skip
                else:
                    if current_q_num > 0:
                        current_question_text.append(text)
        
        # Add last question
        if current_q_num > 0 and current_question_text:
            question = self._create_question(
                current_q_num,
                current_question_text,
                current_options,
                current_answer,
                current_subject,
                current_images,
                exam_name,
                exam_date_shift
            )
            if question:
                questions.append(question)
        
        return questions

    def _create_question(self, q_num: int, q_text_list: List[str], 
                        options_dict: Dict, answer: str, subject: str,
                        images: List[str], exam_name: str, 
                        exam_date_shift: str) -> Optional[Question]:
        """
        Create a Question object from parsed components
        """
        try:
            if not q_text_list or not options_dict:
                return None
            
            # Combine question text
            question_text = " ".join(q_text_list).strip()
            
            # Remove question number from beginning
            question_text = re.sub(r'^Q\d+\.?\s*', '', question_text, flags=re.IGNORECASE)
            
            # Generate question ID
            paper_id = f"{exam_name.replace(' ', '_')}_{exam_date_shift.replace(' ', '_')}"
            question_id = f"{paper_id}_q{q_num}"
            
            # Detect subject from question content
            subject = self._detect_subject(question_text)
            
            # Detect question type
            question_type = self._detect_question_type(question_text)
            
            # Convert options dict to list format
            options_list = [
                {
                    "id": opt_id,
                    "text": options_dict[opt_id],
                    "latex": self._extract_latex(options_dict[opt_id])
                }
                for opt_id in sorted(options_dict.keys())
            ]
            
            # Extract LaTeX version
            question_latex = self._to_latex(question_text)
            
            # Get/validate correct answer
            correct_answer = answer or "1"  # Default if not found
            
            question = Question(
                question_id=question_id,
                exam_name=exam_name,
                exam_date_shift=exam_date_shift,
                subject=subject,
                question_number=q_num,
                question_type=question_type,
                question_text=question_text,
                question_latex=question_latex,
                question_images=images,
                chemical_smiles=[],
                options=options_list,
                correct_answer=correct_answer,
                ml_annotations={
                    "difficulty": None,
                    "concepts": [],
                    "computable_solution": None
                }
            )
            
            return question
            
        except Exception as e:
            logger.warning(f"Error creating question Q{q_num}: {str(e)}")
            return None

    def _detect_subject(self, text: str) -> str:
        """Detect subject based on question content"""
        text_lower = text.lower()
        
        # Chemistry indicators
        chem_keywords = ['molecule', 'element', 'atom', 'compound', 'reaction', 'bond', 'valency', 'smiles', 'organic', 'inorganic', 'chemical']
        if any(kw in text_lower for kw in chem_keywords):
            return "Chemistry"
        
        # Physics indicators
        physics_keywords = ['force', 'velocity', 'acceleration', 'energy', 'momentum', 'wave', 'field', 'charge', 'magnetic', 'electric', 'motion']
        if any(kw in text_lower for kw in physics_keywords):
            return "Physics"
        
        # Default to Mathematics
        return "Mathematics"

    def _detect_question_type(self, text: str) -> str:
        """Detect question type (MCQ, Numerical, etc.)"""
        text_lower = text.lower()
        
        if "column" in text_lower and "match" in text_lower:
            return "Match the Column"
        elif "assert" in text_lower or "reason" in text_lower:
            return "Assertion-Reason"
        elif "value" in text_lower or "find" in text_lower or "calculate" in text_lower:
            return "Numerical"
        else:
            return "MCQ"

    def _extract_answer(self, answer_text: str) -> str:
        """Extract correct answer from answer text"""
        # Look for patterns like "Answer: A" or "Correct answer is B"
        match = re.search(r'[Aa]nswer[:\s]+([A-D])', answer_text)
        if match:
            return match.group(1)
        
        match = re.search(r'\(([A-D])\)', answer_text)
        if match:
            return match.group(1)
        
        # Default to first option
        return "A"

    def _extract_latex(self, text: str) -> Optional[str]:
        """Extract LaTeX content from text if present"""
        latex_parts = self.latex_pattern.findall(text)
        if latex_parts:
            return "$" + latex_parts[0] + "$"
        return None

    def _to_latex(self, text: str) -> Optional[str]:
        """
        Convert plain text mathematical expressions to LaTeX
        
        This is a simplified version. A production system would use
        more sophisticated math OCR/recognition
        """
        # Check if text already contains LaTeX
        if "$" in text:
            return text
        
        # Common patterns to convert
        conversions = {
            r'(\d+)x(\d+)': r'$\1 \\times \2$',
            r'(\w+)\^(\d+)': r'$\1^{\2}$',
            r'(\w+)/(\w+)': r'$\\frac{\1}{\2}$',
        }
        
        result = text
        for pattern, replacement in conversions.items():
            result = re.sub(pattern, replacement, result)
        
        return result if "$" in result else None
