from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aqt.qt import (
    QHBoxLayout,
    QLabel,
    QPoint,
    QScrollArea,
    QSizePolicy,
    Qt,
    QVBoxLayout,
    QWidget,
)

from ..config import load_config
from ..i18n import (
    chat_edit_templates_detail_text,
    chat_edit_templates_title_text,
    tr,
)
from .card_templates import CardTemplateData
from .settings_compact_controls import create_ui_text_edit
from .theme import (
    apply_native_fields_scroll_theme,
    apply_native_text_edit_surface_theme,
    field_name_label_html,
    muted_hint_html,
    strong_label_html,
)
from .widgets import PlainNoWheelComboBox, ScrollAwareTextEdit, bind_text_edit_auto_height

_CARD_BLOCK_SPACING = 12
_SECTION_GAP = 6
_CAPTION_TOP_GAP = 4
_CAPTION_BOTTOM_GAP = 2
_AFTER_EDITOR_GAP = 8
_TEMPLATE_EDITOR_MIN_HEIGHT = 44


def _clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def _add_spacer(layout: QVBoxLayout, host: QWidget, height: int) -> None:
    gap = QWidget(host)
    gap.setFixedHeight(height)
    gap.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    layout.addWidget(gap)


class TemplatesEditPanel(QWidget):
    """Compact editable card templates (not included in the note preview)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.on_templates_changed: Callable[[], None] | None = None
        self._template_editors: list[tuple[str, ScrollAwareTextEdit, ScrollAwareTextEdit]] = []
        self._card_blocks: list[QWidget] = []
        self._styling_block: QWidget | None = None
        self._styling_editor: ScrollAwareTextEdit | None = None
        self._jump_targets: list[tuple[QWidget, str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(4)

        self._title = QLabel(self)
        self._title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._title)

        self._detail = QLabel(self)
        self._detail.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._detail)

        self._jump_host = QWidget(self)
        jump_layout = QHBoxLayout(self._jump_host)
        jump_layout.setContentsMargins(0, 0, 0, 0)
        jump_layout.setSpacing(0)
        jump_layout.addStretch(1)
        self._jump_combo = PlainNoWheelComboBox(self._jump_host)
        self._jump_combo.setMinimumWidth(180)
        self._jump_combo.activated.connect(self._on_jump_activated)
        jump_layout.addWidget(self._jump_combo)
        self._jump_host.setVisible(False)
        layout.addWidget(self._jump_host)

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
        self._fields_layout.setContentsMargins(8, 6, 8, 10)
        self._fields_layout.setSpacing(0)
        self._fields_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._host.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._scroll.setWidget(self._host)
        layout.addWidget(self._scroll, 1)

        apply_native_fields_scroll_theme(self, self._scroll)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(56)
        self.setVisible(False)

    def apply_theme(self) -> None:
        apply_native_fields_scroll_theme(self, self._scroll)
        if self._styling_editor is not None:
            apply_native_text_edit_surface_theme(self._styling_editor)
        for _, front_editor, back_editor in self._template_editors:
            apply_native_text_edit_surface_theme(front_editor)
            apply_native_text_edit_surface_theme(back_editor)

    def apply_language(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        self._title.setText(strong_label_html(chat_edit_templates_title_text(config)))
        self._detail.setText(muted_hint_html(chat_edit_templates_detail_text(config)))
        self._refresh_jump_combo(config)

    def clear(self) -> None:
        _clear_layout(self._fields_layout)
        self._template_editors.clear()
        self._card_blocks.clear()
        self._styling_block = None
        self._styling_editor = None
        self._jump_targets.clear()
        self._jump_combo.clear()
        self._jump_host.setVisible(False)
        self.setVisible(False)

    def has_templates(self) -> bool:
        return bool(self._template_editors)

    def has_editable_sections(self) -> bool:
        return bool(self._template_editors) or self._styling_editor is not None

    def get_styling(self) -> str:
        if self._styling_editor is None:
            return ""
        return self._styling_editor.toPlainText()

    def get_templates(self) -> list[CardTemplateData]:
        return [
            CardTemplateData(
                name=name,
                front=front_editor.toPlainText(),
                back=back_editor.toPlainText(),
            )
            for name, front_editor, back_editor in self._template_editors
        ]

    def set_styling_only(self, styling: str) -> None:
        if not styling.strip():
            self.clear()
            return
        _clear_layout(self._fields_layout)
        self._template_editors.clear()
        self._card_blocks.clear()
        self._styling_block = None
        self._styling_editor = None
        self._jump_targets.clear()
        config = load_config()
        self._add_styling_section(styling, config)
        self._refresh_jump_combo(config)
        self._jump_host.setVisible(bool(self._jump_targets))
        self.apply_language(config)

    def _add_styling_section(self, styling: str, config: dict[str, Any]) -> None:
        styling_label = tr("chat.context.section.styling", config=config)
        styling_block = QWidget(self._host)
        styling_layout = QVBoxLayout(styling_block)
        styling_layout.setContentsMargins(0, 0, 0, 0)
        styling_layout.setSpacing(0)
        self._styling_block = styling_block

        styling_header = QLabel(
            field_name_label_html(styling_label),
            styling_block,
        )
        styling_header.setContentsMargins(0, 0, 0, _SECTION_GAP)
        styling_header.setStyleSheet("margin: 0px; padding: 0px; background: transparent;")
        styling_header.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        styling_header.setFixedHeight(styling_header.fontMetrics().height() + _SECTION_GAP)
        styling_layout.addWidget(styling_header)

        styling_shell, styling_editor = create_ui_text_edit(
            styling_block,
            editor_class=ScrollAwareTextEdit,
        )
        styling_editor.setPlainText(styling)
        apply_native_text_edit_surface_theme(styling_editor)
        styling_editor.document().setDocumentMargin(0)
        styling_editor.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        bind_text_edit_auto_height(
            styling_editor,
            minimum=_TEMPLATE_EDITOR_MIN_HEIGHT,
            maximum=None,
        )
        styling_editor.textChanged.connect(self._emit_templates_changed)
        styling_layout.addWidget(styling_shell)
        self._styling_editor = styling_editor

        self._fields_layout.addWidget(styling_block)
        self._jump_targets.append((styling_header, styling_label))

    def set_templates(
        self,
        templates: list[CardTemplateData],
        *,
        styling: str = "",
        include_styling: bool = True,
    ) -> None:
        _clear_layout(self._fields_layout)
        self._template_editors.clear()
        self._card_blocks.clear()
        self._styling_block = None
        self._styling_editor = None
        self._jump_targets.clear()
        if not templates:
            self.clear()
            return

        config = load_config()
        if include_styling:
            self._add_styling_section(styling, config)

        for index, template in enumerate(templates):
            if index > 0 or include_styling:
                _add_spacer(self._fields_layout, self._host, _CARD_BLOCK_SPACING)

            card_block = QWidget(self._host)
            card_layout = QVBoxLayout(card_block)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(0)
            self._card_blocks.append(card_block)

            label = QLabel(
                field_name_label_html(
                    tr(
                        "chat.edit_templates.card_label",
                        config=config,
                        index=index + 1,
                        name=template.name,
                    )
                ),
                card_block,
            )
            label.setContentsMargins(0, 0, 0, _SECTION_GAP)
            label.setStyleSheet("margin: 0px; padding: 0px; background: transparent;")
            label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            label.setFixedHeight(label.fontMetrics().height() + _SECTION_GAP)
            card_layout.addWidget(label)

            front_caption = QLabel(
                tr("chat.context.front_template", config=config),
                card_block,
            )
            front_caption.setContentsMargins(0, _CAPTION_TOP_GAP, 0, _CAPTION_BOTTOM_GAP)
            front_caption.setStyleSheet("margin: 0px; padding: 0px; background: transparent;")
            card_layout.addWidget(front_caption)
            front_shell, front_editor = create_ui_text_edit(
                card_block,
                editor_class=ScrollAwareTextEdit,
            )
            front_editor.setPlainText(template.front)
            apply_native_text_edit_surface_theme(front_editor)
            front_editor.document().setDocumentMargin(0)
            front_editor.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            bind_text_edit_auto_height(
                front_editor,
                minimum=_TEMPLATE_EDITOR_MIN_HEIGHT,
                maximum=None,
            )
            front_editor.textChanged.connect(self._emit_templates_changed)
            card_layout.addWidget(front_shell)

            _add_spacer_in(card_layout, card_block, _AFTER_EDITOR_GAP)

            back_caption = QLabel(
                tr("chat.context.back_template", config=config),
                card_block,
            )
            back_caption.setContentsMargins(0, _CAPTION_TOP_GAP, 0, _CAPTION_BOTTOM_GAP)
            back_caption.setStyleSheet("margin: 0px; padding: 0px; background: transparent;")
            card_layout.addWidget(back_caption)
            back_shell, back_editor = create_ui_text_edit(
                card_block,
                editor_class=ScrollAwareTextEdit,
            )
            back_editor.setPlainText(template.back)
            apply_native_text_edit_surface_theme(back_editor)
            back_editor.document().setDocumentMargin(0)
            back_editor.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            bind_text_edit_auto_height(
                back_editor,
                minimum=_TEMPLATE_EDITOR_MIN_HEIGHT,
                maximum=None,
            )
            back_editor.textChanged.connect(self._emit_templates_changed)
            card_layout.addWidget(back_shell)

            self._fields_layout.addWidget(card_block)
            self._template_editors.append((template.name, front_editor, back_editor))
            card_jump_label = tr(
                "chat.edit_templates.card_label",
                config=config,
                index=index + 1,
                name=template.name,
            )
            self._jump_targets.append((label, card_jump_label))

        self._refresh_jump_combo(config)
        self._jump_host.setVisible(True)
        self.apply_language(config)

    def _refresh_jump_combo(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        self._jump_combo.blockSignals(True)
        self._jump_combo.clear()
        self._jump_combo.addItem(tr("chat.edit_templates.jump", config=config))
        for _, label in self._jump_targets:
            self._jump_combo.addItem(label)
        self._jump_combo.setCurrentIndex(0)
        self._jump_combo.blockSignals(False)

    def _scroll_to_widget_top(self, widget: QWidget) -> None:
        host = self._scroll.widget()
        if host is None:
            return
        top = widget.mapTo(host, QPoint(0, 0)).y()
        scroll_bar = self._scroll.verticalScrollBar()
        scroll_bar.setValue(max(0, top))

    def _on_jump_activated(self, index: int) -> None:
        if index <= 0:
            return
        target_index = index - 1
        if target_index < 0 or target_index >= len(self._jump_targets):
            return
        target_widget, _ = self._jump_targets[target_index]
        self._scroll_to_widget_top(target_widget)
        self._jump_combo.blockSignals(True)
        self._jump_combo.setCurrentIndex(0)
        self._jump_combo.blockSignals(False)

    def _emit_templates_changed(self) -> None:
        if self.on_templates_changed is not None:
            self.on_templates_changed()


def _add_spacer_in(layout: QVBoxLayout, host: QWidget, height: int) -> None:
    gap = QWidget(host)
    gap.setFixedHeight(height)
    gap.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    layout.addWidget(gap)
