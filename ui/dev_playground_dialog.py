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
from ..i18n import tr
from .chat_dialog import open_chat
from .settings_dialog import open_settings_dialog
from .theme import apply_native_text_edit_surface_theme, get_theme_colors
from .themed_windows import configure_snappable_window


class DevPlaygroundDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = load_config()
        configure_snappable_window(self)
        self.setWindowTitle(tr("dev.playground.title", config=self._config))
        self.setMinimumSize(560, 420)
        self.resize(620, 480)

        root = QVBoxLayout(self)
        self.intro = QLabel(tr("dev.playground.intro", config=self._config), self)
        self.intro.setWordWrap(True)
        root.addWidget(self.intro)

        self.mock_checkbox = QCheckBox(tr("dev.playground.enable", config=self._config), self)
        self.mock_checkbox.setChecked(is_dev_mock_enabled())
        self.mock_checkbox.toggled.connect(self._on_mock_toggled)
        root.addWidget(self.mock_checkbox)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)
        self._refresh_status()

        btn_row = QHBoxLayout()
        self.open_chat_btn = QPushButton(tr("dev.playground.open_chat", config=self._config), self)
        self.open_chat_btn.clicked.connect(lambda: open_chat())
        btn_row.addWidget(self.open_chat_btn)

        self.open_settings_btn = QPushButton(
            tr("dev.playground.open_settings", config=self._config),
            self,
        )
        self.open_settings_btn.clicked.connect(lambda: open_settings_dialog(None))
        btn_row.addWidget(self.open_settings_btn)

        self.reset_btn = QPushButton(tr("dev.playground.reset", config=self._config), self)
        self.reset_btn.clicked.connect(self._reset_mock_state)
        btn_row.addWidget(self.reset_btn)

        self.clear_log_btn = QPushButton(tr("dev.playground.clear_log", config=self._config), self)
        self.clear_log_btn.clicked.connect(self._clear_log)
        btn_row.addWidget(self.clear_log_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        self.activity_label = QLabel(
            f"<b>{tr('dev.playground.activity_log', config=self._config)}</b>",
            self,
        )
        root.addWidget(self.activity_label)
        self.log_view = QPlainTextEdit(self)
        self.log_view.setReadOnly(True)
        apply_native_text_edit_surface_theme(self.log_view)
        root.addWidget(self.log_view, stretch=1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton(tr("dev.playground.close", config=self._config), self)
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)

        set_dev_mock_log_callback(self._append_log)
        if is_dev_mock_enabled():
            dev_mock_log(tr("dev.playground.log.active", config=self._config))

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _clear_log(self) -> None:
        self.log_view.clear()

    def _refresh_status(self) -> None:
        config = load_config()
        self._config = config
        if is_dev_mock_enabled():
            colors = get_theme_colors()
            self.status_label.setText(
                tr("dev.playground.status.active", config=config, success=colors.success)
            )
        else:
            self.status_label.setText(tr("dev.playground.status.inactive", config=config))

    def _on_mock_toggled(self, checked: bool) -> None:
        config = load_config()
        config["dev_mock_mode"] = bool(checked)
        save_config(config)
        self._config = config
        if checked:
            reset_dev_mock_state()
            tooltip(tr("dev.playground.tooltip.enabled", config=config))
            dev_mock_log(tr("dev.playground.log.enabled", config=config))
        else:
            tooltip(tr("dev.playground.tooltip.disabled", config=config))
            dev_mock_log(tr("dev.playground.log.disabled", config=config))
        self._refresh_status()

    def _reset_mock_state(self) -> None:
        reset_dev_mock_state()
        tooltip(tr("dev.playground.tooltip.reset", config=load_config()))

    def apply_theme(self) -> None:
        config = load_config()
        self._config = config
        self.setWindowTitle(tr("dev.playground.title", config=config))
        self.intro.setText(tr("dev.playground.intro", config=config))
        self.mock_checkbox.setText(tr("dev.playground.enable", config=config))
        self.open_chat_btn.setText(tr("dev.playground.open_chat", config=config))
        self.open_settings_btn.setText(tr("dev.playground.open_settings", config=config))
        self.reset_btn.setText(tr("dev.playground.reset", config=config))
        self.clear_log_btn.setText(tr("dev.playground.clear_log", config=config))
        self.activity_label.setText(
            f"<b>{tr('dev.playground.activity_log', config=config)}</b>"
        )
        apply_native_text_edit_surface_theme(self.log_view)
        self._refresh_status()

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
