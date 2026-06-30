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
    QTextEdit,
    Qt,
    QTimer,
    QUrl,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import tooltip

from ..config import api_key_configured, load_config, save_config
from ..constants import DEFAULT_BRAIN_IMPORT_MESSAGE
from ..gemini_client import (
    GeminiError,
    call_gemini,
    extract_dynamic_rules,
    trim_history,
)
from .chat_formatter import format_gemini_reply_html

PREVIEW_STYLE = (
    "<style>"
    "  .anteprima-isolata {"
    "    background-color: rgba(156, 39, 176, 0.08);"
    "    border-left: 4px solid #9C27B0;"
    "    padding: 12px;"
    "    margin: 14px 0 5px 0;"
    "    font-size: 11px;"
    "    border-radius: 4px;"
    "  }"
    "  .anteprima-isolata, .anteprima-isolata * {"
    "    background-color: transparent !important;"
    "  }"
    "  .blocco-campo {"
    "    margin-top: 12px !important;"
    "    margin-bottom: 0px !important;"
    "    line-height: 1.35 !important;"
    "  }"
    "  .blocco-campo:first-child {"
    "    margin-top: 0px !important;"
    "  }"
    "  .titolo-campo {"
    "    font-weight: bold;"
    "    display: block !important;"
    "    margin: 0 0 4px 0 !important;"
    "    padding: 0 !important;"
    "  }"
    "  .contenuto-campo {"
    "    margin: 0 !important;"
    "    padding: 0 !important;"
    "    display: block !important;"
    "  }"
    "  .contenuto-campo p,"
    "  .contenuto-campo div,"
    "  .contenuto-campo ol,"
    "  .contenuto-campo ul {"
    "    margin-top: 0px !important;"
    "    margin-bottom: 4px !important;"
    "    padding-top: 0px !important;"
    "  }"
    "  .contenuto-campo > *:first-child {"
    "    margin-top: 0px !important;"
    "    padding-top: 0px !important;"
    "  }"
    "  .contenuto-campo > *:last-child {"
    "    margin-bottom: 0px !important;"
    "    padding-bottom: 0px !important;"
    "  }"
    "  .contenuto-campo p:last-child,"
    "  .contenuto-campo div:last-child {"
    "    margin-bottom: 0px !important;"
    "  }"
    "</style>"
)

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
        self.setWindowTitle("Chat con Gemini")
        self.resize(520, 640)

        self.api_history: list[dict[str, Any]] = []
        self.note_context: str | None = None
        self._loading_phase = 0
        self._copy_blocks: dict[str, str] = {}
        self._copy_counter = 0

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.context_checkbox = QCheckBox("Includi contesto nota nel prossimo messaggio", self)
        self.context_checkbox.setChecked(False)
        toolbar.addWidget(self.context_checkbox)

        btn_clear = QPushButton("Nuova conversazione", self)
        btn_clear.clicked.connect(self.clear_conversation)
        toolbar.addWidget(btn_clear)
        layout.addLayout(toolbar)

        self.chat_log = QTextBrowser(self)
        self.chat_log.setOpenLinks(False)
        self.chat_log.setReadOnly(True)
        self.chat_log.anchorClicked.connect(self._on_anchor_clicked)
        self.chat_log.setPlaceholderText("La conversazione apparirà qui...")
        self.chat_log.document().setDefaultStyleSheet(
            "body { color: #e0e0e0; }"
            "p { margin: 6px 0; }"
            "b, strong { font-weight: bold; color: #f5f5f5; }"
            "i, em { font-style: italic; }"
            "ul, ol { margin: 6px 0; padding-left: 20px; }"
            "li { margin: 3px 0; }"
            "a { color: #64b5f6; text-decoration: none; }"
            "code { font-family: Consolas, monospace; background: rgba(255,255,255,0.1); "
            "padding: 1px 4px; border-radius: 3px; }"
            "hr { border: none; border-top: 1px solid #555; margin: 12px 0; }"
        )
        layout.addWidget(self.chat_log)

        self.loading_label = QLabel("", self)
        self.loading_label.setVisible(False)
        self.loading_label.setStyleSheet("color: #FF9800; font-weight: bold; padding: 4px;")
        layout.addWidget(self.loading_label)

        input_layout = QHBoxLayout()
        self.input_field = QTextEdit(self)
        self.input_field.setFixedHeight(80)
        self.input_field.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.input_field.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.input_field.setPlaceholderText(
            "Chiedi a Gemini o digiti: 'Memorizza globalmente la regola X'...\n"
            "(Invio per inviare, Shift+Invio per andare a capo)"
        )
        self.input_field.installEventFilter(self)

        self.send_button = QPushButton("Invia", self)
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedHeight(80)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)

        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self._update_loading_animation)

        self._append_system_message(
            "Ciao! Puoi chiedermi spiegazioni o dirmi di memorizzare nuove direttive di stile.",
            color="#2196F3",
            label="Gemini",
        )

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
        tooltip("Contenuto del campo copiato negli appunti.")

    def eventFilter(self, obj, event):
        if obj is self.input_field and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    return super().eventFilter(obj, event)
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def clear_conversation(self) -> None:
        self.api_history.clear()
        self.note_context = None
        self._copy_blocks.clear()
        self.context_checkbox.setChecked(False)
        self.chat_log.clear()
        self._append_system_message(
            "Conversazione azzerata. Puoi iniziare una nuova chat.",
            color="#9C27B0",
            label="Sistema",
        )

    def import_note_from_editor(self, editor) -> None:
        note = editor.note
        field_blocks: list[str] = []
        context_lines: list[str] = []

        for name, value in note.items():
            if not value.strip():
                continue
            cleaned = _strip_field_html_edges(value)
            inner = cleaned if cleaned.startswith("<") else html.escape(cleaned)
            field_blocks.append(
                f"<div class='blocco-campo'>"
                f"<div class='titolo-campo'>{html.escape(name)}:</div>"
                f"<div class='contenuto-campo'>{inner}</div>"
                f"</div>"
            )
            context_lines.append(f"Campo [{name}]:\n{value}")

        if not field_blocks:
            self._append_system_message("La nota corrente è completamente vuota.", color="#f44336")
            return

        self.note_context = "\n\n".join(context_lines)
        self.context_checkbox.setChecked(True)
        self._append_system_message("Contenuto della nota importato con successo!", color="#9C27B0")

        preview_html = PREVIEW_STYLE + "<div class='anteprima-isolata'>" + "".join(field_blocks) + "</div>"
        self.chat_log.append(preview_html)
        self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)

        self.input_field.setPlainText(
            load_config().get("brain_import_message") or DEFAULT_BRAIN_IMPORT_MESSAGE
        )
        self.input_field.setFocus()

    def send_message(self) -> None:
        user_text = self.input_field.toPlainText().strip()
        if not user_text:
            return

        safe_html = html.escape(user_text).replace("\n", "<br>")
        self.chat_log.append(f"<br><b style='color:#4CAF50;'>Tu:</b> {safe_html}")
        self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)
        self.input_field.clear()
        self._set_input_enabled(False)

        config = load_config()
        if not api_key_configured(config):
            self._append_system_message("Errore: API Key mancante (⚙️).", color="#f44336")
            self._set_input_enabled(True)
            return

        payload_text = user_text
        if self.context_checkbox.isChecked() and self.note_context:
            payload_text = (
                f"[CONTESTO DELLA NOTA INTERA DA ANALIZZARE]:\n{self.note_context}\n\n"
                f"[RICHIESTA DELLO STUDENTE]:\n{user_text}"
            )
            self.context_checkbox.setChecked(False)

        self.api_history.append({"role": "user", "parts": [{"text": payload_text}]})
        max_turns = int(config.get("max_history_turns", 20))
        history_for_request = trim_history(self.api_history[:-1], max_turns)
        temperature = float(config.get("temperature_chat", 0.2))

        self._start_loading()

        mw.taskman.run_in_background(
            lambda: call_gemini(
                config=config,
                user_text=payload_text,
                history=history_for_request,
                temperature=temperature,
                include_meta_rule=True,
            ),
            self._handle_response,
        )

    def _handle_response(self, future) -> None:
        self._stop_loading()
        self._set_input_enabled(True)
        self.input_field.setFocus()

        try:
            raw_text = future.result()
            display_text, dynamic_rules = extract_dynamic_rules(raw_text)
            rules_updated = False

            if dynamic_rules is not None:
                config = load_config()
                config["dynamic_instructions"] = dynamic_rules
                save_config(config)
                rules_updated = True

            self.api_history.append({"role": "model", "parts": [{"text": display_text}]})

            self._copy_counter += 1
            reply_html = format_gemini_reply_html(
                display_text,
                self._copy_blocks,
                f"r{self._copy_counter}",
            )
            self.chat_log.append(f"<br><b style='color:#2196F3;'>Gemini:</b><br>{reply_html}")
            if rules_updated:
                self._append_system_message(
                    "Memoria dinamica dell'add-on aggiornata e salvata!",
                    color="#9C27B0",
                )
        except GeminiError as exc:
            if self.api_history and self.api_history[-1]["role"] == "user":
                self.api_history.pop()
            self._append_system_message(f"Errore: {exc}", color="#f44336")
        except Exception as exc:
            if self.api_history and self.api_history[-1]["role"] == "user":
                self.api_history.pop()
            self._append_system_message(f"Errore imprevisto: {exc}", color="#f44336")

        self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)

    def _set_input_enabled(self, enabled: bool) -> None:
        self.send_button.setEnabled(enabled)
        self.input_field.setEnabled(enabled)

    def _start_loading(self) -> None:
        self._loading_phase = 0
        self.loading_label.setText("🤖 Gemini sta scrivendo.")
        self.loading_label.setVisible(True)
        self.loading_timer.start(400)

    def _stop_loading(self) -> None:
        self.loading_timer.stop()
        self.loading_label.setVisible(False)

    def _update_loading_animation(self) -> None:
        self._loading_phase = (self._loading_phase % 3) + 1
        dots = "." * self._loading_phase
        self.loading_label.setText(f"🤖 Gemini sta scrivendo{dots}")

    def _append_system_message(self, text: str, color: str, label: str = "Sistema") -> None:
        safe = html.escape(text)
        self.chat_log.append(
            f"<br><b style='color:{color};'>{label}:</b> {safe}"
            f"<div style='margin-bottom: 10px;'></div>"
        )
        self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)


_chat_window: ChatWindow | None = None


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
