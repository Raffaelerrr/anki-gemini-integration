"""Optional live Gemini API tests (real network, real API key).

Skipped automatically when no API key is configured.

Run from the addon folder:
    py tests/test_live_api.py

Provide a key via environment variable:
    $env:GEMINI_API_KEY = "your-key"
    py tests/test_live_api.py

Or copy .env.example to .env.local and set GEMINI_API_KEY there.
Never commit .env.local or paste keys into chat/issues.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import gemini_api_key_from_env, load_addon_module

LIVE_API_KEY = gemini_api_key_from_env()
SKIP_REASON = (
    "Set GEMINI_API_KEY in the environment or in .env.local to run live API tests."
)


@unittest.skipUnless(LIVE_API_KEY, SKIP_REASON)
class TestLiveGeminiApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gc = load_addon_module("gemini_client")
        cls.pc = load_addon_module("prompt_cache")

    def setUp(self) -> None:
        self.pc.clear_prompt_cache_store()

    def tearDown(self) -> None:
        store = self.pc.get_prompt_cache_store("chat")
        if store.active is not None:
            try:
                self.pc.clear_prompt_cache(config=self._cache_live_config(), purpose="chat")
            except Exception:
                pass
        self.pc.clear_prompt_cache_store()

    def _live_config(self) -> dict:
        return {
            "language": "en",
            "api_key": LIVE_API_KEY,
            "model_optimize": "gemini-2.5-flash-lite",
            "model_chat": "gemini-2.5-flash-lite",
            "thinking_budget_optimize": 0,
            "thinking_budget_chat": 0,
            "timeout_seconds": 45,
            "max_retries": 1,
            "temperature_optimize": 0.1,
            "temperature_chat": 0.1,
            "system_instruction_shared": True,
            "system_instruction": "Reply briefly.",
            "dynamic_instructions": "",
        }

    def _cache_live_config(self) -> dict:
        return {
            **self._live_config(),
            "prompt_cache_enabled": True,
            "prompt_cache_min_chars": 8192,
            "prompt_cache_ttl_seconds": 300,
            "prompt_cache_custom_text": "X" * 8192,
            "prompt_cache_segments": {
                "system_instruction": False,
                "dynamic_rules": False,
                "chat_system_addon": False,
                "custom_cache_text": True,
                "imported_note": False,
                "card_templates_format_guide": False,
                "card_templates": False,
                "notetype_css": False,
                "context_wrapper": False,
            },
        }

    def test_live_optimize_call_returns_text(self):
        result = self.gc.call_gemini(
            config=self._live_config(),
            user_text="Reply with exactly: OK",
            temperature=0.1,
            include_meta_rule=False,
            purpose="optimize",
        )
        self.assertTrue(result.strip())

    def test_live_list_models_returns_gemini_ids(self):
        models = self.gc.list_gemini_models(config=self._live_config())
        self.assertTrue(any("gemini" in model.casefold() for model in models))

    def test_live_stream_chat_returns_text(self):
        config = {**self._live_config(), "chat_streaming": True}
        chunks: list[str] = []

        def on_chunk(text: str) -> None:
            chunks.append(text)

        result = self.gc.stream_gemini(
            config=config,
            user_text="Reply with exactly: STREAM_OK",
            temperature=0.1,
            include_meta_rule=False,
            on_chunk=on_chunk,
        )
        combined = result.strip() or "".join(chunks).strip()
        self.assertTrue(combined)

    def test_live_prompt_cache_create_use_and_clear(self):
        config = self._cache_live_config()
        reply = self.gc.call_gemini(
            config=config,
            user_text="Reply with exactly: CACHE_OK",
            temperature=0.1,
            include_meta_rule=False,
            purpose="chat",
            allow_prompt_cache_create=True,
        )
        self.assertTrue(reply.strip())
        store = self.pc.get_prompt_cache_store("chat")
        self.assertIsNotNone(store.active)


class TestLiveApiSkipBehavior(unittest.TestCase):
    def test_skip_message_is_documented(self):
        if LIVE_API_KEY:
            self.skipTest("Live key present; skip-behavior test not needed.")
        self.assertIn("GEMINI_API_KEY", SKIP_REASON)


if __name__ == "__main__":
    unittest.main(verbosity=2)
