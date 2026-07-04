"""Offline tests for pure logic (no Anki UI required).

Run from the addon folder:
    py tests/test_offline.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import load_addon_module

_load_addon_module = load_addon_module


class TestGeminiClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gc = _load_addon_module("gemini_client")

    def test_strip_markdown_fences(self):
        raw = "```html\n<p>Hello</p>\n```"
        self.assertEqual(self.gc.strip_markdown_fences(raw), "<p>Hello</p>")

    def test_decode_stream_line_preserves_utf8(self):
        raw = "Sì, più atomicità".encode("utf-8")
        self.assertEqual(self.gc._decode_stream_line(raw), "Sì, più atomicità")

    def test_iter_stream_text_deltas_decodes_utf8_text(self):
        import json
        from unittest.mock import Mock

        chunk = {"candidates": [{"content": {"parts": [{"text": "Sì, più"}]}}]}
        body = f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8")
        response = Mock()
        response.iter_lines = lambda decode_unicode=False: iter(body.splitlines())

        deltas = list(self.gc._iter_stream_text_deltas(response, {"language": "en"}))
        self.assertEqual(deltas, ["Sì, più"])

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
        config = {
            "system_instruction": "Rules",
            "dynamic_instructions": "Be concise",
            "thinking_budget_optimize": 0,
            "thinking_budget_chat": -1,
        }
        payload = self.gc.build_request_payload(
            config=config,
            user_text="Hello",
            history=[{"role": "user", "parts": [{"text": "Prev"}]}],
            temperature=0.1,
            include_meta_rule=False,
            purpose="optimize",
        )
        user_text = payload["contents"][-1]["parts"][0]["text"]
        self.assertIn("Return ONLY the updated field HTML/MathJax", user_text)
        self.assertTrue(user_text.endswith("Hello"))
        self.assertEqual(payload["generationConfig"]["thinkingConfig"]["thinkingBudget"], 0)
        system_text = payload["systemInstruction"]["parts"][0]["text"]
        self.assertEqual(system_text, "Rules\n\nADDITIONAL DYNAMIC RULES PREVIOUSLY STORED (Lower priority than the rules above):\nBe concise")
        self.assertNotIn("OUTPUT (mandatory)", system_text)

    def test_build_request_payload_uses_custom_dynamic_prefix(self):
        config = {
            "language": "en",
            "system_instruction": "Rules",
            "dynamic_instructions": "Be concise",
            "prompt_dynamic_rules_prefix": "\nExtra rules:\n",
            "thinking_budget_chat": -1,
        }
        payload = self.gc.build_request_payload(
            config=config,
            user_text="Hello",
            history=None,
            temperature=0.2,
            include_meta_rule=False,
            purpose="optimize",
        )
        system_text = payload["systemInstruction"]["parts"][0]["text"]
        self.assertEqual(system_text, "Rules\nExtra rules:\nBe concise")

    def test_build_request_payload_chat_allows_explanations(self):
        config = {"system_instruction": "Rules", "language": "en", "thinking_budget_chat": -1}
        payload = self.gc.build_request_payload(
            config=config,
            user_text="Hello",
            history=None,
            temperature=0.2,
            include_meta_rule=True,
            purpose="chat",
        )
        system_text = payload["systemInstruction"]["parts"][0]["text"]
        self.assertNotIn("OUTPUT (mandatory)", system_text)
        self.assertIn("CHAT REPLY FORMATTING RULES", system_text)

    def test_build_request_payload_uses_split_instructions(self):
        config = {
            "system_instruction_shared": False,
            "system_instruction_optimize": "Optimize rules",
            "system_instruction_chat": "Chat rules",
            "thinking_budget_optimize": 0,
            "thinking_budget_chat": -1,
        }
        optimize_payload = self.gc.build_request_payload(
            config=config,
            user_text="Hello",
            history=None,
            temperature=0.1,
            include_meta_rule=False,
            purpose="optimize",
        )
        chat_payload = self.gc.build_request_payload(
            config=config,
            user_text="Hello",
            history=None,
            temperature=0.2,
            include_meta_rule=True,
            purpose="chat",
        )
        optimize_text = optimize_payload["systemInstruction"]["parts"][0]["text"]
        chat_text = chat_payload["systemInstruction"]["parts"][0]["text"]
        self.assertIn("Optimize rules", optimize_text)
        self.assertNotIn("Chat rules", optimize_text)
        self.assertIn("Chat rules", chat_text)
        self.assertNotIn("Optimize rules", chat_text)

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
        self.assertEqual(self.i18n.normalize_language(None), "en")

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

    def test_default_system_instruction_per_language(self):
        en = self.i18n.default_system_instruction({"language": "en"})
        it = self.i18n.default_system_instruction({"language": "it"})
        self.assertNotEqual(en, it)
        self.assertIn("student", en.lower())
        self.assertIn("studente", it.lower())
        self.assertIn(r"\(...\)", en)
        self.assertIn(r"\[...\]", en)
        self.assertIn("$$", en)
        self.assertIn("never", en.lower())
        self.assertIn("unformatted", en.lower())
        self.assertNotIn("OUTPUT (mandatory)", en)
        self.assertNotIn("OUTPUT (obbligatorio)", it)
        self.assertIn("{{c1::", en)
        self.assertIn("{{c1::", it)

    def test_optimize_user_prompt_includes_output_rules(self):
        en = self.i18n.default_optimize_user_prompt({"language": "en"})
        self.assertIn("ONLY the updated field HTML/MathJax", en)
        self.assertIn("no explanations", en.lower())
        self.assertIn("do not rewrite", en.lower())

    def test_chat_system_addon_merges_format_and_meta_rule(self):
        en = self.i18n.default_chat_system_addon({"language": "en"})
        self.assertIn("CHAT REPLY FORMATTING RULES", en)
        self.assertIn("UPDATE_DYNAMIC_RULES", en)
        self.assertIn("META-SYSTEM RULE", en)

    def test_effective_advanced_prompts_use_config_overrides(self):
        custom = {"language": "en", "prompt_optimize_user": "Custom optimize prefix"}
        self.assertEqual(self.i18n.effective_optimize_user_prompt(custom), "Custom optimize prefix")
        custom_chat = {"language": "en", "prompt_chat_addon": "Custom chat addon"}
        self.assertEqual(self.i18n.effective_chat_system_addon(custom_chat), "Custom chat addon")
        custom_prefix = {"language": "en", "prompt_dynamic_rules_prefix": "Custom dynamic header:\n"}
        self.assertEqual(self.i18n.effective_dynamic_rules_prefix(custom_prefix), "Custom dynamic header:\n")
        custom_wrapper = {"language": "en", "prompt_chat_context": "Note:\n{context}\nAsk: {request}"}
        self.assertEqual(
            self.i18n.format_chat_context_message(
                custom_wrapper,
                context="Field [Front]:\nHi",
                request="Split this?",
            ),
            "Note:\nField [Front]:\nHi\nAsk: Split this?",
        )

    def test_format_chat_context_message_falls_back_without_placeholders(self):
        config = {"language": "en", "prompt_chat_context": "Missing placeholders"}
        result = self.i18n.format_chat_context_message(
            config,
            context="ctx",
            request="req",
        )
        self.assertIn("ctx", result)
        self.assertIn("req", result)
        self.assertIn("[FULL NOTE CONTEXT TO ANALYZE]", result)

    def test_effective_system_instruction_uses_language_default(self):
        english_default = self.i18n.default_system_instruction({"language": "en"})
        config = {"language": "it", "system_instruction": english_default}
        effective = self.i18n.effective_system_instruction(config)
        self.assertIn("studente", effective.lower())
        self.assertNotEqual(effective, english_default)

    def test_effective_system_instruction_split_by_purpose(self):
        config = {
            "system_instruction_shared": False,
            "system_instruction_optimize": "Optimize rules",
            "system_instruction_chat": "Chat rules",
        }
        self.assertEqual(
            self.i18n.effective_system_instruction(config, purpose="optimize"),
            "Optimize rules",
        )
        self.assertEqual(
            self.i18n.effective_system_instruction(config, purpose="chat"),
            "Chat rules",
        )

    def test_normalize_system_instruction_fields_for_save(self):
        default_en = self.i18n.default_system_instruction({"language": "en"})
        config = {"language": "en"}
        shared_saved = self.i18n.normalize_system_instruction_fields_for_save(
            shared=True,
            shared_text=default_en,
            optimize_text="ignored",
            chat_text="ignored",
            config=config,
        )
        self.assertTrue(shared_saved["system_instruction_shared"])
        self.assertEqual(shared_saved["system_instruction"], "")
        self.assertEqual(shared_saved["system_instruction_optimize"], "")
        self.assertEqual(shared_saved["system_instruction_chat"], "")

        split_saved = self.i18n.normalize_system_instruction_fields_for_save(
            shared=False,
            shared_text="ignored",
            optimize_text="Optimize only",
            chat_text=default_en,
            config=config,
        )
        self.assertFalse(split_saved["system_instruction_shared"])
        self.assertEqual(split_saved["system_instruction"], "")
        self.assertEqual(split_saved["system_instruction_optimize"], "Optimize only")
        self.assertEqual(split_saved["system_instruction_chat"], "")

    def test_normalize_system_instruction_for_save(self):
        default_en = self.i18n.default_system_instruction({"language": "en"})
        config = {"language": "en"}
        self.assertEqual(
            self.i18n.normalize_system_instruction_for_save(default_en, config, "system_instruction"),
            "",
        )
        self.assertEqual(
            self.i18n.normalize_system_instruction_for_save("Custom rules", config, "system_instruction"),
            "Custom rules",
        )


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
        self.assertIn("chat-html-endcap", html_out)
        self.assertIn("<table class='chat-code-block'", html_out)
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

    def test_field_inner_html_renders_inline_tags(self):
        fn = self.chat._field_inner_html
        self.assertEqual(
            fn("Definisci la struttura algebrica di <b>gruppo</b>."),
            "Definisci la struttura algebrica di <b>gruppo</b>.",
        )
        self.assertEqual(fn("plain text only"), "plain text only")
        self.assertEqual(fn("x < 5"), "x &lt; 5")

    def test_closing_tags_suffix_balances_tables_and_divs(self):
        html_utils = _load_addon_module("ui.html_utils")
        fn = html_utils.closing_tags_suffix
        self.assertEqual(fn("<div><table><tr><td>x"), "</td></tr></table></div>")
        self.assertEqual(fn("<p>Hi"), "</p>")
        self.assertEqual(fn("<div><p>Hi</p>"), "</div>")

    def test_field_inner_html_closes_unclosed_markup(self):
        fn = self.chat._field_inner_html
        self.assertTrue(fn("<div><p>Hello").endswith("</p></div>"))

    def test_build_field_preview_block_uses_table_bgcolor(self):
        fn = self.chat._build_field_preview_block
        block = fn("Front", "Hello", first=True)
        self.assertIn("<table class='chat-code-block'", block)
        self.assertIn("bgcolor='#e8eaf6'", block)
        self.assertIn("bgcolor='#f3f4f6'", block)
        self.assertIn("<b class='chat-code-label'>Front:</b>", block)
        self.assertNotIn("<br>", block)
        spaced = fn("Back", "World", first=False)
        self.assertTrue(spaced.startswith("<br>"))

    def test_build_note_preview_html_closes_unclosed_divs(self):
        blocks = [
            (
                "<table class='chat-code-block'><tr><td class='chat-field-content'>"
                "<div><p>x</p>"
            ),
        ]
        html = self.chat._build_note_preview_html(blocks)
        self.assertTrue(html.startswith("<br><table class='chat-preview-panel'"))
        self.assertIn("bgcolor='#7b1fa2'", html)
        self.assertIn("<table class='chat-html-endcap'", html)
        self.assertIn("bgcolor='#ffffff'", html)
        self.assertEqual(html.count("<div"), html.count("</div>"))
        self.assertEqual(html.count("<table"), html.count("</table>"))


class TestConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = _load_addon_module("config")

    def test_default_config_has_language(self):
        self.assertEqual(self.config.DEFAULT_CONFIG["language"], "en")

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
        self.assertLessEqual(
            set(self.config.RESTORABLE_SETTING_KEYS),
            set(self.config.DEFAULT_CONFIG.keys()),
        )
        self.assertEqual(
            set(self.config.RESTORABLE_SETTING_KEYS),
            set(self.config.DEFAULT_CONFIG.keys())
            - {
                "suppress_default_system_instruction_warning",
                "suppress_api_key_restore_warning",
            },
        )

    def test_setting_help_keys_cover_all_settings(self):
        self.assertEqual(set(self.config.SETTING_HELP_KEYS.keys()), set(self.config.RESTORABLE_SETTING_KEYS))

    def test_default_config_value(self):
        self.assertEqual(self.config.default_config_value("model_optimize"), "gemini-2.5-flash-lite")
        self.assertEqual(self.config.default_config_value("brain_import_message"), "")
        self.assertEqual(self.config.default_config_value("max_history_turns"), 10)
        self.assertEqual(self.config.default_config_value("prompt_optimize_user"), "")
        self.assertEqual(self.config.default_config_value("prompt_chat_addon"), "")
        self.assertEqual(self.config.default_config_value("prompt_dynamic_rules_prefix"), "")
        self.assertEqual(self.config.default_config_value("prompt_chat_context"), "")

    def test_api_key_configured(self):
        fn = self.config.api_key_configured
        self.assertFalse(fn({"api_key": ""}))
        self.assertFalse(fn({"api_key": "INSERISCI_QUI_LA_TUA_API_KEY"}))
        self.assertTrue(fn({"api_key": "real-key"}))

    def test_uses_default_system_instruction(self):
        fn = self.config.uses_default_system_instruction
        self.assertTrue(fn({"system_instruction": ""}))
        self.assertFalse(fn({"system_instruction": "My custom rules"}))
        self.assertTrue(
            fn(
                {
                    "system_instruction_shared": False,
                    "system_instruction_optimize": "",
                    "system_instruction_chat": "Chat only custom",
                }
            )
        )
        self.assertFalse(
            fn(
                {
                    "system_instruction_shared": False,
                    "system_instruction_optimize": "Optimize custom",
                    "system_instruction_chat": "",
                }
            )
        )

    def test_restorable_settings_exclude_warning_preference(self):
        self.assertNotIn(
            "suppress_default_system_instruction_warning",
            self.config.RESTORABLE_SETTING_KEYS,
        )

    def test_dismissed_warning_keys(self):
        self.assertEqual(
            self.config.dismissed_warning_keys(
                {"suppress_default_system_instruction_warning": True}
            ),
            ["suppress_default_system_instruction_warning"],
        )
        self.assertEqual(
            self.config.dismissed_warning_keys(
                {"suppress_default_system_instruction_warning": False}
            ),
            [],
        )

    def test_is_warning_dismissed(self):
        fn = self.config.is_warning_dismissed
        self.assertTrue(
            fn({"suppress_default_system_instruction_warning": True}, "suppress_default_system_instruction_warning")
        )
        self.assertFalse(
            fn({"suppress_default_system_instruction_warning": False}, "suppress_default_system_instruction_warning")
        )


class TestOptimizeFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.opt = _load_addon_module("ui.optimize")
        cls.aqt_utils = sys.modules["aqt.utils"]
        cls.qdialog = sys.modules["aqt.qt"].QDialog

    def setUp(self):
        self.opt._last_undo.clear()
        self.aqt_utils.showInfo.reset_mock()
        self.aqt_utils.showWarning.reset_mock()
        self.aqt_utils.tooltip.reset_mock()

    def _base_config(self) -> dict:
        return {
            "language": "en",
            "api_key": "test-key",
            "model_optimize": "gemini-2.5-flash-lite",
            "thinking_budget_optimize": 0,
            "temperature_optimize": 0.1,
            "confirm_before_apply": False,
            "suppress_default_system_instruction_warning": True,
            "system_instruction": "Custom rules",
            "system_instruction_shared": True,
        }

    def _make_editor(self, *, fields=None, field_index=0):
        editor = MagicMock()
        editor.currentField = field_index
        editor.note.fields = list(fields or ["<p>Original</p>"])
        editor.loadNoteKeepingFocus = MagicMock()
        editor.parentWindow = MagicMock()
        return editor

    def test_optimize_requires_focused_field(self):
        editor = self._make_editor()
        editor.currentField = None
        with patch.object(self.opt, "load_config", return_value=self._base_config()):
            self.opt.optimize_field_with_gemini(editor)
        self.aqt_utils.showInfo.assert_called_once()

    def test_optimize_requires_non_empty_field(self):
        editor = self._make_editor(fields=[""])
        with patch.object(self.opt, "load_config", return_value=self._base_config()):
            self.opt.optimize_field_with_gemini(editor)
        self.aqt_utils.showInfo.assert_called_once()

    def test_optimize_requires_api_key(self):
        editor = self._make_editor()
        config = self._base_config()
        config["api_key"] = ""
        with patch.object(self.opt, "load_config", return_value=config):
            self.opt.optimize_field_with_gemini(editor)
        self.aqt_utils.showInfo.assert_called_once()

    def test_optimize_applies_result_without_preview(self):
        editor = self._make_editor()
        with patch.object(self.opt, "load_config", return_value=self._base_config()):
            with patch.object(self.opt, "call_gemini", return_value="<p>Optimized</p>"):
                self.opt.optimize_field_with_gemini(editor)
        self.assertEqual(editor.note.fields[0], "<p>Optimized</p>")
        self.assertTrue(self.aqt_utils.tooltip.called)

    def test_optimize_preview_cancelled_keeps_original(self):
        editor = self._make_editor()
        config = self._base_config()
        config["confirm_before_apply"] = True
        future = MagicMock(result=MagicMock(return_value="<p>Optimized</p>"))
        with patch.object(self.opt, "PreviewDialog") as preview_cls:
            preview_cls.return_value.exec.return_value = self.qdialog.DialogCode.Rejected
            self.opt._handle_optimize_result(future, editor, 0, "<p>Original</p>", config)
        self.assertEqual(editor.note.fields[0], "<p>Original</p>")

    def test_optimize_preview_accepted_applies_result(self):
        editor = self._make_editor()
        config = self._base_config()
        config["confirm_before_apply"] = True
        future = MagicMock(result=MagicMock(return_value="<p>Optimized</p>"))
        with patch.object(self.opt, "PreviewDialog") as preview_cls:
            preview_cls.return_value.exec.return_value = self.qdialog.DialogCode.Accepted
            self.opt._handle_optimize_result(future, editor, 0, "<p>Original</p>", config)
        self.assertEqual(editor.note.fields[0], "<p>Optimized</p>")

    def test_undo_restores_previous_field_content(self):
        editor = self._make_editor()
        self.opt.store_undo(editor, 0, "<p>Before</p>")
        editor.note.fields[0] = "<p>After</p>"
        with patch.object(self.opt, "load_config", return_value=self._base_config()):
            self.opt.undo_last_optimization(editor)
        self.assertEqual(editor.note.fields[0], "<p>Before</p>")
        editor.loadNoteKeepingFocus.assert_called_once()

    def test_undo_without_history_shows_info(self):
        editor = self._make_editor()
        with patch.object(self.opt, "load_config", return_value=self._base_config()):
            self.opt.undo_last_optimization(editor)
        self.aqt_utils.showInfo.assert_called_once()


class TestSettingsLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = _load_addon_module("ui.settings_dialog")
        cls.config_mod = _load_addon_module("config")

    def _dialog_shell(self):
        dialog = MagicMock()
        dialog._saved_api_key = "stored-key"
        dialog.config = {"language": "en", "api_key": "stored-key"}
        dialog._ui_config = lambda: {"language": "en"}
        dialog.api_key_input = MagicMock()
        dialog.api_key_input.text.return_value = ""
        dialog.timeout_input = MagicMock()
        dialog.timeout_input.value.return_value = 30
        return dialog

    def test_config_for_api_keeps_saved_key_when_input_empty(self):
        dialog = self._dialog_shell()
        config = self.settings.SettingsDialog._config_for_api(dialog)
        self.assertEqual(config["api_key"], "stored-key")

    def test_config_for_api_uses_typed_key_when_present(self):
        dialog = self._dialog_shell()
        dialog.api_key_input.text.return_value = "new-key"
        config = self.settings.SettingsDialog._config_for_api(dialog)
        self.assertEqual(config["api_key"], "new-key")

    def test_enter_restore_mode_leaves_api_key_unchecked(self):
        dialog = MagicMock()
        dialog._all_restore_checked = True
        dialog._restore_checkboxes = {
            key: MagicMock() for key in self.config_mod.RESTORABLE_SETTING_KEYS
        }
        dialog.stack = MagicMock()
        dialog._set_subpage_mode = MagicMock()

        self.settings.SettingsDialog._enter_restore_mode(dialog)

        api_checkbox = dialog._restore_checkboxes["api_key"]
        api_checkbox.setChecked.assert_called_once_with(False)
        for key, checkbox in dialog._restore_checkboxes.items():
            if key != "api_key":
                checkbox.setChecked.assert_called_with(True)

    def test_selected_restore_keys_returns_checked_only(self):
        dialog = MagicMock()
        checked = MagicMock()
        checked.isChecked.return_value = True
        unchecked = MagicMock()
        unchecked.isChecked.return_value = False
        dialog._restore_checkboxes = {
            "temperature_optimize": checked,
            "temperature_chat": unchecked,
        }
        selected = self.settings.SettingsDialog._selected_restore_keys(dialog)
        self.assertEqual(selected, ["temperature_optimize"])


class TestGeminiHttpIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gc = _load_addon_module("gemini_client")

    def _base_config(self) -> dict:
        return {
            "language": "en",
            "api_key": "test-key",
            "model_chat": "gemini-2.5-flash",
            "model_optimize": "gemini-2.5-flash-lite",
            "timeout_seconds": 5,
            "max_retries": 2,
            "thinking_budget_chat": -1,
            "thinking_budget_optimize": 0,
        }

    def test_call_gemini_success(self):
        response = MagicMock(ok=True, status_code=200, text="")
        response.json.return_value = {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {"parts": [{"text": "OK"}]},
                }
            ]
        }
        with patch.object(self.gc.requests, "post", return_value=response) as post:
            result = self.gc.call_gemini(config=self._base_config(), user_text="ping")
        self.assertEqual(result, "OK")
        self.assertEqual(post.call_count, 1)

    def test_call_gemini_rate_limit_not_retried(self):
        response = MagicMock(ok=False, status_code=429, text="Too Many Requests")
        with patch.object(self.gc.requests, "post", return_value=response) as post:
            with self.assertRaises(self.gc.GeminiRateLimitError):
                self.gc.call_gemini(config=self._base_config(), user_text="ping")
        self.assertEqual(post.call_count, 1)

    def test_call_gemini_server_error_retried(self):
        bad = MagicMock(ok=False, status_code=500, text="Server error")
        good = MagicMock(ok=True, status_code=200, text="")
        good.json.return_value = {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {"parts": [{"text": "Recovered"}]},
                }
            ]
        }
        with patch.object(self.gc.requests, "post", side_effect=[bad, bad, good]) as post:
            with patch.object(self.gc.time, "sleep"):
                result = self.gc.call_gemini(config=self._base_config(), user_text="ping")
        self.assertEqual(result, "Recovered")
        self.assertEqual(post.call_count, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
