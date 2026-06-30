from __future__ import annotations

from aqt import gui_hooks
from aqt.qt import QAction

from .ui.chat_dialog import close_chat_window, open_chat
from .ui.optimize import optimize_field_with_gemini, undo_last_optimization
from .ui.settings_dialog import open_settings_dialog


def add_editor_buttons(buttons, editor) -> None:
    buttons.append(
        editor.addButton(
            None,
            "Gemini",
            lambda ed=editor: optimize_field_with_gemini(ed),
            tip="Ottimizza questo campo con Gemini (Ctrl+Shift+G)",
            keys="Ctrl+Shift+G",
        )
    )
    buttons.append(
        editor.addButton(
            None,
            "↩",
            lambda ed=editor: undo_last_optimization(ed),
            tip="Annulla l'ultima ottimizzazione Gemini su questa nota",
        )
    )
    buttons.append(
        editor.addButton(
            None,
            "🧠",
            lambda ed=editor: open_chat(ed, analyze=True),
            tip="Importa TUTTI i campi della nota in chat per analizzarla",
        )
    )
    buttons.append(
        editor.addButton(
            None,
            "💬",
            lambda ed=editor: open_chat(),
            tip="Apri o porta in primo piano la Chat con Gemini (Ctrl+Alt+C)",
            keys="Ctrl+Alt+C",
        )
    )
    buttons.append(
        editor.addButton(
            None,
            "⚙️",
            lambda ed=editor: open_settings_dialog(ed),
            tip="Modifica al volo le istruzioni o l'API Key",
        )
    )


def init_tools_menu() -> None:
    from aqt import mw

    action = QAction("Chat con Gemini", mw)
    action.setShortcut("Ctrl+Alt+C")
    action.triggered.connect(lambda: open_chat())
    mw.form.menuTools.addAction(action)


def cleanup() -> None:
    close_chat_window()


gui_hooks.editor_did_init_buttons.append(add_editor_buttons)
gui_hooks.main_window_did_init.append(init_tools_menu)
gui_hooks.profile_will_close.append(lambda *_: cleanup())
