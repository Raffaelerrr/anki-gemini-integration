from __future__ import annotations

from aqt.qt import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QKeyEvent,
    QKeySequence,
    QObject,
    QPainter,
    QPointF,
    QRectF,
    QSizeF,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
    QTextObjectInterface,
    Qt,
)

from ..wrapper_prefix_tokens import (
    normalize_wrapper_prefix_segments,
    parse_wrapper_prefix_segments,
    serialize_wrapper_prefix_segments,
    wrapper_prefix_has_token,
    wrapper_prefix_requires_token,
    wrapper_token_display_label,
)
from .settings_compact_controls import configure_settings_text_edit
from .theme import wrapper_token_colors
from .widgets import ScrollAwareTextEdit

def _qtext_user_object_type() -> int:
    object_types = getattr(QTextFormat, "ObjectTypes", None)
    if object_types is not None:
        return int(object_types.UserObject)
    return int(QTextFormat.UserObject)


def _qtext_user_property() -> int:
    properties = getattr(QTextFormat, "Property", None)
    if properties is not None:
        return int(properties.UserProperty)
    return int(QTextFormat.UserProperty)


WRAPPER_TOKEN_OBJECT_TYPE = _qtext_user_object_type() + 1
WRAPPER_TOKEN_SECTION_PROP = _qtext_user_property() + 1
_OBJECT_REPLACEMENT = "\uFFFC"
_TOKEN_H_MARGIN = 5
_TOKEN_INNER_PAD_X = 6
_TOKEN_INNER_PAD_Y = 2


class _WrapperTokenRenderer(QObject, QTextObjectInterface):
    def intrinsicSize(self, doc, posInDocument, format) -> QSizeF:
        section_id = format.property(WRAPPER_TOKEN_SECTION_PROP)
        label = wrapper_token_display_label(str(section_id or ""))
        body_metrics = self._body_metrics(doc, posInDocument)
        token_metrics = QFontMetricsF(self._token_font())
        text_width = token_metrics.horizontalAdvance(label)
        width = text_width + (_TOKEN_INNER_PAD_X * 2) + (_TOKEN_H_MARGIN * 2)
        ascent = max(body_metrics.ascent(), token_metrics.ascent() + _TOKEN_INNER_PAD_Y)
        descent = max(body_metrics.descent(), token_metrics.descent() + _TOKEN_INNER_PAD_Y)
        return QSizeF(width, ascent + descent)

    def drawObject(self, painter, rect, doc, posInDocument, format) -> None:
        section_id = format.property(WRAPPER_TOKEN_SECTION_PROP)
        label = wrapper_token_display_label(str(section_id or ""))
        bg, fg = wrapper_token_colors()
        token_font = self._token_font()
        token_metrics = QFontMetricsF(token_font)
        pill_height = token_metrics.height() + (_TOKEN_INNER_PAD_Y * 2)
        pill_width = max(0.0, rect.width() - (_TOKEN_H_MARGIN * 2))
        pill_top = rect.y() + max(0.0, (rect.height() - pill_height) / 2.0)
        pill_rect = QRectF(
            rect.x() + _TOKEN_H_MARGIN,
            pill_top,
            pill_width,
            pill_height,
        )
        text_width = token_metrics.horizontalAdvance(label)
        text_x = pill_rect.x() + ((pill_rect.width() - text_width) / 2.0)
        text_y = pill_top + _TOKEN_INNER_PAD_Y + token_metrics.ascent()
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(bg)))
        painter.drawRoundedRect(pill_rect, 4, 4)
        painter.setPen(QColor(fg))
        painter.setFont(token_font)
        painter.drawText(QPointF(text_x, text_y), label)
        painter.restore()

    @staticmethod
    def _body_metrics(doc, posInDocument) -> QFontMetricsF:
        default_font = doc.defaultFont()
        try:
            char_count = doc.characterCount()
            if char_count <= 0:
                return QFontMetricsF(default_font)
            ref_pos = min(max(posInDocument, 0), char_count - 1)
            if ref_pos > 0:
                ref_pos -= 1
                while ref_pos > 0 and doc.characterAt(ref_pos) in "\n\uFFFC":
                    ref_pos -= 1
            char_format = doc.charFormatAt(ref_pos)
            font = char_format.font()
            if not font.family():
                font = default_font
            return QFontMetricsF(font)
        except Exception:
            return QFontMetricsF(default_font)

    @staticmethod
    def _token_font() -> QFont:
        font = QFont("Consolas")
        if not font.exactMatch():
            font = QFont("Courier New")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(8)
        return font


class WrapperPrefixTextEdit(ScrollAwareTextEdit):
    def __init__(self, parent, *, section_id: str, show_newlines: bool = False) -> None:
        super().__init__(parent)
        self._section_id = section_id
        self._loading = False
        self._wrapper_prefix_editor = True
        self.setAcceptRichText(True)
        configure_settings_text_edit(self, show_newlines=show_newlines)
        self._token_renderer = _WrapperTokenRenderer(self)
        layout = self.document().documentLayout()
        layout.registerHandler(WRAPPER_TOKEN_OBJECT_TYPE, self._token_renderer)
        self.document().contentsChange.connect(self._on_contents_change)

    def refresh_token_theme(self) -> None:
        self.viewport().update()

    def set_prefix_text(self, text: str) -> None:
        self._loading = True
        try:
            self.clear()
            normalized_text = text or ""
            segments = normalize_wrapper_prefix_segments(
                parse_wrapper_prefix_segments(normalized_text, self._section_id),
                self._section_id,
            )
            self._render_segments(segments)
            self._move_cursor_to_end()
        finally:
            self._loading = False

    def to_prefix_text(self) -> str:
        segments = self._document_segments()
        return serialize_wrapper_prefix_segments(segments)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.matches(QKeySequence.StandardKey.Cut):
            if self._selection_intersects_token():
                event.accept()
                return
        if event.matches(QKeySequence.StandardKey.Delete):
            if self._selection_intersects_token():
                event.accept()
                return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self._selection_intersects_token():
                event.accept()
                return
            cursor = self.textCursor()
            if event.key() == Qt.Key.Key_Backspace and self._position_is_token(cursor.position() - 1):
                event.accept()
                return
            if event.key() == Qt.Key.Key_Delete and self._position_is_token(cursor.position()):
                event.accept()
                return
        if event.text() and not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self._selection_intersects_token():
                event.accept()
                return
        super().keyPressEvent(event)
        if wrapper_prefix_requires_token(self._section_id):
            segments = self._document_segments()
            if not wrapper_prefix_has_token(segments, self._section_id):
                self._loading = True
                try:
                    self._ensure_required_token()
                finally:
                    self._loading = False

    def cut(self) -> None:
        if self._selection_intersects_token():
            return
        super().cut()

    def insertFromMimeData(self, source) -> None:
        if source is None:
            return
        text = source.text()
        if not text:
            return
        cursor = self.textCursor()
        if cursor.hasSelection() and self._range_intersects_token(
            cursor.selectionStart(),
            cursor.selectionEnd(),
        ):
            return
        cursor.beginEditBlock()
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            if self._range_intersects_token(start, end):
                cursor.endEditBlock()
                return
            cursor.removeSelectedText()
        for kind, content in normalize_wrapper_prefix_segments(
            parse_wrapper_prefix_segments(text, self._section_id),
            self._section_id,
            allow_token=not wrapper_prefix_has_token(
                self._document_segments(),
                self._section_id,
            ),
        ):
            if kind == "text":
                if content:
                    cursor.insertText(content)
            elif kind == "token":
                self._insert_token(cursor, content)
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self._loading = True
        try:
            self._apply_segment_normalization()
            self._ensure_required_token()
        finally:
            self._loading = False

    def _on_contents_change(self, position: int, removed: int, added: int) -> None:
        if self._loading:
            return
        self._loading = True
        try:
            self._apply_segment_normalization()
            self._ensure_required_token()
        finally:
            self._loading = False

    def _apply_segment_normalization(self) -> None:
        segments = self._document_segments()
        normalized = self._normalize_segments(segments)
        if normalized == segments:
            return
        self._set_segments(normalized)

    def _normalize_segments(self, segments: list[tuple[str, str]]) -> list[tuple[str, str]]:
        return normalize_wrapper_prefix_segments(segments, self._section_id)

    def _set_segments(self, segments: list[tuple[str, str]]) -> None:
        cursor = QTextCursor(self.document())
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.removeSelectedText()
        self._render_segments(self._normalize_segments(segments), cursor=cursor)
        self.setTextCursor(cursor)

    def _render_segments(
        self,
        segments: list[tuple[str, str]],
        *,
        cursor: QTextCursor | None = None,
    ) -> None:
        cursor = cursor or self.textCursor()
        cursor.beginEditBlock()
        for kind, content in segments:
            if kind == "text":
                if content:
                    cursor.insertText(content)
            elif kind == "token":
                self._insert_token(cursor, content)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def _ensure_required_token(self) -> None:
        if not wrapper_prefix_requires_token(self._section_id):
            return
        segments = self._document_segments()
        if wrapper_prefix_has_token(segments, self._section_id):
            return
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._insert_token(cursor, self._section_id)

    def _insert_token(self, cursor: QTextCursor, section_id: str) -> None:
        fmt = QTextCharFormat()
        fmt.setObjectType(WRAPPER_TOKEN_OBJECT_TYPE)
        fmt.setProperty(WRAPPER_TOKEN_SECTION_PROP, section_id)
        cursor.insertText(_OBJECT_REPLACEMENT, fmt)

    @staticmethod
    def _character_at(doc, position: int) -> str:
        raw = doc.characterAt(position)
        if isinstance(raw, str):
            return raw
        if raw is None:
            return ""
        is_null = getattr(raw, "isNull", None)
        if callable(is_null) and is_null():
            return ""
        return str(raw)

    def _document_segments(self) -> list[tuple[str, str]]:
        doc = self.document()
        segments: list[tuple[str, str]] = []
        end = max(0, doc.characterCount() - 1)
        position = 0
        while position < end:
            char = self._character_at(doc, position)
            if not char:
                position += 1
                continue
            if char == _OBJECT_REPLACEMENT:
                cursor = QTextCursor(doc)
                cursor.setPosition(position)
                fmt = cursor.charFormat()
                if fmt.objectType() == WRAPPER_TOKEN_OBJECT_TYPE:
                    section_id = fmt.property(WRAPPER_TOKEN_SECTION_PROP)
                    if section_id:
                        segments.append(("token", str(section_id)))
            elif char in ("\u2029", "\n"):
                self._append_document_text(segments, "\n")
            else:
                self._append_document_text(segments, char)
            position += 1
        return segments

    @staticmethod
    def _append_document_text(segments: list[tuple[str, str]], text: str) -> None:
        if not text:
            return
        if segments and segments[-1][0] == "text":
            segments[-1] = ("text", segments[-1][1] + text)
        else:
            segments.append(("text", text))

    def _position_is_token(self, position: int) -> bool:
        if position < 0:
            return False
        cursor = QTextCursor(self.document())
        cursor.setPosition(position)
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
        if not cursor.hasSelection():
            return False
        fmt = cursor.charFormat()
        return fmt.objectType() == WRAPPER_TOKEN_OBJECT_TYPE

    def _range_intersects_token(self, start: int, end: int) -> bool:
        if end <= start:
            return False
        cursor = QTextCursor(self.document())
        cursor.setPosition(start)
        while cursor.position() < end:
            if self._position_is_token(cursor.position()):
                return True
            cursor.movePosition(QTextCursor.MoveOperation.Right)
        return False

    def _selection_intersects_token(self) -> bool:
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return False
        return self._range_intersects_token(cursor.selectionStart(), cursor.selectionEnd())

    def _move_cursor_to_end(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)


def create_wrapper_prefix_text_edit(
    parent,
    *,
    section_id: str,
    show_newlines: bool = False,
) -> tuple[object, WrapperPrefixTextEdit]:
    from .settings_compact_controls import SETTINGS_TEXT_EDIT_MAX_HEIGHT, SETTINGS_TEXT_EDIT_MIN_HEIGHT
    from aqt.qt import QVBoxLayout, QWidget, QSizePolicy

    shell = QWidget(parent)
    shell.setObjectName("settingsTextEditShell")
    shell.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    shell_layout = QVBoxLayout(shell)
    shell_layout.setContentsMargins(0, 0, 0, 0)
    shell_layout.setSpacing(0)

    editor = WrapperPrefixTextEdit(shell, section_id=section_id, show_newlines=show_newlines)
    editor._settings_shell = shell
    from .theme import apply_native_text_edit_surface_theme
    from .widgets import bind_text_edit_auto_height

    apply_native_text_edit_surface_theme(editor)
    bind_text_edit_auto_height(
        editor,
        minimum=SETTINGS_TEXT_EDIT_MIN_HEIGHT,
        maximum=SETTINGS_TEXT_EDIT_MAX_HEIGHT,
    )
    shell_layout.addWidget(editor)
    return shell, editor
