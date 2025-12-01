"""Text normalization utilities for cleaning extracted JEE questions.

Goals (conservative):
- Fix spacing around decimals: ``0 . 30   m`` -> ``0.30 m``.
- Normalize common Unicode minus/variables: ``𝑔`` -> ``g``, ``𝑇`` -> ``T``.
- Normalize Unicode minus sign ``−`` to ``-``.

We deliberately avoid aggressive math rewriting here; the goal is
human-readable, consistent text that still preserves the original
meaning as extracted.
"""

from __future__ import annotations

import re
from typing import List


_UNICODE_REPLACEMENTS = {
    "−": "-",  # minus sign
    "𝑔": "g",
    "𝑇": "T",
    "𝑅": "R",
    "𝜃": "θ",
    "𝜋": "π",
    "𝐿": "L",
    "𝑀": "M",
    "𝑡": "t",
}


def _normalize_unicode(text: str) -> str:
    for src, dst in _UNICODE_REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text


_DECIMAL_PATTERN = re.compile(r"(\d)\s*\.\s*(\d)")
_PERCENT_PATTERN = re.compile(r"(\d(?:\.\d+)?)\s*%")

# Very narrow fraction pattern: "2 9 m" -> "2/9 m" (and similar single-
# digit-over-single-digit cases) to make obviously fractional quantities
# unambiguous for LLMs. We support a small whitelist of common units.
_FRACTION_BEFORE_UNIT_PATTERN = re.compile(r"\b([1-9])\s+([1-9])\s+(m|R|N|J|kg|L|C|V|A|T|H|F)\b")

# Standalone fractions at end of text or before certain punctuation:
# "1 2" at end -> "1/2", used for options like "(1) 1 2"
_STANDALONE_FRACTION_PATTERN = re.compile(r"\b([1-9]\d?)\s+([1-9]\d?)\b(?=\s*$|\s*[,;:)])")

# Units spacing: "10N" -> "10 N", "0.30m" -> "0.30 m", but avoid
# breaking things like "10 m/s" (keep the slash-attached unit intact).
_UNIT_PATTERN = re.compile(r"(\d(?:\.\d+)?)\s*([A-Za-z](?:[A-Za-z])?)\b")

# Very conservative exponent patterns:
# 1) Powers of 10: "10 -2" -> "10^-2".
_TEN_EXP_PATTERN = re.compile(r"10\s*([-−])\s*(\d+)")
# 2) Unit exponents like "m s -2" -> "m s^-2" (only small negative ints).
_UNIT_EXP_PATTERN = re.compile(r"(m|s|kg|N|J|W|Hz|Pa|C|V|F|Ω|ohm)\s+([-−])\s*(\d+)")

# Scientific notation like "2 × 10 2" or "2 x 10 2".
_SCI_NOTATION_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*[x×]\s*10\s*(?:\^\s*)?(\d+)",
    re.IGNORECASE,
)

# trig/func argument normalization: "sin -20" -> "sin(-20)" (and similarly
# for cos, tan etc.), but do not touch cases already using parentheses.
_FUNC_ARG_PATTERN = re.compile(r"\b(sin|cos|tan|cot|sec|cosec)\s+([-−]?\d+(?:\.\d+)?)")

# Dimensional formula normalization: [M L – 2 T – 1] -> [M L^-2 T^-1]
_DIMENSIONAL_FORMULA_PATTERN = re.compile(r"\[(.*?)\]")

# Punctuation spacing: remove space before , . ; :
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:])")


def _normalize_decimals(text: str) -> str:
    """Collapse spaced decimals like ``0 . 30`` -> ``0.30``.

    We apply this repeatedly until no changes occur to handle
    cases like ``0 . 3 0``.
    """

    prev = None
    cur = text
    while prev != cur:
        prev = cur
        cur = _DECIMAL_PATTERN.sub(r"\1.\2", cur)
    return cur


def _normalize_percents(text: str) -> str:
    """Normalize percentages: ``39.9 %`` -> ``39.9%``."""
    return _PERCENT_PATTERN.sub(r"\1%", text)


def _normalize_units(text: str) -> str:
    """Normalize simple unit spacing: ``10N`` -> ``10 N``.

    We intentionally avoid touching patterns like ``10 m/s`` where the
    slash binds the unit. This is a light cosmetic fix only.
    """

    def repl(match: re.Match[str]) -> str:
        value, unit = match.group(1), match.group(2)
        return f"{value} {unit}"

    return _UNIT_PATTERN.sub(repl, text)


def _normalize_simple_fractions(text: str) -> str:
    """Normalize very simple fractions like ``2 9 m`` -> ``2/9 m``.

    We only touch patterns of the form ``[1-9] [1-9] m`` to avoid
    accidentally changing multi-digit numbers like ``29 m``.
    Also handles standalone fractions like ``1 2`` -> ``1/2``.
    """

    def repl_with_unit(match: re.Match[str]) -> str:
        num, den, unit = match.group(1), match.group(2), match.group(3)
        return f"{num}/{den} {unit}"

    def repl_standalone(match: re.Match[str]) -> str:
        num, den = match.group(1), match.group(2)
        return f"{num}/{den}"

    text = _FRACTION_BEFORE_UNIT_PATTERN.sub(repl_with_unit, text)
    text = _STANDALONE_FRACTION_PATTERN.sub(repl_standalone, text)
    return text


def _normalize_exponents(text: str) -> str:
    """Very conservative exponent normalization.

    - ``10 -2`` -> ``10^-2``
    - ``m s -2`` -> ``m s^-2``
    """

    # Normalize minus variants first so patterns are stable.
    t = text.replace("−", "-")
    # Scientific notation first: 2 x 10 2 -> 2 x 10^2
    t = _SCI_NOTATION_PATTERN.sub(r"\1 x 10^\2", t)
    t = _TEN_EXP_PATTERN.sub(r"10^-\2", t)
    t = _UNIT_EXP_PATTERN.sub(r"\1^-\3", t)
    return t


def _normalize_func_args(text: str) -> str:
    """Normalize simple trig function arguments: ``sin -20`` -> ``sin(-20)``.

    We skip cases where the function is already followed by ``(``.
    """

    def repl(match: re.Match[str]) -> str:
        func, arg = match.group(1), match.group(2)
        return f"{func}({arg})"

    # Avoid touching already parenthesized calls like ``sin(-20)``.
    return _FUNC_ARG_PATTERN.sub(repl, text)


def _normalize_dimensional_formulas(text: str) -> str:
    """Normalize dimensional formulas: [M L – 2 T – 1] -> [M L^-2 T^-1].

    Inside brackets, replace patterns like "symbol space minus space digit"
    with "symbol^-digit".
    """

    def process_bracket(match: re.Match[str]) -> str:
        content = match.group(1)
        # Replace (space)(minus variants)(space)(digit) with ^-digit
        # Pattern: space + (− or -) + space + digit
        normalized = re.sub(r"\s+[−-]\s+(\d+)", r"^-\1", content)
        return f"[{normalized}]"

    return _DIMENSIONAL_FORMULA_PATTERN.sub(process_bracket, text)


_MULTIPLE_SPACES = re.compile(r"\s{2,}")


def _collapse_spaces(text: str) -> str:
    # Keep single spaces, collapse runs of 2+ into one.
    return _MULTIPLE_SPACES.sub(" ", text).strip()


def normalize_text(text: str) -> str:
    """Apply conservative, order-safe normalizations to a string."""
    if not text:
        return text
    out = text
    out = _normalize_unicode(out)
    out = _normalize_decimals(out)
    out = _normalize_units(out)
    out = _normalize_simple_fractions(out)
    out = _normalize_exponents(out)
    out = _normalize_dimensional_formulas(out)
    out = _normalize_func_args(out)
    out = _normalize_percents(out)
    out = _collapse_spaces(out)
    return out


def normalize_question_and_options(question_text: str, options: List[str]) -> tuple[str, List[str]]:
    """Normalize a question stem and its options.

    Returns a new (stem, options) tuple with the same structure.
    """

    stem_norm = normalize_text(question_text)
    opts_norm = [normalize_text(o) for o in options]
    return stem_norm, opts_norm
