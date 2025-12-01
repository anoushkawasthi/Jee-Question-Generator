"""Simple text-only question parser for JEE papers.

This parser works directly on the PyMuPDF `text_blocks` structure from
`01_text_images_extraction.json` and extracts only:
- question number
- plain question text (no images / LaTeX reconstruction)
- up to 4 options in numbered format

It is intentionally conservative: if patterns don't look right,
we skip that question rather than guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple


@dataclass
class SimpleQuestion:
    paper_id: str
    question_number: int
    question_text: str
    options: List[str]
    page_start: int
    page_end: int

    def to_dict(self) -> Dict:
        return asdict(self)


class SimpleTextQuestionParser:
    """Parse text-only questions from PyMuPDF text_blocks.

    Assumptions (based on `01_text_images_extraction.json` structure):
    - Question starts with a block whose text looks like `Q1.`, `Q1`, `Q. 1`.
    - Subsequent blocks on same / following lines belong to that question
      until the next question marker.
    - Options appear as `(1)`, `(2)`, `(3)`, `(4)` or `1)`, `2)`, ... at the
      beginning of a span, followed by option text.
    - We do not try to reconstruct inline equations; any weird unicode
      characters are left as-is for now.
    """

    # e.g., "Q1.", "Q1", "Q. 1"
    QUESTION_START_RE = re.compile(r"^Q\s*\.?\s*(\d+)\s*[).:-]?$")

    # Option markers variants at start of a span
    # (1) text, 1) text, (1)text, 1.text
    OPTION_RE = re.compile(r"^\s*(?:\((\d)\)|(?:(\d)[).]))\s*(.*)$")

    def __init__(self, paper_id: str) -> None:
        self.paper_id = paper_id

    def parse(self, text_blocks: List[Dict]) -> List[SimpleQuestion]:
        questions: List[SimpleQuestion] = []

        current_qnum: Optional[int] = None
        current_qtext_parts: List[str] = []
        current_options: Dict[int, str] = {}
        current_pages: List[int] = []

        def split_stem_and_options(full_text: str) -> Tuple[str, List[str]]:
            """Heuristically split question stem and 4 inline options.

            We look for a colon or question mark as the end of the stem,
            then try to cut the tail into 4 reasonably balanced chunks.
            If anything looks off, we return (full_text, []).
            """
            text = " ".join(part.strip() for part in full_text.split())
            if not text:
                return "", []

            # Find last strong punctuation that likely ends the stem
            last_colon = text.rfind(":")
            last_q = text.rfind("?")
            cut_idx = max(last_colon, last_q)

            if cut_idx == -1 or cut_idx > len(text) - 10:
                # No clear separation point or colon/question too close to end
                return text, []

            stem = text[: cut_idx + 1].strip()
            tail = text[cut_idx + 1 :].strip()
            if not tail:
                return text, []

            # Split tail into tokens and try to form 4 contiguous chunks
            tokens = tail.split()
            if len(tokens) < 4:
                # Too few tokens to host 4 options
                return text, []

            n = len(tokens)
            base = n // 4
            rem = n % 4
            sizes = []
            for i in range(4):
                sizes.append(base + (1 if i < rem else 0))

            options: List[str] = []
            idx = 0
            for size in sizes:
                if size <= 0:
                    continue
                chunk = " ".join(tokens[idx : idx + size]).strip()
                idx += size
                if chunk:
                    options.append(chunk)

            # Only accept if we got exactly 4 non-empty options
            if len(options) != 4:
                return text, []

            return stem, options

        def flush_current():
            nonlocal current_qnum, current_qtext_parts, current_options, current_pages
            if current_qnum is None:
                return
            question_text_raw = " ".join(
                part.strip() for part in current_qtext_parts if part.strip()
            ).strip()
            if not question_text_raw:
                # nothing meaningful captured
                current_qnum = None
                current_qtext_parts = []
                current_options = {}
                current_pages = []
                return

            # If explicit numbered options were captured via OPTION_RE, prefer those.
            if current_options:
                question_text = question_text_raw
                options_list: List[str] = []
                for i in range(1, 5):
                    opt = current_options.get(i)
                    if opt:
                        options_list.append(opt.strip())
            else:
                # Try to heuristically split inline options from the tail
                stem, inferred_opts = split_stem_and_options(question_text_raw)
                question_text = stem
                options_list = inferred_opts

            # If we still have no stem, drop this question
            if not question_text:
                current_qnum = None
                current_qtext_parts = []
                current_options = {}
                current_pages = []
                return

            q = SimpleQuestion(
                paper_id=self.paper_id,
                question_number=current_qnum,
                question_text=question_text,
                options=options_list,
                page_start=min(current_pages) if current_pages else -1,
                page_end=max(current_pages) if current_pages else -1,
            )
            questions.append(q)

            # reset
            current_qnum = None
            current_qtext_parts = []
            current_options = {}
            current_pages = []


class MarkerBasedQuestionParser:
            """Parse questions and options using explicit (1)..(4) markers.

            This parser:
            - Flattens text_blocks preserving their original order.
            - Detects question starts like "Q1", "Q1.", etc.
            - Detects marker-only blocks "(1)", "(2)", "(3)", "(4)".
            - For each question, uses the markers to carve out 4 option texts.
            - Falls back to inline option extraction if markers not found.
            """

            QUESTION_START_RE = SimpleTextQuestionParser.QUESTION_START_RE

            # Pattern to find inline options like "(1) text (2) text (3) text (4) text"
            INLINE_OPTION_PATTERN = re.compile(r"\(([1-4])\)\s*")

            def __init__(self, paper_id: str) -> None:
                self.paper_id = paper_id

            def _try_extract_inline_options(self, text: str) -> Tuple[str, List[str]]:
                """Try to extract options embedded inline in the text.

                For questions like Q39 where options appear as:
                "(1) Both Statement I and II... (2) Statement I is correct..."

                Returns (stem, [opt1, opt2, opt3, opt4]) or (text, []) if not found.
                """
                # Find all (1), (2), (3), (4) positions
                matches = list(self.INLINE_OPTION_PATTERN.finditer(text))

                # Check if we have all 4 option markers
                marker_nums = [int(m.group(1)) for m in matches]
                if sorted(set(marker_nums)) != [1, 2, 3, 4]:
                    return text, []

                # Get positions for each marker (first occurrence of each)
                marker_positions: Dict[int, int] = {}
                for m in matches:
                    num = int(m.group(1))
                    if num not in marker_positions:
                        marker_positions[num] = m.start()

                # Ensure we have all 4
                if len(marker_positions) != 4:
                    return text, []

                # Sort by position
                ordered = sorted(marker_positions.items(), key=lambda x: x[1])

                # The stem is everything before the first marker
                first_pos = ordered[0][1]
                stem = text[:first_pos].strip()

                # Extract each option
                options: List[str] = []
                for i, (num, pos) in enumerate(ordered):
                    # Find where this option's text starts (after "(N) ")
                    match_obj = self.INLINE_OPTION_PATTERN.match(text[pos:])
                    if not match_obj:
                        return text, []
                    start = pos + match_obj.end()

                    # Find where this option ends (start of next marker or end of text)
                    if i + 1 < len(ordered):
                        end = ordered[i + 1][1]
                    else:
                        end = len(text)

                    opt_text = text[start:end].strip()
                    options.append(opt_text)

                # Reorder options by marker number (1, 2, 3, 4)
                ordered_by_num = sorted(zip([o[0] for o in ordered], options), key=lambda x: x[0])
                final_options = [opt for _, opt in ordered_by_num]

                return stem, final_options

            def parse(self, text_blocks: List[Dict]) -> List[SimpleQuestion]:
                flat: List[Dict] = []
                for idx, block in enumerate(text_blocks):
                    page = block.get("page")
                    text_obj = block.get("text", {})
                    if isinstance(text_obj, dict):
                        txt = str(text_obj.get("text", ""))
                    else:
                        txt = str(text_obj or "")
                    txt = txt.strip()
                    flat.append({"idx": idx, "page": page, "text": txt})

                # Locate questions and markers
                questions_meta: List[Dict] = []
                markers: List[Dict] = []

                for entry in flat:
                    txt = entry["text"]
                    m_q = self.QUESTION_START_RE.match(txt)
                    if m_q:
                        questions_meta.append({
                            "qnum": int(m_q.group(1)),
                            "start_idx": entry["idx"],
                            "page": entry["page"],
                        })
                        continue

                    if txt in {"(1)", "(2)", "(3)", "(4)"}:
                        markers.append({
                            "marker": int(txt[1]),
                            "idx": entry["idx"],
                            "page": entry["page"],
                        })

                questions_meta.sort(key=lambda q: q["start_idx"])

                results: List[SimpleQuestion] = []

                for qi, qmeta in enumerate(questions_meta):
                    qnum = qmeta["qnum"]
                    start_idx = qmeta["start_idx"]
                    end_idx = (
                        questions_meta[qi + 1]["start_idx"] - 1
                        if qi + 1 < len(questions_meta)
                        else len(flat) - 1
                    )

                    range_blocks = [b for b in flat if start_idx < b["idx"] <= end_idx]
                    pages = {b["page"] for b in range_blocks if b["page"] is not None}

                    local_markers = [m for m in markers if start_idx < m["idx"] <= end_idx]
                    local_markers.sort(key=lambda m: m["idx"])

                    first_marker_idx = min((m["idx"] for m in local_markers), default=None)
                    stem_parts: List[str] = []
                    for b in range_blocks:
                        if first_marker_idx is not None and b["idx"] >= first_marker_idx:
                            break
                        if b["text"]:
                            stem_parts.append(b["text"])

                    stem_text = " ".join(p.strip() for p in stem_parts if p.strip()).strip()

                    options: List[str] = []
                    if local_markers:
                        marker_positions = {m["marker"]: m["idx"] for m in local_markers}
                        # Require full set 1..4 for MCQs
                        if all(k in marker_positions for k in range(1, 5)):
                            ordered = sorted(
                                ((k, marker_positions[k]) for k in range(1, 5)),
                                key=lambda x: x[1],
                            )
                            for mi, (k, midx) in enumerate(ordered):
                                next_idx = (
                                    ordered[mi + 1][1]
                                    if mi + 1 < len(ordered)
                                    else end_idx + 1
                                )
                                body_parts: List[str] = []
                                for b in range_blocks:
                                    if midx < b["idx"] < next_idx and b["text"] not in {"(1)", "(2)", "(3)", "(4)"}:
                                        if b["text"]:
                                            body_parts.append(b["text"])
                                opt_text = " ".join(p.strip() for p in body_parts if p.strip()).strip()
                                options.append(opt_text)

                    # If no marker-based options found, try parsing inline options from stem
                    if not options:
                        stem_text, options = self._try_extract_inline_options(stem_text)

                    if not stem_text:
                        continue

                    q = SimpleQuestion(
                        paper_id=self.paper_id,
                        question_number=qnum,
                        question_text=stem_text,
                        options=options,
                        page_start=min(pages) if pages else -1,
                        page_end=max(pages) if pages else -1,
                    )
                    results.append(q)

                return results
