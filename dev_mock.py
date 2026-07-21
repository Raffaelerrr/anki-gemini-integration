from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from .constants import GEMINI_MODEL_CHOICES

LogCallback = Callable[[str], None]

_log_callback: LogCallback | None = None
_remote_caches: dict[str, dict[str, Any]] = {}
_mock_stream_chunk_ms = 35
_mock_call_delay_ms = 250


def set_dev_mock_log_callback(callback: LogCallback | None) -> None:
    global _log_callback
    _log_callback = callback


def dev_mock_log(message: str) -> None:
    if _log_callback is not None:
        _log_callback(message)


def is_dev_mock_enabled(config: dict[str, Any] | None = None) -> bool:
    if config is None:
        from .config import load_config

        config = load_config()
    return bool(config.get("dev_mock_mode", False))


def clear_dev_mock_remote_caches() -> None:
    _remote_caches.clear()
    dev_mock_log("Cleared in-memory mock remote caches.")


def reset_dev_mock_state() -> None:
    from .prompt_cache import reset_local_prompt_cache_tracking

    clear_dev_mock_remote_caches()
    reset_local_prompt_cache_tracking()
    dev_mock_log("Reset mock caches and local prompt-cache tracking.")


def mock_model_ids() -> list[str]:
    return list(GEMINI_MODEL_CHOICES)


def _sleep_ms(ms: int) -> None:
    if ms > 0:
        time.sleep(ms / 1000.0)


def _user_text_from_payload(payload: dict[str, Any]) -> str:
    contents = payload.get("contents") or []
    if not contents:
        return ""
    parts = (contents[-1].get("parts") or []) if isinstance(contents[-1], dict) else []
    return "".join(str(part.get("text") or "") for part in parts if isinstance(part, dict))


def _uses_cached_content(payload: dict[str, Any]) -> bool:
    return bool(str(payload.get("cachedContent") or "").strip())


def _mock_chat_reply(*, user_text: str, payload: dict[str, Any]) -> str:
    preview = user_text.strip()
    if len(preview) > 120:
        preview = preview[:117] + "..."
    cached = "yes" if _uses_cached_content(payload) else "no"
    return (
        "**[Dev mock — no Gemini billing]**\n\n"
        f"Received **{len(user_text)}** characters (`cachedContent`: **{cached}**).\n\n"
        f"> {preview or '(empty)'}\n\n"
        "Sample fenced field content:\n\n"
        "```\n"
        "Mock optimized field\n"
        "```\n\n"
        "Sample Apply-to-Anki proposal (Edit → Apply to Anki…):\n\n"
        "<APPLY_NOTE>\n"
        "{\n"
        '  "notes": [\n'
        "    {\n"
        '      "notetype": "Basic",\n'
        '      "fields": {\n'
        '        "Front": "Mock front",\n'
        '        "Back": "Mock back"\n'
        "      }\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "</APPLY_NOTE>\n\n"
        "Use **Tools → Anki AI: Dev playground** to turn mock mode off."
    )


def _mock_optimize_reply(*, user_text: str, payload: dict[str, Any]) -> str:
    cached = "cached" if _uses_cached_content(payload) else "uncached"
    snippet = user_text.strip()
    if len(snippet) > 80:
        snippet = snippet[:77] + "..."
    return (
        f'<p><em>[Dev mock optimize — {cached}]</em> '
        f"{snippet or 'empty field'}</p>"
    )


def _stream_text(
    text: str,
    *,
    should_cancel: Callable[[], bool] | None,
    on_chunk: Callable[[str], None] | None,
) -> str:
    accumulated = ""
    step = max(8, len(text) // 12 or 1)
    for index in range(0, len(text), step):
        if should_cancel is not None and should_cancel():
            from .gemini_client import GeminiCancelledError
            from .i18n import tr
            from .config import load_config

            raise GeminiCancelledError(tr("gemini.cancelled", config=load_config()))
        accumulated = text[: index + step]
        if on_chunk is not None:
            on_chunk(accumulated)
        _sleep_ms(_mock_stream_chunk_ms)
    return text


def try_mock_call_gemini(
    *,
    config: dict[str, Any],
    user_text: str,
    payload: dict[str, Any],
    purpose: str,
    should_cancel: Callable[[], bool] | None = None,
    register_response: Callable[[Any], None] | None = None,
    on_chunk: Callable[[str], None] | None = None,
) -> str | None:
    if not is_dev_mock_enabled(config):
        return None

    outgoing = _user_text_from_payload(payload) or user_text
    dev_mock_log(
        f"Mock Gemini call ({purpose}): {len(outgoing)} chars, "
        f"cachedContent={'yes' if _uses_cached_content(payload) else 'no'}"
    )
    _sleep_ms(_mock_call_delay_ms)

    if register_response is not None:
        register_response(None)

    if purpose == "optimize":
        reply = _mock_optimize_reply(user_text=user_text, payload=payload)
        if on_chunk is not None:
            on_chunk(reply)
        dev_mock_log(f"Mock optimize reply: {len(reply)} chars")
        return reply

    reply = _mock_chat_reply(user_text=outgoing, payload=payload)
    if on_chunk is not None or should_cancel is not None:
        result = _stream_text(reply, should_cancel=should_cancel, on_chunk=on_chunk)
        dev_mock_log(f"Mock chat stream finished: {len(result)} chars")
        return result

    dev_mock_log(f"Mock chat reply: {len(reply)} chars")
    return reply


def mock_create_cached_content(
    *,
    model: str,
    bundle: Any,
    ttl_seconds: int,
    display_name: str,
    purpose: str,
) -> Any:
    from .prompt_cache import ActivePromptCache

    name = f"cachedContents/dev-mock-{purpose}-{uuid.uuid4().hex[:10]}"
    expire_at = time.time() + ttl_seconds
    _remote_caches[name] = {
        "name": name,
        "displayName": display_name,
        "model": f"models/{model}",
        "expireTime": datetime.fromtimestamp(expire_at, tz=timezone.utc).isoformat(),
    }
    dev_mock_log(
        f"Mock cache created ({purpose}): {bundle.cached_char_count} chars, TTL {ttl_seconds}s"
    )
    return ActivePromptCache(
        name=name,
        fingerprint=bundle.fingerprint,
        model=model,
        purpose=purpose,
        expire_at=expire_at,
        ttl_seconds=ttl_seconds,
        cached_char_count=bundle.cached_char_count,
    )


def mock_get_cached_content(*, cache_name: str) -> dict[str, Any]:
    item = _remote_caches.get(cache_name)
    if item is None:
        from .prompt_cache import PromptCacheNotFoundError

        raise PromptCacheNotFoundError(cache_name)
    return dict(item)


def mock_delete_cached_content(*, cache_name: str) -> None:
    if cache_name in _remote_caches:
        del _remote_caches[cache_name]
        dev_mock_log(f"Mock cache deleted: {cache_name}")


def mock_update_cached_content_ttl(*, cache_name: str, ttl_seconds: int) -> float:
    item = _remote_caches.get(cache_name)
    if item is None:
        from .prompt_cache import PromptCacheNotFoundError

        raise PromptCacheNotFoundError(cache_name)
    expire_at = time.time() + ttl_seconds
    item["expireTime"] = datetime.fromtimestamp(expire_at, tz=timezone.utc).isoformat()
    dev_mock_log(f"Mock cache TTL extended: {cache_name} (+{ttl_seconds}s)")
    return expire_at


def mock_list_remote_cached_contents() -> list[dict[str, Any]]:
    return [dict(item) for item in _remote_caches.values()]


def is_dev_mock_cache_name(cache_name: str) -> bool:
    resource = cache_name.split("/")[-1]
    return resource.startswith("dev-mock-")
