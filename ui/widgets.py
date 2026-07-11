from __future__ import annotations

import math
import weakref

from aqt.qt import (    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QObject,
    QScrollArea,
    QScrollBar,
    QSpinBox,
    Qt,
    QTimer,
    QTextEdit,
    QWidget,
)

_WHEEL_EVENT_TYPE = 31  # QEvent.Type.Wheel
_WHEEL_GESTURE_MS = 300
_SCROLL_AWARE_WINDOW_COUNTS: weakref.WeakKeyDictionary[QWidget, int] = weakref.WeakKeyDictionary()
_SCROLL_AWARE_EDITORS_BY_WINDOW: weakref.WeakKeyDictionary[
    QWidget, set[ScrollAwareTextEdit]
] = weakref.WeakKeyDictionary()

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


def _wheel_deltas(event) -> tuple[int, int]:
    """Read wheel deltas for edge detection; native scrolling uses the original event."""
    delta_y = event.angleDelta().y()
    delta_x = event.angleDelta().x()
    if hasattr(event, "pixelDelta"):
        pixel = event.pixelDelta()
        px = pixel.x()
        py = pixel.y()
        if px != 0 or py != 0:
            if py != 0:
                delta_y = py
            if px != 0:
                delta_x = px
    return delta_y, delta_x


def _is_scroll_bar_widget(widget: QWidget | None) -> bool:
    while widget is not None:
        if isinstance(widget, QScrollBar):
            return True
        widget = widget.parentWidget()
    return False


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


def _scroll_bar_by_wheel_delta(bar: QScrollBar, delta: int) -> None:
    if delta == 0:
        return
    step = max(1, bar.singleStep())
    movement = round(delta * step / 120)
    if movement == 0:
        movement = 1 if delta > 0 else -1
    bar.setValue(max(bar.minimum(), min(bar.maximum(), bar.value() - movement)))


def _apply_native_wheel_scroll(editor: QTextEdit, event) -> None:
    """Move scroll bars directly; Qt wheel delivery is unreliable once filters intercept."""
    pixel = event.pixelDelta()
    angle = event.angleDelta()
    px = pixel.x()
    py = pixel.y()
    ax = angle.x()
    ay = angle.y()

    if px or py:
        if py:
            bar = editor.verticalScrollBar()
            if bar is not None:
                bar.setValue(max(bar.minimum(), min(bar.maximum(), bar.value() - py)))
        if px:
            bar = editor.horizontalScrollBar()
            if bar is not None:
                bar.setValue(max(bar.minimum(), min(bar.maximum(), bar.value() - px)))
    else:
        if ay:
            bar = editor.verticalScrollBar()
            if bar is not None:
                _scroll_bar_by_wheel_delta(bar, ay)
        if ax:
            bar = editor.horizontalScrollBar()
            if bar is not None:
                _scroll_bar_by_wheel_delta(bar, ax)
    event.accept()


_WIDGET_SIZE_MAX = 16777215
_SETTINGS_TEXT_EDIT_MIN_WIDTH = 160
_SETTINGS_TEXT_EDIT_FALLBACK_WIDTH = 520


def _propagate_widget_geometry(widget: QWidget) -> None:
    parent = widget.parentWidget()
    while parent is not None:
        parent.updateGeometry()
        parent = parent.parentWidget()


def _settings_form_available_width(widget: QWidget) -> int:
    best = 0
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QScrollArea):
            viewport = parent.viewport()
            if viewport is not None and viewport.width() > 0:
                return max(viewport.width() - 16, _SETTINGS_TEXT_EDIT_MIN_WIDTH)
        width = parent.width()
        if width > best:
            best = width
        parent = parent.parentWidget()
    if best > 0:
        return max(best - 16, _SETTINGS_TEXT_EDIT_MIN_WIDTH)
    return _SETTINGS_TEXT_EDIT_FALLBACK_WIDTH


def _settings_editor_ideal_content_width(editor: QTextEdit, *, frame: int) -> int:
    document = editor.document()
    document.setTextWidth(-1)
    if document.isEmpty():
        placeholder = editor.placeholderText().strip()
        if placeholder:
            metrics = editor.fontMetrics()
            max_line = 0
            for line in placeholder.replace("\r\n", "\n").split("\n"):
                max_line = max(max_line, metrics.horizontalAdvance(line))
            return int(max_line + frame + 16)
    return int(math.ceil(document.idealWidth() + frame + 16))


def _settings_placeholder_height(
    editor: QTextEdit,
    *,
    width: int,
    min_height: int,
) -> int:
    placeholder = editor.placeholderText().strip()
    if not placeholder:
        return min_height
    frame = editor.frameWidth() * 2
    inner = max(width - frame - 16, 1)
    rect = editor.fontMetrics().boundingRect(
        0,
        0,
        inner,
        10_000,
        int(Qt.TextFlag.TextWordWrap),
        placeholder,
    )
    return int(max(min_height, rect.height() + frame + 16))


def _settings_target_width(editor: QTextEdit, *, frame: int) -> int:
    available = _settings_form_available_width(editor)
    document = editor.document()
    previous = document.textWidth()
    ideal = _settings_editor_ideal_content_width(editor, frame=frame)
    if previous > 0:
        document.setTextWidth(previous)
    else:
        document.setTextWidth(-1)
    return min(max(ideal, _SETTINGS_TEXT_EDIT_MIN_WIDTH), available)


def _sync_settings_text_edit_shell(editor: QTextEdit, *, width: int, height: int) -> None:
    shell = getattr(editor, "_settings_shell", None)
    if shell is None:
        return
    if shell.width() != width:
        shell.setFixedWidth(width)
    if shell.height() != height:
        shell.setFixedHeight(height)


def bind_text_edit_auto_height(
    editor: QTextEdit,
    *,
    minimum: int = 56,
    maximum: int | None = 160,
) -> None:
    """Grow the editor with its content; scroll internally only after *maximum*.

    Pass ``maximum=None`` to expand to full content height (for nested scroll areas).
    """
    existing_adjust = getattr(editor, "_auto_height_adjust", None)
    if existing_adjust is not None:
        editor._auto_height_minimum = minimum
        editor._auto_height_maximum = maximum
        existing_adjust()
        return

    def _content_height() -> int:
        document = editor.document()
        layout = document.documentLayout()
        doc_height = layout.documentSize().height()
        last = document.lastBlock()
        if last.isValid():
            block_rect = layout.blockBoundingRect(last)
            doc_height = max(doc_height, block_rect.bottom())
        contents = editor.contentsMargins()
        chrome = (
            editor.frameWidth() * 2
            + document.documentMargin() * 2
            + contents.top()
            + contents.bottom()
            + 8
        )
        return int(math.ceil(doc_height + chrome + 2))

    def _adjust() -> None:
        if not _qt_widget_alive(editor):
            return
        if getattr(editor, "_auto_height_adjusting", False):
            return
        editor._auto_height_adjusting = True
        try:
            min_height = getattr(editor, "_auto_height_minimum", minimum)
            max_height = getattr(editor, "_auto_height_maximum", maximum)
            frame = editor.frameWidth() * 2
            wrap_mode = editor.lineWrapMode()
            settings_width = None
            document = editor.document()
            document.blockSignals(True)
            try:
                if wrap_mode == QTextEdit.LineWrapMode.NoWrap:
                    document.setTextWidth(-1)
                elif getattr(editor, "_settings_text_edit", False):
                    settings_width = _settings_target_width(editor, frame=frame)
                    document.setTextWidth(max(settings_width - frame - 8, 1))
                else:
                    viewport_width = editor.viewport().width()
                    if viewport_width <= 0:
                        viewport_width = max(editor.width() - frame, 0)
                    if viewport_width <= 0:
                        parent = editor.parentWidget()
                        if parent is not None and parent.width() > 0:
                            viewport_width = max(parent.width() - 8, 1)
                    document.setTextWidth(
                        max(viewport_width, 1) if viewport_width > 0 else -1
                    )
            finally:
                document.blockSignals(False)
            natural = _content_height()
            if (
                getattr(editor, "_settings_text_edit", False)
                and document.isEmpty()
                and editor.placeholderText().strip()
            ):
                measure_width = settings_width or max(editor.width(), _SETTINGS_TEXT_EDIT_MIN_WIDTH)
                natural = max(
                    natural,
                    _settings_placeholder_height(
                        editor,
                        width=measure_width,
                        min_height=min_height,
                    ),
                )
            if max_height is None:
                height = int(max(min_height, natural))
                editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                editor.setHorizontalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                    if wrap_mode != QTextEdit.LineWrapMode.NoWrap
                    else Qt.ScrollBarPolicy.ScrollBarAsNeeded
                )
                editor.setMinimumHeight(height)
                editor.setMaximumHeight(_WIDGET_SIZE_MAX)
            else:
                height = int(max(min_height, min(natural, max_height)))
                editor.setVerticalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAsNeeded
                    if natural > max_height
                    else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                )
                editor.setHorizontalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAsNeeded
                    if wrap_mode == QTextEdit.LineWrapMode.NoWrap
                    else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                )
                editor.setMinimumHeight(min_height)
                editor.setMaximumHeight(height)

            shell = getattr(editor, "_settings_shell", None)
            if (
                editor.height() == height
                and (
                    settings_width is None
                    or (shell is not None and shell.width() == settings_width and shell.height() == height)
                )
            ):
                return

            editor.setFixedHeight(height)
            editor.updateGeometry()
            if settings_width is not None:
                _sync_settings_text_edit_shell(
                    editor,
                    width=settings_width,
                    height=height,
                )
            _propagate_widget_geometry(editor)
        except RuntimeError:
            return
        finally:
            editor._auto_height_adjusting = False

    editor._auto_height_minimum = minimum
    editor._auto_height_maximum = maximum

    class _ResizeFilter(QObject):
        def eventFilter(self, obj, event) -> bool:
            if event.type() == 14:  # QEvent.Type.Resize
                _adjust()
            return False

    editor.textChanged.connect(_adjust)
    resize_filter = _ResizeFilter(editor)
    editor.installEventFilter(resize_filter)
    viewport = editor.viewport()
    if viewport is not None:
        viewport.installEventFilter(resize_filter)
    editor._auto_height_resize_filter = resize_filter  # prevent GC
    editor._auto_height_adjust = _adjust
    QTimer.singleShot(0, _adjust)


class _ScrollAwareWheelAppFilter(QObject):
    """Record wheel-gesture targets for the whole window (including page scroll areas)."""

    def eventFilter(self, obj, event) -> bool:
        if event.type() != _WHEEL_EVENT_TYPE or not isinstance(obj, QWidget):
            return False
        window = obj.window()
        if window is None or not ScrollAwareTextEdit._window_uses_scroll_aware_wheel(window):
            return False
        ScrollAwareTextEdit._update_wheel_gesture_lock(event)
        editor = ScrollAwareTextEdit._find_scroll_aware_editor(obj)
        if (
            editor is not None
            and editor.hasFocus()
            and ScrollAwareTextEdit._page_scroll_gesture_lock() is None
        ):
            decision = ScrollAwareTextEdit._would_intercept_focused_editor_wheel(editor, event)
            if decision is False:
                return False
        lock = ScrollAwareTextEdit._wheel_gesture_lock
        if lock is None:
            return False
        redirect = ScrollAwareTextEdit._wheel_gesture_in_progress or _is_scroll_bar_widget(obj)
        if redirect and ScrollAwareTextEdit._should_redirect_wheel_to_lock(obj, lock, event):
            ScrollAwareTextEdit._dispatch_wheel_to_lock(lock, event)
            return True
        return False


def _install_scroll_aware_wheel_app_filter() -> None:
    app = QApplication.instance()
    if app is None or getattr(app, "_scroll_aware_wheel_filter_installed", False):
        return
    app.installEventFilter(_ScrollAwareWheelAppFilter(app))
    app._scroll_aware_wheel_filter_installed = True


class _ScrollAwareViewportWheelForwarder(QObject):
    """Ensure viewport wheel events reach ScrollAwareTextEdit.wheelEvent."""

    def __init__(self, editor: ScrollAwareTextEdit) -> None:
        super().__init__(editor)
        self._editor = editor

    def eventFilter(self, obj, event) -> bool:
        if event.type() != _WHEEL_EVENT_TYPE:
            return False
        self._editor.wheelEvent(event)
        return True


class _ScrollAwareTextEditWheelFilter(QObject):
    """Redirect wheel events on scroll bars during cross-widget gesture locks."""

    def __init__(self, editor: ScrollAwareTextEdit) -> None:
        super().__init__(editor)
        self._editor = editor

    def eventFilter(self, obj, event) -> bool:
        if event.type() != _WHEEL_EVENT_TYPE or not _is_scroll_bar_widget(obj):
            return False
        lock = ScrollAwareTextEdit._wheel_gesture_lock
        if lock is not None and ScrollAwareTextEdit._should_redirect_wheel_to_lock(obj, lock, event):
            ScrollAwareTextEdit._dispatch_wheel_to_lock(lock, event)
            return True
        return False


class ScrollAwareTextEdit(QTextEdit):
    """Scroll page by default; scroll text content only after the field is clicked."""

    _wheel_gesture_lock: ScrollAwareTextEdit | QScrollArea | None = None
    _wheel_gesture_in_progress: bool = False
    _wheel_gesture_timer: QTimer | None = None
    _wheel_native_delivery_ids: set[int] = set()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._scroll_aware_window = self.window()
        self._register_in_window()
        self.destroyed.connect(self._unregister_from_window)
        self._ensure_wheel_gesture_timer()
        _install_scroll_aware_wheel_app_filter()
        self._wheel_filter = _ScrollAwareTextEditWheelFilter(self)
        viewport = self.viewport()
        if viewport is not None:
            self._viewport_wheel_forwarder = _ScrollAwareViewportWheelForwarder(self)
            viewport.installEventFilter(self._viewport_wheel_forwarder)
        for bar in (self.horizontalScrollBar(), self.verticalScrollBar()):
            if bar is not None:
                bar.installEventFilter(self._wheel_filter)

    @classmethod
    def _page_scroll_gesture_lock(cls) -> QScrollArea | None:
        lock = cls._wheel_gesture_lock
        if cls._wheel_gesture_in_progress and isinstance(lock, QScrollArea):
            return lock
        return None

    @classmethod
    def _native_wheel_event(cls, editor: ScrollAwareTextEdit, event) -> None:
        """Deliver wheel to the editor after the app filter consumed the original event."""
        event_id = id(event)
        if event_id in cls._wheel_native_delivery_ids:
            return
        cls._wheel_native_delivery_ids.add(event_id)
        _apply_native_wheel_scroll(editor, event)
        QTimer.singleShot(0, lambda eid=event_id: cls._wheel_native_delivery_ids.discard(eid))

    @classmethod
    def _should_forward_editor_wheel_to_page(cls, editor: ScrollAwareTextEdit, event) -> bool:
        delta_y, delta_x = _wheel_deltas(event)
        return (
            delta_x != 0
            and cls._has_horizontal_scroll(editor)
            and not cls._can_scroll_horizontally(editor, delta_x)
        )

    @classmethod
    def _should_swallow_vertical_editor_wheel(cls, editor: ScrollAwareTextEdit, event) -> bool:
        delta_y, delta_x = _wheel_deltas(event)
        return (
            delta_y != 0
            and delta_x == 0
            and cls._has_vertical_scroll(editor)
            and not cls._can_scroll_vertically(editor, delta_y)
        )

    @classmethod
    def _route_focused_editor_wheel(cls, editor: ScrollAwareTextEdit, event) -> bool | None:
        """Route wheel for a focused editor, or None when the editor is not focused."""
        if not editor.hasFocus():
            return None

        page_lock = cls._page_scroll_gesture_lock()
        if page_lock is not None:
            _scroll_area_by_wheel(page_lock, event)
            return True

        delta_y, delta_x = _wheel_deltas(event)

        if cls._should_forward_editor_wheel_to_page(editor, event):
            scroll = cls._find_enclosing_scroll_area(editor)
            if scroll is not None:
                _scroll_area_by_wheel(scroll, event)
            else:
                event.ignore()
            return True

        if cls._should_swallow_vertical_editor_wheel(editor, event):
            event.accept()
            return True

        if cls._editor_can_consume_wheel(editor, delta_y, delta_x):
            return False

        scroll = cls._find_enclosing_scroll_area(editor)
        lock = cls._wheel_gesture_lock
        if scroll is not None:
            _scroll_area_by_wheel(scroll, event)
        elif isinstance(lock, QScrollArea):
            _scroll_area_by_wheel(lock, event)
        else:
            event.ignore()
        return True

    @classmethod
    def _would_intercept_focused_editor_wheel(cls, editor: ScrollAwareTextEdit, event) -> bool | None:
        """Read-only focused-editor routing decision, or None when not focused."""
        if not editor.hasFocus():
            return None
        if cls._page_scroll_gesture_lock() is not None:
            return True
        delta_y, delta_x = _wheel_deltas(event)
        if cls._should_forward_editor_wheel_to_page(editor, event):
            return True
        if cls._should_swallow_vertical_editor_wheel(editor, event):
            return True
        if cls._editor_can_consume_wheel(editor, delta_y, delta_x):
            return False
        return True

    @classmethod
    def _would_intercept_wheel(cls, editor: ScrollAwareTextEdit, event) -> bool:
        """Read-only routing decision (for debug logging)."""
        focused = cls._would_intercept_focused_editor_wheel(editor, event)
        if focused is not None:
            return focused

        lock = cls._wheel_gesture_lock
        if cls._wheel_gesture_in_progress and isinstance(lock, QScrollArea):
            return True
        return not editor.hasFocus()

    @classmethod
    def _route_wheel_event(cls, editor: ScrollAwareTextEdit, event) -> bool:
        focused = cls._route_focused_editor_wheel(editor, event)
        if focused is not None:
            return focused

        lock = cls._wheel_gesture_lock
        if cls._wheel_gesture_in_progress and isinstance(lock, QScrollArea):
            scroll = cls._find_enclosing_scroll_area(editor)
            if scroll is not None:
                _scroll_area_by_wheel(scroll, event)
            else:
                _scroll_area_by_wheel(lock, event)
            return True

        scroll = cls._find_enclosing_scroll_area(editor)
        if scroll is not None:
            _scroll_area_by_wheel(scroll, event)
        else:
            event.ignore()
        return True

    def wheelEvent(self, event) -> None:
        if type(self)._route_wheel_event(self, event):
            return
        _apply_native_wheel_scroll(self, event)

    def _register_in_window(self) -> None:
        window = self._scroll_aware_window
        if window is None:
            return
        _SCROLL_AWARE_WINDOW_COUNTS[window] = _SCROLL_AWARE_WINDOW_COUNTS.get(window, 0) + 1
        editors = _SCROLL_AWARE_EDITORS_BY_WINDOW.get(window)
        if editors is None:
            editors = set()
            _SCROLL_AWARE_EDITORS_BY_WINDOW[window] = editors
        editors.add(self)

    def _unregister_from_window(self, *_args) -> None:
        window = self._scroll_aware_window
        if window is None:
            return
        count = _SCROLL_AWARE_WINDOW_COUNTS.get(window, 0) - 1
        if count <= 0:
            _SCROLL_AWARE_WINDOW_COUNTS.pop(window, None)
            _SCROLL_AWARE_EDITORS_BY_WINDOW.pop(window, None)
        else:
            _SCROLL_AWARE_WINDOW_COUNTS[window] = count
        editors = _SCROLL_AWARE_EDITORS_BY_WINDOW.get(window)
        if editors is not None:
            editors.discard(self)

    @classmethod
    def _window_uses_scroll_aware_wheel(cls, window: QWidget) -> bool:
        return _SCROLL_AWARE_WINDOW_COUNTS.get(window, 0) > 0

    @classmethod
    def _widget_is_within_lock_target(
        cls,
        widget: QWidget,
        lock: ScrollAwareTextEdit | QScrollArea,
    ) -> bool:
        current: QWidget | None = widget
        while current is not None:
            if current is lock:
                return True
            current = current.parentWidget()
        return False

    @classmethod
    def _scroll_bar_owner(cls, widget: QWidget) -> ScrollAwareTextEdit | QScrollArea | None:
        current: QWidget | None = widget
        while current is not None:
            if isinstance(current, QScrollBar):
                parent = current.parentWidget()
                if isinstance(parent, ScrollAwareTextEdit):
                    return parent
                if isinstance(parent, QScrollArea):
                    return parent
                return None
            current = current.parentWidget()
        return None

    @classmethod
    def _should_redirect_wheel_to_lock(
        cls,
        widget: QWidget,
        lock: ScrollAwareTextEdit | QScrollArea,
        event,
    ) -> bool:
        if _is_scroll_bar_widget(widget):
            return cls._scroll_bar_owner(widget) is not lock
        editor = cls._find_scroll_aware_editor(widget)
        if isinstance(lock, QScrollArea) and editor is not None:
            if cls._wheel_gesture_in_progress:
                return True
            if editor.hasFocus():
                delta_y, delta_x = _wheel_deltas(event)
                if cls._editor_can_consume_wheel(editor, delta_y, delta_x):
                    return False
            return True
        return not cls._widget_is_within_lock_target(widget, lock)

    @classmethod
    def _dispatch_wheel_to_lock(cls, lock: ScrollAwareTextEdit | QScrollArea, event) -> None:
        if isinstance(lock, ScrollAwareTextEdit):
            if type(lock)._route_wheel_event(lock, event):
                return
            cls._native_wheel_event(lock, event)
        else:
            _scroll_area_by_wheel(lock, event)

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
        cls._wheel_gesture_in_progress = False

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
    def _has_vertical_scroll(cls, editor: ScrollAwareTextEdit) -> bool:
        bar = editor.verticalScrollBar()
        return bar.maximum() > bar.minimum()

    @classmethod
    def _has_horizontal_scroll(cls, editor: ScrollAwareTextEdit) -> bool:
        bar = editor.horizontalScrollBar()
        return bar.maximum() > bar.minimum()

    @classmethod
    def _can_scroll_vertically(cls, editor: ScrollAwareTextEdit, delta: int) -> bool:
        if not cls._has_vertical_scroll(editor):
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
    def _can_scroll_horizontally(cls, editor: ScrollAwareTextEdit, delta: int) -> bool:
        if not cls._has_horizontal_scroll(editor):
            return False
        if delta == 0:
            return True
        bar = editor.horizontalScrollBar()
        at_left = bar.value() <= bar.minimum()
        at_right = bar.value() >= bar.maximum()
        if delta > 0 and at_left:
            return False
        if delta < 0 and at_right:
            return False
        return True

    @classmethod
    def _can_scroll_internally_in_direction(cls, editor: ScrollAwareTextEdit, delta: int) -> bool:
        return cls._can_scroll_vertically(editor, delta)

    @classmethod
    def _editor_can_consume_wheel(cls, editor: ScrollAwareTextEdit, delta_y: int, delta_x: int) -> bool:
        if delta_x != 0 and cls._can_scroll_horizontally(editor, delta_x):
            return True
        if delta_y != 0 and cls._can_scroll_vertically(editor, delta_y):
            return True
        if delta_y == 0 and delta_x == 0:
            return cls._has_vertical_scroll(editor) or cls._has_horizontal_scroll(editor)
        return False

    @classmethod
    def _point_over_editor(
        cls,
        editor: ScrollAwareTextEdit,
        global_pos,
        widget: QWidget | None,
    ) -> bool:
        if cls._contains_global_point(editor, global_pos):
            return True
        return widget is not None and cls._find_scroll_aware_editor(widget) is editor

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
            and cls._point_over_editor(editor, global_pos, widget)
        ):
            delta_y, delta_x = _wheel_deltas(event)
            if cls._editor_can_consume_wheel(editor, delta_y, delta_x):
                return editor
            return cls._find_enclosing_scroll_area(editor)
        return cls._find_enclosing_scroll_area(widget)

    @classmethod
    def _update_wheel_gesture_lock(cls, event) -> None:
        phase = event.phase()
        timer = cls._ensure_wheel_gesture_timer()
        if phase == Qt.ScrollPhase.ScrollBegin:
            cls._wheel_gesture_lock = cls._resolve_wheel_gesture_lock(
                _event_global_pos(event),
                event,
            )
            cls._wheel_gesture_in_progress = True
            timer.stop()
            return
        if phase == Qt.ScrollPhase.ScrollEnd:
            cls._clear_wheel_gesture_lock()
            timer.stop()
            return
        if cls._wheel_gesture_in_progress:
            if not isinstance(cls._wheel_gesture_lock, QScrollArea):
                widget = cls._widget_under_global_pos(_event_global_pos(event))
                editor = cls._find_scroll_aware_editor(widget)
                if editor is not None and editor.hasFocus():
                    delta_y, delta_x = _wheel_deltas(event)
                    if cls._editor_can_consume_wheel(editor, delta_y, delta_x):
                        cls._wheel_gesture_lock = editor
            timer.stop()
            timer.start()
            return
        if cls._wheel_gesture_lock is None:
            cls._wheel_gesture_lock = cls._resolve_wheel_gesture_lock(
                _event_global_pos(event),
                event,
            )
            cls._wheel_gesture_in_progress = True
        timer.stop()
        timer.start()

    def clear_text_selection(self) -> None:
        if not _qt_widget_alive(self):
            return
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
        editors = _SCROLL_AWARE_EDITORS_BY_WINDOW.get(host)
        if not editors:
            return
        stale: list[ScrollAwareTextEdit] = []
        for editor in list(editors):
            if editor is self:
                continue
            if not _qt_widget_alive(editor):
                stale.append(editor)
                continue
            editor.clear_text_selection()
        for editor in stale:
            editors.discard(editor)

    def is_internally_scrollable(self) -> bool:
        return self._has_vertical_scroll(self) or self._has_horizontal_scroll(self)

    def _forward_wheel_to_enclosing_scroll(self, event) -> None:
        scroll = self._find_enclosing_scroll_area(self)
        if scroll is not None:
            _scroll_area_by_wheel(scroll, event)
        else:
            event.ignore()


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
