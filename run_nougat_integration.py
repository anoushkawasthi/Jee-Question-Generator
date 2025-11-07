"""
Main entry point for Nougat integration pipeline
Processes all .mmd files and creates consolidated JSON
"""

import argparse
import sys
from pathlib import Path

from nougat_pipeline_integration import NougatPipelineIntegration


def main():
    parser = argparse.ArgumentParser(
        description="Nougat Integration Pipeline - Process markdown files to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all .mmd files and create consolidated output
  python run_nougat_integration.py --nougat-dir nougat_output --output-dir data/processed --consolidate
  
  # Just process without consolidation
  python run_nougat_integration.py --nougat-dir nougat_output --output-dir data/processed
  
  # Custom output filename
  python run_nougat_integration.py --nougat-dir nougat_output --output-dir data/processed --consolidate --consolidated-output custom_questions.json
        """
    )
    
    parser.add_argument(
        "--nougat-dir",
        type=str,
        default="nougat_output",
        help="Directory containing .mmd files from Nougat (default: nougat_output)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed/nougat_parsed",
        help="Directory to save parsed JSON files (default: data/processed/nougat_parsed)"
    )
    
    parser.add_argument(
        "--consolidate",
        action="store_true",
        help="Create single consolidated JSON file with all questions"
    )
    
    parser.add_argument(
        "--consolidated-output",
        type=str,
        default=None,
        help="Custom path for consolidated JSON file (optional)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Validate input directory
    nougat_path = Path(args.nougat_dir)
    if not nougat_path.exists():
        print(f"❌ Error: Nougat directory not found: {args.nougat_dir}")
        print(f"   Please run: nougat data/raw_pdfs --out {args.nougat_dir} --markdown")
        return 1
    
    # Count .mmd files
    mmd_files = list(nougat_path.glob("*.mmd"))
    if not mmd_files:
        print(f"❌ Error: No .mmd files found in {args.nougat_dir}")
        return 1
    
    print("\n" + "="*70)
    print("NOUGAT INTEGRATION PIPELINE")
    print("="*70)
    print(f"\n📂 Input:  {args.nougat_dir}/")
    print(f"📂 Output: {args.output_dir}/")
    print(f"📊 Files:  {len(mmd_files)} .mmd files found")
    
    # Initialize integration
    try:
        integration = NougatPipelineIntegration(
            nougat_output_dir=args.nougat_dir,
            json_output_dir=args.output_dir
        )
    except Exception as e:
        print(f"❌ Error initializing integration: {str(e)}")
        return 1
    
    # Process all files
    print(f"\n🔄 Processing {len(mmd_files)} .mmd files...")
    try:
        results = integration.process_all_mmd_files()
    except Exception as e:
        print(f"❌ Error during processing: {str(e)}")
        return 1
    
    # Print summary
    print()
    integration.print_summary(results)
    
    # Create consolidated file if requested
    if args.consolidate:
        print(f"\n🔄 Creating consolidated JSON...")
        try:
            consolidated_path = integration.create_consolidated_json(args.consolidated_output)
            
            if consolidated_path:
                # Get file size
                file_size = Path(consolidated_path).stat().st_size / (1024 * 1024)
                
                print(f"✅ Consolidated JSON created successfully!")
                print(f"   File:  {consolidated_path}")
                print(f"   Size:  {file_size:.2f} MB")
                
                # Count questions
                import json
                with open(consolidated_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                total_q = data['metadata']['total_questions']
                print(f"   Questions: {total_q}")
                
                print(f"\n✨ Ready for next step: LLM annotation!")
                
            else:
                print("❌ Failed to create consolidated JSON")
                return 1
                
        except Exception as e:
            print(f"❌ Error creating consolidated JSON: {str(e)}")
            return 1
    
    print("\n" + "="*70)
    print("✅ PIPELINE COMPLETE")
    print("="*70)
    
    # Print next steps
    if args.consolidate:
        consolidated_file = args.consolidated_output or "data/processed/nougat_parsed/all_questions_consolidated.json"
        print(f"\n📋 Next Steps:")
        print(f"   1. Review {consolidated_file}")
        print(f"   2. Spot-check 20-30 random questions")
        print(f"   3. Run LLM annotation: python run_llm_annotation.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
