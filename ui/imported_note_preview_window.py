from __future__ import annotations

from collections.abc import Callable

from aqt.qt import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    Qt,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import load_config
from ..i18n import tr
from .note_fields import apply_field_rich_edit_theme, load_field_rich_edit
from .note_math_preview import (
    cleanup_note_preview_webview,
    create_note_preview_webview,
    load_note_preview_webview,
    web_math_preview_available,
)
from .settings_compact_controls import create_ui_text_edit
from .theme import (
    apply_native_fields_scroll_theme,
    field_name_label_html,
)
from .widgets import bind_text_edit_auto_height

_LABEL_EDITOR_SPACING = 2
_FIELD_BLOCK_SPACING = 8
_FIELD_MIN_HEIGHT = 56


def _clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


class ImportedNotePreviewWindow(QWidget):
    """Read-only imported note preview in a separate window."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        field_provider: Callable[[], list[tuple[str, str]]],
        notetype_id_provider: Callable[[], int | None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self._field_provider = field_provider
        self._notetype_id_provider = notetype_id_provider or (lambda: None)
        self._uses_web_math = False
        self._web: QWidget | None = None
        self._scroll: QScrollArea | None = None
        self._host: QWidget | None = None
        self._fields_layout: QVBoxLayout | None = None
        self.resize(520, 480)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        self._refresh_btn = QPushButton(self)
        self._refresh_btn.setFlat(True)
        self._refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self._refresh_btn)
        root.addLayout(toolbar)

        self._content_host = QWidget(self)
        self._content_layout = QVBoxLayout(self._content_host)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        if web_math_preview_available():
            self._ensure_web_view()
        if not self._uses_web_math:
            self._setup_plain_preview()

        root.addWidget(self._content_host, 1)
        self.apply_language()

    def _ensure_web_view(self) -> bool:
        if self._web is not None:
            self._uses_web_math = True
            return True
        if not web_math_preview_available():
            self._uses_web_math = False
            return False
        try:
            self._web = create_note_preview_webview(self._content_host)
            self._content_layout.addWidget(self._web, 1)
            self._uses_web_math = True
            return True
        except Exception:
            self._uses_web_math = False
            return False

    def _setup_plain_preview(self) -> None:
        if self._fields_layout is not None:
            return
        self._scroll = QScrollArea(self._content_host)
        self._scroll.setWidgetResizable(True)
        self._host = QWidget(self._scroll)
        self._host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._host.setStyleSheet("background: transparent;")
        self._fields_layout = QVBoxLayout(self._host)
        self._fields_layout.setContentsMargins(8, 8, 8, 10)
        self._fields_layout.setSpacing(0)
        self._fields_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._host)
        self._content_layout.addWidget(self._scroll, 1)
        apply_native_fields_scroll_theme(self, self._scroll)

    def _teardown_web_view(self) -> None:
        if self._web is None:
            return
        cleanup_note_preview_webview(self._web)
        self._content_layout.removeWidget(self._web)
        self._web.deleteLater()
        self._web = None
        self._uses_web_math = False

    def apply_language(self, config: dict | None = None) -> None:
        config = config or load_config()
        self.setWindowTitle(tr("chat.preview.window_title", config=config))
        self._refresh_btn.setToolTip(tr("chat.preview.refresh", config=config))
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        if not icon.isNull():
            self._refresh_btn.setIcon(icon)
            self._refresh_btn.setText("")
        else:
            self._refresh_btn.setIcon(icon)
            self._refresh_btn.setText("↻")

    def apply_theme(self) -> None:
        if self._scroll is not None:
            apply_native_fields_scroll_theme(self, self._scroll)
        if self._host is not None:
            for editor in self._host.findChildren(QTextEdit):
                apply_field_rich_edit_theme(editor)
        if self._uses_web_math and self._web is not None:
            self.refresh()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self._teardown_web_view()
        super().closeEvent(event)

    def refresh(self) -> None:
        config = load_config()
        fields = [
            (name, value)
            for name, value in self._field_provider()
            if value.strip()
        ]
        if self._ensure_web_view():
            load_note_preview_webview(
                self._web,
                fields,
                empty_message=tr("chat.preview.empty", config=config),
                config=config,
                notetype_id=self._notetype_id_provider(),
            )
            return
        self._setup_plain_preview()
        self._refresh_plain_preview(fields, config)

    def _refresh_plain_preview(
        self,
        fields: list[tuple[str, str]],
        config: dict,
    ) -> None:
        if self._fields_layout is None or self._host is None:
            return
        _clear_layout(self._fields_layout)
        if not fields:
            empty = QLabel(tr("chat.preview.empty", config=config), self._host)
            empty.setWordWrap(True)
            self._fields_layout.addWidget(empty)
            return

        for index, (name, value) in enumerate(fields):
            if index > 0:
                gap = QWidget(self._host)
                gap.setFixedHeight(_FIELD_BLOCK_SPACING)
                gap.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
                self._fields_layout.addWidget(gap)

            label = QLabel(field_name_label_html(name), self._host)
            label.setContentsMargins(0, 0, 0, _LABEL_EDITOR_SPACING)
            label.setStyleSheet("margin: 0px; padding: 0px; background: transparent;")
            label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            label.setFixedHeight(label.fontMetrics().height() + _LABEL_EDITOR_SPACING)
            self._fields_layout.addWidget(label)

            editor_shell, editor = create_ui_text_edit(
                self._host,
                editor_class=QTextEdit,
            )
            editor.setReadOnly(True)
            load_field_rich_edit(editor, value)
            editor.document().setDocumentMargin(0)
            editor.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            bind_text_edit_auto_height(editor, minimum=_FIELD_MIN_HEIGHT, maximum=None)
            self._fields_layout.addWidget(editor_shell)
