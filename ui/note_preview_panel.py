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
from .visibility_icons import VisibilityToggleButton, style_scrollbar_extent
from .widgets import ScrollAwareTextEdit, _qt_widget_alive, bind_text_edit_auto_height

_LABEL_EDITOR_SPACING = 2
_FIELD_BLOCK_SPACING = 8
_MAX_SCROLL_HEIGHT = 220
_TOGGLE_BTN_SIZE = 28
_TOGGLE_ROW_PAD_TOP = 2
_TOGGLE_GAP_ABOVE = 6
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
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(_TOGGLE_GAP_ABOVE)

        self._toggle_row = QWidget(self)
        self._toggle_row.setFixedHeight(_TOGGLE_BTN_SIZE + _TOGGLE_ROW_PAD_TOP)
        self._toggle_layout = QHBoxLayout(self._toggle_row)
        self._toggle_layout.setContentsMargins(0, _TOGGLE_ROW_PAD_TOP, 0, 0)
        self._toggle_layout.setSpacing(0)
        self._toggle_layout.addStretch(1)

        self._toggle_btn = VisibilityToggleButton(
            self._toggle_row,
            size=_TOGGLE_BTN_SIZE,
            on_click=self._toggle_content_visibility,
        )
        self._toggle_layout.addWidget(self._toggle_btn)

        self._scrollbar_spacer = QWidget(self._toggle_row)
        self._scrollbar_spacer.setFixedWidth(0)
        self._scrollbar_spacer.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Preferred,
        )
        self._toggle_layout.addWidget(self._scrollbar_spacer)
        self._toggle_row.hide()
        layout.addWidget(self._toggle_row)

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

        bar = self._scroll.verticalScrollBar()
        if bar is not None:
            bar.rangeChanged.connect(self._sync_toggle_row_inset)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._content_visible = True
        self._has_content = False
        self._last_visible_scrollbar_gutter = 0

        apply_native_fields_scroll_theme(self, self._scroll)
        self.setVisible(False)

    def apply_theme(self) -> None:
        apply_native_fields_scroll_theme(self, self._scroll)
        if self._has_content:
            self._toggle_btn.update()
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
        self._last_visible_scrollbar_gutter = 0
        self._scroll.show()
        self._toggle_row.hide()
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

        self._last_visible_scrollbar_gutter = 0
        self._scrollbar_spacer.setFixedWidth(0)
        self._toggle_row.hide()
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
        QTimer.singleShot(0, self._reveal_toggle_row)
        QTimer.singleShot(0, self.reflow)
        QTimer.singleShot(100, self.reflow)

    def _reveal_toggle_row(self) -> None:
        if not _qt_widget_alive(self) or not self._has_content:
            return
        self._reflow_field_heights()
        self._sync_toggle_row_inset()
        self._toggle_row.show()
        self._sync_panel_height()

    def reflow(self) -> None:
        self._reflow_field_heights()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_toggle_row_inset()
        if self._has_content and self._content_visible:
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
        self._scroll.setVisible(self._content_visible)
        self._update_toggle_button()
        self._sync_toggle_row_inset()
        if self._content_visible:
            QTimer.singleShot(0, self.reflow)
        else:
            self._sync_panel_height()
        self.updateGeometry()

    def has_content(self) -> bool:
        return self._has_content

    def _live_scrollbar_gutter(self) -> int:
        bar = self._scroll.verticalScrollBar()
        if bar is None or bar.maximum() <= 0:
            return 0
        for candidate in (bar.width(), bar.sizeHint().width(), style_scrollbar_extent()):
            if candidate > 0:
                return candidate
        return 0

    def _scrollbar_reserve_width(self) -> int:
        if not self._has_content:
            return 0
        if self._content_visible and self._scroll.isVisible():
            gutter = self._live_scrollbar_gutter()
            self._last_visible_scrollbar_gutter = gutter
            return gutter
        return self._last_visible_scrollbar_gutter

    def _sync_toggle_row_inset(self) -> None:
        if not _qt_widget_alive(self._scrollbar_spacer):
            return
        width = self._scrollbar_reserve_width()
        if self._scrollbar_spacer.width() != width:
            self._scrollbar_spacer.setFixedWidth(width)

    def _update_toggle_button(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        self._toggle_btn.set_content_visible(self._content_visible)
        if self._content_visible:
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
        self._sync_toggle_row_inset()
        self._sync_panel_height()

    def _panel_content_height(self) -> int:
        layout = self.layout()
        if layout is None:
            return 0
        margins = layout.contentsMargins()
        total = margins.top() + margins.bottom()
        if self._toggle_row.isVisible():
            total += self._toggle_row.height()
        if self._scroll.isVisible():
            if self._toggle_row.isVisible():
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
