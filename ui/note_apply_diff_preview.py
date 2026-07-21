"""Side-by-side formatted before/after preview for APPLY_NOTE updates."""

from __future__ import annotations

from typing import Any

from aqt.qt import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    Qt,
)

from ..config import load_config
from ..i18n import tr
from .note_math_preview import (
    cleanup_note_preview_webview,
    create_note_preview_webview,
    load_note_preview_webview,
    web_math_preview_available,
)
from .settings_compact_controls import create_settings_hint_label
from .theme import muted_hint_html
from .themed_windows import configure_snappable_window, register_themed_window


class NoteApplyDiffPreviewWindow(QWidget):
    """Modeless before/after MathJax preview for an update target."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(None)
        configure_snappable_window(self)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        register_themed_window(self)
        self._config = load_config()
        self._before: list[tuple[str, str]] = []
        self._after: list[tuple[str, str]] = []
        self._notetype_id: int | None = None
        self._before_web: QWidget | None = None
        self._after_web: QWidget | None = None
        self.resize(980, 640)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self._intro = create_settings_hint_label(self, "")
        root.addWidget(self._intro)

        columns = QHBoxLayout()
        left = QVBoxLayout()
        self._before_label = QLabel(self)
        left.addWidget(self._before_label)
        self._before_host = QWidget(self)
        self._before_host_layout = QVBoxLayout(self._before_host)
        self._before_host_layout.setContentsMargins(0, 0, 0, 0)
        left.addWidget(self._before_host, 1)

        right = QVBoxLayout()
        self._after_label = QLabel(self)
        right.addWidget(self._after_label)
        self._after_host = QWidget(self)
        self._after_host_layout = QVBoxLayout(self._after_host)
        self._after_host_layout.setContentsMargins(0, 0, 0, 0)
        right.addWidget(self._after_host, 1)

        columns.addLayout(left, 1)
        columns.addLayout(right, 1)
        root.addLayout(columns, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._close_btn = QPushButton(self)
        self._close_btn.clicked.connect(self.close)
        buttons.addWidget(self._close_btn)
        root.addLayout(buttons)

        self._ensure_webviews()
        self.apply_language()
        self.apply_theme()

    def show_diff(
        self,
        *,
        before: list[tuple[str, str]],
        after: list[tuple[str, str]],
        notetype_id: int | None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._config = config or load_config()
        self._before = list(before)
        self._after = list(after)
        self._notetype_id = notetype_id
        self.apply_language(self._config)
        self.apply_theme()
        self._reload_panels()
        self.show()
        self.raise_()
        self.activateWindow()

    def apply_language(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or load_config()
        self.setWindowTitle(
            tr("chat.apply_note.diff.title", config=self._config)
        )
        self._intro.setText(
            muted_hint_html(tr("chat.apply_note.diff.intro", config=self._config))
        )
        self._before_label.setText(
            f"<b>{tr('chat.apply_note.diff.before', config=self._config)}</b>"
        )
        self._after_label.setText(
            f"<b>{tr('chat.apply_note.diff.after', config=self._config)}</b>"
        )
        self._close_btn.setText(tr("preview.cancel", config=self._config))

    def apply_theme(self) -> None:
        self.apply_language(self._config)
        self._reload_panels()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._teardown_webviews()
        super().closeEvent(event)

    def _ensure_webviews(self) -> bool:
        if not web_math_preview_available():
            return False
        try:
            if self._before_web is None:
                self._before_web = create_note_preview_webview(self._before_host)
                self._before_host_layout.addWidget(self._before_web, 1)
            if self._after_web is None:
                self._after_web = create_note_preview_webview(self._after_host)
                self._after_host_layout.addWidget(self._after_web, 1)
            return True
        except (AttributeError, TypeError, RuntimeError, OSError):
            self._teardown_webviews()
            return False

    def _teardown_webviews(self) -> None:
        for attr in ("_before_web", "_after_web"):
            web = getattr(self, attr)
            if web is None:
                continue
            cleanup_note_preview_webview(web)
            web.deleteLater()
            setattr(self, attr, None)

    def _reload_panels(self) -> None:
        if not self._ensure_webviews():
            self._intro.setText(
                muted_hint_html(
                    tr("chat.apply_note.diff.unavailable", config=self._config)
                )
            )
            return
        empty = tr("chat.preview.empty", config=self._config)
        load_note_preview_webview(
            self._before_web,
            self._before,
            empty_message=empty,
            config=self._config,
            notetype_id=self._notetype_id,
        )
        load_note_preview_webview(
            self._after_web,
            self._after,
            empty_message=empty,
            config=self._config,
            notetype_id=self._notetype_id,
        )
