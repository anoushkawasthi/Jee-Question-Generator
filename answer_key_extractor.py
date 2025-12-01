"""
Answer Key Extractor Module

Extracts answer keys from PDF's dedicated answer key page (typically last page).
JEE PDFs have answer keys in a structured format on the last page, separate from
the question text.

Usage:
    extractor = AnswerKeyExtractor()
    answers = extractor.extract_from_text_blocks(text_blocks)
    # Returns: {1: '2', 2: '3', 3: '1', ...}
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AnswerKeyExtractor:
    """
    Extracts answer keys from structured text blocks.
    
    JEE answer key format (from last page):
    Q1. (2)  -> Question 1, Answer 2
    Q2. (3)  -> Question 2, Answer 3
    Q3. (1)  -> Question 3, Answer 1
    
    or alternately:
    1. (2)
    2. (3)
    ...
    
    or in continuous text:
    Answer Keys: (2) (3) (1) (2) ...
    """
    
    # Pattern 1: "Q1. (2)" or "Q1 (2)" - captures any number in parens
    PATTERN_Q_NUMBER = r'Q\s*(\d+)\s*[.)\-:]*\s*\((\d+)\)'
    
    # Pattern 2: "1. (2)" - question number followed by answer in parens
    PATTERN_NUM_ONLY = r'(?:^|\n)\s*(\d+)\s*[.)\-:]*\s*\((\d+)\)'
    
    # Pattern 3: "1. 2" or "1. (2)" - answer after question number (MCQ only)
    PATTERN_NUM_ANSWER = r'(?:^|\n)\s*(\d+)\s*[.)\-:]*\s*([1-4])\s*(?:\)|,|$)'
    
    # Pattern 4: Continuous answer sequence at end - captures any number
    PATTERN_ANSWER_SEQUENCE = r'\((\d+)\)'
    
    def __init__(self):
        """Initialize patterns"""
        self.q_number_pattern = re.compile(self.PATTERN_Q_NUMBER, re.IGNORECASE | re.MULTILINE)
        self.num_only_pattern = re.compile(self.PATTERN_NUM_ONLY, re.MULTILINE)
        self.num_answer_pattern = re.compile(self.PATTERN_NUM_ANSWER, re.MULTILINE)
        self.answer_sequence_pattern = re.compile(self.PATTERN_ANSWER_SEQUENCE)
    
    def extract_from_text_blocks(self, text_blocks: List[Dict]) -> Dict[int, str]:
        """
        Extract answer keys from text blocks extracted by PyMuPDF.
        
        Args:
            text_blocks: List of text blocks from 01_text_images_extraction.json
                        Each block: {'page': int, 'text': {nested dict with 'text' key}}
        
        Returns:
            Dictionary mapping question_number (int) -> answer (str)
            Example: {1: '2', 2: '3', 3: '1', ...}
        """
        # Combine all text from all pages into continuous string
        combined_text = self._combine_text_blocks(text_blocks)
        
        if not combined_text.strip():
            logger.warning("No text found in text blocks for answer key extraction")
            return {}
        
        # Try different extraction patterns
        answers = self._try_extract_q_pattern(combined_text)
        if answers:
            logger.info(f"Extracted {len(answers)} answers using Q-number pattern")
            return answers
        
        answers = self._try_extract_num_pattern(combined_text)
        if answers:
            logger.info(f"Extracted {len(answers)} answers using number pattern")
            return answers
        
        answers = self._try_extract_sequence(combined_text)
        if answers:
            logger.info(f"Extracted {len(answers)} answers using sequence pattern")
            return answers
        
        logger.warning("Could not extract answer keys using any pattern")
        return {}
    
    def _combine_text_blocks(self, text_blocks: List[Dict]) -> str:
        """
        Combine all text blocks into a single string.
        
        Args:
            text_blocks: List of text blocks (supports multiple formats)
        
        Returns:
            Combined text string
        """
        combined = []
        
        for block in text_blocks:
            text_obj = block.get('text')
            
            if isinstance(text_obj, dict):
                # Structure: {'text': '...', 'coordinates': {...}, 'block_type': '...'}
                text_content = text_obj.get('text', '')
            elif isinstance(text_obj, str):
                # Simple string format (from PyMuPDF direct extraction)
                text_content = text_obj
            else:
                continue
            
            if text_content:
                combined.append(text_content)
        
        return '\n'.join(combined)
    
    def _try_extract_q_pattern(self, text: str) -> Dict[int, str]:
        """
        Try extracting using Q-number pattern: Q1. (2), Q2. (3), etc.
        
        Args:
            text: Combined text from all blocks
        
        Returns:
            Dictionary of answers or empty dict if no matches
        """
        matches = self.q_number_pattern.findall(text)
        
        if not matches:
            return {}
        
        answers = {}
        for q_num_str, answer in matches:
            try:
                q_num = int(q_num_str)
                answers[q_num] = answer.strip()
            except (ValueError, AttributeError):
                continue
        
        return answers
    
    def _try_extract_num_pattern(self, text: str) -> Dict[int, str]:
        """
        Try extracting using number pattern: 1. (2), 2. (3), etc.
        
        Args:
            text: Combined text from all blocks
        
        Returns:
            Dictionary of answers or empty dict if no matches
        """
        matches = self.num_only_pattern.findall(text)
        
        if not matches:
            return {}
        
        answers = {}
        for q_num_str, answer in matches:
            try:
                q_num = int(q_num_str)
                # Skip Q0 (often from parsing artifacts)
                if q_num == 0:
                    continue
                answers[q_num] = answer.strip()
            except (ValueError, AttributeError):
                continue
        
        return answers
    
    def _try_extract_sequence(self, text: str) -> Dict[int, str]:
        """
        Try extracting as a continuous sequence: (1) (2) (3) (1) ...
        This assumes answers appear in order and we can number them 1, 2, 3, ...
        
        Args:
            text: Combined text from all blocks
        
        Returns:
            Dictionary of answers or empty dict if no matches
        """
        matches = self.answer_sequence_pattern.findall(text)
        
        if len(matches) < 10:  # Need at least 10 answers to be confident
            return {}
        
        answers = {}
        for idx, answer in enumerate(matches, 1):
            answers[idx] = answer.strip()
        
        return answers
    
    def extract_from_json_file(self, json_file_path: str) -> Dict[int, str]:
        """
        Extract answer keys from 01_text_images_extraction.json file.
        
        Args:
            json_file_path: Path to 01_text_images_extraction.json
        
        Returns:
            Dictionary mapping question_number -> answer
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            text_blocks = data.get('text_blocks', [])
            return self.extract_from_text_blocks(text_blocks)
        
        except Exception as e:
            logger.error(f"Error reading JSON file {json_file_path}: {e}")
            return {}
    
    def validate_answers(self, answers: Dict[int, str], expected_count: int = None) -> bool:
        """
        Validate extracted answers.
        
        Args:
            answers: Dictionary of extracted answers
            expected_count: Expected number of answers (optional for validation)
        
        Returns:
            True if answers look valid, False otherwise
        """
        if not answers:
            logger.warning("No answers provided for validation")
            return False
        
        # Check all answers are valid numbers
        for q_num, answer in answers.items():
            try:
                int(answer)  # Just verify it's a valid number
            except ValueError:
                logger.warning(f"Invalid answer for Q{q_num}: '{answer}'")
                return False
            
            if not isinstance(q_num, int) or q_num < 1:
                logger.warning(f"Invalid question number: {q_num}, skipping validation for this entry")
                continue
        
        # Check for expected count if provided
        if expected_count and len(answers) != expected_count:
            logger.warning(f"Expected {expected_count} answers, got {len(answers)}")
            # Don't return False here - might be partial extraction
        
        logger.info(f"Validation passed: {len(answers)} answers")
        return True


def demo_usage():
    """
    Demo usage of AnswerKeyExtractor
    """
    extractor = AnswerKeyExtractor()
    
    # Example 1: Extract from first paper
    json_file = "extraction_output/JEE Main 2024 (01 Feb Shift 1) Previous Year Paper with Answer Keys - MathonGo/01_text_images_extraction.json"
    
    print(f"Extracting from: {json_file}")
    answers = extractor.extract_from_json_file(json_file)
    
    print(f"\nExtracted {len(answers)} answer keys:")
    for q_num in sorted(answers.keys())[:10]:
        print(f"  Q{q_num}: {answers[q_num]}")
    
    # Validate
    is_valid = extractor.validate_answers(answers)
    print(f"\nValidation: {'PASS' if is_valid else 'FAIL'}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    demo_usage()
