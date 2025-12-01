#!/usr/bin/env python3
"""
Validation script for Nougat POC output.
Compares Nougat .mmd output with PyMuPDF extraction quality.
"""

import json
import re
from pathlib import Path

def check_nougat_output():
    """Check if Nougat .mmd file was created"""
    output_dir = Path("test_nougat/output")
    mmd_files = list(output_dir.glob("*.mmd"))
    
    if not mmd_files:
        print("❌ NO .mmd FILE CREATED")
        print(f"   Output directory: {output_dir}")
        print(f"   Files found: {list(output_dir.iterdir())}")
        return False
    
    print(f"✅ .mmd FILE CREATED: {mmd_files[0].name}")
    return mmd_files[0]

def analyze_mmd_quality(mmd_file):
    """Analyze quality of Nougat output"""
    with open(mmd_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n📄 FILE SIZE: {len(content):,} characters")
    print(f"📑 PAGES/SECTIONS: {content.count('# ')}")
    
    # Check for LaTeX preservation
    latex_count = content.count('$')
    print(f"\n🔬 LATEX INDICATORS:")
    print(f"   $ symbols: {latex_count} (should be many for math formulas)")
    
    # Extract first few LaTeX formulas
    latex_patterns = re.findall(r'\$[^$]+\$', content)
    if latex_patterns:
        print(f"   Found {len(latex_patterns)} LaTeX blocks")
        print(f"   Sample formulas:")
        for formula in latex_patterns[:3]:
            print(f"      - {formula[:60]}...")
    else:
        print("   ⚠️  NO LaTeX formulas found - might be garbled like PyMuPDF")
    
    # Check for question structure
    question_markers = content.count('**Q')
    print(f"\n❓ QUESTION MARKERS: {question_markers} (should match question count)")
    
    # Check for garbled math (Unicode artifacts)
    garbled_patterns = [
        ('sin −12𝑔𝑇', 'Garbled sine formula'),
        ('𝑅', 'Garbled R symbol'),
        ('−', 'Garbled minus sign'),
    ]
    
    print(f"\n⚠️  GARBLE DETECTION:")
    has_garble = False
    for pattern, desc in garbled_patterns:
        if pattern in content:
            print(f"   ❌ Found: {desc} - {pattern}")
            has_garble = True
    
    if not has_garble:
        print(f"   ✅ No obvious garbled Unicode artifacts detected")
    
    return content, len(latex_patterns)

def compare_with_pymupdf():
    """Compare with PyMuPDF extraction"""
    pymupdf_path = Path("extraction_output/JEE Main 2024 (01 Feb Shift 1) Previous Year Paper with Answer Keys - MathonGo/02_structured_questions.json")
    
    if pymupdf_path.exists():
        with open(pymupdf_path, 'r', encoding='utf-8') as f:
            pymupdf_data = json.load(f)
        
        print(f"\n📊 COMPARISON WITH PyMuPDF:")
        print(f"   PyMuPDF questions: {len(pymupdf_data.get('questions', []))}")
        
        # Check first question from PyMuPDF
        if pymupdf_data.get('questions'):
            first_q = pymupdf_data['questions'][0].get('question_text', '')
            if '𝑔' in first_q or '−' in first_q or '𝑅' in first_q:
                print(f"   PyMuPDF has garbled math: YES ❌")
            else:
                print(f"   PyMuPDF has garbled math: NO")
    else:
        print(f"\n📊 PyMuPDF comparison file not found")

def print_sample_questions(mmd_file):
    """Print sample questions from .mmd"""
    with open(mmd_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract first question
    question_block = re.search(r'## (Q\d+.*?)(?=## Q|\Z)', content, re.DOTALL)
    
    if question_block:
        print(f"\n📋 SAMPLE QUESTION:")
        print("=" * 70)
        sample = question_block.group(1)[:500]
        print(sample)
        if len(question_block.group(1)) > 500:
            print("...")
        print("=" * 70)

def main():
    print("🧪 NOUGAT POC VALIDATION")
    print("=" * 70)
    
    mmd_file = check_nougat_output()
    if not mmd_file:
        print("\n⛔ Validation failed: No .mmd file generated")
        return False
    
    content, latex_count = analyze_mmd_quality(mmd_file)
    print_sample_questions(mmd_file)
    compare_with_pymupdf()
    
    print("\n" + "=" * 70)
    print("📊 VERDICT:")
    
    if latex_count > 50:
        print(f"✅ NOUGAT LOOKS GOOD - {latex_count} LaTeX blocks found")
        print("   → Proceed with batch processing all 30 PDFs")
        return True
    elif latex_count > 10:
        print(f"⚠️  NOUGAT PARTIAL - {latex_count} LaTeX blocks (expected ~100+)")
        print("   → May need investigation")
        return None
    else:
        print(f"❌ NOUGAT FAILED - Only {latex_count} LaTeX blocks found")
        print("   → Similar issue to PyMuPDF, do not proceed with batch")
        return False

if __name__ == "__main__":
    main()
