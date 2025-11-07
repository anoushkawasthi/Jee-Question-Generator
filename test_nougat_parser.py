"""
Test Suite for Nougat Question Parser
Comprehensive validation of parsing functionality
"""

import json
import tempfile
from pathlib import Path
import sys

from src.components.nougat_question_parser import NougatQuestionParser


class TestNougatParser:
    """Test cases for Nougat parser"""
    
    def __init__(self):
        self.parser = NougatQuestionParser()
        self.passed = 0
        self.failed = 0
    
    def assert_equal(self, actual, expected, msg=""):
        """Assert equality"""
        if actual == expected:
            self.passed += 1
            print(f"  ✅ {msg}")
        else:
            self.failed += 1
            print(f"  ❌ {msg}")
            print(f"     Expected: {expected}")
            print(f"     Got: {actual}")
    
    def assert_true(self, condition, msg=""):
        """Assert condition is true"""
        if condition:
            self.passed += 1
            print(f"  ✅ {msg}")
        else:
            self.failed += 1
            print(f"  ❌ {msg}")
    
    def test_single_question(self):
        """Test parsing single question"""
        print("\n📝 Test 1: Single Question")
        
        markdown = """Q1. What is the SI unit of force?

(1) Newton
(2) Dyne
(3) Erg
(4) Joule

Answer: 1"""
        
        questions = self.parser.parse_markdown_content(markdown, "test_paper")
        
        self.assert_equal(len(questions), 1, "Parsed exactly 1 question")
        self.assert_equal(questions[0].question_number, 1, "Question number is 1")
        self.assert_equal(len(questions[0].options), 4, "Has 4 options")
        self.assert_equal(questions[0].correct_answer, "1", "Correct answer is 1")
        self.assert_true("Newton" in questions[0].options[0]["latex"], "First option is Newton")
    
    def test_multiple_questions(self):
        """Test parsing multiple questions"""
        print("\n📝 Test 2: Multiple Questions")
        
        markdown = """Q1. First question
(1) A
(2) B
(3) C
(4) D
Answer: 1

Q2. Second question
(1) W
(2) X
(3) Y
(4) Z
Answer: 3

Q3. Third question
(1) One
(2) Two
(3) Three
(4) Four
Answer: 2"""
        
        questions = self.parser.parse_markdown_content(markdown)
        
        self.assert_equal(len(questions), 3, "Parsed 3 questions")
        self.assert_equal(questions[0].question_number, 1, "First question number is 1")
        self.assert_equal(questions[1].question_number, 2, "Second question number is 2")
        self.assert_equal(questions[2].question_number, 3, "Third question number is 3")
        self.assert_equal(questions[0].correct_answer, "1", "Q1 answer is 1")
        self.assert_equal(questions[1].correct_answer, "3", "Q2 answer is 3")
        self.assert_equal(questions[2].correct_answer, "2", "Q3 answer is 2")
    
    def test_latex_preservation(self):
        """Test LaTeX is preserved"""
        print("\n📝 Test 3: LaTeX Preservation")
        
        markdown = r"""Q1. Solve $x^2 + 2x + 1 = 0$

(1) $x = -1$
(2) $x = 1$
(3) $x = 0$
(4) $x = 2$

Answer: 1"""
        
        questions = self.parser.parse_markdown_content(markdown)
        
        self.assert_true("$" in questions[0].question_latex, "Question has LaTeX")
        self.assert_true("x^2" in questions[0].question_latex, "LaTeX equation preserved")
        self.assert_true("$" in questions[0].options[0]["latex"], "Option has LaTeX")
        self.assert_equal(questions[0].correct_answer, "1", "Correct answer extracted")
    
    def test_subject_detection(self):
        """Test automatic subject detection"""
        print("\n📝 Test 4: Subject Detection")
        
        physics_markdown = """Q1. A particle moves with velocity $v = 5$ m/s
(1) Correct
(2) Wrong
(3) Maybe
(4) Unknown
Answer: 1"""
        
        chemistry_markdown = """Q1. What is the oxidation state of carbon in $\\mathrm{CO_2}$?
(1) +2
(2) +4
(3) +6
(4) 0
Answer: 2"""
        
        physics_q = self.parser.parse_markdown_content(physics_markdown)[0]
        chemistry_q = self.parser.parse_markdown_content(chemistry_markdown)[0]
        
        self.assert_equal(physics_q.subject, "Physics", "Physics question detected")
        self.assert_equal(chemistry_q.subject, "Chemistry", "Chemistry question detected")
    
    def test_answer_extraction(self):
        """Test various answer formats"""
        print("\n📝 Test 5: Answer Extraction")
        
        # Format: Answer: 1
        md1 = """Q1. Question
(1) A
(2) B
(3) C
(4) D
Answer: 2"""
        
        # Format: Correct Answer: 3
        md2 = """Q2. Question
(1) A
(2) B
(3) C
(4) D
Correct Answer: 3"""
        
        # Format: Answer: (4)
        md3 = """Q3. Question
(1) A
(2) B
(3) C
(4) D
Answer: (4)"""
        
        q1 = self.parser.parse_markdown_content(md1)[0]
        q2 = self.parser.parse_markdown_content(md2)[0]
        q3 = self.parser.parse_markdown_content(md3)[0]
        
        self.assert_equal(q1.correct_answer, "2", "Format 'Answer: 2' works")
        self.assert_equal(q2.correct_answer, "3", "Format 'Correct Answer: 3' works")
        self.assert_equal(q3.correct_answer, "4", "Format 'Answer: (4)' works")
    
    def test_edge_case_no_options(self):
        """Test question with no options"""
        print("\n📝 Test 6: Edge Case - No Options")
        
        markdown = """Q1. This question has no options
Q2. This one has options
(1) A
(2) B
(3) C
(4) D
Answer: 1"""
        
        questions = self.parser.parse_markdown_content(markdown)
        
        # Q1 should be skipped, only Q2 should be parsed
        self.assert_equal(len(questions), 1, "Only valid question parsed")
        self.assert_equal(questions[0].question_number, 2, "Parsed Q2")
    
    def test_edge_case_incomplete_options(self):
        """Test question with less than 4 options"""
        print("\n📝 Test 7: Edge Case - Incomplete Options")
        
        markdown = """Q1. Only two options
(1) First
(2) Second
Answer: 1"""
        
        questions = self.parser.parse_markdown_content(markdown)
        
        # Should be skipped
        self.assert_equal(len(questions), 0, "Question with <4 options skipped")
    
    def test_multiline_question(self):
        """Test question spanning multiple lines"""
        print("\n📝 Test 8: Multiline Question")
        
        markdown = """Q1. Consider a block of mass m placed on an inclined plane at angle θ.
The coefficient of friction is μ.
Find the acceleration of the block.

(1) $g(\\sin\\theta - \\mu\\cos\\theta)$
(2) $g(\\cos\\theta - \\mu\\sin\\theta)$
(3) $g\\sin\\theta$
(4) $\\mu g\\cos\\theta$

Answer: 1"""
        
        questions = self.parser.parse_markdown_content(markdown)
        
        self.assert_equal(len(questions), 1, "Multiline question parsed")
        self.assert_true("block" in questions[0].question_latex.lower(), "Full text included")
        self.assert_true("friction" in questions[0].question_latex.lower(), "All paragraphs included")
    
    def test_json_output_format(self):
        """Test JSON output format"""
        print("\n📝 Test 9: JSON Output Format")
        
        markdown = """Q1. Test question
(1) Option A
(2) Option B
(3) Option C
(4) Option D
Answer: 1"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            self.parser.parse_and_save_json(
                markdown,
                temp_file,
                paper_id="Test Paper"
            )
            
            with open(temp_file, 'r') as f:
                data = json.load(f)
            
            self.assert_true("paper_id" in data, "JSON has paper_id")
            self.assert_true("total_questions" in data, "JSON has total_questions")
            self.assert_true("parsing_method" in data, "JSON has parsing_method")
            self.assert_true("questions" in data, "JSON has questions array")
            self.assert_equal(len(data["questions"]), 1, "Questions array has 1 question")
        finally:
            Path(temp_file).unlink()
    
    def test_complex_latex(self):
        """Test complex LaTeX expressions"""
        print("\n📝 Test 10: Complex LaTeX")
        
        markdown = r"""Q1. The sum of the series $\sum_{n=1}^{\infty} \frac{1}{n^2}$ is:

(1) $\frac{\pi^2}{6}$
(2) $\frac{\pi^2}{4}$
(3) $\pi^2$
(4) $\frac{\pi}{6}$

Answer: 1"""
        
        questions = self.parser.parse_markdown_content(markdown)
        
        self.assert_true(r"\sum" in questions[0].question_latex, "Complex LaTeX preserved")
        self.assert_true(r"\frac" in questions[0].options[0]["latex"], "Fraction LaTeX preserved")
        self.assert_true(r"\pi" in questions[0].options[0]["latex"], "Greek letters preserved")
    
    def test_question_id_generation(self):
        """Test question ID generation"""
        print("\n📝 Test 11: Question ID Generation")
        
        markdown = """Q1. First
(1) A
(2) B
(3) C
(4) D
Answer: 1

Q2. Second
(1) A
(2) B
(3) C
(4) D
Answer: 1"""
        
        questions = self.parser.parse_markdown_content(
            markdown,
            paper_id="JEE Main 2024 01 Feb Shift 1"
        )
        
        self.assert_true("_q1" in questions[0].question_id, "Q1 has correct ID format")
        self.assert_true("_q2" in questions[1].question_id, "Q2 has correct ID format")
        self.assert_true("Main" in questions[0].question_id, "Paper info in ID")
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*70)
        print("NOUGAT PARSER TEST SUITE")
        print("="*70)
        
        try:
            self.test_single_question()
            self.test_multiple_questions()
            self.test_latex_preservation()
            self.test_subject_detection()
            self.test_answer_extraction()
            self.test_edge_case_no_options()
            self.test_edge_case_incomplete_options()
            self.test_multiline_question()
            self.test_json_output_format()
            self.test_complex_latex()
            self.test_question_id_generation()
        except Exception as e:
            print(f"\n❌ Test suite error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Print summary
        print("\n" + "="*70)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📊 Total: {self.passed + self.failed}")
        print("="*70)
        
        if self.failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
            return 0
        else:
            print(f"\n⚠️  {self.failed} test(s) failed")
            return 1


if __name__ == "__main__":
    tester = TestNougatParser()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
