from __future__ import annotations

import math

from aqt.qt import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QObject,
    QScrollArea,
    QSpinBox,
    Qt,
    QTimer,
    QTextEdit,
    QWidget,
)

_WHEEL_EVENT_TYPE = 31  # QEvent.Type.Wheel
_WHEEL_GESTURE_MS = 300


def _qt_widget_alive(widget: QWidget | None) -> bool:
    if widget is None:
        return False
    try:
        widget.objectName()
        return True
    except RuntimeError:
        return False


def _event_global_pos(event) -> object:
    if hasattr(event, "globalPosition"):
        return event.globalPosition().toPoint()
    return event.globalPos()


def _forward_wheel_event(widget: QWidget, event) -> None:
    ancestor = widget.parentWidget()
    while ancestor is not None:
        if isinstance(ancestor, QScrollArea):
            _scroll_area_by_wheel(ancestor, event)
            return
        ancestor = ancestor.parentWidget()
    event.ignore()


def _scroll_area_by_wheel(scroll: QScrollArea, event) -> None:
    scroll.wheelEvent(event)
    event.accept()


def _text_edit_layout_width(editor: QTextEdit) -> int:
    if not _qt_widget_alive(editor):
        return 320
    viewport = editor.viewport()
    if viewport is not None and viewport.width() > 4:
        return viewport.width()
    frame = editor.frameWidth() * 2
    if editor.width() > frame + 4:
        return editor.width() - frame
    widget = editor.parentWidget()
    while widget is not None:
        if widget.width() > 4:
            return max(32, widget.width() - 16)
        widget = widget.parentWidget()
    return 320


def bind_text_edit_auto_height(
    editor: QTextEdit,
    *,
    minimum: int = 56,
    maximum: int | None = 160,
) -> None:
    """Grow the editor with its content; scroll internally only after *maximum*.

    Pass ``maximum=None`` to expand to full content height (for nested scroll areas).
    """

    def _adjust() -> None:
        if not _qt_widget_alive(editor):
            return
        try:
            text_width = _text_edit_layout_width(editor)
            editor.document().setTextWidth(text_width)
            doc_height = editor.document().documentLayout().documentSize().height()
            frame = editor.frameWidth() * 2
            natural = int(math.ceil(doc_height + frame + 8))
            if maximum is None:
                height = int(max(minimum, natural))
                editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            else:
                height = int(max(minimum, min(natural, maximum)))
            if editor.height() != height:
                editor.setFixedHeight(height)
                editor.updateGeometry()
        except RuntimeError:
            return

    class _ResizeFilter(QObject):
        def eventFilter(self, obj, event) -> bool:
            if event.type() == 14:  # QEvent.Type.Resize
                _adjust()
            return False

    editor.textChanged.connect(_adjust)
    editor.document().contentsChanged.connect(_adjust)
    resize_filter = _ResizeFilter(editor)
    editor.installEventFilter(resize_filter)
    viewport = editor.viewport()
    if viewport is not None:
        viewport.installEventFilter(resize_filter)
    editor._auto_height_resize_filter = resize_filter  # prevent GC
    editor._auto_height_adjust = _adjust
    QTimer.singleShot(0, _adjust)
    if maximum is None:
        QTimer.singleShot(50, _adjust)
        QTimer.singleShot(200, _adjust)


class _ScrollAwareWheelAppFilter(QObject):
    """Record wheel-gesture targets for the whole window (including page scroll areas)."""

    def eventFilter(self, obj, event) -> bool:
        if event.type() != _WHEEL_EVENT_TYPE or not isinstance(obj, QWidget):
            return False
        window = obj.window()
        if window is None or not window.findChildren(ScrollAwareTextEdit):
            return False
        ScrollAwareTextEdit._update_wheel_gesture_lock(event)
        return False


def _install_scroll_aware_wheel_app_filter() -> None:
    app = QApplication.instance()
    if app is None or getattr(app, "_scroll_aware_wheel_filter_installed", False):
        return
    app.installEventFilter(_ScrollAwareWheelAppFilter(app))
    app._scroll_aware_wheel_filter_installed = True


class _ScrollAwareTextEditWheelFilter(QObject):
    """Intercept wheel events on the editor and its viewport (Qt delivers them there)."""

    def __init__(self, editor: ScrollAwareTextEdit) -> None:
        super().__init__(editor)
        self._editor = editor

    def eventFilter(self, obj, event) -> bool:
        if event.type() != _WHEEL_EVENT_TYPE:
            return False
        editor = self._editor
        cls = ScrollAwareTextEdit
        lock = cls._wheel_gesture_lock

        if isinstance(lock, QScrollArea):
            _scroll_area_by_wheel(lock, event)
            return True

        if not editor.hasFocus():
            scroll = cls._find_enclosing_scroll_area(editor)
            if scroll is not None:
                _scroll_area_by_wheel(scroll, event)
            else:
                event.ignore()
            return True

        if lock is editor or (
            lock is None and cls._contains_global_point(editor, _event_global_pos(event))
        ):
            editor._wheel_scroll_self(event)
            return True

        scroll = cls._find_enclosing_scroll_area(editor)
        if scroll is not None:
            _scroll_area_by_wheel(scroll, event)
            return True
        return False


class ScrollAwareTextEdit(QTextEdit):
    """Scroll page by default; scroll text content only after the field is clicked."""

    _wheel_gesture_lock: ScrollAwareTextEdit | QScrollArea | None = None
    _wheel_gesture_timer: QTimer | None = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._ensure_wheel_gesture_timer()
        _install_scroll_aware_wheel_app_filter()
        self._wheel_filter = _ScrollAwareTextEditWheelFilter(self)
        self.installEventFilter(self._wheel_filter)
        viewport = self.viewport()
        if viewport is not None:
            viewport.installEventFilter(self._wheel_filter)

    @classmethod
    def _ensure_wheel_gesture_timer(cls) -> QTimer:
        if cls._wheel_gesture_timer is None:
            timer = QTimer()
            timer.setSingleShot(True)
            timer.setInterval(_WHEEL_GESTURE_MS)
            timer.timeout.connect(lambda: cls._clear_wheel_gesture_lock())
            cls._wheel_gesture_timer = timer
        return cls._wheel_gesture_timer

    @classmethod
    def _clear_wheel_gesture_lock(cls) -> None:
        cls._wheel_gesture_lock = None

    @classmethod
    def _widget_under_global_pos(cls, global_pos) -> QWidget | None:
        return QApplication.widgetAt(global_pos)

    @classmethod
    def _contains_global_point(cls, widget: QWidget, global_pos) -> bool:
        return widget.rect().contains(widget.mapFromGlobal(global_pos))

    @classmethod
    def _find_scroll_aware_editor(cls, widget: QWidget | None) -> ScrollAwareTextEdit | None:
        while widget is not None:
            if isinstance(widget, ScrollAwareTextEdit):
                return widget
            widget = widget.parentWidget()
        return None

    @classmethod
    def _find_enclosing_scroll_area(cls, widget: QWidget | None) -> QScrollArea | None:
        while widget is not None:
            if isinstance(widget, QScrollArea):
                return widget
            widget = widget.parentWidget()
        return None

    @classmethod
    def _can_scroll_internally_in_direction(cls, editor: ScrollAwareTextEdit, delta: int) -> bool:
        if not editor.is_internally_scrollable():
            return False
        if delta == 0:
            return True
        bar = editor.verticalScrollBar()
        at_top = bar.value() <= bar.minimum()
        at_bottom = bar.value() >= bar.maximum()
        if delta > 0 and at_top:
            return False
        if delta < 0 and at_bottom:
            return False
        return True

    @classmethod
    def _resolve_wheel_gesture_lock(
        cls,
        global_pos,
        event,
    ) -> ScrollAwareTextEdit | QScrollArea | None:
        widget = cls._widget_under_global_pos(global_pos)
        editor = cls._find_scroll_aware_editor(widget)
        if (
            editor is not None
            and editor.hasFocus()
            and cls._contains_global_point(editor, global_pos)
        ):
            delta = event.angleDelta().y()
            if cls._can_scroll_internally_in_direction(editor, delta):
                return editor
            return cls._find_enclosing_scroll_area(editor)
        return cls._find_enclosing_scroll_area(widget)

    @classmethod
    def _update_wheel_gesture_lock(cls, event) -> None:
        phase = event.phase()
        if phase == Qt.ScrollPhase.ScrollBegin:
            cls._wheel_gesture_lock = cls._resolve_wheel_gesture_lock(
                _event_global_pos(event),
                event,
            )
            cls._ensure_wheel_gesture_timer().stop()
            return
        if phase == Qt.ScrollPhase.ScrollEnd:
            cls._clear_wheel_gesture_lock()
            cls._ensure_wheel_gesture_timer().stop()
            return
        timer = cls._ensure_wheel_gesture_timer()
        if not timer.isActive():
            cls._wheel_gesture_lock = cls._resolve_wheel_gesture_lock(
                _event_global_pos(event),
                event,
            )
        timer.start()

    def clear_text_selection(self) -> None:
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)

    def focusInEvent(self, event) -> None:
        self._clear_peer_selections_in_window()
        super().focusInEvent(event)

    def mousePressEvent(self, event) -> None:
        self._clear_peer_selections_in_window()
        super().mousePressEvent(event)

    def _clear_peer_selections_in_window(self) -> None:
        host = self.window()
        if host is None:
            return
        for editor in host.findChildren(ScrollAwareTextEdit):
            if editor is not self:
                editor.clear_text_selection()

    def is_internally_scrollable(self) -> bool:
        bar = self.verticalScrollBar()
        return bar.maximum() > bar.minimum()

    def _forward_wheel_to_enclosing_scroll(self, event) -> None:
        scroll = self._find_enclosing_scroll_area(self)
        if scroll is not None:
            _scroll_area_by_wheel(scroll, event)
        else:
            event.ignore()

    def _wheel_scroll_self(self, event) -> None:
        if not self.is_internally_scrollable():
            self._forward_wheel_to_enclosing_scroll(event)
            return

        delta = event.angleDelta().y()
        if delta == 0 or not self._can_scroll_internally_in_direction(self, delta):
            event.accept()
            return
        super().wheelEvent(event)
        event.accept()


class _NoWheelMixin:
    def _install_no_wheel(self) -> None:
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        line_edit = self.lineEdit() if hasattr(self, "lineEdit") else None
        if line_edit is not None:
            line_edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == _WHEEL_EVENT_TYPE:
            _forward_wheel_event(self, event)
            return True
        return super().eventFilter(obj, event)

    def wheelEvent(self, event) -> None:
        _forward_wheel_event(self, event)


class PlainNoWheelSpinBox(_NoWheelMixin, QSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._install_no_wheel()


class PlainNoWheelDoubleSpinBox(_NoWheelMixin, QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._install_no_wheel()


class PlainNoWheelComboBox(_NoWheelMixin, QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._install_no_wheel()
