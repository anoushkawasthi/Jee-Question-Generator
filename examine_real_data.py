import json
import os

print("=" * 100)
print("FILE 1: jee_questions_final_consolidated.json (2.44 MB)")
print("=" * 100)

with open('data/processed/jee_questions_final_consolidated.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    
    if 'metadata' in data:
        print("\nMetadata:")
        print(json.dumps(data['metadata'], indent=2)[:500])
    
    if 'papers' in data:
        print(f"\nNumber of papers: {len(data['papers'])}")
        if len(data['papers']) > 0:
            first_paper = data['papers'][0]
            print(f"\nFirst paper keys: {list(first_paper.keys())}")
            print(f"First paper data: {json.dumps(first_paper, indent=2, ensure_ascii=False)[:500]}")

print("\n" + "=" * 100)
print("FILE 2: raw_questions.json (0.96 MB)")
print("=" * 100)

with open('data/processed/raw_questions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    print(f"Type: {type(data)}")
    print(f"Length: {len(data) if hasattr(data, '__len__') else 'N/A'}")
    if isinstance(data, list) and len(data) > 0:
        print(f"\nFirst item: {json.dumps(data[0], indent=2, ensure_ascii=False)[:500]}")

print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)

with open('data/processed/jee_questions_final_consolidated.json', 'r', encoding='utf-8') as f:
    data1 = json.load(f)
    papers_count = len(data1.get('papers', []))
    
with open('data/processed/raw_questions.json', 'r', encoding='utf-8') as f:
    data2 = json.load(f)
    raw_count = len(data2) if isinstance(data2, list) else len(data2.get('questions', []))

print(f"✅ Found jee_questions_final_consolidated.json with {papers_count} papers")
print(f"✅ Found raw_questions.json with {raw_count} questions/items")
