"""Native Qt control factories — single entry point for addon UI widgets."""

from __future__ import annotations

from typing import TypeVar

from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QObject,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QTextOption,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
    QEvent,
)

from .theme import (
    ICON_BUTTON_SIZE,
    apply_native_text_edit_surface_theme,
    muted_hint_html,
    panel_content_html,
    panel_widget_stylesheet,
)
from ..config import load_config
from .widgets import (
    PlainNoWheelComboBox,
    PlainNoWheelDoubleSpinBox,
    PlainNoWheelSpinBox,
    ScrollAwareTextEdit,
    _settings_form_available_width,
    bind_text_edit_auto_height,
)

_TEditor = TypeVar("_TEditor", bound=QTextEdit)

SETTINGS_TEXT_EDIT_MIN_HEIGHT = 44
SETTINGS_TEXT_EDIT_MIN_WIDTH = 160
SETTINGS_SECTION_INNER_SPACING = 4
SETTINGS_SECTION_GAP = 8
SETTINGS_CONTROL_MIN_WIDTH = 72
SETTINGS_CONTROL_HORIZONTAL_PADDING = 28
SETTINGS_LINE_EDIT_HORIZONTAL_PADDING = 52
SETTINGS_COMBO_HORIZONTAL_PADDING = 52
# Fallback before the parent layout has a width.
SETTINGS_TEXT_EDIT_FALLBACK_WIDTH = 520
_SETTINGS_PANEL_PADDING = 16
# Cap so Advanced (long prompts / wrapper) cannot build multi-thousand-pixel
# editors that freeze layout and break page scrolling.
SETTINGS_TEXT_EDIT_MAX_HEIGHT = 280


def create_settings_hint_label(parent: QWidget, text: str) -> QLabel:
    label = QLabel(parent)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setText(muted_hint_html(text))
    label.setWordWrap(True)
    label.setOpenExternalLinks(True)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
    label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    label.setContentsMargins(0, 0, 0, 0)
    return label


def create_settings_section_label(parent: QWidget, title: str) -> QLabel:
    label = QLabel(parent)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setText(f"<b>{title}</b>")
    label.setContentsMargins(0, 0, 0, 0)
    label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    return label


def apply_settings_icon_row_height(
    row: QWidget,
    *,
    allow_multiline: bool = False,
    top_inset: int = 0,
) -> None:
    """Reserve icon-button height for single-line rows; grow for wrapped labels."""
    row.setSizePolicy(
        QSizePolicy.Policy.Preferred,
        QSizePolicy.Policy.Minimum,
    )
    if allow_multiline:
        row.setMinimumHeight(0)
        return
    row.setMinimumHeight(ICON_BUTTON_SIZE + top_inset)


def create_settings_restore_list_label(parent: QWidget, text: str) -> QLabel:
    label = QLabel(parent)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setText(text)
    label.setWordWrap(False)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
    label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    label.setContentsMargins(0, 0, 0, 0)
    if "<img" in text:
        from .help_icons import INLINE_HELP_ICON_DISPLAY_SIZE

        label.setMinimumHeight(INLINE_HELP_ICON_DISPLAY_SIZE + 2)
    return label


def create_settings_help_list_label(parent: QWidget, text: str) -> QLabel:
    label = QLabel(parent)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setText(text)
    label.setWordWrap(True)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
    label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    label.setContentsMargins(0, 0, 0, 0)
    bind_settings_rich_label_auto_height(label)
    return label


def _settings_rich_label_content_width(label: QLabel) -> int:
    width = label.width()
    if width > 1:
        return width

    row = label.parentWidget()
    if row is not None and row.width() > 0:
        layout = row.layout()
        horizontal_margins = 0
        if layout is not None:
            margins = layout.contentsMargins()
            horizontal_margins = margins.left() + margins.right()
        return max(row.width() - horizontal_margins - ICON_BUTTON_SIZE - 12, 120)

    widget = row
    while widget is not None:
        if widget.width() > 0:
            return max(widget.width() - 64, 120)
        widget = widget.parentWidget()
    return 480


def _settings_rich_label_minimum_height(label: QLabel, *, content_width: int) -> int:
    label.setWordWrap(True)
    height = label.heightForWidth(max(content_width, 1))
    if height <= 0:
        height = label.sizeHint().height()
    min_height = label.fontMetrics().height()
    if "<img" in (label.text() or ""):
        from .help_icons import INLINE_HELP_ICON_DISPLAY_SIZE

        min_height = max(min_height, INLINE_HELP_ICON_DISPLAY_SIZE + 2)
    return max(height, min_height)


def sync_settings_rich_label_height(label: QLabel) -> None:
    if label.textFormat() != Qt.TextFormat.RichText:
        return
    content_width = _settings_rich_label_content_width(label)
    height = _settings_rich_label_minimum_height(label, content_width=content_width)
    if height <= 0:
        return
    label.setMinimumHeight(height)
    row = label.parentWidget()
    if row is None:
        return
    layout = row.layout()
    if layout is None:
        return
    margins = layout.contentsMargins()
    row.setMinimumHeight(height + margins.top() + margins.bottom())


def bind_settings_rich_label_auto_height(label: QLabel) -> None:
    if getattr(label, "_settings_rich_height_filter", None) is not None:
        sync_settings_rich_label_height(label)
        return

    class _RichLabelHeightFilter(QObject):
        def eventFilter(self, obj, event) -> bool:
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.ShowToParent):
                sync_settings_rich_label_height(obj)
            return False

    filt = _RichLabelHeightFilter(label)
    label.installEventFilter(filt)
    label._settings_rich_height_filter = filt
    QTimer.singleShot(0, lambda: sync_settings_rich_label_height(label))


def refresh_settings_rich_label_heights(root: QWidget) -> None:
    for label in root.findChildren(QLabel):
        if getattr(label, "_settings_rich_height_filter", None) is not None:
            sync_settings_rich_label_height(label)


def create_settings_restore_checkbox_row(
    parent: QWidget,
    checkbox: QCheckBox,
    label_key: str,
    *,
    config: dict,
) -> QWidget:
    from ..i18n import tr

    from .help_icons import instruction_html

    row_widget = QWidget(parent)
    apply_settings_icon_row_height(row_widget)
    row_layout = QHBoxLayout(row_widget)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(6)
    row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    checkbox.setText("")
    checkbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    label = create_settings_restore_list_label(
        row_widget,
        instruction_html(tr(label_key, config=config)),
    )
    row_layout.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignVCenter)
    row_layout.addWidget(label, 1)
    return row_widget


def create_settings_checkbox_info_row(
    parent: QWidget,
    checkbox: QCheckBox,
    info_button: QPushButton,
) -> QWidget:
    row_widget = QWidget(parent)
    apply_settings_icon_row_height(row_widget)
    row_layout = QHBoxLayout(row_widget)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(SETTINGS_SECTION_INNER_SPACING)
    checkbox.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    info_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    row_layout.addWidget(checkbox, 0, align)
    row_layout.addWidget(info_button, 0, align)
    row_layout.addStretch(1)
    return row_widget


def add_settings_labeled_field(
    layout: QVBoxLayout,
    parent: QWidget,
    label: str,
    shell: QWidget,
) -> None:
    layout.addWidget(QLabel(label, parent))
    layout.addWidget(shell)


def _effective_layout_spacing(layout: QVBoxLayout) -> int:
    spacing = layout.spacing()
    if spacing >= 0:
        return spacing
    return SETTINGS_SECTION_INNER_SPACING


def add_settings_section_break(layout: QVBoxLayout) -> None:
    """Extra space between settings sections (avoids stacking on layout spacing)."""
    spacing = _effective_layout_spacing(layout)
    extra = SETTINGS_SECTION_GAP - 2 * spacing
    if extra > 0:
        layout.addSpacing(extra)


def add_settings_stacked_field(
    layout: QVBoxLayout,
    parent: QWidget,
    label: str,
    shell: QWidget,
    *,
    spacing: int = SETTINGS_SECTION_INNER_SPACING,
) -> None:
    group = QWidget(parent)
    group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    group_layout = QVBoxLayout(group)
    group_layout.setContentsMargins(0, 0, 0, 0)
    group_layout.setSpacing(spacing)
    label_widget = QLabel(label, group)
    label_widget.setContentsMargins(0, 0, 0, 0)
    group_layout.addWidget(label_widget)
    group_layout.addWidget(shell)
    layout.addWidget(group)


def apply_settings_text_edit_newlines(
    editor: QTextEdit | QPlainTextEdit,
    *,
    show: bool,
) -> None:
    option = editor.document().defaultTextOption()
    flags = option.flags()
    marker = QTextOption.Flag.ShowLineAndParagraphSeparators
    if show:
        flags |= marker
    else:
        flags &= ~marker
    option.setFlags(flags)
    editor.document().setDefaultTextOption(option)
    viewport = editor.viewport()
    if viewport is not None:
        viewport.update()


def apply_text_edit_wrap(
    editor: QTextEdit | QPlainTextEdit,
    *,
    wrap: bool,
) -> None:
    if isinstance(editor, QPlainTextEdit):
        editor.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if wrap
            else QPlainTextEdit.LineWrapMode.NoWrap
        )
    else:
        editor.setLineWrapMode(
            QTextEdit.LineWrapMode.WidgetWidth
            if wrap
            else QTextEdit.LineWrapMode.NoWrap
        )
    if wrap:
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # AsNeeded vertical bars shrink the viewport when they appear, which
        # reflows WidgetWidth wrap and can freeze/crash (stack overflow) even
        # on fixed-height editors. Keep the bar reserved while wrapping.
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    else:
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # No wrap-reflow from viewport width; AsNeeded is safe. Auto-height
        # binders may still override this on their next adjust pass.
        if getattr(editor, "_auto_height_adjust", None) is None:
            editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    adjust = getattr(editor, "_auto_height_adjust", None)
    if adjust is not None:
        adjust()


def refresh_settings_text_edit_newlines(root: QWidget, show: bool) -> None:
    for editor in root.findChildren(QTextEdit):
        apply_settings_text_edit_newlines(editor, show=show)
    for editor in root.findChildren(QPlainTextEdit):
        apply_settings_text_edit_newlines(editor, show=show)


def refresh_text_edit_wrap(root: QWidget, wrap: bool) -> None:
    for editor in root.findChildren(QTextEdit):
        if getattr(editor, "_addon_text_edit", False) or getattr(
            editor, "_settings_text_edit", False
        ):
            apply_text_edit_wrap(editor, wrap=wrap)
    for editor in root.findChildren(QPlainTextEdit):
        if getattr(editor, "_addon_text_edit", False) or getattr(
            editor, "_settings_text_edit", False
        ):
            apply_text_edit_wrap(editor, wrap=wrap)


def configure_addon_text_edit(
    editor: QTextEdit,
    *,
    show_newlines: bool | None = None,
    wrap: bool | None = None,
    auto_height: bool = True,
    minimum: int = SETTINGS_TEXT_EDIT_MIN_HEIGHT,
    maximum: int | None = SETTINGS_TEXT_EDIT_MAX_HEIGHT,
    scroll_free: bool = False,
) -> None:
    editor._addon_text_edit = True
    editor.document().setDocumentMargin(0)
    if show_newlines is None or wrap is None:
        config = load_config()
        if show_newlines is None:
            show_newlines = bool(config.get("settings_show_text_newlines", False))
        if wrap is None:
            wrap = bool(config.get("settings_wrap_text_editors", True))
    apply_settings_text_edit_newlines(editor, show=show_newlines)
    apply_text_edit_wrap(editor, wrap=wrap)
    # scroll_free used to force maximum=None (uncapped growth inside page scroll
    # areas). That caused scrollbar ↔ wrap-width ↔ height crash loops. Keep the
    # height cap; long content scrolls inside the editor instead.
    _ = scroll_free
    if auto_height:
        bind_text_edit_auto_height(editor, minimum=minimum, maximum=maximum)


def create_prompt_scroll_page(parent: QWidget) -> tuple[QWidget, QVBoxLayout, QWidget]:
    from aqt.qt import QFrame, QScrollArea

    scroll = QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    host = QWidget(scroll)
    host_layout = QVBoxLayout(host)
    host_layout.setContentsMargins(0, 0, 0, 0)
    host_layout.setSpacing(6)
    scroll.setWidget(host)
    return scroll, host_layout, host


def scroll_area_to_widget(scroll: QWidget, widget: QWidget) -> None:
    from aqt.qt import QScrollArea, QPoint

    if not isinstance(scroll, QScrollArea):
        return
    host = scroll.widget()
    if host is None:
        return
    top = widget.mapTo(host, QPoint(0, 0)).y()
    scroll.verticalScrollBar().setValue(max(0, top))


def configure_settings_text_edit(
    editor: QTextEdit,
    *,
    minimum: int = SETTINGS_TEXT_EDIT_MIN_HEIGHT,
    maximum: int | None = SETTINGS_TEXT_EDIT_MAX_HEIGHT,
    show_newlines: bool = False,
    wrap: bool | None = None,
) -> None:
    editor._settings_text_edit = True
    editor.document().setDocumentMargin(0)
    editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    apply_settings_text_edit_newlines(editor, show=show_newlines)
    if wrap is None:
        wrap = bool(load_config().get("settings_wrap_text_editors", True))
    apply_text_edit_wrap(editor, wrap=wrap)
    bind_text_edit_auto_height(editor, minimum=minimum, maximum=maximum)


def adjust_settings_panel_shell(shell: QWidget) -> None:
    if not getattr(shell, "_settings_panel", False):
        return
    label = getattr(shell, "_settings_panel_label", None)
    if label is None:
        return
    available = _settings_form_available_width(shell)
    was_wrapped = label.wordWrap()
    label.setWordWrap(False)
    ideal = label.sizeHint().width() + _SETTINGS_PANEL_PADDING
    label.setWordWrap(was_wrapped)
    width = min(max(ideal, SETTINGS_TEXT_EDIT_MIN_WIDTH), available)
    inner = max(width - _SETTINGS_PANEL_PADDING, 1)
    height = label.heightForWidth(inner) + _SETTINGS_PANEL_PADDING
    if height <= _SETTINGS_PANEL_PADDING:
        height = label.sizeHint().height() + _SETTINGS_PANEL_PADDING
    if shell.width() == width and shell.height() == height:
        return
    shell.setFixedSize(width, height)


def create_settings_panel(parent: QWidget, html: str) -> QWidget:
    shell = QWidget(parent)
    shell._settings_panel = True
    shell.setObjectName("settingsPanelShell")
    shell.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    layout = QVBoxLayout(shell)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    label = QLabel(shell)
    label.setObjectName("settingsPanelContent")
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setWordWrap(True)
    label.setText(html)
    shell.setStyleSheet(panel_widget_stylesheet())
    layout.addWidget(label)
    shell._settings_panel_label = label
    return shell


def _ideal_compact_control_width(control: QWidget) -> int:
    if isinstance(control, QLineEdit):
        text = control.text() or control.placeholderText()
        if not text:
            return max(control.sizeHint().width(), SETTINGS_CONTROL_MIN_WIDTH)
        text_width = control.fontMetrics().horizontalAdvance(text)
        return max(
            text_width + SETTINGS_LINE_EDIT_HORIZONTAL_PADDING,
            control.sizeHint().width(),
        )
    if isinstance(control, QSpinBox):
        text = control.text() or str(control.value())
        return max(
            control.fontMetrics().horizontalAdvance(text) + SETTINGS_CONTROL_HORIZONTAL_PADDING + 24,
            control.sizeHint().width(),
        )
    if isinstance(control, QDoubleSpinBox):
        text = control.text() or f"{control.value():.{control.decimals()}f}"
        return max(
            control.fontMetrics().horizontalAdvance(text) + SETTINGS_CONTROL_HORIZONTAL_PADDING + 24,
            control.sizeHint().width(),
        )
    if isinstance(control, QComboBox):
        fm = control.fontMetrics()
        max_text_width = 0
        for index in range(control.count()):
            item_text = control.itemText(index)
            max_text_width = max(max_text_width, fm.horizontalAdvance(item_text or ""))
        text = control.currentText()
        line_edit = control.lineEdit()
        if line_edit is not None and line_edit.text():
            text = line_edit.text()
        if not text:
            text = control.itemText(control.currentIndex())
        width = max(
            max_text_width,
            fm.horizontalAdvance(text or ""),
        ) + SETTINGS_COMBO_HORIZONTAL_PADDING
        return max(width, control.minimumSizeHint().width() + 16, control.sizeHint().width())
    return control.sizeHint().width()


def adjust_settings_compact_control_shell(shell: QWidget) -> None:
    control = getattr(shell, "_settings_compact_control", None)
    if control is None:
        return
    available = _settings_form_available_width(shell)
    ideal = _ideal_compact_control_width(control)
    width = min(max(ideal, SETTINGS_CONTROL_MIN_WIDTH), available)
    if shell.width() != width:
        shell.setFixedWidth(width)
        control.setFixedWidth(width)


def _wrap_settings_compact_control(parent: QWidget, control: QWidget) -> tuple[QWidget, QWidget]:
    shell = QWidget(parent)
    shell.setObjectName("settingsControlShell")
    shell._settings_compact_control = control
    shell.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    layout = QVBoxLayout(shell)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    control.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    control._settings_control_shell = shell
    layout.addWidget(control)
    _bind_settings_compact_control(control)
    return shell, control


def _bind_settings_compact_control(control: QWidget) -> None:
    shell = getattr(control, "_settings_control_shell", None)
    if shell is None:
        return

    def _schedule() -> None:
        from aqt.qt import QTimer

        QTimer.singleShot(0, lambda: adjust_settings_compact_control_shell(shell))

    if isinstance(control, QLineEdit):
        control.textChanged.connect(_schedule)
    elif isinstance(control, (QSpinBox, QDoubleSpinBox)):
        control.valueChanged.connect(_schedule)
    elif isinstance(control, QComboBox):
        control.currentTextChanged.connect(_schedule)
        line_edit = control.lineEdit()
        if line_edit is not None:
            line_edit.textChanged.connect(_schedule)


def refresh_settings_text_edit_layouts(root: QWidget) -> None:
    from aqt.qt import QTimer

    if getattr(root, "_settings_layout_refresh_pending", False):
        return
    root._settings_layout_refresh_pending = True

    def _run() -> None:
        root._settings_layout_refresh_pending = False
        for editor in root.findChildren(QTextEdit):
            if not editor.isVisible():
                continue
            adjust = getattr(editor, "_auto_height_adjust", None)
            if adjust is not None:
                adjust()
        for shell in root.findChildren(QWidget):
            if not shell.isVisible():
                continue
            if getattr(shell, "_settings_panel", False):
                adjust_settings_panel_shell(shell)
            elif getattr(shell, "_settings_compact_control", None) is not None:
                adjust_settings_compact_control_shell(shell)

    QTimer.singleShot(0, _run)


def create_ui_line_edit(parent: QWidget) -> tuple[QWidget, QLineEdit]:
    return _wrap_settings_compact_control(parent, QLineEdit())


def create_ui_text_edit(
    parent: QWidget,
    *,
    editor_class: type[_TEditor] = ScrollAwareTextEdit,
    show_newlines: bool | None = None,
    wrap: bool | None = None,
    auto_height: bool = False,
    minimum: int = SETTINGS_TEXT_EDIT_MIN_HEIGHT,
    maximum: int | None = SETTINGS_TEXT_EDIT_MAX_HEIGHT,
    scroll_free: bool = False,
) -> tuple[QWidget, _TEditor]:
    editor = editor_class(parent)
    apply_native_text_edit_surface_theme(editor)
    configure_addon_text_edit(
        editor,
        show_newlines=show_newlines,
        wrap=wrap,
        auto_height=auto_height,
        minimum=minimum,
        maximum=maximum,
        scroll_free=scroll_free,
    )
    return editor, editor


def create_settings_line_edit(parent: QWidget) -> tuple[QWidget, QLineEdit]:
    return create_ui_line_edit(parent)


def create_settings_text_edit(
    parent: QWidget,
    *,
    editor_class: type[_TEditor] = ScrollAwareTextEdit,
) -> tuple[QWidget, _TEditor]:
    return create_ui_text_edit(parent, editor_class=editor_class)


def create_settings_auto_height_text_edit(
    parent: QWidget,
    *,
    editor_class: type[_TEditor] = ScrollAwareTextEdit,
    minimum: int = SETTINGS_TEXT_EDIT_MIN_HEIGHT,
    maximum: int | None = SETTINGS_TEXT_EDIT_MAX_HEIGHT,
    show_newlines: bool = False,
    wrap: bool | None = None,
) -> tuple[QWidget, _TEditor]:
    shell = QWidget(parent)
    shell.setObjectName("settingsTextEditShell")
    shell.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    shell_layout = QVBoxLayout(shell)
    shell_layout.setContentsMargins(0, 0, 0, 0)
    shell_layout.setSpacing(0)

    editor = editor_class(shell)
    editor._settings_shell = shell
    apply_native_text_edit_surface_theme(editor)
    configure_settings_text_edit(
        editor,
        minimum=minimum,
        maximum=maximum,
        show_newlines=show_newlines,
        wrap=wrap,
    )
    shell_layout.addWidget(editor)
    return shell, editor


def create_settings_row_auto_height_text_edit(
    parent: QWidget,
    *,
    editor_class: type[_TEditor] = ScrollAwareTextEdit,
    minimum: int = SETTINGS_TEXT_EDIT_MIN_HEIGHT,
    maximum: int | None = SETTINGS_TEXT_EDIT_MAX_HEIGHT,
    show_newlines: bool = False,
    wrap: bool | None = None,
) -> tuple[QWidget, _TEditor]:
    """Auto-height settings field sized by its row column, not the full form width."""
    shell = QWidget(parent)
    shell.setObjectName("settingsTextEditShell")
    shell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    shell_layout = QVBoxLayout(shell)
    shell_layout.setContentsMargins(0, 0, 0, 0)
    shell_layout.setSpacing(0)
    shell_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    editor = editor_class(shell)
    editor._settings_shell = shell
    editor._settings_row_field = True
    apply_native_text_edit_surface_theme(editor)
    configure_settings_text_edit(
        editor,
        minimum=minimum,
        maximum=maximum,
        show_newlines=show_newlines,
        wrap=wrap,
    )
    shell_layout.addWidget(editor)
    return shell, editor


def create_settings_spinbox(parent: QWidget) -> tuple[QWidget, QSpinBox]:
    return _wrap_settings_compact_control(parent, PlainNoWheelSpinBox())


def create_settings_double_spinbox(parent: QWidget) -> tuple[QWidget, QDoubleSpinBox]:
    return _wrap_settings_compact_control(parent, PlainNoWheelDoubleSpinBox())


def create_settings_combo(parent: QWidget) -> tuple[QWidget, QComboBox]:
    return _wrap_settings_compact_control(parent, PlainNoWheelComboBox())


def create_settings_model_selector_shell(parent: QWidget) -> tuple[QWidget, QComboBox]:
    return _wrap_settings_compact_control(parent, PlainNoWheelComboBox())
