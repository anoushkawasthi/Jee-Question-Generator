import os
import sys
import pickle
import faiss
import numpy as np
import logging
from sentence_transformers import SentenceTransformer
import time # For potential delays
import json
from groq import Groq
from dotenv import load_dotenv

# Update sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PredictPipeline:
    def __init__(self):
        # Load artifacts
        self.artifacts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'artifacts')
        self.index_path = os.path.join(self.artifacts_dir, 'faiss_index.index')
        self.mapping_path = os.path.join(self.artifacts_dir, 'index_to_doc_mapping.pkl')
        self.model_name = 'all-MiniLM-L6-v2' # Must match the one used for indexing

        try:
            logging.info("Loading artifacts...")
            self.index = faiss.read_index(self.index_path)
            with open(self.mapping_path, 'rb') as f:
                self.index_to_doc = pickle.load(f)
            
            logging.info(f"Loading sentence transformer model: {self.model_name}...")
            self.embedding_model = SentenceTransformer(self.model_name)
            
            # Initialize LLM client (Groq)
            logging.info("Initializing Groq LLM client...")
            self.llm_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
            self.llm_model = "llama-3.1-8b-instant"  # Same model used for metadata extraction

            logging.info("PredictPipeline initialized successfully.")

        except FileNotFoundError:
            logging.error("Artifacts (index or mapping) not found. Run vector_store_populator.py first.")
            raise
        except Exception as e:
            logging.error(f"Error initializing PredictPipeline: {e}")
            raise

    def retrieve_relevant_questions(self, query_text, k=5):
        """
        Embeds the query and searches the FAISS index for the top k similar questions.
        
        Args:
            query_text (str): The text to search for (e.g., "Hard Physics Kinematics").
            k (int): Number of similar questions to retrieve.
            
        Returns:
            list: A list of dictionaries, each containing info about a retrieved question.
        """
        logging.info(f"Retrieving top {k} questions for query: '{query_text}'")
        try:
            # 1. Embed the query
            query_embedding = self.embedding_model.encode([query_text], show_progress_bar=False)
            query_embedding = np.array(query_embedding).astype('float32')

            # 2. Search the FAISS index
            # D = distances, I = indices (positions in the index)
            distances, indices = self.index.search(query_embedding, k)

            # 3. Get the original question info using the mapping
            results = []
            for i in indices[0]: # indices is a list containing one list of results
                if i in self.index_to_doc:
                    results.append(self.index_to_doc[i])
                else:
                    logging.warning(f"Index {i} found by FAISS but not in mapping.")
            
            logging.info(f"Retrieved {len(results)} relevant documents.")
            return results

        except Exception as e:
            logging.error(f"Error during retrieval: {e}")
            return []

    def generate_question_variation(self, retrieved_docs):
        """
        Uses the retrieved documents as context to generate a new question variation via LLM.
        
        Args:
            retrieved_docs (list): List of documents returned by retrieve_relevant_questions.
            
        Returns:
            dict: Dictionary containing the generated question with prompt, options, and metadata.
                  Returns None if generation failed.
        """
        logging.info("Generating question variation using retrieved context...")
        
        if not retrieved_docs:
            logging.error("No retrieved documents provided for generation.")
            return None
        
        try:
            # 1. Construct the context from retrieved documents
            context_examples = []
            for i, doc in enumerate(retrieved_docs[:3], 1):  # Use top 3 examples
                example = f"Example {i}:\n"
                example += f"Subject: {doc.get('subject', 'Unknown')}\n"
                example += f"Topic: {doc.get('topic', 'Unknown')}\n"
                example += f"Difficulty: {doc.get('difficulty', 'Unknown')}\n"
                example += f"Question: {doc.get('prompt', '')}\n"
                
                # Add options if available
                options = doc.get('options', [])
                if options:
                    example += "Options:\n"
                    for opt in options:
                        example += f"  {opt.get('id')}. {opt.get('text')}\n"
                    example += f"Correct Answer: {doc.get('correct_answer', 'N/A')}\n"
                
                context_examples.append(example)
            
            context_text = "\n\n".join(context_examples)
            
            # 2. Get metadata from first retrieved document for consistency
            first_doc = retrieved_docs[0]
            subject = first_doc.get('subject', 'Physics')
            topic = first_doc.get('topic', 'General')
            difficulty = first_doc.get('difficulty', 'Medium')
            question_type = first_doc.get('type', 'Single-Correct-MCQ')
            
            # 3. Construct the prompt for LLM
            prompt = f"""You are an expert JEE (Joint Entrance Examination) question paper creator. Based on the following examples, generate ONE NEW, UNIQUE question that tests similar concepts.

EXAMPLES OF EXISTING QUESTIONS:
{context_text}

REQUIREMENTS:
- Subject: {subject}
- Topic: {topic}
- Difficulty Level: {difficulty}
- Question Type: {question_type}
- Generate a completely NEW question (do not copy the examples)
- The question should test similar concepts/topics as the examples
- Provide 4 options numbered 1, 2, 3, 4
- Indicate the correct answer

IMPORTANT: Return your response in VALID JSON format with the following structure:
{{
    "question_prompt": "Your generated question text here",
    "options": [
        {{"id": "1", "text": "Option 1 text"}},
        {{"id": "2", "text": "Option 2 text"}},
        {{"id": "3", "text": "Option 3 text"}},
        {{"id": "4", "text": "Option 4 text"}}
    ],
    "correct_answer": "1",
    "explanation": "Brief explanation of why this is the correct answer"
}}

Generate the question now:"""

            # 4. Call Groq LLM
            logging.info(f"Calling Groq LLM ({self.llm_model}) for question generation...")
            
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert JEE question paper creator. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,  # Higher temperature for more creative variations
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            # 5. Parse the response
            response_text = response.choices[0].message.content
            generated_data = json.loads(response_text)
            
            # 6. Add metadata to the generated question
            generated_question = {
                "question_prompt": generated_data.get("question_prompt", ""),
                "options": generated_data.get("options", []),
                "correct_answer": generated_data.get("correct_answer", ""),
                "explanation": generated_data.get("explanation", ""),
                "metadata": {
                    "subject": subject,
                    "topic": topic,
                    "difficulty": difficulty,
                    "type": question_type,
                    "generated": True,
                    "source_examples": len(retrieved_docs)
                }
            }
            
            logging.info("Successfully generated question variation.")
            return generated_question
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse LLM response as JSON: {e}")
            logging.error(f"Response text: {response_text}")
            return None
        except Exception as e:
            logging.error(f"Error during question generation: {e}")
            return None

    # You might add a validation function here later
    # def validate_question(self, generated_question, subject): ...

# Example usage (for testing this file directly)
if __name__ == "__main__":
    try:
        pipeline = PredictPipeline()
        
        # Example: Find questions similar to "kinematics velocity"
        search_query = "Physics questions about kinematics and velocity"
        retrieved = pipeline.retrieve_relevant_questions(search_query, k=3)
        
        print("\n" + "="*80)
        print("RETRIEVED DOCUMENTS")
        print("="*80)
        for i, doc in enumerate(retrieved, 1):
            print(f"\n{i}. [{doc.get('subject')}] {doc.get('topic')} - {doc.get('difficulty')}")
            print(f"   Source: {doc.get('source_file')}, Q#{doc.get('question_number')}")
            print(f"   Prompt: {doc.get('prompt', '')[:150]}...")
        
        if retrieved:
            print("\n" + "="*80)
            print("GENERATING NEW QUESTION VARIATION")
            print("="*80)
            new_question = pipeline.generate_question_variation(retrieved)
            
            if new_question:
                print(f"\n✓ Generated Question Successfully!")
                print(f"\nSubject: {new_question['metadata']['subject']}")
                print(f"Topic: {new_question['metadata']['topic']}")
                print(f"Difficulty: {new_question['metadata']['difficulty']}")
                print(f"Type: {new_question['metadata']['type']}")
                print(f"\nQuestion:")
                print(new_question['question_prompt'])
                print(f"\nOptions:")
                for opt in new_question['options']:
                    marker = "✓" if opt['id'] == new_question['correct_answer'] else " "
                    print(f"  [{marker}] {opt['id']}. {opt['text']}")
                print(f"\nCorrect Answer: {new_question['correct_answer']}")
                print(f"\nExplanation:")
                print(new_question['explanation'])
            else:
                print("\n✗ Failed to generate question variation.")
        
    except Exception as e:
        print(f"\n✗ Error during prediction test run: {e}")
        import traceback
        traceback.print_exc()