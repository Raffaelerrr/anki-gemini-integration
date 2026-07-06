from __future__ import annotations

import html
import threading
from typing import Any

from aqt import mw
from aqt.qt import (
    QApplication,
    QCheckBox,
    QCloseEvent,
    QShowEvent,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QTextCursor,
    QTextEdit,
    Qt,
    QTimer,
    QUrl,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import tooltip

from ..chat_context_wrapper import wrapper_has_conditional_blocks
from ..config import api_key_configured, load_config, save_config
from ..i18n import (
    chat_context_wrapper_for_session,
    chat_context_wrapper_missing_placeholders,
    chat_edit_wrapper_hint_text,
    chat_edit_wrapper_label_text,
    effective_brain_import_message,
    effective_chat_context_wrapper,
    format_chat_context_message,
    is_builtin_chat_context_wrapper,
    wrapper_import_warning_text,
    wrapper_missing_import_placeholders,
    tr,
)
from ..prompt_inspection import (
    build_chat_prompt_inspection,
    chat_session_config_changed,
    chat_session_config_fingerprint,
)
from ..token_estimate import estimate_chat_request_tokens
from .prompt_inspection_dialog import PromptInspectionWindow
from ..gemini_client import (
    GeminiAuthError,
    GeminiCancelledError,
    GeminiError,
    GeminiRateLimitError,
    call_gemini,
    extract_dynamic_rules,
    merge_system_instructions,
    stream_gemini,
    trim_history,
)
from .card_templates import (
    CardTemplateData,
    extract_notetype_context,
    format_card_templates_block,
)
from .chat_formatter import format_gemini_reply_html, format_streaming_reply_html
from .chat_log_renderer import render_chat_document
from .chat_messages import ChatMessage
from .imported_note_preview_window import ImportedNotePreviewWindow
from .note_preview_panel import NotePreviewPanel
from .templates_edit_panel import TemplatesEditPanel
from .settings_compact_controls import create_ui_text_edit
from .theme import (
    chat_document_stylesheet,
    loading_label_stylesheet,
    muted_hint_html,
    refresh_native_text_edits_in,
    strong_label_html,
    settings_stale_banner_stylesheet,
)
from .widgets import bind_text_edit_auto_height


def _format_note_context(fields: list[tuple[str, str]], config: dict[str, Any]) -> str:
    lines: list[str] = []
    for name, value in fields:
        if not value.strip():
            continue
        lines.append(f"{tr('chat.context.field', config=config, name=name)}\n{value}")
    return "\n\n".join(lines)


class ChatWindow(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.silentlyClose = True
        self.resize(520, 520)

        self.api_history: list[dict[str, Any]] = []
        self.note_context: str | None = None
        self._imported_fields: list[tuple[str, str]] = []
        self._imported_card_templates: list[CardTemplateData] = []
        self._imported_notetype_css: str = ""
        self._imported_notetype_id: int | None = None
        self._context_wrapper_template: str | None = None
        self._messages: list[ChatMessage] = []
        self._loading_phase = 0
        self._copy_blocks: dict[str, str] = {}
        self._copy_counter = 0
        self._streaming_message_index: int | None = None
        self._stream_visible = False
        self._loading_mode: str | None = None
        self._closing = False
        self._request_in_flight = False
        self._cancel_event = threading.Event()
        self._active_response = None
        self._restorable_user_text = ""
        self._request_token = 0
        self._note_preview_window: ImportedNotePreviewWindow | None = None
        self._prompt_inspection_window: PromptInspectionWindow | None = None
        self._session_config_fingerprint = ""
        self._settings_stale_banner_dismissed = False
        self._wrapper_warning_dismissed: set[str] = set()

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.context_checkbox = QCheckBox(self)
        self.context_checkbox.setChecked(False)
        self.context_checkbox.setEnabled(False)
        self.context_checkbox.toggled.connect(self._on_context_checkbox_toggled)
        toolbar.addWidget(self.context_checkbox)

        self.edit_wrapper_checkbox = QCheckBox(self)
        self.edit_wrapper_checkbox.setChecked(False)
        self.edit_wrapper_checkbox.setEnabled(False)
        self.edit_wrapper_checkbox.toggled.connect(self._on_edit_wrapper_toggled)
        toolbar.addWidget(self.edit_wrapper_checkbox)

        self.edit_templates_checkbox = QCheckBox(self)
        self.edit_templates_checkbox.setChecked(False)
        self.edit_templates_checkbox.setEnabled(False)
        self.edit_templates_checkbox.toggled.connect(self._on_edit_templates_toggled)
        toolbar.addWidget(self.edit_templates_checkbox)

        self.btn_note_preview = QPushButton(self)
        self.btn_note_preview.setEnabled(False)
        self.btn_note_preview.clicked.connect(self._open_note_preview_window)
        toolbar.addWidget(self.btn_note_preview)

        self.btn_inspect_prompt = QPushButton(self)
        self.btn_inspect_prompt.setVisible(False)
        self.btn_inspect_prompt.setToolTip(tr("chat.inspect_prompt.tooltip"))
        self.btn_inspect_prompt.clicked.connect(self._open_prompt_inspection)
        toolbar.addWidget(self.btn_inspect_prompt)

        self.btn_clear = QPushButton(self)
        self.btn_clear.clicked.connect(self.clear_conversation)
        toolbar.addWidget(self.btn_clear)
        layout.addLayout(toolbar)

        self._settings_stale_banner = QWidget(self)
        self._settings_stale_banner.setObjectName("settingsStaleBanner")
        stale_layout = QHBoxLayout(self._settings_stale_banner)
        stale_layout.setContentsMargins(0, 0, 0, 0)
        stale_layout.setSpacing(0)
        self._settings_stale_banner_text = QLabel(self._settings_stale_banner)
        self._settings_stale_banner_text.setObjectName("settingsStaleBannerText")
        self._settings_stale_banner_text.setWordWrap(True)
        stale_layout.addWidget(self._settings_stale_banner_text, 1)
        self._settings_stale_banner_close = QPushButton(self._settings_stale_banner)
        self._settings_stale_banner_close.setObjectName("settingsStaleBannerClose")
        self._settings_stale_banner_close.setFixedSize(28, 28)
        self._settings_stale_banner_close.clicked.connect(self._dismiss_settings_stale_banner)
        stale_layout.addWidget(
            self._settings_stale_banner_close,
            0,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        self._settings_stale_banner.setVisible(False)
        layout.addWidget(self._settings_stale_banner)

        self.note_preview_panel = NotePreviewPanel(self)
        self.note_preview_panel.on_fields_changed = self._sync_note_context_from_preview
        layout.addWidget(self.note_preview_panel, 0)

        self.chat_log = QTextBrowser(self)
        self.chat_log.setOpenLinks(False)
        self.chat_log.setReadOnly(True)
        self.chat_log.anchorClicked.connect(self._on_anchor_clicked)
        layout.addWidget(self.chat_log, 1)

        self._wrapper_panel = QWidget(self)
        panel_layout = QVBoxLayout(self._wrapper_panel)
        panel_layout.setContentsMargins(0, 4, 0, 4)
        panel_layout.setSpacing(4)
        wrapper_header = QHBoxLayout()
        wrapper_header.setContentsMargins(0, 0, 0, 0)
        self.context_edit_wrapper_label = QLabel(self._wrapper_panel)
        wrapper_header.addWidget(self.context_edit_wrapper_label)
        wrapper_header.addStretch(1)
        panel_layout.addLayout(wrapper_header)
        self.context_edit_wrapper_hint = QLabel(self._wrapper_panel)
        panel_layout.addWidget(self.context_edit_wrapper_hint)
        self.context_edit_wrapper_warning_banner = QWidget(self._wrapper_panel)
        self.context_edit_wrapper_warning_banner.setObjectName("settingsStaleBanner")
        wrapper_warning_layout = QHBoxLayout(self.context_edit_wrapper_warning_banner)
        wrapper_warning_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_warning_layout.setSpacing(0)
        self.context_edit_wrapper_warning = QLabel(self.context_edit_wrapper_warning_banner)
        self.context_edit_wrapper_warning.setObjectName("settingsStaleBannerText")
        self.context_edit_wrapper_warning.setWordWrap(True)
        wrapper_warning_layout.addWidget(self.context_edit_wrapper_warning, 1)
        self.context_edit_wrapper_warning_close = QPushButton(self.context_edit_wrapper_warning_banner)
        self.context_edit_wrapper_warning_close.setObjectName("settingsStaleBannerClose")
        self.context_edit_wrapper_warning_close.setFixedSize(28, 28)
        self.context_edit_wrapper_warning_close.clicked.connect(self._dismiss_wrapper_warning_banner)
        wrapper_warning_layout.addWidget(
            self.context_edit_wrapper_warning_close,
            0,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        self.context_edit_wrapper_warning_banner.setVisible(False)
        panel_layout.addWidget(self.context_edit_wrapper_warning_banner)
        wrapper_shell, self.context_edit_wrapper_input = create_ui_text_edit(
            self._wrapper_panel,
        )
        self.context_edit_wrapper_input.setMinimumHeight(70)
        bind_text_edit_auto_height(self.context_edit_wrapper_input, minimum=70, maximum=110)
        self.context_edit_wrapper_input.textChanged.connect(self._on_context_edit_wrapper_changed)
        panel_layout.addWidget(wrapper_shell)
        self._wrapper_panel.setVisible(False)
        layout.addWidget(self._wrapper_panel, 0)

        self.templates_edit_panel = TemplatesEditPanel(self)
        self.templates_edit_panel.on_templates_changed = self._sync_templates_from_panel
        layout.addWidget(self.templates_edit_panel, 0)

        self.loading_label = QLabel("", self)
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        input_layout = QHBoxLayout()
        input_shell, self.input_field = create_ui_text_edit(
            self,
            editor_class=QTextEdit,
        )
        input_shell.setFixedHeight(80)
        self.input_field.setFixedHeight(80)
        self.input_field.installEventFilter(self)

        self.send_button = QPushButton(self)
        self.send_button.clicked.connect(self._on_send_button_clicked)
        self.send_button.setFixedHeight(80)

        input_layout.addWidget(input_shell)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)

        self._configure_chat_default_buttons()

        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self._update_loading_animation)

        self._apply_chat_theme()
        self._apply_static_texts()
        self._add_system_message(
            tr("chat.welcome"),
            kind="gemini",
            label=tr("chat.label.gemini"),
        )
        self._capture_session_config()

    def _configure_chat_default_buttons(self) -> None:
        """Keep Enter on Send/Stop; toolbar buttons must not steal dialog default."""
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)
        self.send_button.setAutoDefault(True)
        self.send_button.setDefault(True)

    def _focus_chat_input(self) -> None:
        self.input_field.setFocus()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._configure_chat_default_buttons()
        self._focus_chat_input()

    def _capture_session_config(self) -> None:
        config = load_config()
        self._session_config_fingerprint = chat_session_config_fingerprint(config)
        self._settings_stale_banner_dismissed = False
        self._update_settings_stale_banner(config)

    def _dismiss_settings_stale_banner(self) -> None:
        self._settings_stale_banner_dismissed = True
        self._settings_stale_banner.setVisible(False)

    def _update_settings_stale_banner(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        stale = chat_session_config_changed(self._session_config_fingerprint, config)
        visible = stale and not self._settings_stale_banner_dismissed
        self._settings_stale_banner.setVisible(visible)
        if visible:
            self._settings_stale_banner_text.setText(
                tr("chat.settings_stale.message", config=config)
            )

    def _sync_prompt_inspection_button(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        self.btn_inspect_prompt.setVisible(bool(config.get("chat_prompt_inspection", False)))

    def build_chat_prompt_inspection(self):
        config = load_config()
        user_text = self.input_field.toPlainText().strip()
        draft = user_text or tr("prompt.inspect.empty_draft", config=config)
        if self.context_checkbox.isChecked() and self.note_context:
            payload = self._build_outgoing_payload(config, draft)
        else:
            payload = user_text or tr("prompt.inspect.empty_next_message", config=config)
        return build_chat_prompt_inspection(
            config,
            history=list(self.api_history),
            next_user_text=user_text,
            outgoing_payload=payload,
        )

    def _open_prompt_inspection(self) -> None:
        config = load_config()
        inspection = self.build_chat_prompt_inspection()
        if self._prompt_inspection_window is None:
            self._prompt_inspection_window = PromptInspectionWindow(
                self,
                title=tr("prompt.inspect.chat.title", config=config),
                refresh_callback=self.build_chat_prompt_inspection,
            )
        self._prompt_inspection_window.show_inspection(inspection, config)

    def apply_settings_refresh(self) -> None:
        config = load_config()
        self.apply_language()
        self._sync_prompt_inspection_button(config)
        self._update_settings_stale_banner(config)
        if self._prompt_inspection_window is not None and self._prompt_inspection_window.isVisible():
            self._prompt_inspection_window.refresh()

    def _apply_chat_theme(self) -> None:
        self.chat_log.document().setDefaultStyleSheet(chat_document_stylesheet())
        self.loading_label.setStyleSheet(loading_label_stylesheet())
        self.context_edit_wrapper_warning_banner.setStyleSheet(settings_stale_banner_stylesheet())
        self._settings_stale_banner.setStyleSheet(settings_stale_banner_stylesheet())
        self.note_preview_panel.apply_theme()
        self.templates_edit_panel.apply_theme()
        if self._note_preview_window is not None:
            self._note_preview_window.apply_theme()
        refresh_native_text_edits_in(self)
        self._render_chat_log(preserve_scroll=False)

    def _apply_static_texts(self) -> None:
        config = load_config()
        self.setWindowTitle(tr("chat.title", config=config))
        self.context_checkbox.setText(tr("chat.include_context", config=config))
        self.edit_wrapper_checkbox.setText(tr("chat.edit_wrapper", config=config))
        self.edit_templates_checkbox.setText(tr("chat.edit_templates", config=config))
        self._update_wrapper_static_texts(config)
        self.note_preview_panel.apply_language(config)
        self.btn_note_preview.setText(tr("chat.preview.open_window", config=config))
        self.btn_note_preview.setToolTip(tr("chat.preview.open_window.tooltip", config=config))
        self.btn_clear.setText(tr("chat.new_conversation", config=config))
        self.btn_inspect_prompt.setText(tr("chat.inspect_prompt", config=config))
        self.btn_inspect_prompt.setToolTip(tr("chat.inspect_prompt.tooltip", config=config))
        self._settings_stale_banner_close.setText(tr("chat.settings_stale.dismiss", config=config))
        self.context_edit_wrapper_warning_close.setText(
            tr("chat.settings_stale.dismiss", config=config)
        )
        self._sync_prompt_inspection_button(config)
        self._update_settings_stale_banner(config)
        self.chat_log.setPlaceholderText(tr("chat.log_placeholder", config=config))
        self.input_field.setPlaceholderText(tr("chat.input_placeholder", config=config))
        if self._request_in_flight:
            self.send_button.setText(tr("chat.stop", config=config))
        else:
            self.send_button.setText(tr("chat.send", config=config))
        if self.loading_label.isVisible():
            self._update_loading_animation()
        if self._note_preview_window is not None:
            self._note_preview_window.apply_language(config)

    def _close_note_preview_window(self) -> None:
        if self._note_preview_window is None:
            return
        self._note_preview_window.close()
        self._note_preview_window = None

    def _open_note_preview_window(self) -> None:
        if not self.note_preview_panel.has_content():
            return
        if self._note_preview_window is None:
            self._note_preview_window = ImportedNotePreviewWindow(
                self,
                field_provider=self.note_preview_panel.get_fields,
                notetype_id_provider=lambda: self._imported_notetype_id,
            )
            self._note_preview_window.destroyed.connect(
                lambda *_: setattr(self, "_note_preview_window", None)
            )
        config = load_config()
        self._note_preview_window.apply_language(config)
        self._note_preview_window.apply_theme()
        self._note_preview_window.refresh()
        self._note_preview_window.show()
        self._note_preview_window.raise_()
        self._note_preview_window.activateWindow()

    def _on_context_checkbox_toggled(self, checked: bool) -> None:
        if not checked and self.note_preview_panel.has_content():
            self.note_preview_panel.set_content_visible(False)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._imported_fields:
            QTimer.singleShot(0, self.note_preview_panel.reflow)

    def apply_theme(self) -> None:
        self._apply_chat_theme()

    def apply_language(self) -> None:
        self._apply_static_texts()

    def closeEvent(self, event: QCloseEvent) -> None:
        global _chat_window
        self._closing = True
        self._cancel_in_flight_request()
        self._stop_loading()
        self._close_note_preview_window()
        _chat_window = None
        super().closeEvent(event)

    def prepare_shutdown(self) -> None:
        self._closing = True
        self._cancel_in_flight_request()
        self._stop_loading()
        self._close_note_preview_window()
        self._stream_visible = False
        self._streaming_message_index = None

    def _render_chat_log(
        self,
        *,
        preserve_scroll: bool = False,
        scroll_anchor: int | None = None,
    ) -> None:
        bar = self.chat_log.verticalScrollBar()
        previous_value = bar.value()

        self.chat_log.setHtml(render_chat_document(self._messages))

        if scroll_anchor is not None:
            bar.setValue(min(scroll_anchor, bar.maximum()))
        elif preserve_scroll:
            bar.setValue(min(previous_value, bar.maximum()))
        else:
            self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)

    def _scroll_to_streaming_message_start(self) -> None:
        config = load_config()
        label_text = f"{tr('chat.label.gemini', config=config)}:"
        cursor = QTextCursor(self.chat_log.document())
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        last_match: QTextCursor | None = None
        while True:
            found = self.chat_log.document().find(label_text, cursor)
            if found.isNull() or found.position() == cursor.position():
                break
            last_match = found
            cursor = QTextCursor(found)
            cursor.setPosition(found.selectionEnd())

        if last_match is not None and not last_match.isNull():
            self.chat_log.setTextCursor(last_match)
            self.chat_log.ensureCursorVisible()

    def _add_message(self, message: ChatMessage) -> None:
        self._messages.append(message)
        self._render_chat_log(preserve_scroll=False)

    def _add_system_message(
        self,
        text: str,
        *,
        kind: str = "system",
        label: str | None = None,
    ) -> None:
        if label is None:
            label = tr("chat.label.system")
        label_class = {
            "gemini": "chat-label-gemini",
            "system": "chat-label-system",
            "error": "chat-label-error",
        }.get(kind, "chat-label-system")
        safe = html.escape(text)
        self._add_message(
            ChatMessage(
                label_class=label_class,
                label=label,
                body_html=safe,
                trailing_spacer=True,
            )
        )

    def _on_anchor_clicked(self, url: QUrl) -> None:
        url_str = url.toString()
        if not url_str.startswith("copy:"):
            return
        block_id = url_str[5:]
        content = self._copy_blocks.get(block_id)
        if content is None:
            return
        QApplication.clipboard().setText(content)
        tooltip(tr("chat.copied"))

    def eventFilter(self, obj, event):
        if obj is self.input_field and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    return super().eventFilter(obj, event)
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def clear_conversation(self) -> None:
        if self._request_in_flight:
            self._request_token += 1
            self._restorable_user_text = ""
            self._cancel_in_flight_request()
        config = load_config()
        self.api_history.clear()
        self.note_context = None
        self._imported_fields = []
        self._imported_card_templates = []
        self._imported_notetype_css = ""
        self._imported_notetype_id = None
        self._context_wrapper_template = None
        self._messages.clear()
        self._copy_blocks.clear()
        self._stream_visible = False
        self._streaming_message_index = None
        self.context_checkbox.setChecked(False)
        self.context_checkbox.setEnabled(False)
        self.edit_wrapper_checkbox.setChecked(False)
        self.edit_wrapper_checkbox.setEnabled(False)
        self._wrapper_panel.setVisible(False)
        self.edit_templates_checkbox.setChecked(False)
        self.edit_templates_checkbox.setEnabled(False)
        self.templates_edit_panel.clear()
        self.note_preview_panel.clear()
        self._close_note_preview_window()
        self.btn_note_preview.setEnabled(False)
        self._add_system_message(
            tr("chat.cleared", config=config),
            kind="system",
            label=tr("chat.label.system", config=config),
        )
        self._capture_session_config()

    def import_note_from_editor(self, editor) -> None:
        config = load_config()
        note = editor.note
        imported_fields: list[tuple[str, str]] = []

        for name, value in note.items():
            if not value.strip():
                continue
            imported_fields.append((name, value))

        if not imported_fields:
            self._add_system_message(
                tr("chat.note_empty", config=config),
                kind="error",
                label=tr("chat.label.system", config=config),
            )
            return

        self._imported_fields = imported_fields
        self._imported_notetype_id = note.mid
        raw_templates, raw_css = extract_notetype_context(note)
        import_templates = bool(config.get("brain_import_templates", False))
        import_css = bool(config.get("brain_import_css", False))
        self._imported_card_templates = raw_templates if import_templates else []
        self._imported_notetype_css = raw_css if import_css else ""
        self.note_context = _format_note_context(imported_fields, config)
        self._context_wrapper_template = None
        self.context_checkbox.setEnabled(True)
        self.context_checkbox.setChecked(True)
        self.edit_wrapper_checkbox.setEnabled(True)
        self._collapse_wrapper_panel()
        self._refresh_import_controls(config)
        if import_templates and raw_templates:
            self.templates_edit_panel.set_templates(
                raw_templates,
                styling=raw_css if import_css else "",
                include_styling=import_css,
            )
        elif import_css and raw_css.strip():
            self.templates_edit_panel.set_styling_only(raw_css)
        else:
            self.templates_edit_panel.clear()
        self._add_system_message(
            tr("chat.note_imported", config=config),
            kind="system",
            label=tr("chat.label.system", config=config),
        )

        self.note_preview_panel.set_fields(imported_fields)
        self.btn_note_preview.setEnabled(True)

        self.input_field.setPlainText(effective_brain_import_message(config))
        self.input_field.setFocus()

    def _refresh_import_controls(self, config: dict[str, Any]) -> None:
        import_templates = bool(config.get("brain_import_templates", False))
        import_css = bool(config.get("brain_import_css", False))
        can_edit_templates = (import_templates and bool(self._imported_card_templates)) or (
            import_css and bool(self._imported_notetype_css.strip())
        )
        self.edit_templates_checkbox.setEnabled(can_edit_templates)
        if not can_edit_templates:
            self._collapse_templates_panel()
            self.templates_edit_panel.clear()
        self._update_wrapper_static_texts(config)

    def _update_wrapper_static_texts(self, config: dict[str, Any]) -> None:
        self.context_edit_wrapper_label.setText(
            strong_label_html(chat_edit_wrapper_label_text(config))
        )
        self.context_edit_wrapper_hint.setText(
            muted_hint_html(chat_edit_wrapper_hint_text(config))
        )
        self.templates_edit_panel.apply_language(config)
        self._update_wrapper_format_warning()

    def _sync_note_context_from_preview(self) -> None:
        if not self._imported_fields and not self.note_preview_panel.get_fields():
            return
        config = load_config()
        self._imported_fields = self.note_preview_panel.get_fields()
        non_empty = [(name, value) for name, value in self._imported_fields if value.strip()]
        if not non_empty:
            self.note_context = None
            return
        self.note_context = _format_note_context(non_empty, config)

    def _sync_templates_from_panel(self) -> None:
        if not self.templates_edit_panel.has_editable_sections():
            return
        self._imported_card_templates = self.templates_edit_panel.get_templates()
        self._imported_notetype_css = self.templates_edit_panel.get_styling()

    def _session_wrapper_for_send(self, config: dict[str, Any]) -> str | None:
        if self._context_wrapper_template is not None:
            raw = self._context_wrapper_template.strip()
            if is_builtin_chat_context_wrapper(raw):
                return None
            return raw
        stored = effective_chat_context_wrapper(config).strip()
        if is_builtin_chat_context_wrapper(stored):
            return None
        return stored

    def _wrapper_warning_sections(self, text: str, config: dict[str, Any]) -> list[str]:
        sections: list[str] = []
        if chat_context_wrapper_missing_placeholders(text):
            sections.append("required")
        sections.extend(wrapper_missing_import_placeholders(text, config))
        return sections

    def _build_outgoing_payload(self, config: dict[str, Any], user_text: str) -> str:
        payload_text = user_text
        if self.context_checkbox.isChecked() and self.note_context:
            self._sync_note_context_from_preview()
            self._sync_templates_from_panel()
            session_template = self._session_wrapper_for_send(config)
            payload_text = format_chat_context_message(
                config,
                context=self.note_context,
                request=user_text,
                templates=self._templates_for_message(config),
                styling=self._styling_for_message(config),
                template=session_template,
            )
        return payload_text

    def _confirm_large_chat_payload(self, config: dict[str, Any], token_count: int) -> bool:
        threshold = int(config.get("chat_token_warning_threshold", 3000))
        if token_count <= threshold:
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr("chat.large_payload.title", config=config))
        box.setText(
            tr(
                "chat.large_payload.message",
                config=config,
                count=token_count,
                threshold=threshold,
            )
        )
        box.setInformativeText(tr("chat.large_payload.detail", config=config, threshold=threshold))
        box.setStandardButtons(
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        return box.exec() == QMessageBox.StandardButton.Ok

    def _templates_for_message(self, config: dict[str, Any]) -> str:
        if not config.get("brain_import_templates", False):
            return ""
        if not self._imported_card_templates:
            return ""
        return format_card_templates_block(self._imported_card_templates, config)

    def _styling_for_message(self, config: dict[str, Any]) -> str:
        if not config.get("brain_import_css", False):
            return ""
        return self._imported_notetype_css.strip()

    def _on_edit_templates_toggled(self, checked: bool) -> None:
        if checked:
            self._sync_templates_from_panel()
            self.templates_edit_panel.setVisible(True)
            return
        self._sync_templates_from_panel()
        self.templates_edit_panel.setVisible(False)

    def _collapse_templates_panel(self) -> None:
        if not self.edit_templates_checkbox.isChecked():
            return
        self.edit_templates_checkbox.setChecked(False)

    def _on_edit_wrapper_toggled(self, checked: bool) -> None:
        if checked:
            self._sync_note_context_from_preview()
            self._wrapper_warning_dismissed.clear()
            self._populate_wrapper_editor()
            self._wrapper_panel.setVisible(True)
            self.context_edit_wrapper_input.setFocus()
            return
        wrapper_text = self.context_edit_wrapper_input.toPlainText()
        self._context_wrapper_template = wrapper_text if wrapper_text.strip() else None
        self._wrapper_panel.setVisible(False)

    def _collapse_wrapper_panel(self) -> None:
        if not self.edit_wrapper_checkbox.isChecked():
            return
        self.edit_wrapper_checkbox.setChecked(False)

    def _populate_wrapper_editor(self) -> None:
        config = load_config()
        templates_content = self._templates_for_message(config)
        styling_content = self._styling_for_message(config)
        self.context_edit_wrapper_input.blockSignals(True)
        if self._context_wrapper_template is not None:
            raw = self._context_wrapper_template.strip()
            if wrapper_has_conditional_blocks(raw):
                wrapper = chat_context_wrapper_for_session(
                    config,
                    template_override=raw,
                    templates_content=templates_content,
                    styling_content=styling_content,
                )
            else:
                wrapper = raw
        else:
            wrapper = chat_context_wrapper_for_session(
                config,
                templates_content=templates_content,
                styling_content=styling_content,
            )
        self.context_edit_wrapper_input.setPlainText(wrapper)
        self.context_edit_wrapper_input.blockSignals(False)
        self._update_wrapper_format_warning()

    def _update_wrapper_format_warning(self) -> None:
        if not self.edit_wrapper_checkbox.isChecked():
            self.context_edit_wrapper_warning_banner.setVisible(False)
            return
        config = load_config()
        text = self.context_edit_wrapper_input.toPlainText()
        sections = [
            section
            for section in self._wrapper_warning_sections(text, config)
            if section not in self._wrapper_warning_dismissed
        ]
        if not sections:
            self.context_edit_wrapper_warning_banner.setVisible(False)
            return
        self.context_edit_wrapper_warning.setText(
            wrapper_import_warning_text(config, sections=sections, scope="chat")
        )
        self.context_edit_wrapper_warning_banner.setVisible(True)

    def _dismiss_wrapper_warning_banner(self) -> None:
        config = load_config()
        text = self.context_edit_wrapper_input.toPlainText()
        self._wrapper_warning_dismissed.update(self._wrapper_warning_sections(text, config))
        self._update_wrapper_format_warning()

    def _on_context_edit_wrapper_changed(self) -> None:
        if not self.edit_wrapper_checkbox.isChecked():
            return
        self._context_wrapper_template = self.context_edit_wrapper_input.toPlainText()
        self._wrapper_warning_dismissed.clear()
        self._update_wrapper_format_warning()

    def _on_send_button_clicked(self) -> None:
        if self._request_in_flight:
            self._cancel_in_flight_request()
            return
        self.send_message()

    def _register_active_response(self, response) -> None:
        self._active_response = response

    def _cancel_in_flight_request(self) -> None:
        if not self._request_in_flight:
            return
        self._cancel_event.set()
        if self._active_response is not None:
            try:
                self._active_response.close()
            except Exception:
                pass
            self._active_response = None
        self._start_stopping()
        self.send_button.setEnabled(False)

    def _begin_request(self) -> None:
        self._request_in_flight = True
        self._cancel_event.clear()
        config = load_config()
        self.send_button.setText(tr("chat.stop", config=config))
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(False)
        self.btn_clear.setEnabled(False)

    def _end_request(self) -> None:
        self._request_in_flight = False
        self._cancel_event.clear()
        self._active_response = None
        config = load_config()
        self.send_button.setText(tr("chat.send", config=config))
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self._configure_chat_default_buttons()

    def send_message(self) -> None:
        if self._request_in_flight:
            return

        user_text = self.input_field.toPlainText().strip()
        if not user_text:
            return

        config = load_config()
        included_context = bool(self.context_checkbox.isChecked() and self.note_context)
        payload_text = self._build_outgoing_payload(config, user_text)
        max_turns = int(config.get("max_history_turns", 20))
        history_for_request = trim_history(self.api_history, max_turns)
        system_instruction = merge_system_instructions(
            config,
            include_meta_rule=True,
            purpose="chat",
        )
        token_count = estimate_chat_request_tokens(
            payload_text,
            history_for_request,
            system_instruction=system_instruction,
        )
        if not self._confirm_large_chat_payload(config, token_count):
            return

        safe_html = html.escape(user_text).replace("\n", "<br>")
        you_label = tr("chat.label.you", config=config)
        self._add_message(
            ChatMessage(
                label_class="chat-label-you",
                label=you_label,
                body_html=safe_html,
            )
        )
        self._restorable_user_text = user_text
        self.input_field.clear()
        self._begin_request()
        self._collapse_wrapper_panel()
        self._collapse_templates_panel()

        if not api_key_configured(config):
            self._add_system_message(
                tr("chat.api_key_missing", config=config),
                kind="error",
                label=tr("chat.label.system", config=config),
            )
            self._end_request()
            return

        if included_context:
            self.context_edit_wrapper_warning_banner.setVisible(False)
            self.context_checkbox.setChecked(False)

        self.api_history.append({"role": "user", "parts": [{"text": payload_text}]})
        history_for_request = trim_history(self.api_history[:-1], max_turns)
        temperature = float(config.get("temperature_chat", 0.2))
        use_streaming = bool(config.get("chat_streaming", False))
        cancel_check = self._cancel_event.is_set
        register_response = self._register_active_response
        self._request_token += 1
        request_token = self._request_token
        request_kwargs = {
            "config": config,
            "user_text": payload_text,
            "history": history_for_request,
            "temperature": temperature,
            "include_meta_rule": True,
            "should_cancel": cancel_check,
            "register_response": register_response,
        }

        if use_streaming:
            self._stream_visible = False
            self._start_loading()
            mw.taskman.run_in_background(
                lambda: stream_gemini(
                    **request_kwargs,
                    on_chunk=lambda text: mw.taskman.run_on_main(
                        lambda accumulated=text: self._handle_stream_chunk_safe(accumulated)
                    ),
                ),
                lambda future, token=request_token: self._handle_response(future, token),
            )
            return

        self._start_loading()

        mw.taskman.run_in_background(
            lambda: call_gemini(
                **request_kwargs,
                purpose="chat",
            ),
            lambda future, token=request_token: self._handle_response(future, token),
        )

    def _handle_stream_chunk_safe(self, accumulated: str) -> None:
        if self._closing or self._cancel_event.is_set():
            return
        self._handle_stream_chunk(accumulated)

    def _handle_stream_chunk(self, accumulated: str) -> None:
        if not accumulated:
            return
        if not self._stream_visible:
            self._stop_loading()
            self._begin_streaming_reply()
            self._stream_visible = True
        self._update_streaming_reply(accumulated)

    def _begin_streaming_reply(self) -> None:
        config = load_config()
        gemini_label = tr("chat.label.gemini", config=config)
        self._messages.append(
            ChatMessage(
                label_class="chat-label-gemini",
                label=gemini_label,
                body_html="",
            )
        )
        self._streaming_message_index = len(self._messages) - 1
        self._render_chat_log()
        self._scroll_to_streaming_message_start()

    def _update_streaming_reply(self, text: str) -> None:
        if self._streaming_message_index is None:
            return
        config = load_config()
        stream_id = f"r{self._copy_counter + 1}"
        reply_html = format_streaming_reply_html(
            text,
            self._copy_blocks,
            stream_id,
            config=config,
        )
        message = self._messages[self._streaming_message_index]
        message.body_html = f"<br>{reply_html}" if reply_html else ""
        self._render_chat_log(preserve_scroll=True)

    def _clear_streaming_reply(self) -> None:
        if self._streaming_message_index is None:
            return
        index = self._streaming_message_index
        self._streaming_message_index = None
        if 0 <= index < len(self._messages):
            self._messages.pop(index)
        self._render_chat_log(preserve_scroll=False)

    def _finalize_successful_reply(self, raw_text: str) -> None:
        if self._closing:
            return
        config = load_config()
        display_text, dynamic_rules = extract_dynamic_rules(raw_text)
        rules_updated = False

        if dynamic_rules is not None:
            config["dynamic_instructions"] = dynamic_rules
            save_config(config)
            rules_updated = True

        self.api_history.append({"role": "model", "parts": [{"text": display_text}]})

        self._copy_counter += 1
        reply_html = format_gemini_reply_html(
            display_text,
            self._copy_blocks,
            f"r{self._copy_counter}",
            config=config,
            endcap=False,
        )

        gemini_label = tr("chat.label.gemini", config=config)
        was_streaming = self._streaming_message_index is not None
        if self._streaming_message_index is not None:
            message = self._messages[self._streaming_message_index]
            message.label = gemini_label
            message.body_html = f"<br>{reply_html}" if reply_html else ""
            self._streaming_message_index = None
        else:
            body = f"<br>{reply_html}" if reply_html else ""
            self._messages.append(
                ChatMessage(
                    label_class="chat-label-gemini",
                    label=gemini_label,
                    body_html=body,
                )
            )

        if rules_updated:
            self._messages.append(
                ChatMessage(
                    label_class="chat-label-system",
                    label=tr("chat.label.system", config=config),
                    body_html=html.escape(tr("chat.rules_updated", config=config)),
                    trailing_spacer=True,
                )
            )

        self._render_chat_log(preserve_scroll=True)
        if not was_streaming:
            self._scroll_to_streaming_message_start()

    def _remove_last_user_message(self) -> None:
        for index in range(len(self._messages) - 1, -1, -1):
            if self._messages[index].label_class == "chat-label-you":
                self._messages.pop(index)
                return

    def _handle_reply_cancelled(self) -> None:
        if self._closing:
            return
        config = load_config()
        if self.api_history and self.api_history[-1]["role"] == "user":
            self.api_history.pop()

        if self._streaming_message_index is not None:
            self._clear_streaming_reply()
        self._stream_visible = False
        self._remove_last_user_message()

        if self._restorable_user_text:
            self.input_field.setPlainText(self._restorable_user_text)
        self._restorable_user_text = ""

        self._add_system_message(
            tr("chat.stopped", config=config),
            kind="system",
            label=tr("chat.label.system", config=config),
        )
        self._render_chat_log(preserve_scroll=False)
        self.input_field.setFocus()

    def _handle_reply_error(self, exc: Exception) -> None:
        if self._closing:
            return
        config = load_config()
        if self.api_history and self.api_history[-1]["role"] == "user":
            self.api_history.pop()

        if self._streaming_message_index is not None:
            self._clear_streaming_reply()
        self._stream_visible = False

        if isinstance(exc, (GeminiRateLimitError, GeminiAuthError)):
            message = str(exc)
        elif isinstance(exc, GeminiError):
            message = tr("chat.error", config=config, error=exc)
        else:
            message = tr("chat.unexpected_error", config=config, error=exc)

        self._add_system_message(
            message,
            kind="error",
            label=tr("chat.label.system", config=config),
        )

    def _handle_response(self, future, request_token: int) -> None:
        if self._closing or request_token != self._request_token:
            self._stop_loading()
            self._end_request()
            return
        self._stop_loading()
        cancelled = self._cancel_event.is_set()

        try:
            raw_text = future.result()
            if cancelled:
                self._handle_reply_cancelled()
            else:
                self._finalize_successful_reply(raw_text)
        except GeminiCancelledError:
            self._handle_reply_cancelled()
        except Exception as exc:
            if cancelled:
                self._handle_reply_cancelled()
            else:
                self._handle_reply_error(exc)
        finally:
            self._end_request()
            if not self._closing:
                self.input_field.setFocus()

    def _set_input_enabled(self, enabled: bool) -> None:
        self.input_field.setEnabled(enabled)
        if not self._request_in_flight:
            self.send_button.setEnabled(enabled)

    def _start_loading(self) -> None:
        self._loading_mode = "typing"
        self._loading_phase = 0
        self.loading_label.setVisible(True)
        self._update_loading_animation()
        self.loading_timer.start(400)

    def _start_stopping(self) -> None:
        self._loading_mode = "stopping"
        self._loading_phase = 0
        self.loading_label.setVisible(True)
        self._update_loading_animation()
        if not self.loading_timer.isActive():
            self.loading_timer.start(400)

    def _stop_loading(self) -> None:
        self.loading_timer.stop()
        self.loading_label.setVisible(False)
        self._loading_mode = None

    def _loading_base_text(self) -> str:
        if self._loading_mode == "stopping":
            return tr("chat.stopping")
        return tr("chat.loading")

    def _update_loading_animation(self) -> None:
        self._loading_phase = (self._loading_phase % 3) + 1
        dots = "." * self._loading_phase
        self.loading_label.setText(f"{self._loading_base_text()}{dots}")


_chat_window: ChatWindow | None = None


def refresh_chat_language() -> None:
    if _chat_window is not None:
        _chat_window.apply_language()


def refresh_chat_from_settings() -> None:
    if _chat_window is not None:
        _chat_window.apply_settings_refresh()


def refresh_chat_theme() -> None:
    if _chat_window is not None:
        _chat_window.apply_theme()


def get_chat_window() -> ChatWindow:
    global _chat_window
    if _chat_window is None:
        _chat_window = ChatWindow()
    return _chat_window


def open_chat(editor=None, analyze: bool = False) -> None:
    window = get_chat_window()
    window.show()
    window.raise_()
    window.activateWindow()
    window._focus_chat_input()
    if analyze and editor:
        window.import_note_from_editor(editor)


def close_chat_window(*, force: bool = False) -> None:
    global _chat_window
    if _chat_window is None:
        return
    if force:
        _chat_window.prepare_shutdown()
    _chat_window.close()
    _chat_window = None
