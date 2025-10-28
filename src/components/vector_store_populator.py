import os
import sys
import json
import logging
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import pickle # To save the mapping

# Update sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VectorStorePopulator:
    def __init__(self):
        self.processed_data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed', 'questions_with_metadata.json')
        self.artifacts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'artifacts')
        self.index_path = os.path.join(self.artifacts_dir, 'faiss_index.index')
        self.mapping_path = os.path.join(self.artifacts_dir, 'index_to_doc_mapping.pkl')
        self.model_name = 'all-MiniLM-L6-v2' # Efficient and effective model
        logging.info(f"Loading data from: {self.processed_data_path}")
        logging.info(f"Saving artifacts to: {self.artifacts_dir}")

    def initiate_vector_store_population(self):
        """
        Loads processed questions, generates embeddings, builds a FAISS index,
        and saves the index and mapping.
        """
        try:
            # 1. Load the processed data
            logging.info("Loading questions_with_metadata.json...")
            try:
                with open(self.processed_data_path, 'r', encoding='utf-8') as f:
                    questions_data = json.load(f)
            except FileNotFoundError:
                logging.error(f"File not found: {self.processed_data_path}. Run data_transformation.py first.")
                return
            except json.JSONDecodeError:
                logging.error(f"Error decoding JSON from {self.processed_data_path}. File might be empty or corrupted.")
                return

            if not questions_data:
                logging.warning("No questions found in the JSON file. Aborting.")
                return

            logging.info(f"Loaded {len(questions_data)} questions.")

            # 2. Initialize the embedding model
            logging.info(f"Loading sentence transformer model: {self.model_name}...")
            model = SentenceTransformer(self.model_name)
            logging.info("Model loaded successfully.")

            # 3. Prepare texts and metadata for embedding
            texts_to_embed = []
            index_to_doc_mapping = {} # Maps FAISS index position to original question info

            logging.info("Preparing text data for embedding...")
            for i, question in enumerate(tqdm(questions_data, desc="Preparing data")):
                # Combine prompt and topic for richer context in embedding
                prompt = question.get('question_prompt', '')
                topic = question.get('metadata', {}).get('topic', '')
                text = f"Topic: {topic}\nQuestion: {prompt}"
                texts_to_embed.append(text)

                # Store essential info needed for retrieval later
                index_to_doc_mapping[i] = {
                    "question_number": question.get("question_number"),
                    "source_file": question.get("metadata", {}).get("source_file"),
                    "subject": question.get("metadata", {}).get("subject"),
                    "topic": question.get("metadata", {}).get("topic"),
                    "difficulty": question.get("metadata", {}).get("difficulty"),
                    "type": question.get("metadata", {}).get("type"),
                    "prompt": prompt, # Store prompt for easy display later
                    "options": question.get("options"),
                    "correct_answer": question.get("answer_details", {}).get("correct_option_id")
                    # Add any other fields you might want easy access to after retrieval
                }

            # 4. Generate embeddings (this can take time for large datasets)
            logging.info(f"Generating embeddings for {len(texts_to_embed)} texts...")
            embeddings = model.encode(texts_to_embed, show_progress_bar=True)
            logging.info(f"Embeddings generated. Shape: {embeddings.shape}")

            # Ensure embeddings are float32, required by FAISS
            embeddings = np.array(embeddings).astype('float32')

            # 5. Build the FAISS index
            dimension = embeddings.shape[1] # Get the dimension size from the embeddings
            logging.info(f"Building FAISS index with dimension {dimension}...")
            # Using IndexFlatL2 for simple Euclidean distance search
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings) # Add the vectors to the index
            logging.info(f"FAISS index built. Total vectors indexed: {index.ntotal}")

            # 6. Save the index and the mapping
            logging.info("Saving FAISS index and mapping file...")
            os.makedirs(self.artifacts_dir, exist_ok=True) # Ensure artifacts directory exists

            faiss.write_index(index, self.index_path)

            with open(self.mapping_path, 'wb') as f:
                pickle.dump(index_to_doc_mapping, f)

            logging.info(f"Successfully saved index to {self.index_path}")
            logging.info(f"Successfully saved mapping to {self.mapping_path}")

        except Exception as e:
            logging.error(f"Vector store population failed: {e}")
            raise

# This block allows you to run this file directly for testing
if __name__ == "__main__":
    logging.info("Starting Vector Store Population...")
    populator = VectorStorePopulator()
    populator.initiate_vector_store_population()
    logging.info("Vector Store Population complete.")