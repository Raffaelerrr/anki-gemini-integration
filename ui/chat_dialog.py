from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from aqt import mw
from aqt.qt import (
    QApplication,
    QCheckBox,
    QCloseEvent,
    QDialog,
    QShowEvent,
    QFileDialog,
    QHBoxLayout,
    QIcon,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSize,
    QMenu,
    QToolButton,
    QTextBrowser,
    QTextCursor,
    QTextEdit,
    Qt,
    QTimer,
    QUrl,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import showWarning, tooltip

from ..i18n import (
    effective_brain_import_message,
    format_chat_context_message,
    is_builtin_card_templates_format_prompt,
    is_builtin_wrapper_layout,
    normalize_wrapper_sections_for_save,
    tr,
)
from ..note_context_fields import (
    ImportedNoteData,
    fields_for_note_preview,
    format_imported_notes_context,
    imported_note_from_anki_note,
    merge_imported_notes,
)
from ..note_apply import (
    ApplyNoteHistory,
    NoteApplyBatch,
    NoteApplyPlan,
    apply_note_tags_present,
    clamp_apply_history_max,
    clear_apply_undo,
    extract_apply_note,
    format_apply_batch_for_display,
)
from ..chat_include_mask import IncludeNextMessageMask
from ..config import api_key_configured, is_warning_dismissed, load_config, save_config
from ..prompt_cache import (
    PromptCacheSessionContext,
    build_live_chat_payload,
    build_prompt_cache_bundle,
    clear_prompt_cache,
    flatten_bundle_for_live_send,
    prompt_cache_enabled,
)
from ..prompt_cache_policy import (
    chat_cache_includes_session_content,
    has_tracked_active_cache,
)
from ..settings_presets import (
    BUILTIN_SETTINGS_PRESET_ID,
    apply_preset_to_config,
    normalize_settings_presets,
    preset_diff_from_builtin,
    resolve_preset_payload,
)
from .chat_include_panel import ChatIncludePanel
from .chat_prompt_cache_dialog import ChatPromptCacheDialog
from .chat_request_lifecycle import ChatRequestGate
from .chat_templates_edit_window import ChatTemplatesEditWindow
from .chat_wrapper_edit_window import ChatWrapperEditWindow
from .note_apply_dialog import open_note_apply_dialog
from .note_apply_execute import (
    can_undo_last_note_apply,
    execute_note_apply_plan,
    undo_last_note_apply,
)
from ..prompt_inspection import (
    build_chat_prompt_inspection,
    chat_session_config_changed,
    chat_session_config_fingerprint,
)
from ..token_estimate import estimate_chat_request_chars
from .prompt_cache_confirm import (
    PromptCacheRecreateAcknowledgment,
    PromptCacheRecreatePromptContext,
    confirm_import_note_cache_if_needed,
    confirm_new_conversation_cache_if_needed,
    resolve_prompt_cache_recreate_choice,
)
from .pre_send_prompt_dialog import (
    PreSendPromptContext,
    confirm_pre_send_prompt,
    open_prompt_preview,
)
from ..gemini_client import (
    GeminiAuthError,
    GeminiCancelledError,
    GeminiError,
    GeminiRateLimitError,
    call_gemini,
    extract_dynamic_rules,
    merge_system_instructions,
    resolve_model,
    stream_gemini,
    trim_history,
)
from .card_templates import (
    CardTemplateData,
    ImportedNotetypeData,
    editable_templates_notetypes,
    format_imported_notetype_styling,
    format_imported_notetype_templates,
    format_card_templates_block,
    format_notetype_schemas_block,
    imported_notetype_from_id,
    imported_notetype_has_styling,
    imported_notetype_has_templates,
    merge_imported_notetypes,
    primary_templates_notetype_id,
    templates_and_styling_for_editor,
)
from .chat_notetype_import_dialog import confirm_notetype_import
from .chat_templates_notetype_picker import pick_templates_notetype
from .chat_imported_note_picker import pick_imported_note
from .chat_export import (
    chat_export_last_used_directory,
    default_chat_download_directory,
    default_chat_export_filename,
    format_chat_export_text,
    format_export_folder_menu_text,
    normalize_chat_export_quick_folders,
    save_chat_export_text_to_directory,
)
from .chat_formatter import (
    format_gemini_reply_html,
    format_streaming_reply_html,
    prose_contains_labeled_field_fences,
    stored_block_label,
    stored_block_text,
)
from .chat_body_splitter import ChatBodySplitter
from .chat_log_renderer import render_chat_document
from .chat_math_log import (
    chat_log_scroll_to_bottom,
    chat_log_scroll_to_last_gemini_label,
    chat_log_scroll_y,
    chat_log_set_scroll_y,
    chat_math_log_available,
    cleanup_chat_log_webview,
    create_chat_log_webview,
    load_chat_log_webview,
)
from .chat_note_edit_window import ChatNoteEditWindow
from .chat_messages import ChatMessage
from .imported_note_preview_window import ImportedNotePreviewWindow
from .help_icons import set_instruction_tooltip
from .settings_compact_controls import (
    create_ui_text_edit,
    refresh_settings_text_edit_newlines,
    refresh_text_edit_wrap,
)
from .svg_icons import (
    LoadingStatusIcon,
    barred_brain_icon,
    brain_icon,
    cache_icon,
    download_icon,
    eye_icon,
    import_icon,
    lens_icon,
    pencil_icon,
    plus_icon,
    priority_sign_icon,
    robot_svg_path,
    stop_circle_svg_path,
    stop_sign_icon,
)
from .theme import (
    ICON_BUTTON_SIZE,
    chat_document_stylesheet,
    chat_toolbar_button_stylesheet,
    loading_label_stylesheet,
    refresh_native_text_edits_in,
    settings_stale_banner_stylesheet,
    tooltip_stylesheet,
)
from .themed_windows import SNAPPABLE_WINDOW_FLAGS, configure_snappable_window


class ChatWindow(QWidget):
    def __init__(self):
        super().__init__(None, SNAPPABLE_WINDOW_FLAGS)
        configure_snappable_window(self)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.silentlyClose = False
        self.setMinimumSize(640, 680)
        self.resize(640, 720)

        self.api_history: list[dict[str, Any]] = []
        self.note_context: str | None = None
        self._imported_notes: dict[int, ImportedNoteData] = {}
        self._imported_notetypes: dict[int, ImportedNotetypeData] = {}
        self._imported_card_templates: list[CardTemplateData] = []
        self._imported_notetype_css: str = ""
        self._imported_notetype_id: int | None = None
        self._preview_note_id: int | None = None
        self._include_mask = IncludeNextMessageMask()
        self._pending_apply_batch: NoteApplyBatch | None = None
        self._pending_apply_plan: NoteApplyPlan | None = None
        self._apply_history = ApplyNoteHistory(
            clamp_apply_history_max(load_config().get("chat_apply_history_max", 7))
        )
        self._session_wrapper_override: dict[str, Any] | None = None
        self._prompt_cache_recreate_ack: PromptCacheRecreateAcknowledgment | None = None
        self._messages: list[ChatMessage] = []
        self._loading_phase = 0
        self._loading_rotation_degrees = 0
        self._copy_blocks: dict[str, Any] = {}
        self._field_preview_window: ImportedNotePreviewWindow | None = None
        self._field_preview_payload: list[tuple[str, str]] = []
        self._copy_counter = 0
        self._streaming_message_index: int | None = None
        self._stream_visible = False
        self._loading_mode: str | None = None
        self._closing = False
        self._request_gate = ChatRequestGate()
        self._restorable_user_text = ""
        self._note_preview_window: ImportedNotePreviewWindow | None = None
        self._note_edit_window: ChatNoteEditWindow | None = None
        self._wrapper_edit_window: ChatWrapperEditWindow | None = None
        self._templates_edit_window: ChatTemplatesEditWindow | None = None
        self._note_apply_dialog = None
        self._include_panel: ChatIncludePanel | None = None
        self._prompt_preview_dialog = None
        self._prompt_cache_dialog = None
        self._session_config_fingerprint = ""
        self._settings_stale_banner_dismissed = False

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.btn_include_context = QPushButton(self)
        self.btn_include_context.setEnabled(False)
        self.btn_include_context.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.btn_include_context.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.btn_include_context.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_include_context.setAttribute(
            Qt.WidgetAttribute.WA_AlwaysShowToolTips,
            True,
        )
        self.btn_include_context.clicked.connect(self._open_include_panel)
        toolbar.addWidget(self.btn_include_context)

        self.btn_edit_menu = QToolButton(self)
        self.btn_edit_menu.setObjectName("chatEditMenu")
        self.btn_edit_menu.setEnabled(False)
        self.btn_edit_menu.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_edit_menu.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.btn_edit_menu.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.btn_edit_menu.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.btn_edit_menu.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_edit_menu.setAttribute(
            Qt.WidgetAttribute.WA_AlwaysShowToolTips,
            True,
        )
        self._edit_menu = QMenu(self)
        self._edit_note_action = self._edit_menu.addAction("")
        self._edit_note_action.triggered.connect(self._open_note_edit_window)
        self._edit_wrapper_action = self._edit_menu.addAction("")
        self._edit_wrapper_action.triggered.connect(self._open_wrapper_edit_window)
        self._edit_templates_action = self._edit_menu.addAction("")
        self._edit_templates_action.triggered.connect(self._open_templates_edit_window)
        self._edit_menu.addSeparator()
        self._apply_note_action = self._edit_menu.addAction("")
        self._apply_note_action.triggered.connect(self._open_note_apply_dialog)
        self._undo_apply_note_action = self._edit_menu.addAction("")
        self._undo_apply_note_action.triggered.connect(self._undo_last_note_apply)
        self._edit_menu.addSeparator()
        self._presets_menu = QMenu(self._edit_menu)
        self._presets_menu.aboutToShow.connect(self._rebuild_presets_menu)
        self._presets_menu_action = self._edit_menu.addMenu(self._presets_menu)
        self.btn_edit_menu.setMenu(self._edit_menu)
        toolbar.addWidget(self.btn_edit_menu)

        self.btn_import_notetype = QPushButton(self)
        self.btn_import_notetype.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.btn_import_notetype.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.btn_import_notetype.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_import_notetype.setAttribute(
            Qt.WidgetAttribute.WA_AlwaysShowToolTips,
            True,
        )
        self.btn_import_notetype.clicked.connect(self._open_notetype_import_dialog)
        toolbar.addWidget(self.btn_import_notetype)

        self.btn_note_preview = QPushButton(self)
        self.btn_note_preview.setEnabled(False)
        self.btn_note_preview.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.btn_note_preview.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.btn_note_preview.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_note_preview.setAttribute(
            Qt.WidgetAttribute.WA_AlwaysShowToolTips,
            True,
        )
        self.btn_note_preview.clicked.connect(self._open_note_preview_window)
        toolbar.addWidget(self.btn_note_preview)

        self.btn_inspect_prompt = QPushButton(self)
        self.btn_inspect_prompt.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.btn_inspect_prompt.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.btn_inspect_prompt.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_inspect_prompt.setAttribute(
            Qt.WidgetAttribute.WA_AlwaysShowToolTips,
            True,
        )
        self.btn_inspect_prompt.clicked.connect(self._open_prompt_preview)
        toolbar.addWidget(self.btn_inspect_prompt)

        self.btn_prompt_cache = QPushButton(self)
        self.btn_prompt_cache.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.btn_prompt_cache.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.btn_prompt_cache.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_prompt_cache.setAttribute(
            Qt.WidgetAttribute.WA_AlwaysShowToolTips,
            True,
        )
        self.btn_prompt_cache.clicked.connect(self._open_prompt_cache_session_dialog)
        toolbar.addWidget(self.btn_prompt_cache)

        initial_stop_before_send = bool(
            load_config().get("chat_modify_prompt_before_send", False)
        )
        self.stop_before_send_btn = QPushButton(self)
        self.stop_before_send_btn.setCheckable(True)
        self.stop_before_send_btn.setChecked(initial_stop_before_send)
        self.stop_before_send_btn.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.stop_before_send_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stop_before_send_btn.toggled.connect(self._on_modify_prompt_toggled)
        self.stop_before_send_btn.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.stop_before_send_btn.setAttribute(
            Qt.WidgetAttribute.WA_AlwaysShowToolTips,
            True,
        )
        toolbar.addWidget(self.stop_before_send_btn)

        self.btn_download = QToolButton(self)
        self.btn_download.setObjectName("chatDownloadMenu")
        self.btn_download.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_download.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.btn_download.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.btn_download.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.btn_download.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_download.setAttribute(
            Qt.WidgetAttribute.WA_AlwaysShowToolTips,
            True,
        )
        self._download_menu = QMenu(self)
        self._download_menu.aboutToShow.connect(self._refresh_download_menu)
        self.btn_download.setMenu(self._download_menu)
        toolbar.addWidget(self.btn_download)

        self.btn_clear = QPushButton(self)
        self.btn_clear.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.btn_clear.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        self.btn_clear.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_clear.setAttribute(
            Qt.WidgetAttribute.WA_AlwaysShowToolTips,
            True,
        )
        self.btn_clear.clicked.connect(self.clear_conversation)
        toolbar.addWidget(self.btn_clear)

        toolbar.addStretch(1)
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
        self._settings_stale_banner_close.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self._settings_stale_banner_close.clicked.connect(self._dismiss_settings_stale_banner)
        stale_layout.addWidget(
            self._settings_stale_banner_close,
            0,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        self._settings_stale_banner.setVisible(False)
        layout.addWidget(self._settings_stale_banner)

        self._body_splitter = ChatBodySplitter(self, chat_section_index=0)
        layout.addWidget(self._body_splitter, 1)

        self._uses_web_chat_log = False
        if chat_math_log_available():
            try:
                self.chat_log = create_chat_log_webview(self._body_splitter)
                self.chat_log.set_bridge_command(self._on_chat_log_bridge_cmd, self)
                self._uses_web_chat_log = True
            except (RuntimeError, AttributeError, ImportError, TypeError, ValueError):
                self.chat_log = None
        if not self._uses_web_chat_log:
            self.chat_log = QTextBrowser(self._body_splitter)
            self.chat_log.setOpenLinks(False)
            self.chat_log.setReadOnly(True)
            self.chat_log.anchorClicked.connect(self._on_anchor_clicked)
        self.chat_log.setMinimumHeight(120)
        self.chat_log.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self._body_splitter.set_sections(self.chat_log)
        QTimer.singleShot(0, self._refresh_body_splitter_sizes)

        self.loading_row = QWidget(self)
        loading_row_layout = QHBoxLayout(self.loading_row)
        loading_row_layout.setContentsMargins(0, 0, 0, 0)
        loading_row_layout.setSpacing(3)
        self.loading_icon = LoadingStatusIcon(self.loading_row)
        self.loading_text_label = QLabel("", self.loading_row)
        loading_row_layout.addWidget(self.loading_icon)
        loading_row_layout.addWidget(self.loading_text_label)
        loading_row_layout.addStretch()
        self.loading_row.setVisible(False)
        layout.addWidget(self.loading_row)

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
            tr("chat.welcome", config=load_config()),
            kind="gemini",
            label=tr("chat.label.gemini", config=load_config()),
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
        QTimer.singleShot(0, self._refresh_body_splitter_sizes)
        self._focus_chat_input()

    def _refresh_body_splitter_sizes(self) -> None:
        self._body_splitter.refresh_sizes()

    def _on_body_section_visibility_changed(self, opened_index: int | None = None) -> None:
        self._body_splitter.rebalance_on_visibility_change(opened_index)
        QTimer.singleShot(0, self._refresh_body_splitter_sizes)

    def _has_imported_templates_or_styling(self) -> bool:
        if self._imported_notetypes:
            return imported_notetype_has_templates(
                self._imported_notetypes
            ) or imported_notetype_has_styling(self._imported_notetypes)
        return bool(self._imported_card_templates) or bool(self._imported_notetype_css.strip())

    def _has_import_session(self) -> bool:
        return bool(self._imported_notes) or bool(self._imported_notetypes)

    def _has_sendable_context(self) -> bool:
        return self._has_import_session()

    def _include_context_active(self) -> bool:
        if not self._include_mask.any_selected():
            return False
        if any(
            note_id in self._imported_notes
            for note_id in self._include_mask.selected_note_ids()
        ):
            return True
        selected_schemas = set(self._include_mask.selected_schema_ids())
        if any(mid in self._imported_notetypes for mid in selected_schemas):
            return True
        for mid in self._include_mask.selected_template_ids():
            data = self._imported_notetypes.get(mid)
            if data is not None and data.templates:
                return True
            if not self._imported_notetypes and self._imported_card_templates:
                return True
        for mid in self._include_mask.selected_css_ids():
            data = self._imported_notetypes.get(mid)
            if data is not None and data.css.strip():
                return True
            if not self._imported_notetypes and self._imported_notetype_css.strip():
                return True
        return False

    def _sync_legacy_notetype_cache(self) -> None:
        templates, css = templates_and_styling_for_editor(
            self._imported_notetypes,
            preferred_id=self._imported_notetype_id,
        )
        self._imported_card_templates = templates
        self._imported_notetype_css = css

    def _sync_include_mask_keys(self) -> None:
        note_ids = set(self._imported_notes.keys())
        for note_id in note_ids:
            self._include_mask.ensure_note(note_id)
        self._include_mask.prune_to_note_ids(note_ids)
        type_ids = set(self._imported_notetypes.keys())
        for notetype_id in type_ids:
            self._include_mask.ensure_notetype(notetype_id)
        self._include_mask.prune_to_notetype_ids(type_ids)

    def _reload_include_panel(self) -> None:
        if self._include_panel is None:
            return
        self._include_panel.load(
            self._include_mask,
            notes=self._imported_notes,
            notetypes=self._imported_notetypes,
        )

    def _refresh_include_context_button(self) -> None:
        self.btn_include_context.setEnabled(self._has_import_session())
        self._apply_include_context_icon()
        if self._include_panel is not None and self._include_panel.isVisible():
            self._reload_include_panel()

    def _open_include_panel(self) -> None:
        if not self._has_import_session():
            return
        if self._include_panel is None:
            self._include_panel = ChatIncludePanel(
                self,
                on_changed=self._on_include_mask_changed,
            )
            self._include_panel.destroyed.connect(
                lambda *_: setattr(self, "_include_panel", None)
            )
        self._reload_include_panel()
        config = load_config()
        self._include_panel.apply_language(config)
        self._include_panel.apply_theme()
        self._include_panel.show()
        self._include_panel.raise_()
        self._include_panel.activateWindow()

    def _close_include_panel(self) -> None:
        if self._include_panel is None:
            return
        self._include_panel.close()
        self._include_panel = None

    def _on_include_mask_changed(self) -> None:
        self._rebuild_note_context()
        self._apply_include_context_icon()
        self._on_body_section_visibility_changed()
        if (
            self._prompt_preview_dialog is not None
            and self._prompt_preview_dialog.isVisible()
        ):
            self._prompt_preview_dialog.apply_context(self.build_pre_send_context())

    def _apply_default_mask_for_note_import(
        self,
        note_ids: list[int],
    ) -> None:
        self._sync_include_mask_keys()
        for note_id in note_ids:
            if note_id in self._imported_notes:
                self._include_mask.note_fields[note_id] = True
        for note_id in note_ids:
            note = self._imported_notes.get(note_id)
            if note is None:
                continue
            mid = note.notetype_id
            self._include_mask.ensure_notetype(mid)
            # Templates/CSS stay off until chosen in the include panel.
            self._include_mask.templates[mid] = False
            self._include_mask.css[mid] = False
        self._refresh_include_context_button()

    def _apply_default_mask_for_notetype_import(
        self,
        incoming: list[ImportedNotetypeData],
    ) -> None:
        self._sync_include_mask_keys()
        for data in incoming:
            mid = data.notetype_id
            self._include_mask.schemas[mid] = True
            self._include_mask.templates[mid] = False
            self._include_mask.css[mid] = False
        self._refresh_include_context_button()

    def _register_imported_notetype(
        self,
        data: ImportedNotetypeData,
        *,
        include_templates: bool = True,
        include_css: bool = True,
    ) -> None:
        incoming = ImportedNotetypeData(
            notetype_id=data.notetype_id,
            name=data.name,
            field_names=list(data.field_names),
            templates=list(data.templates) if include_templates else [],
            css=data.css if include_css else "",
        )
        self._imported_notetypes = merge_imported_notetypes(
            self._imported_notetypes,
            [incoming],
        )
        self._sync_legacy_notetype_cache()
        self._sync_include_mask_keys()

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

    def _toolbar_icon_size(self) -> int:
        return ICON_BUTTON_SIZE - 4

    def _set_toolbar_icon(
        self,
        button: QPushButton | QToolButton,
        icon: QIcon,
    ) -> None:
        icon_size = self._toolbar_icon_size()
        if isinstance(button, QToolButton):
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setIcon(icon)
        button.setIconSize(QSize(icon_size, icon_size))
        button.setText("")

    def _apply_include_context_icon(self) -> None:
        icon_size = self._toolbar_icon_size()
        if self._include_mask.any_selected():
            icon = brain_icon(icon_size)
        else:
            icon = barred_brain_icon(icon_size)
        self._set_toolbar_icon(self.btn_include_context, icon)

    def _apply_chat_toolbar_icons(self) -> None:
        icon_size = self._toolbar_icon_size()
        self._apply_include_context_icon()
        self._set_toolbar_icon(self.btn_edit_menu, pencil_icon(icon_size))
        self._set_toolbar_icon(self.btn_import_notetype, import_icon(icon_size))
        self._set_toolbar_icon(self.btn_inspect_prompt, lens_icon(icon_size))
        self._set_toolbar_icon(self.btn_prompt_cache, cache_icon(icon_size))
        self._set_toolbar_icon(self.btn_note_preview, eye_icon(icon_size))
        self._set_toolbar_icon(self.btn_download, download_icon(icon_size))
        self._set_toolbar_icon(self.btn_clear, plus_icon(icon_size))
        self._apply_stop_before_send_icon()

    def _apply_chat_toolbar_styles(self) -> None:
        icon_style = chat_toolbar_button_stylesheet(icon_only=True)
        checkable_style = chat_toolbar_button_stylesheet(icon_only=True, checkable=True)
        self.btn_include_context.setStyleSheet(icon_style)
        self.btn_edit_menu.setStyleSheet(icon_style)
        self.btn_import_notetype.setStyleSheet(icon_style)
        self.btn_inspect_prompt.setStyleSheet(icon_style)
        self.btn_prompt_cache.setStyleSheet(icon_style)
        self.btn_note_preview.setStyleSheet(icon_style)
        self.btn_download.setStyleSheet(icon_style)
        self.btn_clear.setStyleSheet(icon_style)
        self.stop_before_send_btn.setStyleSheet(checkable_style)

    def _stop_before_send_icon(self, *, checked: bool) -> QIcon:
        icon_size = self._toolbar_icon_size()
        if checked:
            return stop_sign_icon(icon_size)
        return priority_sign_icon(icon_size)

    def _apply_stop_before_send_icon(self) -> None:
        self._set_toolbar_icon(
            self.stop_before_send_btn,
            self._stop_before_send_icon(checked=self.stop_before_send_btn.isChecked()),
        )

    def _on_modify_prompt_toggled(self, checked: bool) -> None:
        self._apply_stop_before_send_icon()
        config = load_config()
        config["chat_modify_prompt_before_send"] = bool(checked)
        save_config(config)

    def _chat_effective_config(self, config: dict[str, Any] | None = None) -> dict[str, Any]:
        merged = dict(config or load_config())
        merged["brain_import_templates"] = bool(self._include_mask.selected_template_ids())
        merged["brain_import_css"] = bool(self._include_mask.selected_css_ids())
        return merged

    def _refresh_prompt_cache_toolbar_tooltip(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        if not prompt_cache_enabled(config, "chat"):
            state_key = "chat.prompt_cache.session.tooltip.disabled"
        else:
            state_key = "chat.prompt_cache.session.tooltip.active"
        set_instruction_tooltip(
            self.btn_prompt_cache,
            tr(state_key, config=config),
        )

    def _open_prompt_cache_session_dialog(self) -> None:
        config = load_config()
        if (
            self._prompt_cache_dialog is not None
            and self._prompt_cache_dialog.isVisible()
        ):
            self._prompt_cache_dialog.raise_()
            self._prompt_cache_dialog.activateWindow()
            return
        dialog = ChatPromptCacheDialog(
            self,
            config=config,
            on_finished=self._on_prompt_cache_dialog_finished,
        )
        self._prompt_cache_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _on_prompt_cache_dialog_finished(self, accepted: bool) -> None:
        self._prompt_cache_dialog = None
        if not accepted:
            return
        self._prompt_cache_recreate_ack = None
        config = load_config()
        self._refresh_prompt_cache_toolbar_tooltip(config)
        if (
            self._prompt_preview_dialog is not None
            and self._prompt_preview_dialog.isVisible()
        ):
            self._prompt_preview_dialog.apply_context(self.build_pre_send_context())

    def _close_prompt_cache_dialog(self) -> None:
        dialog = self._prompt_cache_dialog
        if dialog is None:
            return
        self._prompt_cache_dialog = None
        dialog.blockSignals(True)
        dialog.close()

    def build_pre_send_context(self) -> PreSendPromptContext:
        config = self._chat_effective_config()
        user_text = self.input_field.toPlainText().strip()
        included_context = self._include_context_active()
        cache_session = self._prompt_cache_session(config, included_context=included_context)
        bundle = build_prompt_cache_bundle(config, purpose="chat", session=cache_session)
        if bundle is not None:
            payload_text = build_live_chat_payload(
                config,
                user_text or tr("prompt.inspect.empty_next_message", config=config),
                session=cache_session,
                bundle=bundle,
            )
        elif included_context:
            draft = user_text or tr("prompt.inspect.empty_draft", config=config)
            payload_text = self._build_outgoing_payload(config, draft)
        else:
            payload_text = user_text or tr("prompt.inspect.empty_next_message", config=config)
        system_instruction = merge_system_instructions(
            config,
            include_meta_rule=True,
            purpose="chat",
        )
        inspection = build_chat_prompt_inspection(
            config,
            history=list(self.api_history),
            next_user_text=user_text,
            outgoing_payload=payload_text,
        )
        return PreSendPromptContext(
            inspection=inspection,
            outgoing_payload=payload_text,
            system_instruction=system_instruction,
            bundle=bundle,
            model=resolve_model(config, "chat"),
            cache_session=cache_session,
        )

    def _open_prompt_preview(self) -> None:
        context = self.build_pre_send_context()
        self._prompt_preview_dialog = open_prompt_preview(
            self,
            context=context,
            refresh_context=self.build_pre_send_context,
            existing=self._prompt_preview_dialog,
        )

    def apply_settings_refresh(self) -> None:
        config = load_config()
        self._apply_history.set_max_items(
            clamp_apply_history_max(config.get("chat_apply_history_max", 7))
        )
        self.apply_language()
        self._update_settings_stale_banner(config)
        show_newlines = bool(config.get("settings_show_text_newlines", False))
        wrap = bool(config.get("settings_wrap_text_editors", True))
        refresh_settings_text_edit_newlines(self, show_newlines)
        refresh_text_edit_wrap(self, wrap)
        if self._note_edit_window is not None:
            self._note_edit_window.apply_newline_visibility(show_newlines)
            refresh_text_edit_wrap(self._note_edit_window, wrap)
        if self._wrapper_edit_window is not None:
            refresh_text_edit_wrap(self._wrapper_edit_window, wrap)
        if self._templates_edit_window is not None:
            refresh_text_edit_wrap(self._templates_edit_window, wrap)
        if self._note_preview_window is not None:
            refresh_text_edit_wrap(self._note_preview_window, wrap)
        if (
            self._prompt_preview_dialog is not None
            and self._prompt_preview_dialog.isVisible()
        ):
            self._prompt_preview_dialog.apply_context(self.build_pre_send_context())

    def _apply_chat_theme(self) -> None:
        self.setStyleSheet(tooltip_stylesheet())
        if not self._uses_web_chat_log:
            self.chat_log.document().setDefaultStyleSheet(chat_document_stylesheet())
        loading_style = loading_label_stylesheet()
        self.loading_text_label.setStyleSheet(loading_style)
        self._settings_stale_banner.setStyleSheet(settings_stale_banner_stylesheet())
        self._apply_chat_toolbar_styles()
        self._apply_chat_toolbar_icons()
        if self._note_edit_window is not None:
            self._note_edit_window.apply_theme()
        if self._wrapper_edit_window is not None:
            self._wrapper_edit_window.apply_theme()
        if self._templates_edit_window is not None:
            self._templates_edit_window.apply_theme()
        if self._include_panel is not None:
            self._include_panel.apply_theme()
        if self._note_preview_window is not None:
            self._note_preview_window.apply_theme()
        if self._field_preview_window is not None:
            self._field_preview_window.apply_theme()
        refresh_native_text_edits_in(self)
        if self.loading_row.isVisible():
            self._apply_loading_display()
        self._render_chat_log(preserve_scroll=False)

    def _apply_static_texts(self) -> None:
        config = load_config()
        self.setWindowTitle(tr("chat.title", config=config))
        set_instruction_tooltip(
            self.btn_include_context,
            tr("chat.include_context", config=config),
        )
        set_instruction_tooltip(
            self.btn_edit_menu,
            tr("chat.edit.menu.tooltip", config=config),
        )
        set_instruction_tooltip(
            self.btn_import_notetype,
            tr("chat.import_notetype.tooltip", config=config),
        )
        self._refresh_edit_menu_actions(config)
        set_instruction_tooltip(
            self.btn_note_preview,
            tr("chat.preview.open_window.tooltip", config=config),
        )
        set_instruction_tooltip(
            self.btn_clear,
            tr("chat.new_conversation", config=config),
        )
        set_instruction_tooltip(
            self.btn_inspect_prompt,
            tr("chat.inspect_prompt.tooltip", config=config),
        )
        self._refresh_prompt_cache_toolbar_tooltip(config)
        set_instruction_tooltip(
            self.btn_download,
            tr("chat.download.tooltip", config=config),
        )
        set_instruction_tooltip(
            self.stop_before_send_btn,
            tr("chat.modify_prompt_before_send.tooltip", config=config),
        )
        self.stop_before_send_btn.blockSignals(True)
        self.stop_before_send_btn.setChecked(
            bool(config.get("chat_modify_prompt_before_send", False))
        )
        self.stop_before_send_btn.blockSignals(False)
        self._apply_chat_toolbar_icons()
        self._settings_stale_banner_close.setText(tr("chat.settings_stale.dismiss", config=config))
        self._update_settings_stale_banner(config)
        if not self._uses_web_chat_log:
            self.chat_log.setPlaceholderText(tr("chat.log_placeholder", config=config))
        self.input_field.setPlaceholderText(tr("chat.input_placeholder", config=config))
        if self._request_gate.in_flight:
            self.send_button.setText(tr("chat.stop", config=config))
        else:
            self.send_button.setText(tr("chat.send", config=config))
        if self.loading_row.isVisible():
            self._apply_loading_display()
        if self._note_preview_window is not None:
            self._note_preview_window.apply_language(config)
        if self._note_edit_window is not None:
            self._note_edit_window.apply_language(config)
        if self._wrapper_edit_window is not None:
            self._wrapper_edit_window.apply_language(config)
        if self._templates_edit_window is not None:
            self._templates_edit_window.apply_language(config)
        if self._include_panel is not None:
            self._include_panel.apply_language(config)

    def _refresh_edit_menu_actions(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        has_note = bool(self._imported_notes)
        can_edit_templates = self._has_imported_templates_or_styling()
        has_context = self._has_sendable_context()
        has_apply = len(self._apply_history) > 0
        can_undo_apply = can_undo_last_note_apply()
        self._edit_note_action.setText(tr("chat.edit_note", config=config))
        self._edit_wrapper_action.setText(tr("chat.edit_wrapper", config=config))
        self._edit_templates_action.setText(tr("chat.edit_templates", config=config))
        self._apply_note_action.setText(tr("chat.apply_note.menu", config=config))
        self._undo_apply_note_action.setText(
            tr("chat.apply_note.undo.menu", config=config)
        )
        self._presets_menu_action.setText(tr("chat.presets.menu", config=config))
        self._edit_note_action.setEnabled(has_note)
        self._edit_wrapper_action.setEnabled(has_context)
        self._edit_templates_action.setEnabled(can_edit_templates)
        self._apply_note_action.setEnabled(has_apply)
        self._undo_apply_note_action.setEnabled(can_undo_apply)
        self.btn_edit_menu.setEnabled(True)

    def _rebuild_presets_menu(self) -> None:
        config = load_config()
        self._presets_menu.clear()
        presets = normalize_settings_presets(config.get("settings_presets"))
        builtin_action = self._presets_menu.addAction(
            tr("settings.presets.builtin", config=config)
        )
        builtin_action.triggered.connect(
            lambda *_: self._apply_settings_preset_from_chat(BUILTIN_SETTINGS_PRESET_ID)
        )
        if presets:
            self._presets_menu.addSeparator()
        for preset in presets:
            preset_id = str(preset.get("id") or "")
            name = str(preset.get("name") or preset_id[:8])
            action = self._presets_menu.addAction(name)
            action.triggered.connect(
                lambda *_args, pid=preset_id: self._apply_settings_preset_from_chat(pid)
            )

    def _apply_settings_preset_from_chat(self, preset_id: str) -> None:
        config = load_config()
        presets = normalize_settings_presets(config.get("settings_presets"))
        values, runtime = resolve_preset_payload(presets, preset_id)
        if preset_id == BUILTIN_SETTINGS_PRESET_ID:
            name = tr("settings.presets.builtin", config=config)
        else:
            match = next((p for p in presets if p.get("id") == preset_id), None)
            name = str((match or {}).get("name") or preset_id[:8])
        diffs = preset_diff_from_builtin(values, runtime, config=config)
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
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(tr("chat.presets.apply.title", config=config))
        box.setText(tr("chat.presets.apply.message", config=config, name=name))
        box.setInformativeText(summary)
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return
        apply_runtime = runtime is not None
        updated = apply_preset_to_config(
            config,
            values=values,
            runtime=runtime,
            apply_runtime=apply_runtime,
        )
        updated["active_settings_preset_id"] = preset_id
        updated["settings_presets"] = presets
        save_config(updated)
        refresh_chat_from_settings()
        self._add_system_message(
            tr("chat.presets.applied", config=updated, name=name),
            kind="system",
            label=tr("chat.label.system", config=updated),
        )
        self._update_settings_stale_banner(updated)

    def _preview_fields_provider(self) -> list[tuple[str, str]]:
        config = load_config()
        note_id = self._preview_note_id
        if note_id is None:
            return []
        note = self._imported_notes.get(note_id)
        if note is None:
            return []
        return fields_for_note_preview(note.fields, config)

    def _preview_notetype_id_provider(self) -> int | None:
        note_id = self._preview_note_id
        if note_id is None:
            return None
        note = self._imported_notes.get(note_id)
        return note.notetype_id if note is not None else None

    def _close_note_preview_window(self) -> None:
        if self._note_preview_window is None:
            return
        self._note_preview_window.close()
        self._note_preview_window = None
        self._preview_note_id = None

    def _open_note_preview_window(self) -> None:
        if not self._imported_notes:
            return
        config = load_config()
        note_id = pick_imported_note(
            self,
            self._imported_notes,
            config=config,
            purpose="preview",
        )
        if note_id is None:
            return
        self._preview_note_id = note_id
        note = self._imported_notes[note_id]
        if self._note_preview_window is None:
            self._note_preview_window = ImportedNotePreviewWindow(
                self,
                field_provider=self._preview_fields_provider,
                notetype_id_provider=self._preview_notetype_id_provider,
            )
            self._note_preview_window.destroyed.connect(
                lambda *_: (
                    setattr(self, "_note_preview_window", None),
                    setattr(self, "_preview_note_id", None),
                )
            )
        self._note_preview_window.apply_language(config)
        if note.display_label():
            self._note_preview_window.setWindowTitle(
                tr(
                    "chat.preview.window_title_named",
                    config=config,
                    name=note.display_label(),
                )
            )
        self._note_preview_window.apply_theme()
        self._note_preview_window.refresh()
        self._note_preview_window.show()
        self._note_preview_window.raise_()
        self._note_preview_window.activateWindow()

    def _refresh_note_preview_if_open(self) -> None:
        if self._note_preview_window is not None and self._note_preview_window.isVisible():
            self._note_preview_window.refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._refresh_body_splitter_sizes)

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
        self._close_prompt_cache_dialog()
        self._close_session_edit_windows()
        if self._uses_web_chat_log:
            cleanup_chat_log_webview(self.chat_log)
        _chat_window = None
        event.accept()
        super().closeEvent(event)

    def prepare_shutdown(self) -> None:
        self._closing = True
        self._cancel_in_flight_request()
        self._stop_loading()
        self._close_note_preview_window()
        self._close_prompt_cache_dialog()
        self._close_session_edit_windows()
        if self._uses_web_chat_log:
            cleanup_chat_log_webview(self.chat_log)
        self._stream_visible = False
        self._streaming_message_index = None

    def _render_chat_log(
        self,
        *,
        preserve_scroll: bool = False,
        scroll_anchor: int | None = None,
    ) -> None:
        document_html = render_chat_document(self._messages)
        if self._uses_web_chat_log:
            previous_scroll = chat_log_scroll_y(self.chat_log) if preserve_scroll else 0
            load_chat_log_webview(
                self.chat_log,
                document_html,
                stylesheet=chat_document_stylesheet(),
            )
            if scroll_anchor is not None:
                chat_log_set_scroll_y(self.chat_log, scroll_anchor)
            elif preserve_scroll:
                chat_log_set_scroll_y(self.chat_log, previous_scroll)
            else:
                chat_log_scroll_to_bottom(self.chat_log)
            return

        bar = self.chat_log.verticalScrollBar()
        previous_value = bar.value()
        self.chat_log.setHtml(document_html)
        if scroll_anchor is not None:
            bar.setValue(min(scroll_anchor, bar.maximum()))
        elif preserve_scroll:
            bar.setValue(min(previous_value, bar.maximum()))
        else:
            self.chat_log.moveCursor(self.chat_log.textCursor().MoveOperation.End)

    def _scroll_to_streaming_message_start(self) -> None:
        if self._uses_web_chat_log:
            chat_log_scroll_to_last_gemini_label(self.chat_log)
            return
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
            label = tr("chat.label.system", config=load_config())
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

    def _copy_codeblock(self, block_id: str) -> None:
        content = stored_block_text(self._copy_blocks.get(block_id))
        if content is None:
            return
        QApplication.clipboard().setText(content)
        tooltip(tr("chat.copied", config=load_config()))

    def _preview_codeblock(self, block_id: str) -> None:
        stored = self._copy_blocks.get(block_id)
        content = stored_block_text(stored)
        if content is None:
            return
        label = stored_block_label(stored) or tr(
            "formatter.code_block",
            config=load_config(),
        )
        self._field_preview_payload = [(label, content)]
        config = load_config()
        if self._field_preview_window is None:
            self._field_preview_window = ImportedNotePreviewWindow(
                self,
                field_provider=lambda: list(self._field_preview_payload),
            )
            self._field_preview_window.destroyed.connect(
                lambda *_args: setattr(self, "_field_preview_window", None)
            )
        self._field_preview_window.apply_language(config)
        self._field_preview_window.setWindowTitle(
            tr("formatter.preview.window_title", config=config, name=label)
        )
        self._field_preview_window.apply_theme()
        self._field_preview_window.refresh()
        self._field_preview_window.show()
        self._field_preview_window.raise_()
        self._field_preview_window.activateWindow()

    def _on_chat_log_bridge_cmd(self, cmd: str) -> None:
        if cmd.startswith("addon-chat-copy:"):
            self._copy_codeblock(cmd[len("addon-chat-copy:") :])
        elif cmd.startswith("addon-chat-preview:"):
            self._preview_codeblock(cmd[len("addon-chat-preview:") :])

    def _on_anchor_clicked(self, url: QUrl) -> None:
        url_str = url.toString()
        if url_str.startswith("copy:"):
            self._copy_codeblock(url_str[5:])
        elif url_str.startswith("preview:"):
            self._preview_codeblock(url_str[8:])

    def eventFilter(self, obj, event):
        if obj is self.input_field and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    return super().eventFilter(obj, event)
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def _conversation_has_clearable_content(self) -> bool:
        if self.api_history:
            return True
        if self.note_context or self._imported_notes or self._imported_notetypes:
            return True
        return any(
            message.label_class in ("chat-label-you", "chat-label-gemini")
            for message in self._messages
        )

    def _refresh_download_menu(self) -> None:
        config = load_config()
        self._download_menu.clear()

        last_directory = chat_export_last_used_directory(config)
        if last_directory is not None:
            last_text = format_export_folder_menu_text(
                last_directory,
                config=config,
                prefix_key="chat.download.menu.last_used",
            )
        else:
            last_text = tr("chat.download.menu.last_used.unavailable", config=config)
        last_action = self._download_menu.addAction(last_text)
        last_action.setEnabled(last_directory is not None)
        if last_directory is not None:
            last_action.triggered.connect(
                lambda *_args, directory=last_directory: self._download_chat_to_directory(
                    directory
                )
            )

        quick_folders = normalize_chat_export_quick_folders(
            config.get("chat_export_quick_folders")
        )
        if quick_folders:
            self._download_menu.addSeparator()
            for folder in quick_folders:
                folder_path = Path(str(folder.get("path") or ""))
                label = str(folder.get("label") or folder_path.name)
                action = self._download_menu.addAction(label)
                action.setToolTip(str(folder_path))
                action.triggered.connect(
                    lambda *_args, directory=folder_path: self._download_chat_to_directory(
                        directory
                    )
                )

        self._download_menu.addSeparator()
        browse_action = self._download_menu.addAction(
            tr("chat.download.menu.browse", config=config)
        )
        browse_action.triggered.connect(self._download_chat_browse)

    def _build_chat_export_text(self) -> str:
        config = load_config()
        return format_chat_export_text(
            self._messages,
            config,
            api_history=self.api_history,
        )

    def _persist_chat_export_directory(self, directory: Path) -> None:
        config = load_config()
        updated = dict(config)
        updated["chat_download_directory"] = str(directory)
        save_config(updated)

    def _download_chat_to_directory(self, directory: Path) -> None:
        config = load_config()
        text = self._build_chat_export_text()
        if not text.strip():
            return
        try:
            export_path = save_chat_export_text_to_directory(
                text,
                directory,
                config=config,
            )
        except OSError as exc:
            showWarning(tr("chat.download.error", config=config, error=exc))
            return
        self._persist_chat_export_directory(export_path.parent)
        tooltip(tr("chat.download.saved", config=config))

    def _download_chat_browse(self) -> None:
        config = load_config()
        text = self._build_chat_export_text()
        if not text.strip():
            return

        start_dir = str(config.get("chat_download_directory") or "").strip()
        if not start_dir:
            start_dir = str(default_chat_download_directory())
        default_name = default_chat_export_filename()
        initial_path = str(Path(start_dir) / default_name)

        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            tr("chat.download.title", config=config),
            initial_path,
            tr("chat.download.filter", config=config),
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as exc:
            showWarning(tr("chat.download.error", config=config, error=exc))
            return

        self._persist_chat_export_directory(Path(path).parent)
        tooltip(tr("chat.download.saved", config=config))

    def _confirm_new_conversation(self, config: dict[str, Any]) -> bool:
        if is_warning_dismissed(config, "suppress_chat_new_conversation_confirm_warning"):
            return True
        if not self._conversation_has_clearable_content():
            return True

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr("chat.new_conversation.confirm.title", config=config))
        box.setText(tr("chat.new_conversation.confirm.message", config=config))
        box.setInformativeText(tr("chat.new_conversation.confirm.detail", config=config))
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
            updated["suppress_chat_new_conversation_confirm_warning"] = True
            save_config(updated)

        return True

    def clear_conversation(self) -> None:
        config = load_config()
        cache_choice = confirm_new_conversation_cache_if_needed(self, config)
        if cache_choice == "abort":
            return
        if not self._confirm_new_conversation(config):
            return
        if self._request_gate.in_flight:
            self._request_gate.invalidate()
            self._restorable_user_text = ""
            self._cancel_in_flight_request()
        self.api_history.clear()
        self.note_context = None
        self._imported_notes = {}
        self._imported_notetypes = {}
        self._imported_card_templates = []
        self._imported_notetype_css = ""
        self._imported_notetype_id = None
        self._preview_note_id = None
        self._include_mask = IncludeNextMessageMask()
        self._pending_apply_batch = None
        self._pending_apply_plan = None
        self._apply_history.clear()
        clear_apply_undo()
        self._refresh_edit_menu_actions()
        self._session_wrapper_override = None
        self._prompt_cache_recreate_ack = None
        self._messages.clear()
        self._copy_blocks.clear()
        self._stream_visible = False
        self._streaming_message_index = None
        self.btn_include_context.setEnabled(False)
        self._apply_include_context_icon()
        self._refresh_edit_menu_actions()
        self._close_session_edit_windows()
        self._on_body_section_visibility_changed()
        if cache_choice == "clear":
            clear_prompt_cache(config=config, purpose="chat")
        self._close_note_preview_window()
        if self._field_preview_window is not None:
            self._field_preview_window.close()
            self._field_preview_window = None
        self.btn_note_preview.setEnabled(False)
        self._add_system_message(
            tr("chat.cleared", config=config),
            kind="system",
            label=tr("chat.label.system", config=config),
        )
        self._capture_session_config()

    def import_note_from_editor(self, editor) -> None:
        note = editor.note
        imported = imported_note_from_anki_note(note)
        config = load_config()
        if imported is None:
            self._add_system_message(
                tr("chat.note_empty", config=config),
                kind="error",
                label=tr("chat.label.system", config=config),
            )
            return
        self.import_notes([imported], set_brain_message=True)

    def import_notes_by_ids(self, note_ids: list[int]) -> None:
        config = load_config()
        if mw.col is None:
            return
        incoming: list[ImportedNoteData] = []
        empty_count = 0
        for note_id in note_ids:
            try:
                note = mw.col.get_note(note_id)
            except Exception:
                continue
            imported = imported_note_from_anki_note(note)
            if imported is None:
                empty_count += 1
                continue
            incoming.append(imported)
        if not incoming:
            showWarning(
                tr("chat.import_notes.empty_selection", config=config),
                parent=self,
            )
            return
        self.import_notes(incoming, set_brain_message=True)
        if empty_count:
            self._add_system_message(
                tr(
                    "chat.import_notes.skipped_empty",
                    config=config,
                    count=empty_count,
                ),
                kind="system",
                label=tr("chat.label.system", config=config),
            )

    def import_notes(
        self,
        notes: list[ImportedNoteData],
        *,
        set_brain_message: bool = False,
    ) -> None:
        if not notes:
            return
        config = load_config()
        import_cache_choice = confirm_import_note_cache_if_needed(self, config)
        if import_cache_choice == "abort":
            return

        self._imported_notes = merge_imported_notes(self._imported_notes, notes)
        self._imported_notetype_id = notes[-1].notetype_id
        self._refresh_edit_menu_actions()

        for note in notes:
            notetype_data = imported_notetype_from_id(note.notetype_id)
            if notetype_data is None:
                notetype_data = ImportedNotetypeData(
                    notetype_id=note.notetype_id,
                    name=note.notetype_name,
                    field_names=[name for name, _value in note.fields],
                )
            elif not note.notetype_name and notetype_data.name:
                note.notetype_name = notetype_data.name
            self._register_imported_notetype(
                notetype_data,
                include_templates=True,
                include_css=True,
            )

        # Refresh labels after notetype names are known.
        refreshed: list[ImportedNoteData] = []
        for note in notes:
            current = self._imported_notes.get(note.note_id, note)
            type_data = self._imported_notetypes.get(current.notetype_id)
            name = (
                (type_data.name if type_data is not None else "")
                or current.notetype_name
            )
            refreshed.append(
                ImportedNoteData(
                    note_id=current.note_id,
                    notetype_id=current.notetype_id,
                    notetype_name=name,
                    fields=list(current.fields),
                )
            )
        self._imported_notes = merge_imported_notes(self._imported_notes, refreshed)

        self._session_wrapper_override = None
        self._prompt_cache_recreate_ack = None
        if import_cache_choice == "proceed":
            clear_prompt_cache(config=config, purpose="chat")
        self._apply_default_mask_for_note_import([note.note_id for note in notes])
        self._rebuild_note_context(config)
        self._close_session_edit_windows()
        self._refresh_import_controls(config)
        if len(notes) == 1:
            message = tr("chat.note_imported", config=config)
        else:
            message = tr(
                "chat.notes_imported",
                config=config,
                count=len(notes),
            )
        self._add_system_message(
            message,
            kind="system",
            label=tr("chat.label.system", config=config),
        )

        self.btn_note_preview.setEnabled(True)
        self._on_body_section_visibility_changed()
        if set_brain_message:
            self.input_field.setPlainText(effective_brain_import_message(config))
        self.input_field.setFocus()

    def _open_notetype_import_dialog(self) -> None:
        config = load_config()
        import_cache_choice = confirm_import_note_cache_if_needed(self, config)
        if import_cache_choice == "abort":
            return
        selection = confirm_notetype_import(self, config=config)
        if selection is None:
            return
        incoming: list[ImportedNotetypeData] = []
        for notetype_id in selection.notetype_ids:
            data = imported_notetype_from_id(
                notetype_id,
                include_templates=selection.include_templates,
                include_css=selection.include_css,
            )
            if data is not None:
                incoming.append(data)
        if not incoming:
            return
        self._imported_notetypes = merge_imported_notetypes(
            self._imported_notetypes,
            incoming,
        )
        self._sync_legacy_notetype_cache()
        self._refresh_edit_menu_actions()
        self._prompt_cache_recreate_ack = None
        if import_cache_choice == "proceed":
            clear_prompt_cache(config=config, purpose="chat")
        self._apply_default_mask_for_notetype_import(incoming)
        self._rebuild_note_context(config)
        self._close_session_edit_windows()
        self._refresh_import_controls(load_config())
        names = ", ".join(data.name for data in incoming)
        self._add_system_message(
            tr(
                "chat.import_notetype.imported",
                config=config,
                count=len(incoming),
                names=names,
            ),
            kind="system",
            label=tr("chat.label.system", config=config),
        )
        self._configure_chat_default_buttons()
        self._on_body_section_visibility_changed()
        self.input_field.setFocus()

    def _refresh_import_controls(self, config: dict[str, Any]) -> None:
        if not self._has_imported_templates_or_styling():
            self._close_templates_edit_window()
        self._refresh_edit_menu_actions(config)

    def _rebuild_note_context(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        self.note_context = self._context_for_message(config) or None

    def _context_for_message(self, config: dict[str, Any]) -> str:
        parts: list[str] = []
        selected_note_ids = set(self._include_mask.selected_note_ids())
        if selected_note_ids:
            field_context = format_imported_notes_context(
                self._imported_notes,
                config,
                include_note_ids=selected_note_ids,
            )
            if field_context:
                parts.append(field_context)
        selected_schema_ids = set(self._include_mask.selected_schema_ids())
        if selected_schema_ids:
            selected = [
                data
                for data in self._imported_notetypes.values()
                if data.notetype_id in selected_schema_ids
            ]
            schema_block = format_notetype_schemas_block(selected, config=config)
            if schema_block:
                parts.append(schema_block)
        return "\n\n".join(parts)

    def _commit_open_session_editors(self) -> bool:
        if self._note_edit_window is not None and self._note_edit_window.isVisible():
            self._note_edit_window.commit()
        if self._wrapper_edit_window is not None and self._wrapper_edit_window.isVisible():
            if not self._wrapper_edit_window.commit():
                return False
        if self._templates_edit_window is not None and self._templates_edit_window.isVisible():
            if not self._templates_edit_window.commit():
                return False
        return True

    def _wrapper_editor_config(self, config: dict[str, Any]) -> dict[str, Any]:
        if self._session_wrapper_override is None:
            return config
        merged = dict(config)
        merged["prompt_chat_context_order"] = self._session_wrapper_override.get("order")
        merged["prompt_chat_context_sections"] = self._session_wrapper_override.get("sections", {})
        format_guide = self._session_wrapper_override.get("format_guide")
        if format_guide is not None:
            merged["prompt_card_templates_format"] = format_guide
        return merged

    def _session_wrapper_kwargs(self, config: dict[str, Any]) -> dict[str, Any]:
        if self._session_wrapper_override is None:
            return {}
        return {
            "section_order": list(self._session_wrapper_override.get("order") or []),
            "section_prefixes": dict(self._session_wrapper_override.get("sections") or {}),
            "format_guide": self._session_wrapper_override.get("format_guide"),
        }

    def _cache_impact_include_context(self, config: dict[str, Any]) -> bool:
        """Whether session materials should be considered for cache recreate checks."""
        if self._include_context_active():
            return True
        if not has_tracked_active_cache("chat"):
            return False
        if not chat_cache_includes_session_content(config):
            return False
        return bool(
            self._imported_notes
            or self._imported_notetypes
            or self._imported_card_templates
            or self._imported_notetype_css.strip()
        )

    def _resolve_chat_cache_recreate(
        self,
        config: dict[str, Any],
        session: PromptCacheSessionContext,
        *,
        prompt_context: PromptCacheRecreatePromptContext = "send",
    ):
        bundle = build_prompt_cache_bundle(config, purpose="chat", session=session)
        choice, ack = resolve_prompt_cache_recreate_choice(
            self,
            config,
            bundle,
            purpose="chat",
            acknowledgment=self._prompt_cache_recreate_ack,
            prompt_context=prompt_context,
        )
        if choice != "abort":
            self._prompt_cache_recreate_ack = ack
        return choice

    def _prompt_cache_session(
        self,
        config: dict[str, Any],
        *,
        included_context: bool,
    ) -> PromptCacheSessionContext:
        override = self._session_wrapper_override
        return PromptCacheSessionContext(
            note_context=self._context_for_message(config) if included_context else "",
            templates_block=self._templates_for_message(config) if included_context else "",
            styling_block=self._styling_for_message(config) if included_context else "",
            include_note_context=included_context,
            wrapper_section_order=list(override["order"]) if override else None,
            wrapper_section_prefixes=(
                dict(override.get("sections") or {}) if override else None
            ),
            wrapper_format_guide=override.get("format_guide") if override else None,
        )

    def _build_outgoing_payload(self, config: dict[str, Any], user_text: str) -> str:
        included = self._include_context_active()
        if included:
            self._commit_open_session_editors()
            self._rebuild_note_context(config)
        context = self._context_for_message(config) if included else ""
        return format_chat_context_message(
            config,
            context=context,
            request=user_text,
            templates=self._templates_for_message(config) if included else "",
            styling=self._styling_for_message(config) if included else "",
            include_context=included,
            **self._session_wrapper_kwargs(config),
        )

    def _confirm_large_chat_payload(self, config: dict[str, Any], char_count: int) -> bool:
        threshold = int(config.get("chat_payload_warning_chars", 12000))
        if char_count <= threshold:
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr("chat.large_payload.title", config=config))
        box.setText(
            tr(
                "chat.large_payload.message",
                config=config,
                count=char_count,
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
        selected_ids = set(self._include_mask.selected_template_ids())
        if not selected_ids:
            return ""
        if self._imported_notetypes:
            return format_imported_notetype_templates(
                self._imported_notetypes,
                config,
                include_notetype_ids=selected_ids,
            )
        if not self._imported_card_templates:
            return ""
        return format_card_templates_block(self._imported_card_templates, config)

    def _styling_for_message(self, config: dict[str, Any]) -> str:
        selected_ids = set(self._include_mask.selected_css_ids())
        if not selected_ids:
            return ""
        if self._imported_notetypes:
            return format_imported_notetype_styling(
                self._imported_notetypes,
                config,
                include_notetype_ids=selected_ids,
            )
        return self._imported_notetype_css.strip()

    def _open_templates_edit_window(self) -> None:
        config = load_config()
        candidates = editable_templates_notetypes(self._imported_notetypes)
        notetype_id: int | None = None
        notetype_name: str | None = None
        templates: list[CardTemplateData] = []
        styling = ""

        if candidates:
            notetype_id = pick_templates_notetype(self, candidates, config=config)
            if notetype_id is None:
                return
            data = self._imported_notetypes[notetype_id]
            notetype_name = data.name
            templates = list(data.templates)
            styling = data.css
        else:
            templates = list(self._imported_card_templates)
            styling = self._imported_notetype_css

        if not templates and not styling.strip():
            showWarning(tr("chat.edit_templates.empty", config=config), parent=self)
            return
        try:
            if self._templates_edit_window is None:
                self._templates_edit_window = ChatTemplatesEditWindow(
                    self,
                    on_save=self._apply_templates_edit,
                )
                self._templates_edit_window.destroyed.connect(
                    lambda *_: setattr(self, "_templates_edit_window", None)
                )
            self._templates_edit_window.load(
                templates,
                styling,
                notetype_id=notetype_id,
                notetype_name=notetype_name,
            )
            self._templates_edit_window.apply_language(config)
            self._templates_edit_window.apply_theme()
            self._templates_edit_window.show()
            self._templates_edit_window.raise_()
            self._templates_edit_window.activateWindow()
        except Exception as exc:
            showWarning(
                tr(
                    "chat.edit_templates.open_failed",
                    config=config,
                    error=str(exc),
                ),
                parent=self,
            )

    def _close_templates_edit_window(self) -> None:
        if self._templates_edit_window is None:
            return
        self._templates_edit_window.close()
        self._templates_edit_window = None

    def _apply_templates_edit(
        self,
        templates: list[CardTemplateData],
        styling: str,
        notetype_id: int | None = None,
    ) -> bool:
        target_id = notetype_id
        if target_id is None or target_id not in self._imported_notetypes:
            target_id = primary_templates_notetype_id(
                self._imported_notetypes,
                preferred_id=self._imported_notetype_id,
            )

        provisional_notetypes = dict(self._imported_notetypes)
        provisional_legacy_templates = list(self._imported_card_templates)
        provisional_legacy_css = self._imported_notetype_css

        if target_id is not None and target_id in self._imported_notetypes:
            current = self._imported_notetypes[target_id]
            resolved_name = current.name
            saved_templates = [
                CardTemplateData(
                    name=item.name,
                    front=item.front,
                    back=item.back,
                    notetype_name=(item.notetype_name or "").strip() or resolved_name,
                )
                for item in templates
            ]
            provisional_notetypes[target_id] = ImportedNotetypeData(
                notetype_id=current.notetype_id,
                name=current.name,
                field_names=list(current.field_names),
                templates=saved_templates,
                css=styling,
            )
        else:
            provisional_legacy_templates = list(templates)
            provisional_legacy_css = styling

        config = load_config()
        included = self._cache_impact_include_context(config)
        saved_notetypes = self._imported_notetypes
        saved_templates = self._imported_card_templates
        saved_css = self._imported_notetype_css
        self._imported_notetypes = provisional_notetypes
        self._imported_card_templates = provisional_legacy_templates
        self._imported_notetype_css = provisional_legacy_css
        try:
            session = self._prompt_cache_session(config, included_context=included)
            if (
                self._resolve_chat_cache_recreate(
                    config,
                    session,
                    prompt_context="session_edit",
                )
                == "abort"
            ):
                return False
        finally:
            self._imported_notetypes = saved_notetypes
            self._imported_card_templates = saved_templates
            self._imported_notetype_css = saved_css

        self._imported_notetypes = provisional_notetypes
        if target_id is not None and target_id in provisional_notetypes:
            self._sync_legacy_notetype_cache()
        else:
            self._imported_card_templates = provisional_legacy_templates
            self._imported_notetype_css = provisional_legacy_css
        return True

    def _open_wrapper_edit_window(self) -> None:
        config = self._chat_effective_config()
        if self._wrapper_edit_window is None:
            self._wrapper_edit_window = ChatWrapperEditWindow(
                self,
                on_save=self._apply_wrapper_edit,
            )
            self._wrapper_edit_window.destroyed.connect(
                lambda *_: setattr(self, "_wrapper_edit_window", None)
            )
        self._wrapper_edit_window.load_from_config(self._wrapper_editor_config(config))
        self._wrapper_edit_window.apply_language(config)
        self._wrapper_edit_window.apply_theme()
        self._wrapper_edit_window.show()
        self._wrapper_edit_window.raise_()
        self._wrapper_edit_window.activateWindow()

    def _close_wrapper_edit_window(self) -> None:
        if self._wrapper_edit_window is None:
            return
        self._wrapper_edit_window.close()
        self._wrapper_edit_window = None

    def _open_note_apply_dialog(self) -> None:
        if len(self._apply_history) == 0:
            return
        config = load_config()
        self._apply_history.set_max_items(
            clamp_apply_history_max(config.get("chat_apply_history_max", 7))
        )

        def on_apply(plan: NoteApplyPlan):
            result = execute_note_apply_plan(plan, config=config)
            if result.ok and result.mode == "update" and result.note_id is not None:
                self._refresh_imported_note_after_apply(result.note_id)
            self._pending_apply_plan = plan if result.ok else self._pending_apply_plan
            self._messages.append(
                ChatMessage(
                    label_class=(
                        "chat-label-system" if result.ok else "chat-label-error"
                    ),
                    label=tr("chat.label.system", config=config),
                    body_html=html.escape(
                        tr(
                            result.message_key,
                            config=config,
                            **result.message_kwargs,
                        )
                    ),
                    trailing_spacer=True,
                )
            )
            self._render_chat_log(preserve_scroll=True)
            self._refresh_edit_menu_actions(config)
            return result

        def on_undo():
            result = undo_last_note_apply(config=config)
            if result.ok and result.note_id is not None:
                self._refresh_imported_note_after_apply(result.note_id)
            self._messages.append(
                ChatMessage(
                    label_class=(
                        "chat-label-system" if result.ok else "chat-label-error"
                    ),
                    label=tr("chat.label.system", config=config),
                    body_html=html.escape(
                        tr(
                            result.message_key,
                            config=config,
                            **result.message_kwargs,
                        )
                    ),
                    trailing_spacer=True,
                )
            )
            self._render_chat_log(preserve_scroll=True)
            self._refresh_edit_menu_actions(config)
            return result

        dialog = open_note_apply_dialog(
            self,
            self._apply_history,
            on_apply=on_apply,
            on_undo=on_undo,
            imported_notes=self._imported_notes,
            session_notetypes=list(self._imported_notetypes.values()),
            config=config,
            existing=self._note_apply_dialog,
        )
        if dialog is not None and dialog is not self._note_apply_dialog:
            self._note_apply_dialog = dialog
            dialog.destroyed.connect(
                lambda *_: setattr(self, "_note_apply_dialog", None)
            )
        self._refresh_edit_menu_actions(config)

    def _undo_last_note_apply(self) -> None:
        if not can_undo_last_note_apply():
            return
        config = load_config()
        result = undo_last_note_apply(config=config)
        if result.ok and result.note_id is not None:
            self._refresh_imported_note_after_apply(result.note_id)
        self._messages.append(
            ChatMessage(
                label_class=("chat-label-system" if result.ok else "chat-label-error"),
                label=tr("chat.label.system", config=config),
                body_html=html.escape(
                    tr(
                        result.message_key,
                        config=config,
                        **result.message_kwargs,
                    )
                ),
                trailing_spacer=True,
            )
        )
        self._render_chat_log(preserve_scroll=True)
        self._refresh_edit_menu_actions(config)
        dialog = self._note_apply_dialog
        if dialog is not None:
            try:
                dialog.refresh_actions()
            except Exception:
                pass

    def _refresh_imported_note_after_apply(self, note_id: int) -> None:
        """Keep chat's imported note copy in sync after a collection update."""
        if mw.col is None:
            return
        try:
            note = mw.col.get_note(note_id)
        except Exception:
            return
        imported = imported_note_from_anki_note(note)
        if imported is None:
            return
        self._imported_notes = merge_imported_notes(self._imported_notes, [imported])
        edit_window = self._note_edit_window
        if (
            edit_window is not None
            and getattr(edit_window, "_note_id", None) == note_id
        ):
            edit_window.load_fields(
                imported.fields,
                note_id=imported.note_id,
                note_label=imported.display_label(),
            )

    def _open_note_edit_window(self) -> None:
        if not self._imported_notes:
            return
        config = load_config()
        note_id = pick_imported_note(
            self,
            self._imported_notes,
            config=config,
            purpose="edit",
        )
        if note_id is None:
            return
        note = self._imported_notes[note_id]
        if self._note_edit_window is None:
            self._note_edit_window = ChatNoteEditWindow(
                self,
                on_save=self._apply_note_edit,
            )
            self._note_edit_window.destroyed.connect(
                lambda *_: setattr(self, "_note_edit_window", None)
            )
        self._note_edit_window.load_fields(
            note.fields,
            note_id=note.note_id,
            note_label=note.display_label(),
        )
        self._note_edit_window.apply_language(config)
        self._note_edit_window.apply_theme()
        self._note_edit_window.show()
        self._note_edit_window.raise_()
        self._note_edit_window.activateWindow()

    def _close_note_edit_window(self) -> None:
        if self._note_edit_window is None:
            return
        self._note_edit_window.close()
        self._note_edit_window = None

    def _apply_note_edit(
        self,
        fields: list[tuple[str, str]],
        send_empty_fields: bool,
        note_id: int | None = None,
    ) -> None:
        config = load_config()
        config["chat_send_empty_fields"] = bool(send_empty_fields)
        save_config(config)
        if note_id is None or note_id not in self._imported_notes:
            return
        current = self._imported_notes[note_id]
        self._imported_notes[note_id] = ImportedNoteData(
            note_id=current.note_id,
            notetype_id=current.notetype_id,
            notetype_name=current.notetype_name,
            fields=list(fields),
        )
        self._rebuild_note_context()
        if self._preview_note_id == note_id:
            self._refresh_note_preview_if_open()
        if self._include_panel is not None and self._include_panel.isVisible():
            self._reload_include_panel()

    def _close_session_edit_windows(self) -> None:
        self._close_note_edit_window()
        self._close_wrapper_edit_window()
        self._close_templates_edit_window()
        self._close_note_apply_dialog()
        self._close_include_panel()

    def _close_note_apply_dialog(self) -> None:
        dialog = self._note_apply_dialog
        if dialog is None:
            return
        try:
            dialog.close()
        except RuntimeError:
            pass
        self._note_apply_dialog = None

    def _apply_wrapper_edit(
        self,
        order: list[str],
        sections: dict[str, str],
        format_guide: str,
    ) -> bool:
        config = load_config()
        stored_sections = normalize_wrapper_sections_for_save(sections, config=config)
        stored_format = format_guide.strip()
        format_builtin = is_builtin_card_templates_format_prompt(stored_format)
        if (
            is_builtin_wrapper_layout(
                config,
                section_order=order,
                section_prefixes=stored_sections,
            )
            and (format_builtin or not stored_format)
        ):
            provisional_override: dict[str, Any] | None = None
        else:
            provisional_override = {
                "order": order,
                "sections": dict(sections),
                "format_guide": format_guide,
            }

        included = self._cache_impact_include_context(config)
        saved_override = self._session_wrapper_override
        self._session_wrapper_override = provisional_override
        try:
            session = self._prompt_cache_session(config, included_context=included)
            if (
                self._resolve_chat_cache_recreate(
                    config,
                    session,
                    prompt_context="session_edit",
                )
                == "abort"
            ):
                return False
        finally:
            self._session_wrapper_override = saved_override

        self._session_wrapper_override = provisional_override
        return True

    def _on_send_button_clicked(self) -> None:
        if self._request_gate.in_flight:
            self._cancel_in_flight_request()
            return
        self.send_message()

    def _cancel_in_flight_request(self) -> None:
        if not self._request_gate.request_cancel():
            return
        self._start_stopping()
        self.send_button.setEnabled(False)

    def _begin_request(self) -> None:
        self._request_gate.set_in_flight(True)
        config = load_config()
        self.send_button.setText(tr("chat.stop", config=config))
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(False)
        self.btn_clear.setEnabled(False)

    def _end_request(self) -> None:
        self._request_gate.set_in_flight(False)
        config = load_config()
        self.send_button.setText(tr("chat.send", config=config))
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self._configure_chat_default_buttons()

    def _notify_prompt_cache_created(self, active) -> None:
        if self._closing:
            return
        config = load_config()
        from ..prompt_cache import prompt_cache_created_stats

        chars, minutes = prompt_cache_created_stats(active)
        self._add_system_message(
            tr(
                "chat.prompt_cache.created",
                config=config,
                chars=chars,
                minutes=minutes,
            ),
            kind="system",
            label=tr("chat.label.system", config=config),
        )

    def _schedule_prompt_cache_created_notice(self, active) -> None:
        mw.taskman.run_on_main(lambda cache=active: self._notify_prompt_cache_created(cache))

    def send_message(self) -> None:
        if self._request_gate.in_flight:
            return

        user_text = self.input_field.toPlainText().strip()
        if not user_text:
            return

        config = self._chat_effective_config()
        try:
            pre_send_context = self.build_pre_send_context()
            included_context = self._include_context_active()
            payload_text = pre_send_context.outgoing_payload
            system_instruction = pre_send_context.system_instruction
            bundle = pre_send_context.bundle
            cache_session = pre_send_context.cache_session
            pre_send_overrides = None
            if bool(config.get("chat_modify_prompt_before_send", False)):
                pre_send_overrides = confirm_pre_send_prompt(
                    self,
                    context=pre_send_context,
                )
                if pre_send_overrides is None:
                    return
                payload_text = pre_send_overrides.outgoing_payload
                system_instruction = pre_send_overrides.system_instruction
                if pre_send_overrides.bundle is not None:
                    bundle = pre_send_overrides.bundle
            cache_choice = self._resolve_chat_cache_recreate(
                config,
                cache_session,
                prompt_context="send",
            )
            if cache_choice == "abort":
                return
            allow_cache_create = (
                cache_choice != "skip_cache"
                and prompt_cache_enabled(config, "chat")
            )
            allow_cache_use = cache_choice != "skip_cache"
            if bundle is not None and not allow_cache_use:
                system_instruction, payload_text = flatten_bundle_for_live_send(
                    config,
                    bundle,
                    purpose="chat",
                    include_meta_rule=True,
                    system_instruction_override=(
                        system_instruction if pre_send_overrides is not None else None
                    ),
                    outgoing_payload_override=(
                        payload_text if pre_send_overrides is not None else None
                    ),
                    user_text=user_text,
                    session=cache_session,
                )
            max_turns = int(config.get("max_history_turns", 10))
            history_for_request = trim_history(self.api_history, max_turns)
            char_count = estimate_chat_request_chars(
                payload_text,
                history_for_request,
                system_instruction=system_instruction,
            )
            if not self._confirm_large_chat_payload(config, char_count):
                return
        except Exception as exc:
            showWarning(
                tr("chat.send_failed", config=config, error=str(exc)),
                parent=self,
            )
            self._configure_chat_default_buttons()
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
        try:
            self._close_session_edit_windows()

            if not api_key_configured(config):
                self._add_system_message(
                    tr("chat.api_key_missing", config=config),
                    kind="error",
                    label=tr("chat.label.system", config=config),
                )
                self._end_request()
                return

            if included_context:
                self._include_mask.clear_selections()
                self._refresh_include_context_button()
                self._rebuild_note_context(config)

            self.api_history.append({"role": "user", "parts": [{"text": payload_text}]})
            history_for_request = trim_history(self.api_history[:-1], max_turns)
            temperature = float(config.get("temperature_chat", 0.2))
            use_streaming = bool(config.get("chat_streaming", False))
            cancel_check = self._request_gate.should_cancel
            register_response = self._request_gate.register_response
            request_token = self._request_gate.issue_token()
            request_kwargs = {
                "config": config,
                "user_text": user_text,
                "history": history_for_request,
                "temperature": temperature,
                "include_meta_rule": True,
                "cache_session": cache_session,
                "allow_prompt_cache_create": allow_cache_create,
                "allow_prompt_cache_use": allow_cache_use,
                "on_prompt_cache_created": self._schedule_prompt_cache_created_notice,
                "should_cancel": cancel_check,
                "register_response": register_response,
            }
            if pre_send_overrides is not None or (not allow_cache_use and bundle is not None):
                request_kwargs["override_outgoing_payload"] = payload_text
                request_kwargs["override_system_instruction"] = system_instruction
                if allow_cache_use and bundle is not None:
                    request_kwargs["override_bundle"] = bundle

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
        except Exception as exc:
            showWarning(
                tr("chat.send_failed", config=config, error=str(exc)),
                parent=self,
            )
            self._end_request()

    def _handle_stream_chunk_safe(self, accumulated: str) -> None:
        if self._closing or self._request_gate.should_cancel():
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
        had_apply_tags = apply_note_tags_present(display_text)
        display_text, apply_batch = extract_apply_note(display_text)
        rules_updated = False

        if dynamic_rules is not None:
            config["dynamic_instructions"] = dynamic_rules
            save_config(config)
            rules_updated = True

        if apply_batch is not None:
            self._pending_apply_batch = apply_batch
            self._pending_apply_plan = None
            self._apply_history.set_max_items(
                clamp_apply_history_max(config.get("chat_apply_history_max", 7))
            )
            self._apply_history.extend_from_batch(apply_batch)
            preview_text = format_apply_batch_for_display(apply_batch, config=config)
            if preview_text.strip() and not prose_contains_labeled_field_fences(
                display_text
            ):
                if display_text.strip():
                    display_text = f"{display_text.rstrip()}\n\n{preview_text}"
                else:
                    display_text = preview_text
            self._refresh_edit_menu_actions(config)

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

        if apply_batch is not None:
            self._messages.append(
                ChatMessage(
                    label_class="chat-label-system",
                    label=tr("chat.label.system", config=config),
                    body_html=html.escape(
                        tr(
                            "chat.apply_note.detected",
                            config=config,
                            count=apply_batch.note_count,
                            fields=apply_batch.field_names_summary(),
                        )
                    ),
                    trailing_spacer=True,
                )
            )
        elif had_apply_tags:
            self._messages.append(
                ChatMessage(
                    label_class="chat-label-error",
                    label=tr("chat.label.system", config=config),
                    body_html=html.escape(
                        tr("chat.apply_note.parse_failed", config=config)
                    ),
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
        if not self._request_gate.should_handle(request_token, closing=self._closing):
            self._stop_loading()
            self._end_request()
            return
        self._stop_loading()
        cancelled = self._request_gate.should_cancel()

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
        if not self._request_gate.in_flight:
            self.send_button.setEnabled(enabled)

    def _start_loading(self) -> None:
        self._loading_mode = "typing"
        self._loading_phase = 0
        self._loading_rotation_degrees = 0
        self.loading_row.setVisible(True)
        self._update_loading_animation()
        self.loading_timer.start(400)

    def _start_stopping(self) -> None:
        self._loading_mode = "stopping"
        self._loading_phase = 0
        self.loading_row.setVisible(True)
        self._update_loading_animation()
        if not self.loading_timer.isActive():
            self.loading_timer.start(400)

    def _stop_loading(self) -> None:
        self.loading_timer.stop()
        self.loading_row.setVisible(False)
        self._loading_mode = None

    def _loading_base_text(self) -> str:
        config = load_config()
        if self._loading_mode == "stopping":
            return tr("chat.stopping", config=config)
        return tr("chat.loading", config=config)

    def _apply_loading_display(self) -> None:
        dots = "." * self._loading_phase if self._loading_phase else ""
        self.loading_text_label.setText(f"{self._loading_base_text()}{dots}")
        if self._loading_mode == "stopping":
            self.loading_icon.set_loading_icon(stop_circle_svg_path())
        else:
            self.loading_icon.set_loading_icon(
                robot_svg_path(),
                rotation_degrees=self._loading_rotation_degrees,
            )

    def _update_loading_animation(self) -> None:
        self._loading_phase = (self._loading_phase % 3) + 1
        self._apply_loading_display()
        if self._loading_mode == "typing":
            self._loading_rotation_degrees = (
                self._loading_rotation_degrees + 90
            ) % 360


_chat_window: ChatWindow | None = None


def refresh_chat_language() -> None:
    if _chat_window is not None:
        _chat_window.apply_language()


def refresh_chat_from_settings() -> None:
    if _chat_window is not None:
        _chat_window.apply_settings_refresh()


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


def import_selected_browser_notes(browser) -> None:
    config = load_config()
    note_ids: list[int] = []
    try:
        if hasattr(browser, "selected_notes"):
            note_ids = [int(nid) for nid in browser.selected_notes()]
        else:
            note_ids = [int(nid) for nid in browser.selectedNotes()]
    except Exception:
        note_ids = []
    if not note_ids:
        showWarning(tr("chat.import_notes.none_selected", config=config), parent=browser)
        return
    window = get_chat_window()
    window.show()
    window.raise_()
    window.activateWindow()
    window.import_notes_by_ids(note_ids)


def close_chat_window(*, force: bool = False) -> None:
    global _chat_window
    if _chat_window is None:
        return
    if force:
        _chat_window.prepare_shutdown()
    _chat_window.close()
    _chat_window = None
