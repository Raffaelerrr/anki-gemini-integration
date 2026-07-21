from __future__ import annotations

import copy
import json
import uuid
from typing import Any

MAX_SETTINGS_PRESETS = 20
BUILTIN_SETTINGS_PRESET_ID = "builtin_default"
SETTINGS_PRESETS_EXPORT_SCHEMA_VERSION = 2

# Prompt pack keys always stored on named presets (and on Builtin Default).
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
    "mathjax_preview_preamble",
)

# Optional on named presets; Builtin Default always includes "".
SETTINGS_PRESET_OPTIONAL_KEYS: tuple[str, ...] = ("dynamic_instructions",)

# Separate runtime pack (models / temps / thinking).
SETTINGS_PRESET_RUNTIME_KEYS: tuple[str, ...] = (
    "model_optimize",
    "model_chat",
    "thinking_budget_optimize",
    "thinking_budget_chat",
    "temperature_optimize",
    "temperature_chat",
)

SETTINGS_PRESET_ALL_KEYS: tuple[str, ...] = (
    SETTINGS_PRESET_CORE_KEYS + SETTINGS_PRESET_OPTIONAL_KEYS
)

_PRESET_SUMMARY_LABELS: dict[str, str] = {
    "system_instruction": "system instruction",
    "system_instruction_shared": "shared system instruction",
    "system_instruction_optimize": "optimize system instruction",
    "system_instruction_chat": "chat system instruction",
    "brain_import_message": "brain import message",
    "prompt_optimize_user": "optimize user prompt",
    "prompt_chat_addon": "chat system addon",
    "prompt_dynamic_rules_prefix": "dynamic rules prefix",
    "prompt_chat_context_order": "wrapper order",
    "prompt_chat_context_sections": "wrapper sections",
    "prompt_card_templates_format": "format guide",
    "mathjax_preview_preamble": "MathJax preamble",
    "dynamic_instructions": "dynamic instructions",
    "model_optimize": "optimize model",
    "model_chat": "chat model",
    "thinking_budget_optimize": "optimize thinking budget",
    "thinking_budget_chat": "chat thinking budget",
    "temperature_optimize": "optimize temperature",
    "temperature_chat": "chat temperature",
}


def _default_for_key(key: str) -> Any:
    from .config import DEFAULT_CONFIG

    return copy.deepcopy(DEFAULT_CONFIG[key])


def builtin_preset_values() -> dict[str, Any]:
    """Factory prompt-pack values for the non-deletable Default preset."""
    values: dict[str, Any] = {}
    for key in SETTINGS_PRESET_CORE_KEYS:
        values[key] = _default_for_key(key)
    values["dynamic_instructions"] = ""
    return values


def builtin_runtime_values() -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key in SETTINGS_PRESET_RUNTIME_KEYS:
        values[key] = _default_for_key(key)
    return values


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
    if key in {"thinking_budget_optimize", "thinking_budget_chat"}:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return int(_default_for_key(key))
    if key in {"temperature_optimize", "temperature_chat"}:
        try:
            return float(raw)
        except (TypeError, ValueError):
            return float(_default_for_key(key))
    if key in {"model_optimize", "model_chat"}:
        text = str(raw or "").strip()
        return text or str(_default_for_key(key))
    if key in SETTINGS_PRESET_ALL_KEYS:
        return "" if raw is None else str(raw)
    return raw


def normalize_preset_values(
    raw: Any,
    *,
    include_optional_absent: bool = False,
) -> dict[str, Any]:
    """Normalize a prompt-pack values dict."""
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


def normalize_runtime_values(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    if not any(key in raw for key in SETTINGS_PRESET_RUNTIME_KEYS):
        return None
    values: dict[str, Any] = {}
    for key in SETTINGS_PRESET_RUNTIME_KEYS:
        if key in raw:
            values[key] = _normalize_pack_value(key, raw.get(key))
        else:
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
        runtime = normalize_runtime_values(item.get("runtime"))
        entry: dict[str, Any] = {
            "id": preset_id,
            "name": name,
            "values": values,
        }
        if runtime is not None:
            entry["runtime"] = runtime
        presets.append(entry)
        if len(presets) >= MAX_SETTINGS_PRESETS:
            break
    return presets


def new_settings_preset(
    *,
    name: str = "",
    values: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    preset_id = uuid.uuid4().hex
    entry: dict[str, Any] = {
        "id": preset_id,
        "name": name.strip() or preset_id[:8],
        "values": normalize_preset_values(values or builtin_preset_values()),
    }
    normalized_runtime = normalize_runtime_values(runtime)
    if normalized_runtime is not None:
        entry["runtime"] = normalized_runtime
    return entry


def duplicate_settings_preset(
    preset: dict[str, Any],
    *,
    name: str = "",
) -> dict[str, Any]:
    base_name = name.strip() or f"{str(preset.get('name') or 'preset').strip()} copy"
    return new_settings_preset(
        name=base_name,
        values=preset.get("values") if isinstance(preset.get("values"), dict) else {},
        runtime=preset.get("runtime") if isinstance(preset.get("runtime"), dict) else None,
    )


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


def resolve_preset_payload(
    presets: list[dict[str, Any]],
    preset_id: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return (values, runtime) for builtin or named preset."""
    if preset_id == BUILTIN_SETTINGS_PRESET_ID or not preset_id:
        # Builtin is prompt-pack only (plus empty dynamic). Runtime stays opt-in
        # on named presets so loading Default does not reset models/temps.
        return builtin_preset_values(), None
    preset = find_settings_preset(presets, preset_id)
    if preset is None:
        return builtin_preset_values(), None
    values = normalize_preset_values(preset.get("values"))
    runtime = normalize_runtime_values(preset.get("runtime"))
    return values, runtime


def collect_prompt_pack_from_config(
    config: dict[str, Any],
    *,
    include_dynamic: bool,
) -> dict[str, Any]:
    """Build prompt-pack values from a (pending) config dict."""
    values: dict[str, Any] = {}
    for key in SETTINGS_PRESET_CORE_KEYS:
        values[key] = copy.deepcopy(
            config[key] if key in config else _default_for_key(key)
        )
    values = normalize_preset_values(values)
    if include_dynamic:
        values["dynamic_instructions"] = str(config.get("dynamic_instructions") or "")
    return values


def collect_runtime_pack_from_config(config: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key in SETTINGS_PRESET_RUNTIME_KEYS:
        values[key] = copy.deepcopy(
            config[key] if key in config else _default_for_key(key)
        )
    return normalize_runtime_values(values) or builtin_runtime_values()


def prompt_pack_values_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_n = normalize_preset_values(left)
    right_n = normalize_preset_values(right)
    for key in SETTINGS_PRESET_CORE_KEYS:
        if left_n.get(key) != right_n.get(key):
            return False
    left_has = "dynamic_instructions" in left
    right_has = "dynamic_instructions" in right
    if left_has != right_has:
        return False
    if left_has and str(left.get("dynamic_instructions") or "") != str(
        right.get("dynamic_instructions") or ""
    ):
        return False
    return True


def runtime_pack_values_equal(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
) -> bool:
    left_n = normalize_runtime_values(left)
    right_n = normalize_runtime_values(right)
    if left_n is None and right_n is None:
        return True
    if left_n is None or right_n is None:
        return False
    return left_n == right_n


def _summarize_value(value: Any, *, limit: int = 80) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, list):
        text = ", ".join(str(item) for item in value)
    elif isinstance(value, dict):
        text = f"{len(value)} override(s)" if value else "(empty)"
    else:
        text = str(value).replace("\n", " ").strip()
    if not text:
        return "(empty)"
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def preset_diff_from_builtin(
    values: dict[str, Any],
    runtime: dict[str, Any] | None = None,
) -> list[str]:
    """Human-readable lines for how a preset differs from Builtin Default."""
    builtin_values = builtin_preset_values()
    normalized = normalize_preset_values(values)
    lines: list[str] = []
    for key in SETTINGS_PRESET_CORE_KEYS:
        if normalized.get(key) == builtin_values.get(key):
            continue
        label = _PRESET_SUMMARY_LABELS.get(key, key)
        lines.append(f"{label}: {_summarize_value(normalized.get(key))}")
    if "dynamic_instructions" in values:
        left = str(values.get("dynamic_instructions") or "")
        right = str(builtin_values.get("dynamic_instructions") or "")
        if left != right:
            label = _PRESET_SUMMARY_LABELS["dynamic_instructions"]
            lines.append(f"{label}: {_summarize_value(left)}")

    runtime_n = normalize_runtime_values(runtime)
    if runtime_n is not None:
        builtin_runtime = builtin_runtime_values()
        runtime_diffs = 0
        for key in SETTINGS_PRESET_RUNTIME_KEYS:
            if runtime_n.get(key) == builtin_runtime.get(key):
                continue
            runtime_diffs += 1
            label = _PRESET_SUMMARY_LABELS.get(key, key)
            lines.append(f"{label}: {_summarize_value(runtime_n.get(key))}")
        if runtime_diffs == 0:
            lines.append("runtime: factory defaults")
    return lines


def apply_preset_to_config(
    config: dict[str, Any],
    *,
    values: dict[str, Any],
    runtime: dict[str, Any] | None = None,
    apply_runtime: bool = True,
) -> dict[str, Any]:
    """Merge preset packs into a config dict (does not save)."""
    merged = dict(config)
    normalized = normalize_preset_values(values)
    for key in SETTINGS_PRESET_CORE_KEYS:
        merged[key] = copy.deepcopy(normalized[key])
    if "dynamic_instructions" in values:
        merged["dynamic_instructions"] = str(values.get("dynamic_instructions") or "")
    if apply_runtime:
        runtime_n = normalize_runtime_values(runtime)
        if runtime_n is not None:
            for key in SETTINGS_PRESET_RUNTIME_KEYS:
                merged[key] = copy.deepcopy(runtime_n[key])
    return merged


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
            runtime=item.get("runtime") if isinstance(item.get("runtime"), dict) else None,
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
