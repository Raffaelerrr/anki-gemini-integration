from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aqt.qt import (
    QCheckBox,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
    Qt,
)

from ..config import load_config, save_config
from ..i18n import tr
from .note_fields_editor import NoteFieldsEditor
from .themed_windows import configure_snappable_window

_OnSave = Callable[[list[tuple[str, str]], bool], None]


class ChatNoteEditWindow(QWidget):
    """Edit imported note fields in a separate window."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        on_save: _OnSave,
    ) -> None:
        super().__init__(None)
        configure_snappable_window(self)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self._on_save = on_save
        self.resize(640, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self._editor = NoteFieldsEditor(self)
        root.addWidget(self._editor, 1)

        self._send_empty_checkbox = QCheckBox(self)
        self._send_empty_checkbox.toggled.connect(self._persist_send_empty_setting)
        root.addWidget(self._send_empty_checkbox)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self._cancel_btn = QPushButton(self)
        self._cancel_btn.clicked.connect(self.close)
        self._save_btn = QPushButton(self)
        self._save_btn.clicked.connect(self._save_and_close)
        self._save_btn.setDefault(True)
        self._save_btn.setAutoDefault(True)
        footer.addWidget(self._cancel_btn)
        footer.addWidget(self._save_btn)
        root.addLayout(footer)

        self.apply_language()

    def load_fields(self, fields: list[tuple[str, str]]) -> None:
        config = load_config()
        self._editor.set_fields(fields)
        self._send_empty_checkbox.blockSignals(True)
        self._send_empty_checkbox.setChecked(bool(config.get("chat_send_empty_fields", False)))
        self._send_empty_checkbox.blockSignals(False)

    def commit(self) -> None:
        self._on_save(self._editor.get_fields(), self._send_empty_checkbox.isChecked())

    def apply_language(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        self.setWindowTitle(tr("chat.edit_note", config=config))
        self._send_empty_checkbox.setText(tr("chat.edit_note.send_empty_fields", config=config))
        self._cancel_btn.setText(tr("settings.cancel", config=config))
        self._save_btn.setText(tr("settings.save", config=config))

    def apply_theme(self) -> None:
        self._editor.apply_theme()

    def apply_newline_visibility(self, show: bool) -> None:
        self._editor.apply_newline_visibility(show)

    def _persist_send_empty_setting(self, checked: bool) -> None:
        config = load_config()
        config["chat_send_empty_fields"] = bool(checked)
        save_config(config)

    def _save_and_close(self) -> None:
        self.commit()
        self.close()
