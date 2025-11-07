"""
OSRA Chemical Structure Recognition Component

This component converts 2D chemical structure diagrams to SMILES notation
using OSRA (Online SMILES Recognition Application).

Key Capabilities:
- Read 90+ image formats (GIF, JPEG, PNG, TIFF, PDF, PS)
- Extract chemical structures from graphical representations
- Generate SMILES (Simplified Molecular Input Line Entry Specification) strings
- Support SD file output format
"""

import os
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class ChemicalStructureValidator:
    """Validates SMILES strings and chemical structure data"""
    
    # Common SMILES atom symbols
    VALID_ATOMS = {'C', 'N', 'O', 'S', 'P', 'F', 'Cl', 'Br', 'I', 'B', 'Si', 'Se', 'H'}
    
    # SMILES special characters
    VALID_CHARS = {'(', ')', '[', ']', '=', '#', '\\', '/', '@', '-', '+', '%'}
    
    @staticmethod
    def is_valid_smiles(smiles_string: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SMILES syntax.
        
        Args:
            smiles_string: SMILES string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not smiles_string or not isinstance(smiles_string, str):
            return False, "SMILES must be a non-empty string"
        
        try:
            # Check for balanced brackets and parentheses
            if smiles_string.count('[') != smiles_string.count(']'):
                return False, "Unbalanced square brackets"
            if smiles_string.count('(') != smiles_string.count(')'):
                return False, "Unbalanced parentheses"
            
            # Check for valid characters
            valid_set = set(smiles_string) - ChemicalStructureValidator.VALID_CHARS - \
                       ChemicalStructureValidator.VALID_ATOMS - set('0123456789')
            if valid_set and not all(c.isalpha() or c.isdigit() for c in valid_set):
                return False, f"Invalid characters in SMILES: {valid_set}"
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def estimate_molecule_weight(smiles_string: str) -> Optional[float]:
        """
        Rough estimate of molecular weight from SMILES.
        
        Args:
            smiles_string: SMILES string
            
        Returns:
            Estimated molecular weight or None
        """
        # Approximate atomic weights
        weights = {
            'H': 1.008, 'C': 12.011, 'N': 14.007, 'O': 15.999,
            'S': 32.06, 'P': 30.974, 'F': 18.998, 'Cl': 35.45,
            'Br': 79.904, 'I': 126.90, 'B': 10.811, 'Si': 28.086
        }
        
        try:
            weight = 0.0
            # Simple counting (not accurate for complex SMILES)
            for atom, w in weights.items():
                weight += smiles_string.count(atom) * w
            
            return round(weight, 2) if weight > 0 else None
            
        except Exception as e:
            logger.warning(f"Error estimating molecular weight: {str(e)}")
            return None


class OSRAExtractor:
    """
    Extracts chemical structures from images using OSRA.
    
    Attributes:
        osra_path: Path to OSRA executable
        imagemagick_path: Path to ImageMagick convert executable
    """
    
    def __init__(self, osra_path: str = "osra", 
                 imagemagick_path: str = "convert"):
        self.osra_path = osra_path
        self.imagemagick_path = imagemagick_path
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Check if OSRA and ImageMagick are available"""
        try:
            # Check OSRA
            result = subprocess.run(
                [self.osra_path, "-h"],
                capture_output=True,
                timeout=5
            )
            logger.debug("OSRA is available")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"OSRA might not be available: {e}")
    
    def extract_smiles_from_image(self, image_path: str) -> Dict:
        """
        Extract SMILES from a chemical structure image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing SMILES and metadata
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            return {
                "status": "error",
                "image_file": image_path.name,
                "error": f"Image file not found: {image_path}"
            }
        
        try:
            logger.info(f"Extracting chemical structures from: {image_path.name}")
            
            # Create temporary output file for SMILES
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', 
                                            delete=False) as tmp:
                tmp_output = tmp.name
            
            try:
                # Run OSRA command
                cmd = [self.osra_path, "-i", str(image_path), "-o", tmp_output]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                smiles_list = []
                confidence_scores = []
                
                # Read OSRA output
                if os.path.exists(tmp_output):
                    with open(tmp_output, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                # Parse OSRA output format: SMILES confidence_score
                                parts = line.split()
                                if len(parts) >= 1:
                                    smiles = parts[0]
                                    confidence = float(parts[1]) if len(parts) > 1 else 0.5
                                    
                                    # Validate SMILES
                                    is_valid, error = ChemicalStructureValidator.is_valid_smiles(smiles)
                                    
                                    if is_valid:
                                        smiles_list.append(smiles)
                                        confidence_scores.append(confidence)
                
                result = {
                    "status": "success",
                    "image_file": image_path.name,
                    "smiles_list": smiles_list,
                    "confidence_scores": confidence_scores,
                    "structures_detected": len(smiles_list)
                }
                
                logger.info(f"Extracted {len(smiles_list)} chemical structures")
                return result
                
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_output):
                    os.remove(tmp_output)
        
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "image_file": image_path.name,
                "error": "OSRA processing timeout"
            }
        except Exception as e:
            logger.error(f"Error extracting SMILES: {str(e)}")
            return {
                "status": "error",
                "image_file": image_path.name,
                "error": str(e)
            }
    
    def batch_extract_smiles(self, image_directory: str) -> List[Dict]:
        """
        Batch extract SMILES from multiple images.
        
        Args:
            image_directory: Directory containing image files
            
        Returns:
            List of extraction results
        """
        image_dir = Path(image_directory)
        results = []
        
        # Find image files
        image_extensions = {'.png', '.jpg', '.jpeg', '.tiff', '.gif'}
        image_files = [
            f for f in image_dir.iterdir()
            if f.suffix.lower() in image_extensions
        ]
        
        logger.info(f"Found {len(image_files)} image files to process")
        
        for i, image_file in enumerate(sorted(image_files), 1):
            logger.info(f"Processing [{i}/{len(image_files)}]: {image_file.name}")
            result = self.extract_smiles_from_image(str(image_file))
            results.append(result)
        
        logger.info(f"Batch extraction completed: {len(results)} files processed")
        return results
    
    def save_extraction_results(self, results: List[Dict], output_file: str) -> str:
        """
        Save SMILES extraction results to JSON.
        
        Args:
            results: List of extraction results
            output_file: Path to save JSON
            
        Returns:
            Path to saved file
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_images": len(results),
            "successful_extractions": len([r for r in results if r["status"] == "success"]),
            "results": results
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_path}")
        return str(output_path)


class ChemistryContentAnalyzer:
    """Analyzes chemistry content and identifies relevant questions"""
    
    @staticmethod
    def classify_chemistry_diagram(image_filename: str) -> str:
        """
        Classify type of chemistry diagram based on filename.
        
        Args:
            image_filename: Name of the image file
            
        Returns:
            Classification string
        """
        filename_lower = image_filename.lower()
        
        classifications = {
            'structure': r'(structure|compound|molecule|organic)',
            'reaction': r'(reaction|mechanism|pathway)',
            'orbital': r'(orbital|orbital)',
            'graph': r'(graph|chart|plot)',
            'apparatus': r'(apparatus|setup|equipment)'
        }
        
        for classification, pattern in classifications.items():
            if re.search(pattern, filename_lower):
                return classification
        
        return "general"
    
    @staticmethod
    def extract_elements_from_smiles(smiles_list: List[str]) -> List[str]:
        """
        Extract unique chemical elements from SMILES strings.
        
        Args:
            smiles_list: List of SMILES strings
            
        Returns:
            List of unique elements found
        """
        elements = set()
        
        for smiles in smiles_list:
            # Simple element extraction from SMILES
            # This is not exhaustive but covers common elements
            element_pattern = r'([A-Z][a-z]?)'
            matches = re.findall(element_pattern, smiles)
            elements.update(matches)
        
        return sorted(list(elements))


def extract_chemistry_content(image_path: str) -> Dict:
    """
    Convenience function to extract chemistry content from an image.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary containing extraction results
    """
    extractor = OSRAExtractor()
    return extractor.extract_smiles_from_image(image_path)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Example image path
    image_file = "../extracted_images/sample_structure.png"
    
    try:
        extractor = OSRAExtractor()
        result = extractor.extract_smiles_from_image(image_file)
        print("Extraction result:", result)
    except Exception as e:
        print(f"Extraction failed: {str(e)}")
