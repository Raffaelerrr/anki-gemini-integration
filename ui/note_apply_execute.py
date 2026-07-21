"""Execute a confirmed NoteApplyPlan against the Anki collection / Add window."""

from __future__ import annotations

from typing import Any

try:
    from anki.errors import NotFoundError
except ImportError:  # offline tests / non-Anki hosts
    class NotFoundError(Exception):
        """Stub when the Anki package is unavailable."""

from aqt import dialogs, mw
from aqt.qt import QTimer
from aqt.utils import tooltip

from ..i18n import tr
from ..note_apply import (
    NoteApplyExecutionResult,
    NoteApplyPlan,
    apply_mapped_fields_to_note,
    has_apply_undo,
    mapped_field_values,
    model_field_names_from_note,
    proposal_tags_for_apply,
    snapshot_note_for_undo,
    store_apply_undo,
    take_apply_undo,
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


def undo_last_note_apply(
    *,
    config: dict[str, Any] | None = None,
) -> NoteApplyExecutionResult:
    """Restore the last successful update snapshot, if any."""
    snapshot = take_apply_undo()
    if snapshot is None:
        return NoteApplyExecutionResult(
            ok=False,
            mode="update",
            message_key="chat.apply_note.undo.none",
        )
    col = _collection()
    if col is None:
        store_apply_undo(snapshot)
        return NoteApplyExecutionResult(
            ok=False,
            mode="update",
            message_key="chat.apply_note.error.no_collection",
        )
    try:
        note = col.get_note(snapshot.note_id)
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
        return NoteApplyExecutionResult(
            ok=False,
            mode="update",
            message_key="chat.apply_note.undo.missing_note",
            message_kwargs={"note_id": snapshot.note_id},
        )

    apply_mapped_fields_to_note(
        note,
        dict(snapshot.fields),
        tags=list(snapshot.tags),
    )
    try:
        if hasattr(col, "update_note"):
            col.update_note(note)
        else:
            note.flush()
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError) as exc:
        # Put the snapshot back so the user can retry.
        store_apply_undo(snapshot)
        return NoteApplyExecutionResult(
            ok=False,
            mode="update",
            message_key="chat.apply_note.error.write_failed",
            message_kwargs={"detail": str(exc)},
            note_id=snapshot.note_id,
        )

    _refresh_open_editors_for_note(snapshot.note_id)
    tooltip(tr("chat.apply_note.undo.done", config=config))
    return NoteApplyExecutionResult(
        ok=True,
        mode="update",
        message_key="chat.apply_note.undo.done",
        note_id=snapshot.note_id,
        updated_fields=tuple(snapshot.fields.keys()),
    )


def can_undo_last_note_apply() -> bool:
    return has_apply_undo()


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
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
        # Stale / deleted note → fall back to create when possible.
        return _fallback_create_from_missing_update(plan, config=config)

    field_names = model_field_names_from_note(note)
    mapped = mapped_field_values(plan.proposal.fields, field_names)
    if not mapped:
        return NoteApplyExecutionResult(
            ok=False,
            mode="update",
            message_key="chat.apply_note.error.no_field_overlap",
            note_id=note_id,
        )

    undo_snapshot = snapshot_note_for_undo(note)
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
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError) as exc:
        return NoteApplyExecutionResult(
            ok=False,
            mode="update",
            message_key="chat.apply_note.error.write_failed",
            message_kwargs={"detail": str(exc)},
            note_id=note_id,
        )

    if undo_snapshot is not None:
        store_apply_undo(undo_snapshot)

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


def _fallback_create_from_missing_update(
    plan: NoteApplyPlan,
    *,
    config: dict[str, Any] | None,
) -> NoteApplyExecutionResult:
    notetype_id = plan.target_notetype_id
    if notetype_id is None:
        return NoteApplyExecutionResult(
            ok=False,
            mode="update",
            message_key="chat.apply_note.error.missing_note",
            message_kwargs={"note_id": plan.target_note_id},
        )
    create_plan = NoteApplyPlan(
        mode="create",
        proposal_index=plan.proposal_index,
        proposal=plan.proposal,
        target_notetype_id=int(notetype_id),
        target_notetype_name=plan.target_notetype_name,
        field_report=plan.field_report,
        history_item_id=plan.history_item_id,
    )
    result = _execute_create(create_plan, config=config, show_tooltip=False)
    if not result.ok:
        return result
    tooltip(tr("chat.apply_note.tooltip.create_fallback", config=config))
    return NoteApplyExecutionResult(
        ok=True,
        mode="create",
        message_key="chat.apply_note.applied.create_fallback",
        message_kwargs={
            "note_id": plan.target_note_id,
            "notetype": plan.target_notetype_name or f"#{notetype_id}",
            "fields": result.message_kwargs.get("fields", "—"),
        },
        updated_fields=result.updated_fields,
    )


def _resolve_deck_id(deck_name: str | None) -> Any | None:
    if not deck_name or mw is None or mw.col is None:
        return None
    try:
        decks = mw.col.decks
        if hasattr(decks, "id_for_name"):
            deck_id = decks.id_for_name(deck_name)
            return deck_id
        for item in decks.all_names_and_ids():
            if str(getattr(item, "name", "") or "") == deck_name:
                return getattr(item, "id", None)
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
        pass
    return None


def _new_note_for_model(col: Any, notetype_id: int) -> Any | None:
    try:
        model = col.models.get(notetype_id)
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
        model = None
    if model is None:
        try:
            model = col.models.get(int(notetype_id))
        except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
            return None
    if model is None:
        return None
    try:
        if hasattr(col, "new_note"):
            return col.new_note(model)
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
        pass
    try:
        from anki.notes import Note

        return Note(col, model)
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
        return None


def _reload_editor(editor: Any) -> None:
    if hasattr(editor, "loadNoteKeepingFocus"):
        try:
            editor.loadNoteKeepingFocus()
            return
        except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
            pass
    if hasattr(editor, "loadNote"):
        try:
            editor.loadNote()
        except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
            pass


def _execute_create(
    plan: NoteApplyPlan,
    *,
    config: dict[str, Any] | None,
    show_tooltip: bool = True,
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
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError) as exc:
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
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError) as exc:
        return NoteApplyExecutionResult(
            ok=False,
            mode="create",
            message_key="chat.apply_note.error.addcards_failed",
            message_kwargs={"detail": str(exc)},
        )

    editor = getattr(add_dialog, "editor", None)
    if editor is not None and getattr(editor, "note", None) is not None:
        apply_mapped_fields_to_note(
            editor.note,
            mapped,
            tags=proposal_tags_for_apply(plan.proposal),
        )
        _reload_editor(editor)

    _focus_addcards_window(add_dialog)

    if show_tooltip:
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
        except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
            return
        try:
            editor = getattr(add_dialog, "editor", None)
            web = getattr(editor, "web", None) if editor is not None else None
            if web is not None and hasattr(web, "setFocus"):
                web.setFocus()
        except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
            pass

    focus()
    try:
        QTimer.singleShot(0, focus)
        QTimer.singleShot(50, focus)
        QTimer.singleShot(200, focus)
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
        pass


def _refresh_open_editors_for_note(note_id: int) -> None:
    """Reload any open editor currently showing ``note_id``."""
    if mw is None:
        return
    try:
        app = mw.app
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
        return
    try:
        widgets = list(app.topLevelWidgets())
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
        return

    for widget in widgets:
        _maybe_reload_editor_widget(widget, note_id)
        editor = getattr(widget, "editor", None)
        if editor is not None:
            _maybe_reload_editor(editor, note_id)


def _maybe_reload_editor_widget(widget: Any, note_id: int) -> None:
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
    except (ImportError, AttributeError, TypeError, KeyError, IndexError, ValueError, RuntimeError, OSError, NotFoundError):
        return
    _reload_editor(editor)
