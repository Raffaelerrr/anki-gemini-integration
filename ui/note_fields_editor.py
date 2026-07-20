from __future__ import annotations

from aqt.qt import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)

from ..config import load_config
from .settings_compact_controls import apply_settings_text_edit_newlines, create_ui_text_edit
from .theme import (
    apply_native_fields_scroll_theme,
    apply_native_text_edit_surface_theme,
    field_name_label_html,
)
from .widgets import ScrollAwareTextEdit, _qt_widget_alive

_LABEL_EDITOR_SPACING = 2
_FIELD_BLOCK_SPACING = 8
_FIELD_EDITOR_MIN_HEIGHT = 56


def _clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


class NoteFieldsEditor(QWidget):
    """Editable note fields (all fields, including empty)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._field_editors: list[tuple[str, ScrollAwareTextEdit]] = []
        self._field_labels: list[tuple[str, QLabel]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self._host = QWidget(self._scroll)
        self._host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._host.setStyleSheet("background: transparent;")
        self._fields_layout = QVBoxLayout(self._host)
        self._fields_layout.setContentsMargins(8, 8, 8, 10)
        self._fields_layout.setSpacing(0)
        self._fields_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._host.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._scroll.setWidget(self._host)
        layout.addWidget(self._scroll, 1)

        apply_native_fields_scroll_theme(self, self._scroll)

    def apply_theme(self) -> None:
        apply_native_fields_scroll_theme(self, self._scroll)
        for name, label in self._field_labels:
            label.setText(field_name_label_html(name))
        for _, editor in self._field_editors:
            apply_native_text_edit_surface_theme(editor)

    def apply_newline_visibility(self, show: bool) -> None:
        for _, editor in self._field_editors:
            apply_settings_text_edit_newlines(editor, show=show)

    def clear(self) -> None:
        _clear_layout(self._fields_layout)
        self._field_editors.clear()
        self._field_labels.clear()

    def has_fields(self) -> bool:
        return bool(self._field_editors)

    def get_fields(self) -> list[tuple[str, str]]:
        return [(name, editor.toPlainText()) for name, editor in self._field_editors]

    def set_fields(self, fields: list[tuple[str, str]]) -> None:
        _clear_layout(self._fields_layout)
        self._field_editors.clear()
        self._field_labels.clear()
        if not fields:
            return

        for index, (name, value) in enumerate(fields):
            if index > 0:
                gap = QWidget(self._host)
                gap.setFixedHeight(_FIELD_BLOCK_SPACING)
                gap.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
                self._fields_layout.addWidget(gap)

            label = QLabel(field_name_label_html(name), self._host)
            label.setContentsMargins(0, 0, 0, _LABEL_EDITOR_SPACING)
            label.setStyleSheet("margin: 0px; padding: 0px; background: transparent;")
            label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            label.setFixedHeight(label.fontMetrics().height() + _LABEL_EDITOR_SPACING)
            self._fields_layout.addWidget(label)
            self._field_labels.append((name, label))

            editor_shell, editor = create_ui_text_edit(
                self._host,
                editor_class=ScrollAwareTextEdit,
                show_newlines=bool(load_config().get("settings_show_text_newlines", False)),
                auto_height=True,
                minimum=_FIELD_EDITOR_MIN_HEIGHT,
            )
            editor.setPlainText(value)
            editor.document().setDocumentMargin(0)
            editor.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            editor.textChanged.connect(self._schedule_reflow)
            self._fields_layout.addWidget(editor_shell)
            self._field_editors.append((name, editor))

        QTimer.singleShot(0, self.reflow)

    def reflow(self) -> None:
        if not _qt_widget_alive(self):
            return
        for _, editor in self._field_editors:
            if not _qt_widget_alive(editor):
                continue
            adjust = getattr(editor, "_auto_height_adjust", None)
            if adjust is not None:
                adjust()
        self.updateGeometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if event.size().width() != event.oldSize().width():
            QTimer.singleShot(0, self.reflow)

    def _schedule_reflow(self) -> None:
        QTimer.singleShot(0, self.reflow)
