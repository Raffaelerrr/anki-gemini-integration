from __future__ import annotations

import html
import re
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
    QTextCursor,
    QTextEdit,
    Qt,
    QTimer,
    QUrl,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import tooltip

from ..config import api_key_configured, load_config, save_config
from ..i18n import effective_brain_import_message, tr
from ..gemini_client import (
    GeminiError,
    call_gemini,
    extract_dynamic_rules,
    stream_gemini,
    trim_history,
)
from .chat_formatter import format_gemini_reply_html
from .theme import chat_document_stylesheet, loading_label_stylesheet

_TRAILING_EMPTY_HTML = re.compile(
    r"(?:"
    r"\s|"
    r"<br\s*/?>|"
    r"<p>\s*(?:<br\s*/?>)?\s*</p>|"
    r"<div>\s*(?:<br\s*/?>)?\s*</div>"
    r")+$",
    re.IGNORECASE,
)

_LEADING_EMPTY_HTML = re.compile(
    r"^(?:"
    r"\s|"
    r"<br\s*/?>|"
    r"<p>\s*(?:<br\s*/?>|&nbsp;|\u00a0|\s)*</p>|"
    r"<div>\s*(?:<br\s*/?>|&nbsp;|\u00a0|\s)*</div>"
    r")+",
    re.IGNORECASE,
)


def _strip_field_html_edges(value: str) -> str:
    cleaned = value.strip()
    while True:
        new = _LEADING_EMPTY_HTML.sub("", cleaned, count=1)
        if new == cleaned:
            break
        cleaned = new.strip()
    cleaned = re.sub(r"^(<br\s*/?>|<div>\s*<br\s*/?>\s*</div>|<p>\s*</p>)+", "", cleaned)
    cleaned = _TRAILING_EMPTY_HTML.sub("", cleaned)
    return cleaned.strip()


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
        self.resize(520, 640)

        self.api_history: list[dict[str, Any]] = []
        self.note_context: str | None = None
        self._loading_phase = 0
        self._copy_blocks: dict[str, str] = {}
        self._copy_counter = 0
        self._stream_block_start: int | None = None

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.context_checkbox = QCheckBox(self)
        self.context_checkbox.setChecked(False)
        toolbar.addWidget(self.context_checkbox)

        self.btn_clear = QPushButton(self)
        self.btn_clear.clicked.connect(self.clear_conversation)
        toolbar.addWidget(self.btn_clear)
        layout.addLayout(toolbar)

        self.chat_log = QTextBrowser(self)
        self.chat_log.setOpenLinks(False)
        self.chat_log.setReadOnly(True)
        self.chat_log.anchorClicked.connect(self._on_anchor_clicked)
        layout.addWidget(self.chat_log)

        self.loading_label = QLabel("", self)
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        input_layout = QHBoxLayout()
        self.input_field = QTextEdit(self)
        self.input_field.setFixedHeight(80)
        self.input_field.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.input_field.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.input_field.installEventFilter(self)

        self.send_button = QPushButton(self)
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedHeight(80)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)

        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self._update_loading_animation)

        self._apply_chat_theme()
        self._apply_static_texts()
        self._append_system_message(
            tr("chat.welcome"),
            kind="gemini",
            label=tr("chat.label.gemini"),
        )

    def _apply_chat_theme(self) -> None:
        self.chat_log.document().setDefaultStyleSheet(chat_document_stylesheet())
        self.loading_label.setStyleSheet(loading_label_stylesheet())

    def _apply_static_texts(self) -> None:
        config = load_config()
        self.setWindowTitle(tr("chat.title", config=config))
        self.context_checkbox.setText(tr("chat.include_context", config=config))
        self.btn_clear.setText(tr("chat.new_conversation", config=config))
        self.chat_log.setPlaceholderText(tr("chat.log_placeholder", config=config))
        self.input_field.setPlaceholderText(tr("chat.input_placeholder", config=config))
        self.send_button.setText(tr("chat.send", config=config))
        if self.loading_label.isVisible():
            self._update_loading_animation()

    def apply_theme(self) -> None:
        self._apply_chat_theme()

    def apply_language(self) -> None:
        self._apply_static_texts()

    def closeEvent(self, event: QCloseEvent) -> None:
        global _chat_window
        _chat_window = None
        super().closeEvent(event)

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
        self._copy_blocks.clear()
        self.context_checkbox.setChecked(False)
        self.chat_log.clear()
        self._append_system_message(
            tr("chat.cleared", config=config),
            kind="system",
            label=tr("chat.label.system", config=config),
        )

    def import_note_from_editor(self, editor) -> None:
        config = load_config()
        note = editor.note
        field_blocks: list[str] = []
        context_lines: list[str] = []

        for name, value in note.items():
            if not value.strip():
                continue
            cleaned = _strip_field_html_edges(value)
            inner = cleaned if cleaned.startswith("<") else html.escape(cleaned)
            field_blocks.append(
                f"<div class='chat-field-block'>"
                f"<div class='chat-field-title'>{html.escape(name)}:</div>"
                f"<div class='chat-field-content'>{inner}</div>"
                f"</div>"
            )
            context_lines.append(f"{tr('chat.context.field', config=config, name=name)}\n{value}")

        if not field_blocks:
            self._append_system_message(
                tr("chat.note_empty", config=config),
                kind="error",
                label=tr("chat.label.system", config=config),
            )
            return

        self.note_context = "\n\n".join(context_lines)
        self.context_checkbox.setChecked(True)
        self._append_system_message(
            tr("chat.note_imported", config=config),
            kind="system",
            label=tr("chat.label.system", config=config),
        )

        preview_html = "<div class='chat-preview-panel'>" + "".join(field_blocks) + "</div>"
        self.chat_log.append(preview_html)
        self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)

        self.input_field.setPlainText(effective_brain_import_message(config))
        self.input_field.setFocus()

    def send_message(self) -> None:
        user_text = self.input_field.toPlainText().strip()
        if not user_text:
            return

        config = load_config()
        safe_html = html.escape(user_text).replace("\n", "<br>")
        you_label = tr("chat.label.you", config=config)
        self.chat_log.append(f"<br><b class='chat-label-you'>{you_label}:</b> {safe_html}")
        self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)
        self.input_field.clear()
        self._set_input_enabled(False)

        if not api_key_configured(config):
            self._append_system_message(
                tr("chat.api_key_missing", config=config),
                kind="error",
                label=tr("chat.label.system", config=config),
            )
            self._set_input_enabled(True)
            return

        payload_text = user_text
        if self.context_checkbox.isChecked() and self.note_context:
            payload_text = tr(
                "chat.context.prefix",
                config=config,
                context=self.note_context,
                request=user_text,
            )
            self.context_checkbox.setChecked(False)

        self.api_history.append({"role": "user", "parts": [{"text": payload_text}]})
        max_turns = int(config.get("max_history_turns", 20))
        history_for_request = trim_history(self.api_history[:-1], max_turns)
        temperature = float(config.get("temperature_chat", 0.2))
        use_streaming = bool(config.get("chat_streaming", False))

        if use_streaming:
            self._begin_streaming_reply()
            mw.taskman.run_in_background(
                lambda: stream_gemini(
                    config=config,
                    user_text=payload_text,
                    history=history_for_request,
                    temperature=temperature,
                    include_meta_rule=True,
                    on_chunk=lambda text: mw.taskman.run_on_main(
                        lambda accumulated=text: self._update_streaming_reply(accumulated)
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

    def _begin_streaming_reply(self) -> None:
        config = load_config()
        gemini_label = tr("chat.label.gemini", config=config)
        self.chat_log.append(f"<br><b class='chat-label-gemini'>{gemini_label}:</b><br>")
        self._stream_block_start = self.chat_log.textCursor().position()
        self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)

    def _update_streaming_reply(self, text: str) -> None:
        if self._stream_block_start is None:
            return
        cursor = self.chat_log.textCursor()
        cursor.setPosition(self._stream_block_start)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        safe = html.escape(text).replace("\n", "<br>")
        cursor.insertHtml(f"<span class='chat-stream-text'>{safe}</span>")
        self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)

    def _clear_streaming_reply(self) -> None:
        if self._stream_block_start is None:
            return
        cursor = self.chat_log.textCursor()
        cursor.setPosition(self._stream_block_start)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        self._stream_block_start = None

    def _finalize_successful_reply(self, raw_text: str) -> None:
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
        )

        if self._stream_block_start is not None:
            cursor = self.chat_log.textCursor()
            cursor.setPosition(self._stream_block_start)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertHtml(reply_html)
            self._stream_block_start = None
        else:
            gemini_label = tr("chat.label.gemini", config=config)
            self.chat_log.append(f"<br><b class='chat-label-gemini'>{gemini_label}:</b><br>{reply_html}")

        if rules_updated:
            self._append_system_message(
                tr("chat.rules_updated", config=config),
                kind="system",
                label=tr("chat.label.system", config=config),
            )

    def _handle_reply_error(self, exc: Exception) -> None:
        config = load_config()
        if self.api_history and self.api_history[-1]["role"] == "user":
            self.api_history.pop()

        if self._stream_block_start is not None:
            self._clear_streaming_reply()
            self._stream_block_start = None

        if isinstance(exc, GeminiError):
            message = tr("chat.error", config=config, error=exc)
        else:
            message = tr("chat.unexpected_error", config=config, error=exc)

        self._append_system_message(
            message,
            kind="error",
            label=tr("chat.label.system", config=config),
        )

    def _handle_response(self, future) -> None:
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

    def _append_system_message(
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
        self.chat_log.append(
            f"<br><b class='{label_class}'>{label}:</b> {safe}"
            f"<div style='margin-bottom: 10px;'></div>"
        )
        self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)


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


def close_chat_window() -> None:
    global _chat_window
    if _chat_window is not None:
        _chat_window.close()
        _chat_window = None
