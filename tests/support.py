"""Shared helpers for addon tests (offline and optional live API)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

ADDON_DIR = Path(__file__).resolve().parent.parent
PACKAGE = "Anki_AI_Addon"


def _install_requests_mocks() -> None:
    if "requests" in sys.modules and hasattr(sys.modules["requests"], "exceptions"):
        return

    requests_mod = sys.modules.get("requests")
    if requests_mod is None:
        requests_mod = types.ModuleType("requests")
        requests_mod.post = MagicMock()
        requests_mod.get = MagicMock(return_value=MagicMock(
            ok=True,
            status_code=200,
            text="",
            json=MagicMock(return_value={"cachedContents": []}),
        ))
        requests_mod.delete = MagicMock(return_value=MagicMock(ok=True, status_code=200, text=""))
        requests_mod.Timeout = type("Timeout", (Exception,), {})
        requests_mod.ConnectionError = type("ConnectionError", (Exception,), {})
        requests_mod.RequestException = type("RequestException", (Exception,), {})
        sys.modules["requests"] = requests_mod

    requests_exceptions = types.ModuleType("requests.exceptions")
    requests_exceptions.ChunkedEncodingError = type("ChunkedEncodingError", (Exception,), {})
    requests_exceptions.ConnectionError = type("ConnectionError", (Exception,), {})
    requests_exceptions.Timeout = requests_mod.Timeout
    requests_exceptions.RequestException = requests_mod.RequestException
    requests_mod.exceptions = requests_exceptions
    sys.modules["requests.exceptions"] = requests_exceptions


def _install_anki_mocks() -> None:
    _install_requests_mocks()

    if "aqt" in sys.modules:
        return

    aqt = types.ModuleType("aqt")
    aqt.mw = MagicMock()
    aqt.mw.addonManager.getConfig.return_value = None
    aqt.mw.addonManager.writeConfig = MagicMock()
    aqt.mw.taskman = MagicMock()
    aqt.mw.taskman.run_in_background = MagicMock(
        side_effect=lambda fn, cb: cb(MagicMock(result=fn))
    )
    aqt.mw.taskman.run_on_main = MagicMock(side_effect=lambda fn: fn())
    aqt.gui_hooks = MagicMock()

    aqt_qt = types.ModuleType("aqt.qt")

    class _Enum:
        def __init__(self, **members):
            for key, value in members.items():
                setattr(self, key, value)

    class Qt:
        WindowType = _Enum(
            Window=1,
            WindowMinimizeButtonHint=2,
            WindowMaximizeButtonHint=4,
            WindowCloseButtonHint=8,
        )
        WidgetAttribute = _Enum(
            WA_QuitOnClose=1,
            WA_StyledBackground=2,
            WA_DeleteOnClose=3,
            WA_AlwaysShowToolTips=4,
            WA_Hover=5,
            WA_TranslucentBackground=6,
        )
        WindowModality = _Enum(NonModal=0)
        ScrollBarPolicy = _Enum(
            ScrollBarAlwaysOff=0,
            ScrollBarAsNeeded=1,
            ScrollBarAlwaysOn=2,
        )
        FocusPolicy = _Enum(StrongFocus=1)
        FocusReason = _Enum(OtherFocusReason=1)
        Key = _Enum(Key_Return=16777220, Key_Enter=16777221)
        KeyboardModifier = _Enum(ShiftModifier=1)
        MatchFlag = _Enum(MatchContains=1)
        CaseSensitivity = _Enum(CaseInsensitive=0)
        TextFormat = _Enum(RichText=1)
        AspectRatioMode = _Enum(IgnoreAspectRatio=1)
        TransformationMode = _Enum(SmoothTransformation=1)

    class _DocumentStub:
        def setDocumentMargin(self, *args, **kwargs):
            return None

    class _ScrollBarStub:
        def setValue(self, *args, **kwargs):
            return None

        def maximum(self):
            return 0

    class _Signal:
        def connect(self, *args, **kwargs):
            return None

    _SIGNAL_NAMES = frozenset(
        {
            "clicked",
            "toggled",
            "finished",
            "timeout",
            "textChanged",
            "textEdited",
            "valueChanged",
            "currentTextChanged",
        }
    )

    class _Stub:
        EchoMode = _Enum(Password=1)
        DialogCode = _Enum(Rejected=0, Accepted=1)
        LineWrapMode = _Enum(NoWrap=0, WidgetWidth=1)
        MoveOperation = _Enum(End=0)
        MoveMode = _Enum(KeepAnchor=1)
        WrapMode = _Enum(WrapAtWordBoundaryOrAnywhere=1)

        def __init__(self, *args, **kwargs):
            pass

        @staticmethod
        def installEventFilter(*args, **kwargs):
            return None

        def setFocusPolicy(self, *args, **kwargs):
            return None

        def parentWidget(self):
            return None

        def eventFilter(self, obj, event):
            return False

        def accept(self):
            return None

        def setDefault(self, *args, **kwargs):
            return None

        def setIcon(self, *args, **kwargs):
            return None

        def setIconSize(self, *args, **kwargs):
            return None

        def setToolTip(self, *args, **kwargs):
            return None

        def setObjectName(self, *args, **kwargs):
            return None

        def objectName(self):
            return ""

        def __getattr__(self, name):
            if name.startswith("_"):
                raise AttributeError(name)
            if name in _SIGNAL_NAMES:
                signal = _Signal()
                setattr(self, name, signal)
                return signal

            def _noop(*args, **kwargs):
                return None

            return _noop

        def document(self):
            return _DocumentStub()

        def verticalScrollBar(self):
            return _ScrollBarStub()

        def fontMetrics(self):
            return QFontMetricsF()

        def sizeHint(self):
            return QSize()

        def findChildren(self, *args, **kwargs):
            return []

        def setLineWrapMode(self, *args, **kwargs):
            return None

        def setWordWrapMode(self, *args, **kwargs):
            return None

    class _TextEditStub(_Stub):
        LineWrapMode = _Enum(NoWrap=0, WidgetWidth=1)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._text = ""

        def toPlainText(self):
            return self._text

        def setPlainText(self, text):
            self._text = text

        def clear(self):
            self._text = ""

        def setReadOnly(self, *args, **kwargs):
            return None

    class _PlainTextEditStub(_TextEditStub):
        def appendPlainText(self, text):
            self._text += text

    class QIcon(_Stub):
        @staticmethod
        def fromTheme(*args, **kwargs):
            return QIcon()

    class QFileDialog(_Stub):
        @staticmethod
        def getOpenFileName(*args, **kwargs):
            return ("", "")

        @staticmethod
        def getSaveFileName(*args, **kwargs):
            return ("", "")

    class QInputDialog(_Stub):
        @staticmethod
        def getText(*args, **kwargs):
            return ("", False)

    class QTextOption(_Stub):
        Flag = _Enum(ShowLineAndParagraphSeparators=1)
        WrapMode = _Enum(WrapAtWordBoundaryOrAnywhere=1)

    class _CheckBoxStub(_Stub):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._checked = False

        def isChecked(self):
            return self._checked

        def setChecked(self, checked):
            self._checked = bool(checked)

    class _LineEditStub(_Stub):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._text = ""
            self.textEdited = _Signal()

        def text(self):
            return self._text

        def setText(self, text):
            self._text = text

        def clear(self):
            self._text = ""

        def setPlaceholderText(self, *args, **kwargs):
            return None

        def setEchoMode(self, *args, **kwargs):
            return None

        def hasFocus(self):
            return False

    class QMessageBox(_Stub):
        Icon = _Enum(Warning=1, Question=2)
        StandardButton = _Enum(Ok=1, Cancel=2, Yes=4, No=8)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._exec_result = QMessageBox.StandardButton.Ok
            self._dismiss_checkbox = _CheckBoxStub()
            self._buttons: dict[int, _Stub] = {}

        def setIcon(self, *args, **kwargs):
            return None

        def setWindowTitle(self, *args, **kwargs):
            return None

        def setText(self, *args, **kwargs):
            return None

        def setInformativeText(self, *args, **kwargs):
            return None

        def setStandardButtons(self, *args, **kwargs):
            return None

        def setDefaultButton(self, *args, **kwargs):
            return None

        def setCheckBox(self, checkbox):
            self._dismiss_checkbox = checkbox

        def button(self, role):
            if role not in self._buttons:
                self._buttons[role] = _Stub()
            return self._buttons[role]

        def exec(self):
            return self._exec_result

    class QSizePolicy(_Stub):
        Policy = _Enum(Minimum=1, Fixed=2, Preferred=3, Expanding=4)

    class QSize(_Stub):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self._w = 16
            self._h = 16

        def width(self):
            return self._w

        def height(self):
            return self._h

        def setWidth(self, w):
            self._w = w

        def setHeight(self, h):
            self._h = h

    class QPen(_Stub):
        def __init__(self, *args, **kwargs):
            super().__init__()

        def setColor(self, *args, **kwargs):
            return None

        def setWidthF(self, *args, **kwargs):
            return None

    class QStyle(_Stub):
        PM_ScrollBarExtent = 1
        PixelMetric = _Enum(PM_ScrollBarExtent=1)
        StandardPixmap = _Enum(SP_ArrowUp=1, SP_ArrowDown=2)

        def pixelMetric(self, metric):
            return 14

        def standardPixmap(self, pixmap):
            return QIcon()

    class _ApplicationStub(_Stub):
        @staticmethod
        def instance():
            return _ApplicationStub()

        def style(self):
            return QStyle()

        def primaryScreen(self):
            return _ScreenStub()

    class _ScreenStub(_Stub):
        def devicePixelRatio(self):
            return 1.0

    for name, cls in (
        ("QApplication", _ApplicationStub),
        ("QCheckBox", _CheckBoxStub),
        ("QCloseEvent", _Stub),
        ("QDialog", _Stub),
        ("QDoubleSpinBox", _Stub),
        ("QFrame", _Stub),
        ("QHBoxLayout", _Stub),
        ("QLabel", _Stub),
        ("QLineEdit", _LineEditStub),
        ("QObject", _Stub),
        ("QPlainTextEdit", _PlainTextEditStub),
        ("QPushButton", _Stub),
        ("QResizeEvent", _Stub),
        ("QScrollArea", _Stub),
        ("QScrollBar", _ScrollBarStub),
        ("QShowEvent", _Stub),
        ("QSize", QSize),
        ("QSpinBox", _Stub),
        ("QStackedWidget", _Stub),
        ("QTextBrowser", _Stub),
        ("QTextCursor", _Stub),
        ("QTextEdit", _TextEditStub),
        ("QToolButton", _Stub),
        ("QUrl", _Stub),
        ("QVBoxLayout", _Stub),
        ("QWidget", _Stub),
        ("QAction", _Stub),
        ("QPoint", _Stub),
    ):
        setattr(aqt_qt, name, cls)

    aqt_qt.QIcon = QIcon
    aqt_qt.QFileDialog = QFileDialog
    aqt_qt.QInputDialog = QInputDialog
    aqt_qt.QTextOption = QTextOption

    class QFont(_Stub):
        class StyleHint:
            Monospace = 1

        def __init__(self, *args, **kwargs):
            super().__init__()

        def setStyleHint(self, *args, **kwargs):
            return None

    class QFontMetricsF(_Stub):
        def __init__(self, *args, **kwargs):
            super().__init__()

        def horizontalAdvance(self, text):
            return len(str(text)) * 8

        def height(self):
            return 14

    class QPainter(_Stub):
        class RenderHint:
            Antialiasing = 1

        def __init__(self, *args, **kwargs):
            super().__init__()

        def setRenderHint(self, *args, **kwargs):
            return None

        def fillRect(self, *args, **kwargs):
            return None

        def drawPixmap(self, *args, **kwargs):
            return None

        def end(self):
            return None

    class QPixmap(_Stub):
        def __init__(self, *args, **kwargs):
            super().__init__()

        def fill(self, *args, **kwargs):
            return None

        def devicePixelRatio(self):
            return 1.0

        def setDevicePixelRatio(self, *args, **kwargs):
            return None

        def size(self):
            return QSize()

        def isNull(self):
            return False

        def width(self):
            return 16

        def height(self):
            return 16

        def toImage(self):
            return QImage()

    class QRectF(_Stub):
        def __init__(self, *args, **kwargs):
            super().__init__()

    class QTransform(_Stub):
        @staticmethod
        def fromScale(*args, **kwargs):
            return QTransform()

    class QHeaderView(_Stub):
        class ResizeMode:
            ResizeToContents = 0
            Stretch = 1

        def setSectionResizeMode(self, *args, **kwargs):
            return None

    class QTableWidget(_Stub):
        class EditTrigger:
            NoEditTriggers = 0

        class SelectionBehavior:
            SelectRows = 0

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._rows = 0

        def setHorizontalHeaderLabels(self, *args, **kwargs):
            return None

        def horizontalHeader(self):
            return QHeaderView()

        def verticalHeader(self):
            return QHeaderView()

        def setEditTriggers(self, *args, **kwargs):
            return None

        def setSelectionBehavior(self, *args, **kwargs):
            return None

        def setRowCount(self, count):
            self._rows = count

        def rowCount(self):
            return self._rows

        def setItem(self, *args, **kwargs):
            return None

    class QTableWidgetItem(_Stub):
        pass

    class QByteArray(_Stub):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self._data = b"stub"

        def data(self):
            return self._data

        def __bytes__(self):
            return self._data

    class QImage(_Stub):
        def save(self, buffer, fmt):
            return True

    class QIODevice(_Stub):
        class OpenModeFlag:
            WriteOnly = 1

    class QBuffer(QIODevice):
        def __init__(self, *args, **kwargs):
            super().__init__()

        def open(self, *args, **kwargs):
            return True

        def close(self):
            return None

        def data(self):
            return QByteArray()

    aqt_qt.QFont = QFont
    aqt_qt.QFontMetricsF = QFontMetricsF
    aqt_qt.QPainter = QPainter
    aqt_qt.QPixmap = QPixmap
    aqt_qt.QRectF = QRectF
    aqt_qt.QTransform = QTransform
    aqt_qt.QHeaderView = QHeaderView
    aqt_qt.QTableWidget = QTableWidget
    aqt_qt.QTableWidgetItem = QTableWidgetItem
    aqt_qt.QByteArray = QByteArray
    aqt_qt.QIODevice = QIODevice
    aqt_qt.QBuffer = QBuffer
    aqt_qt.QImage = QImage
    aqt_qt.QPen = QPen
    aqt_qt.QStyle = QStyle

    class _TimerStub(_Stub):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.timeout = _Signal()

        def setSingleShot(self, *args, **kwargs):
            return None

        def start(self, *args, **kwargs):
            return None

    aqt_qt.QTimer = _TimerStub
    aqt_qt.QMessageBox = QMessageBox
    aqt_qt.QSizePolicy = QSizePolicy

    class _Frame(_Stub):
        class Shape:
            NoFrame = 0

    class QColor(_Stub):
        def __init__(self, *args, **kwargs):
            super().__init__()

    class QPalette(_Stub):
        class ColorRole:
            Base = 1
            Window = 2
            Text = 3
            ButtonText = 4

        def setColor(self, *args, **kwargs):
            return None

        def color(self, *args, **kwargs):
            return QColor()

    class _PopupStub(_Stub):
        def setMaxVisibleItems(self, *args, **kwargs):
            return None

    class QCompleter(_Stub):
        CompletionMode = _Enum(PopupCompletion=0)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._model = None

        def setFilterMode(self, *args, **kwargs):
            return None

        def setCaseSensitivity(self, *args, **kwargs):
            return None

        def setCompletionMode(self, *args, **kwargs):
            return None

        def setMaxVisibleItems(self, *args, **kwargs):
            return None

        def popup(self):
            return _PopupStub()

        def setModel(self, model):
            self._model = model

    class QStringListModel(_Stub):
        def __init__(self, items=None):
            super().__init__()
            self.items = list(items or [])

    class QComboBox(_Stub):
        InsertPolicy = _Enum(NoInsert=0)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._items: list[str] = []
            self._text = ""
            self._completer = None
            self._properties: dict[str, object] = {}

        def setEditable(self, *args, **kwargs):
            return None

        def setInsertPolicy(self, *args, **kwargs):
            return None

        def setMaxVisibleItems(self, *args, **kwargs):
            return None

        def setProperty(self, key, value):
            self._properties[key] = value
            return True

        def property(self, key):
            return self._properties.get(key)

        def addItems(self, items):
            self._items = list(items)

        def clear(self):
            self._items = []

        def setCurrentText(self, text):
            self._text = text

        def currentText(self):
            return self._text

        def setEditText(self, text):
            self._text = text

        def lineEdit(self):
            return _LineEditStub()

        def setCompleter(self, completer):
            self._completer = completer

        def completer(self):
            return self._completer

        def showPopup(self):
            return None

        def blockSignals(self, blocked):
            return True

        def findData(self, data):
            return -1

        def setCurrentIndex(self, index):
            return None

        def currentData(self):
            return None

        def setStyle(self, *args, **kwargs):
            return None

    class QStyleFactory:
        @staticmethod
        def create(name):
            return _Stub()

    aqt_qt.QFrame = _Frame
    aqt_qt.QColor = QColor
    aqt_qt.QPalette = QPalette
    aqt_qt.QComboBox = QComboBox
    aqt_qt.QStyleFactory = QStyleFactory
    aqt_qt.QCompleter = QCompleter
    aqt_qt.QStringListModel = QStringListModel
    aqt_qt.Qt = Qt

    class QBrush(_Stub):
        pass

    class QEvent(_Stub):
        class Type:
            Wheel = 31
            Close = 19
            ActivationChange = 99

    class QDialogButtonBox(_Stub):
        StandardButton = _Enum(Ok=1, Cancel=2, Save=2, Close=4)

    class QGuiApplication(_ApplicationStub):
        @staticmethod
        def applicationDisplayName():
            return "Anki"

    for extra_name, extra_cls in (
        ("QBrush", QBrush),
        ("QDialogButtonBox", QDialogButtonBox),
        ("QEvent", QEvent),
        ("QGuiApplication", QGuiApplication),
        ("QKeyEvent", _Stub),
        ("QKeySequence", _Stub),
        ("QMenu", _Stub),
        ("QPointF", _Stub),
        ("QSizeF", _Stub),
        ("QSplitter", _Stub),
        ("QTextCharFormat", _Stub),
        ("QTextFormat", type("QTextFormat", (_Stub,), {"UserObject": 1, "UserProperty": 2})),
        ("QTextObjectInterface", type("QTextObjectInterface", (), {})),
    ):
        setattr(aqt_qt, extra_name, extra_cls)

    aqt_utils = types.ModuleType("aqt.utils")
    aqt_utils.showInfo = MagicMock()
    aqt_utils.showWarning = MagicMock()
    aqt_utils.tooltip = MagicMock()

    sys.modules["aqt"] = aqt
    sys.modules["aqt.qt"] = aqt_qt
    sys.modules["aqt.utils"] = aqt_utils


def _ensure_package(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module


def load_addon_module(relative: str):
    """Load an addon submodule without executing __init__.py."""
    _install_anki_mocks()
    _ensure_package(PACKAGE, ADDON_DIR)
    if relative.startswith("ui."):
        _ensure_package(f"{PACKAGE}.ui", ADDON_DIR / "ui")

    file_path = ADDON_DIR / Path(relative.replace(".", "/") + ".py")
    full_name = f"{PACKAGE}.{relative}"
    spec = importlib.util.spec_from_file_location(full_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(full_name)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = full_name.rpartition(".")[0]
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


def load_env_local() -> dict[str, str]:
    """Load KEY=value pairs from .env.local (gitignored)."""
    env_path = ADDON_DIR / ".env.local"
    if not env_path.is_file():
        return {}

    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def gemini_api_key_from_env() -> str:
    import os

    direct = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if direct:
        return direct
    return (load_env_local().get("GEMINI_API_KEY") or "").strip()
