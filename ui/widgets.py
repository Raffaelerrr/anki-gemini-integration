from __future__ import annotations

from aqt.qt import QComboBox, QDoubleSpinBox, QScrollArea, QSpinBox, Qt, QTextEdit, QWidget


def _forward_wheel_event(widget: QWidget, event) -> None:
    ancestor = widget.parentWidget()
    while ancestor is not None:
        if isinstance(ancestor, QScrollArea):
            viewport = ancestor.viewport()
            if viewport is not None:
                viewport.wheelEvent(event)
                return
        ancestor = ancestor.parentWidget()
    event.ignore()


class ScrollAwareTextEdit(QTextEdit):
    """Scroll page by default; scroll text content only after the field is clicked.

    Only one ScrollAwareTextEdit in the same window may keep a text selection.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def clear_text_selection(self) -> None:
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def focusInEvent(self, event) -> None:
        self._clear_peer_selections_in_window()
        super().focusInEvent(event)

    def mousePressEvent(self, event) -> None:
        self._clear_peer_selections_in_window()
        super().mousePressEvent(event)

    def _clear_peer_selections_in_window(self) -> None:
        host = self.window()
        if host is None:
            return
        for editor in host.findChildren(ScrollAwareTextEdit):
            if editor is not self:
                editor.clear_text_selection()

    def wheelEvent(self, event) -> None:
        if not self.hasFocus():
            _forward_wheel_event(self, event)
            return
        super().wheelEvent(event)


class _NoWheelMixin:
    def _install_no_wheel(self) -> None:
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        line_edit = self.lineEdit() if hasattr(self, "lineEdit") else None
        if line_edit is not None:
            line_edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == 31:
            _forward_wheel_event(self, event)
            return True
        return super().eventFilter(obj, event)

    def wheelEvent(self, event) -> None:
        _forward_wheel_event(self, event)


class NoWheelSpinBox(_NoWheelMixin, QSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._install_no_wheel()


class NoWheelDoubleSpinBox(_NoWheelMixin, QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._install_no_wheel()


class NoWheelComboBox(_NoWheelMixin, QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._install_no_wheel()
