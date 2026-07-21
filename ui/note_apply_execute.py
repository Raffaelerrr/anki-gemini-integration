"""Execute a confirmed NoteApplyPlan against the Anki collection / Add window."""

from __future__ import annotations

from typing import Any

from aqt import dialogs, mw
from aqt.qt import QTimer
from aqt.utils import tooltip

from ..i18n import tr
from ..note_apply import (
    NoteApplyExecutionResult,
    NoteApplyPlan,
    apply_mapped_fields_to_note,
    mapped_field_values,
    model_field_names_from_note,
    proposal_tags_for_apply,
)


def execute_note_apply_plan(
    plan: NoteApplyPlan,
    *,
    config: dict[str, Any] | None = None,
) -> NoteApplyExecutionResult:
    """Apply the plan: update an existing note, or open a prefilled AddCards."""
    if plan.mode == "update":
        return _execute_update(plan, config=config)
    if plan.mode == "create":
        return _execute_create(plan, config=config)
    return NoteApplyExecutionResult(
        ok=False,
        mode=plan.mode,
        message_key="chat.apply_note.error.generic",
    )


def _collection():
    if mw is None:
        return None
    return mw.col


def _execute_update(
    plan: NoteApplyPlan,
    *,
    config: dict[str, Any] | None,
) -> NoteApplyExecutionResult:
    col = _collection()
    if col is None:
        return NoteApplyExecutionResult(
            ok=False,
            mode="update",
            message_key="chat.apply_note.error.no_collection",
        )
    note_id = plan.target_note_id
    if note_id is None:
        return NoteApplyExecutionResult(
            ok=False,
            mode="update",
            message_key="chat.apply_note.error.missing_note",
        )
    try:
        note = col.get_note(note_id)
    except Exception:
        return NoteApplyExecutionResult(
            ok=False,
            mode="update",
            message_key="chat.apply_note.error.missing_note",
            message_kwargs={"note_id": note_id},
        )

    field_names = model_field_names_from_note(note)
    mapped = mapped_field_values(plan.proposal.fields, field_names)
    if not mapped:
        return NoteApplyExecutionResult(
            ok=False,
            mode="update",
            message_key="chat.apply_note.error.no_field_overlap",
            note_id=note_id,
        )

    updated = apply_mapped_fields_to_note(
        note,
        mapped,
        tags=proposal_tags_for_apply(plan.proposal),
    )
    try:
        if hasattr(col, "update_note"):
            col.update_note(note)
        else:
            note.flush()
    except Exception as exc:
        return NoteApplyExecutionResult(
            ok=False,
            mode="update",
            message_key="chat.apply_note.error.write_failed",
            message_kwargs={"detail": str(exc)},
            note_id=note_id,
        )

    _refresh_open_editors_for_note(note_id)
    tooltip(
        tr(
            "chat.apply_note.tooltip.updated",
            config=config,
            count=len(updated),
        )
    )
    return NoteApplyExecutionResult(
        ok=True,
        mode="update",
        message_key="chat.apply_note.applied.update",
        message_kwargs={
            "note_id": note_id,
            "fields": ", ".join(updated) if updated else "—",
        },
        updated_fields=tuple(updated),
        note_id=note_id,
    )


def _resolve_deck_id(deck_name: str | None) -> Any | None:
    if not deck_name or mw is None or mw.col is None:
        return None
    try:
        decks = mw.col.decks
        if hasattr(decks, "id_for_name"):
            deck_id = decks.id_for_name(deck_name)
            return deck_id
        # Older Anki: id(name, create=False) may still create; prefer lookup.
        for item in decks.all_names_and_ids():
            if str(getattr(item, "name", "") or "") == deck_name:
                return getattr(item, "id", None)
    except Exception:
        pass
    return None


def _new_note_for_model(col: Any, notetype_id: int) -> Any | None:
    try:
        model = col.models.get(notetype_id)
    except Exception:
        model = None
    if model is None:
        try:
            model = col.models.get(int(notetype_id))
        except Exception:
            return None
    if model is None:
        return None
    try:
        if hasattr(col, "new_note"):
            return col.new_note(model)
    except Exception:
        pass
    try:
        from anki.notes import Note

        return Note(col, model)
    except Exception:
        return None


def _reload_editor(editor: Any) -> None:
    if hasattr(editor, "loadNoteKeepingFocus"):
        try:
            editor.loadNoteKeepingFocus()
            return
        except Exception:
            pass
    if hasattr(editor, "loadNote"):
        try:
            editor.loadNote()
        except Exception:
            pass


def _execute_create(
    plan: NoteApplyPlan,
    *,
    config: dict[str, Any] | None,
) -> NoteApplyExecutionResult:
    col = _collection()
    if col is None or mw is None:
        return NoteApplyExecutionResult(
            ok=False,
            mode="create",
            message_key="chat.apply_note.error.no_collection",
        )
    notetype_id = plan.target_notetype_id
    if notetype_id is None:
        return NoteApplyExecutionResult(
            ok=False,
            mode="create",
            message_key="chat.apply_note.error.missing_notetype",
        )

    note = _new_note_for_model(col, int(notetype_id))
    if note is None:
        return NoteApplyExecutionResult(
            ok=False,
            mode="create",
            message_key="chat.apply_note.error.missing_notetype",
            message_kwargs={"notetype_id": notetype_id},
        )

    field_names = model_field_names_from_note(note)
    mapped = mapped_field_values(plan.proposal.fields, field_names)
    if not mapped:
        return NoteApplyExecutionResult(
            ok=False,
            mode="create",
            message_key="chat.apply_note.error.no_field_overlap",
        )

    apply_mapped_fields_to_note(
        note,
        mapped,
        tags=proposal_tags_for_apply(plan.proposal),
    )
    deck_id = _resolve_deck_id(plan.proposal.deck)

    try:
        add_dialog = dialogs.open("AddCards", mw)
    except Exception as exc:
        return NoteApplyExecutionResult(
            ok=False,
            mode="create",
            message_key="chat.apply_note.error.addcards_failed",
            message_kwargs={"detail": str(exc)},
        )

    try:
        if hasattr(add_dialog, "set_note"):
            try:
                add_dialog.set_note(note, deck_id)
            except TypeError:
                add_dialog.set_note(note)
        elif hasattr(add_dialog, "load_new_note"):
            add_dialog.load_new_note(deck_id=deck_id, notetype_id=notetype_id)
    except Exception as exc:
        return NoteApplyExecutionResult(
            ok=False,
            mode="create",
            message_key="chat.apply_note.error.addcards_failed",
            message_kwargs={"detail": str(exc)},
        )

    editor = getattr(add_dialog, "editor", None)
    if editor is not None and getattr(editor, "note", None) is not None:
        # New AddCards.set_note may only switch notetype; always push fields.
        apply_mapped_fields_to_note(
            editor.note,
            mapped,
            tags=proposal_tags_for_apply(plan.proposal),
        )
        _reload_editor(editor)

    _focus_addcards_window(add_dialog)

    tooltip(tr("chat.apply_note.tooltip.addcards", config=config))
    return NoteApplyExecutionResult(
        ok=True,
        mode="create",
        message_key="chat.apply_note.applied.create",
        message_kwargs={
            "notetype": plan.target_notetype_name or f"#{notetype_id}",
            "fields": ", ".join(mapped.keys()),
        },
        updated_fields=tuple(mapped.keys()),
    )


def _focus_addcards_window(add_dialog: Any) -> None:
    """Bring AddCards to the front (deferred so it wins over the apply dialog)."""

    def focus() -> None:
        try:
            add_dialog.show()
            add_dialog.raise_()
            add_dialog.activateWindow()
            window = add_dialog.windowHandle()
            if window is not None and hasattr(window, "requestActivate"):
                window.requestActivate()
        except Exception:
            return
        try:
            editor = getattr(add_dialog, "editor", None)
            web = getattr(editor, "web", None) if editor is not None else None
            if web is not None and hasattr(web, "setFocus"):
                web.setFocus()
        except Exception:
            pass

    focus()
    try:
        QTimer.singleShot(0, focus)
        QTimer.singleShot(50, focus)
        QTimer.singleShot(200, focus)
    except Exception:
        pass


def _refresh_open_editors_for_note(note_id: int) -> None:
    """Reload any open editor currently showing ``note_id``."""
    if mw is None:
        return
    try:
        app = mw.app
    except Exception:
        return
    try:
        widgets = list(app.topLevelWidgets())
    except Exception:
        return

    for widget in widgets:
        _maybe_reload_editor_widget(widget, note_id)
        editor = getattr(widget, "editor", None)
        if editor is not None:
            _maybe_reload_editor(editor, note_id)


def _maybe_reload_editor_widget(widget: Any, note_id: int) -> None:
    note = getattr(widget, "note", None)
    if note is not None and getattr(note, "id", None) == note_id:
        # Some windows expose note directly (rare).
        pass
    editor = getattr(widget, "editor", None)
    if editor is not None:
        _maybe_reload_editor(editor, note_id)


def _maybe_reload_editor(editor: Any, note_id: int) -> None:
    note = getattr(editor, "note", None)
    if note is None or getattr(note, "id", None) != note_id:
        return
    col = _collection()
    if col is None:
        return
    try:
        editor.note = col.get_note(note_id)
    except Exception:
        return
    _reload_editor(editor)
