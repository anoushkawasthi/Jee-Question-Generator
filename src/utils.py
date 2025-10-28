import re
import os
import pdfplumber
import logging
import groq
from dotenv import load_dotenv
import json

# Configure basic logging - Only show errors
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from all pages of a PDF, separating the main content
    from the answer key (last page).
    
    Args:
        pdf_path (str): The file path to the PDF.
        
    Returns:
        tuple: (all_question_text, answer_key_text)
            Returns (None, None) if an error occurs.
    """
    all_question_text = ""
    answer_key_text = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            if num_pages == 0:
                logging.warning(f"No pages found in PDF: {pdf_path}")
                return None, None
                
            # Loop through all pages *except* the last one
            for i in range(num_pages - 1):
                page = pdf.pages[i]
                text = page.extract_text()
                if text:
                    all_question_text += text + "\n"
            
            # Get text from the LAST page
            last_page = pdf.pages[-1]
            answer_key_text = last_page.extract_text()
            
            if not all_question_text:
                logging.warning(f"No question text extracted from {pdf_path}")
            if not answer_key_text:
                logging.warning(f"No answer key text extracted from {pdf_path}")
                
            return all_question_text, answer_key_text
            
    except Exception as e:
        logging.error(f"Error reading PDF {pdf_path}: {e}")
        return None, None

def parse_answer_key(answer_key_text):
    """
    Parses the raw text of an answer key page into a dictionary.
    
    Args:
        answer_key_text (str): The raw text from the answer key page.
        
    Returns:
        dict: A dictionary mapping question number (str) to answer (str).
    """
    if not answer_key_text:
        return {}
        
    # Pattern: (\d+). (any_answer_text)
    pattern = re.compile(r"(\d+)\.\s*\(([^\)]+)\)")
    matches = pattern.findall(answer_key_text)
    
    answer_key = {question_num: answer.strip() for question_num, answer in matches}
    
    return answer_key

def parse_question_blocks(all_question_text):
    """
    Parses the raw text of all question pages into a dictionary.
    
    Args:
        all_question_text (str): The combined raw text from all question pages.
        
    Returns:
        dict: A dictionary mapping question number (str) to question text (str).
    """
    if not all_question_text:
        return {}

    # Split the text at "Q[digits]." and keep the delimiter
    pattern = re.compile(r"(Q\d+\.)")
    split_text = pattern.split(all_question_text)
    
    questions_dict = {}
    
    # Start from index 1 to skip any header text before Q1
    # Loop 2 items at a time (e.g., 'Q1.', '...text for Q1...')
    for i in range(1, len(split_text), 2):
        try:
            # Re-combine the question number and its text
            q_num_full = split_text[i]
            q_text = split_text[i+1].strip()
            
            # Extract just the number (e.g., '1' from 'Q1.')
            q_num_only = re.search(r'(\d+)', q_num_full).group(1)
            
            # Re-add the question number to the text for completeness
            questions_dict[q_num_only] = f"{q_num_full} {q_text}"
            
        except (IndexError, AttributeError):
            # IndexError: handles if split_text has an odd number of items
            # AttributeError: handles if re.search fails to find a number
            logging.warning(f"Could not parse a question block near: {split_text[i]}")
            continue
            
    return questions_dict


# Load environment variables from .env file
load_dotenv()

def parse_question_and_options(question_text):
    """
    Parse question text to extract the prompt and options separately.
    
    Args:
        question_text (str): Raw question text with options
        
    Returns:
        dict: {
            "prompt": str,
            "options": list of {"id": str, "text": str} or None for non-MCQ
        }
    """
    try:
        # Remove "Q<number>." prefix
        question_text = re.sub(r'^Q\d+\.\s*', '', question_text.strip())
        
        # Pattern to match options like (1), (2), (3), (4) or A), B), C), D)
        option_pattern = r'\n\s*\((\d+|[A-D])\)\s*(.*?)(?=\n\s*\((?:\d+|[A-D])\)|$)'
        
        options_matches = list(re.finditer(option_pattern, question_text, re.DOTALL))
        
        if options_matches:
            # Extract prompt (text before first option)
            first_option_start = options_matches[0].start()
            prompt = question_text[:first_option_start].strip()
            
            # Extract options
            options = []
            for match in options_matches:
                option_id = match.group(1)
                option_text = match.group(2).strip()
                options.append({
                    "id": option_id,
                    "text": option_text
                })
            
            return {
                "prompt": prompt,
                "options": options
            }
        else:
            # No options found (Integer-type or other)
            return {
                "prompt": question_text.strip(),
                "options": None
            }
            
    except Exception as e:
        logging.error(f"Error parsing question options: {e}")
        return {
            "prompt": question_text.strip(),
            "options": None
        }


def get_question_metadata(question_text):
    """
    Calls the Groq Llama3 model to classify a question.
    
    Args:
        question_text (str): The full text of the question.
        
    Returns:
        dict: A dictionary with 'subject', 'topic', 'difficulty', and 'type', 
              or None if an error occurs.
    """
    try:
        # Check if API key is loaded
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            logging.error("GROQ_API_KEY not found. Make sure it's in your .env file.")
            return None

        client = groq.Groq(api_key=api_key)
        
        system_prompt = """
        You are an expert JEE-level physics, chemistry, and mathematics teacher.
        Your task is to analyze the provided JEE question and return metadata in a 
        strict JSON format.

        The JSON output must have these 4 keys:
        1. "subject": (e.g., "Physics", "Chemistry", "Mathematics")
        2. "topic": (e.g., "Kinematics", "Organic Chemistry: Aldehydes", "Calculus: Definite Integrals")
        3. "difficulty": ("Easy", "Medium", "Hard")
        4. "type": ("Single-Correct-MCQ", "Multi-Correct-MCQ", "Integer-Type", "Unknown")

        Respond ONLY with the raw JSON object, nothing else.
        """
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question_text}
            ],
            model="llama-3.1-8b-instant", # Updated: Fast and capable model (replaces decommissioned llama3-8b-8192)
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        
        response_json = chat_completion.choices[0].message.content
        
        # We need to parse the JSON string response
        metadata = json.loads(response_json)
        
        return metadata

    except Exception as e:
        logging.error(f"Error calling LLM for metadata: {e}")
        return None