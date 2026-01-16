import asyncio
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine.url import make_url

from app.config import settings

BACKUP_DIR = Path("/app/backups")
BACKUP_PATTERN = re.compile(r"^app_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.dump$")
_LOCK = asyncio.Lock()


@dataclass
class BackupInfo:
    filename: str
    size_bytes: int
    created_at: datetime


def _db_params() -> dict[str, str | int]:
    url = make_url(settings.database_url)
    return {
        "host": url.host or "db",
        "port": url.port or 5432,
        "user": url.username or "vocab",
        "password": url.password or "",
        "database": url.database or "vocab",
    }


def format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def _validate_filename(filename: str) -> bool:
    return bool(BACKUP_PATTERN.match(filename))


def ensure_backup_dir() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def list_backups() -> list[BackupInfo]:
    ensure_backup_dir()
    items: list[BackupInfo] = []
    for path in BACKUP_DIR.iterdir():
        if not path.is_file():
            continue
        if not _validate_filename(path.name):
            continue
        stat = path.stat()
        items.append(
            BackupInfo(
                filename=path.name,
                size_bytes=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_mtime),
            )
        )
    items.sort(key=lambda x: x.created_at, reverse=True)
    return items


async def create_backup() -> BackupInfo:
    ensure_backup_dir()
    params = _db_params()
    filename = datetime.utcnow().strftime("app_%Y-%m-%d_%H-%M.dump")
    path = BACKUP_DIR / filename
    cmd = [
        "pg_dump",
        "-Fc",
        "-f",
        str(path),
        "-h",
        str(params["host"]),
        "-U",
        str(params["user"]),
        "-p",
        str(params["port"]),
        "-d",
        str(params["database"]),
    ]
    env = os.environ.copy()
    if params["password"]:
        env["PGPASSWORD"] = str(params["password"])
    async with _LOCK:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
        )
        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError("Backup timeout")
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode().strip() or "Backup failed")
    stat = path.stat()
    return BackupInfo(filename=filename, size_bytes=stat.st_size, created_at=datetime.fromtimestamp(stat.st_mtime))


async def restore_backup(filename: str) -> None:
    if not _validate_filename(filename):
        raise RuntimeError("Invalid backup filename")
    path = BACKUP_DIR / filename
    if not path.exists():
        raise RuntimeError("Backup not found")
    params = _db_params()
    cmd = [
        "pg_restore",
        "-Fc",
        "-c",
        "-h",
        str(params["host"]),
        "-U",
        str(params["user"]),
        "-p",
        str(params["port"]),
        "-d",
        str(params["database"]),
        str(path),
    ]
    env = os.environ.copy()
    if params["password"]:
        env["PGPASSWORD"] = str(params["password"])
    async with _LOCK:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
        )
        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError("Restore timeout")
    if proc.returncode != 0:
        stderr_text = stderr.decode().strip()
        if not _is_ignorable_restore_error(stderr_text):
            raise RuntimeError(stderr_text or "Restore failed")


def delete_backup(filename: str) -> None:
    if not _validate_filename(filename):
        raise RuntimeError("Invalid backup filename")
    path = BACKUP_DIR / filename
    if not path.exists():
        raise RuntimeError("Backup not found")
    path.unlink(missing_ok=True)


def format_backup_line(info: BackupInfo) -> str:
    date_str = info.created_at.strftime("%Y-%m-%d %H:%M")
    size_str = format_size(info.size_bytes)
    return f"{info.filename} | {date_str} | {size_str}"


def _is_ignorable_restore_error(stderr: str) -> bool:
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    if not lines:
        return False
    patterns = [
        r'^pg_restore: error: could not execute query: ERROR:\s+unrecognized configuration parameter "transaction_timeout"$',
        r"^Command was: SET transaction_timeout = 0;$",
        r"^pg_restore: warning: errors ignored on restore: 1$",
    ]
    if len(lines) != len(patterns):
        return False
    return all(re.match(pattern, line) for pattern, line in zip(patterns, lines))
