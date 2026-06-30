from __future__ import annotations

import json
import os
from typing import Any

from aqt import mw

from .constants import DEFAULT_BRAIN_IMPORT_MESSAGE, DEFAULT_INSTRUCTION, DEFAULT_MODEL
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
    "model": DEFAULT_MODEL,
    "temperature_optimize": 0.1,
    "temperature_chat": 0.2,
    "timeout_seconds": 30,
    "max_history_turns": 20,
    "confirm_before_apply": True,
    "max_retries": 2,
    "brain_import_message": DEFAULT_BRAIN_IMPORT_MESSAGE,
}


def _merge_defaults(config: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(DEFAULT_CONFIG)
    if config:
        merged.update(config)
    return merged


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
