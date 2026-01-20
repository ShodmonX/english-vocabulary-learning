from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger("i18n")

_MESSAGES: dict[str, str] = {}
_BUTTONS: dict[str, str] = {}
_LOADED = False


def _resolve_key(store: dict[str, object], key: str) -> str | None:
    node: object = store
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    if isinstance(node, str):
        return node
    return None


def load_locales(base_path: Path | None = None) -> None:
    global _MESSAGES, _BUTTONS, _LOADED
    if _LOADED:
        return
    root = base_path or Path(__file__).resolve().parents[2]
    messages_path = root / "locales" / "messages.uz.yml"
    buttons_path = root / "locales" / "buttons.uz.yml"
    _MESSAGES = yaml.safe_load(messages_path.read_text(encoding="utf-8")) or {}
    _BUTTONS = yaml.safe_load(buttons_path.read_text(encoding="utf-8")) or {}
    _LOADED = True


def t(key: str, **vars: object) -> str:
    if not _LOADED:
        load_locales()
    template = _resolve_key(_MESSAGES, key)
    if template is None:
        logger.warning("Missing message key: %s", key)
        return f"[missing:{key}]"
    try:
        return template.format(**vars)
    except KeyError:
        logger.warning("Missing message vars for key: %s", key)
        return f"[missing:{key}]"


def b(key: str, **vars: object) -> str:
    if not _LOADED:
        load_locales()
    template = _resolve_key(_BUTTONS, key)
    if template is None:
        logger.warning("Missing button key: %s", key)
        return f"[missing:{key}]"
    try:
        return template.format(**vars)
    except KeyError:
        logger.warning("Missing button vars for key: %s", key)
        return f"[missing:{key}]"
