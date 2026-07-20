from __future__ import annotations

from typing import Any

from aqt.qt import (
    QHBoxLayout,
    QPushButton,
    QShowEvent,
    QSizePolicy,
    QStyle,
    Qt,
    QTimer,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..chat_context_wrapper import WRAPPER_SECTION_IDS
from ..i18n import (
    effective_card_templates_format_prompt,
    effective_wrapper_layout,
    tr,
)
from .settings_compact_controls import (
    SETTINGS_SECTION_GAP,
    SETTINGS_SECTION_INNER_SPACING,
    apply_settings_icon_row_height,
    create_settings_auto_height_text_edit,
    create_settings_hint_label,
    create_settings_section_label,
    refresh_settings_text_edit_layouts,
)
from .wrapper_prefix_text_edit import create_wrapper_prefix_text_edit
from ..wrapper_prefix_tokens import wrapper_prefix_requires_token
from .theme import configure_circular_icon_button


def _create_reorder_button(
    parent: QWidget,
    *,
    standard_pixmap: QStyle.StandardPixmap,
    fallback_text: str,
    tooltip: str,
    on_click,
) -> QToolButton:
    button = QToolButton(parent)
    icon = parent.style().standardIcon(standard_pixmap)
    if not icon.isNull():
        configure_circular_icon_button(button, icon=icon, bordered=False)
    else:
        configure_circular_icon_button(button, text=fallback_text, bordered=False)
    button.setToolTip(tooltip)
    button.clicked.connect(on_click)
    return button


class WrapperSectionsEditor(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        show_newlines: bool = False,
        wrap: bool | None = None,
    ) -> None:
        super().__init__(parent)
        self._show_newlines = show_newlines
        self._wrap = wrap
        self._config: dict[str, Any] = {}
        self._order: list[str] = list(WRAPPER_SECTION_IDS)
        self._rows: dict[str, _WrapperSectionRow] = {}
        self._text_changed_slot = None
        self._rows_layout = QVBoxLayout()
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(
            SETTINGS_SECTION_INNER_SPACING + SETTINGS_SECTION_GAP
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(self._rows_layout)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def set_show_newlines(self, show_newlines: bool) -> None:
        self._show_newlines = show_newlines

    def set_wrap(self, wrap: bool | None) -> None:
        self._wrap = wrap

    def load_from_config(self, config: dict[str, Any]) -> None:
        self._config = dict(config)
        order, prefixes = effective_wrapper_layout(config)
        self._order = list(order)
        format_guide = effective_card_templates_format_prompt(config)
        self._rebuild_rows()
        for section_id, row in self._rows.items():
            if section_id == "format_guide":
                row.editor.setPlainText(format_guide)
            elif hasattr(row.editor, "set_prefix_text"):
                row.editor.set_prefix_text(prefixes.get(section_id, ""))
            else:
                row.editor.setPlainText(prefixes.get(section_id, ""))
        self.refresh_layout()

    def refresh_layout(self) -> None:
        refresh_settings_text_edit_layouts(self)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self.refresh_layout)

    def collect(self) -> tuple[list[str], dict[str, str], str]:
        order = list(self._order)
        sections: dict[str, str] = {}
        format_guide = ""
        for section_id in order:
            row = self._rows[section_id]
            if hasattr(row.editor, "to_prefix_text"):
                text = row.editor.to_prefix_text()
            else:
                text = row.editor.toPlainText()
            if section_id == "format_guide":
                format_guide = text
            else:
                sections[section_id] = text
        return order, sections, format_guide

    def _rebuild_rows(self) -> None:
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._rows.clear()
        for index, section_id in enumerate(self._order):
            row = _WrapperSectionRow(
                self,
                section_id=section_id,
                config=self._config,
                show_newlines=self._show_newlines,
                wrap=self._wrap,
                on_move_up=lambda _checked=False, sid=section_id: self._move_section(sid, -1),
                on_move_down=lambda _checked=False, sid=section_id: self._move_section(sid, 1),
                can_move_up=index > 0,
                can_move_down=index < len(self._order) - 1,
            )
            self._rows[section_id] = row
            self._rows_layout.addWidget(row)
        self._connect_text_changed()

    def connect_text_changed(self, slot) -> None:
        self._text_changed_slot = slot
        self._connect_text_changed()

    def _connect_text_changed(self) -> None:
        if self._text_changed_slot is None:
            return
        for row in self._rows.values():
            row.editor.textChanged.connect(self._text_changed_slot)

    def _move_section(self, section_id: str, delta: int) -> None:
        if section_id not in self._order:
            return
        index = self._order.index(section_id)
        target = index + delta
        if target < 0 or target >= len(self._order):
            return
        self._order[index], self._order[target] = self._order[target], self._order[index]
        self._sync_row_order()
        self._refresh_move_buttons()

    def _sync_row_order(self) -> None:
        while self._rows_layout.count():
            self._rows_layout.takeAt(0)
        for section_id in self._order:
            self._rows_layout.addWidget(self._rows[section_id])

    def _refresh_move_buttons(self) -> None:
        last_index = len(self._order) - 1
        for index, section_id in enumerate(self._order):
            row = self._rows[section_id]
            row.up_button.setEnabled(index > 0)
            row.down_button.setEnabled(index < last_index)


class _WrapperSectionRow(QWidget):
    def __init__(
        self,
        parent: QWidget,
        *,
        section_id: str,
        config: dict[str, Any],
        show_newlines: bool,
        wrap: bool | None,
        on_move_up,
        on_move_down,
        can_move_up: bool,
        can_move_down: bool,
    ) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SETTINGS_SECTION_INNER_SPACING)

        header_row = QWidget(self)
        header = QHBoxLayout(header_row)
        header.setContentsMargins(0, SETTINGS_SECTION_GAP, 0, 0)
        header.setSpacing(SETTINGS_SECTION_INNER_SPACING)
        apply_settings_icon_row_height(header_row, top_inset=SETTINGS_SECTION_GAP)
        row_align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        self.up_button = _create_reorder_button(
            self,
            standard_pixmap=QStyle.StandardPixmap.SP_ArrowUp,
            fallback_text="^",
            tooltip=tr("settings.wrapper_section.move_up", config=config),
            on_click=on_move_up,
        )
        self.down_button = _create_reorder_button(
            self,
            standard_pixmap=QStyle.StandardPixmap.SP_ArrowDown,
            fallback_text="v",
            tooltip=tr("settings.wrapper_section.move_down", config=config),
            on_click=on_move_down,
        )
        self.up_button.setEnabled(can_move_up)
        self.down_button.setEnabled(can_move_down)
        label = create_settings_section_label(
            self,
            tr(f"settings.wrapper_section.{section_id}", config=config),
        )
        header.addWidget(self.up_button, 0, row_align)
        header.addWidget(self.down_button, 0, row_align)
        header.addWidget(label, 1, row_align)
        layout.addWidget(header_row)

        if section_id == "format_guide":
            hint = tr("settings.prompt_card_templates_format.hint", config=config)
            layout.addWidget(create_settings_hint_label(self, hint))

        if wrapper_prefix_requires_token(section_id):
            shell, editor = create_wrapper_prefix_text_edit(
                self,
                section_id=section_id,
                show_newlines=show_newlines,
                wrap=wrap,
            )
        else:
            shell, editor = create_settings_auto_height_text_edit(
                self,
                show_newlines=show_newlines,
                wrap=wrap,
            )
        layout.addWidget(shell)
        self.editor = editor
