from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from .i18n import tr

_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_WHITESPACE = re.compile(r"\s+")
_NOTE_LABEL_MAX = 48


@dataclass
class ImportedNoteData:
    """Session copy of one imported note's field content."""

    note_id: int
    notetype_id: int
    notetype_name: str = ""
    fields: list[tuple[str, str]] = field(default_factory=list)

    def display_label(self) -> str:
        preview = first_nonempty_field_preview(self.fields)
        type_name = (self.notetype_name or "").strip()
        if preview and type_name:
            return f"{type_name}: {preview}"
        if preview:
            return preview
        if type_name:
            return f"{type_name} #{self.note_id}"
        return f"#{self.note_id}"


def empty_field_placeholder(config: dict[str, Any] | None = None) -> str:
    return tr("chat.context.empty_field", config=config)


def send_empty_note_fields(config: dict[str, Any] | None) -> bool:
    return bool((config or {}).get("chat_send_empty_fields", False))


def first_nonempty_field_preview(
    fields: list[tuple[str, str]],
    *,
    max_len: int = _NOTE_LABEL_MAX,
) -> str:
    for _name, value in fields:
        plain = _WHITESPACE.sub(" ", _HTML_TAG.sub(" ", value)).strip()
        if not plain:
            continue
        if len(plain) > max_len:
            return plain[: max_len - 1].rstrip() + "…"
        return plain
    return ""


def imported_note_from_anki_note(note: Any) -> ImportedNoteData | None:
    """Build session note data from an Anki note-like object (`items`, `id`, `mid`)."""
    try:
        note_id = int(note.id)
        notetype_id = int(note.mid)
    except Exception:
        return None
    fields: list[tuple[str, str]] = list(note.items())
    if not any(value.strip() for _, value in fields):
        return None
    notetype_name = ""
    try:
        from aqt import mw

        model = mw.col.models.get(notetype_id) if mw.col is not None else None
        if model is not None:
            notetype_name = str(model.get("name") or "").strip()
    except Exception:
        notetype_name = ""
    return ImportedNoteData(
        note_id=note_id,
        notetype_id=notetype_id,
        notetype_name=notetype_name,
        fields=fields,
    )


def merge_imported_notes(
    existing: dict[int, ImportedNoteData],
    incoming: Iterable[ImportedNoteData],
) -> dict[int, ImportedNoteData]:
    """Accumulate notes by id; re-import of the same id replaces that entry."""
    merged = dict(existing)
    for note in incoming:
        merged[note.note_id] = ImportedNoteData(
            note_id=note.note_id,
            notetype_id=note.notetype_id,
            notetype_name=(note.notetype_name or "").strip()
            or (merged.get(note.note_id).notetype_name if note.note_id in merged else ""),
            fields=list(note.fields),
        )
    return merged


def ordered_imported_notes(
    notes: dict[int, ImportedNoteData],
) -> list[ImportedNoteData]:
    return sorted(
        notes.values(),
        key=lambda item: (
            (item.notetype_name or "").lower(),
            item.display_label().lower(),
            item.note_id,
        ),
    )


def format_note_context(
    fields: list[tuple[str, str]],
    config: dict[str, Any],
    *,
    notetype_name: str | None = None,
    note_label: str | None = None,
    note_id: int | None = None,
) -> str:
    include_empty = send_empty_note_fields(config)
    placeholder = empty_field_placeholder(config)
    lines: list[str] = []
    label = (note_label or "").strip()
    if label:
        lines.append(tr("chat.context.imported_note", config=config, label=label))
    elif note_id is not None:
        lines.append(tr("chat.context.imported_note_id", config=config, note_id=note_id))
    name = (notetype_name or "").strip()
    if name:
        lines.append(tr("chat.context.imported_notetype", config=config, name=name))
    for field_name, value in fields:
        stripped = value.strip()
        if not stripped:
            if not include_empty:
                continue
            display = placeholder
        else:
            display = value
        lines.append(f"{tr('chat.context.field', config=config, name=field_name)}\n{display}")
    return "\n\n".join(lines)


def format_imported_notes_context(
    notes: dict[int, ImportedNoteData] | Iterable[ImportedNoteData],
    config: dict[str, Any],
    *,
    include_note_ids: set[int] | None = None,
) -> str:
    if isinstance(notes, dict):
        ordered = ordered_imported_notes(notes)
    else:
        ordered = ordered_imported_notes({item.note_id: item for item in notes})
    blocks: list[str] = []
    for note in ordered:
        if include_note_ids is not None and note.note_id not in include_note_ids:
            continue
        block = format_note_context(
            note.fields,
            config,
            notetype_name=note.notetype_name,
            note_label=note.display_label(),
            note_id=note.note_id,
        )
        if block:
            blocks.append(block)
    return "\n\n".join(blocks)


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
