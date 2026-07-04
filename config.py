from __future__ import annotations

import json
import os
from typing import Any

from aqt import mw

from .constants import (
    DEFAULT_MODEL_CHAT,
    DEFAULT_MODEL_OPTIMIZE,
    DEFAULT_THINKING_BUDGET_CHAT,
    DEFAULT_THINKING_BUDGET_OPTIMIZE,
)
from .i18n import DEFAULT_LANGUAGE, is_builtin_system_instruction, system_instruction_storage_key

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
ADDON_MODULE = os.path.basename(ADDON_DIR)
LEGACY_CONFIG_PATH = os.path.join(ADDON_DIR, "config_gemini.json")
META_CONFIG_PATH = os.path.join(ADDON_DIR, "meta.json")

DEFAULT_CONFIG: dict[str, Any] = {
    "language": DEFAULT_LANGUAGE,
    "api_key": "",
    "system_instruction": "",
    "system_instruction_shared": True,
    "system_instruction_optimize": "",
    "system_instruction_chat": "",
    "dynamic_instructions": "",
    "model_optimize": DEFAULT_MODEL_OPTIMIZE,
    "model_chat": DEFAULT_MODEL_CHAT,
    "thinking_budget_optimize": DEFAULT_THINKING_BUDGET_OPTIMIZE,
    "thinking_budget_chat": DEFAULT_THINKING_BUDGET_CHAT,
    "chat_streaming": True,
    "temperature_optimize": 0.1,
    "temperature_chat": 0.2,
    "timeout_seconds": 30,
    "max_history_turns": 10,
    "confirm_before_apply": True,
    "max_retries": 2,
    "brain_import_message": "",
    "prompt_optimize_user": "",
    "prompt_chat_addon": "",
    "prompt_dynamic_rules_prefix": "",
    "prompt_chat_context": "",
    "suppress_default_system_instruction_warning": False,
    "suppress_api_key_restore_warning": False,
}

RESTORABLE_SETTING_KEYS: tuple[str, ...] = (
    "language",
    "api_key",
    "system_instruction",
    "system_instruction_shared",
    "system_instruction_optimize",
    "system_instruction_chat",
    "dynamic_instructions",
    "model_optimize",
    "model_chat",
    "thinking_budget_optimize",
    "thinking_budget_chat",
    "chat_streaming",
    "temperature_optimize",
    "temperature_chat",
    "timeout_seconds",
    "max_history_turns",
    "confirm_before_apply",
    "max_retries",
    "brain_import_message",
    "prompt_optimize_user",
    "prompt_chat_addon",
    "prompt_dynamic_rules_prefix",
    "prompt_chat_context",
)

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
    "prompt_optimize_user": "settings.prompt_optimize_user",
    "prompt_chat_addon": "settings.prompt_chat_addon",
    "prompt_dynamic_rules_prefix": "settings.prompt_dynamic_rules_prefix",
    "prompt_chat_context": "settings.prompt_chat_context",
    "system_instruction": "settings.system_instruction",
    "system_instruction_shared": "settings.system_instruction_shared",
    "system_instruction_optimize": "settings.system_instruction_optimize",
    "system_instruction_chat": "settings.system_instruction_chat",
    "dynamic_instructions": "settings.dynamic_instructions",
}

SETTING_HELP_KEYS: dict[str, str] = {
    key: f"settings.help.{key}" for key in RESTORABLE_SETTING_KEYS
}

DISMISSIBLE_WARNING_KEYS: tuple[str, ...] = (
    "suppress_default_system_instruction_warning",
    "suppress_api_key_restore_warning",
)

DISMISSIBLE_WARNING_LABELS: dict[str, str] = {
    "suppress_default_system_instruction_warning": "warnings.default_system_instruction",
    "suppress_api_key_restore_warning": "warnings.api_key_restore",
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
            "system_instruction": legacy.get("system_instruction", ""),
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


def uses_default_system_instruction(config: dict[str, Any]) -> bool:
    key = system_instruction_storage_key("optimize", config)
    stored = (config.get(key) or "").strip()
    return is_builtin_system_instruction(stored)


def is_warning_dismissed(config: dict[str, Any], key: str) -> bool:
    if key not in DISMISSIBLE_WARNING_KEYS:
        return False
    return bool(config.get(key, False))


def dismissed_warning_keys(config: dict[str, Any]) -> list[str]:
    return [key for key in DISMISSIBLE_WARNING_KEYS if is_warning_dismissed(config, key)]
