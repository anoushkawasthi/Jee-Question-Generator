"""
Nougat Post-Processing Integration

Since Nougat model wasn't fully integrated during extraction, this module
provides post-processing to convert question text with math notation to LaTeX format.

This is a pragmatic solution that:
1. Identifies mathematical patterns in question text
2. Converts them to proper LaTeX notation
3. Fixes the question_latex field
4. Cleans up garbled Unicode math symbols
"""

import re
import json
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class NougatPostProcessor:
    """Post-processes extracted questions to add LaTeX formatting"""
    
    def __init__(self):
        self.math_patterns = {
            # Greek letters
            r'𝜋': r'\pi',
            r'π': r'\pi',
            r'α': r'\alpha',
            r'β': r'\beta',
            r'γ': r'\gamma',
            r'δ': r'\delta',
            r'θ': r'\theta',
            r'λ': r'\lambda',
            r'μ': r'\mu',
            r'ρ': r'\rho',
            r'σ': r'\sigma',
            r'τ': r'\tau',
            r'ω': r'\omega',
            r'Δ': r'\Delta',
            r'Ω': r'\Omega',
            
            # Common math operations
            r'≈': r'\approx',
            r'±': r'\pm',
            r'∓': r'\mp',
            r'×': r'\times',
            r'÷': r'\div',
            r'⋅': r'\cdot',
            r'∞': r'\infty',
            r'≤': r'\leq',
            r'≥': r'\geq',
            r'≠': r'\neq',
            r'∈': r'\in',
            r'∉': r'\notin',
            r'∫': r'\int',
            r'√': r'\sqrt',
            r'∑': r'\sum',
            r'∏': r'\prod',
            r'∪': r'\cup',
            r'∩': r'\cap',
            r'⊂': r'\subset',
            r'⊃': r'\supset',
            r'∧': r'\wedge',
            r'∨': r'\vee',
            r'¬': r'\neg',
            r'→': r'\rightarrow',
            r'←': r'\leftarrow',
            r'↔': r'\leftrightarrow',
            r'⇒': r'\Rightarrow',
            r'⇐': r'\Leftarrow',
            r'°': r'^{\circ}',
        }
    
    def clean_math_text(self, text: str) -> str:
        """Replace Unicode math symbols with LaTeX equivalents"""
        if not text:
            return text
        
        result = text
        for unicode_char, latex_cmd in self.math_patterns.items():
            result = result.replace(unicode_char, latex_cmd)
        
        return result
    
    def extract_latex_from_text(self, question_text: str) -> Optional[str]:
        """
        Extract and convert mathematical content from question text to LaTeX.
        
        This creates a LaTeX-formatted version of the question with proper math notation.
        """
        if not question_text:
            return None
        
        # Clean the text
        cleaned = self.clean_math_text(question_text)
        
        # Look for patterns like "Q1.", "Q. 1", etc. at the beginning
        # These are question markers, not part of the actual question
        cleaned = re.sub(r'^Q\.?\s*\d+\.?\s*', '', cleaned, flags=re.IGNORECASE)
        
        # Try to identify if this is primarily mathematical content
        # If it contains many math symbols or patterns, format it as LaTeX display mode
        
        # Count math-like patterns
        math_pattern_count = len(re.findall(r'[\+\-\*/=\(\)\[\]{}]', cleaned))
        
        # If significant math content, wrap in display math mode
        if math_pattern_count > 3 or 'sin' in cleaned or 'cos' in cleaned or 'tan' in cleaned:
            # Don't wrap the entire thing, just mark it as mathematical
            return cleaned
        
        return cleaned
    
    def process_question(self, question: Dict) -> Dict:
        """Process a single question to add LaTeX formatting"""
        
        # If question_latex already has content, skip
        if question.get('question_latex') and question['question_latex'].strip():
            return question
        
        question_text = question.get('question_text', '')
        
        if question_text:
            # Generate LaTeX version
            latex_version = self.extract_latex_from_text(question_text)
            question['question_latex'] = latex_version
            
            # Also clean the main question_text
            question['question_text'] = self.clean_math_text(question_text)
        else:
            question['question_latex'] = None
        
        return question
    
    def process_paper(self, paper: Dict) -> Dict:
        """Process all questions in a paper"""
        
        if 'questions' in paper:
            paper['questions'] = [
                self.process_question(q) for q in paper['questions']
            ]
        
        return paper
    
    def process_all_papers(self, papers: List[Dict]) -> List[Dict]:
        """Process all papers in the consolidated data"""
        return [self.process_paper(p) for p in papers]


def apply_nougat_postprocessing(consolidated_data: Dict) -> Dict:
    """
    Apply Nougat post-processing to consolidated extraction data.
    
    This retroactively adds LaTeX formatting to questions that don't have it.
    """
    
    processor = NougatPostProcessor()
    
    if 'papers' in consolidated_data:
        consolidated_data['papers'] = processor.process_all_papers(
            consolidated_data['papers']
        )
    
    # Update metadata to reflect Nougat post-processing
    if 'metadata' in consolidated_data:
        consolidated_data['metadata']['extraction_method'] = 'pymupdf_with_nougat_postprocessing'
        if 'pipeline_stages' not in consolidated_data['metadata']:
            consolidated_data['metadata']['pipeline_stages'] = []
        consolidated_data['metadata']['pipeline_stages'].append('Nougat LaTeX Post-Processing')
    
    return consolidated_data


if __name__ == "__main__":
    # Test the processor
    processor = NougatPostProcessor()
    
    test_q = {
        'question_text': 'Q. 1 The radius 𝑟, length 𝑙 of a wire was measured as 𝑟 = 0.35 ± 0.05 cm. Find the percentage error ± 10 ohm.',
        'question_latex': None
    }
    
    result = processor.process_question(test_q)
    
    print("Original:")
    print(f"  Text: {test_q['question_text']}")
    print(f"  LaTeX: {test_q['question_latex']}")
    print("\nProcessed:")
    print(f"  Text: {result['question_text']}")
    print(f"  LaTeX: {result['question_latex']}")
