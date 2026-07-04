"""Shared helpers for addon tests (offline and optional live API)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

ADDON_DIR = Path(__file__).resolve().parent.parent
PACKAGE = "Anki_AI_Addon"


def _install_anki_mocks() -> None:
    if "requests" not in sys.modules:
        requests_mod = types.ModuleType("requests")
        requests_mod.post = MagicMock()
        requests_mod.get = MagicMock()
        requests_mod.Timeout = type("Timeout", (Exception,), {})
        requests_mod.ConnectionError = type("ConnectionError", (Exception,), {})
        sys.modules["requests"] = requests_mod

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
        WidgetAttribute = _Enum(WA_QuitOnClose=1, WA_StyledBackground=2)
        WindowModality = _Enum(NonModal=0)
        ScrollBarPolicy = _Enum(ScrollBarAlwaysOff=0, ScrollBarAsNeeded=1)
        FocusPolicy = _Enum(StrongFocus=1)
        Key = _Enum(Key_Return=16777220, Key_Enter=16777221)
        KeyboardModifier = _Enum(ShiftModifier=1)
        MatchFlag = _Enum(MatchContains=1)
        CaseSensitivity = _Enum(CaseInsensitive=0)

    class _Stub:
        EchoMode = _Enum(Password=1)
        DialogCode = _Enum(Rejected=0, Accepted=1)
        LineWrapMode = _Enum(NoWrap=0)
        MoveOperation = _Enum(End=0)
        MoveMode = _Enum(KeepAnchor=1)

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
        Icon = _Enum(Warning=1)
        StandardButton = _Enum(Ok=1, Cancel=2)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._exec_result = QMessageBox.StandardButton.Ok
            self._dismiss_checkbox = _CheckBoxStub()

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

        def exec(self):
            return self._exec_result

    class QSizePolicy(_Stub):
        Policy = _Enum(Minimum=1, Fixed=2)

    for name, cls in (
        ("QApplication", _Stub),
        ("QCheckBox", _CheckBoxStub),
        ("QCloseEvent", _Stub),
        ("QDialog", _Stub),
        ("QDoubleSpinBox", _Stub),
        ("QFrame", _Stub),
        ("QHBoxLayout", _Stub),
        ("QLabel", _Stub),
        ("QLineEdit", _LineEditStub),
        ("QObject", _Stub),
        ("QPushButton", _Stub),
        ("QScrollArea", _Stub),
        ("QSize", _Stub),
        ("QSpinBox", _Stub),
        ("QStackedWidget", _Stub),
        ("QTextBrowser", _Stub),
        ("QTextCursor", _Stub),
        ("QTextEdit", _Stub),
        ("QUrl", _Stub),
        ("QVBoxLayout", _Stub),
        ("QWidget", _Stub),
        ("QAction", _Stub),
    ):
        setattr(aqt_qt, name, cls)

    class _Signal:
        def connect(self, *args, **kwargs):
            return None

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

    aqt_qt.QFrame = _Frame
    aqt_qt.QColor = QColor
    aqt_qt.QPalette = QPalette
    aqt_qt.QComboBox = QComboBox
    aqt_qt.QCompleter = QCompleter
    aqt_qt.QStringListModel = QStringListModel
    aqt_qt.Qt = Qt

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
