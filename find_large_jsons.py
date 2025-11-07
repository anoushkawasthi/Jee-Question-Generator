import os
import json
from pathlib import Path

print("Searching for JSON files larger than 500 KB (likely candidates for full dataset)...\n")

large_jsons = []
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.json'):
            filepath = os.path.join(root, file)
            size = os.path.getsize(filepath)
            if size > 500 * 1024:  # 500 KB
                large_jsons.append((filepath, size / (1024 * 1024)))

if large_jsons:
    large_jsons.sort(key=lambda x: x[1], reverse=True)
    for path, size_mb in large_jsons:
        print(f"{path:<80} {size_mb:>8.2f} MB")
else:
    print("❌ No JSON files > 500 KB found")
    print("\nLet's check what JSON files exist and their sizes:")
    
    jsons = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.json'):
                filepath = os.path.join(root, file)
                size = os.path.getsize(filepath)
                jsons.append((filepath, size / 1024))
    
    jsons.sort(key=lambda x: x[1], reverse=True)
    print("\nTop 15 JSON files by size:")
    for path, size_kb in jsons[:15]:
        print(f"{path:<80} {size_kb:>8.2f} KB")
