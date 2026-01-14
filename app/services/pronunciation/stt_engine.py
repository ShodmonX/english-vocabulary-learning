from __future__ import annotations

from app.services.pronunciation.base import AssessmentResult, PronunciationEngine
from app.services.pronunciation.matching import match_transcript
from app.services.stt.base import STTProvider


class STTPronunciationEngine(PronunciationEngine):
    def __init__(self, provider: STTProvider) -> None:
        self.provider = provider

    async def assess(self, audio_wav_path: str, reference_text: str) -> AssessmentResult:
        result = await self.provider.transcribe(audio_wav_path)
        verdict, score = match_transcript(reference_text, result.transcript)
        return AssessmentResult(
            transcript=result.transcript,
            verdict=verdict,
            score=score,
            debug=result.debug,
        )
