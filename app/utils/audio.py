from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path

from aiogram import Bot
from aiogram.types import Voice


@dataclass
class AudioFiles:
    ogg_path: Path
    wav_path: Path


async def download_voice(bot: Bot, voice: Voice) -> tuple[Path, int]:
    file = await bot.get_file(voice.file_id)
    tmp_ogg = Path(tempfile.mkstemp(suffix=".ogg")[1])
    await bot.download_file(file.file_path, destination=tmp_ogg)
    return tmp_ogg, voice.file_size or 0


async def convert_to_wav(ogg_path: Path) -> Path:
    wav_path = Path(tempfile.mkstemp(suffix=".wav")[1])
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        str(ogg_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(wav_path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    code = await process.wait()
    if code != 0:
        raise RuntimeError("ffmpeg error")
    return wav_path
