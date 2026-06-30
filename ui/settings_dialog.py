from __future__ import annotations

from typing import Any

from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    Qt,
    QVBoxLayout,
    QWidget,
)

from ..config import load_config, save_config
from ..i18n import LANG_EN, LANG_IT, default_brain_import_message, tr
from .chat_dialog import refresh_chat_language


class SettingsDialog(QDialog):
    def __init__(self, parent, config: dict[str, Any]):
        super().__init__(parent)
        self._config = config
        self.config = dict(config)
        self.setWindowTitle(tr("settings.title", config=config))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(520, 420)
        self.resize(650, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        form_host = QWidget(self)
        layout = QVBoxLayout(form_host)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel(f"<b>{tr('settings.language', config=config)}</b>"))
        self.language_combo = QComboBox(self)
        self.language_combo.addItem(tr("settings.language.it", config=config), LANG_IT)
        self.language_combo.addItem(tr("settings.language.en", config=config), LANG_EN)
        current_lang = (self.config.get("language") or LANG_IT).lower()
        index = self.language_combo.findData(LANG_EN if current_lang.startswith("en") else LANG_IT)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        layout.addWidget(self.language_combo)

        layout.addWidget(QLabel(f"<br><b>{tr('settings.api_key', config=config)}</b>"))
        saved_key = (self.config.get("api_key") or "").strip()
        self._saved_api_key = saved_key
        self.api_key_status = QLabel(self)
        if saved_key:
            self.api_key_status.setText(tr("settings.api_key.saved", config=config))
            self.api_key_status.setStyleSheet("color: #2e7d32; font-size: 11px;")
        else:
            self.api_key_status.setText(tr("settings.api_key.missing", config=config))
            self.api_key_status.setStyleSheet("color: #c62828; font-size: 11px;")
        layout.addWidget(self.api_key_status)
        self.api_key_input = QLineEdit(self)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        if saved_key:
            self.api_key_input.setPlaceholderText(tr("settings.api_key.placeholder.saved", config=config))
        else:
            self.api_key_input.setPlaceholderText(tr("settings.api_key.placeholder.empty", config=config))
        layout.addWidget(self.api_key_input)

        layout.addWidget(QLabel(f"<br><b>{tr('settings.model', config=config)}</b>"))
        self.model_input = QLineEdit(self)
        self.model_input.setText(self.config.get("model", "gemini-2.5-flash"))
        self.model_input.setPlaceholderText(tr("settings.model.placeholder", config=config))
        layout.addWidget(self.model_input)

        params_row = QHBoxLayout()
        params_row.addWidget(QLabel(tr("settings.timeout", config=config)))
        self.timeout_input = QSpinBox(self)
        self.timeout_input.setRange(5, 120)
        self.timeout_input.setValue(int(self.config.get("timeout_seconds", 30)))
        params_row.addWidget(self.timeout_input)

        params_row.addWidget(QLabel(tr("settings.max_retry", config=config)))
        self.retries_input = QSpinBox(self)
        self.retries_input.setRange(0, 5)
        self.retries_input.setValue(int(self.config.get("max_retries", 2)))
        params_row.addWidget(self.retries_input)

        params_row.addWidget(QLabel(tr("settings.chat_history", config=config)))
        self.history_input = QSpinBox(self)
        self.history_input.setRange(0, 100)
        self.history_input.setValue(int(self.config.get("max_history_turns", 20)))
        params_row.addWidget(self.history_input)
        layout.addLayout(params_row)

        temp_row = QHBoxLayout()
        temp_row.addWidget(QLabel(tr("settings.temp_optimize", config=config)))
        self.temp_optimize_input = QDoubleSpinBox(self)
        self.temp_optimize_input.setRange(0.0, 2.0)
        self.temp_optimize_input.setSingleStep(0.1)
        self.temp_optimize_input.setValue(float(self.config.get("temperature_optimize", 0.1)))
        temp_row.addWidget(self.temp_optimize_input)

        temp_row.addWidget(QLabel(tr("settings.temp_chat", config=config)))
        self.temp_chat_input = QDoubleSpinBox(self)
        self.temp_chat_input.setRange(0.0, 2.0)
        self.temp_chat_input.setSingleStep(0.1)
        self.temp_chat_input.setValue(float(self.config.get("temperature_chat", 0.2)))
        temp_row.addWidget(self.temp_chat_input)
        layout.addLayout(temp_row)

        self.confirm_checkbox = QCheckBox(tr("settings.confirm_preview", config=config), self)
        self.confirm_checkbox.setChecked(bool(self.config.get("confirm_before_apply", True)))
        layout.addWidget(self.confirm_checkbox)

        layout.addWidget(QLabel(f"<br><b>{tr('settings.brain_message', config=config)}</b>"))
        layout.addWidget(
            QLabel(
                "<span style='font-size: 11px; color: #666;'>"
                f"{tr('settings.brain_message.hint', config=config)}"
                "</span>"
            )
        )
        self.brain_message_input = QTextEdit(self)
        self.brain_message_input.setMinimumHeight(70)
        self.brain_message_input.setMaximumHeight(120)
        self.brain_message_input.setPlainText(
            self.config.get("brain_import_message") or default_brain_import_message(self.config)
        )
        layout.addWidget(self.brain_message_input)

        layout.addWidget(QLabel(f"<br><b>{tr('settings.system_instruction', config=config)}</b>"))
        self.instruction_input = QTextEdit(self)
        self.instruction_input.setMinimumHeight(140)
        self.instruction_input.setPlainText(self.config.get("system_instruction", ""))
        layout.addWidget(self.instruction_input)

        layout.addWidget(
            QLabel(f"<br><b>{tr('settings.dynamic_instructions', config=config)}</b>")
        )
        self.dynamic_input = QTextEdit(self)
        self.dynamic_input.setMinimumHeight(100)
        self.dynamic_input.setPlaceholderText(tr("settings.dynamic_placeholder", config=config))
        self.dynamic_input.setPlainText(self.config.get("dynamic_instructions", ""))
        layout.addWidget(self.dynamic_input)

        layout.addWidget(QLabel(f"<br><b>{tr('settings.shortcuts', config=config)}</b>"))
        shortcuts = QLabel(
            "<div style='font-size: 11px; color: #2c3e50; line-height: 1.4;'>"
            f"{tr('settings.shortcuts.body', config=config)}"
            "</div>"
        )
        shortcuts.setStyleSheet(
            "background-color: #f7f9fa; border: 1px solid #dcdfe1; "
            "border-radius: 6px; padding: 8px;"
        )
        layout.addWidget(shortcuts)

        scroll.setWidget(form_host)
        root.addWidget(scroll, 1)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton(tr("settings.save", config=config), self)
        btn_save.clicked.connect(self._save_and_accept)
        btn_cancel = QPushButton(tr("settings.cancel", config=config), self)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        root.addLayout(btn_layout)

    def _save_and_accept(self) -> None:
        new_key = self.api_key_input.text().strip()
        self.config["language"] = self.language_combo.currentData() or LANG_IT
        self.config["api_key"] = new_key if new_key else self._saved_api_key
        self.config["model"] = self.model_input.text().strip() or "gemini-2.5-flash"
        self.config["timeout_seconds"] = self.timeout_input.value()
        self.config["max_retries"] = self.retries_input.value()
        self.config["max_history_turns"] = self.history_input.value()
        self.config["temperature_optimize"] = self.temp_optimize_input.value()
        self.config["temperature_chat"] = self.temp_chat_input.value()
        self.config["confirm_before_apply"] = self.confirm_checkbox.isChecked()
        brain_message = self.brain_message_input.toPlainText().strip()
        self.config["brain_import_message"] = brain_message or default_brain_import_message(self.config)
        self.config["system_instruction"] = self.instruction_input.toPlainText()
        self.config["dynamic_instructions"] = self.dynamic_input.toPlainText()
        save_config(self.config)
        refresh_chat_language()
        self.accept()


def open_settings_dialog(editor) -> None:
    config = load_config()
    dialog = SettingsDialog(editor.parentWindow, config)
    dialog.exec()
