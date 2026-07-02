from __future__ import annotations

from typing import Any

from aqt.qt import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    Qt,
    QVBoxLayout,
    QWidget,
)
from aqt import mw
from aqt.utils import showInfo, showWarning

from ..constants import DEFAULT_MODEL_CHAT, DEFAULT_MODEL_OPTIMIZE, DEFAULT_THINKING_BUDGET_CHAT, DEFAULT_THINKING_BUDGET_OPTIMIZE
from ..config import (
    DISMISSIBLE_WARNING_KEYS,
    DISMISSIBLE_WARNING_LABELS,
    RESTORABLE_SETTING_KEYS,
    RESTORABLE_SETTING_LABELS,
    api_key_configured,
    default_config_value,
    dismissed_warning_keys,
    is_warning_dismissed,
    load_config,
    save_config,
)
from ..gemini_client import GeminiError, list_gemini_models
from ..i18n import (
    LANG_EN,
    LANG_IT,
    DEFAULT_LANGUAGE,
    effective_brain_import_message,
    is_builtin_brain_import_message,
    is_builtin_system_instruction,
    normalize_brain_import_message_for_save,
    normalize_system_instruction_fields_for_save,
    effective_system_instruction,
    tr,
)
from .chat_dialog import refresh_chat_language
from .settings_help_dialog import open_settings_help_dialog
from .model_selector import (
    create_model_selector,
    model_selector_value,
    set_model_selector_value,
    update_model_selector_choices,
)
from .widgets import (
    NoWheelComboBox,
    NoWheelDoubleSpinBox,
    NoWheelSpinBox,
    ScrollAwareTextEdit,
)
from .theme import (
    muted_hint_html,
    panel_content_html,
    panel_widget_stylesheet,
    status_color_stylesheet,
)


_settings_dialog: SettingsDialog | None = None

_FOOTER_BUTTON_STYLE = """
QPushButton {
    text-align: left;
    padding: 6px 12px;
    min-height: 28px;
}
"""


def _setup_footer_button(button: QPushButton, *, tooltip: str) -> None:
    button.setToolTip(tooltip)
    button.setStyleSheet(_FOOTER_BUTTON_STYLE)
    button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)


class SettingsDialog(QDialog):
    def __init__(self, parent, config: dict[str, Any]):
        super().__init__(parent)
        self._config = config
        self.config = dict(config)
        self._restore_checkboxes: dict[str, QCheckBox] = {}
        self._warning_restore_checkboxes: dict[str, QCheckBox] = {}
        self._all_restore_checked = True
        self._all_warnings_checked = True
        self._model_refresh_busy = False
        self._settings_help_dialog = None

        self.setWindowTitle(tr("settings.title", config=config))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(680, 420)
        self.resize(780, 760)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        self.stack = QStackedWidget(self)
        self.stack.addWidget(self._build_form_page())
        self.stack.addWidget(self._build_restore_page())
        self.stack.addWidget(self._build_restore_warnings_page())
        root.addWidget(self.stack, 1)

        self._form_btn_layout = QVBoxLayout()
        self._form_btn_layout.setSpacing(6)

        utility_row = QHBoxLayout()
        utility_row.setSpacing(8)
        self.btn_restore_mode = QPushButton(tr("settings.restore_defaults", config=config), self)
        self.btn_restore_mode.clicked.connect(self._enter_restore_mode)
        _setup_footer_button(
            self.btn_restore_mode,
            tooltip=tr("settings.restore_defaults", config=config),
        )
        self.btn_restore_warnings = QPushButton(tr("settings.restore_warnings", config=config), self)
        self.btn_restore_warnings.clicked.connect(self._enter_restore_warnings_mode)
        _setup_footer_button(
            self.btn_restore_warnings,
            tooltip=tr("settings.restore_warnings", config=config),
        )
        self.btn_settings_help = QPushButton(tr("settings.info", config=config), self)
        self.btn_settings_help.clicked.connect(self._open_settings_help)
        _setup_footer_button(
            self.btn_settings_help,
            tooltip=tr("settings.info", config=config),
        )
        utility_row.addWidget(self.btn_restore_mode)
        utility_row.addWidget(self.btn_restore_warnings)
        utility_row.addWidget(self.btn_settings_help)
        utility_row.addStretch(1)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.btn_save = QPushButton(tr("settings.save", config=config), self)
        self.btn_save.clicked.connect(self._save_and_accept)
        _setup_footer_button(
            self.btn_save,
            tooltip=tr("settings.save", config=config),
        )
        self.btn_cancel = QPushButton(tr("settings.cancel", config=config), self)
        self.btn_cancel.clicked.connect(self.reject)
        _setup_footer_button(
            self.btn_cancel,
            tooltip=tr("settings.cancel", config=config),
        )
        action_row.addStretch(1)
        action_row.addWidget(self.btn_save)
        action_row.addWidget(self.btn_cancel)

        self._form_btn_layout.addLayout(utility_row)
        self._form_btn_layout.addLayout(action_row)
        root.addLayout(self._form_btn_layout)

        self._restore_btn_layout = QHBoxLayout()
        self._restore_btn_layout.setSpacing(8)
        self.btn_toggle_all = QPushButton(tr("settings.restore.toggle_all", config=config), self)
        self.btn_toggle_all.clicked.connect(self._toggle_all_restore_checks)
        _setup_footer_button(
            self.btn_toggle_all,
            tooltip=tr("settings.restore.toggle_all", config=config),
        )
        self.btn_apply_restore = QPushButton(tr("settings.restore.apply", config=config), self)
        self.btn_apply_restore.clicked.connect(self._apply_selected_defaults)
        _setup_footer_button(
            self.btn_apply_restore,
            tooltip=tr("settings.restore.apply", config=config),
        )
        self.btn_restore_back = QPushButton(tr("settings.restore.back", config=config), self)
        self.btn_restore_back.clicked.connect(self._leave_restore_mode)
        _setup_footer_button(
            self.btn_restore_back,
            tooltip=tr("settings.restore.back", config=config),
        )
        self._restore_btn_layout.addWidget(self.btn_toggle_all)
        self._restore_btn_layout.addStretch(1)
        self._restore_btn_layout.addWidget(self.btn_apply_restore)
        self._restore_btn_layout.addWidget(self.btn_restore_back)
        root.addLayout(self._restore_btn_layout)

        self._warnings_btn_layout = QHBoxLayout()
        self._warnings_btn_layout.setSpacing(8)
        self.btn_warnings_toggle_all = QPushButton(tr("settings.restore.toggle_all", config=config), self)
        self.btn_warnings_toggle_all.clicked.connect(self._toggle_all_warning_restore_checks)
        _setup_footer_button(
            self.btn_warnings_toggle_all,
            tooltip=tr("settings.restore.toggle_all", config=config),
        )
        self.btn_apply_warning_restore = QPushButton(tr("settings.restore_warnings.apply", config=config), self)
        self.btn_apply_warning_restore.clicked.connect(self._apply_selected_warning_restores)
        _setup_footer_button(
            self.btn_apply_warning_restore,
            tooltip=tr("settings.restore_warnings.apply", config=config),
        )
        self.btn_warnings_back = QPushButton(tr("settings.restore.back", config=config), self)
        self.btn_warnings_back.clicked.connect(self._leave_restore_warnings_mode)
        _setup_footer_button(
            self.btn_warnings_back,
            tooltip=tr("settings.restore.back", config=config),
        )
        self._warnings_btn_layout.addWidget(self.btn_warnings_toggle_all)
        self._warnings_btn_layout.addStretch(1)
        self._warnings_btn_layout.addWidget(self.btn_apply_warning_restore)
        self._warnings_btn_layout.addWidget(self.btn_warnings_back)
        root.addLayout(self._warnings_btn_layout)

        self._set_subpage_mode(None)

    def _build_form_page(self) -> QWidget:
        config = self.config
        page = QWidget(self)
        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        form_host = QWidget(scroll)
        layout = QVBoxLayout(form_host)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel(f"<b>{tr('settings.language', config=config)}</b>"))
        self.language_combo = NoWheelComboBox(form_host)
        self.language_combo.addItem(tr("settings.language.it", config=config), LANG_IT)
        self.language_combo.addItem(tr("settings.language.en", config=config), LANG_EN)
        current_lang = (self.config.get("language") or DEFAULT_LANGUAGE).lower()
        index = self.language_combo.findData(LANG_EN if current_lang.startswith("en") else LANG_IT)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        layout.addWidget(self.language_combo)

        layout.addWidget(QLabel(f"<br><b>{tr('settings.api_key', config=config)}</b>"))
        saved_key = (self.config.get("api_key") or "").strip()
        self._saved_api_key = saved_key
        self.api_key_status = QLabel(form_host)
        self._update_api_key_status()
        layout.addWidget(self.api_key_status)
        self.api_key_input = QLineEdit(form_host)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        if saved_key:
            self.api_key_input.setPlaceholderText(tr("settings.api_key.placeholder.saved", config=config))
        else:
            self.api_key_input.setPlaceholderText(tr("settings.api_key.placeholder.empty", config=config))
        layout.addWidget(self.api_key_input)

        layout.addWidget(QLabel(f"<br><b>{tr('settings.model_optimize', config=config)}</b>"))
        optimize_row = QHBoxLayout()
        self.model_optimize_input = create_model_selector(
            form_host,
            current=self.config.get("model_optimize", DEFAULT_MODEL_OPTIMIZE),
            default=DEFAULT_MODEL_OPTIMIZE,
            config=config,
        )
        optimize_row.addWidget(self.model_optimize_input, stretch=1)
        self.btn_refresh_optimize_models = QPushButton(tr("settings.model.refresh", config=config), form_host)
        self.btn_refresh_optimize_models.clicked.connect(self._refresh_models_from_api)
        optimize_row.addWidget(self.btn_refresh_optimize_models)
        layout.addLayout(optimize_row)

        layout.addWidget(QLabel(f"<b>{tr('settings.model_chat', config=config)}</b>"))
        chat_row = QHBoxLayout()
        self.model_chat_input = create_model_selector(
            form_host,
            current=self.config.get("model_chat", DEFAULT_MODEL_CHAT),
            default=DEFAULT_MODEL_CHAT,
            config=config,
        )
        chat_row.addWidget(self.model_chat_input, stretch=1)
        self.btn_refresh_chat_models = QPushButton(tr("settings.model.refresh", config=config), form_host)
        self.btn_refresh_chat_models.clicked.connect(self._refresh_models_from_api)
        chat_row.addWidget(self.btn_refresh_chat_models)
        layout.addLayout(chat_row)

        self.thinking_budget_hint = QLabel(
            muted_hint_html(tr("settings.thinking_budget.hint", config=config)),
            form_host,
        )
        layout.addWidget(self.thinking_budget_hint)
        thinking_row = QHBoxLayout()
        thinking_row.addWidget(QLabel(tr("settings.thinking_budget_optimize", config=config)))
        self.thinking_budget_optimize_input = NoWheelSpinBox(form_host)
        self.thinking_budget_optimize_input.setRange(-1, 24576)
        self.thinking_budget_optimize_input.setValue(
            int(self.config.get("thinking_budget_optimize", DEFAULT_THINKING_BUDGET_OPTIMIZE))
        )
        thinking_row.addWidget(self.thinking_budget_optimize_input)

        thinking_row.addWidget(QLabel(tr("settings.thinking_budget_chat", config=config)))
        self.thinking_budget_chat_input = NoWheelSpinBox(form_host)
        self.thinking_budget_chat_input.setRange(-1, 24576)
        self.thinking_budget_chat_input.setValue(
            int(self.config.get("thinking_budget_chat", DEFAULT_THINKING_BUDGET_CHAT))
        )
        thinking_row.addWidget(self.thinking_budget_chat_input)
        layout.addLayout(thinking_row)

        self.chat_streaming_checkbox = QCheckBox(tr("settings.chat_streaming", config=config), form_host)
        self.chat_streaming_checkbox.setChecked(bool(self.config.get("chat_streaming", True)))
        layout.addWidget(self.chat_streaming_checkbox)

        params_row = QHBoxLayout()
        params_row.addWidget(QLabel(tr("settings.timeout", config=config)))
        self.timeout_input = NoWheelSpinBox(form_host)
        self.timeout_input.setRange(5, 120)
        self.timeout_input.setValue(int(self.config.get("timeout_seconds", 30)))
        params_row.addWidget(self.timeout_input)

        params_row.addWidget(QLabel(tr("settings.max_retry", config=config)))
        self.retries_input = NoWheelSpinBox(form_host)
        self.retries_input.setRange(0, 5)
        self.retries_input.setValue(int(self.config.get("max_retries", 2)))
        params_row.addWidget(self.retries_input)

        params_row.addWidget(QLabel(tr("settings.chat_history", config=config)))
        self.history_input = NoWheelSpinBox(form_host)
        self.history_input.setRange(0, 100)
        self.history_input.setValue(int(self.config.get("max_history_turns", 20)))
        params_row.addWidget(self.history_input)
        layout.addLayout(params_row)

        temp_row = QHBoxLayout()
        temp_row.addWidget(QLabel(tr("settings.temp_optimize", config=config)))
        self.temp_optimize_input = NoWheelDoubleSpinBox(form_host)
        self.temp_optimize_input.setRange(0.0, 2.0)
        self.temp_optimize_input.setSingleStep(0.1)
        self.temp_optimize_input.setValue(float(self.config.get("temperature_optimize", 0.1)))
        temp_row.addWidget(self.temp_optimize_input)

        temp_row.addWidget(QLabel(tr("settings.temp_chat", config=config)))
        self.temp_chat_input = NoWheelDoubleSpinBox(form_host)
        self.temp_chat_input.setRange(0.0, 2.0)
        self.temp_chat_input.setSingleStep(0.1)
        self.temp_chat_input.setValue(float(self.config.get("temperature_chat", 0.2)))
        temp_row.addWidget(self.temp_chat_input)
        layout.addLayout(temp_row)

        self.confirm_checkbox = QCheckBox(tr("settings.confirm_preview", config=config), form_host)
        self.confirm_checkbox.setChecked(bool(self.config.get("confirm_before_apply", True)))
        layout.addWidget(self.confirm_checkbox)

        layout.addWidget(QLabel(f"<br><b>{tr('settings.brain_message', config=config)}</b>"))
        self.brain_message_hint = QLabel(
            muted_hint_html(tr("settings.brain_message.hint", config=config)),
            form_host,
        )
        layout.addWidget(self.brain_message_hint)
        self.brain_message_input = ScrollAwareTextEdit(form_host)
        self.brain_message_input.setMinimumHeight(70)
        self.brain_message_input.setMaximumHeight(120)
        self.brain_message_input.setPlainText(effective_brain_import_message(self.config))
        layout.addWidget(self.brain_message_input)

        layout.addWidget(QLabel(f"<br><b>{tr('settings.system_instruction', config=config)}</b>"))
        self.instruction_shared_checkbox = QCheckBox(
            tr("settings.system_instruction_shared", config=config),
            form_host,
        )
        self.instruction_shared_checkbox.setChecked(bool(self.config.get("system_instruction_shared", True)))
        self.instruction_shared_checkbox.toggled.connect(self._on_instruction_shared_toggled)
        layout.addWidget(self.instruction_shared_checkbox)

        self.instruction_shared_host = QWidget(form_host)
        shared_instruction_layout = QVBoxLayout(self.instruction_shared_host)
        shared_instruction_layout.setContentsMargins(0, 0, 0, 0)
        self.instruction_input = ScrollAwareTextEdit(self.instruction_shared_host)
        self.instruction_input.setMinimumHeight(140)
        shared_instruction_layout.addWidget(self.instruction_input)

        self.instruction_split_host = QWidget(form_host)
        split_instruction_layout = QVBoxLayout(self.instruction_split_host)
        split_instruction_layout.setContentsMargins(0, 0, 0, 0)
        self.instruction_optimize_label = QLabel(
            f"<b>{tr('settings.system_instruction_optimize', config=config)}</b>",
            self.instruction_split_host,
        )
        split_instruction_layout.addWidget(self.instruction_optimize_label)
        self.instruction_optimize_input = ScrollAwareTextEdit(self.instruction_split_host)
        self.instruction_optimize_input.setMinimumHeight(120)
        split_instruction_layout.addWidget(self.instruction_optimize_input)
        self.instruction_chat_label = QLabel(
            f"<b>{tr('settings.system_instruction_chat', config=config)}</b>",
            self.instruction_split_host,
        )
        split_instruction_layout.addWidget(self.instruction_chat_label)
        self.instruction_chat_input = ScrollAwareTextEdit(self.instruction_split_host)
        self.instruction_chat_input.setMinimumHeight(120)
        split_instruction_layout.addWidget(self.instruction_chat_input)

        layout.addWidget(self.instruction_shared_host)
        layout.addWidget(self.instruction_split_host)
        self._load_instruction_fields_from_config()
        self._sync_instruction_widgets_visibility()

        layout.addWidget(
            QLabel(f"<br><b>{tr('settings.dynamic_instructions', config=config)}</b>")
        )
        self.dynamic_input = ScrollAwareTextEdit(form_host)
        self.dynamic_input.setMinimumHeight(100)
        self.dynamic_input.setPlaceholderText(tr("settings.dynamic_placeholder", config=config))
        self.dynamic_input.setPlainText(self.config.get("dynamic_instructions", ""))
        layout.addWidget(self.dynamic_input)

        layout.addWidget(QLabel(f"<br><b>{tr('settings.shortcuts', config=config)}</b>"))
        self.shortcuts_panel = QLabel(
            panel_content_html(tr("settings.shortcuts.body", config=config)),
            form_host,
        )
        self.shortcuts_panel.setStyleSheet(panel_widget_stylesheet())
        layout.addWidget(self.shortcuts_panel)

        scroll.setWidget(form_host)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        return page

    def _build_restore_page(self) -> QWidget:
        config = self.config
        page = QWidget(self)
        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        host = QWidget(scroll)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel(f"<b>{tr('settings.restore.title', config=config)}</b>"))
        self.restore_hint_label = QLabel(
            muted_hint_html(tr("settings.restore.hint", config=config)),
            host,
        )
        layout.addWidget(self.restore_hint_label)
        layout.addWidget(QLabel("<br>"))

        self._restore_checkboxes.clear()
        for key in RESTORABLE_SETTING_KEYS:
            label_key = RESTORABLE_SETTING_LABELS.get(key, key)
            checkbox = QCheckBox(tr(label_key, config=config), host)
            checkbox.setChecked(key != "api_key")
            layout.addWidget(checkbox)
            self._restore_checkboxes[key] = checkbox

        layout.addStretch(1)
        scroll.setWidget(host)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        return page

    def _build_restore_warnings_page(self) -> QWidget:
        config = self.config
        page = QWidget(self)
        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        host = QWidget(scroll)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel(f"<b>{tr('settings.restore_warnings.title', config=config)}</b>"))
        self.restore_warnings_hint_label = QLabel(
            muted_hint_html(tr("settings.restore_warnings.hint", config=config)),
            host,
        )
        layout.addWidget(self.restore_warnings_hint_label)
        layout.addWidget(QLabel("<br>"))

        self._warning_restore_checkboxes.clear()
        for key in DISMISSIBLE_WARNING_KEYS:
            label_key = DISMISSIBLE_WARNING_LABELS.get(key, key)
            checkbox = QCheckBox(tr(label_key, config=config), host)
            checkbox.setChecked(is_warning_dismissed(self.config, key))
            layout.addWidget(checkbox)
            self._warning_restore_checkboxes[key] = checkbox

        layout.addStretch(1)
        scroll.setWidget(host)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        return page

    def _open_settings_help(self) -> None:
        if self._settings_help_dialog is not None and self._settings_help_dialog.isVisible():
            self._settings_help_dialog.raise_()
            self._settings_help_dialog.activateWindow()
            return

        help_config = self._config_for_api()
        help_config["language"] = self.language_combo.currentData() or DEFAULT_LANGUAGE
        self._settings_help_dialog = open_settings_help_dialog(self, help_config)
        self._settings_help_dialog.finished.connect(self._on_settings_help_closed)

    def _on_settings_help_closed(self) -> None:
        self._settings_help_dialog = None

    def done(self, result: int) -> None:
        if self._settings_help_dialog is not None:
            self._settings_help_dialog.close()
            self._settings_help_dialog = None
        super().done(result)

    def _ui_config(self) -> dict[str, Any]:
        return {"language": self.language_combo.currentData() or DEFAULT_LANGUAGE}

    def _config_for_api(self) -> dict[str, Any]:
        config = dict(self.config)
        config.update(self._ui_config())
        config["api_key"] = self.api_key_input.text().strip() or self._saved_api_key
        config["timeout_seconds"] = self.timeout_input.value()
        return config

    def _set_model_refresh_busy(self, busy: bool) -> None:
        self._model_refresh_busy = busy
        label = tr(
            "settings.model.refresh.in_progress" if busy else "settings.model.refresh",
            config=self._ui_config(),
        )
        for button in (self.btn_refresh_optimize_models, self.btn_refresh_chat_models):
            button.setEnabled(not busy)
            button.setText(label)

    def _refresh_models_from_api(self) -> None:
        if self._model_refresh_busy:
            return

        config = self._config_for_api()
        if not api_key_configured(config):
            showInfo(tr("settings.model.refresh.no_key", config=config))
            return

        self._set_model_refresh_busy(True)

        def work() -> list[str]:
            return list_gemini_models(config=config)

        def done(future) -> None:
            self._set_model_refresh_busy(False)
            try:
                models = future.result()
            except GeminiError as exc:
                showWarning(str(exc))
                return

            update_model_selector_choices(self.model_optimize_input, models)
            update_model_selector_choices(self.model_chat_input, models)
            showInfo(tr("settings.model.refresh.done", config=config, count=len(models)))

        mw.taskman.run_in_background(work, done)

    def _update_api_key_status(self) -> None:
        config = self._ui_config()
        has_key = bool(self._saved_api_key)
        if has_key:
            self.api_key_status.setText(tr("settings.api_key.saved", config=config))
            self.api_key_status.setStyleSheet(status_color_stylesheet(ok=True))
        else:
            self.api_key_status.setText(tr("settings.api_key.missing", config=config))
            self.api_key_status.setStyleSheet(status_color_stylesheet(ok=False))

    def apply_theme(self) -> None:
        config = self._ui_config()
        self.thinking_budget_hint.setText(
            muted_hint_html(tr("settings.thinking_budget.hint", config=config))
        )
        self.brain_message_hint.setText(
            muted_hint_html(tr("settings.brain_message.hint", config=config))
        )
        self.shortcuts_panel.setText(
            panel_content_html(tr("settings.shortcuts.body", config=config))
        )
        self.shortcuts_panel.setStyleSheet(panel_widget_stylesheet())
        self.restore_hint_label.setText(
            muted_hint_html(tr("settings.restore.hint", config=config))
        )
        self.restore_warnings_hint_label.setText(
            muted_hint_html(tr("settings.restore_warnings.hint", config=config))
        )
        self._update_api_key_status()
        if self._settings_help_dialog is not None:
            self._settings_help_dialog.apply_theme()

    def _default_system_instruction_text(self) -> str:
        lang = self.language_combo.currentData() or DEFAULT_LANGUAGE
        return tr("defaults.system_instruction", lang=lang)

    def _set_instruction_field_text(self, editor: ScrollAwareTextEdit, text: str) -> None:
        editor.setPlainText(text)
        editor.clear_text_selection()

    def _set_all_instruction_fields(self, text: str) -> None:
        for editor in (
            self.instruction_input,
            self.instruction_optimize_input,
            self.instruction_chat_input,
        ):
            self._set_instruction_field_text(editor, text)

    def _load_instruction_fields_from_config(self) -> None:
        self._set_instruction_field_text(
            self.instruction_input,
            effective_system_instruction(self.config, purpose="optimize"),
        )
        self._set_instruction_field_text(
            self.instruction_optimize_input,
            effective_system_instruction(self.config, purpose="optimize"),
        )
        self._set_instruction_field_text(
            self.instruction_chat_input,
            effective_system_instruction(self.config, purpose="chat"),
        )

    def _sync_instruction_widgets_visibility(self) -> None:
        shared = self.instruction_shared_checkbox.isChecked()
        self.instruction_shared_host.setVisible(shared)
        self.instruction_split_host.setVisible(not shared)

    def _on_instruction_shared_toggled(self, shared: bool) -> None:
        if shared:
            source = self.instruction_optimize_input.toPlainText().strip()
            if not source:
                source = self.instruction_chat_input.toPlainText()
            self.instruction_input.setPlainText(source)
        else:
            shared_text = self.instruction_input.toPlainText()
            self.instruction_optimize_input.setPlainText(shared_text)
            self.instruction_chat_input.setPlainText(shared_text)
        self._sync_instruction_widgets_visibility()

    def _refresh_builtin_instruction_fields_for_language(self, lang: str) -> None:
        if self.instruction_shared_checkbox.isChecked():
            current = self.instruction_input.toPlainText().strip()
            if is_builtin_system_instruction(current):
                self._set_instruction_field_text(
                    self.instruction_input,
                    tr("defaults.system_instruction", lang=lang),
                )
            return

        current_optimize = self.instruction_optimize_input.toPlainText().strip()
        if is_builtin_system_instruction(current_optimize):
            self._set_instruction_field_text(
                self.instruction_optimize_input,
                tr("defaults.system_instruction", lang=lang),
            )

        current_chat = self.instruction_chat_input.toPlainText().strip()
        if is_builtin_system_instruction(current_chat):
            self._set_instruction_field_text(
                self.instruction_chat_input,
                tr("defaults.system_instruction", lang=lang),
            )

    def _set_subpage_mode(self, mode: str | None) -> None:
        on_form = mode is None
        on_defaults = mode == "defaults"
        on_warnings = mode == "warnings"

        self.btn_restore_mode.setVisible(on_form)
        self.btn_restore_warnings.setVisible(on_form)
        self.btn_settings_help.setVisible(on_form)
        self.btn_save.setVisible(on_form)
        self.btn_cancel.setVisible(on_form)

        self.btn_toggle_all.setVisible(on_defaults)
        self.btn_apply_restore.setVisible(on_defaults)
        self.btn_restore_back.setVisible(on_defaults)

        self.btn_warnings_toggle_all.setVisible(on_warnings)
        self.btn_apply_warning_restore.setVisible(on_warnings)
        self.btn_warnings_back.setVisible(on_warnings)

    def _refresh_warning_restore_checkboxes(self) -> None:
        for key, checkbox in self._warning_restore_checkboxes.items():
            checkbox.setChecked(is_warning_dismissed(self.config, key))

    def _enter_restore_mode(self) -> None:
        self._all_restore_checked = False
        for key, checkbox in self._restore_checkboxes.items():
            checkbox.setChecked(key != "api_key")
        self.stack.setCurrentIndex(1)
        self._set_subpage_mode("defaults")

    def _confirm_dismissible_warning(
        self,
        *,
        title_key: str,
        message_key: str,
        detail_key: str,
        dismiss_config_key: str,
    ) -> bool:
        config = self._ui_config()
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr(title_key, config=config))
        box.setText(tr(message_key, config=config))
        box.setInformativeText(tr(detail_key, config=config))
        box.setStandardButtons(
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)

        dismiss = QCheckBox(tr("optimize.warning.dismiss", config=config), box)
        box.setCheckBox(dismiss)

        if box.exec() != QMessageBox.StandardButton.Ok:
            return False

        if dismiss.isChecked():
            updated = load_config()
            updated[dismiss_config_key] = True
            save_config(updated)

        return True

    def _confirm_api_key_restore(self) -> bool:
        if not self._saved_api_key:
            return True
        if is_warning_dismissed(load_config(), "suppress_api_key_restore_warning"):
            return True
        return self._confirm_dismissible_warning(
            title_key="settings.restore.api_key.title",
            message_key="settings.restore.api_key.message",
            detail_key="settings.restore.api_key.detail",
            dismiss_config_key="suppress_api_key_restore_warning",
        )

    def _leave_restore_mode(self) -> None:
        self.stack.setCurrentIndex(0)
        self._set_subpage_mode(None)

    def _enter_restore_warnings_mode(self) -> None:
        self._refresh_warning_restore_checkboxes()
        dismissed = dismissed_warning_keys(self.config)
        self._all_warnings_checked = bool(dismissed) and len(dismissed) == len(DISMISSIBLE_WARNING_KEYS)
        for key, checkbox in self._warning_restore_checkboxes.items():
            checkbox.setChecked(key in dismissed)
        self.stack.setCurrentIndex(2)
        self._set_subpage_mode("warnings")

    def _leave_restore_warnings_mode(self) -> None:
        self.stack.setCurrentIndex(0)
        self._set_subpage_mode(None)

    def _toggle_all_warning_restore_checks(self) -> None:
        self._all_warnings_checked = not self._all_warnings_checked
        for checkbox in self._warning_restore_checkboxes.values():
            checkbox.setChecked(self._all_warnings_checked)

    def _toggle_all_restore_checks(self) -> None:
        self._all_restore_checked = not self._all_restore_checked
        for checkbox in self._restore_checkboxes.values():
            checkbox.setChecked(self._all_restore_checked)

    def _selected_restore_keys(self) -> list[str]:
        return [key for key, checkbox in self._restore_checkboxes.items() if checkbox.isChecked()]

    def _apply_default_for_key(self, key: str) -> None:
        default_value = default_config_value(key)
        if key == "language":
            index = self.language_combo.findData(default_value or DEFAULT_LANGUAGE)
            if index >= 0:
                self.language_combo.setCurrentIndex(index)
            return

        if key == "api_key":
            self.api_key_input.clear()
            self._saved_api_key = ""
            self.api_key_input.setPlaceholderText(
                tr("settings.api_key.placeholder.empty", config=self._ui_config())
            )
            self._update_api_key_status()
            return

        if key == "model_optimize":
            set_model_selector_value(self.model_optimize_input, str(default_value))
            return

        if key == "model_chat":
            set_model_selector_value(self.model_chat_input, str(default_value))
            return

        if key == "thinking_budget_optimize":
            self.thinking_budget_optimize_input.setValue(int(default_value))
            return

        if key == "thinking_budget_chat":
            self.thinking_budget_chat_input.setValue(int(default_value))
            return

        if key == "chat_streaming":
            self.chat_streaming_checkbox.setChecked(bool(default_value))
            return

        if key == "timeout_seconds":
            self.timeout_input.setValue(int(default_value))
            return

        if key == "max_retries":
            self.retries_input.setValue(int(default_value))
            return

        if key == "max_history_turns":
            self.history_input.setValue(int(default_value))
            return

        if key == "temperature_optimize":
            self.temp_optimize_input.setValue(float(default_value))
            return

        if key == "temperature_chat":
            self.temp_chat_input.setValue(float(default_value))
            return

        if key == "confirm_before_apply":
            self.confirm_checkbox.setChecked(bool(default_value))
            return

        if key == "brain_import_message":
            self.brain_message_input.setPlainText(
                effective_brain_import_message({"language": self.language_combo.currentData() or DEFAULT_LANGUAGE})
            )
            return

        if key == "system_instruction":
            self._set_all_instruction_fields(self._default_system_instruction_text())
            return

        if key == "system_instruction_shared":
            self.instruction_shared_checkbox.setChecked(bool(default_value))
            self._sync_instruction_widgets_visibility()
            return

        if key == "system_instruction_optimize":
            default_text = self._default_system_instruction_text()
            self._set_instruction_field_text(self.instruction_optimize_input, default_text)
            if self.instruction_shared_checkbox.isChecked():
                self._set_instruction_field_text(self.instruction_input, default_text)
            return

        if key == "system_instruction_chat":
            default_text = self._default_system_instruction_text()
            self._set_instruction_field_text(self.instruction_chat_input, default_text)
            if self.instruction_shared_checkbox.isChecked():
                self._set_instruction_field_text(self.instruction_input, default_text)
            return

        if key == "dynamic_instructions":
            self.dynamic_input.setPlainText(str(default_value))
            return

    def _apply_selected_defaults(self) -> None:
        selected = self._selected_restore_keys()
        if not selected:
            showInfo(tr("settings.restore.none_selected", config=self._ui_config()))
            return

        if "api_key" in selected and not self._confirm_api_key_restore():
            selected = [key for key in selected if key != "api_key"]
            if not selected:
                return

        for key in selected:
            self._apply_default_for_key(key)

        self._leave_restore_mode()

    def _selected_warning_restore_keys(self) -> list[str]:
        return [key for key, checkbox in self._warning_restore_checkboxes.items() if checkbox.isChecked()]

    def _apply_selected_warning_restores(self) -> None:
        selected = self._selected_warning_restore_keys()
        if not selected:
            showInfo(tr("settings.restore_warnings.none_selected", config=self._ui_config()))
            return

        for key in selected:
            self.config[key] = False

        self._refresh_warning_restore_checkboxes()
        self._leave_restore_warnings_mode()

    def _on_language_changed(self) -> None:
        lang = self.language_combo.currentData() or DEFAULT_LANGUAGE
        current_brain = self.brain_message_input.toPlainText().strip()
        if is_builtin_brain_import_message(current_brain):
            self.brain_message_input.setPlainText(tr("defaults.brain_import_message", lang=lang))
        self._refresh_builtin_instruction_fields_for_language(lang)

    def _save_and_accept(self) -> None:
        new_key = self.api_key_input.text().strip()
        self.config["language"] = self.language_combo.currentData() or DEFAULT_LANGUAGE
        self.config["api_key"] = new_key if new_key else self._saved_api_key
        self.config["model_optimize"] = model_selector_value(self.model_optimize_input) or DEFAULT_MODEL_OPTIMIZE
        self.config["model_chat"] = model_selector_value(self.model_chat_input) or DEFAULT_MODEL_CHAT
        self.config["thinking_budget_optimize"] = self.thinking_budget_optimize_input.value()
        self.config["thinking_budget_chat"] = self.thinking_budget_chat_input.value()
        self.config["chat_streaming"] = self.chat_streaming_checkbox.isChecked()
        self.config.pop("model", None)
        self.config.pop("thinking_budget", None)
        self.config["timeout_seconds"] = self.timeout_input.value()
        self.config["max_retries"] = self.retries_input.value()
        self.config["max_history_turns"] = self.history_input.value()
        self.config["temperature_optimize"] = self.temp_optimize_input.value()
        self.config["temperature_chat"] = self.temp_chat_input.value()
        self.config["confirm_before_apply"] = self.confirm_checkbox.isChecked()
        brain_message = self.brain_message_input.toPlainText().strip()
        self.config["brain_import_message"] = normalize_brain_import_message_for_save(
            brain_message, self.config
        )
        instruction_fields = normalize_system_instruction_fields_for_save(
            shared=self.instruction_shared_checkbox.isChecked(),
            shared_text=self.instruction_input.toPlainText(),
            optimize_text=self.instruction_optimize_input.toPlainText(),
            chat_text=self.instruction_chat_input.toPlainText(),
            config=self.config,
        )
        self.config.update(instruction_fields)
        self.config["dynamic_instructions"] = self.dynamic_input.toPlainText()
        for key in DISMISSIBLE_WARNING_KEYS:
            self.config[key] = bool(self.config.get(key, False))
        save_config(self.config)
        refresh_chat_language()
        self.accept()


def open_settings_dialog(editor) -> None:
    global _settings_dialog
    config = load_config()
    _settings_dialog = SettingsDialog(editor.parentWindow, config)
    _settings_dialog.exec()
    _settings_dialog = None


def refresh_settings_theme() -> None:
    if _settings_dialog is not None:
        _settings_dialog.apply_theme()
