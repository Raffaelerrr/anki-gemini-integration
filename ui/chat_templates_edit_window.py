from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aqt.qt import (
    QCheckBox,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    Qt,
)

from ..config import load_config, save_config
from ..i18n import tr
from .card_templates import CardTemplateData
from .templates_edit_panel import TemplatesEditPanel
from .themed_windows import configure_snappable_window

_OnSave = Callable[[list[CardTemplateData], str], None]


class ChatTemplatesEditWindow(QWidget):
    """Card templates and note-type CSS editor in a separate window."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        on_save: _OnSave,
        on_include_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(None)
        configure_snappable_window(self)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self._on_save = on_save
        self._on_include_changed = on_include_changed
        self.resize(640, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        include_row = QHBoxLayout()
        self._include_templates_checkbox = QCheckBox(self)
        self._include_templates_checkbox.toggled.connect(self._on_include_toggled)
        include_row.addWidget(self._include_templates_checkbox)
        self._include_css_checkbox = QCheckBox(self)
        self._include_css_checkbox.toggled.connect(self._on_include_toggled)
        include_row.addWidget(self._include_css_checkbox)
        include_row.addStretch(1)
        root.addLayout(include_row)

        self._panel = TemplatesEditPanel(self)
        self._panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._panel.setVisible(True)
        root.addWidget(self._panel, 1)

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

    def load(
        self,
        templates: list[CardTemplateData],
        styling: str,
    ) -> None:
        config = load_config()
        has_templates = bool(templates)
        has_css = bool(styling.strip())
        self._include_templates_checkbox.setEnabled(has_templates)
        self._include_css_checkbox.setEnabled(has_css)
        self._include_templates_checkbox.blockSignals(True)
        self._include_css_checkbox.blockSignals(True)
        self._include_templates_checkbox.setChecked(
            bool(config.get("brain_import_templates", False)) if has_templates else False
        )
        self._include_css_checkbox.setChecked(
            bool(config.get("brain_import_css", False)) if has_css else False
        )
        self._include_templates_checkbox.blockSignals(False)
        self._include_css_checkbox.blockSignals(False)

        if has_templates:
            self._panel.set_templates(
                templates,
                styling=styling,
                include_styling=has_css,
            )
        elif has_css:
            self._panel.set_styling_only(styling)
        else:
            self._panel.clear()
            self._panel.setVisible(True)

    def commit(self) -> None:
        if not self._panel.has_editable_sections():
            return
        self._on_save(self._panel.get_templates(), self._panel.get_styling())

    def apply_language(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        self.setWindowTitle(tr("chat.edit_templates", config=config))
        self._include_templates_checkbox.setText(
            tr("chat.edit_templates.include_templates", config=config)
        )
        self._include_css_checkbox.setText(tr("chat.edit_templates.include_css", config=config))
        self._cancel_btn.setText(tr("settings.cancel", config=config))
        self._save_btn.setText(tr("settings.save", config=config))
        self._panel.apply_language(config)

    def apply_theme(self) -> None:
        self._panel.apply_theme()

    def _persist_include_flags(self) -> None:
        config = load_config()
        config["brain_import_templates"] = self._include_templates_checkbox.isChecked()
        config["brain_import_css"] = self._include_css_checkbox.isChecked()
        save_config(config)
        if self._on_include_changed is not None:
            self._on_include_changed()

    def _on_include_toggled(self, _checked: bool) -> None:
        self._persist_include_flags()

    def _save_and_close(self) -> None:
        self._persist_include_flags()
        self.commit()
        self.close()
