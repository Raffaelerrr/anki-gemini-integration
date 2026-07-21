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


UpdateTargetSource = Literal["imported", "collection", "browser"]


@dataclass(frozen=True)
class ImportedNoteTarget:
    """Note scored as an update target for a proposal (imported or collection)."""

    note_id: int
    notetype_id: int
    notetype_name: str
    label: str
    score: float
    report: FieldMappingReport
    preferred: bool = False
    source: UpdateTargetSource = "imported"


@dataclass(frozen=True)
class ApplyUndoSnapshot:
    """Previous field/tag values for one successful collection update."""

    note_id: int
    fields: dict[str, str]
    tags: tuple[str, ...] = ()


_last_apply_undo: ApplyUndoSnapshot | None = None


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


def clear_apply_undo() -> None:
    global _last_apply_undo
    _last_apply_undo = None


def store_apply_undo(snapshot: ApplyUndoSnapshot) -> None:
    global _last_apply_undo
    _last_apply_undo = snapshot


def peek_apply_undo() -> ApplyUndoSnapshot | None:
    return _last_apply_undo


def has_apply_undo() -> bool:
    return _last_apply_undo is not None


def take_apply_undo() -> ApplyUndoSnapshot | None:
    global _last_apply_undo
    snapshot = _last_apply_undo
    _last_apply_undo = None
    return snapshot


def snapshot_note_for_undo(note: Any) -> ApplyUndoSnapshot | None:
    """Capture current field/tag values before an update write."""
    try:
        note_id = int(note.id)
    except Exception:
        return None
    fields: dict[str, str] = {}
    try:
        for name, value in note.items():
            fields[str(name)] = str(value if value is not None else "")
    except Exception:
        try:
            names = list(note.keys())
            values = list(note.fields)
            for name, value in zip(names, values):
                fields[str(name)] = str(value if value is not None else "")
        except Exception:
            return None
    tags: tuple[str, ...] = ()
    try:
        tags = tuple(str(tag) for tag in (note.tags or []))
    except Exception:
        tags = ()
    return ApplyUndoSnapshot(note_id=note_id, fields=fields, tags=tags)


def collection_note_still_exists(note_id: int) -> bool:
    """Return True when ``note_id`` resolves in the open collection."""
    try:
        from aqt import mw

        col = mw.col if mw is not None else None
        if col is None:
            return False
        col.get_note(int(note_id))
        return True
    except Exception:
        return False


def _target_from_note_data(
    proposal: NoteApplyNote,
    note: Any,
    *,
    source: UpdateTargetSource,
) -> ImportedNoteTarget | None:
    try:
        note_id = int(note.note_id)
        notetype_id = int(note.notetype_id)
    except Exception:
        return None
    field_names = [name for name, _value in getattr(note, "fields", [])]
    score, report = score_proposal_against_fields(
        proposal,
        field_names,
        notetype_name=str(getattr(note, "notetype_name", "") or ""),
    )
    if hasattr(note, "display_label") and callable(note.display_label):
        label = str(note.display_label())
    else:
        label = f"#{note_id}"
    return ImportedNoteTarget(
        note_id=note_id,
        notetype_id=notetype_id,
        notetype_name=str(getattr(note, "notetype_name", "") or ""),
        label=label,
        score=score,
        report=report,
        source=source,
    )


def rank_update_targets(
    proposal: NoteApplyNote,
    notes: Iterable[Any],
    *,
    source: UpdateTargetSource = "imported",
    require_overlap: bool = False,
) -> list[ImportedNoteTarget]:
    """Rank note-like objects as update targets (best first)."""
    ranked: list[ImportedNoteTarget] = []
    for note in notes:
        target = _target_from_note_data(proposal, note, source=source)
        if target is None:
            continue
        if require_overlap and target.report.overlap_score <= 0:
            continue
        ranked.append(target)
    ranked.sort(key=lambda item: (-item.score, item.label.lower(), item.note_id))
    if not ranked:
        return []
    best_id = ranked[0].note_id
    return [
        ImportedNoteTarget(
            note_id=item.note_id,
            notetype_id=item.notetype_id,
            notetype_name=item.notetype_name,
            label=item.label,
            score=item.score,
            report=item.report,
            preferred=(item.note_id == best_id),
            source=item.source,
        )
        for item in ranked
    ]


def rank_imported_update_targets(
    proposal: NoteApplyNote,
    imported_notes: Iterable[Any],
) -> list[ImportedNoteTarget]:
    """Rank imported session notes as update targets (best first)."""
    return rank_update_targets(
        proposal,
        imported_notes,
        source="imported",
        require_overlap=False,
    )


def merge_update_targets(
    *groups: Iterable[ImportedNoteTarget],
) -> list[ImportedNoteTarget]:
    """Merge target lists by note id (first occurrence wins), re-mark preferred."""
    by_id: dict[int, ImportedNoteTarget] = {}
    for group in groups:
        for item in group:
            if item.note_id not in by_id:
                by_id[item.note_id] = item
    merged = list(by_id.values())
    merged.sort(key=lambda item: (-item.score, item.label.lower(), item.note_id))
    if not merged:
        return []
    best_id = merged[0].note_id
    return [
        ImportedNoteTarget(
            note_id=item.note_id,
            notetype_id=item.notetype_id,
            notetype_name=item.notetype_name,
            label=item.label,
            score=item.score,
            report=item.report,
            preferred=(item.note_id == best_id),
            source=item.source,
        )
        for item in merged
    ]


def suggest_imported_update_target(
    proposal: NoteApplyNote,
    imported_notes: Iterable[Any],
) -> ImportedNoteTarget | None:
    ranked = rank_imported_update_targets(proposal, imported_notes)
    return ranked[0] if ranked else None


def filter_existing_update_targets(
    targets: Iterable[ImportedNoteTarget],
) -> list[ImportedNoteTarget]:
    """Drop targets whose notes no longer exist in the collection."""
    kept = [item for item in targets if collection_note_still_exists(item.note_id)]
    return merge_update_targets(kept)


def load_collection_notes_for_notetypes(
    notetype_ids: Iterable[int],
    *,
    limit_per_type: int = 150,
    exclude_ids: Iterable[int] | None = None,
) -> list[Any]:
    """Load collection notes for the given note types (best-effort)."""
    from .note_context_fields import imported_note_from_anki_note

    exclude = {int(nid) for nid in (exclude_ids or ())}
    results: list[Any] = []
    seen: set[int] = set()
    try:
        from aqt import mw

        col = mw.col if mw is not None else None
    except Exception:
        col = None
    if col is None:
        return []

    for raw_id in notetype_ids:
        try:
            notetype_id = int(raw_id)
        except Exception:
            continue
        try:
            note_ids = list(col.find_notes(f"mid:{notetype_id}"))
        except Exception:
            continue
        for nid in note_ids[: max(1, int(limit_per_type))]:
            note_id = int(nid)
            if note_id in exclude or note_id in seen:
                continue
            try:
                note = col.get_note(note_id)
            except Exception:
                continue
            imported = imported_note_from_anki_note(note)
            if imported is None:
                continue
            seen.add(note_id)
            results.append(imported)
    return results


def load_browser_selected_notes(
    *,
    exclude_ids: Iterable[int] | None = None,
) -> list[Any]:
    """Notes currently selected in an open Browser (if any)."""
    from .note_context_fields import imported_note_from_anki_note

    exclude = {int(nid) for nid in (exclude_ids or ())}
    results: list[Any] = []
    try:
        from aqt import dialogs, mw

        if mw is None or mw.col is None:
            return []
        browser = None
        try:
            browser = dialogs._dialogs.get("Browser", [None, None])[1]
        except Exception:
            browser = None
        if browser is None:
            return []
        selected: list[int] = []
        if hasattr(browser, "selected_notes"):
            selected = [int(nid) for nid in browser.selected_notes()]
        elif hasattr(browser, "selectedNotes"):
            selected = [int(nid) for nid in browser.selectedNotes()]
        for note_id in selected:
            if note_id in exclude:
                continue
            try:
                note = mw.col.get_note(note_id)
            except Exception:
                continue
            imported = imported_note_from_anki_note(note)
            if imported is not None:
                results.append(imported)
    except Exception:
        return []
    return results


def fields_after_apply_preview(
    proposal: NoteApplyNote,
    before_fields: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Note fields as they would look after applying ``proposal`` (unmapped kept)."""
    mapped = mapped_field_values(
        proposal.fields,
        [name for name, _value in before_fields],
    )
    after: list[tuple[str, str]] = []
    for name, value in before_fields:
        if name in mapped:
            after.append((name, mapped[name]))
        else:
            after.append((name, value))
    before_lower = {str(name).strip().lower() for name, _ in before_fields}
    for name, value in proposal.fields.items():
        if str(name).strip().lower() not in before_lower:
            after.append((name, value))
    return after


def load_note_fields_for_preview(
    note_id: int,
) -> tuple[list[tuple[str, str]], int | None]:
    """Load live collection fields for before/after preview."""
    try:
        from aqt import mw

        col = mw.col if mw is not None else None
        if col is None:
            return [], None
        note = col.get_note(int(note_id))
        fields = [(str(name), str(value or "")) for name, value in note.items()]
        return fields, int(note.mid)
    except Exception:
        return [], None


def _strip_html_for_duplicate(value: str) -> str:
    text = str(value or "")
    try:
        from anki.utils import strip_html_media

        return str(strip_html_media(text) or "").strip()
    except Exception:
        return re.sub(r"<[^>]+>", "", text).strip()


def _fields_check_is_duplicate(state: Any) -> bool:
    if state is None:
        return False
    name = str(getattr(state, "name", "") or "").upper()
    if name == "DUPLICATE":
        return True
    try:
        return int(state) == 2
    except Exception:
        return "DUPLICATE" in str(state).upper()


def update_would_create_anki_duplicate(
    note_id: int,
    proposal_fields: dict[str, str],
) -> bool:
    """True when applying ``proposal_fields`` would make Anki flag a first-field duplicate.

    Matches Anki's rule: same note type + same first field (HTML stripped), excluding
    the note being updated. Empty first field is not a duplicate.
    """
    try:
        from aqt import mw

        col = mw.col if mw is not None else None
        if col is None:
            return False
        note = col.get_note(int(note_id))
    except Exception:
        return False

    field_names = model_field_names_from_note(note)
    mapped = mapped_field_values(proposal_fields, field_names)
    if not mapped:
        return False

    original_fields: list[str] | None = None
    try:
        original_fields = list(note.fields)
    except Exception:
        original_fields = None

    apply_mapped_fields_to_note(note, mapped, tags=None)

    checked = False
    is_duplicate = False
    try:
        if hasattr(note, "fields_check"):
            checked = True
            is_duplicate = _fields_check_is_duplicate(note.fields_check())
        elif hasattr(note, "dupeOrEmpty"):
            checked = True
            is_duplicate = _fields_check_is_duplicate(note.dupeOrEmpty())
    except Exception:
        checked = False
        is_duplicate = False
    finally:
        if original_fields is not None:
            try:
                note.fields = list(original_fields)
            except Exception:
                pass

    if checked:
        return is_duplicate

    # Fallback when fields_check is unavailable: same mid + stripped first field.
    try:
        model = col.models.get(int(note.mid))
        first_name = str((model.get("flds") or [{}])[0].get("name") or "").strip()
        if not first_name:
            return False
        if first_name in mapped:
            current_first = mapped[first_name]
        else:
            try:
                current_first = str(note[first_name])
            except Exception:
                current_first = ""
        needle = _strip_html_for_duplicate(current_first)
        if not needle:
            return False
        for other_id in col.find_notes(f"mid:{int(note.mid)}"):
            oid = int(other_id)
            if oid == int(note_id):
                continue
            try:
                other = col.get_note(oid)
                other_val = _strip_html_for_duplicate(str(other[first_name]))
            except Exception:
                continue
            if other_val == needle:
                return True
    except Exception:
        return False
    return False


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