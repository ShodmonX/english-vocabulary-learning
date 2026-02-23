from __future__ import annotations

import asyncio
import base64
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.services.i18n import t
from app.services.stt.base import STTProvider, STTProviderError, TranscriptionResult

logger = logging.getLogger("stt.azure")

_RATE_LIMIT_MESSAGE = t("stt.unavailable")
_OVERLOAD_MESSAGE = _RATE_LIMIT_MESSAGE
_CONCURRENCY_SEMAPHORE = asyncio.Semaphore(settings.stt_max_concurrency)


async def _acquire_slot() -> bool:
    if settings.stt_overload_mode == "failfast":
        if _CONCURRENCY_SEMAPHORE.locked():
            return False
        await _CONCURRENCY_SEMAPHORE.acquire()
        return True
    try:
        await asyncio.wait_for(
            _CONCURRENCY_SEMAPHORE.acquire(),
            timeout=float(settings.stt_queue_max_wait_seconds),
        )
        return True
    except asyncio.TimeoutError:
        return False


def _extract_request_id(response: httpx.Response | None) -> str | None:
    if not response:
        return None
    return response.headers.get("x-requestid") or response.headers.get("x-request-id")


def _resolve_region(region: str | None, endpoint: str | None) -> str | None:
    if region and region.strip():
        return region.strip().lower()
    if not endpoint:
        return None
    parsed = urlparse(endpoint)
    host = (parsed.hostname or "").lower()
    if host.endswith(".api.cognitive.microsoft.com"):
        return host.split(".", 1)[0]
    if host.endswith(".stt.speech.microsoft.com"):
        return host.split(".", 1)[0]
    return None


class AzureSpeechSTT(STTProvider):
    def __init__(self) -> None:
        self.api_key = (settings.azure_speech_key or "").strip()
        self.language = (settings.azure_speech_language or "en-US").strip()
        self.timeout_seconds = float(settings.azure_speech_timeout_seconds)
        region = _resolve_region(settings.azure_speech_region, settings.azure_speech_endpoint)
        self.region = region or ""
        raw_endpoint = (settings.azure_speech_endpoint or "").strip().rstrip("/")
        if not self.api_key:
            raise STTProviderError("AZURE_SPEECH_KEY is not configured", user_message=_RATE_LIMIT_MESSAGE)
        if not self.region:
            raise STTProviderError(
                "AZURE_SPEECH_REGION is not configured",
                user_message=_RATE_LIMIT_MESSAGE,
            )
        if raw_endpoint and ".stt.speech.microsoft.com" in raw_endpoint:
            self.endpoint = f"{raw_endpoint}/speech/recognition/conversation/cognitiveservices/v1"
        else:
            self.endpoint = (
                f"https://{self.region}.stt.speech.microsoft.com/"
                "speech/recognition/conversation/cognitiveservices/v1"
            )

    async def transcribe(
        self,
        wav_path: str,
        *,
        reference_text: str | None = None,
    ) -> TranscriptionResult:
        acquired = await _acquire_slot()
        if not acquired:
            logger.warning(
                "Azure STT overload mode=%s max_concurrency=%s queue_wait=%ss",
                settings.stt_overload_mode,
                settings.stt_max_concurrency,
                settings.stt_queue_max_wait_seconds,
            )
            raise STTProviderError("STT concurrency limit reached", user_message=_OVERLOAD_MESSAGE)
        try:
            return await self._transcribe_once(wav_path, reference_text=reference_text)
        finally:
            _CONCURRENCY_SEMAPHORE.release()

    def _build_pron_assessment_header(self, reference_text: str) -> str:
        payload: dict[str, str] = {
            "ReferenceText": reference_text,
            "GradingSystem": "HundredMark",
            "Granularity": "Phoneme",
            "Dimension": "Comprehensive",
            "EnableMiscue": "True",
        }
        if self.language.lower() == "en-us":
            payload["EnableProsodyAssessment"] = "True"
        encoded = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        return encoded.decode("utf-8")

    def _parse_pronunciation_assessment(self, payload: dict) -> dict | None:
        nbest = payload.get("NBest")
        if not isinstance(nbest, list) or not nbest:
            return None
        first = nbest[0]
        if not isinstance(first, dict):
            return None

        def _num(value: object) -> float | None:
            if isinstance(value, (int, float)):
                return float(value)
            return None

        words_raw = first.get("Words")
        words: list[dict[str, object]] = []
        weak_phonemes: list[dict[str, object]] = []
        if isinstance(words_raw, list):
            for item in words_raw:
                if not isinstance(item, dict):
                    continue
                word = str(item.get("Word") or "").strip()
                word_acc = _num(item.get("AccuracyScore"))
                err = str(item.get("ErrorType") or "").strip()
                if word:
                    words.append(
                        {
                            "word": word,
                            "accuracy_score": word_acc,
                            "error_type": err,
                        }
                    )
                phonemes = item.get("Phonemes")
                if isinstance(phonemes, list):
                    for ph in phonemes:
                        if not isinstance(ph, dict):
                            continue
                        symbol = str(ph.get("Phoneme") or "").strip()
                        acc = _num(ph.get("AccuracyScore"))
                        if not symbol or acc is None:
                            continue
                        if acc < 80:
                            weak_phonemes.append({"phoneme": symbol, "accuracy_score": acc})

        weak_phonemes.sort(key=lambda x: float(x.get("accuracy_score") or 0.0))
        seen_symbols: set[str] = set()
        uniq_weak: list[dict[str, object]] = []
        for item in weak_phonemes:
            symbol = str(item.get("phoneme") or "")
            if symbol in seen_symbols:
                continue
            seen_symbols.add(symbol)
            uniq_weak.append(item)
            if len(uniq_weak) >= 6:
                break

        result = {
            "pron_score": _num(first.get("PronScore")),
            "accuracy_score": _num(first.get("AccuracyScore")),
            "fluency_score": _num(first.get("FluencyScore")),
            "completeness_score": _num(first.get("CompletenessScore")),
            "prosody_score": _num(first.get("ProsodyScore")),
            "words": words[:8],
            "weak_phonemes": uniq_weak,
        }
        if all(
            result.get(key) is None
            for key in (
                "pron_score",
                "accuracy_score",
                "fluency_score",
                "completeness_score",
                "prosody_score",
            )
        ) and not result["words"] and not result["weak_phonemes"]:
            return None
        return result

    async def _transcribe_once(
        self,
        wav_path: str,
        *,
        reference_text: str | None = None,
    ) -> TranscriptionResult:
        audio = Path(wav_path).read_bytes()
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Ocp-Apim-Subscription-Region": self.region,
            "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
            "Accept": "application/json",
        }
        ref_text = (reference_text or "").strip()
        if ref_text:
            headers["Pronunciation-Assessment"] = self._build_pron_assessment_header(ref_text)
        params = {"language": self.language, "format": "detailed"}
        timeout = httpx.Timeout(self.timeout_seconds, connect=5.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    params=params,
                    content=audio,
                )
        except httpx.RequestError as exc:
            logger.warning("Azure STT request error: %s", exc)
            raise STTProviderError(str(exc), user_message=_RATE_LIMIT_MESSAGE) from exc

        request_id = _extract_request_id(response)
        logger.info(
            "Azure STT request status=%s request_id=%s",
            response.status_code,
            request_id,
        )

        if response.status_code >= 400:
            message = response.text
            logger.warning(
                "Azure STT error status=%s request_id=%s body=%s",
                response.status_code,
                request_id,
                message,
            )
            if response.status_code in {401, 403, 408, 429, 500, 502, 503, 504}:
                raise STTProviderError(message, user_message=_RATE_LIMIT_MESSAGE)
            raise STTProviderError(message)

        payload = response.json()
        status = str(payload.get("RecognitionStatus") or "")
        transcript = ""
        if status.lower() == "success":
            transcript = str(payload.get("DisplayText") or "").strip()
            if not transcript:
                nbest = payload.get("NBest")
                if isinstance(nbest, list) and nbest:
                    first = nbest[0]
                    if isinstance(first, dict):
                        transcript = str(first.get("Display") or first.get("Lexical") or "").strip()
        elif status.lower() in {"nomatch", "initialsilencetimeout", "babbletimeout"}:
            transcript = ""
        else:
            logger.warning(
                "Azure STT unexpected recognition status=%s request_id=%s payload=%s",
                status,
                request_id,
                payload,
            )
            transcript = str(payload.get("DisplayText") or "").strip()

        confidence = None
        nbest = payload.get("NBest")
        if isinstance(nbest, list) and nbest:
            first = nbest[0]
            if isinstance(first, dict):
                raw_conf = first.get("Confidence")
                if isinstance(raw_conf, (float, int)):
                    confidence = float(raw_conf)

        pron = self._parse_pronunciation_assessment(payload)
        debug: dict[str, object] = {"provider_request_id": request_id, "status": status}
        if pron:
            debug["pronunciation_assessment"] = pron

        return TranscriptionResult(
            transcript=transcript,
            confidence=confidence,
            debug=debug,
        )
