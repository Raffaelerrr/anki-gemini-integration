from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

_APPLY_NOTE_TAG_RE = re.compile(
    r"<\s*APPLY_NOTE\s*>(.*?)</\s*APPLY_NOTE\s*>",
    re.DOTALL | re.IGNORECASE,
)
_MARKDOWN_FENCE_RE = re.compile(
    r"^```[^\n]*\n(.*?)(?:\n```)\s*$",
    re.DOTALL,
)

NoteApplyMode = Literal["update", "create"]

DEFAULT_APPLY_HISTORY_MAX = 7
MIN_APPLY_HISTORY_MAX = 1
MAX_APPLY_HISTORY_MAX = 30


def clamp_apply_history_max(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return DEFAULT_APPLY_HISTORY_MAX
    return max(MIN_APPLY_HISTORY_MAX, min(MAX_APPLY_HISTORY_MAX, n))


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


@dataclass(frozen=True)
class FieldMappingReport:
    """How proposed field names line up with a note type's fields."""

    matched: tuple[str, ...] = ()
    missing_in_proposal: tuple[str, ...] = ()
    extra_in_proposal: tuple[str, ...] = ()

    @property
    def overlap_score(self) -> float:
        """Jaccard overlap of field-name sets (case-insensitive)."""
        matched = len(self.matched)
        total = matched + len(self.missing_in_proposal) + len(self.extra_in_proposal)
        if total <= 0:
            return 0.0
        return matched / total

    @property
    def has_mismatches(self) -> bool:
        return bool(self.missing_in_proposal or self.extra_in_proposal)


@dataclass(frozen=True)
class AvailableNotetype:
    """A local or session note type that can receive a create/update mapping."""

    notetype_id: int
    name: str
    field_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class ImportedNoteTarget:
    """Imported session note scored as an update target for a proposal."""

    note_id: int
    notetype_id: int
    notetype_name: str
    label: str
    score: float
    report: FieldMappingReport
    preferred: bool = False


@dataclass(frozen=True)
class NotetypeCreateMatch:
    """Note type scored as a create-new destination for a proposal."""

    notetype: AvailableNotetype
    score: float
    report: FieldMappingReport


@dataclass(frozen=True)
class NoteApplyPlan:
    """User-confirmed apply intent from the preview dialog."""

    mode: NoteApplyMode
    proposal_index: int
    proposal: NoteApplyNote
    target_note_id: int | None = None
    target_notetype_id: int | None = None
    target_notetype_name: str | None = None
    field_report: FieldMappingReport | None = None
    history_item_id: str | None = None


@dataclass(frozen=True)
class NoteApplyExecutionResult:
    """Outcome of executing a confirmed apply plan against Anki."""

    ok: bool
    mode: NoteApplyMode
    message_key: str
    message_kwargs: dict[str, Any] = field(default_factory=dict)
    updated_fields: tuple[str, ...] = ()
    note_id: int | None = None


@dataclass
class ApplyHistoryItem:
    """One Gemini-proposed note kept in the session apply history."""

    item_id: str
    proposal: NoteApplyNote
    seq: int
    applied: bool = False


class ApplyNoteHistory:
    """FIFO session history of APPLY_NOTE proposals (cap from settings)."""

    def __init__(self, max_items: int = DEFAULT_APPLY_HISTORY_MAX) -> None:
        self._items: list[ApplyHistoryItem] = []
        self._max_items = clamp_apply_history_max(max_items)
        self._next_seq = 1
        self._next_id = 1
        self._last_offered_id: str | None = None

    @property
    def items(self) -> list[ApplyHistoryItem]:
        return list(self._items)

    @property
    def max_items(self) -> int:
        return self._max_items

    def __len__(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()
        self._last_offered_id = None

    def set_max_items(self, max_items: int) -> None:
        self._max_items = clamp_apply_history_max(max_items)
        self._trim()

    def extend_from_batch(self, batch: NoteApplyBatch) -> list[ApplyHistoryItem]:
        """Append each note from a batch; drop oldest when over capacity."""
        added: list[ApplyHistoryItem] = []
        for note in batch.notes:
            item = ApplyHistoryItem(
                item_id=f"a{self._next_id}",
                proposal=note,
                seq=self._next_seq,
                applied=False,
            )
            self._next_id += 1
            self._next_seq += 1
            self._items.append(item)
            added.append(item)
        self._trim()
        return added

    def get(self, item_id: str) -> ApplyHistoryItem | None:
        for item in self._items:
            if item.item_id == item_id:
                return item
        return None

    def mark_applied(self, item_id: str) -> bool:
        item = self.get(item_id)
        if item is None:
            return False
        item.applied = True
        return True

    def has_unapplied(self) -> bool:
        return any(not item.applied for item in self._items)

    def earliest_unapplied(self) -> ApplyHistoryItem | None:
        for item in self._items:
            if not item.applied:
                return item
        return None

    def suggest_focus_item(self) -> ApplyHistoryItem | None:
        """Earliest unapplied, or the next unapplied after the last offered skip."""
        unapplied = [item for item in self._items if not item.applied]
        if not unapplied:
            return None
        if self._last_offered_id is None:
            return unapplied[0]
        last = self.get(self._last_offered_id)
        if last is None:
            return unapplied[0]
        later = [item for item in unapplied if item.seq > last.seq]
        if later:
            return later[0]
        return unapplied[0]

    def remember_offered(self, item_id: str) -> None:
        if self.get(item_id) is not None:
            self._last_offered_id = item_id

    def _trim(self) -> None:
        while len(self._items) > self._max_items:
            dropped = self._items.pop(0)
            if self._last_offered_id == dropped.item_id:
                self._last_offered_id = None


def fields_as_tuples(note: NoteApplyNote) -> list[tuple[str, str]]:
    """Convert proposal fields to the editor's list-of-tuples shape."""
    return [(name, value) for name, value in note.fields.items()]


def mapped_field_values(
    proposal_fields: dict[str, str],
    model_field_names: Iterable[str],
) -> dict[str, str]:
    """Map proposal values onto model field names (case-insensitive).

    Extra proposal fields are dropped. Model fields with no proposal value
    are omitted so callers leave those Anki fields unchanged.
    """
    prop_by_lower: dict[str, str] = {}
    for name, value in (proposal_fields or {}).items():
        key = str(name or "").strip().lower()
        if key and key not in prop_by_lower:
            prop_by_lower[key] = str(value if value is not None else "")

    mapped: dict[str, str] = {}
    for model_name in model_field_names:
        text = str(model_name or "").strip()
        if not text:
            continue
        value = prop_by_lower.get(text.lower())
        if value is not None:
            mapped[text] = value
    return mapped


def apply_mapped_fields_to_note(
    note: Any,
    mapped_fields: dict[str, str],
    *,
    tags: list[str] | None = None,
) -> list[str]:
    """Write mapped fields onto an Anki note-like object.

    Returns the model field names that were written. When ``tags`` is not
    ``None``, replaces ``note.tags`` (use an empty list to clear tags). When
    ``tags`` is ``None``, existing tags are left unchanged.
    """
    updated: list[str] = []
    for name, value in mapped_fields.items():
        try:
            note[name] = value
        except Exception:
            # Fall back to fields[] by matching note.keys()/items() when available.
            try:
                keys = list(note.keys())
                index = next(
                    (
                        i
                        for i, key in enumerate(keys)
                        if str(key).strip().lower() == name.lower()
                    ),
                    None,
                )
                if index is None:
                    continue
                note.fields[index] = value
            except Exception:
                continue
        updated.append(name)
    if tags is not None:
        try:
            note.tags = list(tags)
        except Exception:
            pass
    return updated


def proposal_tags_for_apply(proposal: NoteApplyNote) -> list[str] | None:
    """Tags to write on apply: replace when the proposal lists any; else leave alone."""
    tags = list(proposal.tags or [])
    return tags if tags else None


def model_field_names_from_note(note: Any) -> list[str]:
    """Best-effort field names from an Anki note or note type dict."""
    try:
        model = note.note_type()
        return [
            str(fld.get("name") or "").strip()
            for fld in model.get("flds", [])
            if str(fld.get("name") or "").strip()
        ]
    except Exception:
        pass
    try:
        return [str(name) for name, _value in note.items()]
    except Exception:
        return []


def proposal_with_fields(
    note: NoteApplyNote,
    fields: list[tuple[str, str]] | dict[str, str],
) -> NoteApplyNote:
    """Return a copy of ``note`` with replaced field values."""
    if isinstance(fields, dict):
        normalized = _normalize_fields(fields) or {}
    else:
        normalized = _normalize_fields({name: value for name, value in fields}) or {}
    return NoteApplyNote(
        fields=normalized,
        notetype=note.notetype,
        deck=note.deck,
        tags=list(note.tags),
    )


def field_mapping_report(
    proposed_fields: dict[str, str] | Iterable[str],
    model_field_names: Iterable[str],
) -> FieldMappingReport:
    """Compare proposed field names against a note type's field names."""
    if isinstance(proposed_fields, dict):
        proposed_names = list(proposed_fields.keys())
    else:
        proposed_names = [str(name) for name in proposed_fields]

    prop_by_lower: dict[str, str] = {}
    for name in proposed_names:
        text = str(name or "").strip()
        if text:
            prop_by_lower.setdefault(text.lower(), text)

    model_by_lower: dict[str, str] = {}
    for name in model_field_names:
        text = str(name or "").strip()
        if text:
            model_by_lower.setdefault(text.lower(), text)

    matched = tuple(
        model_by_lower[key] for key in model_by_lower if key in prop_by_lower
    )
    missing = tuple(
        model_by_lower[key] for key in model_by_lower if key not in prop_by_lower
    )
    extra = tuple(
        prop_by_lower[key] for key in prop_by_lower if key not in model_by_lower
    )
    return FieldMappingReport(
        matched=matched,
        missing_in_proposal=missing,
        extra_in_proposal=extra,
    )


def _notetype_name_bonus(proposal_name: str | None, candidate_name: str) -> float:
    left = (proposal_name or "").strip().lower()
    right = (candidate_name or "").strip().lower()
    if not left or not right:
        return 0.0
    if left == right:
        return 0.35
    if left in right or right in left:
        return 0.15
    return 0.0


def score_proposal_against_fields(
    proposal: NoteApplyNote,
    field_names: Iterable[str],
    *,
    notetype_name: str = "",
) -> tuple[float, FieldMappingReport]:
    report = field_mapping_report(proposal.fields, field_names)
    score = report.overlap_score + _notetype_name_bonus(proposal.notetype, notetype_name)
    return min(1.0, score), report


def rank_imported_update_targets(
    proposal: NoteApplyNote,
    imported_notes: Iterable[Any],
) -> list[ImportedNoteTarget]:
    """Rank imported session notes as update targets (best first)."""
    ranked: list[ImportedNoteTarget] = []
    for note in imported_notes:
        field_names = [name for name, _value in getattr(note, "fields", [])]
        score, report = score_proposal_against_fields(
            proposal,
            field_names,
            notetype_name=str(getattr(note, "notetype_name", "") or ""),
        )
        if report.overlap_score <= 0 and not _notetype_name_bonus(
            proposal.notetype,
            str(getattr(note, "notetype_name", "") or ""),
        ):
            # Still list imported notes so the user can pick them; score stays low.
            pass
        label = ""
        if hasattr(note, "display_label") and callable(note.display_label):
            label = str(note.display_label())
        else:
            label = f"#{getattr(note, 'note_id', '?')}"
        ranked.append(
            ImportedNoteTarget(
                note_id=int(note.note_id),
                notetype_id=int(note.notetype_id),
                notetype_name=str(getattr(note, "notetype_name", "") or ""),
                label=label,
                score=score,
                report=report,
            )
        )
    ranked.sort(key=lambda item: (-item.score, item.label.lower(), item.note_id))
    if not ranked:
        return []
    best = ranked[0]
    return [
        ImportedNoteTarget(
            note_id=item.note_id,
            notetype_id=item.notetype_id,
            notetype_name=item.notetype_name,
            label=item.label,
            score=item.score,
            report=item.report,
            preferred=(item.note_id == best.note_id),
        )
        for item in ranked
    ]


def suggest_imported_update_target(
    proposal: NoteApplyNote,
    imported_notes: Iterable[Any],
) -> ImportedNoteTarget | None:
    ranked = rank_imported_update_targets(proposal, imported_notes)
    return ranked[0] if ranked else None


def rank_notetypes_for_create(
    proposal: NoteApplyNote,
    available: Iterable[AvailableNotetype],
) -> list[NotetypeCreateMatch]:
    """Rank note types for create-new; omit types with zero field overlap."""
    matches: list[NotetypeCreateMatch] = []
    for notetype in available:
        score, report = score_proposal_against_fields(
            proposal,
            notetype.field_names,
            notetype_name=notetype.name,
        )
        if report.overlap_score <= 0:
            continue
        matches.append(
            NotetypeCreateMatch(notetype=notetype, score=score, report=report)
        )
    matches.sort(
        key=lambda item: (
            -item.score,
            item.notetype.name.lower(),
            item.notetype.notetype_id,
        )
    )
    return matches


def collect_available_notetypes(
    *,
    session_notetypes: Iterable[Any] | None = None,
    include_collection: bool = True,
) -> list[AvailableNotetype]:
    """Build create-target candidates from session imports and/or the collection."""
    by_id: dict[int, AvailableNotetype] = {}

    for data in session_notetypes or ():
        try:
            notetype_id = int(data.notetype_id)
        except Exception:
            continue
        names = tuple(
            str(name).strip()
            for name in getattr(data, "field_names", []) or []
            if str(name).strip()
        )
        by_id[notetype_id] = AvailableNotetype(
            notetype_id=notetype_id,
            name=str(getattr(data, "name", "") or "").strip() or f"#{notetype_id}",
            field_names=names,
        )

    if include_collection:
        try:
            from aqt import mw

            col = mw.col if mw is not None else None
            if col is not None:
                for model in col.models.all():
                    notetype_id = int(model["id"])
                    names = tuple(
                        str(fld.get("name") or "").strip()
                        for fld in model.get("flds", [])
                        if str(fld.get("name") or "").strip()
                    )
                    by_id[notetype_id] = AvailableNotetype(
                        notetype_id=notetype_id,
                        name=str(model.get("name") or "").strip() or f"#{notetype_id}",
                        field_names=names,
                    )
        except Exception:
            pass

    return sorted(
        by_id.values(),
        key=lambda item: (item.name.lower(), item.notetype_id),
    )


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


def _strip_markdown_fence(payload: str) -> str:
    text = (payload or "").strip()
    match = _MARKDOWN_FENCE_RE.match(text)
    if match:
        return match.group(1).strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def _repair_invalid_json_escapes(payload: str) -> str:
    """Double backslashes that are not valid JSON escapes (common with MathJax)."""
    out: list[str] = []
    i = 0
    length = len(payload)
    while i < length:
        ch = payload[i]
        if ch != "\\" or i + 1 >= length:
            out.append(ch)
            i += 1
            continue
        nxt = payload[i + 1]
        if nxt in '"\\/bfnrt':
            out.append(ch)
            out.append(nxt)
            i += 2
            continue
        if (
            nxt == "u"
            and i + 5 < length
            and all(c in "0123456789abcdefABCDEF" for c in payload[i + 2 : i + 6])
        ):
            out.append(payload[i : i + 6])
            i += 6
            continue
        out.append("\\\\")
        i += 1
    return "".join(out)


def _loads_apply_json(payload: str) -> Any | None:
    """Parse JSON object/array, ignoring trailing junk after the first value."""
    text = (payload or "").lstrip()
    if not text:
        return None
    decoder = json.JSONDecoder()
    try:
        data, _end = decoder.raw_decode(text)
        return data
    except json.JSONDecodeError:
        start = text.find("{")
        if start < 0:
            start = text.find("[")
        if start < 0:
            return None
        try:
            data, _end = decoder.raw_decode(text[start:])
            return data
        except json.JSONDecodeError:
            return None


def _batch_from_parsed_data(data: Any) -> NoteApplyBatch | None:
    if isinstance(data, dict) and isinstance(data.get("notes"), list):
        notes = [_parse_note_object(item) for item in data["notes"]]
        parsed = [note for note in notes if note is not None]
        return NoteApplyBatch(notes=parsed) if parsed else None

    single = _parse_note_object(data)
    if single is None:
        return None
    return NoteApplyBatch(notes=[single])


def parse_apply_note_payload(raw_payload: str) -> NoteApplyBatch | None:
    """Parse JSON inside an APPLY_NOTE block."""
    payload = _strip_markdown_fence(raw_payload or "")
    if not payload:
        return None

    candidates = [payload]
    repaired = _repair_invalid_json_escapes(payload)
    if repaired != payload:
        candidates.append(repaired)

    for candidate in candidates:
        data = _loads_apply_json(candidate)
        if data is None:
            continue
        batch = _batch_from_parsed_data(data)
        if batch is not None:
            return batch
    return None


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

def apply_note_tags_present(text: str) -> bool:
    """True if the reply contains an APPLY_NOTE block (valid or not)."""
    return bool(_APPLY_NOTE_TAG_RE.search(text or ""))