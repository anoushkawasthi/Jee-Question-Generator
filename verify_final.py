import json

# Verify final JSON
d = json.load(open('FINAL_CONSOLIDATED_EXTRACTION_COMPLETE.json'))
print('✅ EXTRACTION PIPELINE COMPLETE')
print(f'PDFs Processed: {d["metadata"]["total_papers_processed"]}')
print(f'Questions in Final JSON: {len(d["questions"])}')
print(f'File Status: Valid JSON')
print(f'Estimated Total Questions: {d["metadata"]["extraction_stats"]["total_questions_in_pdfs"]}')
