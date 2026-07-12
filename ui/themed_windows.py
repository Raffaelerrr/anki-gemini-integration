"""Track open add-on windows that support apply_theme()."""

from __future__ import annotations

from weakref import WeakSet

from aqt.qt import Qt, QWidget

_THEMED_WINDOWS: WeakSet[QWidget] = WeakSet()

# Normal resizable top-level chrome — required for Windows edge/corner snap and Win+Arrow.
SNAPPABLE_WINDOW_FLAGS = (
    Qt.WindowType.Window
    | Qt.WindowType.WindowSystemMenuHint
    | Qt.WindowType.WindowMinimizeButtonHint
    | Qt.WindowType.WindowMaximizeButtonHint
    | Qt.WindowType.WindowCloseButtonHint
)


def configure_snappable_window(
    window: QWidget,
    *,
    application_modal: bool = False,
) -> None:
    """Apply standard window chrome and own taskbar entry (Windows requires no Qt parent)."""
    window.setParent(None)
    window.setWindowFlags(SNAPPABLE_WINDOW_FLAGS)
    if application_modal:
        window.setWindowModality(Qt.WindowModality.ApplicationModal)


def register_themed_window(window: QWidget) -> None:
    _THEMED_WINDOWS.add(window)


def refresh_registered_themed_windows() -> None:
    for window in list(_THEMED_WINDOWS):
        try:
            if not window.isVisible():
                continue
            apply_theme = getattr(window, "apply_theme", None)
            if apply_theme is not None:
                apply_theme()
        except RuntimeError:
            continue
