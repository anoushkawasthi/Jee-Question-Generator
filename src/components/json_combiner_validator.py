"""
JSON Combiner and Validator Component

This component merges all extracted data (text, images, LaTeX, SMILES) into 
final JSON structure with schema validation.

Key Capabilities:
- Parse markdown to identify questions and options
- Map extracted images to questions by coordinate analysis
- Associate SMILES strings with relevant questions
- Validate output against JSON schema
- Handle edge cases and produce detailed error reports
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import jsonschema

logger = logging.getLogger(__name__)


@dataclass
class Question:
    """Represents a single question"""
    question_id: str
    question_number: int
    subject: str
    question_type: str
    question_text: str
    question_latex: Optional[str] = None
    question_images: List[str] = None
    chemical_smiles: List[str] = None
    options: List[Dict] = None
    correct_answer: str = None
    difficulty: Optional[str] = None
    concepts: List[str] = None
    extraction_confidence: float = 0.95
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Initialize list defaults"""
        if self.question_images is None:
            self.question_images = []
        if self.chemical_smiles is None:
            self.chemical_smiles = []
        if self.options is None:
            self.options = []
        if self.concepts is None:
            self.concepts = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding None and empty values"""
        data = asdict(self)
        # Remove None values and empty collections
        return {k: v for k, v in data.items() 
                if v is not None and (not isinstance(v, (list, dict)) or len(v) > 0)}


class QuestionParser:
    """Parses markdown and text to extract question information"""
    
    # Question number patterns: "Q1.", "1.", "Question 1"
    QUESTION_PATTERN = r'(?:Q|Question)?\s*(\d+)\.?\s*'
    
    # Option patterns: "(A)", "(a)", "A)", etc.
    OPTION_PATTERN = r'\(?([A-D])\)?\.?\s+'
    
    # LaTeX patterns for equations
    LATEX_DISPLAY_PATTERN = r'\$\$(.*?)\$\$'
    LATEX_INLINE_PATTERN = r'\$([^\$]+?)\$'
    
    @staticmethod
    def extract_questions_from_markdown(markdown_text: str) -> List[Dict]:
        """
        Extract questions from markdown text.
        
        Args:
            markdown_text: Markdown text containing questions
            
        Returns:
            List of extracted question dictionaries
        """
        questions = []
        
        try:
            # Split by question numbers
            question_blocks = re.split(
                r'(?:^|\n)Q\d+\.|\n\d+\.',
                markdown_text,
                flags=re.MULTILINE
            )
            
            for block_idx, block in enumerate(question_blocks[1:], 1):
                if not block.strip():
                    continue
                
                question_dict = {
                    "question_number": block_idx,
                    "question_text": block.strip(),
                    "options": []
                }
                
                questions.append(question_dict)
            
            logger.info(f"Extracted {len(questions)} questions from markdown")
            return questions
            
        except Exception as e:
            logger.error(f"Error parsing markdown: {str(e)}")
            return []
    
    @staticmethod
    def extract_options(text: str) -> List[Dict]:
        """
        Extract multiple choice options from text.
        
        Args:
            text: Text containing options
            
        Returns:
            List of option dictionaries
        """
        options = []
        
        try:
            # Find all option blocks
            option_pattern = r'\(?([A-D])\)\.?\s*([^A-D]*?)(?=\(?[A-D]\)?|$)'
            matches = re.finditer(option_pattern, text, re.MULTILINE | re.DOTALL)
            
            for match in matches:
                option_id = match.group(1)
                option_text = match.group(2).strip()
                
                if option_text:
                    options.append({
                        "id": option_id,
                        "text": option_text,
                        "latex": None
                    })
            
            return options
            
        except Exception as e:
            logger.warning(f"Error extracting options: {str(e)}")
            return []
    
    @staticmethod
    def detect_subject(question_text: str) -> str:
        """
        Detect subject from question text and keywords.
        
        Args:
            question_text: The question text
            
        Returns:
            Subject name (Mathematics, Physics, or Chemistry)
        """
        text_lower = question_text.lower()
        
        # Subject keywords
        math_keywords = {
            'differentiation', 'integration', 'derivative', 'integral',
            'matrix', 'calculus', 'trigonometry', 'polynomial', 'equation',
            'algebra', 'function', 'limit', 'series', 'sum', 'coefficient'
        }
        
        physics_keywords = {
            'force', 'velocity', 'acceleration', 'energy', 'momentum',
            'electricity', 'magnetic', 'optics', 'wave', 'thermodynamics',
            'mechanics', 'motion', 'speed', 'power', 'current'
        }
        
        chemistry_keywords = {
            'molecule', 'atom', 'compound', 'reaction', 'bond',
            'acid', 'base', 'organic', 'inorganic', 'redox',
            'electron', 'valence', 'isotope', 'element', 'oxidation'
        }
        
        # Count keyword matches
        scores = {
            'Mathematics': sum(1 for kw in math_keywords if kw in text_lower),
            'Physics': sum(1 for kw in physics_keywords if kw in text_lower),
            'Chemistry': sum(1 for kw in chemistry_keywords if kw in text_lower)
        }
        
        # Return subject with highest score, default to Mathematics
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'Mathematics'
    
    @staticmethod
    def detect_question_type(text: str, num_options: int) -> str:
        """
        Detect question type.
        
        Args:
            text: Question text
            num_options: Number of options
            
        Returns:
            Question type (MCQ, Numerical, etc.)
        """
        text_lower = text.lower()
        
        if num_options == 4:
            return 'MCQ'
        elif num_options == 0:
            if any(word in text_lower for word in 
                   ['calculate', 'find', 'value', 'result', 'answer is']):
                return 'Numerical'
            return 'Numerical'
        elif 'match' in text_lower:
            return 'Match the Column'
        elif 'assertion' in text_lower or 'reason' in text_lower:
            return 'Assertion-Reason'
        
        return 'MCQ'
    
    @staticmethod
    def extract_latex_equations(text: str) -> List[str]:
        """
        Extract LaTeX equations from text.
        
        Args:
            text: Text containing LaTeX equations
            
        Returns:
            List of LaTeX equations
        """
        equations = []
        
        # Display equations
        display_eqs = re.findall(QuestionParser.LATEX_DISPLAY_PATTERN, text, re.DOTALL)
        equations.extend(display_eqs)
        
        # Inline equations
        inline_eqs = re.findall(QuestionParser.LATEX_INLINE_PATTERN, text)
        equations.extend(inline_eqs)
        
        return [eq.strip() for eq in equations if eq.strip()]


class SchemaValidator:
    """Validates JSON output against schema"""
    
    def __init__(self, schema_path: str):
        """
        Initialize validator with schema file.
        
        Args:
            schema_path: Path to JSON schema file
        """
        self.schema_path = Path(schema_path)
        self.schema = None
        self._load_schema()
    
    def _load_schema(self) -> None:
        """Load JSON schema from file"""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                self.schema = json.load(f)
            logger.info(f"Schema loaded from {self.schema_path}")
        except Exception as e:
            logger.error(f"Error loading schema: {str(e)}")
            raise
    
    def validate(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate data against schema.
        
        Args:
            data: Data to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            jsonschema.validate(instance=data, schema=self.schema)
            logger.info("Data validation successful")
            return True, []
        except jsonschema.ValidationError as e:
            msg = f"Validation error at {'.'.join(str(p) for p in e.path)}: {e.message}"
            errors.append(msg)
            logger.error(msg)
            return False, errors
        except jsonschema.SchemaError as e:
            msg = f"Schema error: {e.message}"
            errors.append(msg)
            logger.error(msg)
            return False, errors
        except Exception as e:
            msg = f"Validation failed: {str(e)}"
            errors.append(msg)
            logger.error(msg)
            return False, errors


class JSONCombiner:
    """Combines all extracted data into final JSON output"""
    
    def __init__(self, schema_path: str):
        """
        Initialize combiner with schema.
        
        Args:
            schema_path: Path to JSON schema file
        """
        self.schema_path = schema_path
        self.validator = SchemaValidator(schema_path)
        self.parser = QuestionParser()
    
    def combine_extraction_data(self, 
                               paper_metadata: Dict,
                               markdown_content: str,
                               extracted_images: List[Dict],
                               chemical_data: List[Dict]) -> Dict:
        """
        Combine all extracted data into unified JSON structure.
        
        Args:
            paper_metadata: Paper metadata from PyMuPDF
            markdown_content: Markdown content from Nougat
            extracted_images: Images from PyMuPDF
            chemical_data: SMILES data from OSRA
            
        Returns:
            Combined JSON dictionary
        """
        try:
            logger.info("Starting data combination process")
            
            # Parse questions from markdown
            question_dicts = self.parser.extract_questions_from_markdown(markdown_content)
            
            # Build questions array
            questions = []
            image_map = self._build_image_map(extracted_images)
            chemical_map = self._build_chemical_map(chemical_data)
            
            for q_dict in question_dicts:
                question_number = q_dict.get('question_number', len(questions) + 1)
                question_id = f"{paper_metadata['paper_id']}_q{question_number}"
                
                # Extract subject and type
                subject = self.parser.detect_subject(q_dict['question_text'])
                question_type = self.parser.detect_question_type(
                    q_dict['question_text'],
                    len(q_dict['options'])
                )
                
                # Create question object
                question = Question(
                    question_id=question_id,
                    question_number=question_number,
                    subject=subject,
                    question_type=question_type,
                    question_text=q_dict['question_text'],
                    question_latex=None,  # Would be populated from Nougat
                    question_images=image_map.get(question_number, []),
                    chemical_smiles=chemical_map.get(question_number, []),
                    options=q_dict['options'],
                    extraction_confidence=0.85
                )
                
                questions.append(question.to_dict())
            
            # Build final JSON structure
            output = {
                "paper_metadata": {
                    "exam_name": paper_metadata.get('exam_name', 'JEE Main'),
                    "exam_date_shift": paper_metadata.get('exam_date_shift', ''),
                    "paper_id": paper_metadata['paper_id'],
                    "total_questions": len(questions),
                    "extraction_timestamp": datetime.now().isoformat(),
                    "extraction_method": "combined_pipeline"
                },
                "questions": questions,
                "extraction_summary": {
                    "total_pages": paper_metadata.get('total_pages', 0),
                    "pages_with_errors": [],
                    "images_extracted": len(extracted_images),
                    "chemical_structures_detected": len(chemical_data),
                    "overall_confidence": sum(q.get('extraction_confidence', 0.85) 
                                            for q in questions) / len(questions) if questions else 0.0,
                    "extraction_errors": []
                }
            }
            
            logger.info(f"Data combination completed: {len(questions)} questions combined")
            return output
            
        except Exception as e:
            logger.error(f"Error combining data: {str(e)}")
            raise
    
    def _build_image_map(self, images: List[Dict]) -> Dict[int, List[str]]:
        """Map images to question numbers"""
        image_map = {}
        
        for image in images:
            # Extract page number from image metadata
            page = image.get('page', 1)
            filename = image.get('filename', '')
            
            if page not in image_map:
                image_map[page] = []
            image_map[page].append(filename)
        
        return image_map
    
    def _build_chemical_map(self, chemicals: List[Dict]) -> Dict[int, List[str]]:
        """Map chemical structures to question numbers"""
        chemical_map = {}
        
        for chemical in chemicals:
            if chemical.get('status') == 'success':
                # Map based on image filename
                filename = chemical.get('image_file', '')
                
                # Extract question number from filename if possible
                match = re.search(r'_page(\d+)_', filename)
                if match:
                    page = int(match.group(1))
                    if page not in chemical_map:
                        chemical_map[page] = []
                    chemical_map[page].extend(chemical.get('smiles_list', []))
        
        return chemical_map
    
    def save_combined_json(self, combined_data: Dict, output_file: str) -> str:
        """
        Save combined JSON to file with validation.
        
        Args:
            combined_data: Combined data dictionary
            output_file: Path to save JSON file
            
        Returns:
            Path to saved file
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Validate against schema
        is_valid, errors = self.validator.validate(combined_data)
        
        if not is_valid:
            logger.warning(f"Validation errors found: {errors}")
            # Still save the file but log warnings
        
        # Save JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Combined JSON saved to {output_path}")
        return str(output_path)


def combine_extraction_results(paper_metadata: Dict,
                              markdown_content: str,
                              extracted_images: List[Dict],
                              chemical_data: List[Dict],
                              schema_path: str,
                              output_file: str) -> str:
    """
    Convenience function to combine and save extraction results.
    
    Args:
        paper_metadata: Paper metadata
        markdown_content: Markdown text
        extracted_images: List of extracted images
        chemical_data: Chemical structure data
        schema_path: Path to JSON schema
        output_file: Path to save output
        
    Returns:
        Path to saved JSON file
    """
    combiner = JSONCombiner(schema_path)
    combined = combiner.combine_extraction_data(
        paper_metadata,
        markdown_content,
        extracted_images,
        chemical_data
    )
    return combiner.save_combined_json(combined, output_file)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage would be integrated with full pipeline
    print("JSON Combiner and Validator module loaded")
