from __future__ import annotations

import asyncio
import html
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger("translation")
_semaphore = asyncio.Semaphore(2)


async def translate(text: str) -> str | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    if len(cleaned) > 128:
        return None
    if not settings.translation_enabled or not settings.google_translate_api_key:
        return None

    start = time.monotonic()
    async with _semaphore:
        async with httpx.AsyncClient(
            timeout=settings.google_translate_timeout_seconds
        ) as client:
            params = {"key": settings.google_translate_api_key}
            data = {
                "q": cleaned,
                "source": "en",
                "target": "uz",
                "format": "text",
            }
            response = await client.post(
                settings.google_translate_url, params=params, data=data
            )
    duration_ms = int((time.monotonic() - start) * 1000)
    if response.status_code >= 400:
        logger.warning("GTRANSLATE_ERROR status=%s duration_ms=%s", response.status_code, duration_ms)
        return None
    payload = response.json()
    translated = (
        payload.get("data", {})
        .get("translations", [{}])[0]
        .get("translatedText")
    )
    if not translated:
        return None
    translated = html.unescape(translated)
    logger.info("GTRANSLATE_OK duration_ms=%s input_len=%s", duration_ms, len(cleaned))
    return translated
