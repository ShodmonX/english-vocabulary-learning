from __future__ import annotations

from app.config import settings
from app.services.stt.assemblyai_transcribe import AssemblyAITranscribeSTT
from app.services.stt.azure_speech import AzureSpeechSTT
from app.services.stt.base import STTProvider


def create_stt_provider() -> STTProvider:
    if settings.stt_provider == "azure":
        return AzureSpeechSTT()
    return AssemblyAITranscribeSTT()


def current_stt_provider_name() -> str:
    return settings.stt_provider

