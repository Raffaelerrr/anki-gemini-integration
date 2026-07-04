from __future__ import annotations

from aqt.qt import QApplication, QObject

_CLOSE_EVENT_TYPE = 19  # QEvent.Type.Close

_shutting_down = False


def is_shutting_down() -> bool:
    return _shutting_down


def reset_shutdown_state() -> None:
    global _shutting_down
    _shutting_down = False


def shutdown_addon_windows(*, force: bool = True) -> None:
    """Close add-on windows so Anki can exit cleanly."""
    global _shutting_down
    _shutting_down = True

    from .settings_dialog import close_settings_dialog
    from .chat_dialog import close_chat_window

    close_settings_dialog(force=force)
    close_chat_window(force=force)


class _MainWindowCloseFilter(QObject):
    def eventFilter(self, obj, event) -> bool:
        if event.type() != _CLOSE_EVENT_TYPE:
            return False
        from aqt import mw

        if obj is mw:
            shutdown_addon_windows(force=True)
        return False


def install_main_window_close_handler() -> None:
    from aqt import mw

    if getattr(mw, "_gemini_addon_close_handler_installed", False):
        return

    base_close = mw.__class__.closeEvent

    def closeEvent(event) -> None:
        shutdown_addon_windows(force=True)
        base_close(mw, event)

    mw.closeEvent = closeEvent

    original_unload = mw.unloadProfileAndExit

    def unloadProfileAndExit() -> None:
        shutdown_addon_windows(force=True)
        original_unload()

    mw.unloadProfileAndExit = unloadProfileAndExit

    app = QApplication.instance()
    if app is not None and not getattr(app, "_gemini_addon_close_filter_installed", False):
        app.installEventFilter(_MainWindowCloseFilter(app))
        app._gemini_addon_close_filter_installed = True

    mw._gemini_addon_close_handler_installed = True
