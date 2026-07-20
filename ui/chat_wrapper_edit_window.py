from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aqt.qt import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    Qt,
)

from ..config import load_config
from ..i18n import (
    chat_edit_wrapper_hint_text,
    chat_edit_wrapper_label_text,
    tr,
)
from .settings_compact_controls import (
    create_settings_hint_label,
    refresh_settings_text_edit_layouts,
)
from .theme import (
    apply_native_page_scroll_theme,
    muted_hint_html,
    refresh_native_text_edits_in,
    strong_label_html,
)
from .wrapper_sections_editor import WrapperSectionsEditor
from .themed_windows import configure_snappable_window

_OnSave = Callable[[list[str], dict[str, str], str], None]


class ChatWrapperEditWindow(QWidget):
    """Session-only context wrapper editor in a separate window."""

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
        self.resize(760, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self._label = create_settings_hint_label(self, "")
        self._label.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(self._label)

        self._hint = create_settings_hint_label(self, "")
        self._hint.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(self._hint)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        apply_native_page_scroll_theme(scroll, allow_horizontal_scroll=False)
        scroll_host = QWidget(scroll)
        scroll_layout = QVBoxLayout(scroll_host)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        cfg = load_config()
        self._editor = WrapperSectionsEditor(
            scroll_host,
            show_newlines=bool(cfg.get("settings_show_text_newlines", False)),
            wrap=bool(cfg.get("settings_wrap_text_editors", True)),
        )
        scroll_layout.addWidget(self._editor)
        scroll.setWidget(scroll_host)
        root.addWidget(scroll, 1)

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

    def load_from_config(self, config: dict[str, Any]) -> None:
        self._editor.load_from_config(config)
        refresh_settings_text_edit_layouts(self._editor)

    def commit(self) -> None:
        order, sections, format_guide = self._editor.collect()
        self._on_save(order, sections, format_guide)

    def apply_language(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        self.setWindowTitle(tr("chat.edit_wrapper", config=config))
        self._label.setText(strong_label_html(chat_edit_wrapper_label_text(config)))
        self._hint.setText(muted_hint_html(chat_edit_wrapper_hint_text(config)))
        self._cancel_btn.setText(tr("settings.cancel", config=config))
        self._save_btn.setText(tr("settings.save", config=config))

    def apply_theme(self) -> None:
        refresh_native_text_edits_in(self)
        refresh_settings_text_edit_layouts(self._editor)

    def _save_and_close(self) -> None:
        self.commit()
        self.close()
