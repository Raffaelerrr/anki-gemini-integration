from __future__ import annotations

from typing import Any

from .i18n import tr


def empty_field_placeholder(config: dict[str, Any] | None = None) -> str:
    return tr("chat.context.empty_field", config=config)


def send_empty_note_fields(config: dict[str, Any] | None) -> bool:
    return bool((config or {}).get("chat_send_empty_fields", False))


def format_note_context(fields: list[tuple[str, str]], config: dict[str, Any]) -> str:
    include_empty = send_empty_note_fields(config)
    placeholder = empty_field_placeholder(config)
    lines: list[str] = []
    for name, value in fields:
        stripped = value.strip()
        if not stripped:
            if not include_empty:
                continue
            display = placeholder
        else:
            display = value
        lines.append(f"{tr('chat.context.field', config=config, name=name)}\n{display}")
    return "\n\n".join(lines)


def fields_for_note_preview(
    fields: list[tuple[str, str]],
    config: dict[str, Any],
) -> list[tuple[str, str]]:
    include_empty = send_empty_note_fields(config)
    placeholder = empty_field_placeholder(config)
    preview_fields: list[tuple[str, str]] = []
    for name, value in fields:
        if value.strip():
            preview_fields.append((name, value))
        elif include_empty:
            preview_fields.append((name, placeholder))
        else:
            preview_fields.append((name, value))
    return preview_fields
