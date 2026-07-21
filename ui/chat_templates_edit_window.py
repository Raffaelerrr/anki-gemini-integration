from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aqt.qt import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    Qt,
)

from ..config import load_config
from ..i18n import tr
from .card_templates import CardTemplateData
from .templates_edit_panel import TemplatesEditPanel
from .themed_windows import configure_snappable_window

_OnSave = Callable[[list[CardTemplateData], str, int | None], bool]


class ChatTemplatesEditWindow(QWidget):
    """Card templates and note-type CSS editor in a separate window."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        on_save: _OnSave,
    ) -> None:
        super().__init__(None)
        configure_snappable_window(self)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self._on_save = on_save
        self._notetype_id: int | None = None
        self._notetype_name: str | None = None
        self.resize(640, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

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
        *,
        notetype_id: int | None = None,
        notetype_name: str | None = None,
    ) -> None:
        self._notetype_id = notetype_id
        self._notetype_name = (notetype_name or "").strip() or None
        has_templates = bool(templates)
        has_css = bool(styling.strip())

        if has_templates:
            self._panel.set_templates(
                templates,
                styling=styling,
                include_styling=has_css,
                notetype_name=self._notetype_name,
            )
        elif has_css:
            self._panel.set_styling_only(
                styling,
                notetype_name=self._notetype_name,
            )
        else:
            self._panel.clear()
            self._panel.setVisible(True)

    def commit(self) -> bool:
        if not self._panel.has_editable_sections():
            return True
        return bool(
            self._on_save(
                self._panel.get_templates(),
                self._panel.get_styling(),
                self._notetype_id,
            )
        )

    def apply_language(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        if self._notetype_name:
            self.setWindowTitle(
                tr(
                    "chat.edit_templates.window_title_named",
                    config=config,
                    name=self._notetype_name,
                )
            )
        else:
            self.setWindowTitle(tr("chat.edit_templates", config=config))
        self._cancel_btn.setText(tr("settings.cancel", config=config))
        self._save_btn.setText(tr("settings.save", config=config))
        self._panel.apply_language(config)

    def apply_theme(self) -> None:
        self._panel.apply_theme()

    def _save_and_close(self) -> None:
        if self.commit():
            self.close()

