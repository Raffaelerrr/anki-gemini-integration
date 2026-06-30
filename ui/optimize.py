from __future__ import annotations

import html
import re
from typing import Any

from aqt import mw
from aqt.qt import QDialog
from aqt.utils import showInfo, showWarning, tooltip

from ..config import api_key_configured, load_config, save_config
from ..gemini_client import GeminiError, call_gemini, strip_markdown_fences
from ..i18n import tr
from .preview_dialog import PreviewDialog

_last_undo: dict[int, tuple[int, str]] = {}


def _editor_key(editor) -> int:
    return id(editor)


def store_undo(editor, field_index: int, original_text: str) -> None:
    _last_undo[_editor_key(editor)] = (field_index, original_text)


def undo_last_optimization(editor) -> None:
    config = load_config()
    key = _editor_key(editor)
    backup = _last_undo.get(key)
    if not backup:
        showInfo(tr("optimize.no_undo", config=config))
        return

    field_index, original_text = backup
    editor.note.fields[field_index] = original_text
    editor.loadNoteKeepingFocus()
    del _last_undo[key]
    tooltip(tr("optimize.undo_done", config=config))


def _apply_optimized_text(editor, field_index: int, original: str, optimized: str) -> None:
    config = load_config()
    store_undo(editor, field_index, original)
    editor.note.fields[field_index] = optimized
    editor.loadNoteKeepingFocus()
    tooltip(tr("optimize.applied", config=config))


def _handle_optimize_result(future, editor, field_index: int, original: str, config: dict[str, Any]) -> None:
    try:
        result = future.result()
        optimized = strip_markdown_fences(result)

        if config.get("confirm_before_apply", True):
            dialog = PreviewDialog(editor.parentWindow, original, optimized, config=config)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                tooltip(tr("optimize.cancelled", config=config))
                return

        _apply_optimized_text(editor, field_index, original, optimized)
    except GeminiError as exc:
        showWarning(str(exc))
    except Exception as exc:
        showWarning(tr("optimize.error", config=config, error=exc))


def optimize_field_with_gemini(editor) -> None:
    config = load_config()
    field_index = editor.currentField
    if field_index is None:
        showInfo(tr("optimize.click_field", config=config))
        return

    original = editor.note.fields[field_index]
    if not original.strip():
        showInfo(tr("optimize.field_empty", config=config))
        return

    if not api_key_configured(config):
        showInfo(tr("optimize.api_key_missing", config=config))
        return

    tooltip(tr("optimize.in_progress", config=config))

    temperature = float(config.get("temperature_optimize", 0.1))

    mw.taskman.run_in_background(
        lambda: call_gemini(
            config=config,
            user_text=original,
            temperature=temperature,
            include_meta_rule=False,
        ),
        lambda future: _handle_optimize_result(future, editor, field_index, original, config),
    )
