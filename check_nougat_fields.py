import json

# Check what's in the 02_structured_questions.json
with open("extraction_output/JEE Main 2024 (01 Feb Shift 1) Previous Year Paper with Answer Keys - MathonGo/02_structured_questions.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Sample question from 02_structured_questions.json:")
print("=" * 100)

if data.get("questions"):
    q = data["questions"][0]
    print(f"\nQuestion ID: {q.get('question_id')}")
    print(f"\nquestion_text field:")
    print(q.get("question_text", "MISSING")[:200])
    print(f"\n\nquestion_latex field:")
    print(q.get("question_latex", "MISSING")[:200] if q.get("question_latex") else "NONE/NULL")
    
    # Check if LaTeX data exists somewhere else
    print(f"\n\nAll keys in question object:")
    for key in sorted(q.keys()):
        val = q[key]
        if isinstance(val, str):
            print(f"  {key}: {str(val)[:100]}...")
        elif isinstance(val, list):
            print(f"  {key}: LIST ({len(val)} items)")
        else:
            print(f"  {key}: {str(val)[:100]}")
