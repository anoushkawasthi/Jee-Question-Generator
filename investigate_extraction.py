import json
import os
from pathlib import Path

print("=" * 100)
print("INVESTIGATING EXTRACTION PIPELINE OUTPUT QUALITY")
print("=" * 100)

# Check one paper's extraction
sample_paper_dir = "extraction_output/JEE Main 2024 (01 Feb Shift 1) Previous Year Paper with Answer Keys - MathonGo"

if os.path.exists(sample_paper_dir):
    print(f"\n📁 Checking: {sample_paper_dir}\n")
    
    # List all JSON files in the directory
    json_files = [f for f in os.listdir(sample_paper_dir) if f.endswith('.json')]
    print(f"JSON files found: {json_files}\n")
    
    for json_file in json_files:
        filepath = os.path.join(sample_paper_dir, json_file)
        size_kb = os.path.getsize(filepath) / 1024
        
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                print(f"\n📄 {json_file} ({size_kb:.1f} KB)")
                print(f"   Keys: {list(data.keys())}")
                
                # Check for Nougat markers
                has_latex = False
                has_markdown = False
                
                if isinstance(data, dict):
                    content = json.dumps(data, ensure_ascii=False)
                    if 'latex' in content.lower() or '$' in content:
                        has_latex = True
                    if '```' in content or '#' in content:
                        has_markdown = True
                
                print(f"   Has LaTeX markers: {has_latex}")
                print(f"   Has Markdown markers: {has_markdown}")
                print(f"   Nougat output: {'✅ YES' if (has_latex or has_markdown) else '❌ NO'}")
                
            except Exception as e:
                print(f"   ERROR reading: {e}")
else:
    print(f"❌ Directory not found: {sample_paper_dir}")

print("\n" + "=" * 100)
print("CHECKING: Was Nougat ever successfully used?")
print("=" * 100)

# Search for any Nougat markers in entire extraction_output
latex_count = 0
markdown_count = 0
pymupdf_only_count = 0

if os.path.exists("extraction_output"):
    for root, dirs, files in os.walk("extraction_output"):
        for file in files:
            if file.endswith('.json'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        content = json.dumps(data, ensure_ascii=False)
                        
                        if '$' in content or '$$' in content or '\\latex' in content:
                            latex_count += 1
                        elif '```' in content or '#' in content:
                            markdown_count += 1
                        else:
                            pymupdf_only_count += 1
                except:
                    pass

print(f"\nJSON files with LaTeX markers: {latex_count}")
print(f"JSON files with Markdown markers: {markdown_count}")
print(f"JSON files with PyMuPDF-only (no Nougat): {pymupdf_only_count}")
print(f"\n⚠️  Nougat Conversion Result: {'✅ Used' if (latex_count + markdown_count) > 0 else '❌ FAILED - Nougat was never successfully run'}")
