from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aqt.qt import (
    QCheckBox,
    QCloseEvent,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    Qt,
    QFileDialog,
)
from aqt.utils import showInfo, showWarning

from ..config import load_config, save_config
from ..i18n import tr
from ..prompt_cache import (
    PROMPT_CACHE_USER_SEGMENT_ORDER,
    clear_prompt_cache,
    extend_prompt_cache_ttl,
    get_prompt_cache_store,
    prompt_cache_change_ttl_seconds,
    prompt_cache_status_text,
    segment_label_key,
)
from ..prompt_cache_policy import (
    CHAT_PROMPT_CACHE_RESTORABLE_KEYS,
    CHAT_PROMPT_CACHE_RESTORABLE_LABELS,
    ChatPromptCacheSettings,
    normalize_custom_text_presets,
    purposes_requiring_cache_invalidation,
)
from .prompt_cache_confirm import confirm_custom_text_load_replace
from .settings_compact_controls import (
    SETTINGS_SECTION_GAP,
    add_settings_section_break,
    add_settings_stacked_field,
    create_settings_auto_height_text_edit,
    create_settings_checkbox_info_row,
    create_settings_combo,
    create_settings_hint_label,
    create_settings_section_label,
    create_settings_spinbox,
    refresh_settings_text_edit_layouts,
)
from .help_icons import refresh_info_button_explanation, wire_info_button_explanation
from .settings_help_dialog import _make_info_button
from .theme import (
    apply_native_page_scroll_theme,
    info_button_stylesheet,
    refresh_native_text_edits_in,
)
from .themed_windows import configure_snappable_window, register_themed_window


def _set_dialog_default_button(button: QPushButton) -> None:
    button.setAutoDefault(True)
    button.setDefault(True)


class ChatPromptCacheDialog(QWidget):
    """Persistent chat prompt cache settings."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        config: dict[str, Any] | None = None,
        on_finished: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__(None)
        configure_snappable_window(self)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        register_themed_window(self)
        self._on_finished = on_finished
        self.silentlyClose = False
        merged_config = load_config()
        if config:
            merged_config.update(config)
        self._global_config = merged_config
        self._baseline_settings = ChatPromptCacheSettings.from_config(self._global_config)
        self._accepted = False
        self._manual_custom_cache_text = ""
        self._restore_checkboxes: dict[str, QCheckBox] = {}
        self._all_restore_checked = True

        self.setWindowTitle(tr("chat.prompt_cache.session.title", config=self._global_config))
        self.resize(640, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(SETTINGS_SECTION_GAP)

        self._intro_label = create_settings_hint_label(
            self,
            tr("chat.prompt_cache.session.intro", config=self._global_config),
        )
        root.addWidget(self._intro_label)

        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._build_settings_page())
        self._stack.addWidget(self._build_restore_page())
        root.addWidget(self._stack, 1)

        self._form_btn_layout = QHBoxLayout()
        self._form_btn_layout.setSpacing(SETTINGS_SECTION_GAP)
        self._restore_defaults_btn = QPushButton(
            tr("settings.restore_defaults", config=self._global_config),
            self,
        )
        self._restore_defaults_btn.clicked.connect(self._enter_restore_mode)
        self._form_btn_layout.addWidget(self._restore_defaults_btn)
        self._form_btn_layout.addStretch(1)
        self._cancel_btn = QPushButton(tr("preview.cancel", config=self._global_config), self)
        self._cancel_btn.clicked.connect(self.close)
        self._ok_btn = QPushButton(
            tr("chat.prompt_cache.session.apply", config=self._global_config),
            self,
        )
        self._ok_btn.clicked.connect(self._accept_settings)
        self._form_btn_layout.addWidget(self._cancel_btn)
        self._form_btn_layout.addWidget(self._ok_btn)
        root.addLayout(self._form_btn_layout)

        self._restore_btn_layout = QHBoxLayout()
        self._restore_btn_layout.setSpacing(SETTINGS_SECTION_GAP)
        self._toggle_all_btn = QPushButton(
            tr("settings.restore.toggle_all", config=self._global_config),
            self,
        )
        self._toggle_all_btn.clicked.connect(self._toggle_all_restore_checks)
        self._apply_restore_btn = QPushButton(
            tr("settings.restore.apply", config=self._global_config),
            self,
        )
        self._apply_restore_btn.clicked.connect(self._apply_selected_defaults)
        self._restore_back_btn = QPushButton(
            tr("chat.prompt_cache.session.restore.back", config=self._global_config),
            self,
        )
        self._restore_back_btn.clicked.connect(self._leave_restore_mode)
        self._restore_btn_layout.addWidget(self._toggle_all_btn)
        self._restore_btn_layout.addStretch(1)
        self._restore_btn_layout.addWidget(self._apply_restore_btn)
        self._restore_btn_layout.addWidget(self._restore_back_btn)
        root.addLayout(self._restore_btn_layout)

        self._default_buttons = (self._ok_btn, self._apply_restore_btn)
        self._set_subpage_mode(None)
        self._load_settings(self._baseline_settings)
        self.apply_theme()

    def _build_settings_page(self) -> QWidget:
        page = QWidget(self)
        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        apply_native_page_scroll_theme(scroll, allow_horizontal_scroll=False)
        host = QWidget(scroll)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SETTINGS_SECTION_GAP)

        layout.addWidget(
            create_settings_section_label(
                host,
                tr("chat.prompt_cache.session.section", config=self._global_config),
            )
        )
        layout.addWidget(
            create_settings_hint_label(
                host,
                tr("settings.prompt_cache.hint", config=self._global_config),
            )
        )

        self._enabled_checkbox = QCheckBox(
            tr("settings.prompt_cache_enabled_chat", config=self._global_config),
            host,
        )
        layout.addWidget(self._enabled_checkbox)

        ttl_row = QHBoxLayout()
        ttl_row.addWidget(
            QLabel(tr("settings.prompt_cache_ttl", config=self._global_config), host)
        )
        ttl_shell, self._ttl_input = create_settings_spinbox(host)
        self._ttl_input.setRange(60, 7 * 24 * 3600)
        self._ttl_input.setSingleStep(300)
        ttl_row.addWidget(ttl_shell)
        ttl_row.addStretch(1)
        layout.addLayout(ttl_row)

        min_row = QHBoxLayout()
        min_row.addWidget(
            QLabel(tr("settings.prompt_cache_min_chars", config=self._global_config), host)
        )
        min_chars_shell, self._min_chars_input = create_settings_spinbox(host)
        self._min_chars_input.setRange(256, 1_000_000)
        min_row.addWidget(min_chars_shell)
        min_row.addStretch(1)
        layout.addLayout(min_row)

        self._status_label = QLabel(host)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        change_ttl_row = QHBoxLayout()
        change_ttl_row.addWidget(
            QLabel(tr("settings.prompt_cache.change_ttl_seconds", config=self._global_config), host)
        )
        change_ttl_shell, self._change_ttl_input = create_settings_spinbox(host)
        self._change_ttl_input.setRange(60, 7 * 24 * 3600)
        self._change_ttl_input.setSingleStep(300)
        self._change_ttl_input.setValue(prompt_cache_change_ttl_seconds(self._global_config))
        change_ttl_row.addWidget(change_ttl_shell)
        change_ttl_row.addStretch(1)
        layout.addLayout(change_ttl_row)

        cache_btn_row = QHBoxLayout()
        cache_btn_row.setSpacing(SETTINGS_SECTION_GAP)
        self._change_ttl_btn = QPushButton(
            tr("settings.prompt_cache.change_ttl", config=self._global_config),
            host,
        )
        self._change_ttl_btn.clicked.connect(self._change_chat_cache_ttl)
        self._clear_cache_btn = QPushButton(
            tr("chat.prompt_cache.session.clear_cache", config=self._global_config),
            host,
        )
        self._clear_cache_btn.clicked.connect(self._clear_chat_cache)
        cache_btn_row.addWidget(self._change_ttl_btn)
        cache_btn_row.addWidget(self._clear_cache_btn)
        cache_btn_row.addStretch(1)
        layout.addLayout(cache_btn_row)

        add_settings_section_break(layout)
        layout.addWidget(
            create_settings_section_label(
                host,
                tr("settings.prompt_cache_segments", config=self._global_config),
            )
        )
        layout.addWidget(
            create_settings_hint_label(
                host,
                tr("settings.prompt_cache_segments.hint", config=self._global_config),
            )
        )
        self._segment_checkboxes: dict[str, QCheckBox] = {}
        for segment_id in PROMPT_CACHE_USER_SEGMENT_ORDER:
            label = tr(segment_label_key(segment_id), config=self._global_config)
            checkbox = QCheckBox(label, host)
            if segment_id == "system_instruction":
                info_btn = _make_info_button(host, self._global_config)
                wire_info_button_explanation(
                    info_btn,
                    config=self._global_config,
                    message_key="settings.prompt_cache.system_instruction_cache_info",
                )
                layout.addWidget(create_settings_checkbox_info_row(host, checkbox, info_btn))
                self._system_instruction_info_btn = info_btn
            else:
                layout.addWidget(checkbox)
            self._segment_checkboxes[segment_id] = checkbox

        add_settings_section_break(layout)
        layout.addWidget(
            create_settings_section_label(
                host,
                tr("settings.prompt_cache_custom_text", config=self._global_config),
            )
        )
        layout.addWidget(
            create_settings_hint_label(
                host,
                tr("settings.prompt_cache_custom_text.hint", config=self._global_config),
            )
        )

        preset_shell, self._preset_combo = create_settings_combo(host)
        self._preset_combo.addItem(
            tr("settings.prompt_cache_presets.manual", config=self._global_config),
            "",
        )
        for preset in normalize_custom_text_presets(
            self._global_config.get("prompt_cache_custom_text_presets")
        ):
            if preset.get("chat"):
                self._preset_combo.addItem(str(preset.get("name") or ""), str(preset.get("id") or ""))
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        add_settings_stacked_field(
            layout,
            host,
            tr("settings.prompt_cache_presets.active", config=self._global_config),
            preset_shell,
        )

        custom_shell, self._custom_text_input = create_settings_auto_height_text_edit(
            host,
            show_newlines=bool(self._global_config.get("settings_show_text_newlines", False)),
        )
        layout.addWidget(custom_shell)

        custom_cache_btn_row = QHBoxLayout()
        self._custom_text_load_btn = QPushButton(
            tr("settings.prompt_cache_custom_text.load_file", config=self._global_config),
            host,
        )
        self._custom_text_load_btn.clicked.connect(self._load_custom_text_from_file)
        custom_cache_btn_row.addWidget(self._custom_text_load_btn)
        custom_cache_btn_row.addStretch(1)
        layout.addLayout(custom_cache_btn_row)

        scroll.setWidget(host)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        return page

    def _build_restore_page(self) -> QWidget:
        config = self._global_config
        page = QWidget(self)
        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        apply_native_page_scroll_theme(scroll, allow_horizontal_scroll=False)

        host = QWidget(scroll)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SETTINGS_SECTION_GAP)

        layout.addWidget(
            create_settings_section_label(
                host,
                tr("chat.prompt_cache.session.restore.title", config=config),
            )
        )
        layout.addWidget(
            create_settings_hint_label(
                host,
                tr("chat.prompt_cache.session.restore.hint", config=config),
            )
        )

        self._restore_checkboxes.clear()
        restore_list_host = QWidget(host)
        restore_list_layout = QVBoxLayout(restore_list_host)
        restore_list_layout.setContentsMargins(0, 0, 0, 0)
        restore_list_layout.setSpacing(4)
        for key in CHAT_PROMPT_CACHE_RESTORABLE_KEYS:
            label_key = CHAT_PROMPT_CACHE_RESTORABLE_LABELS.get(key, key)
            checkbox = QCheckBox(tr(label_key, config=config), restore_list_host)
            checkbox.setChecked(True)
            restore_list_layout.addWidget(checkbox)
            self._restore_checkboxes[key] = checkbox
        layout.addWidget(restore_list_host)
        layout.addStretch(1)

        scroll.setWidget(host)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        return page

    @property
    def accepted(self) -> bool:
        return self._accepted

    def closeEvent(self, event: QCloseEvent) -> None:
        callback = self._on_finished
        accepted = self._accepted
        self._on_finished = None
        event.accept()
        super().closeEvent(event)
        if callback is not None:
            callback(accepted)

    def _set_subpage_mode(self, mode: str | None) -> None:
        on_form = mode is None
        on_restore = mode == "restore"

        self._intro_label.setVisible(on_form)
        self._restore_defaults_btn.setVisible(on_form)
        self._cancel_btn.setVisible(on_form)
        self._ok_btn.setVisible(on_form)

        self._toggle_all_btn.setVisible(on_restore)
        self._apply_restore_btn.setVisible(on_restore)
        self._restore_back_btn.setVisible(on_restore)

        for button in self._default_buttons:
            button.setAutoDefault(False)
            button.setDefault(False)

        if on_form:
            _set_dialog_default_button(self._ok_btn)
        elif on_restore:
            _set_dialog_default_button(self._apply_restore_btn)

    def _enter_restore_mode(self) -> None:
        self._all_restore_checked = True
        for checkbox in self._restore_checkboxes.values():
            checkbox.setChecked(True)
        self._stack.setCurrentIndex(1)
        self._set_subpage_mode("restore")

    def _leave_restore_mode(self) -> None:
        self._stack.setCurrentIndex(0)
        self._set_subpage_mode(None)

    def _toggle_all_restore_checks(self) -> None:
        self._all_restore_checked = not self._all_restore_checked
        for checkbox in self._restore_checkboxes.values():
            checkbox.setChecked(self._all_restore_checked)

    def _selected_restore_keys(self) -> list[str]:
        return [key for key, checkbox in self._restore_checkboxes.items() if checkbox.isChecked()]

    def _apply_default_for_key(self, key: str) -> None:
        defaults = ChatPromptCacheSettings.defaults()
        if key == "enabled":
            self._enabled_checkbox.setChecked(bool(defaults.enabled))
            return
        if key == "prompt_cache_ttl_seconds":
            self._ttl_input.setValue(int(defaults.prompt_cache_ttl_seconds))
            return
        if key == "prompt_cache_min_chars":
            self._min_chars_input.setValue(int(defaults.prompt_cache_min_chars))
            return
        if key == "prompt_cache_segments":
            for segment_id, checkbox in self._segment_checkboxes.items():
                checkbox.setChecked(
                    bool(defaults.prompt_cache_segments.get(segment_id, False))
                )
            return
        if key == "prompt_cache_custom_text":
            self._manual_custom_cache_text = defaults.prompt_cache_custom_text
            if not self._selected_preset_id():
                self._custom_text_input.setPlainText(defaults.prompt_cache_custom_text)
            return
        if key == "prompt_cache_active_preset_id":
            self._preset_combo.blockSignals(True)
            self._preset_combo.setCurrentIndex(0)
            self._preset_combo.blockSignals(False)
            self._sync_custom_text_field()

    def _apply_selected_defaults(self) -> None:
        selected = self._selected_restore_keys()
        if not selected:
            showInfo(tr("settings.restore.none_selected", config=self._global_config))
            return
        for key in selected:
            self._apply_default_for_key(key)
        self._refresh_cache_status()
        self._leave_restore_mode()

    def _effective_config(self) -> dict[str, Any]:
        return self._collect_settings().apply_to_config(dict(self._global_config))

    def _chat_cache_active(self) -> bool:
        return get_prompt_cache_store("chat").active is not None

    def _refresh_cache_status(self) -> None:
        self._status_label.setText(
            prompt_cache_status_text(self._effective_config(), "chat")
        )
        has_active = self._chat_cache_active()
        self._change_ttl_btn.setEnabled(has_active)
        self._clear_cache_btn.setEnabled(has_active)

    def _change_chat_cache_ttl(self) -> None:
        config = self._global_config
        if not self._chat_cache_active():
            showWarning(tr("settings.prompt_cache.change_ttl.none", config=config))
            return
        ttl_seconds = self._change_ttl_input.value()
        if extend_prompt_cache_ttl(
            config=self._effective_config(),
            purpose="chat",
            extra_seconds=ttl_seconds,
        ):
            self._refresh_cache_status()
            return
        if get_prompt_cache_store("chat").active is not None:
            showWarning(tr("settings.prompt_cache.change_ttl.failed", config=config))
        else:
            showWarning(tr("settings.prompt_cache.change_ttl.none", config=config))

    def _clear_chat_cache(self) -> None:
        clear_prompt_cache(config=self._effective_config(), purpose="chat")
        self._refresh_cache_status()

    def _selected_preset_id(self) -> str:
        return str(self._preset_combo.currentData() or "")

    def _commit_custom_text_editor(self) -> None:
        if not self._selected_preset_id():
            self._manual_custom_cache_text = self._custom_text_input.toPlainText()

    def _sync_custom_text_field(self) -> None:
        preset_id = self._selected_preset_id()
        if preset_id:
            for preset in normalize_custom_text_presets(
                self._global_config.get("prompt_cache_custom_text_presets")
            ):
                if preset.get("id") == preset_id:
                    self._custom_text_input.setPlainText(str(preset.get("text") or ""))
                    custom_checkbox = self._segment_checkboxes.get("custom_cache_text")
                    if custom_checkbox is not None:
                        custom_checkbox.setChecked(True)
                    return
            return
        self._custom_text_input.setPlainText(self._manual_custom_cache_text)

    def _load_settings(self, settings: ChatPromptCacheSettings) -> None:
        self._enabled_checkbox.setChecked(bool(settings.enabled))
        self._ttl_input.setValue(int(settings.prompt_cache_ttl_seconds))
        self._min_chars_input.setValue(int(settings.prompt_cache_min_chars))
        for segment_id, checkbox in self._segment_checkboxes.items():
            checkbox.setChecked(bool(settings.prompt_cache_segments.get(segment_id, False)))
        self._manual_custom_cache_text = settings.prompt_cache_custom_text
        preset_index = self._preset_combo.findData(settings.prompt_cache_active_preset_id)
        self._preset_combo.blockSignals(True)
        self._preset_combo.setCurrentIndex(preset_index if preset_index >= 0 else 0)
        self._preset_combo.blockSignals(False)
        self._sync_custom_text_field()
        self._refresh_cache_status()

    def _on_preset_changed(self, _index: int) -> None:
        self._commit_custom_text_editor()
        self._sync_custom_text_field()

    def _load_custom_text_from_file(self) -> None:
        config = self._global_config
        existing = self._custom_text_input.toPlainText().strip()
        if existing and not confirm_custom_text_load_replace(self, config=config):
            return

        path = QFileDialog.getOpenFileName(
            self,
            tr("settings.prompt_cache_custom_text.load_file.title", config=config),
            "",
            tr("settings.prompt_cache_custom_text.load_file.filter", config=config),
        )[0]
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

        self._custom_text_input.setPlainText(text)
        if not self._selected_preset_id():
            self._manual_custom_cache_text = text
        custom_checkbox = self._segment_checkboxes.get("custom_cache_text")
        if custom_checkbox is not None:
            custom_checkbox.setChecked(True)

    def _collect_settings(self) -> ChatPromptCacheSettings:
        self._commit_custom_text_editor()
        segments = {
            segment_id: checkbox.isChecked()
            for segment_id, checkbox in self._segment_checkboxes.items()
        }
        return ChatPromptCacheSettings(
            enabled=self._enabled_checkbox.isChecked(),
            prompt_cache_ttl_seconds=self._ttl_input.value(),
            prompt_cache_min_chars=self._min_chars_input.value(),
            prompt_cache_segments=segments,
            prompt_cache_custom_text=self._manual_custom_cache_text.strip(),
            prompt_cache_active_preset_id=self._selected_preset_id(),
        )

    def _accept_settings(self) -> None:
        pending = self._collect_settings()
        merged = pending.apply_to_config(dict(self._global_config))
        affected = purposes_requiring_cache_invalidation(self._global_config, merged)
        if "chat" in affected and get_prompt_cache_store("chat").active is not None:
            clear_prompt_cache(config=self._global_config, purpose="chat")
        save_config(merged)
        self._global_config = merged
        self._baseline_settings = ChatPromptCacheSettings.from_config(merged)
        self._accepted = True
        self.close()

    def apply_theme(self) -> None:
        config = self._global_config
        self.setWindowTitle(tr("chat.prompt_cache.session.title", config=config))
        self._intro_label.setText(tr("chat.prompt_cache.session.intro", config=config))
        self._enabled_checkbox.setText(tr("settings.prompt_cache_enabled_chat", config=config))
        self._change_ttl_btn.setText(tr("settings.prompt_cache.change_ttl", config=config))
        self._clear_cache_btn.setText(tr("chat.prompt_cache.session.clear_cache", config=config))
        self._custom_text_load_btn.setText(
            tr("settings.prompt_cache_custom_text.load_file", config=config)
        )
        self._restore_defaults_btn.setText(tr("settings.restore_defaults", config=config))
        self._toggle_all_btn.setText(tr("settings.restore.toggle_all", config=config))
        self._apply_restore_btn.setText(tr("settings.restore.apply", config=config))
        self._restore_back_btn.setText(
            tr("chat.prompt_cache.session.restore.back", config=config)
        )
        self._cancel_btn.setText(tr("preview.cancel", config=config))
        self._ok_btn.setText(tr("chat.prompt_cache.session.apply", config=config))
        if hasattr(self, "_system_instruction_info_btn"):
            self._system_instruction_info_btn.setStyleSheet(info_button_stylesheet())
            refresh_info_button_explanation(
                self._system_instruction_info_btn,
                config=config,
                message_key="settings.prompt_cache.system_instruction_cache_info",
            )
        self._refresh_cache_status()
        refresh_native_text_edits_in(self)
        refresh_settings_text_edit_layouts(self)


def open_chat_prompt_cache_settings(
    parent: QWidget | None,
    *,
    config: dict[str, Any] | None = None,
    on_finished: Callable[[bool], None] | None = None,
) -> ChatPromptCacheDialog:
    """Open chat cache settings without blocking other Anki windows."""
    dialog = ChatPromptCacheDialog(parent, config=config, on_finished=on_finished)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog


def open_chat_prompt_cache_dialog(
    parent: QWidget | None,
    *,
    settings: ChatPromptCacheSettings | None = None,
    config: dict[str, Any] | None = None,
    on_finished: Callable[[bool], None] | None = None,
) -> ChatPromptCacheDialog:
    """Backward-compatible helper; settings arg is ignored (config is the source of truth)."""
    del settings
    return open_chat_prompt_cache_settings(
        parent,
        config=config,
        on_finished=on_finished,
    )
