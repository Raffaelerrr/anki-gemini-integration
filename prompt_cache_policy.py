from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from typing import Any

from .config import default_config_value
from .constants import DEFAULT_PROMPT_CACHE_MIN_CHARS
from .gemini_client import Purpose
from .prompt_cache import (
    CHAT_ONLY_SEGMENTS,
    get_prompt_cache_store,
    prompt_cache_enabled,
    prompt_cache_min_chars,
    prompt_cache_segments,
    prompt_cache_ttl_seconds,
)

MAX_CUSTOM_TEXT_PRESETS = 30

SESSION_CACHE_SEGMENT_IDS: frozenset[str] = frozenset(
    segment_id
    for segment_id in CHAT_ONLY_SEGMENTS
    if segment_id != "chat_system_addon"
)

CHAT_PROMPT_CACHE_CONFIG_KEYS: tuple[str, ...] = (
    "prompt_cache_enabled_chat",
    "prompt_cache_ttl_seconds_chat",
    "prompt_cache_min_chars_chat",
    "prompt_cache_segments_chat",
    "prompt_cache_custom_text_chat",
    "prompt_cache_active_preset_id_chat",
)

OPTIMIZE_PROMPT_CACHE_CONFIG_KEYS: tuple[str, ...] = (
    "prompt_cache_enabled_optimize",
    "prompt_cache_ttl_seconds_optimize",
    "prompt_cache_min_chars_optimize",
    "prompt_cache_segments_optimize",
    "prompt_cache_custom_text_optimize",
    "prompt_cache_active_preset_id_optimize",
)

_PURPOSE_INVALIDATION_KEYS: dict[Purpose, frozenset[str]] = {
    "optimize": frozenset(
        {
            "language",
            "system_instruction",
            "system_instruction_shared",
            "system_instruction_optimize",
            "system_instruction_chat",
            "dynamic_instructions",
            "prompt_dynamic_rules_prefix",
            "prompt_cache_enabled_optimize",
            "prompt_cache_custom_text_optimize",
            "prompt_cache_segments_optimize",
            "prompt_cache_active_preset_id_optimize",
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
            "prompt_cache_enabled_chat",
            "prompt_cache_custom_text_chat",
            "prompt_cache_segments_chat",
            "prompt_cache_active_preset_id_chat",
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


def _active_preset_id(config: dict[str, Any], *, purpose: Purpose) -> str:
    return str(config.get(f"prompt_cache_active_preset_id_{purpose}") or "").strip()


def effective_custom_cache_text(config: dict[str, Any], *, purpose: Purpose) -> str:
    preset_id = _active_preset_id(config, purpose=purpose)
    if preset_id:
        for preset in normalize_custom_text_presets(config.get("prompt_cache_custom_text_presets")):
            if preset["id"] != preset_id:
                continue
            if purpose == "chat" and preset.get("chat"):
                return str(preset.get("text") or "").strip()
            if purpose == "optimize" and preset.get("optimize"):
                return str(preset.get("text") or "").strip()
            return ""
    return str(config.get(f"prompt_cache_custom_text_{purpose}") or "").strip()


def chat_cache_includes_session_content(config: dict[str, Any]) -> bool:
    segments = prompt_cache_segments(config, "chat")
    return any(segments.get(segment_id) for segment_id in SESSION_CACHE_SEGMENT_IDS)


def cache_enabled_segments_are_global_only(config: dict[str, Any]) -> bool:
    if not prompt_cache_enabled(config, "chat"):
        return True
    return not chat_cache_includes_session_content(config)


def _any_prompt_cache_enabled(config: dict[str, Any]) -> bool:
    return prompt_cache_enabled(config, "chat") or prompt_cache_enabled(config, "optimize")


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
    if not _any_prompt_cache_enabled(old_config) and not _any_prompt_cache_enabled(new_config):
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


@dataclass
class ChatPromptCacheSettings:
    """Persistent chat prompt cache settings stored in addon config."""

    enabled: bool = False
    prompt_cache_ttl_seconds: int = 3600
    prompt_cache_min_chars: int = DEFAULT_PROMPT_CACHE_MIN_CHARS
    prompt_cache_segments: dict[str, bool] = field(default_factory=dict)
    prompt_cache_custom_text: str = ""
    prompt_cache_active_preset_id: str = ""

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ChatPromptCacheSettings:
        return cls(
            enabled=prompt_cache_enabled(config, "chat"),
            prompt_cache_ttl_seconds=prompt_cache_ttl_seconds(config, "chat"),
            prompt_cache_min_chars=prompt_cache_min_chars(config, "chat"),
            prompt_cache_segments=dict(prompt_cache_segments(config, "chat")),
            prompt_cache_custom_text=str(config.get("prompt_cache_custom_text_chat") or "").strip(),
            prompt_cache_active_preset_id=str(
                config.get("prompt_cache_active_preset_id_chat") or ""
            ).strip(),
        )

    @classmethod
    def defaults(cls) -> ChatPromptCacheSettings:
        return cls(
            enabled=bool(default_config_value("prompt_cache_enabled_chat")),
            prompt_cache_ttl_seconds=int(default_config_value("prompt_cache_ttl_seconds_chat")),
            prompt_cache_min_chars=int(default_config_value("prompt_cache_min_chars_chat")),
            prompt_cache_segments=dict(default_config_value("prompt_cache_segments_chat")),
            prompt_cache_custom_text=str(default_config_value("prompt_cache_custom_text_chat")),
            prompt_cache_active_preset_id=str(
                default_config_value("prompt_cache_active_preset_id_chat")
            ),
        )

    def apply_to_config(self, base_config: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base_config)
        merged["prompt_cache_enabled_chat"] = bool(self.enabled)
        merged["prompt_cache_ttl_seconds_chat"] = int(self.prompt_cache_ttl_seconds)
        merged["prompt_cache_min_chars_chat"] = int(self.prompt_cache_min_chars)
        merged["prompt_cache_segments_chat"] = dict(self.prompt_cache_segments)
        merged["prompt_cache_custom_text_chat"] = str(self.prompt_cache_custom_text or "").strip()
        merged["prompt_cache_active_preset_id_chat"] = str(
            self.prompt_cache_active_preset_id or ""
        ).strip()
        return merged


# Backward-compatible alias while callers migrate.
ChatPromptCacheSessionSettings = ChatPromptCacheSettings


CHAT_PROMPT_CACHE_RESTORABLE_KEYS: tuple[str, ...] = (
    "enabled",
    "prompt_cache_ttl_seconds",
    "prompt_cache_min_chars",
    "prompt_cache_segments",
    "prompt_cache_custom_text",
    "prompt_cache_active_preset_id",
)

CHAT_PROMPT_CACHE_RESTORABLE_LABELS: dict[str, str] = {
    "enabled": "settings.prompt_cache_enabled_chat",
    "prompt_cache_ttl_seconds": "settings.prompt_cache_ttl",
    "prompt_cache_min_chars": "settings.prompt_cache_min_chars",
    "prompt_cache_segments": "settings.prompt_cache_segments",
    "prompt_cache_custom_text": "settings.prompt_cache_custom_text",
    "prompt_cache_active_preset_id": "settings.prompt_cache_presets.active",
}


def chat_prompt_cache_summary(config: dict[str, Any]) -> str:
    from .i18n import tr

    enabled = prompt_cache_enabled(config, "chat")
    if not enabled:
        return tr("settings.prompt_cache.chat_summary.disabled", config=config)
    ttl = prompt_cache_ttl_seconds(config, "chat")
    enabled_segments = sum(
        1 for enabled_segment in prompt_cache_segments(config, "chat").values() if enabled_segment
    )
    return tr(
        "settings.prompt_cache.chat_summary.enabled",
        config=config,
        ttl=ttl,
        segments=enabled_segments,
    )
