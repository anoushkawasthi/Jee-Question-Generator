import json
import os

filepath = 'data/processed/nougat_parsed/all_questions_consolidated.json'

# Check file size
file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
print(f"File size: {file_size_mb:.2f} MB")

# Load and count
with open(filepath, 'r', encoding='utf-8') as f:
    data = json.load(f)

actual_count = len(data['questions'])
metadata_count = data['metadata']['total_questions']
with_answers = data['metadata']['verification_stats']['questions_with_answers']
without_answers = data['metadata']['verification_stats']['questions_missing_answers']
quality = data['metadata']['verification_stats']['data_quality']

print(f"\n📊 ACTUAL COUNT: {actual_count} questions in array")
print(f"📋 METADATA CLAIM: {metadata_count} total questions")
print(f"✅ With answers: {with_answers}")
print(f"❌ Without answers: {without_answers}")
print(f"📈 Data quality: {quality}")

# Show sample
if actual_count > 0:
    print(f"\n✅ First question ID: {data['questions'][0]['question_id']}")
    print(f"✅ Last question ID: {data['questions'][-1]['question_id']}")
else:
    print("❌ NO QUESTIONS FOUND!")
