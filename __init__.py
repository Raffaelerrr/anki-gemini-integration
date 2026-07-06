from __future__ import annotations

from aqt import gui_hooks
from aqt.qt import QAction

from .config import load_config
from .i18n import tr
from .ui.window_lifecycle import (
    install_main_window_close_handler,
    reset_shutdown_state,
    shutdown_addon_windows,
)
from .ui.chat_dialog import open_chat
from .ui.optimize import optimize_field_with_gemini, undo_last_optimization
from .ui.scroll_test_dialog import open_scroll_test_dialog
from .ui.settings_dialog import open_settings_dialog
from .ui.theme import refresh_addon_theme


def add_editor_buttons(buttons, editor) -> None:
    config = load_config()
    buttons.append(
        editor.addButton(
            None,
            "Gemini",
            lambda ed=editor: optimize_field_with_gemini(ed),
            tip=tr("editor.tip.optimize", config=config),
            keys="Ctrl+Shift+G",
        )
    )
    buttons.append(
        editor.addButton(
            None,
            "↩",
            lambda ed=editor: undo_last_optimization(ed),
            tip=tr("editor.tip.undo", config=config),
        )
    )
    buttons.append(
        editor.addButton(
            None,
            "🧠",
            lambda ed=editor: open_chat(ed, analyze=True),
            tip=tr("editor.tip.analyze_note", config=config),
        )
    )
    buttons.append(
        editor.addButton(
            None,
            "💬",
            lambda ed=editor: open_chat(),
            tip=tr("editor.tip.chat", config=config),
            keys="Ctrl+Alt+C",
        )
    )
    buttons.append(
        editor.addButton(
            None,
            "⚙️",
            lambda ed=editor: open_settings_dialog(ed),
            tip=tr("editor.tip.settings", config=config),
        )
    )


def init_tools_menu() -> None:
    from aqt import mw

    install_main_window_close_handler()
    config = load_config()
    action = QAction(tr("menu.tools.chat", config=config), mw)
    action.setShortcut("Ctrl+Alt+C")
    action.triggered.connect(lambda: open_chat())
    mw.form.menuTools.addAction(action)
    scroll_test_action = QAction("Anki AI: Scroll test (debug)", mw)
    scroll_test_action.triggered.connect(lambda: open_scroll_test_dialog(mw))
    mw.form.menuTools.addAction(scroll_test_action)


def cleanup() -> None:
    shutdown_addon_windows(force=True)


def _on_profile_did_open() -> None:
    reset_shutdown_state()


def _on_theme_changed() -> None:
    refresh_addon_theme()


gui_hooks.editor_did_init_buttons.append(add_editor_buttons)
gui_hooks.main_window_did_init.append(init_tools_menu)
gui_hooks.profile_did_open.append(_on_profile_did_open)
gui_hooks.profile_will_close.append(lambda *_: cleanup())
gui_hooks.theme_did_change.append(_on_theme_changed)
