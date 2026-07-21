from __future__ import annotations

import copy
import json
import uuid
from typing import Any

MAX_SETTINGS_PRESETS = 20
BUILTIN_SETTINGS_PRESET_ID = "builtin_default"
SETTINGS_PRESETS_EXPORT_SCHEMA_VERSION = 1

# Prompt-only pack keys (always included when saving a named preset).
SETTINGS_PRESET_CORE_KEYS: tuple[str, ...] = (
    "system_instruction",
    "system_instruction_shared",
    "system_instruction_optimize",
    "system_instruction_chat",
    "brain_import_message",
    "prompt_optimize_user",
    "prompt_chat_addon",
    "prompt_dynamic_rules_prefix",
    "prompt_chat_context_order",
    "prompt_chat_context_sections",
    "prompt_card_templates_format",
)

# Optional: included only when the user opts in.
SETTINGS_PRESET_OPTIONAL_KEYS: tuple[str, ...] = ("dynamic_instructions",)

SETTINGS_PRESET_ALL_KEYS: tuple[str, ...] = (
    SETTINGS_PRESET_CORE_KEYS + SETTINGS_PRESET_OPTIONAL_KEYS
)


def builtin_preset_values() -> dict[str, Any]:
    """Empty/builtin storage values for the non-deletable Default preset."""
    from .config import DEFAULT_CONFIG

    values: dict[str, Any] = {}
    for key in SETTINGS_PRESET_CORE_KEYS:
        values[key] = copy.deepcopy(DEFAULT_CONFIG[key])
    return values


def _default_for_key(key: str) -> Any:
    from .config import DEFAULT_CONFIG

    return copy.deepcopy(DEFAULT_CONFIG[key])


def _normalize_pack_value(key: str, raw: Any) -> Any:
    if key == "system_instruction_shared":
        return bool(raw) if raw is not None else True
    if key == "prompt_chat_context_order":
        if isinstance(raw, list):
            return [str(item) for item in raw]
        return _default_for_key(key)
    if key == "prompt_chat_context_sections":
        if isinstance(raw, dict):
            return {str(k): str(v) for k, v in raw.items()}
        return {}
    if key in SETTINGS_PRESET_ALL_KEYS:
        return "" if raw is None else str(raw)
    return raw


def normalize_preset_values(
    raw: Any,
    *,
    include_optional_absent: bool = False,
) -> dict[str, Any]:
    """Normalize a preset values dict. Optional keys omitted unless present or forced."""
    source = raw if isinstance(raw, dict) else {}
    values: dict[str, Any] = {}
    for key in SETTINGS_PRESET_CORE_KEYS:
        if key in source:
            values[key] = _normalize_pack_value(key, source.get(key))
        else:
            values[key] = _default_for_key(key)
    for key in SETTINGS_PRESET_OPTIONAL_KEYS:
        if key in source:
            values[key] = _normalize_pack_value(key, source.get(key))
        elif include_optional_absent:
            values[key] = _default_for_key(key)
    return values


def normalize_settings_presets(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    presets: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        preset_id = str(item.get("id") or "").strip() or uuid.uuid4().hex
        if preset_id == BUILTIN_SETTINGS_PRESET_ID or preset_id in seen_ids:
            preset_id = uuid.uuid4().hex
        seen_ids.add(preset_id)
        name = str(item.get("name") or "").strip() or preset_id[:8]
        values = normalize_preset_values(item.get("values"))
        presets.append(
            {
                "id": preset_id,
                "name": name,
                "values": values,
            }
        )
        if len(presets) >= MAX_SETTINGS_PRESETS:
            break
    return presets


def new_settings_preset(
    *,
    name: str = "",
    values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    preset_id = uuid.uuid4().hex
    return {
        "id": preset_id,
        "name": name.strip() or preset_id[:8],
        "values": normalize_preset_values(values or builtin_preset_values()),
    }


def clone_settings_presets(config: dict[str, Any]) -> list[dict[str, Any]]:
    return copy.deepcopy(normalize_settings_presets(config.get("settings_presets")))


def resolve_active_settings_preset_id(
    config: dict[str, Any],
    presets: list[dict[str, Any]] | None = None,
) -> str:
    active = str(config.get("active_settings_preset_id") or "").strip()
    if active == BUILTIN_SETTINGS_PRESET_ID or not active:
        return BUILTIN_SETTINGS_PRESET_ID
    named = presets if presets is not None else normalize_settings_presets(
        config.get("settings_presets")
    )
    if any(preset.get("id") == active for preset in named):
        return active
    return BUILTIN_SETTINGS_PRESET_ID


def find_settings_preset(
    presets: list[dict[str, Any]],
    preset_id: str,
) -> dict[str, Any] | None:
    for preset in presets:
        if preset.get("id") == preset_id:
            return preset
    return None


def collect_prompt_pack_from_config(
    config: dict[str, Any],
    *,
    include_dynamic: bool,
) -> dict[str, Any]:
    """Build preset values from a (pending) config dict."""
    values: dict[str, Any] = {}
    for key in SETTINGS_PRESET_CORE_KEYS:
        values[key] = copy.deepcopy(
            config[key] if key in config else _default_for_key(key)
        )
    values = normalize_preset_values(values)
    if include_dynamic:
        values["dynamic_instructions"] = str(config.get("dynamic_instructions") or "")
    return values


def prompt_pack_values_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_n = normalize_preset_values(left)
    right_n = normalize_preset_values(right)
    # Compare core always; optional only when present on either side.
    for key in SETTINGS_PRESET_CORE_KEYS:
        if left_n.get(key) != right_n.get(key):
            return False
    left_has = "dynamic_instructions" in left_n
    right_has = "dynamic_instructions" in right_n
    if left_has != right_has:
        return False
    if left_has and left_n.get("dynamic_instructions") != right_n.get(
        "dynamic_instructions"
    ):
        return False
    return True


def export_settings_presets_document(presets: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SETTINGS_PRESETS_EXPORT_SCHEMA_VERSION,
        "presets": normalize_settings_presets(presets),
    }


def parse_settings_presets_import(raw: Any) -> list[dict[str, Any]]:
    """Parse import JSON (envelope or bare list). Raises ValueError on bad shape."""
    if isinstance(raw, dict):
        version = raw.get("schema_version", 1)
        try:
            version_i = int(version)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid schema_version") from exc
        if version_i > SETTINGS_PRESETS_EXPORT_SCHEMA_VERSION:
            raise ValueError("unsupported schema_version")
        payload = raw.get("presets", raw.get("settings_presets"))
        if payload is None and any(k in raw for k in ("id", "name", "values")):
            payload = [raw]
    elif isinstance(raw, list):
        payload = raw
    else:
        raise ValueError("expected object or array")
    presets = normalize_settings_presets(payload)
    if not presets:
        raise ValueError("no presets found")
    return presets


def merge_imported_settings_presets(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Append imported presets with fresh ids. Returns (merged, added_count)."""
    merged = normalize_settings_presets(existing)
    added = 0
    for item in incoming:
        if len(merged) >= MAX_SETTINGS_PRESETS:
            break
        preset = new_settings_preset(
            name=str(item.get("name") or ""),
            values=item.get("values") if isinstance(item.get("values"), dict) else {},
        )
        merged.append(preset)
        added += 1
    return merged, added


def dumps_settings_presets_export(presets: list[dict[str, Any]]) -> str:
    return json.dumps(
        export_settings_presets_document(presets),
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def loads_settings_presets_import(text: str) -> list[dict[str, Any]]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid json") from exc
    return parse_settings_presets_import(raw)
