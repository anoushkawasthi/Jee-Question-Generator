# JEE Question Paper Generator

This project is an intelligent question paper generator for the Joint Entrance Examination (JEE). It moves beyond simple random selection by leveraging a **Retrieval-Augmented Generation (RAG)** pipeline to create fresh, diverse, and well-balanced exam papers.

Teachers and students can specify parameters like subject distribution, difficulty ratio, and total question count to generate custom papers, complete with an answer key and analytics.

## 🎯 Objectives

* **Automate** the generation of JEE-style papers with custom parameters.
* **Ensure** proper topic, subject, and difficulty distribution.
* **Generate** fresh variations of existing questions using an LLM (RAG) to create an ever-expanding question bank.
* **Provide** accurate answer keys and analytics on paper composition.
* **Export** final papers in a print-ready PDF format.

## 🛠️ Tech Stack

* **Backend:** Python (FastAPI / Flask)
* **Database:** Vector DB (FAISS / Pinecone) + MongoDB/PostgreSQL
* **Core ML:** Retrieval-Augmented Generation (RAG)
* **LLM:** Mistral, Llama, or GPT
* **Data Parsing:** `pdfplumber`, Regular Expressions (Regex)
* **Validation:** SymPy (for math/physics validation)
* **PDF Export:** ReportLab / FPDF

## ⚙️ Project Pipeline

The project is broken into two distinct pipelines:

### Part 1: Knowledge Base Construction (Offline Pipeline)

This pipeline runs once to build our vector database from raw PDF files.

1.  **Data Ingestion (`src/components/data_ingestion.py`):**
    * Reads all raw PDF question papers from the `data/raw/` directory.
    * Extracts the raw text content from each page.

2.  **Data Transformation & Enrichment (`src/components/data_transformation.py`):**
    * **Parsing:** Uses Regular Expressions (Regex) to parse the raw text. It identifies and separates question blocks, options, subjects (Physics, Chemistry, Maths), and the answer key.
    * **Enrichment:** For each parsed question, it makes an API call to an LLM to generate the "rich metadata" that is not present in the text: `topic`, `difficulty`, and `type` (e.g., MCQ, Integer).
    * **Output:** Saves all this structured data to `data/processed/questions_with_metadata.json`.

3.  **Vector Store Population (`src/components/vector_store_populator.py`):**
    * Loads the processed JSON file.
    * Uses a sentence-embedding model to create a vector (embedding) for each question.
    * Saves these embeddings and their associated metadata into a FAISS vector index (`artifacts/index.faiss`) for fast retrieval.

### Part 2: RAG Generation (Online Pipeline)

This is the "live" pipeline that runs when a user makes a request via the API.

1.  **Constraint-Based Retrieval (Step 2: Retrieval):**
    * The user provides constraints (e.g., 10 Physics, 5 Chemistry; 40% Medium, 60% Hard).
    * The system queries the FAISS vector database to retrieve a set of "base questions" that match these constraints.

2.  **Question Variation (Step 3: RAG):**
    * The retrieved questions are passed as context to a generative LLM (e.g., Mistral).
    * The LLM is prompted to generate *variations* of these questions—rephrasing them, changing numerical values, or altering scenarios—while preserving the core concept.

3.  **Validation (Step 4: Validation):**
    * The newly generated question variations are passed through a validation layer.
    * **SymPy** and other math solvers are used to check the correctness of solutions for numerical problems.
    * Rule-based checks ensure correct formatting and that MCQs have only one valid answer.

4.  **Paper Assembly & Export (Step 5-6: Assembly & Analytics):**
    * The final, validated set of questions is assembled into a structured exam paper.
    * An answer key is automatically generated.
    * Analytics on the paper's composition (topic coverage, difficulty breakdown) are provided.
    * The final paper is exported as a clean, print-ready PDF.

## 🚀 How to Run

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/JEE-Question-Generator.git](https://github.com/your-username/JEE-Question-Generator.git)
    cd JEE-Question-Generator
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3.  **Set up API Keys:**
    * (Instructions on where to add your LLM API key, e.g., in a `.env` file)

4.  **Run the Offline Knowledge Base Pipeline:**
    * Add your source PDFs to the `data/raw/` folder.
    * Run the main training pipeline (this will run all three `components`):
    ```bash
    python src/pipeline/train_pipeline.py
    ```

5.  **Run the Application Server:**
    ```bash
    python app.py
    ```
    * The API will now be running at `http://127.0.0.1:8000`.

