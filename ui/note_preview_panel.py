from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aqt.qt import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSize,
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
    visibility_toggle_button_stylesheet,
)
from .visibility_icons import visibility_icon
from .widgets import ScrollAwareTextEdit, _qt_widget_alive, bind_text_edit_auto_height

_LABEL_EDITOR_SPACING = 2
_FIELD_BLOCK_SPACING = 8
_MAX_SCROLL_HEIGHT = 220
_TOGGLE_BTN_SIZE = 24
_TOGGLE_ICON_SIZE = 18
_TOGGLE_TOOLBAR_HEIGHT = 28
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
        self._field_editors: list[tuple[str, ScrollAwareTextEdit]] = []
        self._field_labels: list[tuple[str, QLabel]] = []

        self.setObjectName("nativeFieldsPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        self._toolbar = QWidget(self)
        self._toolbar.setFixedHeight(_TOGGLE_TOOLBAR_HEIGHT)
        self._toolbar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        toolbar_layout = QHBoxLayout(self._toolbar)
        toolbar_layout.setContentsMargins(0, 2, 2, 2)
        toolbar_layout.setSpacing(0)
        toolbar_layout.addStretch(1)

        self._toggle_btn = QPushButton(self._toolbar)
        self._toggle_btn.setFixedSize(_TOGGLE_BTN_SIZE, _TOGGLE_BTN_SIZE)
        self._toggle_btn.setIconSize(QSize(_TOGGLE_ICON_SIZE, _TOGGLE_ICON_SIZE))
        self._toggle_btn.setAutoDefault(False)
        self._toggle_btn.setDefault(False)
        self._toggle_btn.clicked.connect(self._toggle_content_visibility)
        self._toggle_btn.setStyleSheet(visibility_toggle_button_stylesheet(size=_TOGGLE_BTN_SIZE))
        toolbar_layout.addWidget(
            self._toggle_btn,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addWidget(self._toolbar)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setMinimumHeight(0)
        self._scroll.setMaximumHeight(_MAX_SCROLL_HEIGHT)
        self._scroll.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self._host = QWidget(self._scroll)
        self._host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._host.setStyleSheet("background: transparent;")
        self._fields_layout = QVBoxLayout(self._host)
        self._fields_layout.setContentsMargins(8, 8, 8, 10)
        self._fields_layout.setSpacing(0)
        self._fields_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._host.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._scroll.setWidget(self._host)

        layout.addWidget(self._scroll)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._content_visible = True
        self._has_content = False

        apply_native_fields_scroll_theme(self, self._scroll)
        self._toolbar.hide()
        self.setVisible(False)

    def apply_theme(self) -> None:
        apply_native_fields_scroll_theme(self, self._scroll)
        self._toggle_btn.setStyleSheet(visibility_toggle_button_stylesheet(size=_TOGGLE_BTN_SIZE))
        if self._has_content:
            self._update_toggle_button()
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
        self._toolbar.hide()
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
        self._toolbar.show()

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
            )
            editor.setPlainText(value)
            apply_native_text_edit_surface_theme(editor)
            editor.document().setDocumentMargin(0)
            editor.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            bind_text_edit_auto_height(editor, minimum=_FIELD_EDITOR_MIN_HEIGHT, maximum=None)
            editor.textChanged.connect(self._emit_fields_changed)
            self._fields_layout.addWidget(editor_shell)
            self._field_editors.append((name, editor))

        self._has_content = True
        self._update_toggle_button()
        self.setVisible(True)
        QTimer.singleShot(0, self.reflow)
        QTimer.singleShot(100, self.reflow)

    def reflow(self) -> None:
        self._reflow_field_heights()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._has_content and self._content_visible:
            QTimer.singleShot(0, self.reflow)

    def _emit_fields_changed(self) -> None:
        if self.on_fields_changed is not None:
            self.on_fields_changed()
        QTimer.singleShot(0, self.reflow)

    def _toggle_content_visibility(self) -> None:
        self._content_visible = not self._content_visible
        self._scroll.setVisible(self._content_visible)
        self._update_toggle_button()
        if self._content_visible:
            QTimer.singleShot(0, self.reflow)
        else:
            self._sync_panel_height()
        self.updateGeometry()

    def _update_toggle_button(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        visible = self._content_visible
        self._toggle_btn.setText("")
        self._toggle_btn.setIcon(visibility_icon(visible=visible, size=_TOGGLE_ICON_SIZE))
        if visible:
            self._toggle_btn.setToolTip(tr("chat.preview.hide_imported_note", config=config))
        else:
            self._toggle_btn.setToolTip(tr("chat.preview.show_imported_note", config=config))

    def _content_height(self) -> int:
        margins = self._fields_layout.contentsMargins()
        total = margins.top() + margins.bottom()
        for index in range(self._fields_layout.count()):
            item = self._fields_layout.itemAt(index)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                total += widget.height()
        return total

    def _sync_scroll_height(self) -> None:
        if not _qt_widget_alive(self) or not self._has_content or not self._content_visible:
            return
        content_h = self._content_height()
        if content_h <= 0:
            hint = self._fields_layout.sizeHint().height()
            margins = self._fields_layout.contentsMargins()
            content_h = hint + margins.top() + margins.bottom()
        target = min(max(content_h + 2, 1), _MAX_SCROLL_HEIGHT)
        if self._scroll.height() != target:
            self._scroll.setFixedHeight(target)
        self._sync_panel_height()

    def _panel_content_height(self) -> int:
        layout = self.layout()
        if layout is None:
            return 0
        margins = layout.contentsMargins()
        total = margins.top() + margins.bottom()
        if self._toolbar.isVisible():
            total += self._toolbar.height()
        if self._scroll.isVisible():
            if self._toolbar.isVisible():
                total += layout.spacing()
            total += self._scroll.height()
        return total

    def _sync_panel_height(self) -> None:
        if not _qt_widget_alive(self) or not self._has_content or not self.isVisible():
            return
        target = self._panel_content_height()
        if self.height() != target:
            self.setFixedHeight(target)
        self.updateGeometry()
        parent = self.parentWidget()
        if parent is not None:
            parent.updateGeometry()

    def _reflow_field_heights(self) -> None:
        if not _qt_widget_alive(self):
            return
        for _, editor in self._field_editors:
            if not _qt_widget_alive(editor):
                continue
            adjust = getattr(editor, "_auto_height_adjust", None)
            if adjust is not None:
                adjust()
        self._sync_scroll_height()
