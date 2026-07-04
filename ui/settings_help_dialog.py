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
from ..i18n import tr
from .theme import info_button_stylesheet, muted_hint_html


def _make_info_button(parent: QWidget, config: dict[str, Any]) -> QPushButton:
    button = QPushButton("i", parent)
    button.setToolTip(tr("settings.help.info_tooltip", config=config))
    button.setStyleSheet(info_button_stylesheet())
    return button


class SettingsHelpDialog(QDialog):
    def __init__(self, parent, config: dict[str, Any]):
        super().__init__(parent)
        self.config = config
        self._info_buttons: list[QPushButton] = []
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
        btn_close = QPushButton(tr("settings.help.close", config=config), self)
        btn_close.clicked.connect(self.accept)
        close_row.addWidget(btn_close)
        root.addLayout(close_row)

    def _build_list_page(self) -> QWidget:
        page = QWidget(self)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        self.intro_label = QLabel(muted_hint_html(tr("settings.help.intro", config=self.config)))
        outer.addWidget(self.intro_label)

        btn_overview = QPushButton(tr("settings.help.prompts_overview.link", config=self.config), page)
        btn_overview.clicked.connect(self._show_prompts_overview)
        outer.addWidget(btn_overview)

        outer.addWidget(QLabel("<br>"))

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        host = QWidget(scroll)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)

        for key in RESTORABLE_SETTING_KEYS:
            label_key = RESTORABLE_SETTING_LABELS.get(key, key)
            row = QHBoxLayout()
            label = QLabel(tr(label_key, config=self.config), host)
            label.setWordWrap(True)
            row.addWidget(label, stretch=1)

            btn_info = _make_info_button(host, self.config)
            btn_info.clicked.connect(lambda _checked=False, setting_key=key: self._show_detail(setting_key))
            self._info_buttons.append(btn_info)
            row.addWidget(btn_info)
            layout.addLayout(row)

        layout.addStretch(1)
        scroll.setWidget(host)
        outer.addWidget(scroll, 1)
        return page

    def _build_detail_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        self.detail_title = QLabel(page)
        self.detail_title.setWordWrap(True)
        layout.addWidget(self.detail_title)

        self.detail_body = QTextBrowser(page)
        self.detail_body.setOpenExternalLinks(True)
        self.detail_body.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self.detail_body, 1)

        btn_back = QPushButton(tr("settings.help.back", config=self.config), page)
        btn_back.clicked.connect(self._show_list)
        layout.addWidget(btn_back)
        return page

    def _show_list(self) -> None:
        self.stack.setCurrentIndex(0)

    def _show_prompts_overview(self) -> None:
        self.detail_title.setText(
            f"<b>{tr('settings.help.prompts_overview.title', config=self.config)}</b>"
        )
        self.detail_body.setHtml(tr("settings.help.prompts_overview", config=self.config))
        self.stack.setCurrentIndex(1)

    def _show_detail(self, setting_key: str) -> None:
        label_key = RESTORABLE_SETTING_LABELS.get(setting_key, setting_key)
        help_key = SETTING_HELP_KEYS.get(setting_key, setting_key)
        self.detail_title.setText(f"<b>{tr(label_key, config=self.config)}</b>")
        self.detail_body.setHtml(tr(help_key, config=self.config))
        self.stack.setCurrentIndex(1)

    def apply_theme(self) -> None:
        self.intro_label.setText(muted_hint_html(tr("settings.help.intro", config=self.config)))
        for button in self._info_buttons:
            button.setStyleSheet(info_button_stylesheet())


def open_settings_help_dialog(parent, config: dict[str, Any]) -> SettingsHelpDialog:
    dialog = SettingsHelpDialog(parent, config)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog
