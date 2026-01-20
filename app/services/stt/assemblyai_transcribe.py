from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import httpx

from app.config import settings
from app.services.stt.base import STTProvider, STTProviderError, TranscriptionResult

logger = logging.getLogger("stt.assemblyai")

_RATE_LIMIT_MESSAGE = (
    "Hozir talaffuz tekshiruvi mavjud emas. Iltimos, keyinroq yana urinib ko‘ring."
)
_TRANSIENT_BACKOFFS = (0.5, 1.5)
_POLL_INTERVAL_SECONDS = 0.5
_MAX_POLL_SECONDS = 15.0
_BASE_URL = "https://api.assemblyai.com/v2"


def _extract_request_id(response: httpx.Response | None) -> str | None:
    if not response:
        return None
    return response.headers.get("x-request-id") or response.headers.get("X-Request-Id")


def _log_api_error(message: str, response: httpx.Response | None = None) -> None:
    logger.warning(
        "AssemblyAI STT error status=%s request_id=%s message=%s",
        response.status_code if response else None,
        _extract_request_id(response),
        message,
    )


def _is_quota_or_rate_limit(status_code: int | None, message: str) -> bool:
    if status_code == 429:
        return True
    lowered = message.lower()
    keywords = (
        "quota",
        "trial",
        "limit",
        "rate limit",
        "insufficient",
        "billing",
    )
    return any(keyword in lowered for keyword in keywords)


def _is_temporary_unavailable(status_code: int | None) -> bool:
    return status_code in {500, 502, 503, 504}


async def _request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response:
    for attempt in range(len(_TRANSIENT_BACKOFFS) + 1):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code >= 500 and attempt < len(_TRANSIENT_BACKOFFS):
                _log_api_error(response.text, response)
                await asyncio.sleep(_TRANSIENT_BACKOFFS[attempt])
                continue
            return response
        except httpx.RequestError as exc:
            _log_api_error(str(exc), None)
            if attempt < len(_TRANSIENT_BACKOFFS):
                await asyncio.sleep(_TRANSIENT_BACKOFFS[attempt])
                continue
            raise STTProviderError(str(exc), user_message=_RATE_LIMIT_MESSAGE) from exc
    raise STTProviderError("AssemblyAI request retry loop exhausted", user_message=_RATE_LIMIT_MESSAGE)


class AssemblyAITranscribeSTT(STTProvider):
    def __init__(self) -> None:
        self.api_key = settings.assemblyai_api_key

    async def transcribe(self, wav_path: str) -> TranscriptionResult:
        headers = {"authorization": self.api_key}
        timeout = httpx.Timeout(15.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            upload_url = await self._upload_audio(client, headers, wav_path)
            transcript_id = await self._create_transcript(client, headers, upload_url)
            text = await self._poll_transcript(client, headers, transcript_id)
            return TranscriptionResult(transcript=text.strip())

    async def _upload_audio(
        self, client: httpx.AsyncClient, headers: dict[str, str], wav_path: str
    ) -> str:
        path = Path(wav_path)
        with path.open("rb") as audio_file:
            response = await _request_with_retries(
                client,
                "POST",
                f"{_BASE_URL}/upload",
                headers=headers,
                content=audio_file.read(),
            )
        if response.status_code >= 400:
            message = response.text
            _log_api_error(message, response)
            if _is_quota_or_rate_limit(response.status_code, message) or _is_temporary_unavailable(
                response.status_code
            ):
                raise STTProviderError(message, user_message=_RATE_LIMIT_MESSAGE)
            raise STTProviderError(message)
        payload = response.json()
        upload_url = payload.get("upload_url")
        if not upload_url:
            raise STTProviderError("AssemblyAI upload response missing upload_url")
        return upload_url

    async def _create_transcript(
        self, client: httpx.AsyncClient, headers: dict[str, str], upload_url: str
    ) -> str:
        response = await _request_with_retries(
            client,
            "POST",
            f"{_BASE_URL}/transcript",
            headers={**headers, "content-type": "application/json"},
            json={"audio_url": upload_url, "language_code": "en"},
        )
        if response.status_code >= 400:
            message = response.text
            _log_api_error(message, response)
            if _is_quota_or_rate_limit(response.status_code, message) or _is_temporary_unavailable(
                response.status_code
            ):
                raise STTProviderError(message, user_message=_RATE_LIMIT_MESSAGE)
            raise STTProviderError(message)
        payload = response.json()
        transcript_id = payload.get("id")
        if not transcript_id:
            raise STTProviderError("AssemblyAI transcript response missing id")
        return transcript_id

    async def _poll_transcript(
        self, client: httpx.AsyncClient, headers: dict[str, str], transcript_id: str
    ) -> str:
        deadline = time.monotonic() + _MAX_POLL_SECONDS
        while time.monotonic() < deadline:
            response = await _request_with_retries(
                client,
                "GET",
                f"{_BASE_URL}/transcript/{transcript_id}",
                headers=headers,
            )
            if response.status_code >= 400:
                message = response.text
                _log_api_error(message, response)
                if _is_quota_or_rate_limit(response.status_code, message) or _is_temporary_unavailable(
                    response.status_code
                ):
                    raise STTProviderError(message, user_message=_RATE_LIMIT_MESSAGE)
                raise STTProviderError(message)
            payload = response.json()
            status = payload.get("status")
            if status == "completed":
                text = payload.get("text", "")
                return text or ""
            if status == "failed":
                error_message = payload.get("error", "AssemblyAI transcription failed")
                _log_api_error(error_message, response)
                if _is_quota_or_rate_limit(None, error_message):
                    raise STTProviderError(error_message, user_message=_RATE_LIMIT_MESSAGE)
                raise STTProviderError(error_message)
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        raise STTProviderError("AssemblyAI transcription timeout", user_message=_RATE_LIMIT_MESSAGE)
