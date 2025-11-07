"""
LLM Annotation Pipeline - Phase 2
Enriches questions with difficulty, concepts, and solutions using Claude/GPT
"""

import json
import argparse
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Optional, List
import random

logger = logging.getLogger(__name__)


class LLMAnnotationPipeline:
    """
    Annotates questions using LLM API
    Adds difficulty, concepts, and computable solution metadata
    """
    
    def __init__(self, json_file: str, output_file: Optional[str] = None, 
                 api_provider: str = "anthropic"):
        """
        Initialize annotation pipeline
        
        Args:
            json_file: Path to consolidated JSON
            output_file: Path to save annotated JSON (default: same with _annotated suffix)
            api_provider: "anthropic" (Claude) or "openai" (GPT)
        """
        self.json_file = Path(json_file)
        if not self.json_file.exists():
            raise FileNotFoundError(f"JSON file not found: {json_file}")
        
        # Output file
        if output_file:
            self.output_file = Path(output_file)
        else:
            stem = self.json_file.stem
            suffix = self.json_file.suffix
            self.output_file = self.json_file.parent / f"{stem}_annotated{suffix}"
        
        self.api_provider = api_provider
        self.questions_processed = 0
        self.questions_failed = 0
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def load_questions(self) -> Dict:
        """Load consolidated JSON"""
        with open(self.json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def build_annotation_prompt(self, question: Dict) -> str:
        """
        Build prompt for LLM annotation
        
        Args:
            question: Single question from JSON
            
        Returns:
            Prompt string for LLM
        """
        question_text = question.get('question_latex', '')
        options_text = '\n'.join([
            f"{opt['id']}. {opt.get('latex', opt.get('text', ''))}"
            for opt in question.get('options', [])
        ])
        
        prompt = f"""Analyze this JEE Main question and provide structured metadata.

QUESTION TEXT:
{question_text}

OPTIONS:
{options_text}

CORRECT ANSWER: {question.get('correct_answer', 'N/A')}

Please respond with ONLY valid JSON (no markdown formatting, no code blocks):
{{
  "difficulty": "<Easy|Medium|Hard>",
  "concepts": ["concept1", "concept2", "concept3"],
  "solution_approach": "<Brief description of how to solve>",
  "key_insight": "<Key insight or trick needed>",
  "computable_solution": "<True if can be solved with direct computation, False if requires conceptual reasoning>",
  "estimated_time_seconds": <30-300>
}}

Ensure all fields are present and valid. Return ONLY the JSON object."""
        
        return prompt
    
    def annotate_with_claude(self, question: Dict) -> Optional[Dict]:
        """
        Annotate question using Claude API
        
        Args:
            question: Question to annotate
            
        Returns:
            Annotation dict or None if failed
        """
        try:
            import anthropic
        except ImportError:
            logger.error("anthropic package not installed. Run: pip install anthropic")
            return None
        
        try:
            client = anthropic.Anthropic()
            prompt = self.build_annotation_prompt(question)
            
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse response
            response_text = message.content[0].text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()
            
            annotation = json.loads(response_text)
            return annotation
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}")
            return None
        except anthropic.APIError as e:
            logger.warning(f"Claude API error: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error with Claude: {str(e)}")
            return None
    
    def annotate_with_openai(self, question: Dict) -> Optional[Dict]:
        """
        Annotate question using OpenAI API
        
        Args:
            question: Question to annotate
            
        Returns:
            Annotation dict or None if failed
        """
        try:
            from openai import OpenAI
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            return None
        
        try:
            client = OpenAI()
            prompt = self.build_annotation_prompt(question)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()
            
            annotation = json.loads(response_text)
            return annotation
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"OpenAI API error: {str(e)}")
            return None
    
    def annotate_question(self, question: Dict) -> Dict:
        """
        Annotate single question using selected API
        
        Args:
            question: Question to annotate
            
        Returns:
            Question with added ml_annotations field
        """
        if self.api_provider == "anthropic":
            annotation = self.annotate_with_claude(question)
        elif self.api_provider == "openai":
            annotation = self.annotate_with_openai(question)
        else:
            raise ValueError(f"Unknown API provider: {self.api_provider}")
        
        if annotation:
            question['ml_annotations'] = annotation
            self.questions_processed += 1
        else:
            question['ml_annotations'] = {
                "difficulty": None,
                "concepts": [],
                "solution_approach": None,
                "key_insight": None,
                "computable_solution": None,
                "estimated_time_seconds": None
            }
            self.questions_failed += 1
        
        return question
    
    def run_annotation(self, sample_size: Optional[int] = None, 
                      skip_existing: bool = True) -> str:
        """
        Run annotation pipeline on all questions
        
        Args:
            sample_size: If set, only annotate this many random questions (for testing)
            skip_existing: Skip questions that already have ml_annotations
            
        Returns:
            Path to output file
        """
        print(f"\n{'='*70}")
        print(f"LLM ANNOTATION PIPELINE - {self.api_provider.upper()}")
        print(f"{'='*70}")
        
        # Load data
        print(f"\n📂 Loading: {self.json_file}")
        data = self.load_questions()
        questions = data['questions']
        
        print(f"📊 Total questions: {len(questions)}")
        
        # Determine which questions to process
        if skip_existing:
            to_process = [
                q for q in questions 
                if not q.get('ml_annotations') or not q['ml_annotations'].get('difficulty')
            ]
            print(f"⏭️  Skipping {len(questions) - len(to_process)} already annotated")
        else:
            to_process = questions
        
        # Sample if requested
        if sample_size and sample_size < len(to_process):
            to_process = random.sample(to_process, sample_size)
            print(f"🎲 Processing sample of {sample_size} questions")
        
        print(f"🔄 Processing {len(to_process)} questions...\n")
        
        # Process each question
        start_time = time.time()
        for i, question in enumerate(to_process):
            try:
                self.annotate_question(question)
                
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    remaining = (len(to_process) - i - 1) / rate
                    
                    print(f"  [{i + 1:3d}/{len(to_process)}] "
                          f"✅ {self.questions_processed} | "
                          f"❌ {self.questions_failed} | "
                          f"ETA: {remaining:.0f}s")
                
                # Rate limiting (be nice to API)
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print(f"\n⚠️  Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error annotating question: {str(e)}")
                self.questions_failed += 1
        
        elapsed = time.time() - start_time
        
        # Save results
        print(f"\n💾 Saving to: {self.output_file}")
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"✅ ANNOTATION COMPLETE")
        print(f"{'='*70}")
        print(f"✅ Successful: {self.questions_processed}")
        print(f"❌ Failed: {self.questions_failed}")
        print(f"⏱️  Time elapsed: {elapsed:.1f}s")
        if self.questions_processed > 0:
            print(f"⚡ Rate: {self.questions_processed / elapsed:.1f} q/s")
        print(f"\n📁 Output: {self.output_file}")
        
        return str(self.output_file)


def main():
    parser = argparse.ArgumentParser(
        description="LLM Annotation Pipeline - Add ML metadata to questions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Annotate all questions using Claude
  python run_llm_annotation.py --json-file data/processed/nougat_parsed/all_questions_consolidated.json --provider anthropic
  
  # Test with small sample (10 questions)
  python run_llm_annotation.py --json-file questions.json --provider openai --sample 10
  
  # Custom output file
  python run_llm_annotation.py --json-file questions.json --output my_annotated_questions.json
        """
    )
    
    parser.add_argument(
        "--json-file",
        type=str,
        default="data/processed/nougat_parsed/all_questions_consolidated.json",
        help="Path to consolidated JSON file"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: input_annotated.json)"
    )
    
    parser.add_argument(
        "--provider",
        type=str,
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider to use (default: anthropic)"
    )
    
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Process only N random questions (useful for testing)"
    )
    
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip questions that already have annotations"
    )
    
    args = parser.parse_args()
    
    # Validate file
    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"❌ Error: File not found: {args.json_file}")
        print(f"\n   First run: python run_nougat_integration.py --consolidate")
        return 1
    
    # Initialize and run
    try:
        pipeline = LLMAnnotationPipeline(
            json_file=args.json_file,
            output_file=args.output,
            api_provider=args.provider
        )
        
        pipeline.run_annotation(
            sample_size=args.sample,
            skip_existing=args.skip_existing
        )
        
        return 0
        
    except FileNotFoundError as e:
        print(f"❌ Error: {str(e)}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
