import sys
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import logging

# Add src to sys.path to allow importing PredictPipeline
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import your pipeline class
try:
    from pipeline.predict_pipeline import PredictPipeline
except ModuleNotFoundError:
    print("\n❌ Error: Could not import PredictPipeline.")
    print("Ensure 'src/pipeline/predict_pipeline.py' exists and there are no import errors within it.")
    print("Make sure you run the app from the root project directory.\n")
    sys.exit(1) # Exit if pipeline can't be imported

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Initialize FastAPI App ---
app = FastAPI(
    title="JEE Question Generator API",
    description="API for generating JEE-style question variations using RAG.",
    version="1.0.0"
)

# --- Load the Prediction Pipeline ---
# This happens once when the server starts
try:
    logger.info("Loading prediction pipeline...")
    pipeline = PredictPipeline()
    logger.info("Prediction pipeline loaded successfully.")
except Exception as e:
    logger.error(f"💥 FATAL: Failed to load prediction pipeline on startup: {e}")
    # Optionally, you might want the app to exit if the pipeline fails to load
    # sys.exit(1)
    pipeline = None # Set pipeline to None if loading failed

# --- Define Request Body Structure using Pydantic ---
class GenerationRequest(BaseModel):
    search_query: str = Field(..., description="Text query to find relevant questions (e.g., 'Medium Physics Kinematics questions')")
    k: int = Field(3, description="Number of relevant questions to retrieve for context", ge=1, le=10)

# --- API Endpoints ---
@app.get("/", summary="Health Check")
def read_root():
    """Basic health check endpoint."""
    return {"status": "OK", "message": "JEE Question Generator API is running"}

@app.post("/generate", summary="Generate Question Variation")
async def generate_question(request: GenerationRequest):
    """
    Retrieves relevant questions based on the query and generates a new variation.
    """
    if pipeline is None:
        logger.error("Pipeline not loaded. Cannot process request.")
        raise HTTPException(status_code=503, detail="Pipeline is not available")

    try:
        # 1. Retrieve relevant documents
        logger.info(f"Received generation request with query: '{request.search_query}'")
        retrieved_docs = pipeline.retrieve_relevant_questions(request.search_query, k=request.k)

        if not retrieved_docs:
            logger.warning("No relevant documents found for the query.")
            raise HTTPException(status_code=404, detail="No relevant documents found for the query")

        # 2. Generate variation
        # Note: We're using the metadata from the *first* retrieved doc implicitly here
        # You might want to pass explicit subject/topic/difficulty based on user input later
        generated_question_data = pipeline.generate_question_variation(retrieved_docs)

        if not generated_question_data:
            logger.error("Failed to generate question variation using LLM.")
            raise HTTPException(status_code=500, detail="Failed to generate question variation")

        logger.info("Successfully generated question variation.")
        return generated_question_data

    except HTTPException as http_exc:
        # Re-raise HTTPException so FastAPI handles it
        raise http_exc
    except Exception as e:
        logger.exception(f"An unexpected error occurred during generation: {e}") # Log full traceback
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")
