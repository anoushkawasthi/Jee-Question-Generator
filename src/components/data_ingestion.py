import os
import sys
import json
import logging
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
# We use a relative import (..) to go "up one folder" from components to src
from ..utils import extract_text_from_pdf, parse_answer_key, parse_question_blocks
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


# Configure basic logging - Only show errors, not warnings
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

class DataIngestion:
    def __init__(self):
        # Define the root path for raw PDFs, relative to this file
        self.raw_data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw_pdfs')
        self.output_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'raw_questions.json')
    
    def save_parsed_data(self, data):
        """
        Save parsed data to JSON file.
        
        Args:
            data: Parsed questions data
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Parsed data saved to: {self.output_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving parsed data: {e}")
            return False
    
    def load_parsed_data(self):
        """
        Load previously parsed data from JSON file.
        
        Returns:
            Parsed data or None if file doesn't exist
        """
        if os.path.exists(self.output_path):
            try:
                with open(self.output_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"📂 Loaded {len(data)} papers from cached file: {self.output_path}")
                return data
            except Exception as e:
                logging.error(f"Error loading parsed data: {e}")
                return None
        return None
    
    def process_single_pdf(self, pdf_path, file):
        """
        Process a single PDF file (helper function for parallel processing).
        
        Args:
            pdf_path (str): Path to the PDF file
            file (str): Filename
            
        Returns:
            dict: Paper data with questions, or None if processing fails
        """
        try:
            # 1. Extract text using our util function
            question_text, answer_text = extract_text_from_pdf(pdf_path)
            
            if not question_text or not answer_text:
                return None
                
            # 2. Parse text using our util functions
            answer_key_dict = parse_answer_key(answer_text)
            questions_dict = parse_question_blocks(question_text)
            
            if not answer_key_dict or not questions_dict:
                return None

            # 3. Combine the data
            paper_data = {
                "source_file": file,
                "questions": []
            }
            
            for q_num, q_text in questions_dict.items():
                if q_num in answer_key_dict:
                    paper_data["questions"].append({
                        "question_number": q_num,
                        "question_text": q_text,
                        "correct_answer": answer_key_dict[q_num]
                    })
            
            return paper_data
            
        except Exception as e:
            logging.error(f"Error processing {file}: {e}")
            return None

    def initiate_data_ingestion(self, max_files=None, max_workers=4, use_cache=True):
        """
        Finds all PDFs, extracts data, and returns a structured list.
        Uses parallel processing for speed.
        
        Args:
            max_files (int, optional): Maximum number of files to process. 
                                    Use for testing with a subset of files.
            max_workers (int): Number of parallel workers (default: 4)
            use_cache (bool): If True, load from cached file if available
        """
        # Try to load from cache first
        if use_cache:
            cached_data = self.load_parsed_data()
            if cached_data:
                return cached_data
        
        all_papers_data = [] # This will hold data from all processed PDFs

        try:
            # First, collect all PDF files
            pdf_files = []
            for root, dirs, files in os.walk(self.raw_data_path):
                for file in files:
                    if file.endswith(".pdf"):
                        pdf_path = os.path.join(root, file)
                        pdf_files.append((pdf_path, file))
            
            # Limit files if max_files is specified
            if max_files:
                pdf_files = pdf_files[:max_files]
            
            print(f"📁 Found {len(pdf_files)} PDF file(s) to process")
            print(f"🚀 Using {max_workers} parallel workers for speed\n")
            
            # Process PDFs in parallel with progress bar
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self.process_single_pdf, pdf_path, file): file 
                    for pdf_path, file in pdf_files
                }
                
                # Process completed tasks with progress bar
                for future in tqdm(as_completed(future_to_file), total=len(pdf_files), 
                                desc="Processing PDFs", unit="file"):
                    paper_data = future.result()
                    if paper_data and paper_data["questions"]:
                        all_papers_data.append(paper_data)
            
            # Save the parsed data for future use
            self.save_parsed_data(all_papers_data)
            
            return all_papers_data

        except Exception as e:
            logging.error(f"Data ingestion failed: {e}")
            return None

# This block allows you to run this file directly for testing
if __name__ == "__main__":
    print("🔧 Starting Data Ingestion...\n")
    ingestion = DataIngestion()
    
    # Process ALL files with parallel processing (max_workers=4 for speed)
    all_data = ingestion.initiate_data_ingestion(max_files=None, max_workers=4)
    
    if all_data:
        print(f"\n✅ Data ingestion successful! Processed {len(all_data)} paper(s).")
        
        # --- Print a sample for verification ---
        print("\n" + "="*60)
        print("📋 VERIFICATION: FIRST 5 QUESTIONS FROM FIRST PAPER")
        print("="*60)
        try:
            first_paper_questions = all_data[0]["questions"]
            print(f"Source: {all_data[0]['source_file']}")
            print(f"Total questions in this paper: {len(first_paper_questions)}\n")
            
            for i in range(min(5, len(first_paper_questions))):
                print(f"Q{first_paper_questions[i]['question_number']}:")
                print(f"Text: {first_paper_questions[i]['question_text'][:150]}...") 
                print(f"Answer: {first_paper_questions[i]['correct_answer']}\n")
        except Exception as e:
            print(f"❌ Could not print verification: {e}")
            
    else:
        print("❌ Data ingestion failed.")