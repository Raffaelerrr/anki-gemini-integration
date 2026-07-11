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
from .settings_compact_controls import (
    configure_addon_text_edit,
    create_prompt_scroll_page,
    create_ui_text_edit,
    refresh_settings_text_edit_layouts,
)
from .theme import (
    apply_native_page_scroll_theme,
    muted_hint_html,
    refresh_native_text_edits_in,
    strong_label_html,
)
from .themed_windows import register_themed_window


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
        self._last_inspection: PromptInspection | None = None
        self._last_config: dict | None = None
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

        self._scroll, scroll_layout, scroll_host = create_prompt_scroll_page(self)
        apply_native_page_scroll_theme(self._scroll, allow_horizontal_scroll=False)
        root.addWidget(self._scroll, 1)

        self._body = create_ui_text_edit(
            scroll_host,
            scroll_free=True,
            auto_height=True,
            minimum=44,
        )[1]
        self._body.setReadOnly(True)
        self._body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        scroll_layout.addWidget(self._body)

        self.apply_language()

        register_themed_window(self)

    def apply_theme(self) -> None:
        apply_native_page_scroll_theme(self._scroll, allow_horizontal_scroll=False)
        config = self._last_config or load_config()
        self.apply_language(config)
        if self._last_inspection is not None:
            self.set_inspection(self._last_inspection, config)
        refresh_native_text_edits_in(self)

    def apply_language(self, config: dict | None = None) -> None:
        config = config or load_config()
        self._refresh_btn.setText(tr("prompt.inspect.refresh", config=config))

    def set_inspection(self, inspection: PromptInspection, config: dict | None = None) -> None:
        config = config or load_config()
        self._last_inspection = inspection
        self._last_config = config
        self._formula_label.setText(
            strong_label_html(
                tr(
                    "prompt.inspect.formula",
                    config=config,
                    formula=inspection.formula_text(config),
                )
            )
        )
        self._formula_label.setTextFormat(Qt.TextFormat.RichText)
        self._meta_label.setText(muted_hint_html(inspection.metadata_text(config)))
        self._meta_label.setTextFormat(Qt.TextFormat.RichText)
        self._body.setPlainText(inspection.plain_full_text(config))
        self._schedule_body_layout_refresh()

    def refresh(self) -> None:
        if self._refresh_callback is None:
            return
        config = load_config()
        self.set_inspection(self._refresh_callback(), config)

    def show_inspection(self, inspection: PromptInspection, config: dict | None = None) -> None:
        config = config or load_config()
        show_newlines = bool(config.get("settings_show_text_newlines", False))
        configure_addon_text_edit(self._body, show_newlines=show_newlines, scroll_free=True)
        self.apply_language(config)
        self.set_inspection(inspection, config)
        self.show()
        self.raise_()
        self.activateWindow()
        self._scroll.setFocus(Qt.FocusReason.OtherFocusReason)

    def _schedule_body_layout_refresh(self) -> None:
        from aqt.qt import QTimer

        QTimer.singleShot(0, lambda: refresh_settings_text_edit_layouts(self))
