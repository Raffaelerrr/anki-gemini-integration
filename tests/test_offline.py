"""Offline tests for pure logic (no Anki UI required).

Run from the addon folder:
    py tests/test_offline.py
"""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ADDON_DIR = Path(__file__).resolve().parent.parent
ADDONS21_DIR = ADDON_DIR.parent
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
        WidgetAttribute = _Enum(WA_QuitOnClose=1)
        WindowModality = _Enum(NonModal=0)
        ScrollBarPolicy = _Enum(ScrollBarAlwaysOff=0, ScrollBarAsNeeded=1)
        Key = _Enum(Key_Return=16777220, Key_Enter=16777221)
        KeyboardModifier = _Enum(ShiftModifier=1)
        MatchFlag = _Enum(MatchContains=1)
        CaseSensitivity = _Enum(CaseInsensitive=0)

    class _Stub:
        EchoMode = _Enum(Password=1)
        DialogCode = _Enum(Accepted=1)
        LineWrapMode = _Enum(NoWrap=0)
        MoveOperation = _Enum(End=0)
        MoveMode = _Enum(KeepAnchor=1)

        def __init__(self, *args, **kwargs):
            pass

        @staticmethod
        def installEventFilter(*args, **kwargs):
            return None

    for name in (
        "QApplication",
        "QCheckBox",
        "QCloseEvent",
        "QDialog",
        "QDoubleSpinBox",
        "QFrame",
        "QHBoxLayout",
        "QLabel",
        "QLineEdit",
        "QPushButton",
        "QScrollArea",
        "QSpinBox",
        "QStackedWidget",
        "QTextBrowser",
        "QTextCursor",
        "QTextEdit",
        "QTimer",
        "QUrl",
        "QVBoxLayout",
        "QWidget",
        "QAction",
    ):
        setattr(aqt_qt, name, _Stub)

    class _Frame(_Stub):
        class Shape:
            NoFrame = 0

    class _Signal:
        def connect(self, *args, **kwargs):
            return None

    class _LineEditStub(_Stub):
        def __init__(self):
            super().__init__()
            self.textEdited = _Signal()

        def setPlaceholderText(self, *args, **kwargs):
            return None

        def hasFocus(self):
            return False

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

    aqt_qt.QFrame = _Frame
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


def _load_addon_module(relative: str):
    """Load an addon submodule without executing __init__.py."""
    _install_anki_mocks()
    _ensure_package(PACKAGE, ADDON_DIR)
    if relative.startswith("ui."):
        _ensure_package(f"{PACKAGE}.ui", ADDON_DIR / "ui")

    module_name = relative.split(".")[-1]
    file_path = ADDON_DIR / relative.replace(".", "/").replace(f"ui/", "ui/") 
    if not str(file_path).endswith(".py"):
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


class TestGeminiClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gc = _load_addon_module("gemini_client")

    def test_strip_markdown_fences(self):
        raw = "```html\n<p>Hello</p>\n```"
        self.assertEqual(self.gc.strip_markdown_fences(raw), "<p>Hello</p>")

    def test_extract_dynamic_rules(self):
        text = "Visible<UPDATE_DYNAMIC_RULES>\nRule 1\n</UPDATE_DYNAMIC_RULES>"
        cleaned, rules = self.gc.extract_dynamic_rules(text)
        self.assertEqual(cleaned, "Visible")
        self.assertEqual(rules, "Rule 1")

    def test_extract_dynamic_rules_none(self):
        cleaned, rules = self.gc.extract_dynamic_rules("No tags here")
        self.assertEqual(cleaned, "No tags here")
        self.assertIsNone(rules)

    def test_trim_history(self):
        history = [{"role": "user", "parts": []} for _ in range(10)]
        trimmed = self.gc.trim_history(history, max_turns=2)
        self.assertEqual(len(trimmed), 4)

    def test_trim_history_zero_turns(self):
        history = [{"role": "user", "parts": []}]
        self.assertEqual(self.gc.trim_history(history, max_turns=0), [])

    def test_build_api_url(self):
        url = self.gc.build_api_url("gemini-2.5-flash")
        self.assertIn("generativelanguage.googleapis.com", url)
        self.assertIn("gemini-2.5-flash", url)
        self.assertIn("generateContent", url)

    def test_build_stream_api_url(self):
        url = self.gc.build_api_url("gemini-2.5-flash", stream=True)
        self.assertIn("streamGenerateContent", url)
        self.assertIn("alt=sse", url)

    def test_resolve_model_prefers_purpose_specific(self):
        config = {
            "model": "legacy-model",
            "model_optimize": "optimize-model",
            "model_chat": "chat-model",
        }
        self.assertEqual(self.gc.resolve_model(config, "optimize"), "optimize-model")
        self.assertEqual(self.gc.resolve_model(config, "chat"), "chat-model")

    def test_resolve_model_falls_back_to_legacy(self):
        config = {"model": "legacy-model"}
        self.assertEqual(self.gc.resolve_model(config, "optimize"), "legacy-model")

    def test_build_generation_config_includes_thinking_budget(self):
        config = {"thinking_budget_optimize": 0, "thinking_budget_chat": -1}
        optimize_gen = self.gc.build_generation_config(config, 0.2, "optimize")
        chat_gen = self.gc.build_generation_config(config, 0.2, "chat")
        self.assertEqual(optimize_gen["thinkingConfig"]["thinkingBudget"], 0)
        self.assertEqual(chat_gen["thinkingConfig"]["thinkingBudget"], -1)

    def test_build_request_payload(self):
        config = {"system_instruction": "Rules", "thinking_budget_optimize": 0, "thinking_budget_chat": -1}
        payload = self.gc.build_request_payload(
            config=config,
            user_text="Hello",
            history=[{"role": "user", "parts": [{"text": "Prev"}]}],
            temperature=0.1,
            include_meta_rule=False,
            purpose="optimize",
        )
        self.assertEqual(payload["contents"][-1]["parts"][0]["text"], "Hello")
        self.assertEqual(payload["generationConfig"]["thinkingConfig"]["thinkingBudget"], 0)

    def test_parse_response_success(self):
        config = {"language": "en"}
        data = {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {"parts": [{"text": "Hello"}]},
                }
            ]
        }
        self.assertEqual(self.gc._parse_response_payload(data, config), "Hello")

    def test_parse_response_blocked(self):
        config = {"language": "en"}
        data = {"promptFeedback": {"blockReason": "SAFETY"}}
        with self.assertRaises(self.gc.GeminiResponseError) as ctx:
            self.gc._parse_response_payload(data, config)
        self.assertIn("SAFETY", str(ctx.exception))

    def test_classify_http_error_auth(self):
        config = {"language": "en"}
        err = self.gc._classify_http_error(403, "nope", config)
        self.assertIsInstance(err, self.gc.GeminiAuthError)

    def test_call_gemini_auth_not_retried(self):
        config = {
            "language": "en",
            "api_key": "bad",
            "model_chat": "gemini-2.5-flash",
            "timeout_seconds": 5,
            "max_retries": 2,
            "thinking_budget_chat": -1,
        }
        response = MagicMock(ok=False, status_code=403, text="Forbidden")

        with patch.object(self.gc.requests, "post", return_value=response) as post:
            with self.assertRaises(self.gc.GeminiAuthError):
                self.gc.call_gemini(config=config, user_text="test")
        self.assertEqual(post.call_count, 1)

    def test_model_id_from_list_entry_requires_generate_content(self):
        entry = {
            "name": "models/gemini-2.5-flash",
            "baseModelId": "gemini-2.5-flash",
            "supportedGenerationMethods": ["countTokens"],
        }
        self.assertIsNone(self.gc._model_id_from_list_entry(entry))

    def test_model_id_from_list_entry_uses_base_model_id(self):
        entry = {
            "name": "models/gemini-2.5-flash",
            "baseModelId": "gemini-2.5-flash",
            "supportedGenerationMethods": ["generateContent"],
        }
        self.assertEqual(self.gc._model_id_from_list_entry(entry), "gemini-2.5-flash")

    def test_sort_model_ids_orders_newer_and_lite_first(self):
        models = ["gemini-2.0-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]
        self.assertEqual(
            self.gc.sort_model_ids(models),
            ["gemini-2.5-flash-lite", "gemini-2.5-pro", "gemini-2.0-flash"],
        )

    def test_list_gemini_models_paginates(self):
        config = {"language": "en", "api_key": "good", "timeout_seconds": 5}
        first = MagicMock(
            ok=True,
            status_code=200,
            text="",
        )
        first.json.return_value = {
            "models": [
                {
                    "name": "models/gemini-2.5-flash",
                    "baseModelId": "gemini-2.5-flash",
                    "supportedGenerationMethods": ["generateContent"],
                }
            ],
            "nextPageToken": "page-2",
        }
        second = MagicMock(
            ok=True,
            status_code=200,
            text="",
        )
        second.json.return_value = {
            "models": [
                {
                    "name": "models/gemini-2.5-pro",
                    "baseModelId": "gemini-2.5-pro",
                    "supportedGenerationMethods": ["generateContent"],
                }
            ]
        }

        with patch.object(self.gc.requests, "get", side_effect=[first, second]) as get:
            models = self.gc.list_gemini_models(config=config)

        self.assertEqual(get.call_count, 2)
        self.assertEqual(models, ["gemini-2.5-flash", "gemini-2.5-pro"])


class TestI18n(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i18n = _load_addon_module("i18n")

    def test_all_keys_have_both_languages(self):
        missing = []
        for key, translations in self.i18n._STRINGS.items():
            for lang in self.i18n.SUPPORTED_LANGUAGES:
                if lang not in translations or not translations[lang].strip():
                    missing.append(f"{key}.{lang}")
        self.assertEqual(missing, [])

    def test_tr_english(self):
        config = {"language": "en"}
        self.assertIn("Optimize", self.i18n.tr("editor.tip.optimize", config=config))

    def test_tr_italian_default(self):
        self.assertIn("Ottimizza", self.i18n.tr("editor.tip.optimize", lang="it"))

    def test_tr_interpolation(self):
        config = {"language": "en"}
        msg = self.i18n.tr("chat.error", config=config, error="timeout")
        self.assertEqual(msg, "Error: timeout")

    def test_normalize_language(self):
        self.assertEqual(self.i18n.normalize_language("en"), "en")
        self.assertEqual(self.i18n.normalize_language("EN"), "en")
        self.assertEqual(self.i18n.normalize_language("it"), "it")
        self.assertEqual(self.i18n.normalize_language(None), "it")

    def test_default_brain_import_message_per_language(self):
        en = self.i18n.default_brain_import_message({"language": "en"})
        it = self.i18n.default_brain_import_message({"language": "it"})
        self.assertNotEqual(en, it)
        self.assertIn("atomicity", en.lower())

    def test_effective_brain_import_message_uses_language_default(self):
        italian_default = self.i18n.default_brain_import_message({"language": "it"})
        config = {"language": "en", "brain_import_message": italian_default}
        effective = self.i18n.effective_brain_import_message(config)
        self.assertIn("atomicity", effective.lower())
        self.assertNotEqual(effective, italian_default)

    def test_effective_brain_import_message_keeps_custom_text(self):
        config = {"language": "en", "brain_import_message": "My custom prompt"}
        self.assertEqual(self.i18n.effective_brain_import_message(config), "My custom prompt")


class TestChatFormatter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fmt = _load_addon_module("ui.chat_formatter")

    def test_parse_field_label_front(self):
        self.assertEqual(self.fmt._parse_field_label_line("Front:"), "Front")

    def test_parse_field_label_bold(self):
        self.assertEqual(self.fmt._parse_field_label_line("**Back**:"), "Back")

    def test_parse_field_label_campo(self):
        self.assertEqual(self.fmt._parse_field_label_line("Campo [Extra]:"), "Extra")

    def test_parse_field_label_field_en(self):
        self.assertEqual(self.fmt._parse_field_label_line("Field [Front]:"), "Front")

    def test_reject_sentence_as_field_name(self):
        self.assertIsNone(self.fmt._parse_field_label_line("This is a sentence."))

    def test_format_reply_with_code_block(self):
        text = "Front:\n```\n<b>Hi</b>\n```"
        store: dict[str, str] = {}
        html_out = self.fmt.format_gemini_reply_html(
            text, store, "t1", config={"language": "en"}
        )
        self.assertIn("copy:t1-0", html_out)
        self.assertIn("Copy", html_out)
        self.assertEqual(store["t1-0"], "<b>Hi</b>")

    def test_format_reply_empty(self):
        self.assertEqual(
            self.fmt.format_gemini_reply_html("", {}, "t1", config={"language": "en"}),
            "",
        )

    def test_format_reply_uses_theme_classes(self):
        html_out = self.fmt.format_gemini_reply_html(
            "Hello **world**",
            {},
            "t1",
            config={"language": "en"},
        )
        self.assertIn("chat-prose", html_out)
        self.assertNotIn("#e0e0e0", html_out)


class TestTheme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theme = _load_addon_module("ui.theme")

    def test_default_palette_is_light_without_anki_theme(self):
        colors = self.theme.get_theme_colors()
        self.assertEqual(colors.text, self.theme._LIGHT.text)

    def test_chat_stylesheet_uses_palette_colors(self):
        stylesheet = self.theme.chat_document_stylesheet()
        self.assertIn(".chat-label-you", stylesheet)
        self.assertIn(".chat-prose", stylesheet)
        self.assertIn(self.theme._LIGHT.text, stylesheet)

    def test_muted_hint_html(self):
        html_out = self.theme.muted_hint_html("Hint text")
        self.assertIn("Hint text", html_out)
        self.assertIn(self.theme._LIGHT.text_muted, html_out)


class TestModelSelector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ms = _load_addon_module("ui.model_selector")

    def test_model_choice_list_adds_custom(self):
        choices = self.ms.model_choice_list("my-custom-model")
        self.assertEqual(choices[0], "my-custom-model")
        self.assertIn("gemini-2.5-flash", choices)

    def test_filter_model_choices_partial_match(self):
        all_models = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]
        self.assertEqual(
            self.ms.filter_model_choices(all_models, "lite"),
            ["gemini-2.5-flash-lite"],
        )

    def test_filter_model_choices_empty_query_returns_all(self):
        all_models = ["gemini-2.5-flash", "gemini-2.5-pro"]
        self.assertEqual(self.ms.filter_model_choices(all_models, ""), all_models)

    def test_create_model_selector_keeps_custom_value(self):
        combo = self.ms.create_model_selector(
            None,
            current="gemini-custom-preview",
            default="gemini-2.5-flash-lite",
            config={"language": "en"},
        )
        self.assertEqual(self.ms.model_selector_value(combo), "gemini-custom-preview")

    def test_update_model_selector_choices_merges_api_models(self):
        combo = self.ms.create_model_selector(
            None,
            current="gemini-2.5-flash",
            default="gemini-2.5-flash-lite",
            config={"language": "en"},
        )
        self.ms.update_model_selector_choices(
            combo,
            ["gemini-3.5-flash", "gemini-2.5-pro"],
        )
        all_models = combo.property("_gemini_all_models")
        self.assertIn("gemini-3.5-flash", all_models)
        self.assertIn("gemini-2.5-flash-lite", all_models)
        self.assertEqual(self.ms.model_selector_value(combo), "gemini-2.5-flash")


class TestChatDialogHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chat = _load_addon_module("ui.chat_dialog")

    def test_strip_field_html_edges(self):
        fn = self.chat._strip_field_html_edges
        self.assertEqual(fn("<p>Hi</p><br>"), "<p>Hi</p>")
        self.assertEqual(fn("  <div>Text</div>  "), "<div>Text</div>")


class TestConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load_addon_module("config")

    def test_default_config_has_language(self):
        self.assertIn("language", self.config.DEFAULT_CONFIG)

    def test_default_config_has_model_settings(self):
        defaults = self.config.DEFAULT_CONFIG
        self.assertEqual(defaults["model_optimize"], "gemini-2.5-flash-lite")
        self.assertEqual(defaults["model_chat"], "gemini-2.5-flash")
        self.assertEqual(defaults["thinking_budget_optimize"], 0)
        self.assertEqual(defaults["thinking_budget_chat"], -1)
        self.assertTrue(defaults["chat_streaming"])

    def test_apply_config_migrations_from_legacy_model(self):
        migrated = self.config._apply_config_migrations(
            {"model": "legacy-model", "model_optimize": "", "model_chat": ""},
            {"model": "legacy-model", "model_optimize": "", "model_chat": ""},
        )
        self.assertEqual(migrated["model_optimize"], "legacy-model")
        self.assertEqual(migrated["model_chat"], "legacy-model")

    def test_apply_config_migrations_from_legacy_thinking_budget(self):
        migrated = self.config._apply_config_migrations(
            {"thinking_budget": 1024},
            {"thinking_budget": 1024},
        )
        self.assertEqual(migrated["thinking_budget_optimize"], 1024)
        self.assertEqual(migrated["thinking_budget_chat"], 1024)
        self.assertNotIn("thinking_budget", migrated)

    def test_restorable_settings_cover_defaults(self):
        self.assertEqual(set(self.config.RESTORABLE_SETTING_KEYS), set(self.config.DEFAULT_CONFIG.keys()))

    def test_setting_help_keys_cover_all_settings(self):
        self.assertEqual(set(self.config.SETTING_HELP_KEYS.keys()), set(self.config.RESTORABLE_SETTING_KEYS))

    def test_default_config_value(self):
        self.assertEqual(self.config.default_config_value("model_optimize"), "gemini-2.5-flash-lite")
        self.assertEqual(self.config.default_config_value("brain_import_message"), "")

    def test_api_key_configured(self):
        fn = self.config.api_key_configured
        self.assertFalse(fn({"api_key": ""}))
        self.assertFalse(fn({"api_key": "INSERISCI_QUI_LA_TUA_API_KEY"}))
        self.assertTrue(fn({"api_key": "real-key"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
