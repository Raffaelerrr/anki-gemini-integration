from __future__ import annotations

import copy
import uuid
from typing import Any

from .gemini_client import Purpose
from .prompt_cache import (
    CHAT_ONLY_SEGMENTS,
    get_prompt_cache_store,
    prompt_cache_segments,
)

MAX_CUSTOM_TEXT_PRESETS = 30

SESSION_CACHE_SEGMENT_IDS: frozenset[str] = frozenset(
    segment_id
    for segment_id in CHAT_ONLY_SEGMENTS
    if segment_id != "chat_system_addon"
)

_PURPOSE_INVALIDATION_KEYS: dict[Purpose, frozenset[str]] = {    "optimize": frozenset(
        {
            "language",
            "system_instruction",
            "system_instruction_shared",
            "system_instruction_optimize",
            "system_instruction_chat",
            "dynamic_instructions",
            "prompt_dynamic_rules_prefix",
            "prompt_cache_enabled",
            "prompt_cache_custom_text",
            "prompt_cache_segments",
            "prompt_cache_active_preset_id",
            "prompt_cache_custom_text_presets",
            "model_optimize",
        }
    ),
    "chat": frozenset(
        {
            "language",
            "system_instruction",
            "system_instruction_shared",
            "system_instruction_optimize",
            "system_instruction_chat",
            "dynamic_instructions",
            "prompt_dynamic_rules_prefix",
            "prompt_cache_enabled",
            "prompt_cache_custom_text",
            "prompt_cache_segments",
            "prompt_cache_active_preset_id",
            "prompt_cache_custom_text_presets",
            "model_chat",
            "prompt_chat_addon",
            "prompt_chat_context_order",
            "prompt_chat_context_sections",
            "prompt_card_templates_format",
        }
    ),
}


def normalize_custom_text_presets(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    presets: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        preset_id = str(item.get("id") or "").strip()
        name = str(item.get("name") or "").strip()
        text = str(item.get("text") or "")
        if not preset_id:
            preset_id = uuid.uuid4().hex
        if not name:
            name = preset_id[:8]
        presets.append(
            {
                "id": preset_id,
                "name": name,
                "text": text,
                "chat": bool(item.get("chat", True)),
                "optimize": bool(item.get("optimize", True)),
            }
        )
    return presets[:MAX_CUSTOM_TEXT_PRESETS]


def effective_custom_cache_text(config: dict[str, Any], *, purpose: Purpose) -> str:
    preset_id = str(config.get("prompt_cache_active_preset_id") or "").strip()
    if preset_id:
        for preset in normalize_custom_text_presets(config.get("prompt_cache_custom_text_presets")):
            if preset["id"] != preset_id:
                continue
            if purpose == "chat" and preset.get("chat"):
                return str(preset.get("text") or "").strip()
            if purpose == "optimize" and preset.get("optimize"):
                return str(preset.get("text") or "").strip()
            return ""
    return str(config.get("prompt_cache_custom_text") or "").strip()


def chat_cache_includes_session_content(config: dict[str, Any]) -> bool:
    segments = prompt_cache_segments(config)
    return any(segments.get(segment_id) for segment_id in SESSION_CACHE_SEGMENT_IDS)


def cache_enabled_segments_are_global_only(config: dict[str, Any]) -> bool:
    if not bool(config.get("prompt_cache_enabled", False)):
        return True
    return not chat_cache_includes_session_content(config)


def has_tracked_active_cache(purpose: Purpose) -> bool:
    return get_prompt_cache_store(purpose).active is not None


def has_any_tracked_active_cache() -> bool:
    return has_tracked_active_cache("chat") or has_tracked_active_cache("optimize")


def _config_value_equal(old: Any, new: Any) -> bool:
    if isinstance(old, dict) and isinstance(new, dict):
        return old == new
    if isinstance(old, list) and isinstance(new, list):
        return old == new
    return old == new


def _purpose_keys_changed(old: dict[str, Any], new: dict[str, Any], purpose: Purpose) -> bool:
    keys = _PURPOSE_INVALIDATION_KEYS[purpose]
    for key in keys:
        old_value = old.get(key)
        new_value = new.get(key)
        if key == "prompt_cache_custom_text_presets":
            old_value = normalize_custom_text_presets(old_value)
            new_value = normalize_custom_text_presets(new_value)
        if not _config_value_equal(old_value, new_value):
            return True
    return False


def purposes_requiring_cache_invalidation(
    old_config: dict[str, Any],
    new_config: dict[str, Any],
) -> tuple[Purpose, ...]:
    if not bool(old_config.get("prompt_cache_enabled", False)) and not bool(
        new_config.get("prompt_cache_enabled", False)
    ):
        return ()
    purposes: list[Purpose] = []
    for purpose in ("chat", "optimize"):
        if _purpose_keys_changed(old_config, new_config, purpose):
            purposes.append(purpose)
    return tuple(purposes)


def new_preset(*, name: str = "", text: str = "") -> dict[str, Any]:
    preset_id = uuid.uuid4().hex
    return {
        "id": preset_id,
        "name": name.strip() or preset_id[:8],
        "text": text,
        "chat": True,
        "optimize": True,
    }


def clone_presets(config: dict[str, Any]) -> list[dict[str, Any]]:
    return copy.deepcopy(normalize_custom_text_presets(config.get("prompt_cache_custom_text_presets")))
