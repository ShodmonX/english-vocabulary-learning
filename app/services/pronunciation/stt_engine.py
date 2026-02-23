from __future__ import annotations

from app.services.pronunciation.base import AssessmentResult, PronunciationEngine
from app.services.pronunciation.matching import match_transcript
from app.services.stt.base import STTProvider


class STTPronunciationEngine(PronunciationEngine):
    def __init__(self, provider: STTProvider) -> None:
        self.provider = provider

    @staticmethod
    def _extract_provider_score(debug: dict | None) -> float | None:
        if not isinstance(debug, dict):
            return None
        pa = debug.get("pronunciation_assessment")
        if not isinstance(pa, dict):
            return None
        raw = pa.get("pron_score")
        if isinstance(raw, (int, float)):
            return float(raw) / 100.0
        return None

    async def assess(self, audio_wav_path: str, reference_text: str) -> AssessmentResult:
        result = await self.provider.transcribe(
            audio_wav_path,
            reference_text=reference_text,
        )
        provider_score = self._extract_provider_score(result.debug)
        if provider_score is not None:
            score = max(0.0, min(1.0, provider_score))
            if score >= 0.85:
                verdict = "correct"
            elif score >= 0.70:
                verdict = "close"
            else:
                verdict = "wrong"
        else:
            verdict, score = match_transcript(reference_text, result.transcript)
        return AssessmentResult(
            transcript=result.transcript,
            verdict=verdict,
            score=score,
            debug=result.debug,
        )
