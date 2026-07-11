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

    def test_resolve_model_uses_default_when_missing(self):
        config: dict[str, str] = {}
        self.assertEqual(self.gc.resolve_model(config, "optimize"), "gemini-2.5-flash-lite")
        self.assertEqual(self.gc.resolve_model(config, "chat"), "gemini-2.5-flash")

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
        self.assertEqual(
            system_text,
            "Rules\n\nADDITIONAL DYNAMIC RULES PREVIOUSLY STORED "
            "(Lower priority than the rules above)\nBe concise",
        )
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
        self.assertEqual(system_text, "Rules\n\nExtra rules:\nBe concise")

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

    def test_build_request_payload_uses_cached_content(self):
        config = {"language": "en", "thinking_budget_chat": -1}
        payload = self.gc.build_request_payload(
            config=config,
            user_text="Hello",
            history=None,
            temperature=0.2,
            include_meta_rule=False,
            purpose="chat",
            cached_content_name="cachedContents/abc123",
            live_system_instruction="Live rules only",
        )
        self.assertEqual(payload["cachedContent"], "cachedContents/abc123")
        self.assertEqual(
            payload["systemInstruction"]["parts"][0]["text"],
            "Live rules only",
        )

    def test_prepare_gemini_request_skip_cache_omits_cached_content(self):
        pc = _load_addon_module("prompt_cache")
        pc.clear_prompt_cache_store()
        config = {
            "language": "en",
            "api_key": "test-key",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {"system_instruction": True},
            "system_instruction": "X" * 9000,
            "thinking_budget_chat": -1,
        }
        bundle = pc.build_prompt_cache_bundle(config, purpose="chat")
        assert bundle is not None
        pc.ensure_prompt_cache(config=config, purpose="chat", bundle=bundle)
        prepared = self.gc.prepare_gemini_request(
            config=config,
            user_text="Hello",
            history=None,
            temperature=0.2,
            include_meta_rule=False,
            purpose="chat",
            allow_prompt_cache_create=False,
            allow_prompt_cache_use=False,
        )
        self.assertNotIn("cachedContent", prepared.payload)

    def test_prepare_gemini_request_skip_cache_uses_flattened_overrides(self):
        pc = _load_addon_module("prompt_cache")
        pc.clear_prompt_cache_store()
        config = {
            "language": "en",
            "api_key": "test-key",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {"system_instruction": True},
            "system_instruction": "X" * 9000,
            "thinking_budget_chat": -1,
        }
        bundle = pc.build_prompt_cache_bundle(config, purpose="chat")
        assert bundle is not None
        edited = pc.rebuild_prompt_cache_bundle(
            config,
            purpose="chat",
            enabled_segment_ids=bundle.enabled_segment_ids,
            segment_texts={"system_instruction": "Y" * 9000},
            live_system_text="",
        )
        assert edited is not None
        system, payload = pc.flatten_bundle_for_live_send(
            config,
            edited,
            purpose="chat",
            include_meta_rule=False,
            user_text="Question?",
        )
        prepared = self.gc.prepare_gemini_request(
            config=config,
            user_text="Question?",
            history=None,
            temperature=0.2,
            include_meta_rule=False,
            purpose="chat",
            allow_prompt_cache_create=False,
            allow_prompt_cache_use=False,
            override_outgoing_payload=payload,
            override_system_instruction=system,
        )
        self.assertNotIn("cachedContent", prepared.payload)
        self.assertIn("Y" * 9000, prepared.payload["systemInstruction"]["parts"][0]["text"])

    def test_prepare_gemini_request_falls_back_when_cache_create_fails(self):
        pc = _load_addon_module("prompt_cache")
        pc.clear_prompt_cache_store()
        config = {
            "language": "en",
            "api_key": "test-key",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {
                "system_instruction": True,
                "imported_note": True,
            },
            "system_instruction": "X" * 9000,
            "thinking_budget_chat": -1,
        }
        session = pc.PromptCacheSessionContext(
            note_context="Note body",
            include_note_context=True,
        )
        with patch.object(pc, "create_cached_content", side_effect=pc.PromptCacheError("cache failed")):
            prepared = self.gc.prepare_gemini_request(
                config=config,
                user_text="Question?",
                history=None,
                temperature=0.2,
                include_meta_rule=False,
                purpose="chat",
                cache_session=session,
            )
        payload = prepared.payload
        self.assertNotIn("cachedContent", payload)
        user_part = payload["contents"][-1]["parts"][0]["text"]
        self.assertIn("Note body", user_part)
        self.assertIn("Question?", user_part)

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

    def test_classify_http_error_rate_limit_with_retry_after(self):
        config = {"language": "en"}
        err = self.gc._classify_http_error(
            429,
            '{"error":{"code":429,"status":"RESOURCE_EXHAUSTED","message":"Too many requests"}}',
            config,
            headers={"Retry-After": "12"},
        )
        self.assertIsInstance(err, self.gc.GeminiRateLimitError)
        self.assertIn("12", str(err))

    def test_classify_http_error_daily_quota(self):
        config = {"language": "en"}
        body = (
            '{"error":{"code":429,"status":"RESOURCE_EXHAUSTED","message":"Quota exceeded",'
            '"details":[{"@type":"type.googleapis.com/google.rpc.QuotaFailure","violations":'
            '[{"quotaId":"GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}'
        )
        err = self.gc._classify_http_error(429, body, config)
        self.assertIsInstance(err, self.gc.GeminiRateLimitError)
        self.assertIn("Daily Gemini quota", str(err))

    def test_stream_error_payload_rate_limit(self):
        config = {"language": "en"}
        payload = {
            "error": {
                "code": 429,
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.RetryInfo",
                        "retryDelay": "5s",
                    }
                ],
            }
        }
        with self.assertRaises(self.gc.GeminiRateLimitError) as ctx:
            self.gc._raise_if_stream_error_payload(payload, config)
        self.assertIn("5", str(ctx.exception))

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


class TestPromptCompose(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = _load_addon_module("prompt_compose")

    def test_join_prompt_blocks_skips_empty_parts(self):
        self.assertEqual(
            self.compose.join_prompt_blocks("A", "", "  ", "B"),
            "A\n\nB",
        )

    def test_join_prompt_header_body(self):
        self.assertEqual(
            self.compose.join_prompt_header_body("Header:", "Body"),
            "Header:\nBody",
        )


class TestI18n(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i18n = _load_addon_module("i18n")
        cls.wrapper = _load_addon_module("chat_context_wrapper")

    def test_all_keys_have_both_languages(self):
        allow_empty = {
            "chat.include_context.icon",
            "chat.include_context.icon.excluded",
            "chat.edit.menu.icon",
            "chat.inspect_prompt",
            "chat.stop_before_send.icon",
            "chat.modify_prompt_before_send",
        }
        missing = []
        for key, translations in self.i18n._STRINGS.items():
            if key in allow_empty:
                continue
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

    def test_tr_interpolation_preserves_icon_placeholders(self):
        config = {"language": "en"}
        msg = self.i18n.tr(
            "settings.help.addon_payload_sizes",
            config=config,
            billing_url="https://example.com/billing",
        )
        self.assertIn("{icon:lens}", msg)
        self.assertIn("https://example.com/billing", msg)

    def test_edit_wrapper_strings(self):
        en = {"language": "en"}
        it = {"language": "it"}
        self.assertEqual(self.i18n.tr("chat.edit_wrapper", config=en), "Edit context wrapper")
        self.assertEqual(self.i18n.tr("chat.edit_wrapper", config=it), "Modifica wrapper contesto")
        self.assertEqual(
            self.i18n.tr("chat.edit_wrapper.tooltip", config=en),
            "Edit context wrapper",
        )
        self.assertEqual(
            self.i18n.tr("chat.edit_templates.tooltip", config=en),
            "Edit templates",
        )
        self.assertIn("request placeholder", self.i18n.tr("chat.edit_wrapper.wrapper_hint", config=en))
        self.assertIn("session", self.i18n.tr("chat.edit_wrapper.wrapper_label", config=en).lower())
        invalid_msg = self.i18n.tr("chat.edit_wrapper.wrapper_invalid", config=en)
        self.assertIn("{{context}}", invalid_msg)
        self.assertIn("{{request}}", invalid_msg)
        basic_label = self.i18n.chat_edit_wrapper_label_text({"language": "en"})
        self.assertIn("Context wrapper", basic_label)
        full_label = self.i18n.chat_edit_wrapper_label_text(
            {"language": "en", "brain_import_templates": True, "brain_import_css": True}
        )
        self.assertIn("optional sections", full_label.lower())
        self.assertNotEqual(basic_label, full_label)
        self.assertEqual(self.i18n.tr("chat.preview.refresh", config=en), "Refresh preview")
        self.assertEqual(
            self.i18n.tr("chat.preview.open_window.tooltip", config=en),
            "{icon:eye} Open the imported note preview in a separate window",
        )
        templates_title = self.i18n.chat_edit_templates_title_text(
            {"language": "en", "brain_import_templates": True, "brain_import_css": True}
        )
        self.assertIn("templates", templates_title.lower())
        self.assertEqual(
            self.i18n.chat_edit_templates_detail_text({"language": "en"}),
            "Not shown in the note preview.",
        )
        self.assertIn(
            "excluded",
            self.i18n.tr("chat.include_context", config=en).lower(),
        )

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
        self.assertIn("outside code blocks", en)
        self.assertIn("render in the chat window", en)
        self.assertIn("UPDATE_DYNAMIC_RULES", en)
        self.assertIn("META-SYSTEM RULE", en)

    def test_effective_advanced_prompts_use_config_overrides(self):
        custom = {"language": "en", "prompt_optimize_user": "Custom optimize prefix"}
        self.assertEqual(self.i18n.effective_optimize_user_prompt(custom), "Custom optimize prefix")
        custom_chat = {"language": "en", "prompt_chat_addon": "Custom chat addon"}
        self.assertEqual(self.i18n.effective_chat_system_addon(custom_chat), "Custom chat addon")
        custom_prefix = {"language": "en", "prompt_dynamic_rules_prefix": "Custom dynamic header:\n"}
        self.assertEqual(self.i18n.effective_dynamic_rules_prefix(custom_prefix), "Custom dynamic header:\n")
        custom_wrapper = {
            "language": "en",
            "prompt_chat_context_sections": {
                "context": "Note:\n{{context}}",
                "request": "Ask: {{request}}",
            },
        }
        result = self.i18n.format_chat_context_message(
            custom_wrapper,
            context="Field [Front]\nHi",
            request="Split this?",
        )
        self.assertEqual(result, "Note:\nField [Front]\nHi\n\nAsk: Split this?")

    def test_format_chat_context_message_accepts_session_section_override(self):
        config = {"language": "en"}
        section_prefixes = {
            "context": "Note:\n{{context}}",
            "templates": "Templates:\n{{templates}}",
            "styling": "Styling:\n{{styling}}",
            "request": "Ask:\n{{request}}",
            "format_guide": "",
        }
        result = self.i18n.format_chat_context_message(
            config,
            context="Field [Front]\nHi",
            request="Split this?",
            section_prefixes=section_prefixes,
        )
        self.assertEqual(
            result,
            "Note:\nField [Front]\nHi\n\nAsk:\nSplit this?",
        )
        result_with_templates = self.i18n.format_chat_context_message(
            {**config, "brain_import_templates": True},
            context="Field [Front]\nHi",
            request="Split this?",
            templates="tmpl-body",
            section_prefixes=section_prefixes,
        )
        self.assertIn("Templates:\n", result_with_templates)
        self.assertIn("tmpl-body", result_with_templates)

    def test_format_chat_context_message_falls_back_without_request_placeholder(self):
        config = {
            "language": "en",
            "prompt_chat_context_sections": {
                "request": "Missing request marker",
            },
        }
        result = self.i18n.format_chat_context_message(
            config,
            context="ctx",
            request="req",
        )
        self.assertIn("ctx", result)
        self.assertIn("req", result)
        self.assertIn("[FULL NOTE CONTEXT TO ANALYZE]", result)

    def test_format_chat_context_message_invalid_session_falls_back_to_settings_wrapper(self):
        config = {
            "language": "en",
            "prompt_chat_context_sections": {
                "context": "Settings:\n{{context}}",
                "request": "Q: {{request}}",
            },
        }
        result = self.i18n.format_chat_context_message(
            config,
            context="ctx",
            request="req",
            section_prefixes={"request": "Broken"},
        )
        self.assertEqual(result, "Settings:\nctx\n\nQ: req")

    def test_format_chat_context_message_omits_templates_without_placeholder(self):
        config = {"language": "en", "brain_import_templates": True}
        section_prefixes = {
            "context": "Note:\n{{context}}",
            "templates": "[TEMPLATES]\n",
            "request": "Q: {{request}}",
            "format_guide": "",
        }
        result = self.i18n.format_chat_context_message(
            config,
            context="ctx",
            request="req",
            templates="tmpl-body",
            section_prefixes=section_prefixes,
        )
        self.assertEqual(result, "Note:\nctx\n\nQ: req")
        self.assertNotIn("tmpl-body", result)
        self.assertNotIn("[TEMPLATES]", result)

    def test_format_chat_context_message_omits_styling_without_placeholder(self):
        config = {"language": "en", "brain_import_css": True}
        section_prefixes = {
            "context": "Note:\n{{context}}",
            "styling": "[STYLE]\n",
            "request": "Q: {{request}}",
            "format_guide": "",
        }
        result = self.i18n.format_chat_context_message(
            config,
            context="ctx",
            request="req",
            styling=".card { color: red; }",
            section_prefixes=section_prefixes,
        )
        self.assertEqual(result, "Note:\nctx\n\nQ: req")
        self.assertNotIn(".card", result)
        self.assertNotIn("[STYLE]", result)

    def test_format_chat_context_message_respects_section_order(self):
        config = {"language": "en", "brain_import_templates": True}
        order = ["request", "context", "format_guide", "templates", "styling"]
        section_prefixes = {
            "context": "C:\n{{context}}",
            "templates": "T:\n{{templates}}",
            "request": "R:\n{{request}}",
            "format_guide": "",
        }
        result = self.i18n.format_chat_context_message(
            config,
            context="ctx",
            request="req",
            templates="tmpl",
            section_order=order,
            section_prefixes=section_prefixes,
        )
        self.assertLess(result.index("R:\nreq"), result.index("C:\nctx"))
        self.assertLess(result.index("[HOW TO READ ANKI"), result.index("T:\ntmpl"))

    def test_format_chat_context_message_omits_format_guide_without_templates_or_styling(self):
        config = {"language": "en", "brain_import_templates": True, "brain_import_css": True}
        section_prefixes = {
            "context": "Note:\n{{context}}",
            "request": "Q: {{request}}",
            "format_guide": "",
        }
        result = self.i18n.format_chat_context_message(
            config,
            context="ctx",
            request="req",
            templates="",
            styling="",
            section_prefixes=section_prefixes,
        )
        self.assertNotIn("[HOW TO READ ANKI CARD TEMPLATES AND STYLING]", result)

    def test_format_chat_context_message_includes_templates_and_styling(self):
        config = {"language": "en", "brain_import_templates": True, "brain_import_css": True}
        result = self.i18n.format_chat_context_message(
            config,
            context="Field [Front]\nHi",
            request="Split?",
            templates="[CARD TYPE 1 NAME] Basic\n[FRONT TEMPLATE]\n{{Front}}",
            styling=".card { color: red; }",
        )
        self.assertIn("[CARD TEMPLATES]", result)
        self.assertIn("[NOTE TYPE STYLING]", result)
        self.assertIn("{{Front}}", result)
        self.assertIn(".card { color: red; }", result)

    def test_format_chat_context_message_uses_minimal_custom_wrapper(self):
        config = {
            "language": "en",
            "brain_import_templates": True,
            "prompt_chat_context_sections": {
                "context": "Note:\n{{context}}",
                "templates": "",
                "request": "Ask: {{request}}",
            },
        }
        result = self.i18n.format_chat_context_message(
            config,
            context="ctx",
            request="req",
            templates="tmpl-block",
        )
        self.assertEqual(result, "Note:\nctx\n\nAsk: req")

    def test_apply_wrapper_placeholders_does_not_expand_inside_values(self):
        templates = "[CARD TYPE 1 NAME] Basic\n[FRONT TEMPLATE]\n{{Front}}"
        context = "Mention {templates} once in a field."
        prefix = "[FULL NOTE CONTEXT TO ANALYZE]\n{{context}}"
        rendered = self.wrapper.apply_wrapper_placeholders(
            prefix,
            context=context,
            request="Split?",
            templates=templates,
            styling=".card { color: red; }",
        )
        self.assertEqual(rendered.count("[CARD TYPE 1 NAME]"), 0)
        self.assertIn("Mention {templates} once in a field.", rendered)

    def test_apply_wrapper_placeholders_does_not_duplicate_templates_block(self):
        templates = "[CARD TYPE 1 NAME] Basic\n[FRONT TEMPLATE]\n{{Front}}"
        prefix = "[CARD TEMPLATES]\n{{templates}}"
        rendered = self.wrapper.apply_wrapper_placeholders(
            prefix,
            context="",
            request="",
            templates=templates,
            styling="",
        )
        self.assertEqual(rendered.count("[CARD TYPE 1 NAME]"), 1)

    def test_format_chat_context_message_does_not_duplicate_templates_on_repeat(self):
        config = {"language": "en", "brain_import_templates": True, "brain_import_css": True}
        templates = "[CARD TYPE 1 NAME] Basic\n[FRONT TEMPLATE]\n{{Front}}"
        styling = ".card { color: red; }"
        context = "Field [Front]\nHello"
        for _ in range(2):
            result = self.i18n.format_chat_context_message(
                config,
                context=context,
                request="Split?",
                templates=templates,
                styling=styling,
            )
            self.assertEqual(result.count("[CARD TYPE 1 NAME]"), 1)
            self.assertEqual(result.count("[HOW TO READ ANKI CARD TEMPLATES AND STYLING]"), 1)

    def test_format_chat_context_message_includes_templates_format_guide(self):
        config = {"language": "en", "brain_import_templates": True}
        result = self.i18n.format_chat_context_message(
            config,
            context="ctx",
            request="req",
            templates="[FRONT TEMPLATE]\n{{Front}}",
        )
        self.assertIn("[HOW TO READ ANKI CARD TEMPLATES AND STYLING]", result)
        self.assertLess(result.index("ctx"), result.index("[HOW TO READ ANKI"))
        self.assertLess(result.index("[HOW TO READ ANKI"), result.index("{{Front}}"))
        self.assertLess(result.index("{{Front}}"), result.index("req"))

    def test_format_chat_context_message_omits_format_guide_without_templates(self):
        config = {"language": "en"}
        result = self.i18n.format_chat_context_message(
            config,
            context="ctx",
            request="req",
        )
        self.assertNotIn("[HOW TO READ ANKI CARD TEMPLATES AND STYLING]", result)

    def test_effective_card_templates_format_prompt(self):
        config = {"language": "en"}
        text = self.i18n.effective_card_templates_format_prompt(config)
        self.assertIn("Card types", text)
        self.assertIn("{{Front}}", text)

    def test_build_optimize_prompt_inspection(self):
        prompt_inspection = _load_addon_module("prompt_inspection")
        config = {"language": "en", "dynamic_instructions": "Rule A"}
        inspection = prompt_inspection.build_optimize_prompt_inspection(config)
        self.assertEqual(inspection.purpose, "optimize")
        formula = inspection.formula_text(config)
        self.assertIn("System instructions", formula)
        self.assertIn("Dynamic rules", formula)
        self.assertIn("User message prefix", formula)
        full = inspection.full_text(config)
        self.assertIn("Rule A", full)

    def test_chat_session_config_fingerprint(self):
        prompt_inspection = _load_addon_module("prompt_inspection")
        base = {"language": "en", "model_chat": "gemini-2.5-flash"}
        fp1 = prompt_inspection.chat_session_config_fingerprint(base)
        fp2 = prompt_inspection.chat_session_config_fingerprint(dict(base))
        self.assertEqual(fp1, fp2)
        changed = dict(base)
        changed["temperature_chat"] = 0.9
        self.assertTrue(
            prompt_inspection.chat_session_config_changed(fp1, changed)
        )

    def test_build_chat_prompt_inspection(self):
        prompt_inspection = _load_addon_module("prompt_inspection")
        config = {"language": "en", "max_history_turns": 10}
        inspection = prompt_inspection.build_chat_prompt_inspection(
            config,
            history=[{"role": "user", "parts": [{"text": "Hi"}]}],
            next_user_text="Next",
            outgoing_payload="Wrapped next",
        )
        formula = inspection.formula_text(config)
        self.assertIn("Chat history", formula)
        self.assertIn("Next user message", formula)
        self.assertIn("Wrapped next", inspection.full_text(config))
        self.assertIn("Wrapped next", inspection.plain_full_text(config))
        self.assertNotIn("Current draft in the input box", inspection.plain_full_text(config))

    def test_format_card_templates_block(self):
        card_templates = _load_addon_module("ui.card_templates")
        block = card_templates.format_card_templates_block(
            [
                card_templates.CardTemplateData(
                    name="Basic",
                    front="{{Front}}",
                    back="{{Back}}",
                )
            ],
            config={"language": "en"},
        )
        self.assertIn("[CARD TYPE 1 NAME] Basic", block)
        self.assertIn("[FRONT TEMPLATE]", block)
        self.assertIn("{{Front}}", block)

    def test_wrapper_section_missing_request_placeholder(self):
        fn = self.wrapper.wrapper_section_missing_placeholders
        self.assertFalse(fn("request", ""))
        self.assertFalse(fn("request", "[STUDENT REQUEST]\n{{request}}"))
        self.assertTrue(fn("request", "[STUDENT REQUEST]\n"))

    def test_wrapper_prefix_token_segments(self):
        tokens = _load_addon_module("wrapper_prefix_tokens")
        text = "[FULL NOTE CONTEXT TO ANALYZE]\n{{context}}"
        segments = tokens.parse_wrapper_prefix_segments(text, "context")
        self.assertEqual(
            segments,
            [("text", "[FULL NOTE CONTEXT TO ANALYZE]\n"), ("token", "context")],
        )
        self.assertEqual(tokens.serialize_wrapper_prefix_segments(segments), text)
        self.assertEqual(
            tokens.ensure_newline_before_wrapper_tag(
                "[FULL NOTE CONTEXT TO ANALYZE]{{context}}",
                "context",
            ),
            text,
        )
        self.assertTrue(tokens.wrapper_prefix_has_token(segments, "context"))
        self.assertEqual(tokens.wrapper_token_display_label("context"), "context")
        self.assertTrue(tokens.wrapper_prefix_requires_token("request"))
        self.assertFalse(tokens.wrapper_prefix_requires_token("format_guide"))

    def test_wrapper_prefix_token_segments_dedupe(self):
        tokens = _load_addon_module("wrapper_prefix_tokens")
        raw = tokens.parse_wrapper_prefix_segments(
            "Header\n{{context}} tail {{context}}",
            "context",
        )
        normalized = tokens.normalize_wrapper_prefix_segments(raw, "context")
        self.assertEqual(
            normalized,
            [("text", "Header\n"), ("token", "context"), ("text", " tail ")],
        )
        self.assertEqual(
            tokens.serialize_wrapper_prefix_segments(normalized),
            "Header\n{{context}} tail ",
        )
        no_token = tokens.normalize_wrapper_prefix_segments(
            tokens.parse_wrapper_prefix_segments("A{{context}}B{{context}}", "context"),
            "context",
            allow_token=False,
        )
        self.assertEqual(no_token, [("text", "AB")])

    def test_build_cache_safe_wrapper_omits_request(self) -> None:
        config = {"language": "en"}
        order, prefixes = self.i18n.effective_wrapper_layout(config)
        safe = self.wrapper.build_cache_safe_wrapper(
            config,
            section_order=order,
            section_prefixes=prefixes,
            cache_imported_note=False,
            cache_format_guide=False,
            cache_templates=True,
            cache_styling=True,
            context_content="Field A\nvalue",
            templates_content="tmpl",
            styling_content="css",
            format_guide=self.i18n.effective_card_templates_format_prompt(config),
        )
        self.assertIn("{{context}}", safe)
        self.assertNotIn("{{request}}", safe)
        self.assertNotIn("[STUDENT REQUEST]", safe)

    def test_build_cache_safe_wrapper_omits_context_when_note_cached(self) -> None:
        config = {"language": "en"}
        order, prefixes = self.i18n.effective_wrapper_layout(config)
        safe = self.wrapper.build_cache_safe_wrapper(
            config,
            section_order=order,
            section_prefixes=prefixes,
            cache_imported_note=True,
            cache_format_guide=False,
            cache_templates=False,
            cache_styling=False,
            context_content="Field A\nvalue",
            format_guide=self.i18n.effective_card_templates_format_prompt(config),
        )
        self.assertNotIn("[FULL NOTE CONTEXT TO ANALYZE]", safe)
        self.assertNotIn("{{request}}", safe)

    def test_format_chat_context_message_request_only_without_note(self) -> None:
        config = {"language": "en"}
        result = self.i18n.format_chat_context_message(
            config,
            context="",
            request="Just a question?",
            include_context=False,
        )
        self.assertIn("[STUDENT REQUEST]", result)
        self.assertIn("Just a question?", result)
        self.assertNotIn("[FULL NOTE CONTEXT TO ANALYZE]", result)

    def test_format_chat_context_message_omits_context_when_import_unchecked(self) -> None:
        config = {"language": "en"}
        result = self.i18n.format_chat_context_message(
            config,
            context="Field [Front]\nHi",
            request="Explain this?",
            include_context=False,
        )
        self.assertIn("[STUDENT REQUEST]", result)
        self.assertIn("Explain this?", result)
        self.assertNotIn("Field [Front]", result)
        self.assertNotIn("[FULL NOTE CONTEXT TO ANALYZE]", result)

    def test_format_chat_context_message_omits_context_block_when_empty(self) -> None:
        result = self.i18n.format_chat_context_message(
            {"language": "en"},
            context="",
            request="Hi?",
            include_context=True,
        )
        self.assertIn("[STUDENT REQUEST]", result)
        self.assertIn("Hi?", result)
        self.assertNotIn("[FULL NOTE CONTEXT TO ANALYZE]", result)

    def test_build_live_request_message_uses_request_section(self) -> None:
        config = {"language": "en"}
        order, prefixes = self.i18n.effective_wrapper_layout(config)
        live = self.wrapper.build_live_request_message(
            config,
            section_order=order,
            section_prefixes=prefixes,
            request="My question?",
        )
        self.assertIn("[STUDENT REQUEST]", live)
        self.assertIn("My question?", live)
        self.assertNotIn("{{context}}", live)

    def test_wrapper_missing_import_placeholders(self):
        config = {"language": "en", "brain_import_templates": True, "brain_import_css": True}
        missing = self.wrapper.wrapper_missing_import_placeholders(
            {
                "context": "Note:\n{{context}}",
                "request": "Q: {{request}}",
                "templates": "[TEMPLATES]\n",
                "styling": "[STYLE]\n",
            },
            config,
        )
        self.assertEqual(missing, ["templates", "styling"])

    def test_build_wrapper_preview_respects_import_settings(self):
        wrapper = self.i18n.build_wrapper_preview({"language": "en"})
        self.assertIn("…", wrapper)
        self.assertIn("[STUDENT REQUEST]", wrapper)

    def test_is_builtin_wrapper_layout(self):
        self.assertTrue(self.i18n.is_builtin_wrapper_layout({"language": "en"}))

    def test_estimate_chat_request_chars(self):
        token_estimate = _load_addon_module("token_estimate")
        self.assertEqual(token_estimate.estimate_text_tokens(""), 0)
        self.assertEqual(token_estimate.estimate_text_tokens("abcd"), 1)
        self.assertEqual(
            token_estimate.estimate_chat_request_chars(
                "message",
                [{"role": "user", "parts": [{"text": "history"}]}],
            ),
            14,
        )
        self.assertEqual(
            token_estimate.estimate_chat_request_chars(
                "message",
                [{"role": "user", "parts": [{"text": "history"}]}],
                system_instruction="system",
            ),
            20,
        )

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
        self.assertIn("chat-code-copy", html_out)
        self.assertIn("⧉", html_out)
        self.assertNotIn(">Copy<", html_out)
        self.assertNotIn("chat-html-endcap", html_out)
        self.assertIn("class='chat-code-block", html_out)
        self.assertEqual(store["t1-0"], "<b>Hi</b>")

    def test_format_reply_legacy_endcap(self):
        html_out = self.fmt.format_gemini_reply_html(
            "Hello",
            {},
            "t1",
            config={"language": "en"},
            endcap=True,
        )
        self.assertIn("chat-html-endcap", html_out)

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

    def test_format_reply_preserves_inline_math_delimiters_through_markdown(self):
        text = r"The formula \(E=mc^2\) is famous."
        html_out = self.fmt.format_gemini_reply_html(
            text,
            {},
            "t1",
            config={"language": "en"},
        )
        self.assertIn(r"\(E=mc^2\)", html_out)

    def test_format_reply_preserves_display_math_delimiters_through_markdown(self):
        text = (
            "Integral:\n"
            r"\[\int_0^\infty e^{-x^2}\, dx = \frac{\sqrt{\pi}}{2}\]"
        )
        html_out = self.fmt.format_gemini_reply_html(
            text,
            {},
            "t1",
            config={"language": "en"},
        )
        self.assertIn(r"\[\int_0^\infty", html_out)
        self.assertIn(r"\frac{\sqrt{\pi}}{2}\]", html_out)

    def test_format_reply_preserves_matrix_line_breaks_in_display_math(self):
        text = (
            r"\[\mathbf{A} = \begin{pmatrix}"
            r"a & b \\"
            r"c & d"
            r"\end{pmatrix}\]"
        )
        html_out = self.fmt.format_gemini_reply_html(
            text,
            {},
            "t1",
            config={"language": "en"},
        )
        self.assertIn(r"a & b \\", html_out)

    def test_short_reply_and_user_message_html_for_chat_lines(self):
        """Full-document chat omits per-reply endcaps; user lines never include them."""
        reply = self.fmt.format_gemini_reply_html(
            "You're welcome! I'm glad I could help.",
            {},
            "r1",
            config={"language": "en"},
        )
        user = "<br><b class='chat-label-you'>You:</b> Thank you"
        self.assertNotIn("chat-hr", user)
        self.assertNotIn("chat-html-endcap", user)
        self.assertNotIn("<hr", user.lower())
        self.assertNotIn("chat-html-endcap", reply)
        self.assertNotIn("chat-hr", reply)

    def test_split_streaming_reply_closed_bold(self):
        safe, tail = self.fmt.split_streaming_reply("Hello **world**!")
        self.assertEqual(safe, "Hello **world**!")
        self.assertEqual(tail, "")

    def test_split_streaming_reply_unclosed_bold(self):
        safe, tail = self.fmt.split_streaming_reply("Hello **wor")
        self.assertEqual(safe, "Hello ")
        self.assertEqual(tail, "**wor")

    def test_split_streaming_reply_open_fence(self):
        safe, tail = self.fmt.split_streaming_reply("Intro\n```python\nprint(1)")
        self.assertEqual(safe, "Intro\n")
        self.assertEqual(tail, "```python\nprint(1)")

    def test_split_streaming_reply_closed_fence_then_prose(self):
        text = "Text\n```\nline\n```\nMore **ok**"
        safe, tail = self.fmt.split_streaming_reply(text)
        self.assertEqual(safe, text)
        self.assertEqual(tail, "")

    def test_format_streaming_reply_renders_safe_prefix(self):
        store: dict[str, str] = {}
        html_out = self.fmt.format_streaming_reply_html(
            "Hello **world** and **par",
            store,
            "s1",
            config={"language": "en"},
        )
        self.assertIn("chat-prose", html_out)
        self.assertIn("chat-stream-text", html_out)
        self.assertIn("**par", html_out)
        self.assertNotIn("**world**", html_out)


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

    def test_strong_label_html(self):
        html_out = self.theme.strong_label_html("Wrapper text")
        self.assertIn("Wrapper text", html_out)
        self.assertIn(self.theme._LIGHT.text_strong, html_out)

    def test_field_name_label_html_escapes_name(self):
        html_out = self.theme.field_name_label_html("Text <field>")
        self.assertIn("Text &lt;field&gt;", html_out)
        self.assertIn(self.theme._LIGHT.text_strong, html_out)


class TestSvgIcons(unittest.TestCase):
    def test_stop_sign_svg_exists(self):
        addon_dir = Path(__file__).resolve().parent.parent
        path = addon_dir / "ui" / "icons" / "stop.svg"
        self.assertTrue(path.is_file(), msg=str(path))

    def test_priority_sign_svg_exists(self):
        addon_dir = Path(__file__).resolve().parent.parent
        path = addon_dir / "ui" / "icons" / "priority.svg"
        self.assertTrue(path.is_file(), msg=str(path))

    def test_plus_svg_exists(self):
        addon_dir = Path(__file__).resolve().parent.parent
        path = addon_dir / "ui" / "icons" / "plus.svg"
        self.assertTrue(path.is_file(), msg=str(path))

    def test_brain_svg_exists(self):
        addon_dir = Path(__file__).resolve().parent.parent
        path = addon_dir / "ui" / "icons" / "brain.svg"
        self.assertTrue(path.is_file(), msg=str(path))

    def test_lens_svg_exists(self):
        addon_dir = Path(__file__).resolve().parent.parent
        path = addon_dir / "ui" / "icons" / "lens.svg"
        self.assertTrue(path.is_file(), msg=str(path))

    def test_pencil_svg_exists(self):
        addon_dir = Path(__file__).resolve().parent.parent
        path = addon_dir / "ui" / "icons" / "pencil.svg"
        self.assertTrue(path.is_file(), msg=str(path))

    def test_barred_brain_svg_exists(self):
        addon_dir = Path(__file__).resolve().parent.parent
        path = addon_dir / "ui" / "icons" / "barred_brain.svg"
        self.assertTrue(path.is_file(), msg=str(path))

    def test_chat_svg_exists(self):
        addon_dir = Path(__file__).resolve().parent.parent
        path = addon_dir / "ui" / "icons" / "chat.svg"
        self.assertTrue(path.is_file(), msg=str(path))

    def test_settings_svg_exists(self):
        addon_dir = Path(__file__).resolve().parent.parent
        path = addon_dir / "ui" / "icons" / "settings.svg"
        self.assertTrue(path.is_file(), msg=str(path))

    def test_undo_svg_exists(self):
        addon_dir = Path(__file__).resolve().parent.parent
        path = addon_dir / "ui" / "icons" / "undo.svg"
        self.assertTrue(path.is_file(), msg=str(path))

    def test_robot_svg_exists(self):
        addon_dir = Path(__file__).resolve().parent.parent
        path = addon_dir / "ui" / "icons" / "robot.svg"
        self.assertTrue(path.is_file(), msg=str(path))

    def test_stop_circle_svg_exists(self):
        addon_dir = Path(__file__).resolve().parent.parent
        path = addon_dir / "ui" / "icons" / "stop_circle.svg"
        self.assertTrue(path.is_file(), msg=str(path))


class TestHelpIcons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.help_icons = _load_addon_module("ui.help_icons")

    def test_expand_help_icons_replaces_brain_token(self):
        original = self.help_icons._help_icon_html_by_key
        try:
            self.help_icons._help_icon_html_by_key = lambda: {
                "brain": '<img src="data:image/png;base64,test" />',
                "plus": '<img src="data:image/png;base64,plus" />',
            }
            out = self.help_icons.expand_help_icons(
                "({icon:brain} = included, {icon:plus} New conversation)"
            )
            self.assertIn('<img src="data:image/png;base64,test" />', out)
            self.assertIn('<img src="data:image/png;base64,plus" />', out)
            self.assertNotIn("{icon:brain}", out)
            self.assertNotIn("{icon:plus}", out)
        finally:
            self.help_icons._help_icon_html_by_key = original

    def test_chat_toolbar_help_icon_keys(self):
        self.assertEqual(
            set(self.help_icons.CHAT_TOOLBAR_HELP_ICON_KEYS),
            {
                "brain",
                "barred_brain",
                "pencil",
                "eye",
                "lens",
                "plus",
                "stop",
                "priority",
            },
        )

    def test_help_icon_target_physical_pixels_matches_display_without_screen(self):
        self.assertEqual(self.help_icons._help_icon_target_physical_pixels(16), 16)

    def test_help_icon_render_pixels_supersamples_target_physical_size(self):
        physical = self.help_icons._help_icon_target_physical_pixels(16)
        pixels = self.help_icons._help_icon_render_pixels(16)
        self.assertGreaterEqual(
            pixels,
            round(physical * self.help_icons.MIN_HELP_ICON_SUPERSAMPLE),
        )


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
        _, combo = self.ms.create_model_selector(
            None,
            current="gemini-custom-preview",
            default="gemini-2.5-flash-lite",
            config={"language": "en"},
        )
        self.assertEqual(self.ms.model_selector_value(combo), "gemini-custom-preview")

    def test_update_model_selector_choices_merges_api_models(self):
        _, combo = self.ms.create_model_selector(
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


class TestNoteContextFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields = _load_addon_module("note_context_fields")

    def test_format_note_context_skips_empty_by_default(self):
        config = {"language": "en"}
        text = self.fields.format_note_context(
            [("Front", "Hello"), ("Back", "World")],
            config,
        )
        self.assertIn("Field [Front]\nHello", text)
        self.assertIn("Field [Back]\nWorld", text)
        self.assertEqual(self.fields.format_note_context([("Front", "  ")], config), "")

    def test_format_note_context_includes_empty_when_enabled(self):
        config = {"language": "en", "chat_send_empty_fields": True}
        text = self.fields.format_note_context([("Front", ""), ("Back", "Hi")], config)
        self.assertIn("Field [Front]\n(This field is empty)", text)
        self.assertIn("Field [Back]\nHi", text)

    def test_fields_for_note_preview_shows_placeholder_when_enabled(self):
        config = {"language": "en", "chat_send_empty_fields": True}
        preview = self.fields.fields_for_note_preview(
            [("Front", ""), ("Back", "Hi")],
            config,
        )
        self.assertEqual(preview, [("Front", "(This field is empty)"), ("Back", "Hi")])

    def test_fields_for_note_preview_keeps_empty_values_when_disabled(self):
        config = {"language": "en"}
        preview = self.fields.fields_for_note_preview(
            [("Front", ""), ("Back", "Hi")],
            config,
        )
        self.assertEqual(preview, [("Front", ""), ("Back", "Hi")])


class TestNoteMathPreview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preview = _load_addon_module("ui.note_math_preview")

    def test_build_note_preview_body_includes_math_and_field_name(self):
        body = self.preview.build_note_preview_body(
            [("Front", r"<p>Energy: \(E=mc^2\)</p>")],
        )
        self.assertIn("Front", body)
        self.assertIn(r"\(E=mc^2\)", body)
        self.assertIn('id="addon-note-preview"', body)
        self.assertIn("addon-note-preview-loading", body)
        self.assertIn("preview-pending", body)

    def test_build_note_preview_body_includes_loading_message(self):
        body = self.preview.build_note_preview_body(
            [("Front", "Hello")],
            loading_message="Rendering preview…",
        )
        self.assertIn("Rendering preview…", body)
        self.assertIn("addon-note-preview-loading", body)
        self.assertIn("preview-loading-label", body)

    def test_build_note_preview_body_empty_message_has_no_loading_shell(self):
        body = self.preview.build_note_preview_body([], empty_message="Nothing here")
        self.assertIn("Nothing here", body)
        self.assertIn("empty-preview", body)
        self.assertNotIn("addon-note-preview-loading", body)

    def test_build_note_preview_body_includes_preamble_before_fields(self):
        preamble = (
            '<div style="display: none;">\n\\(\n'
            r"\newcommand{\R}{\mathbb{R}}" + "\n\\)\n</div>"
        )
        body = self.preview.build_note_preview_body(
            [("Front", r"\(\R\)")],
            mathjax_preamble=preamble,
        )
        self.assertIn("mathjax-preamble", body)
        self.assertIn(r"\newcommand{\R}{\mathbb{R}}", body)
        self.assertLess(body.index("mathjax-preamble"), body.index("Front"))

    def test_extract_template_preamble_sections_finds_hidden_newcommand_block(self):
        template = (
            '<div style="display: none;">\n\\(\n'
            r"\newcommand{\R}{\mathbb{R}}" + "\n"
            r"\newcommand{\C}{\mathbb{C}}" + "\n\\)\n</div>\n"
            "{{Front}}"
        )
        sections = self.preview.extract_template_preamble_sections(template)
        self.assertEqual(len(sections), 1)
        self.assertIn(r"\newcommand{\R}{\mathbb{R}}", sections[0])
        self.assertIn("display: none", sections[0])

    def test_extract_template_preamble_sections_finds_mathjax_script(self):
        template = (
            "<script>\n"
            "MathJax.config.tex['macros'] = { R: '{\\\\mathbb{R}}' };\n"
            "</script>\n{{Front}}"
        )
        sections = self.preview.extract_template_preamble_sections(template)
        self.assertEqual(len(sections), 1)
        self.assertIn("MathJax.config", sections[0])

    def test_resolve_mathjax_preview_preamble_prefers_settings_when_no_notetype(self):
        preamble = self.preview.resolve_mathjax_preview_preamble(
            {"mathjax_preview_preamble": "<div>fallback</div>"},
            notetype_id=None,
        )
        self.assertEqual(preamble, "<div>fallback</div>")

    def test_build_note_preview_body_empty_message(self):
        body = self.preview.build_note_preview_body([], empty_message="Nothing here")
        self.assertIn("Nothing here", body)
        self.assertIn("empty-preview", body)

    def test_note_preview_typeset_js_reveals_after_typeset(self):
        script = self.preview.note_preview_typeset_js()
        self.assertIn("addon-note-preview-loading", script)
        self.assertIn("preview-pending", script)
        self.assertIn("preview-ready", script)
        self.assertIn("scheduleReveal", script)
        self.assertIn("setTimeout", script)
        self.assertIn(str(self.preview.NOTE_PREVIEW_LOADING_MIN_MS), script)
        self.assertIn("MathJax.typesetPromise", script)

    def test_web_math_preview_available_false_without_anki(self):
        self.assertFalse(self.preview.web_math_preview_available())

    def test_mathjax_typeset_js_targets_root_element(self):
        script = self.preview.mathjax_typeset_js("addon-chat-log")
        self.assertIn("addon-chat-log", script)
        self.assertIn("MathJax.typesetPromise", script)


class TestChatMathLog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chat_math = _load_addon_module("ui.chat_math_log")

    def test_chat_math_log_available_false_without_anki(self):
        self.assertFalse(self.chat_math.chat_math_log_available())


class TestNoteFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.note_fields = _load_addon_module("ui.note_fields")

    def test_strip_field_html_edges(self):
        fn = self.note_fields.strip_field_html_edges
        self.assertEqual(fn("<p>Hi</p><br>"), "<p>Hi</p>")
        self.assertEqual(fn("  <div>Text</div>  "), "<div>Text</div>")

    def test_field_inner_html_renders_inline_tags(self):
        fn = self.note_fields.field_inner_html
        self.assertEqual(
            fn("Definisci la struttura algebrica di <b>gruppo</b>."),
            "Definisci la struttura algebrica di <b>gruppo</b>.",
        )
        self.assertEqual(fn("plain text only"), "plain text only")
        self.assertEqual(fn("x < 5"), "x &lt; 5")
        self.assertEqual(fn("line one\nline two"), "line one<br>line two")

    def test_field_inner_html_closes_unclosed_markup(self):
        fn = self.note_fields.field_inner_html
        self.assertTrue(fn("<div><p>Hello").endswith("</p></div>"))


class TestChatLogRenderer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = _load_addon_module("ui.chat_log_renderer")
        cls.messages = _load_addon_module("ui.chat_messages")

    def test_render_chat_document_wraps_messages(self):
        html = self.renderer.render_chat_document(
            [
                self.messages.ChatMessage(
                    label_class="chat-label-you",
                    label="You",
                    body_html="Hi",
                ),
                self.messages.ChatMessage(
                    label_class="chat-label-gemini",
                    label="Gemini",
                    body_html="Hello",
                ),
            ]
        )
        self.assertIn("chat-message-wrap", html)
        self.assertIn('id="addon-chat-log"', html)
        self.assertIn("chat-label-you", html)
        self.assertIn("chat-label-gemini", html)
        self.assertNotIn("chat-html-endcap", html)


class TestChatExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chat_export = _load_addon_module("ui.chat_export")
        cls.messages = _load_addon_module("ui.chat_messages")

    def test_format_chat_messages_as_text(self):
        text = self.chat_export.format_chat_messages_as_text(
            [
                self.messages.ChatMessage(
                    label_class="chat-label-you",
                    label="You",
                    body_html="Hello<br>world",
                ),
                self.messages.ChatMessage(
                    label_class="chat-label-gemini",
                    label="Gemini",
                    body_html="Hi &amp; bye",
                ),
            ]
        )
        self.assertIn("You:\nHello", text)
        self.assertIn("world", text)
        self.assertIn("Gemini:\nHi & bye", text)

    def test_format_chat_export_text_includes_metadata_header(self):
        from datetime import datetime

        config = {
            "language": "en",
            "model_chat": "gemini-2.5-flash",
            "temperature_chat": 0.2,
            "thinking_budget_chat": -1,
            "chat_streaming": True,
            "max_history_turns": 10,
        }
        text = self.chat_export.format_chat_export_text(
            [
                self.messages.ChatMessage(
                    label_class="chat-label-gemini",
                    label="Gemini",
                    body_html="Hello",
                ),
            ],
            config,
            api_history=[
                {"role": "user", "parts": [{"text": "Hi"}]},
                {"role": "model", "parts": [{"text": "Hello"}]},
            ],
            exported_at=datetime(2026, 7, 11, 23, 45, 10),
        )
        self.assertIn("Anki AI chat export", text)
        self.assertIn("Exported at: 2026-07-11 23:45:10", text)
        self.assertIn("Model: gemini-2.5-flash", text)
        self.assertIn("Temperature: 0.2", text)
        self.assertIn("---", text)
        self.assertIn("Gemini:\nHello", text)

    def test_default_chat_export_filename(self):
        from datetime import datetime

        stamp = datetime(2026, 7, 11, 23, 45, 10)
        self.assertEqual(
            self.chat_export.default_chat_export_filename(now=stamp),
            "anki-ai-chat-2026-07-11-234510.txt",
        )

    def test_default_chat_download_directory_uses_documents(self):
        path = self.chat_export.default_chat_download_directory()
        self.assertEqual(path.name, "Documents")


class TestHtmlUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html_utils = _load_addon_module("ui.html_utils")

    def test_closing_tags_suffix_balances_tables_and_divs(self):
        fn = self.html_utils.closing_tags_suffix
        self.assertEqual(fn("<div><table><tr><td>x"), "</td></tr></table></div>")
        self.assertEqual(fn("<p>Hi"), "</p>")
        self.assertEqual(fn("<div><p>Hi</p>"), "</div>")

    def test_html_endcap_uses_taller_spacer(self):
        endcap = self.html_utils.html_endcap()
        self.assertIn("line-height:4px", endcap)
        self.assertIn("chat-html-endcap", endcap)


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
        self.assertFalse(defaults["brain_import_templates"])
        self.assertFalse(defaults["brain_import_css"])
        self.assertEqual(defaults["chat_payload_warning_chars"], 12000)

    def test_apply_config_normalization_resets_wrapper_on_version_bump(self):
        stored = {
            "config_version": 1,
            "language": "en",
            "prompt_chat_context_sections": {"context": "Custom:\n{{context}}"},
            "prompt_chat_context_order": ["request", "context"],
            "prompt_card_templates_format": "Old guide",
        }
        merged = self.config._normalize_config(
            {**self.config.DEFAULT_CONFIG, **stored},
            stored,
        )
        self.assertEqual(merged["config_version"], self.config.CONFIG_VERSION)
        self.assertEqual(merged["prompt_chat_context_sections"], {})
        self.assertEqual(
            merged["prompt_chat_context_order"],
            self.config.DEFAULT_CONFIG["prompt_chat_context_order"],
        )
        self.assertEqual(merged["prompt_card_templates_format"], "")
        self.assertNotIn("model", merged)
        self.assertNotIn("thinking_budget", merged)

    def test_apply_config_normalization_strips_obsolete_keys(self):
        stored = {
            "config_version": self.config.CONFIG_VERSION,
            "model": "old-model",
            "thinking_budget": 512,
            "prompt_cache_min_tokens": 2048,
            "prompt_cache_import_note_default": "cancel",
        }
        merged = self.config._normalize_config(
            {**self.config.DEFAULT_CONFIG, **stored},
            stored,
        )
        self.assertNotIn("model", merged)
        self.assertNotIn("thinking_budget", merged)
        self.assertNotIn("prompt_cache_min_tokens", merged)
        self.assertNotIn("prompt_cache_import_note_default", merged)

    def test_apply_config_normalization_migrates_legacy_prompt_cache_min_chars(self):
        for stored_value in (8189, "8189"):
            with self.subTest(stored_value=stored_value):
                stored = {
                    "config_version": self.config.CONFIG_VERSION,
                    "prompt_cache_min_chars": stored_value,
                }
                merged = self.config._normalize_config(
                    {**self.config.DEFAULT_CONFIG, **stored},
                    stored,
                )
                self.assertEqual(
                    merged["prompt_cache_min_chars"],
                    _load_addon_module("constants").DEFAULT_PROMPT_CACHE_MIN_CHARS,
                )

    def test_restorable_settings_cover_defaults(self):
        self.assertLessEqual(
            set(self.config.RESTORABLE_SETTING_KEYS),
            set(self.config.DEFAULT_CONFIG.keys()),
        )
        self.assertEqual(
            set(self.config.RESTORABLE_SETTING_KEYS),
            set(self.config.DEFAULT_CONFIG.keys())
            - {
                "config_version",
                "chat_send_empty_fields",
                "chat_modify_prompt_before_send",
                "optimize_modify_prompt_before_send",
                "suppress_default_system_instruction_warning",
                "suppress_api_key_restore_warning",
                "suppress_settings_unsaved_close_warning",
                "suppress_settings_save_confirm_warning",
                "suppress_settings_cancel_confirm_warning",
                "suppress_prompt_cache_created_optimize_notice",
                "suppress_chat_new_conversation_confirm_warning",
                "suppress_prompt_cache_recreate_confirm",
                "suppress_settings_save_cache_clear_warning",
                "suppress_new_conversation_cache_warning",
                "suppress_import_note_cache_warning",
                "suppress_prompt_cache_custom_text_load_confirm",
                "suppress_prompt_cache_delete_orphans_confirm",
                "prompt_cache_change_ttl_seconds",
                "prompt_cache_recreate_default",
                "prompt_cache_new_conversation_cache_default",
                "prompt_cache_custom_text_presets",
                "prompt_cache_active_preset_id",
                "settings_show_text_newlines",
                "dev_mock_mode",
            },
        )

    def test_setting_help_keys_cover_all_settings(self):
        self.assertEqual(set(self.config.SETTING_HELP_KEYS.keys()), set(self.config.RESTORABLE_SETTING_KEYS))

    def test_setting_help_strings_exist_in_i18n(self):
        i18n = _load_addon_module("i18n")
        missing = [
            self.config.SETTING_HELP_KEYS[key]
            for key in self.config.RESTORABLE_SETTING_KEYS
            if self.config.SETTING_HELP_KEYS[key] not in i18n._STRINGS
        ]
        self.assertEqual(missing, [])

    def test_default_config_value(self):
        self.assertEqual(self.config.default_config_value("model_optimize"), "gemini-2.5-flash-lite")
        self.assertEqual(self.config.default_config_value("brain_import_message"), "")
        self.assertEqual(self.config.default_config_value("max_history_turns"), 10)
        self.assertEqual(self.config.default_config_value("prompt_optimize_user"), "")
        self.assertEqual(self.config.default_config_value("prompt_chat_addon"), "")
        self.assertEqual(self.config.default_config_value("prompt_dynamic_rules_prefix"), "")
        self.assertEqual(self.config.default_config_value("prompt_chat_context"), "")
        self.assertEqual(self.config.default_config_value("prompt_card_templates_format"), "")
        self.assertEqual(self.config.default_config_value("mathjax_preview_preamble"), "")

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

    def test_default_config_warning_preferences(self):
        defaults = self.config.DEFAULT_CONFIG
        self.assertFalse(defaults["suppress_settings_unsaved_close_warning"])
        self.assertTrue(defaults["suppress_settings_save_confirm_warning"])
        self.assertTrue(defaults["suppress_settings_cancel_confirm_warning"])
        self.assertTrue(defaults["suppress_chat_new_conversation_confirm_warning"])

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

    def test_stream_gemini_cancelled(self):
        checks = [0]

        def should_cancel() -> bool:
            checks[0] += 1
            return checks[0] > 1

        response = MagicMock(ok=True, status_code=200, text="")
        response.iter_lines.return_value = [
            b'data: {"candidates":[{"content":{"parts":[{"text":"Hello"}]}}]}',
            b"",
        ]

        with patch.object(self.gc.requests, "post", return_value=response):
            with self.assertRaises(self.gc.GeminiCancelledError):
                self.gc.stream_gemini(
                    config=self._base_config(),
                    user_text="ping",
                    should_cancel=should_cancel,
                )

    def test_stream_gemini_rate_limit_not_retried(self):
        response = MagicMock(ok=False, status_code=429, text="Too Many Requests")
        response.headers = {}
        with patch.object(self.gc.requests, "post", return_value=response) as post:
            with self.assertRaises(self.gc.GeminiRateLimitError):
                self.gc.stream_gemini(config=self._base_config(), user_text="ping")
        self.assertEqual(post.call_count, 1)

    def test_stream_gemini_rate_limit_in_sse_payload(self):
        response = MagicMock(ok=True, status_code=200, text="")
        response.headers = {}
        response.iter_lines.return_value = [
            b'data: {"error":{"code":429,"status":"RESOURCE_EXHAUSTED","message":"Quota"}}',
            b"",
        ]
        with patch.object(self.gc.requests, "post", return_value=response):
            with self.assertRaises(self.gc.GeminiRateLimitError):
                self.gc.stream_gemini(config=self._base_config(), user_text="ping")

    def test_stream_gemini_closed_response_is_cancelled(self):
        cancelled = {"value": False}

        def should_cancel() -> bool:
            return cancelled["value"]

        response = MagicMock(ok=True, status_code=200, text="")

        def iter_lines(**kwargs):
            cancelled["value"] = True
            raise AttributeError("'NoneType' object has no attribute 'read'")

        response.iter_lines.side_effect = iter_lines

        with patch.object(self.gc.requests, "post", return_value=response):
            with self.assertRaises(self.gc.GeminiCancelledError):
                self.gc.stream_gemini(
                    config=self._base_config(),
                    user_text="ping",
                    should_cancel=should_cancel,
                )

    def test_call_gemini_cancellable_uses_stream(self):
        response = MagicMock(ok=True, status_code=200, text="")
        response.iter_lines.return_value = [
            b'data: {"candidates":[{"content":{"parts":[{"text":"OK"}]}}]}',
            b"",
        ]
        with patch.object(self.gc.requests, "post", return_value=response) as post:
            result = self.gc.call_gemini(
                config=self._base_config(),
                user_text="ping",
                should_cancel=lambda: False,
            )
        self.assertEqual(result, "OK")
        self.assertIn("alt=sse", post.call_args.args[0])


class TestPromptCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pc = _load_addon_module("prompt_cache")

    def setUp(self) -> None:
        self.pc.clear_prompt_cache_store()

    def test_bundle_disabled_by_default(self) -> None:
        bundle = self.pc.build_prompt_cache_bundle({"language": "en"}, purpose="chat")
        self.assertIsNone(bundle)

    def test_bundle_respects_minimum_chars(self) -> None:
        config = {
            "language": "en",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 199_997,
            "prompt_cache_segments": {"system_instruction": True},
            "system_instruction": "Short rules",
        }
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat")
        self.assertIsNone(bundle)

    def test_bundle_includes_enabled_system_instruction(self) -> None:
        config = {
            "language": "en",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {"system_instruction": True},
            "system_instruction": "X" * 9000,
        }
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat")
        self.assertIsNotNone(bundle)
        self.assertIn("system_instruction", bundle.enabled_segment_ids)
        self.assertIn("X" * 100, bundle.cached_system_text)

    def test_prompt_cache_segments_auto_enables_context_wrapper(self) -> None:
        config = {
            "prompt_cache_segments": {
                "imported_note": True,
                "card_templates": False,
                "notetype_css": False,
                "context_wrapper": False,
            }
        }
        segments = self.pc.prompt_cache_segments(config)
        self.assertTrue(segments["context_wrapper"])
        segments_off = self.pc.prompt_cache_segments(
            {"prompt_cache_segments": {"imported_note": False}}
        )
        self.assertFalse(segments_off["context_wrapper"])

    def test_bundle_omits_context_wrapper_when_note_is_cached_segment(self) -> None:
        config = {
            "language": "en",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {
                "system_instruction": True,
                "imported_note": True,
            },
            "system_instruction": "X" * 9000,
        }
        session = self.pc.PromptCacheSessionContext(
            note_context="Field A\nvalue",
            include_note_context=True,
        )
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat", session=session)
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertNotIn("context_wrapper", bundle.enabled_segment_ids)
        self.assertIn("Field A", bundle.cached_system_text)
        self.assertNotIn("[STUDENT REQUEST]", bundle.cached_system_text)
        self.assertNotIn("{{request}}", bundle.cached_system_text)

    def test_bundle_includes_cache_safe_wrapper_when_templates_cached(self) -> None:
        config = {
            "language": "en",
            "brain_import_templates": True,
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {
                "system_instruction": True,
                "imported_note": False,
                "card_templates": True,
            },
            "system_instruction": "X" * 9000,
        }
        session = self.pc.PromptCacheSessionContext(
            note_context="Field A\nvalue",
            templates_block="[FRONT TEMPLATE]\n{{Front}}",
            include_note_context=True,
        )
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat", session=session)
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertIn("context_wrapper", bundle.enabled_segment_ids)
        self.assertIn("card_templates", bundle.enabled_segment_ids)
        self.assertIn("{{context}}", bundle.cached_system_text)
        self.assertNotIn("{{request}}", bundle.cached_system_text)

    def test_live_chat_payload_uses_request_only_without_note(self) -> None:
        config = {"language": "en"}
        session = self.pc.PromptCacheSessionContext(
            note_context="",
            include_note_context=False,
        )
        payload = self.pc.build_live_chat_payload(
            config,
            "My question?",
            session=session,
            bundle=None,
        )
        self.assertIn("[STUDENT REQUEST]", payload)
        self.assertIn("My question?", payload)

    def test_live_chat_payload_uses_plain_question_when_note_cached(self) -> None:
        config = {"language": "en", "prompt_cache_enabled": True, "prompt_cache_min_chars": 37}
        session = self.pc.PromptCacheSessionContext(
            note_context="Field A\nvalue",
            include_note_context=True,
        )
        bundle = self.pc.PromptCacheBundle(
            fingerprint="fp",
            cached_system_text="cached",
            cached_contents=[],
            live_system_text="",
            cached_char_count=6,
            estimated_cached_tokens=100,
            enabled_segment_ids=("imported_note", "context_wrapper"),
        )
        payload = self.pc.build_live_chat_payload(
            config,
            "My question?",
            session=session,
            bundle=bundle,
        )
        self.assertIn("My question?", payload)
        self.assertIn("[STUDENT REQUEST]", payload)
        self.assertNotIn("Field A", payload)

    def test_bundle_includes_format_guide_segment_when_enabled(self) -> None:
        config = {
            "language": "en",
            "brain_import_templates": True,
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {
                "system_instruction": True,
                "card_templates_format_guide": True,
            },
            "system_instruction": "X" * 9000,
        }
        session = self.pc.PromptCacheSessionContext(
            templates_block="[FRONT TEMPLATE]\n{{Front}}",
            include_note_context=True,
        )
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat", session=session)
        self.assertIsNotNone(bundle)
        self.assertIn("card_templates_format_guide", bundle.enabled_segment_ids)
        self.assertIn("[HOW TO READ ANKI CARD TEMPLATES AND STYLING]", bundle.cached_system_text)

    def test_live_chat_payload_omits_format_guide_when_cached(self) -> None:
        config = {
            "language": "en",
            "brain_import_templates": True,
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
        }
        session = self.pc.PromptCacheSessionContext(
            note_context="Field [Front]\nHello",
            templates_block="[FRONT TEMPLATE]\n{{Front}}",
            include_note_context=True,
        )
        bundle = self.pc.PromptCacheBundle(
            fingerprint="fp",
            cached_system_text="cached",
            cached_contents=[],
            live_system_text="",
            cached_char_count=6,
            estimated_cached_tokens=100,
            enabled_segment_ids=(
                "imported_note",
                "card_templates_format_guide",
                "card_templates",
            ),
        )
        payload = self.pc.build_live_chat_payload(
            config,
            "My question?",
            session=session,
            bundle=bundle,
        )
        self.assertNotIn("[HOW TO READ ANKI CARD TEMPLATES AND STYLING]", payload)
        self.assertNotIn("{{Front}}", payload)
        self.assertIn("My question?", payload)

    def test_optimize_bundle_uses_split_system_instruction(self) -> None:
        config = {
            "language": "en",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {"system_instruction": True},
            "system_instruction_shared": False,
            "system_instruction_optimize": "Optimize-only " + ("X" * 9000),
            "system_instruction_chat": "Chat-only " + ("Y" * 9000),
        }
        optimize_bundle = self.pc.build_prompt_cache_bundle(config, purpose="optimize")
        chat_bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat")
        self.assertIsNotNone(optimize_bundle)
        self.assertIsNotNone(chat_bundle)
        self.assertIn("Optimize-only", optimize_bundle.cached_system_text)
        self.assertNotIn("Chat-only", optimize_bundle.cached_system_text)
        self.assertIn("Chat-only", chat_bundle.cached_system_text)
        self.assertNotIn("Optimize-only", chat_bundle.cached_system_text)

    def test_ensure_prompt_cache_reports_created(self) -> None:
        config = {
            "language": "en",
            "api_key": "test-key",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {"system_instruction": True},
            "system_instruction": "X" * 9000,
        }
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat")
        self.assertIsNotNone(bundle)
        with patch.object(self.pc, "create_cached_content") as create, patch.object(
            self.pc, "cleanup_orphan_remote_caches"
        ), patch.object(self.pc, "delete_untracked_addon_caches"), patch.object(
            self.pc, "_verify_active_remote_cache", return_value=True
        ):
            create.return_value = self.pc.ActivePromptCache(
                name="cachedContents/abc",
                fingerprint=bundle.fingerprint,
                model="gemini-2.5-flash",
                purpose="chat",
                expire_at=9999999999.0,
                ttl_seconds=3600,
                cached_char_count=bundle.cached_char_count,
            )
            first = self.pc.ensure_prompt_cache(
                config=config,
                purpose="chat",
                bundle=bundle,
            )
            second = self.pc.ensure_prompt_cache(
                config=config,
                purpose="chat",
                bundle=bundle,
            )
        self.assertTrue(first.created)
        self.assertIsNotNone(first.active)
        self.assertFalse(second.created)
        self.assertIsNotNone(second.active)

    def test_fingerprint_changes_when_segment_text_changes(self) -> None:
        base = {
            "language": "en",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {"system_instruction": True},
        }
        first = self.pc.build_prompt_cache_bundle(
            {**base, "system_instruction": "A" * 9000},
            purpose="chat",
        )
        second = self.pc.build_prompt_cache_bundle(
            {**base, "system_instruction": "B" * 9000},
            purpose="chat",
        )
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertNotEqual(first.fingerprint, second.fingerprint)

    def test_rebuild_preserves_custom_cache_content_shape(self) -> None:
        config = {
            "language": "en",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {
                "system_instruction": True,
                "custom_cache_text": True,
            },
            "system_instruction": "A" * 9000,
            "prompt_cache_custom_text": "Custom rules here.",
        }
        original = self.pc.build_prompt_cache_bundle(config, purpose="chat")
        assert original is not None
        self.assertTrue(original.cached_system_text.strip())
        self.assertTrue(original.cached_contents)

        rebuilt = self.pc.rebuild_prompt_cache_bundle(
            config,
            purpose="chat",
            enabled_segment_ids=original.enabled_segment_ids,
            segment_texts={
                "system_instruction": "A" * 9000,
                "custom_cache_text": "Edited custom rules.",
            },
            live_system_text="",
        )
        self.assertIsNotNone(rebuilt)
        assert rebuilt is not None
        self.assertTrue(rebuilt.cached_system_text.strip())
        self.assertTrue(rebuilt.cached_contents)
        self.assertEqual(len(rebuilt.cached_contents), 1)
        self.assertEqual(rebuilt.cached_contents[0]["role"], "user")
        self.assertIn(
            "Edited custom rules.",
            rebuilt.cached_contents[0]["parts"][0]["text"],
        )

    def test_flattened_cache_upload_text_includes_formatted_sections(self) -> None:
        config = {
            "language": "en",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {
                "system_instruction": True,
                "custom_cache_text": True,
            },
            "system_instruction": "A" * 9000,
            "prompt_cache_custom_text": "Custom rules here.",
        }
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat")
        assert bundle is not None
        flat = self.pc.flattened_cache_upload_text(bundle)
        self.assertIn("=== System instructions ===", flat)
        self.assertIn("A" * 9000, flat)
        self.assertIn("=== Custom cache text ===", flat)
        self.assertIn("Custom rules here.", flat)
        self.assertLess(flat.index("=== System instructions ==="), flat.index("=== Custom cache text ==="))

    def test_flatten_bundle_for_live_send_merges_cached_segments(self) -> None:
        config = {
            "language": "en",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {
                "system_instruction": True,
                "custom_cache_text": True,
            },
            "system_instruction": "A" * 9000,
            "prompt_cache_custom_text": "Original custom rules.",
        }
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat")
        assert bundle is not None
        edited = self.pc.rebuild_prompt_cache_bundle(
            config,
            purpose="chat",
            enabled_segment_ids=bundle.enabled_segment_ids,
            segment_texts={
                "system_instruction": "B" * 9000,
                "custom_cache_text": "Edited custom rules.",
            },
            live_system_text="Live addon text.",
        )
        assert edited is not None
        system, payload = self.pc.flatten_bundle_for_live_send(
            config,
            edited,
            purpose="chat",
            include_meta_rule=False,
            user_text="User question?",
        )
        self.assertIn("Live addon text.", system)
        self.assertIn("B" * 9000, system)
        self.assertIn("Edited custom rules.", payload)
        self.assertIn("User question?", payload)

    def test_flatten_bundle_for_live_send_optimize(self) -> None:
        config = {
            "language": "en",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {"system_instruction": True},
            "system_instruction": "A" * 9000,
        }
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="optimize")
        assert bundle is not None
        edited = self.pc.rebuild_prompt_cache_bundle(
            config,
            purpose="optimize",
            enabled_segment_ids=bundle.enabled_segment_ids,
            segment_texts={"system_instruction": "C" * 9000},
            live_system_text="",
        )
        assert edited is not None
        system, payload = self.pc.flatten_bundle_for_live_send(
            config,
            edited,
            purpose="optimize",
            include_meta_rule=False,
            user_text="Field body",
        )
        self.assertIn("C" * 9000, system)
        self.assertEqual(payload, "Field body")

    def test_confirm_new_conversation_returns_none_without_tracked_cache(self) -> None:
        pcc = _load_addon_module("ui.prompt_cache_confirm")
        config = {"language": "en"}
        with patch.object(pcc, "has_tracked_active_cache", return_value=False):
            self.assertIsNone(pcc.confirm_new_conversation_cache_if_needed(None, config))

    def test_cached_fingerprint_ignores_live_system_text(self) -> None:
        config = {
            "language": "en",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {"system_instruction": True},
            "system_instruction": "A" * 9000,
        }
        first = self.pc.rebuild_prompt_cache_bundle(
            config,
            purpose="chat",
            enabled_segment_ids=("system_instruction",),
            segment_texts={"system_instruction": "A" * 9000},
            live_system_text="Live A",
        )
        second = self.pc.rebuild_prompt_cache_bundle(
            config,
            purpose="chat",
            enabled_segment_ids=("system_instruction",),
            segment_texts={"system_instruction": "A" * 9000},
            live_system_text="Live B",
        )
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        assert first is not None and second is not None
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertNotEqual(first.live_system_text, second.live_system_text)

    def test_will_recreate_only_when_stale_active_exists(self) -> None:
        store = self.pc.PromptCacheStore(purpose="chat")
        config = {
            "language": "en",
            "model_chat": "gemini-2.5-flash",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {"system_instruction": True},
            "system_instruction": "A" * 9000,
        }
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat")
        assert bundle is not None
        self.assertFalse(
            self.pc.prompt_cache_will_recreate(store, bundle, config, purpose="chat")
        )
        store.active = self.pc.ActivePromptCache(
            name="cachedContents/old",
            fingerprint="stale",
            model="gemini-2.5-flash",
            purpose="chat",
            expire_at=9_999_999_999.0,
            ttl_seconds=3600,
            cached_char_count=bundle.cached_char_count,
        )
        self.assertTrue(
            self.pc.prompt_cache_will_recreate(store, bundle, config, purpose="chat")
        )

    def test_needs_recreate_confirm_when_stale_active(self) -> None:
        config = {
            "language": "en",
            "model_chat": "gemini-2.5-flash",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_ttl_seconds": 3600,
            "prompt_cache_segments": {"system_instruction": True},
            "system_instruction": "A" * 9000,
        }
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat")
        assert bundle is not None
        store = self.pc.get_prompt_cache_store("chat")
        store.active = self.pc.ActivePromptCache(
            name="cachedContents/old",
            fingerprint="stale",
            model="gemini-2.5-flash",
            purpose="chat",
            expire_at=9_999_999_999.0,
            ttl_seconds=3600,
            cached_char_count=bundle.cached_char_count,
        )
        self.assertTrue(
            self.pc.needs_prompt_cache_recreate_confirm(
                config,
                bundle,
                purpose="chat",
            )
        )

    def test_needs_no_recreate_confirm_without_stale_active(self) -> None:
        config = {
            "language": "en",
            "model_chat": "gemini-2.5-flash",
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {"system_instruction": True},
            "system_instruction": "A" * 9000,
        }
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat")
        assert bundle is not None
        self.assertFalse(
            self.pc.needs_prompt_cache_recreate_confirm(
                config,
                bundle,
                purpose="chat",
            )
        )

    def test_purpose_from_display_name(self) -> None:
        self.assertEqual(self.pc.purpose_from_display_name("anki-ai-chat"), "chat")
        self.assertEqual(self.pc.purpose_from_display_name("anki-ai-optimize"), "optimize")
        self.assertIsNone(self.pc.purpose_from_display_name("other"))

    def test_persist_and_hydrate_store(self) -> None:
        import os
        import tempfile

        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        old_path = self.pc.PROMPT_CACHE_STATE_PATH
        try:
            self.pc.PROMPT_CACHE_STATE_PATH = path
            self.pc.clear_prompt_cache_store()
            store = self.pc.get_prompt_cache_store("chat")
            active = self.pc.ActivePromptCache(
                name="cachedContents/test",
                fingerprint="fp",
                model="gemini-2.5-flash",
                purpose="chat",
                expire_at=9_999_999_999.0,
                ttl_seconds=3600,
                cached_char_count=100,
            )
            self.pc._set_store_active(store, active)
            self.pc._stores.clear()
            self.pc._stores_hydrated = False
            self.pc._hydrate_stores_from_disk()
            reloaded = self.pc.get_prompt_cache_store("chat").active
            self.assertIsNotNone(reloaded)
            self.assertEqual(reloaded.name, "cachedContents/test")
        finally:
            self.pc.PROMPT_CACHE_STATE_PATH = old_path
            try:
                os.unlink(path)
            except OSError:
                pass

    def test_remote_entry_filters_addon_display_names(self) -> None:
        entry = self.pc._remote_entry_from_api(
            {
                "name": "cachedContents/abc",
                "displayName": "anki-ai-chat",
                "model": "models/gemini-2.5-flash",
                "expireTime": "2030-01-01T00:00:00Z",
            },
            tracked_names=set(),
        )
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.purpose, "chat")
        self.assertEqual(entry.model, "gemini-2.5-flash")
        self.assertFalse(entry.tracked)
        self.assertIsNone(
            self.pc._remote_entry_from_api(
                {"name": "cachedContents/x", "displayName": "other"},
                tracked_names=set(),
            )
        )


class TestDevMock(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dev_mock = _load_addon_module("dev_mock")
        cls.gc = _load_addon_module("gemini_client")
        cls.pc = _load_addon_module("prompt_cache")
        cls.config = _load_addon_module("config")

    def setUp(self) -> None:
        self.dev_mock.reset_dev_mock_state()
        self.pc.clear_prompt_cache_store()

    def tearDown(self) -> None:
        self.dev_mock.reset_dev_mock_state()
        config = self.config.load_config()
        config["dev_mock_mode"] = False
        self.config.save_config(config)

    def test_mock_call_gemini_chat(self) -> None:
        config = {"language": "en", "dev_mock_mode": True}
        payload = {"contents": [{"role": "user", "parts": [{"text": "Hello mock"}]}]}
        reply = self.dev_mock.try_mock_call_gemini(
            config=config,
            user_text="Hello mock",
            payload=payload,
            purpose="chat",
        )
        self.assertIsNotNone(reply)
        assert reply is not None
        self.assertIn("[Dev mock", reply)

    def test_mock_prompt_cache_create_without_api_key(self) -> None:
        config = {
            "language": "en",
            "dev_mock_mode": True,
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 37,
            "prompt_cache_segments": {"system_instruction": True},
            "system_instruction": "X" * 9000,
        }
        bundle = self.pc.build_prompt_cache_bundle(config, purpose="chat")
        self.assertIsNotNone(bundle)
        result = self.pc.ensure_prompt_cache(config=config, purpose="chat", bundle=bundle)
        self.assertTrue(result.created)
        self.assertIsNotNone(result.active)
        assert result.active is not None
        self.assertTrue(result.active.name.startswith("cachedContents/dev-mock-"))

    def test_api_key_not_required_when_mock_enabled(self) -> None:
        config = {"dev_mock_mode": True, "api_key": ""}
        self.assertTrue(self.config.api_key_configured(config))

    def test_prepare_gemini_request_uses_mock_without_network(self) -> None:
        config = {
            "language": "en",
            "dev_mock_mode": True,
            "chat_streaming": False,
        }
        prepared = self.gc.prepare_gemini_request(
            config=config,
            user_text="Ping",
            history=None,
            temperature=0.2,
            include_meta_rule=False,
            purpose="chat",
        )
        with patch.object(self.gc.requests, "post") as post:
            reply = self.gc.call_gemini(
                config=config,
                user_text="Ping",
                include_meta_rule=False,
                purpose="chat",
            )
        post.assert_not_called()
        self.assertIn("[Dev mock", reply)


class TestPromptCachePolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = _load_addon_module("prompt_cache_policy")

    def test_temperature_change_does_not_invalidate_cache(self) -> None:
        old = {
            "prompt_cache_enabled": True,
            "temperature_chat": 0.2,
            "model_chat": "gemini-2.5-flash",
        }
        new = dict(old)
        new["temperature_chat"] = 0.5
        self.assertEqual(self.policy.purposes_requiring_cache_invalidation(old, new), ())

    def test_model_change_invalidates_chat_cache(self) -> None:
        old = {
            "prompt_cache_enabled": True,
            "model_chat": "gemini-2.5-flash",
        }
        new = dict(old)
        new["model_chat"] = "gemini-2.5-pro"
        self.assertEqual(
            self.policy.purposes_requiring_cache_invalidation(old, new),
            ("chat",),
        )

    def test_global_only_when_session_segments_disabled(self) -> None:
        config = {
            "prompt_cache_enabled": True,
            "prompt_cache_segments": {"system_instruction": True},
        }
        self.assertTrue(self.policy.cache_enabled_segments_are_global_only(config))

    def test_not_global_only_when_note_cached(self) -> None:
        config = {
            "prompt_cache_enabled": True,
            "prompt_cache_segments": {
                "system_instruction": True,
                "imported_note": True,
            },
        }
        self.assertFalse(self.policy.cache_enabled_segments_are_global_only(config))

    def test_effective_custom_cache_text_uses_active_preset(self) -> None:
        config = {
            "prompt_cache_custom_text": "Legacy text",
            "prompt_cache_active_preset_id": "preset-a",
            "prompt_cache_custom_text_presets": [
                {
                    "id": "preset-a",
                    "name": "Rules",
                    "text": "Preset rules",
                    "chat": True,
                    "optimize": False,
                }
            ],
        }
        self.assertEqual(
            self.policy.effective_custom_cache_text(config, purpose="chat"),
            "Preset rules",
        )
        self.assertEqual(
            self.policy.effective_custom_cache_text(config, purpose="optimize"),
            "",
        )


class TestPromptCacheConfirmLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pcc = _load_addon_module("ui.prompt_cache_confirm")

    def test_recreate_default_skip_cache(self) -> None:
        config = {"prompt_cache_recreate_default": "skip_cache"}
        self.assertEqual(self.pcc._recreate_default_choice(config), "skip_cache")

    def test_recreate_default_unknown_falls_back_to_proceed(self) -> None:
        config = {"prompt_cache_recreate_default": "unexpected"}
        self.assertEqual(self.pcc._recreate_default_choice(config), "proceed")

    def test_recreate_confirm_uses_default_when_dismissed(self) -> None:
        config = {
            "language": "en",
            "suppress_prompt_cache_recreate_confirm": True,
            "prompt_cache_recreate_default": "skip_cache",
        }
        with patch.object(self.pcc, "needs_prompt_cache_recreate_confirm", return_value=True):
            choice = self.pcc.confirm_prompt_cache_recreate_if_needed(
                None,
                config,
                MagicMock(),
                purpose="chat",
            )
        self.assertEqual(choice, "skip_cache")

    def test_import_note_dismissed_always_proceeds(self) -> None:
        config = {
            "language": "en",
            "suppress_import_note_cache_warning": True,
        }
        with patch.object(self.pcc, "has_tracked_active_cache", return_value=True):
            with patch.object(self.pcc, "chat_cache_includes_session_content", return_value=True):
                choice = self.pcc.confirm_import_note_cache_if_needed(None, config)
        self.assertEqual(choice, "proceed")

    def test_default_action_settings_exclude_import_note(self) -> None:
        config_mod = _load_addon_module("config")
        keys = {entry[0] for entry in config_mod.DEFAULT_ACTION_SETTINGS}
        self.assertNotIn("prompt_cache_import_note_default", keys)


class TestSettingsCompactControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.controls = _load_addon_module("ui.settings_compact_controls")

    def test_configure_text_edit_helpers_exist(self) -> None:
        self.assertTrue(callable(self.controls.configure_addon_text_edit))
        self.assertTrue(callable(self.controls.configure_settings_text_edit))

    def test_configure_addon_text_edit_marks_editor(self) -> None:
        editor = MagicMock()
        editor.document.return_value = MagicMock()
        with patch.object(self.controls, "load_config", return_value={"settings_show_text_newlines": False}):
            with patch.object(self.controls, "bind_text_edit_auto_height"):
                self.controls.configure_addon_text_edit(editor, scroll_free=True)
        self.assertTrue(getattr(editor, "_addon_text_edit", False))

    def test_configure_settings_text_edit_marks_editor(self) -> None:
        editor = MagicMock()
        editor.document.return_value = MagicMock()
        with patch.object(self.controls, "bind_text_edit_auto_height"):
            self.controls.configure_settings_text_edit(editor)
        self.assertTrue(getattr(editor, "_settings_text_edit", False))


class TestSettingsWarningsLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.settings = _load_addon_module("ui.settings_dialog")
        cls.config_mod = _load_addon_module("config")

    def test_refresh_warning_restore_checkboxes_unchecks_all(self) -> None:
        dialog = MagicMock()
        first = MagicMock()
        second = MagicMock()
        dialog._warning_restore_checkboxes = {"a": first, "b": second}
        self.settings.SettingsDialog._refresh_warning_restore_checkboxes(dialog)
        first.setChecked.assert_called_once_with(False)
        second.setChecked.assert_called_once_with(False)

    def test_apply_warning_restores_saves_default_actions_without_warning_selection(self) -> None:
        dialog = MagicMock()
        dialog.config = {
            "language": "en",
            "prompt_cache_recreate_default": "recreate",
        }
        dialog._baseline_config = dict(dialog.config)
        dialog._selected_warning_restore_keys = MagicMock(return_value=[])
        combo = MagicMock()
        combo.currentData.return_value = "skip_cache"
        dialog._default_action_combos = {"prompt_cache_recreate_default": combo}
        with patch.object(self.settings, "save_config") as save:
            self.settings.SettingsDialog._apply_selected_warning_restores(dialog)
        self.assertEqual(dialog.config["prompt_cache_recreate_default"], "skip_cache")
        self.assertEqual(
            dialog._baseline_config["prompt_cache_recreate_default"],
            "skip_cache",
        )
        save.assert_called_once()


class TestUiModuleImports(unittest.TestCase):
    _CORE_MODULES = (
        "prompt_cache_policy",
        "prompt_inspection",
        "dev_mock",
        "prompt_compose",
        "note_context_fields",
    )

    def test_core_addon_modules_import_under_mocks(self) -> None:
        for module_name in self._CORE_MODULES:
            with self.subTest(module=module_name):
                _load_addon_module(module_name)

    def test_all_ui_modules_import_under_mocks(self) -> None:
        ui_dir = Path(__file__).resolve().parent.parent / "ui"
        for path in sorted(ui_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            module_name = f"ui.{path.stem}"
            with self.subTest(module=module_name):
                _load_addon_module(module_name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
