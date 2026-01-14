from __future__ import annotations

import asyncio
from functools import lru_cache

from faster_whisper import WhisperModel

from app.config import settings
from app.services.stt.base import STTProvider, STTProviderError, TranscriptionResult


@lru_cache(maxsize=1)
def _get_model() -> WhisperModel:
    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


class LocalWhisperSTT(STTProvider):
    def __init__(self) -> None:
        self.model = _get_model()

    def transcribe_sync(self, wav_path: str) -> TranscriptionResult:
        try:
            segments, info = self.model.transcribe(
                wav_path,
                language="en",
                vad_filter=True,
                beam_size=5,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text for segment in segments).strip()
            return TranscriptionResult(
                transcript=text,
                confidence=getattr(info, "language_probability", None),
                debug={"language": info.language, "language_probability": info.language_probability},
            )
        except Exception as exc:
            raise STTProviderError(str(exc)) from exc

    async def transcribe(self, wav_path: str) -> TranscriptionResult:
        return await asyncio.to_thread(self.transcribe_sync, wav_path)
