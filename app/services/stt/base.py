from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    transcript: str
    confidence: float | None = None
    debug: dict | None = None


class STTProviderError(Exception):
    pass


class STTProvider:
    async def transcribe(self, wav_path: str) -> TranscriptionResult:
        raise NotImplementedError
