"""
Validation and Testing Script for Extraction Pipeline

This script validates the installation, tests components, and verifies configuration.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineValidator:
    """Validates extraction pipeline installation and configuration"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'all_passed': True
        }
    
    def test_directory_structure(self) -> bool:
        """Test project directory structure"""
        logger.info("\n[TEST 1/8] Checking directory structure...")
        
        required_dirs = [
            'src',
            'src/components',
            'src/pipeline',
            'schemas',
            'data',
            'data/raw_pdfs'
        ]
        
        all_exist = True
        for dir_path in required_dirs:
            exists = Path(dir_path).exists()
            status = "✓" if exists else "✗"
            logger.info(f"  {status} {dir_path}")
            if not exists:
                all_exist = False
        
        self.results['tests'].append({
            'name': 'Directory Structure',
            'passed': all_exist,
            'details': f"Checked {len(required_dirs)} directories"
        })
        
        return all_exist
    
    def test_required_files(self) -> bool:
        """Test presence of required files"""
        logger.info("\n[TEST 2/8] Checking required files...")
        
        required_files = [
            'requirements.txt',
            'extraction_main.py',
            'src/extraction_config.py',
            'src/components/pdf_text_image_extractor.py',
            'src/components/nougat_converter.py',
            'src/components/osra_chemical_extractor.py',
            'src/components/json_combiner_validator.py',
            'src/pipeline/extraction_pipeline.py',
            'src/pipeline/batch_processor.py',
            'schemas/jee_question_schema.json',
            'EXTRACTION_PIPELINE_GUIDE.md',
            'EXTRACTION_QUICK_START.md'
        ]
        
        all_exist = True
        for file_path in required_files:
            exists = Path(file_path).exists()
            status = "✓" if exists else "✗"
            logger.info(f"  {status} {file_path}")
            if not exists:
                all_exist = False
        
        self.results['tests'].append({
            'name': 'Required Files',
            'passed': all_exist,
            'details': f"Checked {len(required_files)} files"
        })
        
        return all_exist
    
    def test_schema_validity(self) -> bool:
        """Test JSON schema validity"""
        logger.info("\n[TEST 3/8] Validating JSON schema...")
        
        schema_path = 'schemas/jee_question_schema.json'
        
        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            
            # Check required properties
            required_keys = ['$schema', 'title', 'type', 'properties']
            schema_has_keys = all(key in schema for key in required_keys)
            
            if schema_has_keys:
                logger.info(f"  ✓ Schema is valid JSON")
                logger.info(f"  ✓ Title: {schema.get('title')}")
                
                # Check for main sections
                props = schema.get('properties', {})
                sections = list(props.keys())
                logger.info(f"  ✓ Main sections: {', '.join(sections)}")
                
                self.results['tests'].append({
                    'name': 'Schema Validity',
                    'passed': True,
                    'details': f"Schema has {len(sections)} main sections"
                })
                return True
            else:
                logger.error(f"  ✗ Schema missing required keys")
                return False
                
        except json.JSONDecodeError as e:
            logger.error(f"  ✗ Invalid JSON: {str(e)}")
            self.results['tests'].append({
                'name': 'Schema Validity',
                'passed': False,
                'details': f"JSON decode error: {str(e)}"
            })
            return False
        except FileNotFoundError:
            logger.error(f"  ✗ Schema file not found")
            self.results['tests'].append({
                'name': 'Schema Validity',
                'passed': False,
                'details': 'Schema file not found'
            })
            return False
    
    def test_python_imports(self) -> bool:
        """Test Python module imports"""
        logger.info("\n[TEST 4/8] Testing Python imports...")
        
        sys.path.insert(0, str(Path('src').absolute()))
        
        modules = [
            ('extraction_config', 'ExtractionConfig'),
            ('components.pdf_text_image_extractor', 'PyMuPDFExtractor'),
            ('components.nougat_converter', 'NougatConverter'),
            ('components.osra_chemical_extractor', 'OSRAExtractor'),
            ('components.json_combiner_validator', 'JSONCombiner'),
            ('pipeline.extraction_pipeline', 'ExtractionPipeline'),
            ('pipeline.batch_processor', 'BatchProcessor')
        ]
        
        all_imported = True
        for module_name, class_name in modules:
            try:
                module = __import__(module_name, fromlist=[class_name])
                getattr(module, class_name)
                logger.info(f"  ✓ {module_name}.{class_name}")
            except ImportError as e:
                logger.warning(f"  ⚠ {module_name}: {str(e)}")
                # Don't fail for optional dependencies
            except Exception as e:
                logger.error(f"  ✗ {module_name}: {str(e)}")
                all_imported = False
        
        self.results['tests'].append({
            'name': 'Python Imports',
            'passed': all_imported,
            'details': f"Tested {len(modules)} modules"
        })
        
        return all_imported
    
    def test_dependencies(self) -> bool:
        """Test required Python dependencies"""
        logger.info("\n[TEST 5/8] Checking dependencies...")
        
        required_packages = [
            'pathlib',
            'json',
            'logging',
            'datetime',
            're',
            'jsonschema'
        ]
        
        missing = []
        for package in required_packages:
            try:
                __import__(package)
                logger.info(f"  ✓ {package}")
            except ImportError:
                logger.warning(f"  ⚠ {package}")
                missing.append(package)
        
        all_present = len(missing) == 0
        
        self.results['tests'].append({
            'name': 'Dependencies',
            'passed': all_present,
            'details': f"Checked {len(required_packages)} packages"
        })
        
        return all_present
    
    def test_optional_dependencies(self) -> bool:
        """Test optional dependencies (warnings only)"""
        logger.info("\n[TEST 6/8] Checking optional dependencies...")
        
        optional_packages = [
            ('fitz', 'PyMuPDF'),
            ('transformers', 'Transformers (for Nougat)'),
            ('torch', 'PyTorch (for GPU support)')
        ]
        
        installed = 0
        for package, name in optional_packages:
            try:
                __import__(package)
                logger.info(f"  ✓ {name}")
                installed += 1
            except ImportError:
                logger.warning(f"  ⚠ {name} not installed (optional)")
        
        self.results['tests'].append({
            'name': 'Optional Dependencies',
            'passed': True,
            'details': f"{installed}/{len(optional_packages)} optional packages installed"
        })
        
        return True
    
    def test_configuration(self) -> bool:
        """Test configuration loading"""
        logger.info("\n[TEST 7/8] Testing configuration...")
        
        try:
            from extraction_config import get_config
            
            config = get_config()
            logger.info(f"  ✓ Configuration loaded successfully")
            logger.info(f"    - PDF Input Dir: {config.PDF_INPUT_DIR}")
            logger.info(f"    - Output Dir: {config.EXTRACTION_OUTPUT_DIR}")
            logger.info(f"    - Log Level: {config.LOG_LEVEL}")
            
            self.results['tests'].append({
                'name': 'Configuration',
                'passed': True,
                'details': 'Configuration loaded from environment'
            })
            
            return True
            
        except Exception as e:
            logger.error(f"  ✗ Configuration error: {str(e)}")
            self.results['tests'].append({
                'name': 'Configuration',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
            return False
    
    def test_sample_schema_validation(self) -> bool:
        """Test schema validation with sample data"""
        logger.info("\n[TEST 8/8] Testing schema validation...")
        
        try:
            from components.json_combiner_validator import SchemaValidator
            
            validator = SchemaValidator('schemas/jee_question_schema.json')
            
            # Create minimal valid sample
            sample_data = {
                "paper_metadata": {
                    "exam_name": "JEE Main",
                    "exam_date_shift": "01 Feb Shift 1",
                    "paper_id": "TEST_01FEB_S1",
                    "total_questions": 1,
                    "extraction_timestamp": datetime.now().isoformat()
                },
                "questions": [
                    {
                        "question_id": "TEST_01FEB_S1_q1",
                        "question_number": 1,
                        "subject": "Mathematics",
                        "question_type": "MCQ",
                        "question_text": "Sample question",
                        "options": [
                            {"id": "A", "text": "Option A"},
                            {"id": "B", "text": "Option B"}
                        ],
                        "correct_answer": "A"
                    }
                ],
                "extraction_summary": {
                    "total_pages": 1,
                    "images_extracted": 0,
                    "chemical_structures_detected": 0,
                    "overall_confidence": 0.95
                }
            }
            
            is_valid, errors = validator.validate(sample_data)
            
            if is_valid:
                logger.info(f"  ✓ Sample data validates successfully")
                self.results['tests'].append({
                    'name': 'Schema Validation',
                    'passed': True,
                    'details': 'Sample data passes validation'
                })
                return True
            else:
                logger.error(f"  ✗ Validation failed: {errors}")
                self.results['tests'].append({
                    'name': 'Schema Validation',
                    'passed': False,
                    'details': f"Validation errors: {errors}"
                })
                return False
                
        except Exception as e:
            logger.error(f"  ✗ Error: {str(e)}")
            self.results['tests'].append({
                'name': 'Schema Validation',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
            return False
    
    def run_all_tests(self) -> None:
        """Run all validation tests"""
        logger.info("=" * 70)
        logger.info("JEE EXTRACTION PIPELINE - VALIDATION TEST SUITE")
        logger.info("=" * 70)
        
        sys.path.insert(0, str(Path('src').absolute()))
        
        tests = [
            self.test_directory_structure,
            self.test_required_files,
            self.test_schema_validity,
            self.test_python_imports,
            self.test_dependencies,
            self.test_optional_dependencies,
            self.test_configuration,
            self.test_sample_schema_validation
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                logger.error(f"Test error: {str(e)}")
                self.results['all_passed'] = False
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self) -> None:
        """Print validation summary"""
        logger.info("\n" + "=" * 70)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 70)
        
        passed_count = sum(1 for t in self.results['tests'] if t['passed'])
        total_count = len(self.results['tests'])
        
        logger.info(f"Total Tests: {total_count}")
        logger.info(f"Passed: {passed_count}")
        logger.info(f"Failed: {total_count - passed_count}")
        logger.info(f"Success Rate: {(passed_count/total_count)*100:.1f}%")
        
        if self.results['all_passed'] and passed_count == total_count:
            logger.info("\n✓ ALL TESTS PASSED - Pipeline is ready!")
        else:
            logger.warning("\n✗ Some tests failed - Review the output above")
        
        logger.info("=" * 70 + "\n")
        
        # Save detailed results
        self._save_results()
    
    def _save_results(self) -> None:
        """Save validation results to file"""
        output_file = 'validation_results.json'
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Detailed results saved to: {output_file}")


def main():
    """Main entry point"""
    validator = PipelineValidator()
    validator.run_all_tests()


if __name__ == "__main__":
    main()
