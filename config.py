from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aqt import mw

from .constants import (
    DEFAULT_MODEL_CHAT,
    DEFAULT_MODEL_OPTIMIZE,
    DEFAULT_PROMPT_CACHE_MIN_CHARS,
    DEFAULT_THINKING_BUDGET_CHAT,
    DEFAULT_THINKING_BUDGET_OPTIMIZE,
)
from .i18n import DEFAULT_LANGUAGE, is_builtin_system_instruction, system_instruction_storage_key

ADDON_DIR = Path(__file__).resolve().parent
ADDON_MODULE = ADDON_DIR.name
LEGACY_CONFIG_PATH = ADDON_DIR / "config_gemini.json"
META_CONFIG_PATH = ADDON_DIR / "meta.json"

CONFIG_VERSION = 5

_OBSOLETE_CONFIG_KEYS: tuple[str, ...] = (
    "thinking_budget",
    "model",
    "chat_token_warning_threshold",
    "chat_prompt_inspection",
    "prompt_cache_recreate_confirm_usd",
    "prompt_cache_min_tokens",
    "prompt_cache_import_note_default",
    "prompt_cache_enabled",
    "prompt_cache_ttl_seconds",
    "prompt_cache_min_chars",
    "prompt_cache_custom_text",
    "prompt_cache_active_preset_id",
    "prompt_cache_segments",
)

_WRAPPER_RESET_KEYS: tuple[str, ...] = (
    "prompt_chat_context",
    "prompt_chat_context_order",
    "prompt_chat_context_sections",
    "prompt_card_templates_format",
)

DEFAULT_CONFIG: dict[str, Any] = {
    "config_version": CONFIG_VERSION,
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
    "settings_show_text_newlines": False,
    "settings_wrap_text_editors": True,
    "temperature_optimize": 0.1,
    "temperature_chat": 0.2,
    "timeout_seconds": 30,
    "max_history_turns": 10,
    "confirm_before_apply": True,
    "max_retries": 2,
    "brain_import_message": "",
    "brain_import_templates": False,
    "brain_import_css": False,
    "chat_payload_warning_chars": 12000,
    "chat_apply_history_max": 7,
    "prompt_optimize_user": "",
    "prompt_chat_addon": "",
    "prompt_dynamic_rules_prefix": "",
    "prompt_chat_context": "",
    "prompt_chat_context_order": [
        "request",
        "context",
        "format_guide",
        "templates",
        "styling",
    ],
    "prompt_chat_context_sections": {},
    "prompt_card_templates_format": "",
    "mathjax_preview_preamble": "",
    "settings_presets": [],
    "active_settings_preset_id": "",
    "prompt_cache_enabled_chat": False,
    "prompt_cache_enabled_optimize": False,
    "prompt_cache_ttl_seconds_chat": 3600,
    "prompt_cache_ttl_seconds_optimize": 3600,
    "prompt_cache_min_chars_chat": DEFAULT_PROMPT_CACHE_MIN_CHARS,
    "prompt_cache_min_chars_optimize": DEFAULT_PROMPT_CACHE_MIN_CHARS,
    "prompt_cache_custom_text_chat": "",
    "prompt_cache_custom_text_optimize": "",
    "prompt_cache_custom_text_presets": [],
    "prompt_cache_active_preset_id_chat": "",
    "prompt_cache_active_preset_id_optimize": "",
    "prompt_cache_change_ttl_seconds": 3600,
    "prompt_cache_recreate_default": "recreate",
    "prompt_cache_new_conversation_cache_default": "clear",
    "prompt_cache_segments_chat": dict(
        {
            "system_instruction": True,
            "dynamic_rules": False,
            "chat_system_addon": True,
            "custom_cache_text": False,
            "imported_note": False,
            "card_templates_format_guide": False,
            "card_templates": False,
            "notetype_css": False,
            "context_wrapper": False,
        }
    ),
    "prompt_cache_segments_optimize": dict(
        {
            "system_instruction": True,
            "dynamic_rules": False,
            "custom_cache_text": False,
        }
    ),
    "chat_send_empty_fields": False,
    "chat_modify_prompt_before_send": False,
    "chat_download_directory": "",
    "chat_export_quick_folders": [],
    "optimize_modify_prompt_before_send": False,
    "suppress_default_system_instruction_warning": False,
    "suppress_api_key_restore_warning": False,
    "suppress_settings_unsaved_close_warning": False,
    "suppress_settings_save_confirm_warning": True,
    "suppress_settings_cancel_confirm_warning": True,
    "suppress_prompt_cache_created_optimize_notice": False,
    "suppress_chat_new_conversation_confirm_warning": True,
    "suppress_prompt_cache_recreate_confirm": False,
    "suppress_settings_save_cache_clear_warning": False,
    "suppress_new_conversation_cache_warning": False,
    "suppress_import_note_cache_warning": False,
    "suppress_prompt_cache_custom_text_load_confirm": False,
    "suppress_prompt_cache_delete_orphans_confirm": False,
    "suppress_apply_note_duplicate_warning": False,
    "dev_mock_mode": False,
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
    "brain_import_templates",
    "brain_import_css",
    "chat_payload_warning_chars",
    "chat_apply_history_max",
    "prompt_optimize_user",
    "prompt_chat_addon",
    "prompt_dynamic_rules_prefix",
    "prompt_chat_context",
    "prompt_chat_context_order",
    "prompt_chat_context_sections",
    "prompt_card_templates_format",
    "mathjax_preview_preamble",
    "chat_export_quick_folders",
    "prompt_cache_enabled_optimize",
    "prompt_cache_ttl_seconds_optimize",
    "prompt_cache_min_chars_optimize",
    "prompt_cache_custom_text_optimize",
    "prompt_cache_segments_optimize",
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
    "brain_import_templates": "settings.brain_import_templates",
    "brain_import_css": "settings.brain_import_css",
    "chat_payload_warning_chars": "settings.chat_payload_warning_chars",
    "chat_apply_history_max": "settings.chat_apply_history_max",
    "prompt_optimize_user": "settings.prompt_optimize_user",
    "prompt_chat_addon": "settings.prompt_chat_addon",
    "prompt_dynamic_rules_prefix": "settings.prompt_dynamic_rules_prefix",
    "prompt_chat_context": "settings.prompt_chat_context",
    "prompt_chat_context_order": "settings.prompt_chat_context_order",
    "prompt_chat_context_sections": "settings.prompt_chat_context_sections",
    "prompt_card_templates_format": "settings.prompt_card_templates_format",
    "mathjax_preview_preamble": "settings.mathjax_preview_preamble",
    "chat_export_quick_folders": "settings.chat_export_quick_folders",
    "prompt_cache_enabled_optimize": "settings.prompt_cache_enabled_optimize",
    "prompt_cache_ttl_seconds_optimize": "settings.prompt_cache_ttl",
    "prompt_cache_min_chars_optimize": "settings.prompt_cache_min_chars",
    "prompt_cache_custom_text_optimize": "settings.prompt_cache_custom_text",
    "prompt_cache_segments_optimize": "settings.prompt_cache_segments",
    "system_instruction": "settings.restore_label.system_instruction",
    "system_instruction_shared": "settings.system_instruction_shared",
    "system_instruction_optimize": "settings.restore_label.system_instruction_optimize",
    "system_instruction_chat": "settings.restore_label.system_instruction_chat",
    "dynamic_instructions": "settings.dynamic_instructions",
}

SETTING_HELP_KEYS: dict[str, str] = {key: f"settings.help.{key}" for key in RESTORABLE_SETTING_KEYS}

DISMISSIBLE_WARNING_KEYS: tuple[str, ...] = (
    "suppress_default_system_instruction_warning",
    "suppress_api_key_restore_warning",
    "suppress_settings_unsaved_close_warning",
    "suppress_settings_save_confirm_warning",
    "suppress_settings_cancel_confirm_warning",
    "suppress_prompt_cache_created_optimize_notice",
    "suppress_chat_new_conversation_confirm_warning",
    "suppress_prompt_cache_recreate_confirm",
    "suppress_settings_save_cache_clear_warning",
    "suppress_new_conversation_cache_warning",
    "suppress_import_note_cache_warning",
    "suppress_prompt_cache_custom_text_load_confirm",
    "suppress_prompt_cache_delete_orphans_confirm",
    "suppress_apply_note_duplicate_warning",
)

DISMISSIBLE_WARNING_LABELS: dict[str, str] = {
    "suppress_default_system_instruction_warning": "warnings.default_system_instruction",
    "suppress_api_key_restore_warning": "warnings.api_key_restore",
    "suppress_settings_unsaved_close_warning": "warnings.settings_unsaved_close",
    "suppress_settings_save_confirm_warning": "warnings.settings_save_confirm",
    "suppress_settings_cancel_confirm_warning": "warnings.settings_cancel_confirm",
    "suppress_prompt_cache_created_optimize_notice": "warnings.prompt_cache_created_optimize",
    "suppress_chat_new_conversation_confirm_warning": "warnings.chat_new_conversation_confirm",
    "suppress_prompt_cache_recreate_confirm": "warnings.prompt_cache_recreate_confirm",
    "suppress_settings_save_cache_clear_warning": "warnings.settings_save_cache_clear",
    "suppress_new_conversation_cache_warning": "warnings.new_conversation_cache",
    "suppress_import_note_cache_warning": "warnings.import_note_cache",
    "suppress_prompt_cache_custom_text_load_confirm": "warnings.prompt_cache_custom_text_load",
    "suppress_prompt_cache_delete_orphans_confirm": "warnings.prompt_cache_delete_orphans",
    "suppress_apply_note_duplicate_warning": "warnings.apply_note_duplicate",
}

DEFAULT_ACTION_SETTINGS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "prompt_cache_recreate_default",
        "warnings.default_action.recreate",
        ("recreate", "skip_cache"),
    ),
    (
        "prompt_cache_new_conversation_cache_default",
        "warnings.default_action.new_conversation_cache",
        ("keep", "clear"),
    ),
)


def default_config_value(key: str) -> Any:
    if key not in DEFAULT_CONFIG:
        raise KeyError(key)
    return DEFAULT_CONFIG[key]


def _merge_defaults(config: dict[str, Any] | None) -> dict[str, Any]:
    stored = config or {}
    merged = dict(DEFAULT_CONFIG)
    merged.update(stored)
    return _normalize_config(merged, stored)


def _stored_config_version(stored: dict[str, Any] | None) -> int:
    try:
        return int((stored or {}).get("config_version") or 0)
    except (TypeError, ValueError):
        return 0


def _coerce_prompt_cache_min_chars(value: Any, *, fallback: int) -> int:
    try:
        min_chars = int(value)
    except (TypeError, ValueError):
        min_chars = 0
    if min_chars == 8189:
        return DEFAULT_PROMPT_CACHE_MIN_CHARS
    return max(1, min_chars) if min_chars > 0 else fallback


def _normalize_prompt_cache_segments(raw: Any, *, purpose: str) -> dict[str, bool]:
    from .prompt_cache import (
        DEFAULT_PROMPT_CACHE_SEGMENTS,
        DEFAULT_PROMPT_CACHE_SEGMENTS_OPTIMIZE,
        normalize_prompt_cache_segments_for_purpose,
    )

    default = (
        DEFAULT_PROMPT_CACHE_SEGMENTS
        if purpose == "chat"
        else DEFAULT_PROMPT_CACHE_SEGMENTS_OPTIMIZE
    )
    return normalize_prompt_cache_segments_for_purpose(raw, purpose=purpose, default=default)


def _migrate_prompt_cache_purpose_split(config: dict[str, Any], stored: dict[str, Any]) -> None:
    legacy_ttl = config.pop("prompt_cache_ttl_seconds", None)
    legacy_min_chars = config.pop("prompt_cache_min_chars", None)
    legacy_custom_text = config.pop("prompt_cache_custom_text", None)
    legacy_active_preset = config.pop("prompt_cache_active_preset_id", None)
    legacy_segments = config.pop("prompt_cache_segments", None)

    for purpose in ("chat", "optimize"):
        ttl_key = f"prompt_cache_ttl_seconds_{purpose}"
        if ttl_key not in stored:
            if legacy_ttl is not None:
                try:
                    config[ttl_key] = max(60, int(legacy_ttl))
                except (TypeError, ValueError):
                    config[ttl_key] = default_config_value(ttl_key)
            elif purpose == "optimize" and "prompt_cache_ttl_seconds_chat" in stored:
                try:
                    config[ttl_key] = max(60, int(stored["prompt_cache_ttl_seconds_chat"]))
                except (TypeError, ValueError):
                    config[ttl_key] = default_config_value(ttl_key)
            else:
                config[ttl_key] = default_config_value(ttl_key)

        min_key = f"prompt_cache_min_chars_{purpose}"
        if min_key not in stored:
            if legacy_min_chars is not None:
                config[min_key] = _coerce_prompt_cache_min_chars(
                    legacy_min_chars,
                    fallback=int(default_config_value(min_key)),
                )
            else:
                config[min_key] = default_config_value(min_key)
        else:
            config[min_key] = _coerce_prompt_cache_min_chars(
                config.get(min_key),
                fallback=int(default_config_value(min_key)),
            )

        text_key = f"prompt_cache_custom_text_{purpose}"
        if text_key not in stored:
            if legacy_custom_text is not None:
                config[text_key] = str(legacy_custom_text or "")
            elif purpose == "optimize" and "prompt_cache_custom_text_chat" in stored:
                config[text_key] = str(stored["prompt_cache_custom_text_chat"] or "")
            else:
                config[text_key] = ""
        else:
            config[text_key] = str(config.get(text_key) or "")

        preset_key = f"prompt_cache_active_preset_id_{purpose}"
        if preset_key not in stored:
            if legacy_active_preset is not None:
                config[preset_key] = str(legacy_active_preset or "")
            elif purpose == "optimize" and "prompt_cache_active_preset_id_chat" in stored:
                config[preset_key] = str(stored["prompt_cache_active_preset_id_chat"] or "")
            else:
                config[preset_key] = ""
        else:
            config[preset_key] = str(config.get(preset_key) or "")

        segments_key = f"prompt_cache_segments_{purpose}"
        if segments_key not in stored:
            source = legacy_segments if isinstance(legacy_segments, dict) else None
            config[segments_key] = _normalize_prompt_cache_segments(source, purpose=purpose)
        else:
            config[segments_key] = _normalize_prompt_cache_segments(
                config.get(segments_key),
                purpose=purpose,
            )


def _normalize_config(config: dict[str, Any], stored: dict[str, Any] | None = None) -> dict[str, Any]:
    stored = stored or {}
    stored_version = _stored_config_version(stored)
    if stored_version < CONFIG_VERSION:
        if stored_version < 2:
            for key in _WRAPPER_RESET_KEYS:
                config[key] = default_config_value(key)
        if stored_version < 3:
            _migrate_prompt_cache_purpose_split(config, stored)
        if stored_version < 4:
            from .chat_context_wrapper import LEGACY_DEFAULT_WRAPPER_SECTION_ORDER

            order = config.get("prompt_chat_context_order")
            if list(order or []) == list(LEGACY_DEFAULT_WRAPPER_SECTION_ORDER):
                config["prompt_chat_context_order"] = list(
                    DEFAULT_CONFIG["prompt_chat_context_order"]
                )
        if stored_version < 5:
            config.setdefault("settings_presets", [])
            config.setdefault("active_settings_preset_id", "")
        config["config_version"] = CONFIG_VERSION

    for key in _OBSOLETE_CONFIG_KEYS:
        config.pop(key, None)

    config["prompt_chat_context"] = ""

    if not isinstance(config.get("prompt_chat_context_sections"), dict):
        config["prompt_chat_context_sections"] = {}
    if not isinstance(config.get("prompt_chat_context_order"), list):
        config["prompt_chat_context_order"] = list(
            DEFAULT_CONFIG["prompt_chat_context_order"]
        )

    for purpose in ("chat", "optimize"):
        min_key = f"prompt_cache_min_chars_{purpose}"
        config[min_key] = _coerce_prompt_cache_min_chars(
            config.get(min_key),
            fallback=int(default_config_value(min_key)),
        )
        ttl_key = f"prompt_cache_ttl_seconds_{purpose}"
        try:
            config[ttl_key] = max(60, int(config.get(ttl_key, default_config_value(ttl_key))))
        except (TypeError, ValueError):
            config[ttl_key] = default_config_value(ttl_key)
        preset_key = f"prompt_cache_active_preset_id_{purpose}"
        if not isinstance(config.get(preset_key), str):
            config[preset_key] = ""
        segments_key = f"prompt_cache_segments_{purpose}"
        config[segments_key] = _normalize_prompt_cache_segments(
            config.get(segments_key),
            purpose=purpose,
        )
        text_key = f"prompt_cache_custom_text_{purpose}"
        config[text_key] = str(config.get(text_key) or "")

    from .prompt_cache_policy import normalize_custom_text_presets
    from .settings_presets import (
        normalize_settings_presets,
        resolve_active_settings_preset_id,
    )

    config["prompt_cache_custom_text_presets"] = normalize_custom_text_presets(
        config.get("prompt_cache_custom_text_presets")
    )
    config["settings_presets"] = normalize_settings_presets(config.get("settings_presets"))
    config["active_settings_preset_id"] = resolve_active_settings_preset_id(config)
    recreate = str(config.get("prompt_cache_recreate_default") or "recreate")
    config["prompt_cache_recreate_default"] = (
        recreate if recreate in ("recreate", "skip_cache") else "recreate"
    )
    conv = str(config.get("prompt_cache_new_conversation_cache_default") or "clear")
    config["prompt_cache_new_conversation_cache_default"] = (
        conv if conv in ("keep", "clear") else "clear"
    )
    try:
        change_ttl = int(config.get("prompt_cache_change_ttl_seconds", 3600))
    except (TypeError, ValueError):
        change_ttl = 3600
    config["prompt_cache_change_ttl_seconds"] = max(60, change_ttl)

    legacy_enabled = bool(stored.get("prompt_cache_enabled", False))
    if "prompt_cache_enabled_chat" not in stored:
        config["prompt_cache_enabled_chat"] = legacy_enabled
    else:
        config["prompt_cache_enabled_chat"] = bool(config.get("prompt_cache_enabled_chat", False))
    if "prompt_cache_enabled_optimize" not in stored:
        config["prompt_cache_enabled_optimize"] = legacy_enabled
    else:
        config["prompt_cache_enabled_optimize"] = bool(
            config.get("prompt_cache_enabled_optimize", False)
        )
    config.pop("prompt_cache_enabled", None)

    from .ui.chat_export import normalize_chat_export_quick_folders

    config["chat_export_quick_folders"] = normalize_chat_export_quick_folders(
        config.get("chat_export_quick_folders")
    )

    from .note_apply import clamp_apply_history_max

    config["chat_apply_history_max"] = clamp_apply_history_max(
        config.get("chat_apply_history_max", DEFAULT_CONFIG["chat_apply_history_max"])
    )

    return config


def _migrate_legacy_config() -> dict[str, Any] | None:
    if not LEGACY_CONFIG_PATH.is_file():
        return None
    try:
        legacy = json.loads(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"))
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
    if not META_CONFIG_PATH.is_file():
        return {}
    try:
        meta = json.loads(META_CONFIG_PATH.read_text(encoding="utf-8"))
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

    if stored and _stored_config_version(stored) < CONFIG_VERSION:
        save_config(config)

    if not stored.get("api_key") and (legacy := _migrate_legacy_config()):
        config = legacy
        save_config(config)

    if config.get("api_key") == "INSERISCI_QUI_LA_TUA_API_KEY":
        config["api_key"] = ""

    return config


def save_config(config: dict[str, Any]) -> None:
    mw.addonManager.writeConfig(ADDON_MODULE, config)


def api_key_configured(config: dict[str, Any]) -> bool:
    from .dev_mock import is_dev_mock_enabled

    if is_dev_mock_enabled(config):
        return True
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
