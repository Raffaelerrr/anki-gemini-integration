"""Track open add-on windows that support apply_theme()."""

from __future__ import annotations

from weakref import WeakSet

from aqt.qt import QWidget

_THEMED_WINDOWS: WeakSet[QWidget] = WeakSet()


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
