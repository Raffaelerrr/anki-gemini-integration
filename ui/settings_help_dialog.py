from __future__ import annotations

from typing import Any

from aqt.qt import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextBrowser,
    Qt,
    QVBoxLayout,
    QWidget,
)

from ..config import RESTORABLE_SETTING_KEYS, RESTORABLE_SETTING_LABELS, SETTING_HELP_KEYS
from ..constants import (
    GEMINI_AI_STUDIO_BILLING_URL,
    GEMINI_AI_STUDIO_USAGE_URL,
    GEMINI_API_BILLING_DOCS_URL,
)
from ..i18n import tr
from .help_icons import expand_help_icons, instruction_html
from .settings_compact_controls import (
    apply_settings_icon_row_height,
    create_settings_help_list_label,
)
from .theme import (
    apply_native_page_scroll_theme,
    configure_circular_icon_button,
    info_button_stylesheet,
    muted_hint_html,
)


def _make_info_button(parent: QWidget, config: dict[str, Any]) -> QPushButton:
    button = QPushButton(parent)
    configure_circular_icon_button(button, text="i")
    button.setToolTip(tr("settings.help.info_tooltip", config=config))
    button.setAutoDefault(False)
    button.setDefault(False)
    return button


def _set_dialog_default_button(button: QPushButton) -> None:
    button.setAutoDefault(True)
    button.setDefault(True)


class SettingsHelpDialog(QDialog):
    def __init__(self, parent, config: dict[str, Any]):
        super().__init__(parent)
        self.config = config
        self._info_buttons: list[QPushButton] = []
        self.silentlyClose = True
        self.setWindowTitle(tr("settings.help.title", config=config))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(460, 420)
        self.resize(560, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        self.stack = QStackedWidget(self)
        self.stack.addWidget(self._build_list_page())
        self.stack.addWidget(self._build_detail_page())
        root.addWidget(self.stack, 1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        self.btn_close = QPushButton(tr("settings.help.close", config=config), self)
        self.btn_close.clicked.connect(self.accept)
        close_row.addWidget(self.btn_close)
        root.addLayout(close_row)

        self._default_buttons = (
            self.btn_overview,
            self.btn_chat_live,
            self.btn_chat_toolbar,
            self.btn_track_costs,
            self.btn_addon_sizes,
            self.btn_back,
            self.btn_close,
        )
        self._set_help_page("list")

    def _build_list_page(self) -> QWidget:
        page = QWidget(self)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        self.intro_label = QLabel(muted_hint_html(tr("settings.help.intro", config=self.config)))
        outer.addWidget(self.intro_label)

        self.btn_overview = QPushButton(tr("settings.help.prompts_overview.link", config=self.config), page)
        self.btn_overview.setAutoDefault(False)
        self.btn_overview.setDefault(False)
        self.btn_overview.clicked.connect(self._show_prompts_overview)
        outer.addWidget(self.btn_overview)

        self.btn_chat_live = QPushButton(tr("settings.help.chat_live_settings.link", config=self.config), page)
        self.btn_chat_live.setAutoDefault(False)
        self.btn_chat_live.setDefault(False)
        self.btn_chat_live.clicked.connect(self._show_chat_live_settings)
        outer.addWidget(self.btn_chat_live)

        self.btn_chat_toolbar = QPushButton(tr("settings.help.chat_toolbar_icons.link", config=self.config), page)
        self.btn_chat_toolbar.setAutoDefault(False)
        self.btn_chat_toolbar.setDefault(False)
        self.btn_chat_toolbar.clicked.connect(self._show_chat_toolbar_icons)
        outer.addWidget(self.btn_chat_toolbar)

        self.btn_track_costs = QPushButton(tr("settings.help.track_api_costs.link", config=self.config), page)
        self.btn_track_costs.setAutoDefault(False)
        self.btn_track_costs.setDefault(False)
        self.btn_track_costs.clicked.connect(self._show_track_api_costs)
        outer.addWidget(self.btn_track_costs)

        self.btn_addon_sizes = QPushButton(tr("settings.help.addon_payload_sizes.link", config=self.config), page)
        self.btn_addon_sizes.setAutoDefault(False)
        self.btn_addon_sizes.setDefault(False)
        self.btn_addon_sizes.clicked.connect(self._show_addon_payload_sizes)
        outer.addWidget(self.btn_addon_sizes)

        outer.addWidget(QLabel("<br>"))

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        apply_native_page_scroll_theme(scroll)

        host = QWidget(scroll)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        for key in RESTORABLE_SETTING_KEYS:
            label_key = RESTORABLE_SETTING_LABELS.get(key, key)
            row_widget = QWidget(host)
            apply_settings_icon_row_height(row_widget, allow_multiline=True)
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 2, 0, 4)
            row.setSpacing(6)
            row.setAlignment(Qt.AlignmentFlag.AlignTop)
            label = create_settings_help_list_label(
                row_widget,
                instruction_html(tr(label_key, config=self.config)),
            )
            row.addWidget(label, stretch=1)

            btn_info = _make_info_button(row_widget, self.config)
            btn_info.clicked.connect(lambda _checked=False, setting_key=key: self._show_detail(setting_key))
            self._info_buttons.append(btn_info)
            row.addWidget(btn_info, 0, Qt.AlignmentFlag.AlignTop)
            layout.addWidget(row_widget)

        scroll.setWidget(host)
        outer.addWidget(scroll, 1)
        return page

    def _build_detail_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self.detail_title = QLabel(page)
        self.detail_title.setTextFormat(Qt.TextFormat.RichText)
        self.detail_title.setWordWrap(True)
        layout.addWidget(self.detail_title)

        self.detail_body = QTextBrowser(page)
        self.detail_body.setOpenExternalLinks(True)
        self.detail_body.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self.detail_body, 1)

        self.btn_back = QPushButton(tr("settings.help.back", config=self.config), page)
        self.btn_back.setAutoDefault(False)
        self.btn_back.setDefault(False)
        self.btn_back.clicked.connect(self._show_list)
        layout.addWidget(self.btn_back)
        return page

    def _clear_default_buttons(self) -> None:
        for button in self._default_buttons:
            button.setAutoDefault(False)
            button.setDefault(False)

    def _set_help_page(self, page: str) -> None:
        self._clear_default_buttons()
        if page == "list":
            _set_dialog_default_button(self.btn_close)
        else:
            _set_dialog_default_button(self.btn_back)

    def _show_list(self) -> None:
        self.stack.setCurrentIndex(0)
        self._set_help_page("list")

    def _set_detail_html(self, html: str) -> None:
        self.detail_body.setHtml(expand_help_icons(html))

    def _show_prompts_overview(self) -> None:
        self.detail_title.setText(
            f"<b>{tr('settings.help.prompts_overview.title', config=self.config)}</b>"
        )
        self._set_detail_html(tr("settings.help.prompts_overview", config=self.config))
        self.stack.setCurrentIndex(1)
        self._set_help_page("detail")

    def _show_chat_live_settings(self) -> None:
        self.detail_title.setText(
            f"<b>{tr('settings.help.chat_live_settings.title', config=self.config)}</b>"
        )
        self._set_detail_html(tr("settings.help.chat_live_settings", config=self.config))
        self.stack.setCurrentIndex(1)
        self._set_help_page("detail")

    def _show_chat_toolbar_icons(self) -> None:
        self.detail_title.setText(
            f"<b>{tr('settings.help.chat_toolbar_icons.title', config=self.config)}</b>"
        )
        self._set_detail_html(tr("settings.help.chat_toolbar_icons", config=self.config))
        self.stack.setCurrentIndex(1)
        self._set_help_page("detail")

    def _show_track_api_costs(self) -> None:
        self.detail_title.setText(
            f"<b>{tr('settings.help.track_api_costs.title', config=self.config)}</b>"
        )
        self._set_detail_html(
            tr(
                "settings.help.track_api_costs",
                config=self.config,
                billing_url=GEMINI_AI_STUDIO_BILLING_URL,
                usage_url=GEMINI_AI_STUDIO_USAGE_URL,
                docs_url=GEMINI_API_BILLING_DOCS_URL,
            )
        )
        self.stack.setCurrentIndex(1)
        self._set_help_page("detail")

    def _show_addon_payload_sizes(self) -> None:
        self.detail_title.setText(
            f"<b>{tr('settings.help.addon_payload_sizes.title', config=self.config)}</b>"
        )
        self._set_detail_html(
            tr(
                "settings.help.addon_payload_sizes",
                config=self.config,
                billing_url=GEMINI_AI_STUDIO_BILLING_URL,
            )
        )
        self.stack.setCurrentIndex(1)
        self._set_help_page("detail")

    def _show_detail(self, setting_key: str) -> None:
        label_key = RESTORABLE_SETTING_LABELS.get(setting_key, setting_key)
        help_key = SETTING_HELP_KEYS.get(setting_key, setting_key)
        self.detail_title.setText(
            instruction_html(f"<b>{tr(label_key, config=self.config)}</b>")
        )
        self._set_detail_html(tr(help_key, config=self.config))
        self.stack.setCurrentIndex(1)
        self._set_help_page("detail")

    def show_detail(self, setting_key: str) -> None:
        self._show_detail(setting_key)

    def apply_theme(self) -> None:
        self.intro_label.setText(muted_hint_html(tr("settings.help.intro", config=self.config)))
        for button in self._info_buttons:
            button.setStyleSheet(info_button_stylesheet())


def open_settings_help_dialog(
    parent,
    config: dict[str, Any],
    *,
    detail_key: str | None = None,
) -> SettingsHelpDialog:
    dialog = SettingsHelpDialog(parent, config)
    if detail_key:
        dialog.show_detail(detail_key)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog
