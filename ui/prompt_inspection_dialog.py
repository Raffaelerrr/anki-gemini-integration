from __future__ import annotations

from collections.abc import Callable

from aqt.qt import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    Qt,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import load_config
from ..i18n import tr
from ..prompt_inspection import PromptInspection
from .settings_compact_controls import create_ui_text_edit
from .theme import apply_native_text_edit_surface_theme, muted_hint_html, strong_label_html


class PromptInspectionWindow(QWidget):
    """Read-only prompt inspector with optional live refresh."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        refresh_callback: Callable[[], PromptInspection] | None = None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self._refresh_callback = refresh_callback
        self.resize(640, 520)
        self.setWindowTitle(title)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        self._refresh_btn = QPushButton(self)
        self._refresh_btn.clicked.connect(self.refresh)
        self._refresh_btn.setVisible(refresh_callback is not None)
        toolbar.addWidget(self._refresh_btn)
        root.addLayout(toolbar)

        self._formula_label = QLabel(self)
        self._formula_label.setWordWrap(True)
        self._formula_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self._formula_label)

        self._meta_label = QLabel(self)
        self._meta_label.setWordWrap(True)
        self._meta_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self._meta_label)

        body_shell, self._body = create_ui_text_edit(self)
        self._body.setReadOnly(True)
        apply_native_text_edit_surface_theme(self._body)
        self._body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root.addWidget(body_shell, 1)

        self.apply_language()

    def apply_language(self, config: dict | None = None) -> None:
        config = config or load_config()
        self._refresh_btn.setText(tr("prompt.inspect.refresh", config=config))

    def set_inspection(self, inspection: PromptInspection, config: dict | None = None) -> None:
        config = config or load_config()
        self._formula_label.setText(
            strong_label_html(
                tr(
                    "prompt.inspect.formula",
                    config=config,
                    formula=inspection.formula_text(config),
                )
            )
        )
        self._meta_label.setText(muted_hint_html(inspection.metadata_text(config)))
        self._body.setPlainText(inspection.full_text(config))

    def refresh(self) -> None:
        if self._refresh_callback is None:
            return
        config = load_config()
        self.set_inspection(self._refresh_callback(), config)

    def show_inspection(self, inspection: PromptInspection, config: dict | None = None) -> None:
        config = config or load_config()
        self.apply_language(config)
        self.set_inspection(inspection, config)
        self.show()
        self.raise_()
        self.activateWindow()
