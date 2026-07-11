from __future__ import annotations

from aqt import mw
from aqt.qt import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import tooltip

from ..config import load_config, save_config
from ..dev_mock import (
    dev_mock_log,
    is_dev_mock_enabled,
    reset_dev_mock_state,
    set_dev_mock_log_callback,
)
from .chat_dialog import open_chat
from .theme import apply_native_text_edit_surface_theme


class DevPlaygroundDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Anki AI — Dev playground")
        self.setMinimumSize(560, 420)
        self.resize(620, 480)

        root = QVBoxLayout(self)
        intro = QLabel(
            "<b>Dev mock mode</b> intercepts Gemini API calls and prompt-cache HTTP requests. "
            "Use chat, optimize, and caching as usual — nothing is billed.<br><br>"
            "Mock replies are labeled <code>[Dev mock]</code>. Remote caches live in memory only "
            "and reset when Anki closes (or when you click <b>Reset mock state</b>).",
            self,
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        self.mock_checkbox = QCheckBox("Enable dev mock mode (no real Gemini / cache API calls)", self)
        self.mock_checkbox.setChecked(is_dev_mock_enabled())
        self.mock_checkbox.toggled.connect(self._on_mock_toggled)
        root.addWidget(self.mock_checkbox)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)
        self._refresh_status()

        btn_row = QHBoxLayout()
        self.open_chat_btn = QPushButton("Open chat", self)
        self.open_chat_btn.clicked.connect(lambda: open_chat())
        btn_row.addWidget(self.open_chat_btn)

        self.reset_btn = QPushButton("Reset mock state", self)
        self.reset_btn.clicked.connect(self._reset_mock_state)
        btn_row.addWidget(self.reset_btn)

        self.clear_log_btn = QPushButton("Clear log", self)
        self.clear_log_btn.clicked.connect(self._clear_log)
        btn_row.addWidget(self.clear_log_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        root.addWidget(QLabel("<b>Activity log</b>", self))
        self.log_view = QPlainTextEdit(self)
        self.log_view.setReadOnly(True)
        apply_native_text_edit_surface_theme(self.log_view)
        root.addWidget(self.log_view, stretch=1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)

        set_dev_mock_log_callback(self._append_log)
        if is_dev_mock_enabled():
            dev_mock_log("Dev mock mode is active.")

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _clear_log(self) -> None:
        self.log_view.clear()

    def _refresh_status(self) -> None:
        if is_dev_mock_enabled():
            self.status_label.setText(
                "<span style='color:#2e7d32;'><b>Active</b> — chat, optimize, prompt caching, "
                "and model refresh use local mocks. API key is not required.</span>"
            )
        else:
            self.status_label.setText(
                "Inactive — normal Gemini API calls. Enable the checkbox above for free local testing."
            )

    def _on_mock_toggled(self, checked: bool) -> None:
        config = load_config()
        config["dev_mock_mode"] = bool(checked)
        save_config(config)
        if checked:
            reset_dev_mock_state()
            tooltip("Dev mock mode enabled")
            dev_mock_log("Dev mock mode enabled — local tracking reset.")
        else:
            tooltip("Dev mock mode disabled")
            dev_mock_log("Dev mock mode disabled — real API calls will be used.")
        self._refresh_status()

    def _reset_mock_state(self) -> None:
        reset_dev_mock_state()
        tooltip("Mock state reset")

    def closeEvent(self, event) -> None:
        set_dev_mock_log_callback(None)
        super().closeEvent(event)


_dev_playground_dialog: DevPlaygroundDialog | None = None


def _clear_dev_playground_dialog_ref(_result: int | None = None) -> None:
    global _dev_playground_dialog
    _dev_playground_dialog = None


def open_dev_playground_dialog(parent: QWidget | None = None) -> DevPlaygroundDialog:
    global _dev_playground_dialog
    host = parent if parent is not None else mw
    if _dev_playground_dialog is not None:
        try:
            if _dev_playground_dialog.isVisible():
                _dev_playground_dialog.raise_()
                _dev_playground_dialog.activateWindow()
                return _dev_playground_dialog
        except RuntimeError:
            _dev_playground_dialog = None

    dialog = DevPlaygroundDialog(host)
    _dev_playground_dialog = dialog
    dialog.finished.connect(_clear_dev_playground_dialog_ref)
    dialog.show()
    return dialog
