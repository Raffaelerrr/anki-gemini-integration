from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

_APPLY_NOTE_TAG_RE = re.compile(r"<APPLY_NOTE>(.*?)</APPLY_NOTE>", re.DOTALL)


@dataclass(frozen=True)
class NoteApplyNote:
    """One note worth of field values Gemini proposes applying to Anki."""

    fields: dict[str, str]
    notetype: str | None = None
    deck: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NoteApplyBatch:
    """One or more notes parsed from an APPLY_NOTE block."""

    notes: list[NoteApplyNote]

    @property
    def note_count(self) -> int:
        return len(self.notes)

    def field_names_summary(self) -> str:
        names: list[str] = []
        seen: set[str] = set()
        for note in self.notes:
            for name in note.fields:
                lowered = name.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                names.append(name)
        return ", ".join(names)


def _normalize_tags(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    tags: list[str] = []
    for item in raw:
        text = str(item or "").strip()
        if text:
            tags.append(text)
    return tags


def _normalize_fields(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict) or not raw:
        return None
    fields: dict[str, str] = {}
    for key, value in raw.items():
        name = str(key or "").strip()
        if not name:
            continue
        fields[name] = str(value if value is not None else "")
    return fields or None


def _parse_note_object(raw: Any) -> NoteApplyNote | None:
    if not isinstance(raw, dict):
        return None
    fields = _normalize_fields(raw.get("fields"))
    if fields is None:
        return None
    notetype = str(raw.get("notetype") or "").strip() or None
    deck = str(raw.get("deck") or "").strip() or None
    return NoteApplyNote(
        fields=fields,
        notetype=notetype,
        deck=deck,
        tags=_normalize_tags(raw.get("tags")),
    )


def parse_apply_note_payload(raw_payload: str) -> NoteApplyBatch | None:
    """Parse JSON inside an APPLY_NOTE block."""
    payload = (raw_payload or "").strip()
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    if isinstance(data, dict) and isinstance(data.get("notes"), list):
        notes = [_parse_note_object(item) for item in data["notes"]]
        parsed = [note for note in notes if note is not None]
        return NoteApplyBatch(notes=parsed) if parsed else None

    single = _parse_note_object(data)
    if single is None:
        return None
    return NoteApplyBatch(notes=[single])


def format_apply_batch_for_display(batch: NoteApplyBatch) -> str:
    """Rebuild per-field code blocks for the chat log after APPLY_NOTE is stripped."""
    parts: list[str] = []
    for index, note in enumerate(batch.notes, start=1):
        if batch.note_count > 1:
            header = f"Note {index}"
            meta: list[str] = []
            if note.notetype:
                meta.append(f"notetype: {note.notetype}")
            if note.deck:
                meta.append(f"deck: {note.deck}")
            if note.tags:
                meta.append(f"tags: {', '.join(note.tags)}")
            if meta:
                header = f"{header} ({'; '.join(meta)})"
            parts.append(f"### {header}")
        for name, value in note.fields.items():
            parts.append(f"{name}:\n```\n{value}\n```")
    return "\n\n".join(parts)


def extract_apply_note(text: str) -> tuple[str, NoteApplyBatch | None]:
    """Remove APPLY_NOTE tags from visible chat text and parse the payload."""
    match = _APPLY_NOTE_TAG_RE.search(text)
    if not match:
        return text, None

    batch = parse_apply_note_payload(match.group(1))
    if batch is None:
        # Keep malformed blocks visible so field content is not lost silently.
        return text, None

    cleaned = _APPLY_NOTE_TAG_RE.sub("", text).strip()
    return cleaned, batch
