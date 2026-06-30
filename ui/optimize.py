from __future__ import annotations

import html
import re
from typing import Any

from aqt import mw
from aqt.qt import QDialog
from aqt.utils import showInfo, showWarning, tooltip

from ..config import api_key_configured, load_config, save_config
from ..gemini_client import GeminiError, call_gemini, strip_markdown_fences
from .preview_dialog import PreviewDialog

_last_undo: dict[int, tuple[int, str]] = {}


def _editor_key(editor) -> int:
    return id(editor)


def store_undo(editor, field_index: int, original_text: str) -> None:
    _last_undo[_editor_key(editor)] = (field_index, original_text)


def undo_last_optimization(editor) -> None:
    key = _editor_key(editor)
    backup = _last_undo.get(key)
    if not backup:
        showInfo("Nessuna ottimizzazione recente da annullare in questa sessione.")
        return

    field_index, original_text = backup
    editor.note.fields[field_index] = original_text
    editor.loadNoteKeepingFocus()
    del _last_undo[key]
    tooltip("Ottimizzazione annullata.")


def _apply_optimized_text(editor, field_index: int, original: str, optimized: str) -> None:
    store_undo(editor, field_index, original)
    editor.note.fields[field_index] = optimized
    editor.loadNoteKeepingFocus()
    tooltip("Campo ottimizzato con Gemini.")


def _handle_optimize_result(future, editor, field_index: int, original: str, config: dict[str, Any]) -> None:
    try:
        result = future.result()
        optimized = strip_markdown_fences(result)

        if config.get("confirm_before_apply", True):
            dialog = PreviewDialog(editor.parentWindow, original, optimized)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                tooltip("Ottimizzazione annullata.")
                return

        _apply_optimized_text(editor, field_index, original, optimized)
    except GeminiError as exc:
        showWarning(str(exc))
    except Exception as exc:
        showWarning(f"Errore durante l'ottimizzazione con Gemini:\n{exc}")


def optimize_field_with_gemini(editor) -> None:
    field_index = editor.currentField
    if field_index is None:
        showInfo("Per favore, fai clic dentro un campo di testo prima di usare Gemini.")
        return

    original = editor.note.fields[field_index]
    if not original.strip():
        showInfo("Il campo attivo è vuoto!")
        return

    config = load_config()
    if not api_key_configured(config):
        showInfo("Errore: API Key mancante. Impostala con il bottone ⚙️.")
        return

    tooltip("Ottimizzazione in corso…")

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
