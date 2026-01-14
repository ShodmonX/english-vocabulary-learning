from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass
class AssessmentResult:
    transcript: str
    verdict: Literal["correct", "close", "wrong"]
    score: float
    debug: dict | None = None


class PronunciationEngine(Protocol):
    async def assess(self, audio_wav_path: str, reference_text: str) -> AssessmentResult:
        ...
