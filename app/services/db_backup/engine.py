from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.engine.url import make_url

from app.config import settings
from app.db.repo.admin import log_admin_action, set_feature_flag
from app.db.session import AsyncSessionLocal

BACKUP_KINDS = {"auto", "manual", "pre_restore"}
_LOCK = asyncio.Lock()


@dataclass
class BackupMeta:
    filename: str
    created_at: datetime
    size_bytes: int
    kind: str


def _backup_dir() -> Path:
    path = Path(settings.backup_dir)
    # BACKUP_DIR should be a shared volume with the Postgres container (same host path as /backups).
    path.mkdir(parents=True, exist_ok=True)
    return path


def _db_params() -> dict[str, str | int]:
    url = make_url(settings.database_url)
    return {
        "host": url.host or "db",
        "port": url.port or 5432,
        "user": url.username or "vocab",
        "password": url.password or "",
        "database": url.database or "vocab",
    }


def _prefix_for_kind(kind: str) -> str:
    if kind == "auto":
        return settings.auto_backup_prefix
    if kind == "manual":
        return settings.manual_backup_prefix
    if kind == "pre_restore":
        return settings.pre_restore_backup_prefix
    raise ValueError("Unknown backup kind")


def _kind_from_filename(filename: str) -> str | None:
    for kind in BACKUP_KINDS:
        prefix = _prefix_for_kind(kind)
        if filename.startswith(prefix):
            return kind
    return None


def _parse_backup_datetime(filename: str, prefix: str) -> datetime | None:
    if not filename.startswith(prefix) or not filename.endswith(".dump"):
        return None
    timestamp = filename[len(prefix) : -5]
    try:
        return datetime.strptime(timestamp, "%Y-%m-%d_%H-%M")
    except ValueError:
        return None


def _validate_filename(filename: str) -> BackupMeta | None:
    if Path(filename).name != filename:
        return None
    kind = _kind_from_filename(filename)
    if not kind:
        return None
    created_at = _parse_backup_datetime(filename, _prefix_for_kind(kind))
    if not created_at:
        return None
    return BackupMeta(filename=filename, created_at=created_at, size_bytes=0, kind=kind)


def _format_backup_name(kind: str, timestamp: datetime) -> str:
    prefix = _prefix_for_kind(kind)
    return f"{prefix}{timestamp.strftime('%Y-%m-%d_%H-%M')}.dump"


def _format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def format_backup_line(info: BackupMeta) -> str:
    date_str = info.created_at.strftime("%Y-%m-%d %H:%M")
    size_str = _format_size(info.size_bytes)
    kind_label = info.kind.replace("_", " ").upper()
    return f"{info.filename} | {date_str} | {size_str} | {kind_label}"


def is_backup_locked() -> bool:
    return _LOCK.locked()


class _BackupLock:
    def __init__(self) -> None:
        self._timeout = settings.backup_lock_timeout_seconds

    async def __aenter__(self) -> None:
        try:
            await asyncio.wait_for(_LOCK.acquire(), timeout=self._timeout)
        except asyncio.TimeoutError as exc:
            raise RuntimeError("Backup lock timeout") from exc

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if _LOCK.locked():
            _LOCK.release()


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


async def _run_command(cmd: list[str], env: dict[str, str], timeout: int, error_hint: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"{error_hint} timeout")
    if proc.returncode != 0:
        stderr_text = stderr.decode().strip()
        raise RuntimeError(stderr_text or f"{error_hint} failed")


async def _run_restore(cmd: list[str], env: dict[str, str], timeout: int) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError("Restore timeout")
    if proc.returncode != 0:
        stderr_text = stderr.decode().strip()
        if not _is_ignorable_restore_error(stderr_text):
            raise RuntimeError(stderr_text or "Restore failed")


async def create_backup(kind: str) -> BackupMeta:
    if kind not in BACKUP_KINDS:
        raise ValueError("Invalid backup kind")
    async with _BackupLock():
        return await _create_backup(kind)


async def _create_backup(kind: str) -> BackupMeta:
    backup_dir = _backup_dir()
    timestamp = datetime.utcnow()
    filename = _format_backup_name(kind, timestamp)
    path = backup_dir / filename
    params = _db_params()
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
    await _run_command(cmd, env, timeout=60, error_hint="Backup")
    stat = path.stat()
    return BackupMeta(
        filename=filename,
        size_bytes=stat.st_size,
        created_at=datetime.fromtimestamp(stat.st_mtime),
        kind=kind,
    )


async def list_backups(kind: str | None = None) -> list[BackupMeta]:
    if kind and kind not in BACKUP_KINDS:
        raise ValueError("Invalid backup kind")
    backup_dir = _backup_dir()
    items: list[BackupMeta] = []
    for path in backup_dir.iterdir():
        if not path.is_file():
            continue
        meta = _validate_filename(path.name)
        if not meta:
            continue
        if kind and meta.kind != kind:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        meta.size_bytes = stat.st_size
        meta.created_at = datetime.fromtimestamp(stat.st_mtime)
        items.append(meta)
    items.sort(key=lambda x: x.created_at, reverse=True)
    return items


async def delete_backup(filename: str) -> None:
    meta = _validate_filename(filename)
    if not meta:
        raise RuntimeError("Invalid backup filename")
    async with _BackupLock():
        path = _backup_dir() / filename
        if not path.exists():
            raise RuntimeError("Backup not found")
        path.unlink(missing_ok=True)


async def cleanup_auto_backups(retention_days: int) -> int:
    if retention_days <= 0:
        return 0
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    deleted = 0
    async with _BackupLock():
        backup_dir = _backup_dir()
        for path in backup_dir.iterdir():
            if not path.is_file() or path.suffix != ".dump":
                continue
            name = path.name
            if not name.startswith(settings.auto_backup_prefix):
                continue
            created_at = _parse_backup_datetime(name, settings.auto_backup_prefix)
            if not created_at:
                continue
            if created_at > cutoff:
                continue
            try:
                path.unlink()
                deleted += 1
            except OSError:
                continue
    return deleted


async def restore_from_backup(filename: str) -> None:
    meta = _validate_filename(filename)
    if not meta:
        raise RuntimeError("Invalid backup filename")
    async with _BackupLock():
        async with AsyncSessionLocal() as session:
            await set_feature_flag(session, "maintenance", True)
        try:
            try:
                safety = await _create_backup("pre_restore")
            except Exception as exc:
                async with AsyncSessionLocal() as session:
                    await log_admin_action(
                        session, 0, "backup/pre_restore/fail", "backup", _truncate(str(exc))
                    )
                raise RuntimeError("Safety backup olinmadi, restore bekor qilindi.") from exc
            async with AsyncSessionLocal() as session:
                await log_admin_action(
                    session, 0, "backup/pre_restore/success", "backup", safety.filename
                )

            params = _db_params()
            env = os.environ.copy()
            if params["password"]:
                env["PGPASSWORD"] = str(params["password"])
            await _run_command(
                [
                    "psql",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-h",
                    str(params["host"]),
                    "-U",
                    str(params["user"]),
                    "-p",
                    str(params["port"]),
                    "-d",
                    str(params["database"]),
                    "-c",
                    "DROP SCHEMA public CASCADE; CREATE SCHEMA public;",
                ],
                env,
                timeout=30,
                error_hint="Schema reset",
            )
            await _run_restore(
                [
                    "pg_restore",
                    "-Fc",
                    "-h",
                    str(params["host"]),
                    "-U",
                    str(params["user"]),
                    "-p",
                    str(params["port"]),
                    "-d",
                    str(params["database"]),
                    str(_backup_dir() / filename),
                ],
                env,
                timeout=180,
            )
            await _run_command(
                [
                    "psql",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-h",
                    str(params["host"]),
                    "-U",
                    str(params["user"]),
                    "-p",
                    str(params["port"]),
                    "-d",
                    str(params["database"]),
                    "-c",
                    "SELECT 1;",
                ],
                env,
                timeout=15,
                error_hint="Healthcheck",
            )
        finally:
            async with AsyncSessionLocal() as session:
                await set_feature_flag(session, "maintenance", False)


def _truncate(text: str, max_len: int = 64) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."
