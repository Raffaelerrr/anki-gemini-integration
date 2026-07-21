from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

from aqt.qt import (
    QCheckBox,
    QCloseEvent,
    QDialog,
    QFrame,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QResizeEvent,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)
from aqt import mw
from aqt.utils import showInfo, showWarning, tooltip

from ..constants import (
    DEFAULT_MODEL_CHAT,
    DEFAULT_MODEL_OPTIMIZE,
    DEFAULT_PROMPT_CACHE_MIN_CHARS,
    DEFAULT_THINKING_BUDGET_CHAT,
    DEFAULT_THINKING_BUDGET_OPTIMIZE,
    GEMINI_AI_STUDIO_BILLING_URL,
    GEMINI_AI_STUDIO_USAGE_URL,
    GEMINI_API_BILLING_DOCS_URL,
)
from ..config import (
    DEFAULT_ACTION_SETTINGS,
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
from ..prompt_cache import (
    PROMPT_CACHE_OPTIMIZE_USER_SEGMENT_ORDER,
    any_tracked_active_cache,
    clear_prompt_cache,
    extend_prompt_cache_ttl,
    get_prompt_cache_store,
    prompt_cache_change_ttl_seconds,
    prompt_cache_segments,
    prompt_cache_status_text,
    segment_label_key,
)
from ..prompt_cache_policy import (
    MAX_CUSTOM_TEXT_PRESETS,
    chat_prompt_cache_summary,
    clone_presets,
    new_preset,
    normalize_custom_text_presets,
    purposes_requiring_cache_invalidation,
)
from ..settings_presets import (
    BUILTIN_SETTINGS_PRESET_ID,
    MAX_SETTINGS_PRESETS,
    builtin_preset_values,
    clone_settings_presets,
    collect_prompt_pack_from_config,
    collect_runtime_pack_from_config,
    dumps_settings_presets_export,
    duplicate_settings_preset,
    find_settings_preset,
    loads_settings_presets_import,
    merge_imported_settings_presets,
    new_settings_preset,
    normalize_settings_presets,
    preset_diff_from_builtin,
    prompt_pack_values_equal,
    resolve_active_settings_preset_id,
    resolve_preset_payload,
    runtime_pack_values_equal,
    translate_preset_import_error,
)
from .chat_prompt_cache_dialog import ChatPromptCacheDialog
from .chat_export import (
    MAX_CHAT_EXPORT_QUICK_FOLDERS,
    default_chat_download_directory,
    normalize_chat_export_quick_folders,
)
from .prompt_cache_confirm import (
    choose_prompt_cache_ttl_targets,
    confirm_custom_text_load_replace,
)
from .prompt_cache_manager_dialog import open_prompt_cache_manager
from ..i18n import (
    LANG_EN,
    LANG_IT,
    DEFAULT_LANGUAGE,
    default_card_templates_format_prompt,
    default_chat_system_addon,
    default_dynamic_rules_prefix,
    default_optimize_user_prompt,
    default_wrapper_section_order,
    effective_brain_import_message,
    effective_card_templates_format_prompt,
    effective_mathjax_preview_preamble,
    effective_chat_system_addon,
    effective_dynamic_rules_prefix,
    effective_optimize_user_prompt,
    is_builtin_brain_import_message,
    is_builtin_card_templates_format_prompt,
    is_builtin_chat_system_addon,
    is_builtin_dynamic_rules_prefix,
    is_builtin_optimize_user_prompt,
    is_builtin_system_instruction,
    is_builtin_wrapper_layout,
    normalize_brain_import_message_for_save,
    normalize_card_templates_format_prompt_for_save,
    normalize_mathjax_preview_preamble_for_save,
    normalize_chat_system_addon_for_save,
    normalize_dynamic_rules_prefix_for_save,
    normalize_optimize_user_prompt_for_save,
    normalize_system_instruction_fields_for_save,
    normalize_wrapper_order_for_save,
    normalize_wrapper_sections_for_save,
    effective_system_instruction,
    tr,
)
from .wrapper_sections_editor import WrapperSectionsEditor
from .themed_windows import configure_snappable_window
from .chat_dialog import refresh_chat_from_settings, refresh_chat_language
from .prompt_inspection_dialog import PromptInspectionWindow
from .settings_help_dialog import (
    _make_info_button,
    open_settings_help_dialog,
)
from .help_icons import (
    instruction_html,
    refresh_info_button_explanation,
    wire_info_button_explanation,
)
from .model_selector import (
    create_model_selector,
    model_selector_value,
    set_model_selector_value,
    update_model_selector_choices,
)
from .settings_compact_controls import (
    SETTINGS_SECTION_GAP,
    SETTINGS_SECTION_INNER_SPACING,
    add_settings_labeled_field,
    add_settings_section_break,
    add_settings_stacked_field,
    apply_settings_icon_row_height,
    create_settings_auto_height_text_edit,
    create_settings_row_auto_height_text_edit,
    create_settings_checkbox_info_row,
    create_settings_combo,
    create_settings_double_spinbox,
    create_settings_hint_label,
    create_settings_line_edit,
    create_settings_panel,
    create_settings_restore_checkbox_row,
    create_settings_section_label,
    create_settings_spinbox,
    refresh_settings_text_edit_layouts,
    refresh_settings_text_edit_newlines,
    refresh_text_edit_wrap,
)
from .widgets import ScrollAwareTextEdit
from .theme import (
    apply_native_page_scroll_theme,
    info_button_stylesheet,
    muted_hint_html,
    panel_content_html,
    refresh_native_text_edits_in,
    settings_stale_banner_stylesheet,
    status_color_stylesheet,
)


_settings_dialog: SettingsDialog | None = None

_QUICK_FOLDER_ROW_TEXT_MIN_HEIGHT = 32
_QUICK_FOLDER_ROW_TEXT_MAX_HEIGHT = 120
_QUICK_FOLDER_AFTER_BUTTONS_SPACING = 12


class _ChatExportQuickFolderRow(NamedTuple):
    host: QWidget
    checkbox: QCheckBox
    label_input: ScrollAwareTextEdit
    path_input: ScrollAwareTextEdit

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
    button.setAutoDefault(False)
    button.setDefault(False)


def _set_dialog_default_button(button: QPushButton | None) -> None:
    """Assign dialog default (Enter) to one visible footer button."""
    if button is not None:
        button.setAutoDefault(True)
        button.setDefault(True)


class SettingsDialog(QDialog):
    def __init__(self, parent, config: dict[str, Any]):
        super().__init__(parent)
        self._config = config
        self.config = dict(config)
        self._restore_checkboxes: dict[str, QCheckBox] = {}
        self._warning_restore_checkboxes: dict[str, QCheckBox] = {}
        self._default_action_combos: dict[str, Any] = {}
        self._all_restore_checked = True
        self._all_warnings_checked = False
        self._model_refresh_busy = False
        self._settings_help_dialog = None
        self._chat_prompt_cache_dialog: ChatPromptCacheDialog | None = None
        self._optimize_prompt_inspection_window: PromptInspectionWindow | None = None
        self._force_shutdown = False
        self.silentlyClose = True
        self.setWindowModality(Qt.WindowModality.NonModal)

        self.setWindowTitle(tr("settings.title", config=config))
        configure_snappable_window(self)
        self.setMinimumSize(680, 420)
        self.resize(780, 760)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        self.stack = QStackedWidget(self)
        self.stack.addWidget(self._build_form_page())
        self.stack.addWidget(self._build_restore_page())
        self.stack.addWidget(self._build_restore_warnings_page())
        self.stack.addWidget(self._build_advanced_page())
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
        self.btn_restore_warnings = QPushButton(tr("settings.warnings", config=config), self)
        self.btn_restore_warnings.clicked.connect(self._enter_restore_warnings_mode)
        _setup_footer_button(
            self.btn_restore_warnings,
            tooltip=tr("settings.warnings", config=config),
        )
        self.btn_settings_help = QPushButton(tr("settings.info", config=config), self)
        self.btn_settings_help.clicked.connect(self._open_settings_help)
        _setup_footer_button(
            self.btn_settings_help,
            tooltip=tr("settings.info", config=config),
        )
        self.btn_advanced = QPushButton(tr("settings.advanced", config=config), self)
        self.btn_advanced.clicked.connect(self._enter_advanced_mode)
        _setup_footer_button(
            self.btn_advanced,
            tooltip=tr("settings.advanced.title", config=config),
        )
        utility_row.addWidget(self.btn_restore_mode)
        utility_row.addWidget(self.btn_restore_warnings)
        utility_row.addWidget(self.btn_advanced)
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
        self.btn_cancel.clicked.connect(self._cancel_and_reject)
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
        self.btn_check_dismissed_warnings = QPushButton(
            tr("settings.warnings.check_dismissed", config=config), self
        )
        self.btn_check_dismissed_warnings.clicked.connect(self._check_all_dismissed_warning_restores)
        _setup_footer_button(
            self.btn_check_dismissed_warnings,
            tooltip=tr("settings.warnings.check_dismissed", config=config),
        )
        self.btn_warnings_toggle_all = QPushButton(tr("settings.restore.toggle_all", config=config), self)
        self.btn_warnings_toggle_all.clicked.connect(self._toggle_all_warning_restore_checks)
        _setup_footer_button(
            self.btn_warnings_toggle_all,
            tooltip=tr("settings.restore.toggle_all", config=config),
        )
        self.btn_apply_warning_restore = QPushButton(tr("settings.warnings.apply", config=config), self)
        self.btn_apply_warning_restore.clicked.connect(self._apply_selected_warning_restores)
        _setup_footer_button(
            self.btn_apply_warning_restore,
            tooltip=tr("settings.warnings.apply", config=config),
        )
        self.btn_warnings_back = QPushButton(tr("settings.restore.back", config=config), self)
        self.btn_warnings_back.clicked.connect(self._leave_restore_warnings_mode)
        _setup_footer_button(
            self.btn_warnings_back,
            tooltip=tr("settings.restore.back", config=config),
        )
        self._warnings_btn_layout.addWidget(self.btn_check_dismissed_warnings)
        self._warnings_btn_layout.addWidget(self.btn_warnings_toggle_all)
        self._warnings_btn_layout.addStretch(1)
        self._warnings_btn_layout.addWidget(self.btn_apply_warning_restore)
        self._warnings_btn_layout.addWidget(self.btn_warnings_back)
        root.addLayout(self._warnings_btn_layout)

        self._advanced_btn_layout = QHBoxLayout()
        self._advanced_btn_layout.setSpacing(8)
        self.btn_advanced_back = QPushButton(tr("settings.restore.back", config=config), self)
        self.btn_advanced_back.clicked.connect(self._leave_advanced_mode)
        _setup_footer_button(
            self.btn_advanced_back,
            tooltip=tr("settings.restore.back", config=config),
        )
        self._advanced_btn_layout.addStretch(1)
        self._advanced_btn_layout.addWidget(self.btn_advanced_back)
        root.addLayout(self._advanced_btn_layout)

        self._default_footer_buttons = (
            self.btn_save,
            self.btn_apply_restore,
            self.btn_apply_warning_restore,
            self.btn_advanced_back,
        )

        self._set_subpage_mode(None)
        self._baseline_config = self._collect_pending_config()
        self._wire_settings_preset_dirty_watchers()
        self._refresh_settings_preset_dirty_state()
        refresh_settings_text_edit_newlines(
            self,
            bool(self.config.get("settings_show_text_newlines", False)),
        )
        refresh_text_edit_wrap(
            self,
            bool(self.config.get("settings_wrap_text_editors", True)),
        )
        QTimer.singleShot(0, lambda: refresh_settings_text_edit_layouts(self))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, lambda: refresh_settings_text_edit_layouts(self))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        # Height-only resizes are often caused by auto-height fields; remasuring
        # every editor then feeds another resize loop. Only reflow on width change.
        if event.size().width() != event.oldSize().width():
            QTimer.singleShot(0, lambda: refresh_settings_text_edit_layouts(self))

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._force_shutdown:
            super().closeEvent(event)
            return
        if not self._confirm_close_if_needed():
            event.ignore()
            return
        super().closeEvent(event)

    def reject(self) -> None:
        if self._force_shutdown:
            super().reject()
            return
        if not self._confirm_cancel_if_needed():
            return
        super().reject()

    def force_shutdown(self) -> None:
        self._force_shutdown = True
        if self._settings_help_dialog is not None:
            self._settings_help_dialog.close()
            self._settings_help_dialog = None
        if self._chat_prompt_cache_dialog is not None:
            self._chat_prompt_cache_dialog.close()
            self._chat_prompt_cache_dialog = None
        self.reject()

    def _build_form_page(self) -> QWidget:
        config = self.config
        page = QWidget(self)
        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        apply_native_page_scroll_theme(scroll, allow_horizontal_scroll=False)

        form_host = QWidget(scroll)
        form_host.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(form_host)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel(f"<b>{tr('settings.language', config=config)}</b>"))
        language_shell, self.language_combo = create_settings_combo(form_host)
        self.language_combo.addItem(tr("settings.language.it", config=config), LANG_IT)
        self.language_combo.addItem(tr("settings.language.en", config=config), LANG_EN)
        current_lang = (self.config.get("language") or DEFAULT_LANGUAGE).lower()
        index = self.language_combo.findData(LANG_EN if current_lang.startswith("en") else LANG_IT)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        layout.addWidget(language_shell)

        layout.addWidget(QLabel(f"<br><b>{tr('settings.api_key', config=config)}</b>"))
        saved_key = (self.config.get("api_key") or "").strip()
        self._saved_api_key = saved_key
        self.api_key_status = QLabel(form_host)
        self._update_api_key_status()
        layout.addWidget(self.api_key_status)
        api_key_shell, self.api_key_input = create_settings_line_edit(form_host)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        if saved_key:
            self.api_key_input.setPlaceholderText(tr("settings.api_key.placeholder.saved", config=config))
        else:
            self.api_key_input.setPlaceholderText(tr("settings.api_key.placeholder.empty", config=config))
        layout.addWidget(api_key_shell)

        layout.addWidget(
            create_settings_hint_label(
                form_host,
                tr(
                    "settings.api_cost_tracking",
                    config=config,
                    billing_url=GEMINI_AI_STUDIO_BILLING_URL,
                    usage_url=GEMINI_AI_STUDIO_USAGE_URL,
                ),
            )
        )

        layout.addWidget(QLabel(f"<br><b>{tr('settings.model_optimize', config=config)}</b>"))
        optimize_row = QHBoxLayout()
        model_optimize_shell, self.model_optimize_input = create_model_selector(
            form_host,
            current=self.config.get("model_optimize", DEFAULT_MODEL_OPTIMIZE),
            default=DEFAULT_MODEL_OPTIMIZE,
            config=config,
        )
        optimize_row.addWidget(model_optimize_shell)
        self.btn_refresh_optimize_models = QPushButton(tr("settings.model.refresh", config=config), form_host)
        self.btn_refresh_optimize_models.setAutoDefault(False)
        self.btn_refresh_optimize_models.setDefault(False)
        self.btn_refresh_optimize_models.clicked.connect(self._refresh_models_from_api)
        optimize_row.addWidget(self.btn_refresh_optimize_models)
        optimize_row.addStretch(1)
        layout.addLayout(optimize_row)

        layout.addWidget(QLabel(f"<b>{tr('settings.model_chat', config=config)}</b>"))
        chat_row = QHBoxLayout()
        model_chat_shell, self.model_chat_input = create_model_selector(
            form_host,
            current=self.config.get("model_chat", DEFAULT_MODEL_CHAT),
            default=DEFAULT_MODEL_CHAT,
            config=config,
        )
        chat_row.addWidget(model_chat_shell)
        self.btn_refresh_chat_models = QPushButton(tr("settings.model.refresh", config=config), form_host)
        self.btn_refresh_chat_models.setAutoDefault(False)
        self.btn_refresh_chat_models.setDefault(False)
        self.btn_refresh_chat_models.clicked.connect(self._refresh_models_from_api)
        chat_row.addWidget(self.btn_refresh_chat_models)
        chat_row.addStretch(1)
        layout.addLayout(chat_row)

        self.thinking_budget_hint = create_settings_hint_label(
            form_host,
            tr("settings.thinking_budget.hint", config=config),
        )
        layout.addWidget(self.thinking_budget_hint)
        thinking_optimize_shell, self.thinking_budget_optimize_input = create_settings_spinbox(form_host)
        self.thinking_budget_optimize_input.setRange(-1, 24576)
        self.thinking_budget_optimize_input.setValue(
            int(self.config.get("thinking_budget_optimize", DEFAULT_THINKING_BUDGET_OPTIMIZE))
        )
        add_settings_labeled_field(
            layout,
            form_host,
            tr("settings.thinking_budget_optimize", config=config),
            thinking_optimize_shell,
        )

        thinking_chat_shell, self.thinking_budget_chat_input = create_settings_spinbox(form_host)
        self.thinking_budget_chat_input.setRange(-1, 24576)
        self.thinking_budget_chat_input.setValue(
            int(self.config.get("thinking_budget_chat", DEFAULT_THINKING_BUDGET_CHAT))
        )
        add_settings_labeled_field(
            layout,
            form_host,
            tr("settings.thinking_budget_chat", config=config),
            thinking_chat_shell,
        )

        timeout_shell, self.timeout_input = create_settings_spinbox(form_host)
        self.timeout_input.setRange(5, 120)
        self.timeout_input.setValue(int(self.config.get("timeout_seconds", 30)))
        add_settings_labeled_field(
            layout,
            form_host,
            tr("settings.timeout", config=config),
            timeout_shell,
        )

        retries_shell, self.retries_input = create_settings_spinbox(form_host)
        self.retries_input.setRange(0, 5)
        self.retries_input.setValue(int(self.config.get("max_retries", 2)))
        add_settings_labeled_field(
            layout,
            form_host,
            tr("settings.max_retry", config=config),
            retries_shell,
        )

        history_shell, self.history_input = create_settings_spinbox(form_host)
        self.history_input.setRange(0, 100)
        self.history_input.setValue(int(self.config.get("max_history_turns", 10)))
        add_settings_labeled_field(
            layout,
            form_host,
            tr("settings.chat_history", config=config),
            history_shell,
        )

        token_warn_shell, self.chat_payload_warning_input = create_settings_spinbox(form_host)
        self.chat_payload_warning_input.setRange(1, 2_000_000)
        self.chat_payload_warning_input.setSingleStep(1000)
        self.chat_payload_warning_input.setValue(
            int(self.config.get("chat_payload_warning_chars", 12000))
        )
        add_settings_labeled_field(
            layout,
            form_host,
            tr("settings.chat_payload_warning_chars", config=config),
            token_warn_shell,
        )

        apply_hist_shell, self.chat_apply_history_max_input = create_settings_spinbox(
            form_host
        )
        self.chat_apply_history_max_input.setRange(1, 30)
        self.chat_apply_history_max_input.setValue(
            int(self.config.get("chat_apply_history_max", 7))
        )
        add_settings_labeled_field(
            layout,
            form_host,
            tr("settings.chat_apply_history_max", config=config),
            apply_hist_shell,
        )

        temp_optimize_shell, self.temp_optimize_input = create_settings_double_spinbox(form_host)
        self.temp_optimize_input.setRange(0.0, 2.0)
        self.temp_optimize_input.setSingleStep(0.1)
        self.temp_optimize_input.setValue(float(self.config.get("temperature_optimize", 0.1)))
        add_settings_labeled_field(
            layout,
            form_host,
            tr("settings.temp_optimize", config=config),
            temp_optimize_shell,
        )

        temp_chat_shell, self.temp_chat_input = create_settings_double_spinbox(form_host)
        self.temp_chat_input.setRange(0.0, 2.0)
        self.temp_chat_input.setSingleStep(0.1)
        self.temp_chat_input.setValue(float(self.config.get("temperature_chat", 0.2)))
        add_settings_labeled_field(
            layout,
            form_host,
            tr("settings.temp_chat", config=config),
            temp_chat_shell,
        )

        self.confirm_checkbox = QCheckBox(tr("settings.confirm_preview", config=config), form_host)
        self.confirm_checkbox.setChecked(bool(self.config.get("confirm_before_apply", True)))
        layout.addWidget(self.confirm_checkbox)

        self.chat_streaming_checkbox = QCheckBox(tr("settings.chat_streaming", config=config), form_host)
        self.chat_streaming_checkbox.setChecked(bool(self.config.get("chat_streaming", True)))
        layout.addWidget(self.chat_streaming_checkbox)

        layout.addWidget(
            create_settings_section_label(
                form_host,
                tr("settings.chat_export_quick_folders", config=config),
            )
        )
        layout.addWidget(
            create_settings_hint_label(
                form_host,
                tr("settings.chat_export_quick_folders.hint", config=config),
            )
        )
        self._chat_export_quick_folder_rows: list[_ChatExportQuickFolderRow] = []
        self._chat_export_quick_folders_container = QWidget(form_host)
        self._chat_export_quick_folders_layout = QVBoxLayout(self._chat_export_quick_folders_container)
        self._chat_export_quick_folders_layout.setContentsMargins(0, 0, 0, 0)
        self._chat_export_quick_folders_layout.setSpacing(6)
        layout.addWidget(self._chat_export_quick_folders_container)
        quick_folder_btn_row = QHBoxLayout()
        self.chat_export_quick_folder_add_btn = QPushButton(
            tr("settings.chat_export_quick_folders.add", config=config),
            form_host,
        )
        self.chat_export_quick_folder_add_btn.clicked.connect(
            self._add_chat_export_quick_folder_row
        )
        self.chat_export_quick_folder_remove_btn = QPushButton(
            tr("settings.chat_export_quick_folders.remove", config=config),
            form_host,
        )
        self.chat_export_quick_folder_remove_btn.clicked.connect(
            self._remove_chat_export_quick_folder_row
        )
        quick_folder_btn_row.addWidget(self.chat_export_quick_folder_add_btn)
        quick_folder_btn_row.addWidget(self.chat_export_quick_folder_remove_btn)
        quick_folder_btn_row.addStretch(1)
        layout.addLayout(quick_folder_btn_row)
        layout.addSpacing(_QUICK_FOLDER_AFTER_BUTTONS_SPACING)

        self.show_text_newlines_checkbox = QCheckBox(
            tr("settings.show_text_newlines", config=config),
            form_host,
        )
        self.show_text_newlines_checkbox.setChecked(
            bool(self.config.get("settings_show_text_newlines", False))
        )
        self.show_text_newlines_checkbox.toggled.connect(self._on_show_text_newlines_toggled)
        layout.addWidget(self.show_text_newlines_checkbox)
        self.show_text_newlines_hint = create_settings_hint_label(
            form_host,
            tr("settings.show_text_newlines.hint", config=config),
        )
        layout.addWidget(self.show_text_newlines_hint)

        self.wrap_text_editors_checkbox = QCheckBox(
            tr("settings.wrap_text_editors", config=config),
            form_host,
        )
        self.wrap_text_editors_checkbox.setChecked(
            bool(self.config.get("settings_wrap_text_editors", True))
        )
        self.wrap_text_editors_checkbox.toggled.connect(self._on_wrap_text_editors_toggled)
        layout.addWidget(self.wrap_text_editors_checkbox)
        self.wrap_text_editors_hint = create_settings_hint_label(
            form_host,
            tr("settings.wrap_text_editors.hint", config=config),
        )
        layout.addWidget(self.wrap_text_editors_hint)

        self._load_chat_export_quick_folder_rows(
            normalize_chat_export_quick_folders(
                self.config.get("chat_export_quick_folders")
            )
        )
        self._sync_chat_export_quick_folder_buttons()

        self.btn_inspect_optimize_prompt = QPushButton(
            tr("settings.inspect_optimize_prompt", config=config),
            form_host,
        )
        self.btn_inspect_optimize_prompt.setAutoDefault(False)
        self.btn_inspect_optimize_prompt.setDefault(False)
        self.btn_inspect_optimize_prompt.clicked.connect(self._open_optimize_prompt_inspection)
        layout.addWidget(self.btn_inspect_optimize_prompt)

        brain_message_title = QLabel(form_host)
        brain_message_title.setTextFormat(Qt.TextFormat.RichText)
        brain_message_title.setText(
            instruction_html(f"<br><b>{tr('settings.brain_message', config=config)}</b>")
        )
        layout.addWidget(brain_message_title)
        self.brain_message_hint = create_settings_hint_label(
            form_host,
            tr("settings.brain_message.hint", config=config),
        )
        layout.addWidget(self.brain_message_hint)
        brain_shell, self.brain_message_input = create_settings_auto_height_text_edit(
            form_host,
            show_newlines=self.show_text_newlines_checkbox.isChecked(),
            wrap=self.wrap_text_editors_checkbox.isChecked(),
        )
        self.brain_message_input.setPlainText(effective_brain_import_message(self.config))
        adjust = getattr(self.brain_message_input, "_auto_height_adjust", None)
        if adjust is not None:
            adjust()
        layout.addWidget(brain_shell)

        self._settings_presets_title = QLabel(
            f"<br><b>{tr('settings.presets', config=config)}</b>",
            form_host,
        )
        layout.addWidget(self._settings_presets_title)
        self._settings_presets_hint = create_settings_hint_label(
            form_host,
            tr("settings.presets.hint", config=config),
        )
        layout.addWidget(self._settings_presets_hint)

        preset_combo_shell, self.settings_preset_combo = create_settings_combo(form_host)
        self.settings_preset_combo.currentIndexChanged.connect(self._on_settings_preset_changed)
        add_settings_stacked_field(
            layout,
            form_host,
            tr("settings.presets.active", config=config),
            preset_combo_shell,
        )

        self.settings_presets_include_dynamic_checkbox = QCheckBox(
            tr("settings.presets.include_dynamic", config=config),
            form_host,
        )
        self.settings_presets_include_dynamic_checkbox.setChecked(False)
        self.settings_presets_include_dynamic_checkbox.toggled.connect(
            self._refresh_settings_preset_dirty_state
        )
        layout.addWidget(self.settings_presets_include_dynamic_checkbox)

        self.settings_presets_include_runtime_checkbox = QCheckBox(
            tr("settings.presets.include_runtime", config=config),
            form_host,
        )
        self.settings_presets_include_runtime_checkbox.setChecked(False)
        self.settings_presets_include_runtime_checkbox.toggled.connect(
            self._refresh_settings_preset_dirty_state
        )
        layout.addWidget(self.settings_presets_include_runtime_checkbox)

        self.settings_presets_dirty_label = create_settings_hint_label(form_host, "")
        self.settings_presets_dirty_label.setVisible(False)
        layout.addWidget(self.settings_presets_dirty_label)

        preset_btn_row = QHBoxLayout()
        preset_btn_row.setSpacing(SETTINGS_SECTION_GAP)
        self.settings_presets_save_as_btn = QPushButton(
            tr("settings.presets.save_as", config=config),
            form_host,
        )
        self.settings_presets_save_as_btn.clicked.connect(self._save_settings_preset_as)
        self.settings_presets_update_btn = QPushButton(
            tr("settings.presets.update", config=config),
            form_host,
        )
        self.settings_presets_update_btn.clicked.connect(self._update_settings_preset)
        self.settings_presets_duplicate_btn = QPushButton(
            tr("settings.presets.duplicate", config=config),
            form_host,
        )
        self.settings_presets_duplicate_btn.clicked.connect(self._duplicate_settings_preset)
        self.settings_presets_rename_btn = QPushButton(
            tr("settings.presets.rename", config=config),
            form_host,
        )
        self.settings_presets_rename_btn.clicked.connect(self._rename_settings_preset)
        self.settings_presets_delete_btn = QPushButton(
            tr("settings.presets.delete", config=config),
            form_host,
        )
        self.settings_presets_delete_btn.clicked.connect(self._delete_settings_preset)
        preset_btn_row.addWidget(self.settings_presets_save_as_btn)
        preset_btn_row.addWidget(self.settings_presets_update_btn)
        preset_btn_row.addWidget(self.settings_presets_duplicate_btn)
        preset_btn_row.addWidget(self.settings_presets_rename_btn)
        preset_btn_row.addWidget(self.settings_presets_delete_btn)
        preset_btn_row.addStretch(1)
        layout.addLayout(preset_btn_row)

        preset_io_row = QHBoxLayout()
        preset_io_row.setSpacing(SETTINGS_SECTION_GAP)
        self.settings_presets_preview_btn = QPushButton(
            tr("settings.presets.preview", config=config),
            form_host,
        )
        self.settings_presets_preview_btn.clicked.connect(self._preview_settings_preset)
        self.settings_presets_export_btn = QPushButton(
            tr("settings.presets.export", config=config),
            form_host,
        )
        self.settings_presets_export_btn.clicked.connect(self._export_settings_presets)
        self.settings_presets_export_selected_btn = QPushButton(
            tr("settings.presets.export_selected", config=config),
            form_host,
        )
        self.settings_presets_export_selected_btn.clicked.connect(
            self._export_selected_settings_preset
        )
        self.settings_presets_import_btn = QPushButton(
            tr("settings.presets.import", config=config),
            form_host,
        )
        self.settings_presets_import_btn.clicked.connect(self._import_settings_presets)
        preset_io_row.addWidget(self.settings_presets_preview_btn)
        preset_io_row.addWidget(self.settings_presets_export_btn)
        preset_io_row.addWidget(self.settings_presets_export_selected_btn)
        preset_io_row.addWidget(self.settings_presets_import_btn)
        preset_io_row.addStretch(1)
        layout.addLayout(preset_io_row)

        self._settings_presets = clone_settings_presets(config)
        self._active_settings_preset_id = resolve_active_settings_preset_id(
            config,
            self._settings_presets,
        )
        self._settings_preset_loading = False
        self._rebuild_settings_preset_combo(select_id=self._active_settings_preset_id)
        self._refresh_settings_preset_actions()

        layout.addWidget(QLabel(f"<br><b>{tr('settings.system_instruction', config=config)}</b>"))
        self.system_instruction_subtitle = create_settings_hint_label(
            form_host,
            tr("settings.system_instruction.subtitle", config=config),
        )
        layout.addWidget(self.system_instruction_subtitle)
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
        instruction_shell, self.instruction_input = create_settings_auto_height_text_edit(
            self.instruction_shared_host,
            show_newlines=self.show_text_newlines_checkbox.isChecked(),
            wrap=self.wrap_text_editors_checkbox.isChecked(),
        )
        shared_instruction_layout.addWidget(instruction_shell)

        self.instruction_split_host = QWidget(form_host)
        split_instruction_layout = QVBoxLayout(self.instruction_split_host)
        split_instruction_layout.setContentsMargins(0, 0, 0, 0)
        self.instruction_optimize_label = QLabel(
            f"<b>{tr('settings.system_instruction_optimize', config=config)}</b>",
            self.instruction_split_host,
        )
        split_instruction_layout.addWidget(self.instruction_optimize_label)
        self.instruction_optimize_subtitle = create_settings_hint_label(
            self.instruction_split_host,
            tr("settings.system_instruction_optimize.subtitle", config=config),
        )
        split_instruction_layout.addWidget(self.instruction_optimize_subtitle)
        optimize_shell, self.instruction_optimize_input = create_settings_auto_height_text_edit(
            self.instruction_split_host,
            show_newlines=self.show_text_newlines_checkbox.isChecked(),
            wrap=self.wrap_text_editors_checkbox.isChecked(),
        )
        split_instruction_layout.addWidget(optimize_shell)
        self.instruction_chat_label = QLabel(
            f"<b>{tr('settings.system_instruction_chat', config=config)}</b>",
            self.instruction_split_host,
        )
        split_instruction_layout.addWidget(self.instruction_chat_label)
        self.instruction_chat_subtitle = create_settings_hint_label(
            self.instruction_split_host,
            tr("settings.system_instruction_chat.subtitle", config=config),
        )
        split_instruction_layout.addWidget(self.instruction_chat_subtitle)
        chat_instr_shell, self.instruction_chat_input = create_settings_auto_height_text_edit(
            self.instruction_split_host,
            show_newlines=self.show_text_newlines_checkbox.isChecked(),
            wrap=self.wrap_text_editors_checkbox.isChecked(),
        )
        split_instruction_layout.addWidget(chat_instr_shell)

        layout.addWidget(self.instruction_shared_host)
        layout.addWidget(self.instruction_split_host)
        self._load_instruction_fields_from_config()
        self._sync_instruction_widgets_visibility()

        layout.addWidget(
            QLabel(f"<br><b>{tr('settings.dynamic_instructions', config=config)}</b>")
        )
        self.dynamic_instructions_hint = create_settings_hint_label(
            form_host,
            tr("settings.dynamic_instructions.hint", config=config),
        )
        layout.addWidget(self.dynamic_instructions_hint)
        dynamic_shell, self.dynamic_input = create_settings_auto_height_text_edit(
            form_host,
            show_newlines=self.show_text_newlines_checkbox.isChecked(),
            wrap=self.wrap_text_editors_checkbox.isChecked(),
        )
        self.dynamic_input.setPlaceholderText(tr("settings.dynamic_placeholder", config=config))
        self.dynamic_input.setPlainText(self.config.get("dynamic_instructions", ""))
        adjust = getattr(self.dynamic_input, "_auto_height_adjust", None)
        if adjust is not None:
            adjust()
        layout.addWidget(dynamic_shell)

        layout.addWidget(QLabel(f"<br><b>{tr('settings.shortcuts', config=config)}</b>"))
        self.shortcuts_panel_shell = create_settings_panel(
            form_host,
            panel_content_html(tr("settings.shortcuts.body", config=config)),
        )
        self.shortcuts_panel = self.shortcuts_panel_shell._settings_panel_label
        layout.addWidget(self.shortcuts_panel_shell)

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
        apply_native_page_scroll_theme(scroll, allow_horizontal_scroll=False)

        host = QWidget(scroll)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel(f"<b>{tr('settings.restore.title', config=config)}</b>"))
        self.restore_hint_label = create_settings_hint_label(
            host,
            tr("settings.restore.hint", config=config),
        )
        layout.addWidget(self.restore_hint_label)
        self.chat_cache_restore_hint_label = create_settings_hint_label(
            host,
            tr("settings.restore.chat_cache.hint", config=config),
        )
        self.chat_cache_restore_hint_label.setOpenExternalLinks(False)
        self.chat_cache_restore_hint_label.linkActivated.connect(
            self._on_restore_chat_cache_link_activated
        )
        layout.addWidget(self.chat_cache_restore_hint_label)
        layout.addWidget(QLabel("<br>"))

        self._restore_checkboxes.clear()
        restore_list_host = QWidget(host)
        restore_list_layout = QVBoxLayout(restore_list_host)
        restore_list_layout.setContentsMargins(0, 0, 0, 0)
        restore_list_layout.setSpacing(4)
        for key in RESTORABLE_SETTING_KEYS:
            label_key = RESTORABLE_SETTING_LABELS.get(key, key)
            checkbox = QCheckBox(host)
            checkbox.setChecked(key != "api_key")
            restore_list_layout.addWidget(
                create_settings_restore_checkbox_row(
                    restore_list_host,
                    checkbox,
                    label_key,
                    config=config,
                )
            )
            self._restore_checkboxes[key] = checkbox

        layout.addWidget(restore_list_host)

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
        apply_native_page_scroll_theme(scroll, allow_horizontal_scroll=False)

        host = QWidget(scroll)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel(f"<b>{tr('settings.warnings.title', config=config)}</b>"))
        self.restore_warnings_hint_label = create_settings_hint_label(
            host,
            tr("settings.warnings.hint", config=config),
        )
        layout.addWidget(self.restore_warnings_hint_label)
        layout.addWidget(QLabel("<br>"))

        self._warning_restore_checkboxes.clear()
        for key in DISMISSIBLE_WARNING_KEYS:
            label_key = DISMISSIBLE_WARNING_LABELS.get(key, key)
            checkbox = QCheckBox(tr(label_key, config=config), host)
            checkbox.setChecked(False)
            layout.addWidget(checkbox)
            self._warning_restore_checkboxes[key] = checkbox

        add_settings_section_break(layout)
        layout.addWidget(
            QLabel(f"<b>{tr('warnings.default_actions.title', config=config)}</b>")
        )
        layout.addWidget(
            create_settings_hint_label(
                host,
                tr("warnings.default_actions.hint", config=config),
            )
        )
        self._default_action_combos.clear()
        for config_key, label_key, values in DEFAULT_ACTION_SETTINGS:
            combo_shell, combo = create_settings_combo(host)
            for value in values:
                option_key = f"{label_key}.{value}"
                combo.addItem(tr(option_key, config=config), value)
            current = str(self.config.get(config_key) or values[0])
            index = combo.findData(current)
            combo.setCurrentIndex(index if index >= 0 else 0)
            add_settings_labeled_field(
                layout,
                host,
                tr(label_key, config=config),
                combo_shell,
            )
            self._default_action_combos[config_key] = combo

        layout.addStretch(1)
        scroll.setWidget(host)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        return page

    def _build_advanced_page(self) -> QWidget:
        config = self.config
        page = QWidget(self)
        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        apply_native_page_scroll_theme(scroll, allow_horizontal_scroll=False)

        host = QWidget(scroll)
        host.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(SETTINGS_SECTION_INNER_SPACING)

        layout.addWidget(create_settings_section_label(host, tr("settings.advanced.title", config=config)))
        layout.addWidget(
            create_settings_hint_label(host, tr("settings.advanced.hint", config=config))
        )
        add_settings_section_break(layout)

        layout.addWidget(create_settings_section_label(host, tr("settings.prompt_optimize_user", config=config)))
        layout.addWidget(
            create_settings_hint_label(host, tr("settings.prompt_optimize_user.hint", config=config))
        )
        optimize_prompt_shell, self.prompt_optimize_user_input = create_settings_auto_height_text_edit(
            host,
            show_newlines=self.show_text_newlines_checkbox.isChecked(),
            wrap=self.wrap_text_editors_checkbox.isChecked(),
        )
        self.prompt_optimize_user_input.setPlainText(effective_optimize_user_prompt(config))
        layout.addWidget(optimize_prompt_shell)

        add_settings_section_break(layout)
        layout.addWidget(create_settings_section_label(host, tr("settings.prompt_chat_addon", config=config)))
        layout.addWidget(
            create_settings_hint_label(host, tr("settings.prompt_chat_addon.hint", config=config))
        )
        chat_addon_shell, self.prompt_chat_addon_input = create_settings_auto_height_text_edit(
            host,
            show_newlines=self.show_text_newlines_checkbox.isChecked(),
            wrap=self.wrap_text_editors_checkbox.isChecked(),
        )
        self.prompt_chat_addon_input.setPlainText(effective_chat_system_addon(config))
        layout.addWidget(chat_addon_shell)

        add_settings_section_break(layout)
        layout.addWidget(
            create_settings_section_label(host, tr("settings.prompt_dynamic_rules_prefix", config=config))
        )
        layout.addWidget(
            create_settings_hint_label(
                host,
                tr("settings.prompt_dynamic_rules_prefix.hint", config=config),
            )
        )
        dynamic_prefix_shell, self.prompt_dynamic_rules_prefix_input = create_settings_auto_height_text_edit(
            host,
            show_newlines=self.show_text_newlines_checkbox.isChecked(),
            wrap=self.wrap_text_editors_checkbox.isChecked(),
        )
        self.prompt_dynamic_rules_prefix_input.setPlainText(effective_dynamic_rules_prefix(config))
        layout.addWidget(dynamic_prefix_shell)

        add_settings_section_break(layout)
        wrapper_title_row = QWidget(host)
        apply_settings_icon_row_height(wrapper_title_row)
        wrapper_header = QHBoxLayout(wrapper_title_row)
        wrapper_header.setContentsMargins(0, 0, 0, 0)
        wrapper_header.setSpacing(SETTINGS_SECTION_INNER_SPACING)
        row_align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        self._wrapper_context_label = QLabel(
            f"<b>{tr('settings.prompt_chat_context', config=config)}</b>",
            wrapper_title_row,
        )
        self._wrapper_context_label.setContentsMargins(0, 0, 0, 0)
        self._wrapper_context_label.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Preferred,
        )
        wrapper_header.addWidget(self._wrapper_context_label, 0, row_align)
        self.btn_wrapper_context_help = _make_info_button(wrapper_title_row, config)
        self.btn_wrapper_context_help.clicked.connect(self._open_wrapper_context_help)
        wrapper_header.addWidget(self.btn_wrapper_context_help, 0, row_align)
        wrapper_header.addStretch(1)
        layout.addWidget(wrapper_title_row)
        layout.addWidget(
            create_settings_hint_label(host, tr("settings.prompt_chat_context.hint", config=config))
        )

        self.wrapper_sections_editor = WrapperSectionsEditor(
            host,
            show_newlines=self.show_text_newlines_checkbox.isChecked(),
            wrap=self.wrap_text_editors_checkbox.isChecked(),
        )
        self.wrapper_sections_editor.load_from_config(config)
        layout.addWidget(self.wrapper_sections_editor)

        add_settings_section_break(layout)
        layout.addWidget(
            create_settings_section_label(host, tr("settings.mathjax_preview_preamble", config=config))
        )
        layout.addWidget(
            create_settings_hint_label(
                host,
                tr("settings.mathjax_preview_preamble.hint", config=config),
            )
        )
        preamble_shell, self.mathjax_preview_preamble_input = create_settings_auto_height_text_edit(
            host,
            show_newlines=self.show_text_newlines_checkbox.isChecked(),
            wrap=self.wrap_text_editors_checkbox.isChecked(),
        )
        self.mathjax_preview_preamble_input.setPlainText(effective_mathjax_preview_preamble(config))
        layout.addWidget(preamble_shell)

        add_settings_section_break(layout)
        layout.addWidget(
            create_settings_section_label(
                host,
                tr("settings.prompt_cache.section.optimize", config=config),
            )
        )
        layout.addWidget(
            create_settings_hint_label(
                host,
                tr("settings.prompt_cache.hint.optimize", config=config),
            )
        )
        self.chat_prompt_cache_summary_label = create_settings_hint_label(
            host,
            chat_prompt_cache_summary(config),
        )
        layout.addWidget(self.chat_prompt_cache_summary_label)
        self.btn_open_chat_prompt_cache_settings = QPushButton(
            tr("settings.prompt_cache.open_chat_settings", config=config),
            host,
        )
        self.btn_open_chat_prompt_cache_settings.clicked.connect(
            self._open_chat_prompt_cache_settings
        )
        layout.addWidget(self.btn_open_chat_prompt_cache_settings)

        self.prompt_cache_enabled_optimize_checkbox = QCheckBox(
            tr("settings.prompt_cache_enabled_optimize", config=config),
            host,
        )
        self.prompt_cache_enabled_optimize_checkbox.setChecked(
            bool(config.get("prompt_cache_enabled_optimize", False))
        )
        layout.addWidget(self.prompt_cache_enabled_optimize_checkbox)

        self.optimize_modify_prompt_checkbox = QCheckBox(
            tr("settings.optimize_modify_prompt_before_send", config=config),
            host,
        )
        self.optimize_modify_prompt_checkbox.setChecked(
            bool(config.get("optimize_modify_prompt_before_send", False))
        )
        layout.addWidget(self.optimize_modify_prompt_checkbox)
        layout.addWidget(
            create_settings_hint_label(
                host,
                tr("settings.optimize_modify_prompt_before_send.hint", config=config),
            )
        )

        ttl_row = QHBoxLayout()
        ttl_row.addWidget(QLabel(tr("settings.prompt_cache_ttl", config=config), host))
        ttl_shell, self.prompt_cache_ttl_input = create_settings_spinbox(host)
        self.prompt_cache_ttl_input.setRange(60, 7 * 24 * 3600)
        self.prompt_cache_ttl_input.setSingleStep(300)
        self.prompt_cache_ttl_input.setValue(
            int(config.get("prompt_cache_ttl_seconds_optimize", 3600))
        )
        ttl_row.addWidget(ttl_shell)
        ttl_row.addStretch(1)
        layout.addLayout(ttl_row)

        min_row = QHBoxLayout()
        min_row.addWidget(QLabel(tr("settings.prompt_cache_min_chars", config=config), host))
        min_chars_shell, self.prompt_cache_min_chars_input = create_settings_spinbox(host)
        self.prompt_cache_min_chars_input.setRange(256, 1_000_000)
        self.prompt_cache_min_chars_input.setValue(
            int(config.get("prompt_cache_min_chars_optimize", DEFAULT_PROMPT_CACHE_MIN_CHARS))
        )
        min_row.addWidget(min_chars_shell)
        min_row.addStretch(1)
        layout.addLayout(min_row)

        self.prompt_cache_status_label = QLabel(host)
        layout.addWidget(self.prompt_cache_status_label)

        change_ttl_row = QHBoxLayout()
        change_ttl_row.addWidget(
            QLabel(tr("settings.prompt_cache.change_ttl_seconds", config=config), host)
        )
        change_ttl_shell, self.prompt_cache_change_ttl_input = create_settings_spinbox(host)
        self.prompt_cache_change_ttl_input.setRange(60, 7 * 24 * 3600)
        self.prompt_cache_change_ttl_input.setSingleStep(300)
        self.prompt_cache_change_ttl_input.setValue(
            int(config.get("prompt_cache_change_ttl_seconds", 3600))
        )
        change_ttl_row.addWidget(change_ttl_shell)
        change_ttl_row.addStretch(1)
        layout.addLayout(change_ttl_row)

        cache_btn_row = QHBoxLayout()
        self.prompt_cache_change_ttl_btn = QPushButton(
            tr("settings.prompt_cache.change_ttl", config=config),
            host,
        )
        self.prompt_cache_change_ttl_btn.clicked.connect(self._change_prompt_cache_ttl)
        self.prompt_cache_clear_optimize_btn = QPushButton(
            tr("settings.prompt_cache.clear_optimize", config=config),
            host,
        )
        self.prompt_cache_clear_optimize_btn.clicked.connect(self._clear_optimize_prompt_cache)
        self.prompt_cache_clear_btn = QPushButton(tr("settings.prompt_cache.clear", config=config), host)
        self.prompt_cache_clear_btn.clicked.connect(self._clear_prompt_cache)
        self.prompt_cache_manage_btn = QPushButton(tr("settings.prompt_cache.manage", config=config), host)
        self.prompt_cache_manage_btn.clicked.connect(self._open_prompt_cache_manager)
        cache_btn_row.addWidget(self.prompt_cache_change_ttl_btn)
        cache_btn_row.addWidget(self.prompt_cache_clear_optimize_btn)
        cache_btn_row.addWidget(self.prompt_cache_clear_btn)
        cache_btn_row.addWidget(self.prompt_cache_manage_btn)
        cache_btn_row.addStretch(1)
        layout.addLayout(cache_btn_row)

        add_settings_section_break(layout)
        layout.addWidget(
            create_settings_section_label(host, tr("settings.prompt_cache_segments", config=config))
        )
        layout.addWidget(
            create_settings_hint_label(
                host,
                tr("settings.prompt_cache_segments.hint", config=config),
            )
        )
        segments = prompt_cache_segments(config, "optimize")
        self.prompt_cache_segment_checkboxes: dict[str, QCheckBox] = {}
        for segment_id in PROMPT_CACHE_OPTIMIZE_USER_SEGMENT_ORDER:
            label = tr(segment_label_key(segment_id), config=config)
            checkbox = QCheckBox(label, host)
            checkbox.setChecked(bool(segments.get(segment_id, False)))

            if segment_id == "system_instruction":
                info_btn = _make_info_button(host, config)
                wire_info_button_explanation(
                    info_btn,
                    config=config,
                    message_key="settings.prompt_cache.system_instruction_cache_info",
                )
                layout.addWidget(create_settings_checkbox_info_row(host, checkbox, info_btn))
                self._prompt_cache_system_instruction_info_btn = info_btn
            else:
                layout.addWidget(checkbox)

            self.prompt_cache_segment_checkboxes[segment_id] = checkbox

        add_settings_section_break(layout)
        layout.addWidget(
            create_settings_section_label(host, tr("settings.prompt_cache_custom_text", config=config))
        )
        layout.addWidget(
            create_settings_hint_label(
                host,
                tr("settings.prompt_cache_custom_text.hint", config=config),
            )
        )
        preset_combo_shell, self.prompt_cache_preset_combo = create_settings_combo(host)
        self.prompt_cache_preset_combo.addItem(
            tr("settings.prompt_cache_presets.manual", config=config),
            "",
        )
        for preset in normalize_custom_text_presets(config.get("prompt_cache_custom_text_presets")):
            if preset.get("optimize"):
                self.prompt_cache_preset_combo.addItem(
                    str(preset.get("name") or ""),
                    str(preset.get("id") or ""),
                )
        active_id = str(config.get("prompt_cache_active_preset_id_optimize") or "")
        active_index = self.prompt_cache_preset_combo.findData(active_id)
        self.prompt_cache_preset_combo.setCurrentIndex(active_index if active_index >= 0 else 0)
        self.prompt_cache_preset_combo.currentIndexChanged.connect(
            self._on_prompt_cache_preset_changed
        )
        add_settings_stacked_field(
            layout,
            host,
            tr("settings.prompt_cache_presets.active", config=config),
            preset_combo_shell,
        )

        custom_cache_shell, self.prompt_cache_custom_text_input = create_settings_auto_height_text_edit(
            host,
            show_newlines=self.show_text_newlines_checkbox.isChecked(),
            wrap=self.wrap_text_editors_checkbox.isChecked(),
        )
        self.prompt_cache_custom_text_input.setPlainText(
            (config.get("prompt_cache_custom_text_optimize") or "").strip()
        )
        layout.addWidget(custom_cache_shell)
        custom_cache_btn_row = QHBoxLayout()
        self.prompt_cache_custom_text_load_btn = QPushButton(
            tr("settings.prompt_cache_custom_text.load_file", config=config),
            host,
        )
        self.prompt_cache_custom_text_load_btn.clicked.connect(
            self._load_prompt_cache_custom_text_from_file
        )
        custom_cache_btn_row.addWidget(self.prompt_cache_custom_text_load_btn)
        custom_cache_btn_row.addStretch(1)
        layout.addLayout(custom_cache_btn_row)

        name_shell, self.prompt_cache_preset_name_input = create_settings_line_edit(host)
        add_settings_stacked_field(
            layout,
            host,
            tr("settings.prompt_cache_presets.name", config=config),
            name_shell,
        )

        self.prompt_cache_preset_chat_checkbox = QCheckBox(
            tr("settings.prompt_cache_presets.for_chat", config=config),
            host,
        )
        self.prompt_cache_preset_optimize_checkbox = QCheckBox(
            tr("settings.prompt_cache_presets.for_optimize", config=config),
            host,
        )
        preset_checks_row = QHBoxLayout()
        preset_checks_row.setSpacing(SETTINGS_SECTION_GAP)
        preset_checks_row.addWidget(self.prompt_cache_preset_chat_checkbox)
        preset_checks_row.addWidget(self.prompt_cache_preset_optimize_checkbox)
        preset_checks_row.addStretch(1)
        layout.addLayout(preset_checks_row)

        preset_btn_row = QHBoxLayout()
        self.prompt_cache_preset_add_btn = QPushButton(
            tr("settings.prompt_cache_presets.add", config=config),
            host,
        )
        self.prompt_cache_preset_add_btn.clicked.connect(self._add_prompt_cache_preset)
        self.prompt_cache_preset_remove_btn = QPushButton(
            tr("settings.prompt_cache_presets.remove", config=config),
            host,
        )
        self.prompt_cache_preset_remove_btn.clicked.connect(self._remove_prompt_cache_preset)
        preset_btn_row.addWidget(self.prompt_cache_preset_add_btn)
        preset_btn_row.addWidget(self.prompt_cache_preset_remove_btn)
        preset_btn_row.addStretch(1)
        layout.addLayout(preset_btn_row)
        self._prompt_cache_presets: list[dict[str, Any]] = clone_presets(config)
        self._manual_custom_cache_text = (
            (config.get("prompt_cache_custom_text_optimize") or "").strip()
        )
        self._sync_prompt_cache_preset_fields()

        billing_link = QLabel(host)
        billing_link.setTextFormat(Qt.TextFormat.RichText)
        billing_link.setOpenExternalLinks(True)
        billing_link.setWordWrap(True)
        billing_link.setText(
            muted_hint_html(
                tr(
                    "settings.prompt_cache.billing_link",
                    config=config,
                    billing_url=GEMINI_AI_STUDIO_BILLING_URL,
                )
            )
        )
        layout.addWidget(billing_link)

        self._refresh_prompt_cache_status()

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

    def _open_wrapper_context_help(self) -> None:
        if self._settings_help_dialog is not None and self._settings_help_dialog.isVisible():
            self._settings_help_dialog.show_detail("prompt_chat_context")
            self._settings_help_dialog.raise_()
            self._settings_help_dialog.activateWindow()
            return

        help_config = self._wrapper_warning_config()
        self._settings_help_dialog = open_settings_help_dialog(
            self,
            help_config,
            detail_key="prompt_chat_context",
        )
        self._settings_help_dialog.finished.connect(self._on_settings_help_closed)

    def _wrapper_warning_config(self) -> dict[str, Any]:
        config = dict(self.config)
        config.update(self._ui_config())
        return config

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
        if hasattr(self, "system_instruction_subtitle"):
            self.system_instruction_subtitle.setText(
                muted_hint_html(tr("settings.system_instruction.subtitle", config=config))
            )
        if hasattr(self, "instruction_optimize_label"):
            self.instruction_optimize_label.setText(
                f"<b>{tr('settings.system_instruction_optimize', config=config)}</b>"
            )
        if hasattr(self, "instruction_optimize_subtitle"):
            self.instruction_optimize_subtitle.setText(
                muted_hint_html(tr("settings.system_instruction_optimize.subtitle", config=config))
            )
        if hasattr(self, "instruction_chat_label"):
            self.instruction_chat_label.setText(
                f"<b>{tr('settings.system_instruction_chat', config=config)}</b>"
            )
        if hasattr(self, "instruction_chat_subtitle"):
            self.instruction_chat_subtitle.setText(
                muted_hint_html(tr("settings.system_instruction_chat.subtitle", config=config))
            )
        self.dynamic_instructions_hint.setText(
            muted_hint_html(tr("settings.dynamic_instructions.hint", config=config))
        )
        self.show_text_newlines_checkbox.setText(
            tr("settings.show_text_newlines", config=config)
        )
        self.show_text_newlines_hint.setText(
            muted_hint_html(tr("settings.show_text_newlines.hint", config=config))
        )
        self.wrap_text_editors_checkbox.setText(
            tr("settings.wrap_text_editors", config=config)
        )
        self.wrap_text_editors_hint.setText(
            muted_hint_html(tr("settings.wrap_text_editors.hint", config=config))
        )
        self.shortcuts_panel.setText(
            panel_content_html(tr("settings.shortcuts.body", config=config))
        )
        self.restore_hint_label.setText(
            muted_hint_html(tr("settings.restore.hint", config=config))
        )
        if hasattr(self, "chat_cache_restore_hint_label"):
            self.chat_cache_restore_hint_label.setText(
                muted_hint_html(tr("settings.restore.chat_cache.hint", config=config))
            )
        if hasattr(self, "btn_open_chat_prompt_cache_settings"):
            self.btn_open_chat_prompt_cache_settings.setText(
                tr("settings.prompt_cache.open_chat_settings", config=config)
            )
        if hasattr(self, "chat_prompt_cache_summary_label"):
            self.chat_prompt_cache_summary_label.setText(chat_prompt_cache_summary(config))
        self.restore_warnings_hint_label.setText(
            muted_hint_html(tr("settings.warnings.hint", config=config))
        )
        refresh_native_text_edits_in(self)
        refresh_settings_text_edit_layouts(self)
        if hasattr(self, "wrapper_sections_editor"):
            self.wrapper_sections_editor.refresh_layout()
        self._update_api_key_status()
        if hasattr(self, "btn_wrapper_context_help"):
            self.btn_wrapper_context_help.setStyleSheet(info_button_stylesheet())
        if hasattr(self, "_prompt_cache_system_instruction_info_btn"):
            self._prompt_cache_system_instruction_info_btn.setStyleSheet(
                info_button_stylesheet()
            )
            refresh_info_button_explanation(
                self._prompt_cache_system_instruction_info_btn,
                config=config,
                message_key="settings.prompt_cache.system_instruction_cache_info",
            )
        if self._settings_help_dialog is not None:
            self._settings_help_dialog.apply_theme()

    def _default_system_instruction_text(self) -> str:
        lang = self.language_combo.currentData() or DEFAULT_LANGUAGE
        return tr("defaults.system_instruction", lang=lang)

    def _set_instruction_field_text(self, editor: ScrollAwareTextEdit, text: str) -> None:
        editor.setPlainText(text)
        editor.clear_text_selection()
        adjust = getattr(editor, "_auto_height_adjust", None)
        if adjust is not None:
            adjust()

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
        on_advanced = mode == "advanced"

        self.btn_restore_mode.setVisible(on_form)
        self.btn_restore_warnings.setVisible(on_form)
        self.btn_advanced.setVisible(on_form)
        self.btn_settings_help.setVisible(on_form)
        self.btn_save.setVisible(on_form)
        self.btn_cancel.setVisible(on_form)

        self.btn_toggle_all.setVisible(on_defaults)
        self.btn_apply_restore.setVisible(on_defaults)
        self.btn_restore_back.setVisible(on_defaults)

        self.btn_check_dismissed_warnings.setVisible(on_warnings)
        self.btn_warnings_toggle_all.setVisible(on_warnings)
        self.btn_apply_warning_restore.setVisible(on_warnings)
        self.btn_warnings_back.setVisible(on_warnings)

        self.btn_advanced_back.setVisible(on_advanced)

        for button in self._default_footer_buttons:
            button.setAutoDefault(False)
            button.setDefault(False)

        if on_form:
            _set_dialog_default_button(self.btn_save)
        elif on_defaults:
            _set_dialog_default_button(self.btn_apply_restore)
        elif on_warnings:
            _set_dialog_default_button(self.btn_apply_warning_restore)
        elif on_advanced:
            _set_dialog_default_button(self.btn_advanced_back)

    def _refresh_warning_restore_checkboxes(self) -> None:
        for checkbox in self._warning_restore_checkboxes.values():
            checkbox.setChecked(False)

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
            self.config[dismiss_config_key] = True

        return True

    def _collect_pending_config(self) -> dict[str, Any]:
        config = dict(self.config)
        new_key = self.api_key_input.text().strip()
        config["language"] = self.language_combo.currentData() or DEFAULT_LANGUAGE
        config["api_key"] = new_key if new_key else self._saved_api_key
        config["model_optimize"] = model_selector_value(self.model_optimize_input) or DEFAULT_MODEL_OPTIMIZE
        config["model_chat"] = model_selector_value(self.model_chat_input) or DEFAULT_MODEL_CHAT
        config["thinking_budget_optimize"] = self.thinking_budget_optimize_input.value()
        config["thinking_budget_chat"] = self.thinking_budget_chat_input.value()
        config["chat_streaming"] = self.chat_streaming_checkbox.isChecked()
        config["chat_export_quick_folders"] = normalize_chat_export_quick_folders(
            self._collect_chat_export_quick_folders_from_ui()
        )
        config.pop("chat_prompt_inspection", None)
        config.pop("model", None)
        config.pop("thinking_budget", None)
        config["timeout_seconds"] = self.timeout_input.value()
        config["max_retries"] = self.retries_input.value()
        config["max_history_turns"] = self.history_input.value()
        config["chat_payload_warning_chars"] = self.chat_payload_warning_input.value()
        config["chat_apply_history_max"] = self.chat_apply_history_max_input.value()
        config["temperature_optimize"] = self.temp_optimize_input.value()
        config["temperature_chat"] = self.temp_chat_input.value()
        config["confirm_before_apply"] = self.confirm_checkbox.isChecked()
        config["settings_show_text_newlines"] = self.show_text_newlines_checkbox.isChecked()
        config["settings_wrap_text_editors"] = self.wrap_text_editors_checkbox.isChecked()
        brain_message = self.brain_message_input.toPlainText().strip()
        config["brain_import_message"] = normalize_brain_import_message_for_save(
            brain_message, config
        )
        instruction_fields = normalize_system_instruction_fields_for_save(
            shared=self.instruction_shared_checkbox.isChecked(),
            shared_text=self.instruction_input.toPlainText(),
            optimize_text=self.instruction_optimize_input.toPlainText(),
            chat_text=self.instruction_chat_input.toPlainText(),
            config=config,
        )
        config.update(instruction_fields)
        config["dynamic_instructions"] = self.dynamic_input.toPlainText()
        config["prompt_optimize_user"] = normalize_optimize_user_prompt_for_save(
            self.prompt_optimize_user_input.toPlainText()
        )
        config["prompt_chat_addon"] = normalize_chat_system_addon_for_save(
            self.prompt_chat_addon_input.toPlainText()
        )
        config["prompt_dynamic_rules_prefix"] = normalize_dynamic_rules_prefix_for_save(
            self.prompt_dynamic_rules_prefix_input.toPlainText()
        )
        order, sections, format_guide = self.wrapper_sections_editor.collect()
        config["prompt_chat_context_order"] = normalize_wrapper_order_for_save(order)
        config["prompt_chat_context_sections"] = normalize_wrapper_sections_for_save(
            sections,
            config=config,
        )
        config["prompt_chat_context"] = ""
        config["prompt_card_templates_format"] = normalize_card_templates_format_prompt_for_save(
            format_guide
        )
        config["mathjax_preview_preamble"] = normalize_mathjax_preview_preamble_for_save(
            self.mathjax_preview_preamble_input.toPlainText()
        )
        config["prompt_cache_enabled_optimize"] = (
            self.prompt_cache_enabled_optimize_checkbox.isChecked()
        )
        config["prompt_cache_ttl_seconds_optimize"] = self.prompt_cache_ttl_input.value()
        config["prompt_cache_min_chars_optimize"] = self.prompt_cache_min_chars_input.value()
        self._commit_prompt_cache_preset_editor()
        config["prompt_cache_custom_text_optimize"] = (
            self.prompt_cache_custom_text_input.toPlainText().strip()
        )
        config["prompt_cache_custom_text_presets"] = normalize_custom_text_presets(
            self._prompt_cache_presets
        )
        config["prompt_cache_active_preset_id_optimize"] = str(
            self.prompt_cache_preset_combo.currentData() or ""
        )
        config["settings_presets"] = normalize_settings_presets(self._settings_presets)
        config["active_settings_preset_id"] = str(
            self.settings_preset_combo.currentData() or BUILTIN_SETTINGS_PRESET_ID
        )
        config["prompt_cache_change_ttl_seconds"] = self.prompt_cache_change_ttl_input.value()
        config["optimize_modify_prompt_before_send"] = (
            self.optimize_modify_prompt_checkbox.isChecked()
        )
        config["prompt_cache_segments_optimize"] = {
            segment_id: checkbox.isChecked()
            for segment_id, checkbox in self.prompt_cache_segment_checkboxes.items()
        }
        for config_key, combo in self._default_action_combos.items():
            value = combo.currentData()
            if value is not None:
                config[config_key] = value
        for key in DISMISSIBLE_WARNING_KEYS:
            config[key] = bool(config.get(key, False))
        return config

    def _has_unsaved_changes(self) -> bool:
        return self._collect_pending_config() != self._baseline_config

    def _confirm_close_if_needed(self) -> bool:
        if not self._has_unsaved_changes():
            return True
        if is_warning_dismissed(self.config, "suppress_settings_unsaved_close_warning"):
            return True
        return self._confirm_dismissible_warning(
            title_key="settings.unsaved_close.title",
            message_key="settings.unsaved_close.message",
            detail_key="settings.unsaved_close.detail",
            dismiss_config_key="suppress_settings_unsaved_close_warning",
        )

    def _confirm_cancel_if_needed(self) -> bool:
        if not self._has_unsaved_changes():
            return True
        if is_warning_dismissed(self.config, "suppress_settings_cancel_confirm_warning"):
            return True
        return self._confirm_dismissible_warning(
            title_key="settings.cancel_confirm.title",
            message_key="settings.cancel_confirm.message",
            detail_key="settings.cancel_confirm.detail",
            dismiss_config_key="suppress_settings_cancel_confirm_warning",
        )

    def _confirm_save_if_needed(self) -> bool:
        if not self._has_unsaved_changes():
            return True
        pending = self._collect_pending_config()
        affected = purposes_requiring_cache_invalidation(self._baseline_config, pending)
        active = [
            purpose
            for purpose in affected
            if get_prompt_cache_store(purpose).active is not None
        ]
        if active and not is_warning_dismissed(
            self.config,
            "suppress_settings_save_cache_clear_warning",
        ):
            if not self._confirm_save_cache_clear(active, pending):
                return False
        if is_warning_dismissed(self.config, "suppress_settings_save_confirm_warning"):
            return True
        return self._confirm_dismissible_warning(
            title_key="settings.save_confirm.title",
            message_key="settings.save_confirm.message",
            detail_key="settings.save_confirm.detail",
            dismiss_config_key="suppress_settings_save_confirm_warning",
        )

    def _confirm_save_cache_clear(
        self,
        purposes: list[str],
        config: dict[str, Any],
    ) -> bool:
        purpose_labels = ", ".join(
            tr(f"settings.prompt_cache.manager.purpose.{purpose}", config=config)
            for purpose in purposes
        )
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr("settings.save_cache_clear.title", config=config))
        box.setText(
            tr(
                "settings.save_cache_clear.message",
                config=config,
                purposes=purpose_labels,
            )
        )
        box.setInformativeText(tr("settings.save_cache_clear.detail", config=config))
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
            updated["suppress_settings_save_cache_clear_warning"] = True
            save_config(updated)
            self.config["suppress_settings_save_cache_clear_warning"] = True
        return True

    def _cancel_and_reject(self) -> None:
        self.reject()

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
        self._all_warnings_checked = False
        for config_key, combo in self._default_action_combos.items():
            current = str(self.config.get(config_key) or combo.itemData(0))
            index = combo.findData(current)
            combo.setCurrentIndex(index if index >= 0 else 0)
        self.stack.setCurrentIndex(2)
        self._set_subpage_mode("warnings")
        QTimer.singleShot(0, lambda: refresh_settings_text_edit_layouts(self))

    def _leave_restore_warnings_mode(self) -> None:
        self.stack.setCurrentIndex(0)
        self._set_subpage_mode(None)

    def _enter_advanced_mode(self) -> None:
        self.stack.setCurrentIndex(3)
        self._refresh_prompt_cache_status()
        self._set_subpage_mode("advanced")
        page = self.stack.currentWidget()
        QTimer.singleShot(
            0,
            lambda: refresh_settings_text_edit_layouts(page if page is not None else self),
        )

    def _leave_advanced_mode(self) -> None:
        self.stack.setCurrentIndex(0)
        self._set_subpage_mode(None)

    def _check_all_dismissed_warning_restores(self) -> None:
        dismissed = dismissed_warning_keys(self.config)
        if not dismissed:
            showInfo(tr("settings.restore_warnings.none_dismissed", config=self._ui_config()))
            return
        for key, checkbox in self._warning_restore_checkboxes.items():
            checkbox.setChecked(key in dismissed)
        self._all_warnings_checked = len(dismissed) == len(DISMISSIBLE_WARNING_KEYS)

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

        if key == "chat_export_quick_folders":
            self._load_chat_export_quick_folder_rows(
                normalize_chat_export_quick_folders(default_value)
            )
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

        if key == "chat_payload_warning_chars":
            self.chat_payload_warning_input.setValue(int(default_value))
            return

        if key == "chat_apply_history_max":
            self.chat_apply_history_max_input.setValue(int(default_value))
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

        if key == "brain_import_templates":
            self.config["brain_import_templates"] = bool(default_value)
            return

        if key == "brain_import_css":
            self.config["brain_import_css"] = bool(default_value)
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

        if key == "prompt_optimize_user":
            lang = self.language_combo.currentData() or DEFAULT_LANGUAGE
            self.prompt_optimize_user_input.setPlainText(
                default_optimize_user_prompt({"language": lang})
            )
            return

        if key == "prompt_chat_addon":
            lang = self.language_combo.currentData() or DEFAULT_LANGUAGE
            self.prompt_chat_addon_input.setPlainText(
                default_chat_system_addon({"language": lang})
            )
            return

        if key == "prompt_dynamic_rules_prefix":
            lang = self.language_combo.currentData() or DEFAULT_LANGUAGE
            self.prompt_dynamic_rules_prefix_input.setPlainText(
                default_dynamic_rules_prefix({"language": lang})
            )
            return

        if key in {"prompt_chat_context", "prompt_chat_context_order", "prompt_chat_context_sections"}:
            lang = self.language_combo.currentData() or DEFAULT_LANGUAGE
            self.wrapper_sections_editor.load_from_config(
                {
                    "language": lang,
                    "prompt_chat_context_order": default_wrapper_section_order(),
                    "prompt_chat_context_sections": {},
                    "prompt_card_templates_format": "",
                }
            )
            return

        if key == "prompt_card_templates_format":
            # Reset only the format guide. Keep the editor's current order/sections so
            # a later restore of this key (checked by default after the wrapper keys)
            # does not undo a just-applied default wrapper layout.
            lang = self.language_combo.currentData() or DEFAULT_LANGUAGE
            order, sections, _current_guide = self.wrapper_sections_editor.collect()
            self.wrapper_sections_editor.load_from_config(
                {
                    "language": lang,
                    "prompt_chat_context_order": order,
                    "prompt_chat_context_sections": sections,
                    "prompt_card_templates_format": "",
                }
            )
            return

        if key == "mathjax_preview_preamble":
            self.mathjax_preview_preamble_input.setPlainText("")
            return
        if key == "prompt_cache_enabled_optimize":
            self.prompt_cache_enabled_optimize_checkbox.setChecked(bool(default_value))
            return
        if key == "prompt_cache_ttl_seconds_optimize":
            self.prompt_cache_ttl_input.setValue(int(default_value))
            return
        if key == "prompt_cache_min_chars_optimize":
            self.prompt_cache_min_chars_input.setValue(int(default_value))
            return
        if key == "prompt_cache_custom_text_optimize":
            self.prompt_cache_custom_text_input.setPlainText("")
            return
        if key == "prompt_cache_segments_optimize":
            defaults = default_config_value("prompt_cache_segments_optimize")
            for segment_id, checkbox in self.prompt_cache_segment_checkboxes.items():
                checkbox.setChecked(bool(defaults.get(segment_id, False)))
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
        for key in selected:
            self.config[key] = False

        for config_key, combo in self._default_action_combos.items():
            value = combo.currentData()
            if value is not None:
                self.config[config_key] = value
                self._baseline_config[config_key] = value

        save_config(self.config)
        self._refresh_warning_restore_checkboxes()
        self._leave_restore_warnings_mode()

    def _on_wrap_text_editors_toggled(self, checked: bool) -> None:
        if hasattr(self, "wrapper_sections_editor"):
            self.wrapper_sections_editor.set_wrap(checked)
        refresh_text_edit_wrap(self, checked)
        if (
            self._optimize_prompt_inspection_window is not None
            and self._optimize_prompt_inspection_window.isVisible()
        ):
            refresh_text_edit_wrap(self._optimize_prompt_inspection_window, checked)
        refresh_settings_text_edit_layouts(self)

    def _on_show_text_newlines_toggled(self, checked: bool) -> None:
        if hasattr(self, "wrapper_sections_editor"):
            self.wrapper_sections_editor.set_show_newlines(checked)
        refresh_settings_text_edit_newlines(self, checked)
        if (
            self._optimize_prompt_inspection_window is not None
            and self._optimize_prompt_inspection_window.isVisible()
        ):
            refresh_settings_text_edit_newlines(
                self._optimize_prompt_inspection_window, checked
            )

    def _wire_settings_preset_dirty_watchers(self) -> None:
        widgets = [
            getattr(self, name, None)
            for name in (
                "instruction_input",
                "instruction_optimize_input",
                "instruction_chat_input",
                "dynamic_input",
                "brain_message_input",
                "prompt_optimize_user_input",
                "prompt_chat_addon_input",
                "prompt_dynamic_rules_prefix_input",
                "mathjax_preview_preamble_input",
                "instruction_shared_checkbox",
                "thinking_budget_optimize_input",
                "thinking_budget_chat_input",
                "temp_optimize_input",
                "temp_chat_input",
            )
        ]
        for widget in widgets:
            if widget is None:
                continue
            if hasattr(widget, "textChanged"):
                widget.textChanged.connect(self._refresh_settings_preset_dirty_state)
            elif hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self._refresh_settings_preset_dirty_state)
            elif hasattr(widget, "toggled"):
                widget.toggled.connect(self._refresh_settings_preset_dirty_state)
        editor = getattr(self, "wrapper_sections_editor", None)
        if editor is not None and hasattr(editor, "connect_text_changed"):
            editor.connect_text_changed(self._refresh_settings_preset_dirty_state)
        for name in ("model_optimize_input", "model_chat_input"):
            combo = getattr(self, name, None)
            if combo is not None and hasattr(combo, "currentTextChanged"):
                combo.currentTextChanged.connect(self._refresh_settings_preset_dirty_state)

    def _selected_settings_preset_id(self) -> str:
        return str(self.settings_preset_combo.currentData() or BUILTIN_SETTINGS_PRESET_ID)

    def _rebuild_settings_preset_combo(self, *, select_id: str = "") -> None:
        config = self._ui_config()
        self._settings_preset_loading = True
        self.settings_preset_combo.blockSignals(True)
        self.settings_preset_combo.clear()
        self.settings_preset_combo.addItem(
            tr("settings.presets.builtin", config=config),
            BUILTIN_SETTINGS_PRESET_ID,
        )
        for preset in self._settings_presets:
            self.settings_preset_combo.addItem(
                str(preset.get("name") or ""),
                str(preset.get("id") or ""),
            )
        target = select_id or self._active_settings_preset_id
        index = self.settings_preset_combo.findData(target)
        self.settings_preset_combo.setCurrentIndex(index if index >= 0 else 0)
        self.settings_preset_combo.blockSignals(False)
        self._settings_preset_loading = False
        self._active_settings_preset_id = self._selected_settings_preset_id()
        self._sync_include_checkboxes_from_active_preset()
        self._refresh_settings_preset_actions()
        self._refresh_settings_preset_dirty_state()

    def _active_settings_preset_payload(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        return resolve_preset_payload(
            self._settings_presets,
            self._selected_settings_preset_id(),
        )

    def _sync_include_checkboxes_from_active_preset(self) -> None:
        values, runtime = self._active_settings_preset_payload()
        self.settings_presets_include_dynamic_checkbox.blockSignals(True)
        self.settings_presets_include_runtime_checkbox.blockSignals(True)
        self.settings_presets_include_dynamic_checkbox.setChecked(
            "dynamic_instructions" in values
        )
        self.settings_presets_include_runtime_checkbox.setChecked(runtime is not None)
        self.settings_presets_include_dynamic_checkbox.blockSignals(False)
        self.settings_presets_include_runtime_checkbox.blockSignals(False)

    def _current_form_prompt_pack(self, *, include_dynamic: bool | None = None) -> dict[str, Any]:
        if include_dynamic is None:
            include_dynamic = self.settings_presets_include_dynamic_checkbox.isChecked()
        pending = self._collect_pending_config()
        return collect_prompt_pack_from_config(pending, include_dynamic=include_dynamic)

    def _current_form_runtime_pack(self) -> dict[str, Any]:
        pending = self._collect_pending_config()
        return collect_runtime_pack_from_config(pending)

    def _form_matches_active_preset(self) -> bool:
        active_values, active_runtime = self._active_settings_preset_payload()
        include_dynamic = (
            "dynamic_instructions" in active_values
            or self.settings_presets_include_dynamic_checkbox.isChecked()
        )
        current_values = self._current_form_prompt_pack(include_dynamic=include_dynamic)
        if "dynamic_instructions" not in active_values and not (
            self.settings_presets_include_dynamic_checkbox.isChecked()
        ):
            current_values = {
                key: value
                for key, value in current_values.items()
                if key != "dynamic_instructions"
            }
            active_values = {
                key: value
                for key, value in active_values.items()
                if key != "dynamic_instructions"
            }
        if not prompt_pack_values_equal(current_values, active_values):
            return False
        include_runtime = (
            active_runtime is not None
            or self.settings_presets_include_runtime_checkbox.isChecked()
        )
        if not include_runtime:
            return True
        if active_runtime is None:
            return False
        current_runtime = self._current_form_runtime_pack()
        return runtime_pack_values_equal(current_runtime, active_runtime)

    def _refresh_settings_preset_dirty_state(self) -> None:
        if not hasattr(self, "settings_presets_dirty_label"):
            return
        if not hasattr(self, "wrapper_sections_editor"):
            return
        if not hasattr(self, "_baseline_config"):
            return
        if getattr(self, "_settings_preset_loading", False):
            return
        config = self._ui_config()
        dirty = not self._form_matches_active_preset()
        self.settings_presets_dirty_label.setVisible(dirty)
        if dirty:
            self.settings_presets_dirty_label.setText(
                muted_hint_html(tr("settings.presets.dirty", config=config))
            )
        self._refresh_settings_preset_actions()

    def _refresh_settings_preset_actions(self) -> None:
        if not hasattr(self, "settings_presets_update_btn"):
            return
        preset_id = self._selected_settings_preset_id()
        is_builtin = preset_id == BUILTIN_SETTINGS_PRESET_ID
        self.settings_presets_update_btn.setEnabled(not is_builtin)
        self.settings_presets_rename_btn.setEnabled(not is_builtin)
        self.settings_presets_delete_btn.setEnabled(not is_builtin)
        at_cap = len(self._settings_presets) >= MAX_SETTINGS_PRESETS
        self.settings_presets_save_as_btn.setEnabled(not at_cap)
        self.settings_presets_duplicate_btn.setEnabled(not at_cap)
        self.settings_presets_export_btn.setEnabled(bool(self._settings_presets))
        self.settings_presets_export_selected_btn.setEnabled(not is_builtin)

    def _apply_runtime_pack_to_form(self, runtime: dict[str, Any] | None) -> None:
        if runtime is None:
            self.settings_presets_include_runtime_checkbox.setChecked(False)
            return
        self.settings_presets_include_runtime_checkbox.setChecked(True)
        set_model_selector_value(
            self.model_optimize_input,
            str(runtime.get("model_optimize") or DEFAULT_MODEL_OPTIMIZE),
        )
        set_model_selector_value(
            self.model_chat_input,
            str(runtime.get("model_chat") or DEFAULT_MODEL_CHAT),
        )
        self.thinking_budget_optimize_input.setValue(
            int(runtime.get("thinking_budget_optimize", DEFAULT_THINKING_BUDGET_OPTIMIZE))
        )
        self.thinking_budget_chat_input.setValue(
            int(runtime.get("thinking_budget_chat", DEFAULT_THINKING_BUDGET_CHAT))
        )
        self.temp_optimize_input.setValue(float(runtime.get("temperature_optimize", 0.1)))
        self.temp_chat_input.setValue(float(runtime.get("temperature_chat", 0.2)))

    def _apply_prompt_pack_values_to_form(
        self,
        values: dict[str, Any],
        runtime: dict[str, Any] | None = None,
        *,
        apply_runtime: bool = True,
    ) -> None:
        lang = self.language_combo.currentData() or DEFAULT_LANGUAGE
        pack = dict(values)
        pack["language"] = lang
        shared = bool(pack.get("system_instruction_shared", True))
        self.instruction_shared_checkbox.setChecked(shared)
        self._sync_instruction_widgets_visibility()
        self._set_instruction_field_text(
            self.instruction_input,
            effective_system_instruction(pack, purpose="optimize"),
        )
        self._set_instruction_field_text(
            self.instruction_optimize_input,
            effective_system_instruction(pack, purpose="optimize"),
        )
        self._set_instruction_field_text(
            self.instruction_chat_input,
            effective_system_instruction(pack, purpose="chat"),
        )
        self.brain_message_input.setPlainText(effective_brain_import_message(pack))
        if hasattr(self, "prompt_optimize_user_input"):
            self.prompt_optimize_user_input.setPlainText(effective_optimize_user_prompt(pack))
        if hasattr(self, "prompt_chat_addon_input"):
            self.prompt_chat_addon_input.setPlainText(effective_chat_system_addon(pack))
        if hasattr(self, "prompt_dynamic_rules_prefix_input"):
            self.prompt_dynamic_rules_prefix_input.setPlainText(
                effective_dynamic_rules_prefix(pack)
            )
        if hasattr(self, "wrapper_sections_editor"):
            self.wrapper_sections_editor.load_from_config(pack)
        if hasattr(self, "mathjax_preview_preamble_input"):
            self.mathjax_preview_preamble_input.setPlainText(
                effective_mathjax_preview_preamble(pack)
            )
        if "dynamic_instructions" in values:
            self.dynamic_input.setPlainText(str(values.get("dynamic_instructions") or ""))
            self.settings_presets_include_dynamic_checkbox.setChecked(True)
        else:
            self.settings_presets_include_dynamic_checkbox.setChecked(False)
        if apply_runtime:
            self._apply_runtime_pack_to_form(runtime)

    def _preset_display_name(self, preset_id: str) -> str:
        config = self._ui_config()
        if preset_id == BUILTIN_SETTINGS_PRESET_ID:
            return tr("settings.presets.builtin", config=config)
        preset = find_settings_preset(self._settings_presets, preset_id)
        if preset is None:
            return tr("settings.presets.builtin", config=config)
        return str(preset.get("name") or preset_id[:8])

    def _confirm_load_settings_preset(self, preset_id: str) -> bool:
        config = self._ui_config()
        values, runtime = resolve_preset_payload(self._settings_presets, preset_id)
        diffs = preset_diff_from_builtin(values, runtime, config=config)
        name = self._preset_display_name(preset_id)
        if not diffs:
            summary = tr("settings.presets.preview.matches_default", config=config)
        else:
            summary = "\n".join(f"• {line}" for line in diffs[:12])
            if len(diffs) > 12:
                summary += "\n" + tr(
                    "settings.presets.preview.more",
                    config=config,
                    count=len(diffs) - 12,
                )
        dirty = not self._form_matches_active_preset()
        message = tr(
            "settings.presets.load.message",
            config=config,
            name=name,
        )
        if dirty:
            message = (
                tr("settings.presets.load.dirty_warning", config=config)
                + "\n\n"
                + message
            )
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(tr("settings.presets.load.title", config=config))
        box.setText(message)
        box.setInformativeText(summary)
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        return box.exec() == QMessageBox.StandardButton.Yes

    def _on_settings_preset_changed(self) -> None:
        if self._settings_preset_loading:
            return
        preset_id = self._selected_settings_preset_id()
        previous_id = self._active_settings_preset_id
        if preset_id == previous_id:
            return
        if not self._confirm_load_settings_preset(preset_id):
            self._settings_preset_loading = True
            self.settings_preset_combo.blockSignals(True)
            index = self.settings_preset_combo.findData(previous_id)
            self.settings_preset_combo.setCurrentIndex(index if index >= 0 else 0)
            self.settings_preset_combo.blockSignals(False)
            self._settings_preset_loading = False
            return
        self._active_settings_preset_id = preset_id
        values, runtime = resolve_preset_payload(self._settings_presets, preset_id)
        self._settings_preset_loading = True
        try:
            self._apply_prompt_pack_values_to_form(values, runtime, apply_runtime=True)
        finally:
            self._settings_preset_loading = False
        self._refresh_settings_preset_actions()
        self._refresh_settings_preset_dirty_state()
        QTimer.singleShot(0, lambda: refresh_settings_text_edit_layouts(self))

    def _build_preset_from_form(self, *, name: str) -> dict[str, Any]:
        values = self._current_form_prompt_pack()
        runtime = None
        if self.settings_presets_include_runtime_checkbox.isChecked():
            runtime = self._current_form_runtime_pack()
        return new_settings_preset(name=name, values=values, runtime=runtime)

    def _save_settings_preset_as(self) -> None:
        config = self._ui_config()
        if len(self._settings_presets) >= MAX_SETTINGS_PRESETS:
            showWarning(
                tr(
                    "settings.presets.limit",
                    config=config,
                    max=MAX_SETTINGS_PRESETS,
                )
            )
            return
        name, ok = QInputDialog.getText(
            self,
            tr("settings.presets.save_as", config=config),
            tr("settings.presets.name_prompt", config=config),
        )
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        preset = self._build_preset_from_form(name=name)
        self._settings_presets.append(preset)
        self._rebuild_settings_preset_combo(select_id=preset["id"])

    def _update_settings_preset(self) -> None:
        config = self._ui_config()
        preset_id = self._selected_settings_preset_id()
        if preset_id == BUILTIN_SETTINGS_PRESET_ID:
            showWarning(tr("settings.presets.cannot_modify_builtin", config=config))
            return
        preset = find_settings_preset(self._settings_presets, preset_id)
        if preset is None:
            return
        updated = self._build_preset_from_form(name=str(preset.get("name") or ""))
        preset["values"] = updated["values"]
        if "runtime" in updated:
            preset["runtime"] = updated["runtime"]
        else:
            preset.pop("runtime", None)
        self._refresh_settings_preset_dirty_state()

    def _duplicate_settings_preset(self) -> None:
        config = self._ui_config()
        if len(self._settings_presets) >= MAX_SETTINGS_PRESETS:
            showWarning(
                tr(
                    "settings.presets.limit",
                    config=config,
                    max=MAX_SETTINGS_PRESETS,
                )
            )
            return
        preset_id = self._selected_settings_preset_id()
        if preset_id == BUILTIN_SETTINGS_PRESET_ID:
            source_name = tr("settings.presets.builtin", config=config)
            duplicate = new_settings_preset(
                name=tr(
                    "settings.presets.duplicate_name",
                    config=config,
                    name=source_name,
                ),
                values=builtin_preset_values(),
                runtime=None,
            )
        else:
            preset = find_settings_preset(self._settings_presets, preset_id)
            if preset is None:
                return
            duplicate = duplicate_settings_preset(
                preset,
                name=tr(
                    "settings.presets.duplicate_name",
                    config=config,
                    name=str(preset.get("name") or ""),
                ),
            )
        self._settings_presets.append(duplicate)
        self._rebuild_settings_preset_combo(select_id=duplicate["id"])
        values, runtime = resolve_preset_payload(self._settings_presets, duplicate["id"])
        self._settings_preset_loading = True
        try:
            self._apply_prompt_pack_values_to_form(values, runtime, apply_runtime=True)
        finally:
            self._settings_preset_loading = False
        self._refresh_settings_preset_dirty_state()
        QTimer.singleShot(0, lambda: refresh_settings_text_edit_layouts(self))

    def _rename_settings_preset(self) -> None:
        config = self._ui_config()
        preset_id = self._selected_settings_preset_id()
        if preset_id == BUILTIN_SETTINGS_PRESET_ID:
            showWarning(tr("settings.presets.cannot_modify_builtin", config=config))
            return
        preset = find_settings_preset(self._settings_presets, preset_id)
        if preset is None:
            return
        name, ok = QInputDialog.getText(
            self,
            tr("settings.presets.rename", config=config),
            tr("settings.presets.rename_prompt", config=config),
            text=str(preset.get("name") or ""),
        )
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        preset["name"] = name
        self._rebuild_settings_preset_combo(select_id=preset_id)

    def _delete_settings_preset(self) -> None:
        config = self._ui_config()
        preset_id = self._selected_settings_preset_id()
        if preset_id == BUILTIN_SETTINGS_PRESET_ID:
            showWarning(tr("settings.presets.cannot_modify_builtin", config=config))
            return
        preset = find_settings_preset(self._settings_presets, preset_id)
        if preset is None:
            return
        answer = QMessageBox.question(
            self,
            tr("settings.presets.delete", config=config),
            tr(
                "settings.presets.delete_confirm",
                config=config,
                name=str(preset.get("name") or ""),
            ),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._settings_presets = [
            item for item in self._settings_presets if item.get("id") != preset_id
        ]
        self._rebuild_settings_preset_combo(select_id=BUILTIN_SETTINGS_PRESET_ID)
        values, runtime = resolve_preset_payload(
            self._settings_presets,
            BUILTIN_SETTINGS_PRESET_ID,
        )
        self._settings_preset_loading = True
        try:
            self._apply_prompt_pack_values_to_form(values, runtime, apply_runtime=True)
        finally:
            self._settings_preset_loading = False
        self._refresh_settings_preset_dirty_state()

    def _preview_settings_preset(self) -> None:
        config = self._ui_config()
        preset_id = self._selected_settings_preset_id()
        values, runtime = resolve_preset_payload(self._settings_presets, preset_id)
        diffs = preset_diff_from_builtin(values, runtime, config=config)
        name = self._preset_display_name(preset_id)
        if not diffs:
            body = tr("settings.presets.preview.matches_default", config=config)
        else:
            body = "\n".join(f"• {line}" for line in diffs)
        showInfo(
            tr("settings.presets.preview.body", config=config, name=name, summary=body)
        )

    def _export_preset_list(self, presets: list[dict[str, Any]], *, title_key: str) -> None:
        config = self._ui_config()
        if not presets:
            return
        path, _filter = QFileDialog.getSaveFileName(
            self,
            tr(title_key, config=config),
            "prompt-presets.json",
            tr("settings.presets.file_filter", config=config),
        )
        if not path:
            return
        try:
            Path(path).write_text(
                dumps_settings_presets_export(presets),
                encoding="utf-8",
            )
        except OSError as exc:
            showWarning(
                tr("settings.presets.export_error", config=config, error=str(exc))
            )
            return
        showInfo(
            tr(
                "settings.presets.export_done",
                config=config,
                count=len(presets),
            )
        )

    def _export_settings_presets(self) -> None:
        self._export_preset_list(
            self._settings_presets,
            title_key="settings.presets.export.title",
        )

    def _export_selected_settings_preset(self) -> None:
        config = self._ui_config()
        preset_id = self._selected_settings_preset_id()
        if preset_id == BUILTIN_SETTINGS_PRESET_ID:
            showWarning(tr("settings.presets.cannot_export_builtin", config=config))
            return
        preset = find_settings_preset(self._settings_presets, preset_id)
        if preset is None:
            return
        self._export_preset_list(
            [preset],
            title_key="settings.presets.export_selected.title",
        )

    def _import_settings_presets(self) -> None:
        config = self._ui_config()
        path, _filter = QFileDialog.getOpenFileName(
            self,
            tr("settings.presets.import.title", config=config),
            "",
            tr("settings.presets.file_filter", config=config),
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            incoming = loads_settings_presets_import(text)
        except (OSError, ValueError) as exc:
            showWarning(
                tr(
                    "settings.presets.import_error",
                    config=config,
                    error=translate_preset_import_error(exc, config=config),
                )
            )
            return
        merged, added = merge_imported_settings_presets(self._settings_presets, incoming)
        self._settings_presets = merged
        select_id = self._selected_settings_preset_id()
        self._rebuild_settings_preset_combo(select_id=select_id)
        if added:
            showInfo(
                tr("settings.presets.import_done", config=config, count=added)
            )
        elif len(self._settings_presets) >= MAX_SETTINGS_PRESETS:
            showWarning(
                tr(
                    "settings.presets.limit",
                    config=config,
                    max=MAX_SETTINGS_PRESETS,
                )
            )

    def _on_language_changed(self) -> None:
        lang = self.language_combo.currentData() or DEFAULT_LANGUAGE
        current_brain = self.brain_message_input.toPlainText().strip()
        if is_builtin_brain_import_message(current_brain):
            self.brain_message_input.setPlainText(tr("defaults.brain_import_message", lang=lang))
        self._refresh_builtin_instruction_fields_for_language(lang)
        current_optimize_prompt = self.prompt_optimize_user_input.toPlainText().strip()
        if is_builtin_optimize_user_prompt(current_optimize_prompt):
            self.prompt_optimize_user_input.setPlainText(
                tr("instructions.optimize_user_prompt", lang=lang)
            )
        current_chat_addon = self.prompt_chat_addon_input.toPlainText().strip()
        if is_builtin_chat_system_addon(current_chat_addon):
            self.prompt_chat_addon_input.setPlainText(
                tr("instructions.chat_system_addon", lang=lang)
            )
        current_dynamic_prefix = self.prompt_dynamic_rules_prefix_input.toPlainText().strip()
        if is_builtin_dynamic_rules_prefix(current_dynamic_prefix):
            self.prompt_dynamic_rules_prefix_input.setPlainText(
                tr("instructions.dynamic_rules_prefix", lang=lang)
            )
        if is_builtin_wrapper_layout(self._baseline_config):
            pending = dict(self._baseline_config)
            pending["language"] = lang
            self.wrapper_sections_editor.load_from_config(pending)

    def _save_and_accept(self) -> None:
        if not self._confirm_save_if_needed():
            return

        pending = self._collect_pending_config()
        affected = purposes_requiring_cache_invalidation(self._baseline_config, pending)
        self.config = pending
        save_config(self.config)
        for purpose in affected:
            clear_prompt_cache(config=self.config, purpose=purpose)
        refresh_chat_from_settings()
        self.accept()

    def _load_prompt_cache_custom_text_from_file(self) -> None:
        config = self._ui_config()
        existing = self.prompt_cache_custom_text_input.toPlainText().strip()
        if existing and not confirm_custom_text_load_replace(self, config):
            return

        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            tr("settings.prompt_cache_custom_text.load_file.title", config=config),
            "",
            tr("settings.prompt_cache_custom_text.load_file.filter", config=config),
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except OSError as exc:
            showWarning(
                tr(
                    "settings.prompt_cache_custom_text.load_error",
                    config=config,
                    error=str(exc),
                )
            )
            return

        self.prompt_cache_custom_text_input.setPlainText(text)
        custom_checkbox = self.prompt_cache_segment_checkboxes.get("custom_cache_text")
        if custom_checkbox is not None:
            custom_checkbox.setChecked(True)

    def _refresh_prompt_cache_status(self) -> None:
        if not hasattr(self, "prompt_cache_status_label"):
            return
        config = self._ui_config() if hasattr(self, "language_combo") else self.config
        self.prompt_cache_status_label.setText(prompt_cache_status_text(config, "optimize"))
        if hasattr(self, "chat_prompt_cache_summary_label"):
            self.chat_prompt_cache_summary_label.setText(chat_prompt_cache_summary(config))
        if hasattr(self, "prompt_cache_change_ttl_btn"):
            self.prompt_cache_change_ttl_btn.setEnabled(any_tracked_active_cache())
        if hasattr(self, "prompt_cache_clear_optimize_btn"):
            self.prompt_cache_clear_optimize_btn.setEnabled(
                get_prompt_cache_store("optimize").active is not None
            )

    def _on_restore_chat_cache_link_activated(self, href: str) -> None:
        if href == "chat-cache-settings":
            self._open_chat_prompt_cache_settings()

    def _open_chat_prompt_cache_settings(self) -> None:
        if (
            self._chat_prompt_cache_dialog is not None
            and self._chat_prompt_cache_dialog.isVisible()
        ):
            self._chat_prompt_cache_dialog.raise_()
            self._chat_prompt_cache_dialog.activateWindow()
            return
        dialog = ChatPromptCacheDialog(
            self,
            config=self._ui_config(),
            on_finished=self._on_chat_prompt_cache_settings_finished,
        )
        self._chat_prompt_cache_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _on_chat_prompt_cache_settings_finished(self, accepted: bool) -> None:
        self._chat_prompt_cache_dialog = None
        if not accepted:
            return
        self.config = load_config()
        self._refresh_prompt_cache_status()
        refresh_chat_from_settings()

    def _change_prompt_cache_ttl(self) -> None:
        config = self._ui_config()
        if not any_tracked_active_cache():
            showWarning(tr("settings.prompt_cache.change_ttl.none", config=config))
            return
        ttl_seconds = self.prompt_cache_change_ttl_input.value()
        purposes = choose_prompt_cache_ttl_targets(
            self,
            config,
            ttl_seconds=ttl_seconds,
        )
        if not purposes:
            return
        config = dict(config)
        config["prompt_cache_change_ttl_seconds"] = ttl_seconds
        updated = 0
        failed = False
        for purpose in purposes:
            if extend_prompt_cache_ttl(
                config=config,
                purpose=purpose,
                extra_seconds=ttl_seconds,
            ):
                updated += 1
            elif get_prompt_cache_store(purpose).active is not None:
                failed = True
        self._refresh_prompt_cache_status()
        if updated > 0:
            tooltip(
                tr(
                    "settings.prompt_cache.change_ttl.partial",
                    config=config,
                    count=updated,
                )
            )
        elif failed:
            showWarning(tr("settings.prompt_cache.change_ttl.failed", config=config))
        else:
            showWarning(tr("settings.prompt_cache.change_ttl.none", config=config))

    def _selected_prompt_cache_preset_id(self) -> str:
        if not hasattr(self, "prompt_cache_preset_combo"):
            return ""
        return str(self.prompt_cache_preset_combo.currentData() or "")

    def _find_prompt_cache_preset(self, preset_id: str) -> dict[str, Any] | None:
        for preset in self._prompt_cache_presets:
            if preset.get("id") == preset_id:
                return preset
        return None

    def _commit_prompt_cache_preset_editor(self) -> None:
        if not hasattr(self, "prompt_cache_custom_text_input"):
            return
        text = self.prompt_cache_custom_text_input.toPlainText()
        preset_id = self._selected_prompt_cache_preset_id()
        if preset_id:
            preset = self._find_prompt_cache_preset(preset_id)
            if preset is not None:
                preset["text"] = text
                preset["name"] = self.prompt_cache_preset_name_input.text().strip() or preset["name"]
                preset["chat"] = self.prompt_cache_preset_chat_checkbox.isChecked()
                preset["optimize"] = self.prompt_cache_preset_optimize_checkbox.isChecked()
        else:
            self._manual_custom_cache_text = text

    def _sync_prompt_cache_preset_fields(self) -> None:
        if not hasattr(self, "prompt_cache_preset_combo"):
            return
        preset_id = self._selected_prompt_cache_preset_id()
        editing_preset = bool(preset_id)
        self.prompt_cache_preset_name_input.setEnabled(editing_preset)
        self.prompt_cache_preset_chat_checkbox.setEnabled(editing_preset)
        self.prompt_cache_preset_optimize_checkbox.setEnabled(editing_preset)
        self.prompt_cache_preset_remove_btn.setEnabled(editing_preset)
        if editing_preset:
            preset = self._find_prompt_cache_preset(preset_id)
            if preset is None:
                return
            self.prompt_cache_preset_name_input.setText(str(preset.get("name") or ""))
            self.prompt_cache_preset_chat_checkbox.setChecked(bool(preset.get("chat", True)))
            self.prompt_cache_preset_optimize_checkbox.setChecked(
                bool(preset.get("optimize", True))
            )
            self.prompt_cache_custom_text_input.setPlainText(str(preset.get("text") or ""))
        else:
            self.prompt_cache_preset_name_input.clear()
            self.prompt_cache_preset_chat_checkbox.setChecked(True)
            self.prompt_cache_preset_optimize_checkbox.setChecked(True)
            self.prompt_cache_custom_text_input.setPlainText(self._manual_custom_cache_text)

    def _on_prompt_cache_preset_changed(self) -> None:
        self._commit_prompt_cache_preset_editor()
        self._sync_prompt_cache_preset_fields()

    def _rebuild_prompt_cache_preset_combo(self, *, select_id: str = "") -> None:
        config = self._ui_config()
        self.prompt_cache_preset_combo.blockSignals(True)
        self.prompt_cache_preset_combo.clear()
        self.prompt_cache_preset_combo.addItem(
            tr("settings.prompt_cache_presets.manual", config=config),
            "",
        )
        for preset in self._prompt_cache_presets:
            if preset.get("optimize"):
                self.prompt_cache_preset_combo.addItem(
                    str(preset.get("name") or ""),
                    str(preset.get("id") or ""),
                )
        target = select_id or self._selected_prompt_cache_preset_id()
        index = self.prompt_cache_preset_combo.findData(target)
        self.prompt_cache_preset_combo.setCurrentIndex(index if index >= 0 else 0)
        self.prompt_cache_preset_combo.blockSignals(False)

    def _add_prompt_cache_preset(self) -> None:
        config = self._ui_config()
        if len(self._prompt_cache_presets) >= MAX_CUSTOM_TEXT_PRESETS:
            showWarning(
                tr(
                    "settings.prompt_cache_presets.limit",
                    config=config,
                    max=MAX_CUSTOM_TEXT_PRESETS,
                )
            )
            return
        self._commit_prompt_cache_preset_editor()
        text = self.prompt_cache_custom_text_input.toPlainText()
        preset = new_preset(name=f"preset-{len(self._prompt_cache_presets) + 1}", text=text)
        self._prompt_cache_presets.append(preset)
        self._rebuild_prompt_cache_preset_combo(select_id=preset["id"])
        self._sync_prompt_cache_preset_fields()

    def _remove_prompt_cache_preset(self) -> None:
        preset_id = self._selected_prompt_cache_preset_id()
        if not preset_id:
            return
        self._prompt_cache_presets = [
            preset for preset in self._prompt_cache_presets if preset.get("id") != preset_id
        ]
        self._rebuild_prompt_cache_preset_combo(select_id="")
        self._sync_prompt_cache_preset_fields()

    def _clear_optimize_prompt_cache(self) -> None:
        clear_prompt_cache(config=self._ui_config(), purpose="optimize")
        self._refresh_prompt_cache_status()

    def _clear_prompt_cache(self) -> None:
        clear_prompt_cache(config=self._ui_config())
        self._refresh_prompt_cache_status()

    def _open_prompt_cache_manager(self) -> None:
        open_prompt_cache_manager(self, config=self._ui_config())
        self._refresh_prompt_cache_status()

    def _collect_chat_export_quick_folders_from_ui(self) -> list[dict[str, str]]:
        folders: list[dict[str, str]] = []
        for row in self._chat_export_quick_folder_rows:
            path = row.path_input.toPlainText().strip()
            if not path:
                continue
            label = row.label_input.toPlainText().strip() or Path(path).name
            folders.append({"label": label, "path": path})
        return folders

    def _clear_chat_export_quick_folder_rows(self) -> None:
        while self._chat_export_quick_folders_layout.count():
            item = self._chat_export_quick_folders_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._chat_export_quick_folder_rows.clear()

    def _load_chat_export_quick_folder_rows(
        self,
        folders: list[dict[str, str]],
    ) -> None:
        self._clear_chat_export_quick_folder_rows()
        for folder in folders:
            self._add_chat_export_quick_folder_row(
                label=str(folder.get("label") or ""),
                path=str(folder.get("path") or ""),
            )

    def _add_chat_export_quick_folder_row(
        self,
        *,
        label: str = "",
        path: str = "",
    ) -> None:
        if len(self._chat_export_quick_folder_rows) >= MAX_CHAT_EXPORT_QUICK_FOLDERS:
            return
        config = self._ui_config()
        show_newlines = self.show_text_newlines_checkbox.isChecked()
        wrap = self.wrap_text_editors_checkbox.isChecked()
        row_host = QWidget(self._chat_export_quick_folders_container)
        row = QHBoxLayout(row_host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        checkbox = QCheckBox(row_host)
        checkbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        checkbox.toggled.connect(self._sync_chat_export_quick_folder_buttons)
        row.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignTop)
        label_shell, label_input = create_settings_row_auto_height_text_edit(
            row_host,
            minimum=_QUICK_FOLDER_ROW_TEXT_MIN_HEIGHT,
            maximum=_QUICK_FOLDER_ROW_TEXT_MAX_HEIGHT,
            show_newlines=show_newlines,
            wrap=wrap,
        )
        label_input.setPlaceholderText(
            tr("settings.chat_export_quick_folders.label", config=config)
        )
        label_input.setPlainText(label)
        row.addWidget(label_shell, 1, Qt.AlignmentFlag.AlignTop)
        path_shell, path_input = create_settings_row_auto_height_text_edit(
            row_host,
            minimum=_QUICK_FOLDER_ROW_TEXT_MIN_HEIGHT,
            maximum=_QUICK_FOLDER_ROW_TEXT_MAX_HEIGHT,
            show_newlines=show_newlines,
            wrap=wrap,
        )
        path_input.setPlaceholderText(
            tr("settings.chat_export_quick_folders.path", config=config)
        )
        path_input.setPlainText(path)
        row.addWidget(path_shell, 2, Qt.AlignmentFlag.AlignTop)
        browse_btn = QPushButton(
            tr("settings.chat_export_quick_folders.browse", config=config),
            row_host,
        )
        browse_btn.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        browse_btn.clicked.connect(
            lambda _checked=False, editor=path_input: self._browse_chat_export_quick_folder(
                editor
            )
        )
        row.addWidget(browse_btn, 0, Qt.AlignmentFlag.AlignTop)
        folder_row = _ChatExportQuickFolderRow(
            host=row_host,
            checkbox=checkbox,
            label_input=label_input,
            path_input=path_input,
        )
        self._chat_export_quick_folders_layout.addWidget(row_host)
        self._chat_export_quick_folder_rows.append(folder_row)
        self._sync_chat_export_quick_folder_buttons()
        QTimer.singleShot(0, lambda: refresh_settings_text_edit_layouts(self))

    def _remove_chat_export_quick_folder_row(self) -> None:
        selected_rows = [
            row
            for row in self._chat_export_quick_folder_rows
            if row.checkbox.isChecked()
        ]
        if not selected_rows:
            return
        for row in selected_rows:
            self._chat_export_quick_folder_rows.remove(row)
            self._chat_export_quick_folders_layout.removeWidget(row.host)
            row.host.deleteLater()
        self._sync_chat_export_quick_folder_buttons()
        QTimer.singleShot(0, lambda: refresh_settings_text_edit_layouts(self))

    def _sync_chat_export_quick_folder_buttons(self) -> None:
        count = len(self._chat_export_quick_folder_rows)
        has_selection = any(
            row.checkbox.isChecked() for row in self._chat_export_quick_folder_rows
        )
        self.chat_export_quick_folder_add_btn.setEnabled(
            count < MAX_CHAT_EXPORT_QUICK_FOLDERS
        )
        self.chat_export_quick_folder_remove_btn.setEnabled(has_selection)

    def _browse_chat_export_quick_folder(self, path_input: ScrollAwareTextEdit) -> None:
        config = self._ui_config()
        start_dir = path_input.toPlainText().strip() or str(
            default_chat_download_directory()
        )
        selected = QFileDialog.getExistingDirectory(
            self,
            tr("settings.chat_export_quick_folders.browse.title", config=config),
            start_dir,
        )
        if selected:
            path_input.setPlainText(selected)
            refresh_settings_text_edit_layouts(self)

    def _open_optimize_prompt_inspection(self) -> None:
        pending = self._collect_pending_config()
        config = pending
        inspection = build_optimize_prompt_inspection(pending)
        if self._optimize_prompt_inspection_window is None:
            self._optimize_prompt_inspection_window = PromptInspectionWindow(
                self,
                title=tr("prompt.inspect.optimize.title", config=config),
            )
        self._optimize_prompt_inspection_window.show_inspection(inspection, pending)


def _clear_settings_dialog_ref(_result: int | None = None) -> None:
    global _settings_dialog
    _settings_dialog = None


def close_settings_dialog(*, force: bool = False) -> None:
    global _settings_dialog
    if _settings_dialog is None:
        return
    if force:
        _settings_dialog.force_shutdown()
    else:
        _settings_dialog.close()


def open_settings_dialog(editor) -> None:
    global _settings_dialog
    if _settings_dialog is not None and _settings_dialog.isVisible():
        _settings_dialog.raise_()
        _settings_dialog.activateWindow()
        return
    config = load_config()
    _settings_dialog = SettingsDialog(None, config)
    _settings_dialog.finished.connect(_clear_settings_dialog_ref)
    _settings_dialog.show()
