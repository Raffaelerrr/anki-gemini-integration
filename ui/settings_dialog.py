from __future__ import annotations

from typing import Any

from aqt import mw
from aqt.qt import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)
from aqt.utils import showInfo

from ..config import load_config, save_config
from ..constants import DEFAULT_BRAIN_IMPORT_MESSAGE


class SettingsDialog(QDialog):
    def __init__(self, parent, config: dict[str, Any]):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni Avanzate Gemini")
        self.resize(650, 860)
        self.config = dict(config)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>Chiave API Google AI Studio:</b>"))
        saved_key = (self.config.get("api_key") or "").strip()
        self._saved_api_key = saved_key
        self.api_key_status = QLabel(self)
        if saved_key:
            self.api_key_status.setText("Chiave salvata. Lascia il campo vuoto per mantenerla, oppure incolla una nuova chiave.")
            self.api_key_status.setStyleSheet("color: #2e7d32; font-size: 11px;")
        else:
            self.api_key_status.setText("Nessuna chiave salvata. Incolla la chiave da aistudio.google.com.")
            self.api_key_status.setStyleSheet("color: #c62828; font-size: 11px;")
        layout.addWidget(self.api_key_status)
        self.api_key_input = QLineEdit(self)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        if saved_key:
            self.api_key_input.setPlaceholderText("••••••••  (chiave già salvata)")
        else:
            self.api_key_input.setPlaceholderText("Incolla la chiave da aistudio.google.com")
        layout.addWidget(self.api_key_input)

        layout.addWidget(QLabel("<br><b>Modello Gemini:</b>"))
        self.model_input = QLineEdit(self)
        self.model_input.setText(self.config.get("model", "gemini-2.5-flash"))
        self.model_input.setPlaceholderText("es. gemini-2.5-flash")
        layout.addWidget(self.model_input)

        params_row = QHBoxLayout()
        params_row.addWidget(QLabel("Timeout (s):"))
        self.timeout_input = QSpinBox(self)
        self.timeout_input.setRange(5, 120)
        self.timeout_input.setValue(int(self.config.get("timeout_seconds", 30)))
        params_row.addWidget(self.timeout_input)

        params_row.addWidget(QLabel("Max retry:"))
        self.retries_input = QSpinBox(self)
        self.retries_input.setRange(0, 5)
        self.retries_input.setValue(int(self.config.get("max_retries", 2)))
        params_row.addWidget(self.retries_input)

        params_row.addWidget(QLabel("Storico chat (turni):"))
        self.history_input = QSpinBox(self)
        self.history_input.setRange(0, 100)
        self.history_input.setValue(int(self.config.get("max_history_turns", 20)))
        params_row.addWidget(self.history_input)
        layout.addLayout(params_row)

        temp_row = QHBoxLayout()
        temp_row.addWidget(QLabel("Temperatura ottimizzazione:"))
        self.temp_optimize_input = QDoubleSpinBox(self)
        self.temp_optimize_input.setRange(0.0, 2.0)
        self.temp_optimize_input.setSingleStep(0.1)
        self.temp_optimize_input.setValue(float(self.config.get("temperature_optimize", 0.1)))
        temp_row.addWidget(self.temp_optimize_input)

        temp_row.addWidget(QLabel("Temperatura chat:"))
        self.temp_chat_input = QDoubleSpinBox(self)
        self.temp_chat_input.setRange(0.0, 2.0)
        self.temp_chat_input.setSingleStep(0.1)
        self.temp_chat_input.setValue(float(self.config.get("temperature_chat", 0.2)))
        temp_row.addWidget(self.temp_chat_input)
        layout.addLayout(temp_row)

        self.confirm_checkbox = QCheckBox(
            "Mostra anteprima prima di applicare l'ottimizzazione del campo",
            self,
        )
        self.confirm_checkbox.setChecked(bool(self.config.get("confirm_before_apply", True)))
        layout.addWidget(self.confirm_checkbox)

        layout.addWidget(
            QLabel("<br><b>Messaggio predefinito importazione nota (🧠):</b>")
        )
        layout.addWidget(
            QLabel(
                "<span style='font-size: 11px; color: #666;'>"
                "Testo inserito automaticamente nella chat quando importi una nota con il bottone 🧠."
                "</span>"
            )
        )
        self.brain_message_input = QTextEdit(self)
        self.brain_message_input.setFixedHeight(70)
        self.brain_message_input.setPlainText(
            self.config.get("brain_import_message") or DEFAULT_BRAIN_IMPORT_MESSAGE
        )
        layout.addWidget(self.brain_message_input)

        layout.addWidget(QLabel("<br><b>System Instruction Globali (Alta Priorità - Statiche):</b>"))
        self.instruction_input = QTextEdit(self)
        self.instruction_input.setPlainText(self.config.get("system_instruction", ""))
        layout.addWidget(self.instruction_input)

        layout.addWidget(
            QLabel("<br><b>Direttive Dinamiche Apprese (Bassa Priorità - Aggiornabili via Chat):</b>")
        )
        self.dynamic_input = QTextEdit(self)
        self.dynamic_input.setPlaceholderText(
            "Le regole che dirai a Gemini di ricordare nella chat appariranno qui automaticamente..."
        )
        self.dynamic_input.setPlainText(self.config.get("dynamic_instructions", ""))
        layout.addWidget(self.dynamic_input)

        layout.addWidget(QLabel("<br><b>Scorciatoie da Tastiera:</b>"))
        shortcuts = QLabel(
            "<div style='font-size: 11px; color: #2c3e50; line-height: 1.4;'>"
            "• <b>Ctrl + Shift + G</b> : Ottimizza il campo attivo nell'Editor.<br>"
            "• <b>Ctrl + Alt + C</b> : Apri / Porta in primo piano la Chat con Gemini."
            "</div>"
        )
        shortcuts.setStyleSheet(
            "background-color: #f7f9fa; border: 1px solid #dcdfe1; "
            "border-radius: 6px; padding: 8px;"
        )
        layout.addWidget(shortcuts)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Salva ed Applica", self)
        btn_save.clicked.connect(self._save_and_accept)
        btn_cancel = QPushButton("Annulla", self)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _save_and_accept(self) -> None:
        new_key = self.api_key_input.text().strip()
        self.config["api_key"] = new_key if new_key else self._saved_api_key
        self.config["model"] = self.model_input.text().strip() or "gemini-2.5-flash"
        self.config["timeout_seconds"] = self.timeout_input.value()
        self.config["max_retries"] = self.retries_input.value()
        self.config["max_history_turns"] = self.history_input.value()
        self.config["temperature_optimize"] = self.temp_optimize_input.value()
        self.config["temperature_chat"] = self.temp_chat_input.value()
        self.config["confirm_before_apply"] = self.confirm_checkbox.isChecked()
        self.config["brain_import_message"] = self.brain_message_input.toPlainText().strip()
        self.config["system_instruction"] = self.instruction_input.toPlainText()
        self.config["dynamic_instructions"] = self.dynamic_input.toPlainText()
        save_config(self.config)
        self.accept()


def open_settings_dialog(editor) -> None:
    config = load_config()
    dialog = SettingsDialog(editor.parentWindow, config)
    dialog.exec()
