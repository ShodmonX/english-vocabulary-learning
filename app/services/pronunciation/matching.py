import re

from rapidfuzz import fuzz


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def match_transcript(reference: str, transcript: str) -> tuple[str, float]:
    ref = normalize_text(reference)
    hyp = normalize_text(transcript)
    if not hyp:
        return "wrong", 0.0
    if ref in hyp:
        return "correct", 1.0
    score = fuzz.ratio(ref, hyp) / 100.0
    if score >= 0.88:
        return "correct", score
    if score >= 0.75:
        return "close", score
    return "wrong", score
