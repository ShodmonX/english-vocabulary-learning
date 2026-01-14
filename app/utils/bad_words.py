from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

_BAD_WORDS_PATH = Path(__file__).resolve().parents[1] / "data" / "bad_words.txt"
_NON_ALNUM = re.compile(r"[^\w]+", flags=re.UNICODE)


def _normalize(text: str) -> str:
    cleaned = _NON_ALNUM.sub(" ", text.casefold()).strip()
    return f" {cleaned} " if cleaned else ""


@lru_cache(maxsize=1)
def _bad_phrases() -> list[str]:
    if not _BAD_WORDS_PATH.exists():
        return []
    lines = _BAD_WORDS_PATH.read_text(encoding="utf-8").splitlines()
    phrases = []
    for line in lines:
        normalized = _normalize(line)
        if normalized:
            phrases.append(normalized)
    return phrases


def contains_bad_words(text: str) -> bool:
    normalized = _normalize(text)
    if not normalized:
        return False
    for phrase in _bad_phrases():
        if phrase in normalized:
            return True
    return False
