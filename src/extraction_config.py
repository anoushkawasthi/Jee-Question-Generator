"""
Configuration Module for Extraction Pipeline

Loads configuration from environment variables and config files.
"""

import os
from pathlib import Path
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


class ExtractionConfig:
    """Configuration for the extraction pipeline"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        # Directories
        self.PDF_INPUT_DIR = os.getenv('PDF_INPUT_DIR', 'data/raw_pdfs')
        self.EXTRACTION_OUTPUT_DIR = os.getenv('EXTRACTION_OUTPUT_DIR', 'extraction_output')
        self.SCHEMAS_DIR = os.getenv('SCHEMAS_DIR', 'schemas')
        self.LOGS_DIR = os.getenv('LOGS_DIR', 'logs')
        
        # Nougat Configuration
        self.NOUGAT_MODEL = os.getenv('NOUGAT_MODEL', 'facebook/nougat-base')
        self.NOUGAT_DEVICE = os.getenv('NOUGAT_DEVICE', 'cuda')
        self.NOUGAT_BATCH_SIZE = int(os.getenv('NOUGAT_BATCH_SIZE', '1'))
        
        # OSRA Configuration
        self.OSRA_PATH = os.getenv('OSRA_PATH', 'osra')
        self.IMAGEMAGICK_PATH = os.getenv('IMAGEMAGICK_PATH', 'convert')
        
        # Schema Path
        self.SCHEMA_PATH = os.getenv('SCHEMA_PATH', 'schemas/jee_question_schema.json')
        
        # Batch Processing
        self.BATCH_MAX_WORKERS = int(os.getenv('BATCH_MAX_WORKERS', '2'))
        self.BATCH_PARALLEL = os.getenv('BATCH_PARALLEL', 'false').lower() == 'true'
        
        # Logging
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create necessary directories if they don't exist"""
        for dir_path in [self.PDF_INPUT_DIR, self.EXTRACTION_OUTPUT_DIR, 
                        self.SCHEMAS_DIR, self.LOGS_DIR]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        return {
            'pdf_input_dir': self.PDF_INPUT_DIR,
            'extraction_output_dir': self.EXTRACTION_OUTPUT_DIR,
            'schemas_dir': self.SCHEMAS_DIR,
            'logs_dir': self.LOGS_DIR,
            'nougat_model': self.NOUGAT_MODEL,
            'nougat_device': self.NOUGAT_DEVICE,
            'nougat_batch_size': self.NOUGAT_BATCH_SIZE,
            'osra_path': self.OSRA_PATH,
            'imagemagick_path': self.IMAGEMAGICK_PATH,
            'schema_path': self.SCHEMA_PATH,
            'batch_max_workers': self.BATCH_MAX_WORKERS,
            'batch_parallel': self.BATCH_PARALLEL,
            'log_level': self.LOG_LEVEL
        }
    
    def __repr__(self) -> str:
        """String representation of configuration"""
        config_dict = self.to_dict()
        return json.dumps(config_dict, indent=2)


# Global configuration instance
config = ExtractionConfig()


def get_config() -> ExtractionConfig:
    """Get the global configuration instance"""
    return config


def load_config_from_file(config_file: str) -> dict:
    """
    Load configuration from JSON file
    
    Args:
        config_file: Path to configuration JSON file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing configuration file: {str(e)}")
        return {}


if __name__ == "__main__":
    print("Extraction Pipeline Configuration")
    print("=" * 50)
    print(config)
