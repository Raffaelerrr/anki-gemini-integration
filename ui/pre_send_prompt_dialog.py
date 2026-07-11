from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from aqt.qt import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    Qt,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ..config import load_config
from ..i18n import tr
from ..prompt_cache import (
    PROMPT_CACHE_SEGMENT_ORDER,
    PromptCacheBundle,
    PromptCacheSessionContext,
    build_live_system_instruction,
    cached_segment_texts,
    flattened_cache_upload_text,
    rebuild_prompt_cache_bundle,
    segment_label_key,
)
from ..prompt_compose import join_prompt_blocks
from ..prompt_inspection import (
    PromptInspection,
    PromptSegment,
    merge_inspection_system_text,
)
from .settings_compact_controls import (
    configure_addon_text_edit,
    create_prompt_scroll_page,
    create_ui_text_edit,
    refresh_settings_text_edit_layouts,
    scroll_area_to_widget,
)
from .theme import apply_native_page_scroll_theme, muted_hint_html, strong_label_html
from .widgets import PlainNoWheelComboBox

_NO_CACHE_EDITABLE_KEYS = frozenset(
    {
        "prompt.inspect.system_instruction",
        "prompt.inspect.dynamic_rules_prefix",
        "prompt.inspect.dynamic_instructions",
        "prompt.inspect.chat_system_addon",
        "prompt.inspect.next_user_message",
    }
)


@dataclass(frozen=True)
class PreSendPromptOverrides:
    outgoing_payload: str
    system_instruction: str
    bundle: PromptCacheBundle | None = None


@dataclass(frozen=True)
class PreSendPromptContext:
    inspection: PromptInspection
    outgoing_payload: str
    system_instruction: str
    bundle: PromptCacheBundle | None
    model: str
    cache_session: PromptCacheSessionContext | None = None


def _cached_formula_text(bundle: PromptCacheBundle, config: dict[str, Any]) -> str:
    names = [
        tr(segment_label_key(segment_id), config=config)
        for segment_id in bundle.enabled_segment_ids
    ]
    return " + ".join(names)


def _live_formula_text(
    *,
    config: dict[str, Any],
    inspection: PromptInspection,
    has_history: bool,
) -> str:
    names = [tr("prompt.inspect.pre_send.live_system", config=config)]
    if has_history:
        names.append(tr("prompt.inspect.chat_history", config=config))
    names.append(tr("prompt.inspect.next_user_message", config=config))
    return " + ".join(names)


def _compose_live_prompt_preview(
    *,
    live_system: str,
    history_text: str,
    payload: str,
) -> str:
    parts: list[str] = []
    if live_system.strip():
        parts.append(live_system.strip())
    if history_text.strip():
        parts.append(history_text.strip())
    if payload.strip():
        parts.append(payload.strip())
    return join_prompt_blocks(*parts)


def _section_label(parent: QWidget, html: str) -> QLabel:
    label = QLabel(parent)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setText(html)
    return label


def _add_auto_height_editor(
    layout: QVBoxLayout,
    parent: QWidget,
    *,
    text: str,
    read_only: bool = False,
    stretch: int = 0,
) -> QTextEdit:
    editor = create_ui_text_edit(
        parent,
        scroll_free=True,
        auto_height=True,
        minimum=44,
    )[1]
    editor.setPlainText(text)
    editor.setReadOnly(read_only)
    editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    layout.addWidget(editor, stretch)
    return editor


def _merge_system_from_editors(editors: dict[str, QTextEdit]) -> str:
    segments: list[PromptSegment] = []
    for key in (
        "prompt.inspect.system_instruction",
        "prompt.inspect.dynamic_rules_prefix",
        "prompt.inspect.dynamic_instructions",
        "prompt.inspect.chat_system_addon",
    ):
        editor = editors.get(key)
        if editor is None:
            continue
        text = editor.toPlainText()
        if not text.strip() and key != "prompt.inspect.system_instruction":
            continue
        segments.append(PromptSegment(label_key=key, text=text, role="system"))
    return merge_inspection_system_text(segments)


class PreSendPromptDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        *,
        inspection: PromptInspection,
        outgoing_payload: str,
        system_instruction: str,
        bundle: PromptCacheBundle | None,
        model: str,
        cache_session: PromptCacheSessionContext | None = None,
        read_only: bool = False,
        refresh_context: Callable[[], PreSendPromptContext] | None = None,
    ) -> None:
        super().__init__(parent)
        self._read_only = read_only
        self._refresh_context = refresh_context
        self._bundle = bundle
        self._model = model
        self._cache_session = cache_session
        self._system_instruction = system_instruction
        self._outgoing_payload = outgoing_payload
        self._result: PreSendPromptOverrides | None = None
        self._inspection = inspection
        self._segment_editors: dict[str, QTextEdit] = {}
        self._cached_segment_editors: dict[str, QTextEdit] = {}
        self._live_jump_targets: list[tuple[QWidget, str]] = []
        self._cache_jump_targets: list[tuple[QWidget, str]] = []
        self._history_text = ""
        self._history_edit: QTextEdit | None = None
        config = load_config()
        if read_only:
            self.setWindowFlags(
                Qt.WindowType.Window
                | Qt.WindowType.WindowMinimizeButtonHint
                | Qt.WindowType.WindowMaximizeButtonHint
                | Qt.WindowType.WindowCloseButtonHint
            )
            self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
            self.setModal(False)
            self.setWindowTitle(tr("prompt.inspect.preview.title", config=config))
        else:
            self.setWindowTitle(tr("prompt.inspect.pre_send.title", config=config))
        self.resize(720, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        toolbar = QHBoxLayout()
        self._view_switch_btn = QPushButton(self)
        self._view_switch_btn.clicked.connect(self._toggle_view)
        self._view_switch_btn.setVisible(bundle is not None)
        toolbar.addWidget(self._view_switch_btn)
        if read_only and refresh_context is not None:
            self._refresh_btn = QPushButton(
                tr("prompt.inspect.refresh", config=config),
                self,
            )
            self._refresh_btn.clicked.connect(self._refresh_preview_context)
            toolbar.addWidget(self._refresh_btn)
        toolbar.addStretch(1)
        self._jump_combo = PlainNoWheelComboBox(self)
        self._jump_combo.setMinimumWidth(180)
        self._jump_combo.activated.connect(self._on_jump_activated)
        toolbar.addWidget(self._jump_combo)
        root.addLayout(toolbar)

        self._formula_label = QLabel(self)
        self._formula_label.setWordWrap(True)
        self._formula_label.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(self._formula_label)

        self._meta_label = QLabel(self)
        self._meta_label.setWordWrap(True)
        self._meta_label.setTextFormat(Qt.TextFormat.RichText)
        self._meta_label.setText(muted_hint_html(inspection.metadata_text(config)))
        root.addWidget(self._meta_label)

        self._stack = QStackedWidget(self)
        self._stack.currentChanged.connect(self._on_stack_page_changed)
        root.addWidget(self._stack, 1)

        self._live_scroll, live_layout, live_host = create_prompt_scroll_page(self._stack)
        apply_native_page_scroll_theme(self._live_scroll, allow_horizontal_scroll=False)
        self._stack.addWidget(self._live_scroll)

        self._live_system_edit: QTextEdit | None = None
        self._live_payload_edit: QTextEdit | None = None
        self._full_live_prompt_edit: QTextEdit | None = None
        self._full_cached_prompt_edit: QTextEdit | None = None

        if bundle is not None:
            self._build_live_cached_page(
                config,
                live_layout,
                live_host,
                outgoing_payload,
                bundle,
                inspection,
            )
            self._cache_scroll, cache_layout, cache_host = create_prompt_scroll_page(self._stack)
            apply_native_page_scroll_theme(self._cache_scroll, allow_horizontal_scroll=False)
            self._stack.addWidget(self._cache_scroll)
            self._build_caching_page(config, cache_layout, cache_host, bundle)
        else:
            self._cache_scroll = None
            self._build_live_no_cache_page(
                config,
                live_layout,
                live_host,
                inspection,
            )

        buttons = QDialogButtonBox(self)
        if read_only:
            buttons.addButton(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(self.reject)
        else:
            buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
            send_btn = buttons.addButton(
                tr("chat.send", config=config),
                QDialogButtonBox.ButtonRole.AcceptRole,
            )
            send_btn.setDefault(True)
            buttons.rejected.connect(self.reject)
            buttons.accepted.connect(self._accept)
        root.addWidget(buttons)

        if read_only:
            self._apply_read_only_mode()

        self._on_stack_page_changed(self._stack.currentIndex())
        self._apply_newline_visibility(config)
        self._schedule_layout_refresh()

    def _apply_read_only_mode(self) -> None:
        for editor in self.findChildren(QTextEdit):
            editor.setReadOnly(True)

    def apply_context(self, context: PreSendPromptContext) -> None:
        config = load_config()
        self._inspection = context.inspection
        self._bundle = context.bundle
        self._cache_session = context.cache_session
        self._system_instruction = context.system_instruction
        self._outgoing_payload = context.outgoing_payload
        self._meta_label.setText(
            muted_hint_html(context.inspection.metadata_text(config))
        )

        for segment in context.inspection.segments:
            if segment.role == "history":
                self._history_text = segment.text
                if self._history_edit is not None:
                    self._history_edit.setPlainText(segment.text)

        if context.bundle is not None:
            assert self._live_system_edit is not None
            assert self._live_payload_edit is not None
            live_system = build_live_system_instruction(
                config,
                purpose="chat",
                include_meta_rule=True,
                bundle=context.bundle,
            )
            self._live_system_edit.setPlainText(live_system)
            self._live_payload_edit.setPlainText(context.outgoing_payload)
            segment_texts = cached_segment_texts(
                config,
                purpose="chat",
                session=context.cache_session,
                enabled_segment_ids=context.bundle.enabled_segment_ids,
            )
            for segment_id, editor in self._cached_segment_editors.items():
                editor.setPlainText(segment_texts.get(segment_id, ""))
        else:
            for segment in context.inspection.segments:
                editor = self._segment_editors.get(segment.label_key)
                if editor is not None:
                    editor.setPlainText(segment.text)

        self._refresh_live_prompt_preview()
        self._refresh_cached_prompt_preview()
        self._update_formula_label()
        self._schedule_layout_refresh()

    def _refresh_preview_context(self) -> None:
        if self._refresh_context is None:
            return
        self.apply_context(self._refresh_context())

    def _build_live_cached_page(
        self,
        config: dict[str, Any],
        layout: QVBoxLayout,
        host: QWidget,
        outgoing_payload: str,
        bundle: PromptCacheBundle,
        inspection: PromptInspection,
    ) -> None:
        layout.addWidget(
            _section_label(
                host,
                muted_hint_html(
                    tr(
                        "prompt.inspect.pre_send.preview_hint",
                        config=config,
                    )
                    if self._read_only
                    else tr("prompt.inspect.pre_send.live_hint", config=config)
                ),
            )
        )
        if not self._read_only:
            layout.addWidget(
                _section_label(
                    host,
                    muted_hint_html(tr("prompt.inspect.pre_send.live_cache_tip", config=config)),
                )
            )

        full_label = _section_label(
            host,
            strong_label_html(tr("prompt.inspect.pre_send.full_live_prompt", config=config)),
        )
        layout.addWidget(full_label)
        self._live_jump_targets.append(
            (full_label, tr("prompt.inspect.pre_send.full_live_prompt", config=config))
        )

        live_system = build_live_system_instruction(
            config,
            purpose="chat",
            include_meta_rule=True,
            bundle=bundle,
        )
        for segment in inspection.segments:
            if segment.role == "history":
                self._history_text = segment.text

        self._full_live_prompt_edit = _add_auto_height_editor(
            layout,
            host,
            text=_compose_live_prompt_preview(
                live_system=live_system,
                history_text=self._history_text,
                payload=outgoing_payload,
            ),
            read_only=True,
        )

        if not self._read_only:
            layout.addWidget(
                _section_label(
                    host,
                    muted_hint_html(tr("prompt.inspect.pre_send.edit_live_sections", config=config)),
                )
            )

        system_header = _section_label(
            host,
            strong_label_html(tr("prompt.inspect.pre_send.live_system", config=config)),
        )
        layout.addWidget(system_header)
        self._live_jump_targets.append(
            (system_header, tr("prompt.inspect.pre_send.live_system", config=config))
        )
        self._live_system_edit = _add_auto_height_editor(
            layout,
            host,
            text=live_system,
            read_only=self._read_only,
            stretch=1,
        )
        if not self._read_only:
            self._live_system_edit.textChanged.connect(self._refresh_live_prompt_preview)

        if self._history_text.strip():
            history_header = _section_label(
                host,
                strong_label_html(tr("prompt.inspect.chat_history", config=config)),
            )
            layout.addWidget(history_header)
            self._live_jump_targets.append(
                (history_header, tr("prompt.inspect.chat_history", config=config))
            )
            self._history_edit = _add_auto_height_editor(
                layout,
                host,
                text=self._history_text,
                read_only=True,
                stretch=1,
            )

        payload_header = _section_label(
            host,
            strong_label_html(tr("prompt.inspect.next_user_message", config=config)),
        )
        layout.addWidget(payload_header)
        self._live_jump_targets.append(
            (payload_header, tr("prompt.inspect.next_user_message", config=config))
        )
        self._live_payload_edit = _add_auto_height_editor(
            layout,
            host,
            text=outgoing_payload,
            read_only=self._read_only,
            stretch=2,
        )
        if not self._read_only:
            self._live_payload_edit.textChanged.connect(self._refresh_live_prompt_preview)

    def _build_live_no_cache_page(
        self,
        config: dict[str, Any],
        layout: QVBoxLayout,
        host: QWidget,
        inspection: PromptInspection,
    ) -> None:
        if self._read_only:
            layout.addWidget(
                _section_label(
                    host,
                    muted_hint_html(tr("prompt.inspect.pre_send.preview_hint", config=config)),
                )
            )

        full_label = _section_label(
            host,
            strong_label_html(tr("prompt.inspect.pre_send.full_live_prompt", config=config)),
        )
        layout.addWidget(full_label)
        self._live_jump_targets.append(
            (full_label, tr("prompt.inspect.pre_send.full_live_prompt", config=config))
        )
        self._full_live_prompt_edit = _add_auto_height_editor(
            layout,
            host,
            text=inspection.plain_full_text(config),
            read_only=True,
        )

        if not self._read_only:
            layout.addWidget(
                _section_label(
                    host,
                    muted_hint_html(tr("prompt.inspect.pre_send.edit_live_sections", config=config)),
                )
            )

        for segment in inspection.segments:
            title = tr(segment.label_key, config=config)
            header = _section_label(host, strong_label_html(title))
            layout.addWidget(header)
            self._live_jump_targets.append((header, title))

            read_only = self._read_only or segment.label_key not in _NO_CACHE_EDITABLE_KEYS
            editor = _add_auto_height_editor(
                layout,
                host,
                text=segment.text,
                read_only=read_only,
                stretch=1 if segment.label_key == "prompt.inspect.next_user_message" else 0,
            )
            self._segment_editors[segment.label_key] = editor
            if segment.role == "history":
                self._history_text = segment.text
                self._history_edit = editor
            if not read_only:
                editor.textChanged.connect(self._refresh_live_prompt_preview)

    def _build_caching_page(
        self,
        config: dict[str, Any],
        layout: QVBoxLayout,
        host: QWidget,
        bundle: PromptCacheBundle,
    ) -> None:
        layout.addWidget(
            _section_label(
                host,
                muted_hint_html(tr("prompt.inspect.pre_send.cache_hint", config=config)),
            )
        )
        if not self._read_only:
            layout.addWidget(
                _section_label(
                    host,
                    muted_hint_html(tr("prompt.inspect.pre_send.cache_edit_tip", config=config)),
                )
            )

        full_label = _section_label(
            host,
            strong_label_html(tr("prompt.inspect.pre_send.full_cached_prompt", config=config)),
        )
        layout.addWidget(full_label)
        self._cache_jump_targets.append(
            (full_label, tr("prompt.inspect.pre_send.full_cached_prompt", config=config))
        )
        self._full_cached_prompt_edit = _add_auto_height_editor(
            layout,
            host,
            text=flattened_cache_upload_text(bundle),
            read_only=True,
        )

        if not self._read_only:
            layout.addWidget(
                _section_label(
                    host,
                    muted_hint_html(tr("prompt.inspect.pre_send.edit_cached_sections", config=config)),
                )
            )

        segment_texts = cached_segment_texts(
            config,
            purpose="chat",
            session=self._cache_session,
            enabled_segment_ids=bundle.enabled_segment_ids,
        )
        enabled_set = set(bundle.enabled_segment_ids)
        for segment_id in PROMPT_CACHE_SEGMENT_ORDER:
            if segment_id not in enabled_set:
                continue
            raw_text = segment_texts.get(segment_id, "")
            title = tr(segment_label_key(segment_id), config=config)
            header = _section_label(host, strong_label_html(title))
            layout.addWidget(header)
            self._cache_jump_targets.append((header, title))
            editor = _add_auto_height_editor(
                layout,
                host,
                text=raw_text,
                read_only=self._read_only,
                stretch=1 if segment_id == "custom_cache_text" else 0,
            )
            self._cached_segment_editors[segment_id] = editor
            if not self._read_only:
                editor.textChanged.connect(self._refresh_cached_prompt_preview)

    def _current_scroll_area(self) -> QScrollArea | None:
        if self._stack.currentIndex() == 0:
            return self._live_scroll
        return self._cache_scroll

    def _current_jump_targets(self) -> list[tuple[QWidget, str]]:
        if self._stack.currentIndex() == 0:
            return self._live_jump_targets
        return self._cache_jump_targets

    def _refresh_jump_combo(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        self._jump_combo.blockSignals(True)
        self._jump_combo.clear()
        self._jump_combo.addItem(tr("prompt.inspect.pre_send.jump", config=config))
        for _, label in self._current_jump_targets():
            self._jump_combo.addItem(label)
        self._jump_combo.setCurrentIndex(0)
        self._jump_combo.blockSignals(False)

    def _update_formula_label(self) -> None:
        config = load_config()
        if self._bundle is not None and self._stack.currentIndex() == 1:
            formula = _cached_formula_text(self._bundle, config)
        elif self._bundle is not None:
            formula = _live_formula_text(
                config=config,
                inspection=self._inspection,
                has_history=bool(self._history_text.strip()),
            )
        else:
            formula = self._inspection.formula_text(config)
        self._formula_label.setText(
            strong_label_html(
                tr("prompt.inspect.formula", config=config, formula=formula)
            )
        )

    def _on_jump_activated(self, index: int) -> None:
        if index <= 0:
            return
        targets = self._current_jump_targets()
        target_index = index - 1
        if target_index < 0 or target_index >= len(targets):
            return
        scroll = self._current_scroll_area()
        if scroll is not None:
            scroll_area_to_widget(scroll, targets[target_index][0])
        self._jump_combo.blockSignals(True)
        self._jump_combo.setCurrentIndex(0)
        self._jump_combo.blockSignals(False)

    def _refresh_live_prompt_preview(self) -> None:
        if self._full_live_prompt_edit is None:
            return
        if self._bundle is not None:
            live_system = (
                self._live_system_edit.toPlainText()
                if self._live_system_edit is not None
                else ""
            )
            payload = (
                self._live_payload_edit.toPlainText()
                if self._live_payload_edit is not None
                else ""
            )
            preview = _compose_live_prompt_preview(
                live_system=live_system,
                history_text=self._history_text,
                payload=payload,
            )
        else:
            parts: list[str] = []
            system = _merge_system_from_editors(self._segment_editors)
            if system.strip():
                parts.append(system)
            if self._history_text.strip():
                parts.append(self._history_text)
            payload_editor = self._segment_editors.get("prompt.inspect.next_user_message")
            if payload_editor is not None:
                payload = payload_editor.toPlainText()
                if payload.strip():
                    parts.append(payload)
            preview = join_prompt_blocks(*parts)
        self._full_live_prompt_edit.setPlainText(preview)
        self._schedule_layout_refresh()

    def _refresh_cached_prompt_preview(self) -> None:
        if self._full_cached_prompt_edit is None or self._bundle is None:
            return
        segment_texts = {
            segment_id: editor.toPlainText()
            for segment_id, editor in self._cached_segment_editors.items()
        }
        config = load_config()
        rebuilt = rebuild_prompt_cache_bundle(
            config,
            purpose="chat",
            enabled_segment_ids=self._bundle.enabled_segment_ids,
            segment_texts=segment_texts,
            live_system_text=self._bundle.live_system_text,
        )
        preview = flattened_cache_upload_text(rebuilt) if rebuilt is not None else ""
        self._full_cached_prompt_edit.setPlainText(preview)
        self._schedule_layout_refresh()

    def _apply_newline_visibility(self, config: dict[str, Any]) -> None:
        show_newlines = bool(config.get("settings_show_text_newlines", False))
        for editor in self.findChildren(QTextEdit):
            configure_addon_text_edit(editor, show_newlines=show_newlines, scroll_free=True)

    def _schedule_layout_refresh(self) -> None:
        from aqt.qt import QTimer

        QTimer.singleShot(0, lambda: refresh_settings_text_edit_layouts(self))

    def _focus_current_page(self) -> None:
        page = self._stack.currentWidget()
        if page is not None:
            page.setFocus(Qt.FocusReason.OtherFocusReason)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._focus_current_page()

    def _update_view_switch_button(self) -> None:
        config = load_config()
        if self._bundle is None:
            self._view_switch_btn.setVisible(False)
            return
        if self._stack.currentIndex() == 0:
            self._view_switch_btn.setText(
                tr("prompt.inspect.pre_send.view_caching", config=config)
            )
        else:
            self._view_switch_btn.setText(
                tr("prompt.inspect.pre_send.view_live", config=config)
            )
        self._view_switch_btn.setVisible(True)

    def _toggle_view(self) -> None:
        if self._bundle is None:
            return
        self._stack.setCurrentIndex(1 - self._stack.currentIndex())

    def _on_stack_page_changed(self, _index: int) -> None:
        self._update_view_switch_button()
        self._update_formula_label()
        self._refresh_jump_combo()
        self._jump_combo.setVisible(
            self._bundle is None or self._stack.currentIndex() == 0 or bool(self._cache_jump_targets)
        )
        self._focus_current_page()

    def _accept(self) -> None:
        bundle = self._bundle
        if bundle is not None:
            assert self._live_payload_edit is not None
            assert self._live_system_edit is not None
            outgoing_payload = self._live_payload_edit.toPlainText()
            system_instruction = self._live_system_edit.toPlainText()
            segment_texts = {
                segment_id: editor.toPlainText()
                for segment_id, editor in self._cached_segment_editors.items()
            }
            config = load_config()
            rebuilt = rebuild_prompt_cache_bundle(
                config,
                purpose="chat",
                enabled_segment_ids=bundle.enabled_segment_ids,
                segment_texts=segment_texts,
                live_system_text=system_instruction,
            )
            if rebuilt is not None:
                bundle = rebuilt
            else:
                bundle = replace(bundle, live_system_text=system_instruction.strip())
        else:
            outgoing_payload = self._segment_editors[
                "prompt.inspect.next_user_message"
            ].toPlainText()
            system_instruction = _merge_system_from_editors(self._segment_editors)
        self._result = PreSendPromptOverrides(
            outgoing_payload=outgoing_payload,
            system_instruction=system_instruction,
            bundle=bundle,
        )
        self.accept()

    def overrides(self) -> PreSendPromptOverrides | None:
        return self._result


def confirm_pre_send_prompt(
    parent: QWidget | None,
    *,
    context: PreSendPromptContext,
) -> PreSendPromptOverrides | None:
    dialog = PreSendPromptDialog(
        parent,
        inspection=context.inspection,
        outgoing_payload=context.outgoing_payload,
        system_instruction=context.system_instruction,
        bundle=context.bundle,
        model=context.model,
        cache_session=context.cache_session,
        read_only=False,
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.overrides()


def open_prompt_preview(
    parent: QWidget | None,
    *,
    context: PreSendPromptContext,
    refresh_context: Callable[[], PreSendPromptContext],
    existing: PreSendPromptDialog | None = None,
) -> PreSendPromptDialog:
    if existing is not None:
        existing.apply_context(context)
        existing.show()
        existing.raise_()
        existing.activateWindow()
        return existing
    dialog = PreSendPromptDialog(
        parent,
        inspection=context.inspection,
        outgoing_payload=context.outgoing_payload,
        system_instruction=context.system_instruction,
        bundle=context.bundle,
        model=context.model,
        cache_session=context.cache_session,
        read_only=True,
        refresh_context=refresh_context,
    )
    dialog.show()
    return dialog
