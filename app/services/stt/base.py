from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    transcript: str
    confidence: float | None = None
    debug: dict | None = None


class STTProviderError(Exception):
    def __init__(self, message: str, *, user_message: str | None = None) -> None:
        super().__init__(message)
        self.user_message = user_message


class STTProvider:
    async def transcribe(self, wav_path: str) -> TranscriptionResult:
        raise NotImplementedError
