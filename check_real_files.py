import json

print("=" * 80)
print("CHECKING: data/processed/jee_questions_final_consolidated.json")
print("=" * 80)

try:
    with open('data/processed/jee_questions_final_consolidated.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f'\nKeys in file: {list(data.keys())}')
        
        if 'questions' in data:
            print(f'Number of questions: {len(data["questions"])}')
            if len(data['questions']) > 0:
                print(f'\nFirst question:')
                print(json.dumps(data['questions'][0], indent=2, ensure_ascii=False)[:800])
                print("\n...")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 80)
print("CHECKING: data/processed/raw_questions.json")
print("=" * 80)

try:
    with open('data/processed/raw_questions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f'\nKeys in file: {list(data.keys())}')
        
        if isinstance(data, list):
            print(f'Number of items (array): {len(data)}')
            if len(data) > 0:
                print(f'\nFirst item:')
                print(json.dumps(data[0], indent=2, ensure_ascii=False)[:800])
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    print(f'{key}: {len(value)} items')
                else:
                    print(f'{key}: {str(value)[:100]}')
except Exception as e:
    print(f"ERROR: {e}")
