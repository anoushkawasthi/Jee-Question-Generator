import json
from pathlib import Path

p = Path("extraction_output") / "JEE Main 2024 (01 Feb Shift 1) Previous Year Paper with Answer Keys - MathonGo" / "01_text_images_extraction.json"
data = json.loads(p.read_text(encoding="utf-8"))
hits = []
for b in data.get("text_blocks", []):
    t = b.get("text", {})
    txt = t.get("text") if isinstance(t, dict) else str(t)
    if "(1" in txt or "(2" in txt or "(3" in txt or "(4" in txt:
        hits.append(txt)
print("Found", len(hits), "blocks with explicit option markers.")
for h in hits[:10]:
    print(">>", h)