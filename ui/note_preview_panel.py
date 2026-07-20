from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aqt.qt import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)

from ..config import load_config
from ..i18n import tr
from .settings_compact_controls import create_ui_text_edit
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


class NotePreviewPanel(QWidget):
    """Editable imported note fields (above the chat log)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.on_fields_changed: Callable[[], None] | None = None
        self.on_content_visibility_changed: Callable[[bool], None] | None = None
        self._field_editors: list[tuple[str, ScrollAwareTextEdit]] = []
        self._field_labels: list[tuple[str, QLabel]] = []
        self._visibility_toggle: QWidget | None = None

        self.setObjectName("nativeFieldsPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(0)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setMinimumHeight(56)
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

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(56)
        self._content_visible = True
        self._has_content = False

        apply_native_fields_scroll_theme(self, self._scroll)
        self.setVisible(False)

    def bind_visibility_toggle(self, button: QWidget) -> None:
        self._visibility_toggle = button

    def content_visible(self) -> bool:
        return self._content_visible

    def apply_theme(self) -> None:
        apply_native_fields_scroll_theme(self, self._scroll)
        if self._has_content and self._visibility_toggle is not None:
            self._visibility_toggle.update()
        for name, label in self._field_labels:
            label.setText(field_name_label_html(name))
        for _, editor in self._field_editors:
            apply_native_text_edit_surface_theme(editor)

    def apply_language(self, config: dict[str, Any] | None = None) -> None:
        if self._has_content:
            self._update_toggle_button(config)

    def clear(self) -> None:
        _clear_layout(self._fields_layout)
        self._field_editors.clear()
        self._field_labels.clear()
        self._has_content = False
        self._content_visible = True
        self._scroll.show()
        self._hide_visibility_toggle()
        self.setVisible(False)

    def get_fields(self) -> list[tuple[str, str]]:
        return [(name, editor.toPlainText()) for name, editor in self._field_editors]

    def set_fields(self, fields: list[tuple[str, str]]) -> None:
        _clear_layout(self._fields_layout)
        self._field_editors.clear()
        self._field_labels.clear()
        non_empty = [(name, value) for name, value in fields if value.strip()]
        if not non_empty:
            self.clear()
            return

        self._content_visible = True
        self._scroll.show()

        for index, (name, value) in enumerate(non_empty):
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
                auto_height=True,
                minimum=_FIELD_EDITOR_MIN_HEIGHT,
            )
            editor.setPlainText(value)
            apply_native_text_edit_surface_theme(editor)
            editor.document().setDocumentMargin(0)
            editor.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            editor.textChanged.connect(self._emit_fields_changed)
            self._fields_layout.addWidget(editor_shell)
            self._field_editors.append((name, editor))

        self._has_content = True
        self._update_toggle_button()
        self.setVisible(True)
        QTimer.singleShot(0, self._reveal_visibility_toggle)
        QTimer.singleShot(0, self.reflow)
        QTimer.singleShot(100, self.reflow)

    def _reveal_visibility_toggle(self) -> None:
        if not _qt_widget_alive(self) or not self._has_content:
            return
        self._reflow_field_heights()
        self._show_visibility_toggle()
        self.updateGeometry()

    def _show_visibility_toggle(self) -> None:
        if self._visibility_toggle is not None:
            self._visibility_toggle.show()

    def _hide_visibility_toggle(self) -> None:
        if self._visibility_toggle is not None:
            self._visibility_toggle.hide()

    def reflow(self) -> None:
        self._reflow_field_heights()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if (
            self._has_content
            and self._content_visible
            and event.size().width() != event.oldSize().width()
        ):
            QTimer.singleShot(0, self.reflow)

    def _emit_fields_changed(self) -> None:
        if self.on_fields_changed is not None:
            self.on_fields_changed()
        QTimer.singleShot(0, self.reflow)

    def _toggle_content_visibility(self) -> None:
        self.set_content_visible(not self._content_visible)

    def set_content_visible(self, visible: bool) -> None:
        if not self._has_content or self._content_visible == visible:
            return
        self._content_visible = visible
        if self._content_visible:
            self.setMinimumHeight(56)
            self._scroll.show()
            self.setVisible(True)
        else:
            self._scroll.hide()
            self.setMinimumHeight(0)
            self.setVisible(False)
        self._update_toggle_button()
        if self._content_visible:
            QTimer.singleShot(0, self.reflow)
        self.updateGeometry()
        if self.on_content_visibility_changed is not None:
            self.on_content_visibility_changed(self._content_visible)

    def has_content(self) -> bool:
        return self._has_content

    def _update_toggle_button(self, config: dict[str, Any] | None = None) -> None:
        if self._visibility_toggle is None:
            return
        from .theme import apply_widget_tooltip_palette

        apply_widget_tooltip_palette(self._visibility_toggle)
        config = config or load_config()
        set_visible = getattr(self._visibility_toggle, "set_content_visible", None)
        if callable(set_visible):
            set_visible(self._content_visible)
        if self._content_visible:
            self._visibility_toggle.setToolTip(
                tr("chat.preview.hide_imported_note", config=config)
            )
        else:
            self._visibility_toggle.setToolTip(
                tr("chat.preview.show_imported_note", config=config)
            )

    def _reflow_field_heights(self) -> None:
        if not _qt_widget_alive(self):
            return
        for _, editor in self._field_editors:
            if not _qt_widget_alive(editor):
                continue
            adjust = getattr(editor, "_auto_height_adjust", None)
            if adjust is not None:
                adjust()
        self.updateGeometry()
