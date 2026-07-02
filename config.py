from __future__ import annotations

import json
import os
from typing import Any

from aqt import mw

from .constants import (
    DEFAULT_INSTRUCTION,
    DEFAULT_MODEL_CHAT,
    DEFAULT_MODEL_OPTIMIZE,
    DEFAULT_THINKING_BUDGET_CHAT,
    DEFAULT_THINKING_BUDGET_OPTIMIZE,
)
from .i18n import DEFAULT_LANGUAGE

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
ADDON_MODULE = os.path.basename(ADDON_DIR)
LEGACY_CONFIG_PATH = os.path.join(ADDON_DIR, "config_gemini.json")
META_CONFIG_PATH = os.path.join(ADDON_DIR, "meta.json")

DEFAULT_CONFIG: dict[str, Any] = {
    "language": DEFAULT_LANGUAGE,
    "api_key": "",
    "system_instruction": DEFAULT_INSTRUCTION,
    "dynamic_instructions": "",
    "model_optimize": DEFAULT_MODEL_OPTIMIZE,
    "model_chat": DEFAULT_MODEL_CHAT,
    "thinking_budget_optimize": DEFAULT_THINKING_BUDGET_OPTIMIZE,
    "thinking_budget_chat": DEFAULT_THINKING_BUDGET_CHAT,
    "chat_streaming": True,
    "temperature_optimize": 0.1,
    "temperature_chat": 0.2,
    "timeout_seconds": 30,
    "max_history_turns": 20,
    "confirm_before_apply": True,
    "max_retries": 2,
    "brain_import_message": "",
}

RESTORABLE_SETTING_KEYS: tuple[str, ...] = tuple(DEFAULT_CONFIG.keys())

# Maps config keys to existing settings label i18n keys for the restore list.
RESTORABLE_SETTING_LABELS: dict[str, str] = {
    "language": "settings.language",
    "api_key": "settings.api_key",
    "model_optimize": "settings.model_optimize",
    "model_chat": "settings.model_chat",
    "thinking_budget_optimize": "settings.thinking_budget_optimize",
    "thinking_budget_chat": "settings.thinking_budget_chat",
    "chat_streaming": "settings.chat_streaming",
    "timeout_seconds": "settings.timeout",
    "max_retries": "settings.max_retry",
    "max_history_turns": "settings.chat_history",
    "temperature_optimize": "settings.temp_optimize",
    "temperature_chat": "settings.temp_chat",
    "confirm_before_apply": "settings.confirm_preview",
    "brain_import_message": "settings.brain_message",
    "system_instruction": "settings.system_instruction",
    "dynamic_instructions": "settings.dynamic_instructions",
}


def default_config_value(key: str) -> Any:
    if key not in DEFAULT_CONFIG:
        raise KeyError(key)
    return DEFAULT_CONFIG[key]


def _merge_defaults(config: dict[str, Any] | None) -> dict[str, Any]:
    stored = config or {}
    merged = dict(DEFAULT_CONFIG)
    merged.update(stored)
    return _apply_config_migrations(merged, stored)


def _coerce_thinking_budget(raw: Any, default: int) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _apply_config_migrations(config: dict[str, Any], stored: dict[str, Any] | None = None) -> dict[str, Any]:
    stored = stored or {}
    legacy_model = (config.get("model") or "").strip()
    if legacy_model:
        if not (stored.get("model_optimize") or "").strip():
            config["model_optimize"] = legacy_model
        if not (stored.get("model_chat") or "").strip():
            config["model_chat"] = legacy_model

    if "thinking_budget" in stored:
        legacy_budget = stored["thinking_budget"]
        if "thinking_budget_optimize" not in stored:
            config["thinking_budget_optimize"] = _coerce_thinking_budget(
                legacy_budget, DEFAULT_THINKING_BUDGET_OPTIMIZE
            )
        if "thinking_budget_chat" not in stored:
            config["thinking_budget_chat"] = _coerce_thinking_budget(
                legacy_budget, DEFAULT_THINKING_BUDGET_CHAT
            )

    config.pop("thinking_budget", None)
    return config


def _migrate_legacy_config() -> dict[str, Any] | None:
    if not os.path.exists(LEGACY_CONFIG_PATH):
        return None
    try:
        with open(LEGACY_CONFIG_PATH, "r", encoding="utf-8") as handle:
            legacy = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[Anki AI Add-on] Impossibile leggere config legacy: {exc}")
        return None

    if "api_key" not in legacy or "system_instruction" not in legacy:
        return None

    migrated = _merge_defaults(
        {
            "api_key": legacy.get("api_key", ""),
            "system_instruction": legacy.get("system_instruction", DEFAULT_INSTRUCTION),
            "dynamic_instructions": legacy.get("dynamic_instructions", ""),
        }
    )
    return migrated


def _read_meta_config() -> dict[str, Any]:
    if not os.path.exists(META_CONFIG_PATH):
        return {}
    try:
        with open(META_CONFIG_PATH, "r", encoding="utf-8") as handle:
            meta = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[Anki AI Add-on] Impossibile leggere meta.json: {exc}")
        return {}
    stored = meta.get("config")
    return stored if isinstance(stored, dict) else {}


def load_config() -> dict[str, Any]:
    stored = mw.addonManager.getConfig(ADDON_MODULE)
    if not stored:
        stored = _read_meta_config()
    config = _merge_defaults(stored)

    if not stored.get("api_key") and (legacy := _migrate_legacy_config()):
        config = legacy
        save_config(config)

    if config.get("api_key") == "INSERISCI_QUI_LA_TUA_API_KEY":
        config["api_key"] = ""

    return config


def save_config(config: dict[str, Any]) -> None:
    mw.addonManager.writeConfig(ADDON_MODULE, config)


def api_key_configured(config: dict[str, Any]) -> bool:
    key = (config.get("api_key") or "").strip()
    return bool(key) and "INSERISCI_QUI" not in key
