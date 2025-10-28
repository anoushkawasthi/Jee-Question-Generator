import os
import sys
import json
import logging
import time
from tqdm import tqdm

# Update sys.path to ensure correct module imports from the root
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Relative imports from other parts of our 'src' package
from src.components.data_ingestion import DataIngestion
from src.utils import get_question_metadata, parse_question_and_options

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataTransformation:
    def __init__(self):
        self.output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed')
        self.output_filepath = os.path.join(self.output_dir, 'questions_with_metadata.json')
        logging.info(f"Processed data will be saved to: {self.output_filepath}")

    def initiate_data_transformation(self, max_papers=None):
        """
        Fetches parsed data, enriches it with LLM metadata paper-by-paper, 
        and saves to JSON after each paper.
        
        Args:
            max_papers (int, optional): Limit number of papers to process (for testing)
        """
        try:
            # 1. Get the parsed data from DataIngestion (will use cache if available)
            logging.info("Loading parsed data...")
            ingestion = DataIngestion()
            all_papers_data = ingestion.initiate_data_ingestion(use_cache=True)
            
            if not all_papers_data:
                logging.error("Data ingestion returned no data. Aborting transformation.")
                return

            # Limit papers if max_papers is specified (for testing)
            if max_papers:
                all_papers_data = all_papers_data[:max_papers]
                print(f"🧪 TESTING MODE: Processing only {max_papers} paper(s)")
            
            total_papers = len(all_papers_data)
            print(f"\n📚 Total papers to process: {total_papers}")
            print(f"💾 Progress will be saved after each paper\n")
            
            # Load existing processed questions if file exists (for resume capability)
            final_enriched_questions = []
            processed_files = set()
            
            if os.path.exists(self.output_filepath):
                try:
                    with open(self.output_filepath, 'r', encoding='utf-8') as f:
                        final_enriched_questions = json.load(f)
                    print(f"📥 Loaded {len(final_enriched_questions)} previously processed questions\n")
                    
                    # Get list of already processed source files
                    for q in final_enriched_questions:
                        if 'metadata' in q and 'source_file' in q['metadata']:
                            processed_files.add(q['metadata']['source_file'])
                except:
                    final_enriched_questions = []
                    processed_files = set()
            
            # Process papers that haven't been processed yet
            papers_to_process = [p for p in all_papers_data if p['source_file'] not in processed_files]
            
            if not papers_to_process:
                print("✅ All papers already processed!")
                return
            
            print(f"🔄 Papers remaining to process: {len(papers_to_process)}\n")
            
            for paper_idx, paper in enumerate(papers_to_process, 1):
                source_file = paper['source_file']
                questions = paper['questions']
                
                print(f"\n{'='*70}")
                print(f"� Processing Paper {paper_idx}/{len(papers_to_process)}")
                print(f"📁 File: {source_file}")
                print(f"❓ Questions in this paper: {len(questions)}\n")
                print(f"{'='*70}\n")
                
                paper_enriched_questions = []
                
                # Process each question in this paper with progress bar
                for question in tqdm(questions, desc=f"Paper {paper_idx}", unit="q"):
                    try:
                        # Add source file info
                        question['source_file'] = source_file
                        
                        # Parse question to extract prompt and options
                        parsed = parse_question_and_options(question['question_text'])
                        
                        # Get metadata from LLM
                        metadata = get_question_metadata(question['question_text'])
                        
                        if metadata:
                            # Build the new restructured format
                            restructured_question = {
                                "question_number": int(question['question_number']),
                                "question_prompt": parsed['prompt'],
                                "options": parsed['options'],  # Will be None for Integer-type questions
                                "answer_details": {
                                    "correct_option_id": question['correct_answer']
                                },
                                "metadata": {
                                    "source_file": source_file,
                                    "subject": metadata.get('subject', 'Unknown'),
                                    "topic": metadata.get('topic', 'Unknown'),
                                    "difficulty": metadata.get('difficulty', 'Medium'),
                                    "type": metadata.get('type', 'Unknown')
                                }
                            }
                            
                            # Add correct_option_text if options exist
                            if parsed['options']:
                                correct_opt = next(
                                    (opt for opt in parsed['options'] if opt['id'] == question['correct_answer']),
                                    None
                                )
                                if correct_opt:
                                    restructured_question['answer_details']['correct_option_text'] = correct_opt['text']
                            
                            paper_enriched_questions.append(restructured_question)
                        else:
                            logging.warning(f"Failed to get metadata for Q{question['question_number']}")
                        
                        # IMPORTANT: Add a small delay to avoid hitting API rate limits
                        time.sleep(0.5) # 0.5 seconds between requests
                        
                    except Exception as e:
                        logging.error(f"Error processing question {question.get('question_number')}: {e}")
                        time.sleep(1) # Longer pause if an error occurs
                
                # Add this paper's questions to the overall list
                final_enriched_questions.extend(paper_enriched_questions)
                
                # 3. Save progress after each paper
                print(f"\n💾 Saving progress... ({len(final_enriched_questions)} total questions)")
                os.makedirs(self.output_dir, exist_ok=True)
                
                with open(self.output_filepath, 'w', encoding='utf-8') as f:
                    json.dump(final_enriched_questions, f, indent=4, ensure_ascii=False)
                
                print(f"✅ Paper {paper_idx}/{len(papers_to_process)} complete!\n")
            
            # 4. Final summary
            print(f"\n{'='*70}")
            print(f"🎉 ALL PAPERS PROCESSED!")
            print(f"📊 Total enriched questions: {len(final_enriched_questions)}")
            print(f"💾 Saved to: {self.output_filepath}")
            print(f"{'='*70}\n")

        except Exception as e:
            logging.error(f"Data transformation failed: {e}")
            raise

# This block allows you to run this file directly for testing
if __name__ == "__main__":
    print("🔧 Starting Data Transformation...\n")
    transformation = DataTransformation()
    
    # TEST with 1 paper first to verify new structure
    # Set max_papers=None to process all papers
    transformation.initiate_data_transformation(max_papers=None)
    
    print("\n✅ Data Transformation complete!")