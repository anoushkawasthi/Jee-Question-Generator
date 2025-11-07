"""
PDF Text and Image Extraction Component (PyMuPDF)

This component extracts raw text blocks with coordinates and embedded images 
from PDF files using PyMuPDF (fitz).

Key Capabilities:
- Extract text with bounding box coordinates (x0, y0, x1, y1) for spatial analysis
- Extract all embedded images in PNG format with systematic naming
- Process at high speed
- Support JSON output format for coordinate-based text extraction
"""

import os
import json
import fitz  # PyMuPDF
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class TextBlock:
    """Represents an extracted text block with coordinates"""
    
    def __init__(self, text: str, x0: float, y0: float, x1: float, y1: float, 
                 block_type: str = "text"):
        self.text = text.strip()
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.block_type = block_type
        self.width = x1 - x0
        self.height = y1 - y0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "text": self.text,
            "coordinates": {
                "x0": round(self.x0, 2),
                "y0": round(self.y0, 2),
                "x1": round(self.x1, 2),
                "y1": round(self.y1, 2),
                "width": round(self.width, 2),
                "height": round(self.height, 2)
            },
            "block_type": self.block_type
        }
    
    def overlaps_with(self, other: 'TextBlock', threshold: float = 0.1) -> bool:
        """Check if this block overlaps with another block"""
        x_overlap = not (self.x1 < other.x0 or self.x0 > other.x1)
        y_overlap = not (self.y1 < other.y0 or self.y0 > other.y1)
        return x_overlap and y_overlap


class PyMuPDFExtractor:
    """
    Extracts text and images from PDF files using PyMuPDF.
    
    Attributes:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted images
        zoom_level: Zoom level for image extraction (default: 2 for 72*2=144 DPI)
    """
    
    def __init__(self, pdf_path: str, output_dir: str = "extracted_images", 
                 zoom_level: float = 2.0):
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.zoom_level = zoom_level
        self.paper_id = self._extract_paper_id()
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    def _extract_paper_id(self) -> str:
        """Extract a unique paper ID from the PDF filename"""
        # Remove .pdf extension and use as paper_id
        return self.pdf_path.stem
    
    def extract_text_blocks(self) -> List[Dict]:
        """
        Extract text blocks with coordinates from all pages.
        
        Returns:
            List of dictionaries containing text blocks with coordinates
        """
        text_blocks = []
        
        try:
            pdf_document = fitz.open(self.pdf_path)
            total_pages = len(pdf_document)
            
            logger.info(f"Extracting text from {total_pages} pages of {self.pdf_path.name}")
            
            for page_num in range(total_pages):
                page = pdf_document[page_num]
                page_blocks = []
                
                # Get text dictionary with detailed layout info
                text_dict = page.get_text("dict")
                
                for block in text_dict.get("blocks", []):
                    if block["type"] == 0:  # Text block
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                text = span.get("text", "").strip()
                                if text:  # Only include non-empty text
                                    bbox = span.get("bbox")
                                    if bbox:
                                        x0, y0, x1, y1 = bbox
                                        text_block = TextBlock(text, x0, y0, x1, y1)
                                        page_blocks.append({
                                            "page": page_num + 1,
                                            "text": text_block.to_dict()
                                        })
                
                logger.debug(f"Extracted {len(page_blocks)} text blocks from page {page_num + 1}")
                text_blocks.extend(page_blocks)
            
            pdf_document.close()
            logger.info(f"Successfully extracted {len(text_blocks)} total text blocks")
            
        except Exception as e:
            logger.error(f"Error extracting text blocks: {str(e)}")
            raise
        
        return text_blocks
    
    def extract_images(self) -> List[Dict]:
        """
        Extract all embedded images from the PDF.
        
        Returns:
            List of dictionaries containing image metadata and filenames
        """
        extracted_images = []
        image_counter = 0
        
        try:
            pdf_document = fitz.open(self.pdf_path)
            total_pages = len(pdf_document)
            
            logger.info(f"Extracting images from {total_pages} pages")
            
            for page_num in range(total_pages):
                page = pdf_document[page_num]
                
                # Get list of images on the page
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    try:
                        # img is a tuple: (xref, smask, width, height, colorspace, ...)
                        xref = img[0]
                        
                        # Extract image from PDF
                        pix = fitz.Pixmap(pdf_document, xref)
                        
                        # Generate filename
                        image_counter += 1
                        filename = f"{self.paper_id}_page{page_num + 1}_img{image_counter}.png"
                        filepath = self.output_dir / filename
                        
                        # Save as PNG
                        pix.save(str(filepath))
                        
                        extracted_images.append({
                            "page": page_num + 1,
                            "filename": filename,
                            "filepath": str(filepath),
                            "width": pix.width,
                            "height": pix.height
                        })
                        
                        logger.debug(f"Extracted image: {filename}")
                        pix = None
                        
                    except Exception as e:
                        logger.warning(f"Error extracting image {img_index} from page {page_num + 1}: {str(e)}")
                        continue
            
            pdf_document.close()
            logger.info(f"Successfully extracted {len(extracted_images)} total images")
            
        except Exception as e:
            logger.error(f"Error extracting images: {str(e)}")
            raise
        
        return extracted_images
    
    def extract_page_metadata(self) -> Dict:
        """
        Extract metadata about the PDF pages.
        
        Returns:
            Dictionary containing page metadata
        """
        metadata = {
            "filename": self.pdf_path.name,
            "paper_id": self.paper_id,
            "total_pages": 0,
            "page_dimensions": []
        }
        
        try:
            pdf_document = fitz.open(self.pdf_path)
            metadata["total_pages"] = len(pdf_document)
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                rect = page.rect
                metadata["page_dimensions"].append({
                    "page": page_num + 1,
                    "width": round(rect.width, 2),
                    "height": round(rect.height, 2)
                })
            
            pdf_document.close()
            
        except Exception as e:
            logger.error(f"Error extracting page metadata: {str(e)}")
            raise
        
        return metadata
    
    def extract_all(self) -> Dict:
        """
        Perform complete extraction: text, images, and metadata.
        
        Returns:
            Dictionary containing all extraction results
        """
        logger.info(f"Starting complete extraction from {self.pdf_path.name}")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "pdf_file": self.pdf_path.name,
            "paper_id": self.paper_id,
            "metadata": self.extract_page_metadata(),
            "text_blocks": self.extract_text_blocks(),
            "images": self.extract_images(),
            "extraction_status": "success"
        }
        
        logger.info("Complete extraction finished successfully")
        return results
    
    def save_extraction_json(self, output_file: str) -> str:
        """
        Save extraction results to JSON file.
        
        Args:
            output_file: Path to save the JSON file
            
        Returns:
            Path to the saved file
        """
        extraction_data = self.extract_all()
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(extraction_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Extraction results saved to {output_path}")
        return str(output_path)


def extract_pdf(pdf_path: str, output_dir: str = "extracted_images") -> Dict:
    """
    Convenience function to extract text and images from a PDF.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted images
        
    Returns:
        Dictionary containing extraction results
    """
    extractor = PyMuPDFExtractor(pdf_path, output_dir)
    return extractor.extract_all()


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Example PDF path
    pdf_file = "../data/raw_pdfs/2024/sample_paper.pdf"
    
    try:
        results = extract_pdf(pdf_file)
        print(f"Extraction successful!")
        print(f"Text blocks: {len(results['text_blocks'])}")
        print(f"Images: {len(results['images'])}")
    except Exception as e:
        print(f"Extraction failed: {str(e)}")
