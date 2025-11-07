"""
Main Extraction Pipeline

Orchestrates the complete extraction workflow:
1. PyMuPDF: Extract text and images
2. Nougat: Convert to LaTeX markdown
3. OSRA: Extract chemical structures
4. JSON Combiner: Merge all data with validation

This pipeline follows a modular architecture for flexibility and reusability.
"""

import os
import logging
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# Import pipeline components
from components.pdf_text_image_extractor import PyMuPDFExtractor
from components.nougat_converter import NougatConverter
from components.osra_chemical_extractor import OSRAExtractor
from components.json_combiner_validator import JSONCombiner

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    """
    Main extraction pipeline orchestrating all components.
    
    Workflow:
    1. Extract text and images (PyMuPDF)
    2. Convert to Markdown with LaTeX (Nougat)
    3. Extract chemical structures (OSRA)
    4. Combine and validate JSON output
    """
    
    def __init__(self, 
                 pdf_path: str,
                 output_dir: str = "extraction_output",
                 schema_path: str = "schemas/jee_question_schema.json"):
        """
        Initialize the extraction pipeline.
        
        Args:
            pdf_path: Path to the PDF file to extract
            output_dir: Directory for output files
            schema_path: Path to JSON schema for validation
        """
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.schema_path = Path(schema_path)
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
        # Verify schema exists
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        
        # Initialize components
        self.text_extractor = None
        self.nougat_converter = None
        self.osra_extractor = None
        self.json_combiner = None
        
        logger.info(f"Pipeline initialized for: {self.pdf_path.name}")
    
    def _init_components(self) -> None:
        """Initialize all extraction components"""
        try:
            logger.info("Initializing extraction components...")
            
            # PyMuPDF Extractor
            self.text_extractor = PyMuPDFExtractor(
                str(self.pdf_path),
                output_dir=str(self.images_dir)
            )
            
            # Nougat Converter
            self.nougat_converter = NougatConverter()
            
            # OSRA Extractor
            try:
                self.osra_extractor = OSRAExtractor()
            except Exception as e:
                logger.warning(f"OSRA not available: {e}")
                self.osra_extractor = None
            
            # JSON Combiner
            self.json_combiner = JSONCombiner(str(self.schema_path))
            
            logger.info("Components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            raise
    
    def extract_text_and_images(self) -> Dict:
        """
        Step 1: Extract text blocks and images using PyMuPDF.
        
        Returns:
            Dictionary with extraction results
        """
        logger.info("Step 1: Extracting text and images (PyMuPDF)...")
        
        if not self.text_extractor:
            self._init_components()
        
        try:
            results = self.text_extractor.extract_all()
            
            # Save intermediate results
            json_path = self.output_dir / "01_text_images_extraction.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Text extraction: {len(results['text_blocks'])} blocks, "
                       f"{len(results['images'])} images")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in text extraction: {str(e)}")
            raise
    
    def convert_to_markdown(self) -> Dict:
        """
        Step 2: Convert PDF to Markdown with LaTeX using Nougat.
        
        Returns:
            Dictionary with conversion results
        """
        logger.info("Step 2: Converting to Markdown with LaTeX (Nougat)...")
        
        if not self.nougat_converter:
            self._init_components()
        
        try:
            results = self.nougat_converter.convert_pdf_to_markdown(str(self.pdf_path))
            
            # Save intermediate results
            json_path = self.output_dir / "02_nougat_conversion.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            markdown_content = results.get('markdown_content', '')
            logger.info(f"Markdown conversion: {results.get('equations_detected', 0)} equations detected")
            
            return results
            
        except Exception as e:
            logger.warning(f"Nougat LaTeX conversion skipped (optional feature): {str(e)}")
            # Return empty markdown results - LaTeX is optional
            return {"status": "skipped", "markdown_content": "", "equations_detected": 0, "reason": "Nougat not available"}
    
    def extract_chemical_structures(self, image_directory: Optional[str] = None) -> list:
        """
        Step 3: Extract chemical structures from images using OSRA.
        
        Args:
            image_directory: Directory containing extracted images (uses images_dir if None)
            
        Returns:
            List of extraction results
        """
        logger.info("Step 3: Extracting chemical structures (OSRA)...")
        
        if not self.osra_extractor:
            logger.warning("OSRA not available, skipping chemical structure extraction")
            return []
        
        image_dir = image_directory or str(self.images_dir)
        
        if not Path(image_dir).exists():
            logger.warning(f"Image directory not found: {image_dir}")
            return []
        
        try:
            results = self.osra_extractor.batch_extract_smiles(image_dir)
            
            # Save intermediate results
            json_path = self.output_dir / "03_osra_extraction.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            successful = len([r for r in results if r.get('status') == 'success'])
            logger.info(f"Chemical extraction: {successful}/{len(results)} images processed")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in chemical extraction: {str(e)}")
            return []
    
    def combine_and_validate(self, 
                            text_results: Dict,
                            markdown_results: Dict,
                            chemical_results: list) -> Dict:
        """
        Step 4: Combine all data and validate against schema.
        
        Args:
            text_results: Results from text extraction
            markdown_results: Results from markdown conversion
            chemical_results: Results from chemical extraction
            
        Returns:
            Combined and validated JSON dictionary
        """
        logger.info("Step 4: Combining and validating data...")
        
        if not self.json_combiner:
            self._init_components()
        
        try:
            # Prepare metadata
            paper_metadata = text_results.get('metadata', {})
            paper_metadata['paper_id'] = text_results.get('paper_id', 'unknown')
            paper_metadata['exam_name'] = 'JEE Main'
            paper_metadata['exam_date_shift'] = self._extract_exam_info()
            
            # Combine all data
            combined_data = self.json_combiner.combine_extraction_data(
                paper_metadata=paper_metadata,
                markdown_content=markdown_results.get('markdown_content', ''),
                extracted_images=text_results.get('images', []),
                chemical_data=chemical_results
            )
            
            logger.info(f"Data combined: {len(combined_data['questions'])} questions")
            
            # Validate
            is_valid, errors = self.json_combiner.validator.validate(combined_data)
            
            if not is_valid:
                logger.warning(f"Validation errors: {errors}")
            else:
                logger.info("JSON validation passed")
            
            return combined_data
            
        except Exception as e:
            logger.error(f"Error in combination and validation: {str(e)}")
            raise
    
    def _extract_exam_info(self) -> str:
        """
        Extract exam date and shift from PDF filename.
        
        Returns:
            Exam date and shift string
        """
        filename = self.pdf_path.name
        
        # Try to extract from filename patterns
        # Example: "JEE Main 2024 (01 Feb Shift 1)"
        import re
        match = re.search(r'(\d{1,2}\s+\w+\s+(?:Shift\s+\d)?)', filename)
        
        if match:
            return match.group(1)
        
        return "Unknown"
    
    def run(self, save_final_json: bool = True) -> Dict:
        """
        Execute the complete extraction pipeline.
        
        Args:
            save_final_json: Whether to save final JSON to file
            
        Returns:
            Combined and validated extraction data
        """
        logger.info("=" * 60)
        logger.info("Starting JEE Question Extraction Pipeline")
        logger.info(f"PDF: {self.pdf_path.name}")
        logger.info(f"Output: {self.output_dir}")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Step 1: Extract text and images
            text_results = self.extract_text_and_images()
            
            # Step 2: Convert to Markdown with LaTeX
            markdown_results = self.convert_to_markdown()
            
            # Step 3: Extract chemical structures
            chemical_results = self.extract_chemical_structures()
            
            # Step 4: Combine and validate
            combined_data = self.combine_and_validate(
                text_results,
                markdown_results,
                chemical_results
            )
            
            # Save final JSON
            if save_final_json:
                output_file = self.output_dir / "final_extraction.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(combined_data, f, indent=2, ensure_ascii=False)
                logger.info(f"Final JSON saved to: {output_file}")
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info("=" * 60)
            logger.info(f"Pipeline completed successfully in {elapsed_time:.2f} seconds")
            logger.info(f"Total questions extracted: {len(combined_data.get('questions', []))}")
            logger.info("=" * 60)
            
            return combined_data
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"Pipeline failed: {str(e)}")
            logger.error("=" * 60)
            raise


def run_extraction_pipeline(pdf_path: str, 
                           output_dir: str = "extraction_output",
                           schema_path: str = "schemas/jee_question_schema.json") -> Dict:
    """
    Convenience function to run the extraction pipeline.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Output directory
        schema_path: Path to JSON schema
        
    Returns:
        Extracted and validated data
    """
    pipeline = ExtractionPipeline(pdf_path, output_dir, schema_path)
    return pipeline.run()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example: Run extraction pipeline
    pdf_file = "data/raw_pdfs/2024/JEE_Main_2024_Sample.pdf"
    
    if Path(pdf_file).exists():
        try:
            results = run_extraction_pipeline(pdf_file)
            print(f"\nExtraction successful!")
            print(f"Questions extracted: {len(results.get('questions', []))}")
        except Exception as e:
            print(f"Extraction failed: {str(e)}")
    else:
        print(f"PDF file not found: {pdf_file}")
