from __future__ import annotations

import html
from typing import Any

from aqt import mw
from aqt.qt import (
    QApplication,
    QCheckBox,
    QCloseEvent,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    Qt,
    QTimer,
    QUrl,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import tooltip

from ..config import api_key_configured, load_config, save_config
from ..i18n import (
    chat_context_wrapper_missing_placeholders,
    effective_brain_import_message,
    effective_chat_context_wrapper,
    format_chat_context_message,
    tr,
)
from ..gemini_client import (
    GeminiError,
    call_gemini,
    extract_dynamic_rules,
    stream_gemini,
    trim_history,
)
from .chat_formatter import format_gemini_reply_html
from .chat_log_renderer import render_chat_document
from .chat_messages import ChatMessage
from .note_preview_panel import NotePreviewPanel
from .settings_compact_controls import create_ui_text_edit
from .theme import (
    chat_document_stylesheet,
    loading_label_stylesheet,
    muted_hint_html,
    refresh_native_text_edits_in,
    strong_label_html,
    wrapper_warning_stylesheet,
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
        self._context_wrapper_template: str | None = None
        self._messages: list[ChatMessage] = []
        self._loading_phase = 0
        self._copy_blocks: dict[str, str] = {}
        self._copy_counter = 0
        self._streaming_message_index: int | None = None
        self._stream_visible = False
        self._closing = False

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.context_checkbox = QCheckBox(self)
        self.context_checkbox.setChecked(False)
        toolbar.addWidget(self.context_checkbox)

        self.edit_wrapper_checkbox = QCheckBox(self)
        self.edit_wrapper_checkbox.setChecked(False)
        self.edit_wrapper_checkbox.setEnabled(False)
        self.edit_wrapper_checkbox.toggled.connect(self._on_edit_wrapper_toggled)
        toolbar.addWidget(self.edit_wrapper_checkbox)

        self.btn_clear = QPushButton(self)
        self.btn_clear.clicked.connect(self.clear_conversation)
        toolbar.addWidget(self.btn_clear)
        layout.addLayout(toolbar)

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
        self.context_edit_wrapper_warning = QLabel(self._wrapper_panel)
        self.context_edit_wrapper_warning.setVisible(False)
        self.context_edit_wrapper_warning.setWordWrap(True)
        wrapper_header.addWidget(self.context_edit_wrapper_warning)
        panel_layout.addLayout(wrapper_header)
        self.context_edit_wrapper_hint = QLabel(self._wrapper_panel)
        panel_layout.addWidget(self.context_edit_wrapper_hint)
        wrapper_shell, self.context_edit_wrapper_input = create_ui_text_edit(
            self._wrapper_panel,
        )
        self.context_edit_wrapper_input.setMinimumHeight(70)
        bind_text_edit_auto_height(self.context_edit_wrapper_input, minimum=70, maximum=110)
        self.context_edit_wrapper_input.textChanged.connect(self._on_context_edit_wrapper_changed)
        panel_layout.addWidget(wrapper_shell)
        self._wrapper_panel.setVisible(False)
        layout.addWidget(self._wrapper_panel, 0)

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
        self.input_field.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.input_field.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.input_field.installEventFilter(self)

        self.send_button = QPushButton(self)
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedHeight(80)

        input_layout.addWidget(input_shell)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)

        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self._update_loading_animation)

        self._apply_chat_theme()
        self._apply_static_texts()
        self._add_system_message(
            tr("chat.welcome"),
            kind="gemini",
            label=tr("chat.label.gemini"),
        )

    def _apply_chat_theme(self) -> None:
        self.chat_log.document().setDefaultStyleSheet(chat_document_stylesheet())
        self.loading_label.setStyleSheet(loading_label_stylesheet())
        self.context_edit_wrapper_warning.setStyleSheet(wrapper_warning_stylesheet())
        self.note_preview_panel.apply_theme()
        refresh_native_text_edits_in(self)
        self._render_chat_log(preserve_scroll=False)

    def _apply_static_texts(self) -> None:
        config = load_config()
        self.setWindowTitle(tr("chat.title", config=config))
        self.context_checkbox.setText(tr("chat.include_context", config=config))
        self.edit_wrapper_checkbox.setText(tr("chat.edit_wrapper", config=config))
        self.context_edit_wrapper_label.setText(
            strong_label_html(tr("chat.edit_wrapper.wrapper_label", config=config))
        )
        self.context_edit_wrapper_hint.setText(
            muted_hint_html(tr("chat.edit_wrapper.wrapper_hint", config=config))
        )
        self.context_edit_wrapper_warning.setText(
            tr("chat.edit_wrapper.wrapper_invalid", config=config)
        )
        self._update_wrapper_format_warning()
        self.note_preview_panel.apply_language(config)
        self.btn_clear.setText(tr("chat.new_conversation", config=config))
        self.chat_log.setPlaceholderText(tr("chat.log_placeholder", config=config))
        self.input_field.setPlaceholderText(tr("chat.input_placeholder", config=config))
        self.send_button.setText(tr("chat.send", config=config))
        if self.loading_label.isVisible():
            self._update_loading_animation()

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
        self._stop_loading()
        _chat_window = None
        super().closeEvent(event)

    def prepare_shutdown(self) -> None:
        self._closing = True
        self._stop_loading()
        self._stream_visible = False
        self._streaming_message_index = None

    def _render_chat_log(self, *, preserve_scroll: bool) -> None:
        bar = self.chat_log.verticalScrollBar()
        previous_value = bar.value()
        at_bottom = bar.value() >= bar.maximum() - 8

        self.chat_log.setHtml(render_chat_document(self._messages))

        if preserve_scroll and not at_bottom:
            bar.setValue(min(previous_value, bar.maximum()))
        else:
            self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)

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
        config = load_config()
        self.api_history.clear()
        self.note_context = None
        self._imported_fields = []
        self._context_wrapper_template = None
        self._messages.clear()
        self._copy_blocks.clear()
        self._stream_visible = False
        self._streaming_message_index = None
        self.context_checkbox.setChecked(False)
        self.edit_wrapper_checkbox.setChecked(False)
        self.edit_wrapper_checkbox.setEnabled(False)
        self._wrapper_panel.setVisible(False)
        self.note_preview_panel.clear()
        self._add_system_message(
            tr("chat.cleared", config=config),
            kind="system",
            label=tr("chat.label.system", config=config),
        )

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
        self.note_context = _format_note_context(imported_fields, config)
        self._context_wrapper_template = None
        self.context_checkbox.setChecked(True)
        self.edit_wrapper_checkbox.setEnabled(True)
        self.edit_wrapper_checkbox.setChecked(False)
        self._wrapper_panel.setVisible(False)
        self._add_system_message(
            tr("chat.note_imported", config=config),
            kind="system",
            label=tr("chat.label.system", config=config),
        )

        self.note_preview_panel.set_fields(imported_fields)

        self.input_field.setPlainText(effective_brain_import_message(config))
        self.input_field.setFocus()

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

    def _on_edit_wrapper_toggled(self, checked: bool) -> None:
        if checked:
            self._sync_note_context_from_preview()
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
        self.context_edit_wrapper_input.blockSignals(True)
        wrapper = self._context_wrapper_template or effective_chat_context_wrapper(config)
        self.context_edit_wrapper_input.setPlainText(wrapper)
        self.context_edit_wrapper_input.blockSignals(False)
        self._update_wrapper_format_warning()

    def _update_wrapper_format_warning(self) -> None:
        if not self.edit_wrapper_checkbox.isChecked():
            self.context_edit_wrapper_warning.setVisible(False)
            return
        text = self.context_edit_wrapper_input.toPlainText()
        self.context_edit_wrapper_warning.setVisible(
            chat_context_wrapper_missing_placeholders(text)
        )

    def _on_context_edit_wrapper_changed(self) -> None:
        if not self.edit_wrapper_checkbox.isChecked():
            return
        self._context_wrapper_template = self.context_edit_wrapper_input.toPlainText()
        self._update_wrapper_format_warning()

    def send_message(self) -> None:
        user_text = self.input_field.toPlainText().strip()
        if not user_text:
            return

        config = load_config()
        safe_html = html.escape(user_text).replace("\n", "<br>")
        you_label = tr("chat.label.you", config=config)
        self._add_message(
            ChatMessage(
                label_class="chat-label-you",
                label=you_label,
                body_html=safe_html,
            )
        )
        self.input_field.clear()
        self._set_input_enabled(False)
        self._collapse_wrapper_panel()

        if not api_key_configured(config):
            self._add_system_message(
                tr("chat.api_key_missing", config=config),
                kind="error",
                label=tr("chat.label.system", config=config),
            )
            self._set_input_enabled(True)
            return

        payload_text = user_text
        if self.context_checkbox.isChecked() and self.note_context:
            self._sync_note_context_from_preview()
            payload_text = format_chat_context_message(
                config,
                context=self.note_context,
                request=user_text,
                template=self._context_wrapper_template,
            )
            self.context_edit_wrapper_warning.setVisible(False)
            self.context_checkbox.setChecked(False)

        self.api_history.append({"role": "user", "parts": [{"text": payload_text}]})
        max_turns = int(config.get("max_history_turns", 20))
        history_for_request = trim_history(self.api_history[:-1], max_turns)
        temperature = float(config.get("temperature_chat", 0.2))
        use_streaming = bool(config.get("chat_streaming", False))

        if use_streaming:
            self._stream_visible = False
            self._start_loading()
            mw.taskman.run_in_background(
                lambda: stream_gemini(
                    config=config,
                    user_text=payload_text,
                    history=history_for_request,
                    temperature=temperature,
                    include_meta_rule=True,
                    on_chunk=lambda text: mw.taskman.run_on_main(
                        lambda accumulated=text: self._handle_stream_chunk_safe(accumulated)
                    ),
                ),
                self._handle_response,
            )
            return

        self._start_loading()

        mw.taskman.run_in_background(
            lambda: call_gemini(
                config=config,
                user_text=payload_text,
                history=history_for_request,
                temperature=temperature,
                include_meta_rule=True,
                purpose="chat",
            ),
            self._handle_response,
        )

    def _handle_stream_chunk_safe(self, accumulated: str) -> None:
        if self._closing:
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
        self._render_chat_log(preserve_scroll=False)

    def _update_streaming_reply(self, text: str) -> None:
        if self._streaming_message_index is None:
            return
        safe = html.escape(text).replace("\n", "<br>")
        message = self._messages[self._streaming_message_index]
        message.body_html = f"<br><span class='chat-stream-text'>{safe}</span>"
        self._render_chat_log(preserve_scroll=True)

    def _clear_streaming_reply(self) -> None:
        if self._streaming_message_index is None:
            return
        self._messages.pop(self._streaming_message_index)
        self._streaming_message_index = None
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

        self._render_chat_log(preserve_scroll=False)

        if rules_updated:
            self._add_system_message(
                tr("chat.rules_updated", config=config),
                kind="system",
                label=tr("chat.label.system", config=config),
            )

    def _handle_reply_error(self, exc: Exception) -> None:
        if self._closing:
            return
        config = load_config()
        if self.api_history and self.api_history[-1]["role"] == "user":
            self.api_history.pop()

        if self._streaming_message_index is not None:
            self._clear_streaming_reply()
        self._stream_visible = False

        if isinstance(exc, GeminiError):
            message = tr("chat.error", config=config, error=exc)
        else:
            message = tr("chat.unexpected_error", config=config, error=exc)

        self._add_system_message(
            message,
            kind="error",
            label=tr("chat.label.system", config=config),
        )

    def _handle_response(self, future) -> None:
        if self._closing:
            return
        self._stop_loading()
        self._set_input_enabled(True)
        self.input_field.setFocus()

        try:
            raw_text = future.result()
            self._finalize_successful_reply(raw_text)
        except Exception as exc:
            self._handle_reply_error(exc)

        self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)

    def _set_input_enabled(self, enabled: bool) -> None:
        self.send_button.setEnabled(enabled)
        self.input_field.setEnabled(enabled)

    def _start_loading(self) -> None:
        self._loading_phase = 0
        self.loading_label.setText(tr("chat.loading"))
        self.loading_label.setVisible(True)
        self.loading_timer.start(400)

    def _stop_loading(self) -> None:
        self.loading_timer.stop()
        self.loading_label.setVisible(False)

    def _update_loading_animation(self) -> None:
        self._loading_phase = (self._loading_phase % 3) + 1
        dots = "." * self._loading_phase
        self.loading_label.setText(f"{tr('chat.loading')}{dots}")


_chat_window: ChatWindow | None = None


def refresh_chat_language() -> None:
    if _chat_window is not None:
        _chat_window.apply_language()


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
