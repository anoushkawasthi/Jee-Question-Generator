"""
Create final consolidated JSON from Nougat extraction
"""
import json
import shutil

# Load the working Phase 1 Nougat output
with open('data/processed/nougat_parsed/all_questions_consolidated.json') as f:
    data = json.load(f)

# Copy it to the root as the final consolidated JSON
shutil.copy('data/processed/nougat_parsed/all_questions_consolidated.json', 'FINAL_CONSOLIDATED_QUESTIONS.json')

print('✅ Final Consolidated JSON Created: FINAL_CONSOLIDATED_QUESTIONS.json')
total_qs = len(data['questions'])
total_papers = data['metadata'].get('total_papers', 'N/A')
data_quality = data['metadata'].get('verification_stats', {}).get('data_quality', 'N/A')
file_size = len(json.dumps(data))/1024/1024

print(f'📊 Total Questions: {total_qs}')
print(f'📋 Total Papers: {total_papers}')
print(f'✅ Data Quality: {data_quality}')
print(f'📁 File Size: {file_size:.2f} MB')
