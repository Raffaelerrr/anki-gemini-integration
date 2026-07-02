from __future__ import annotations

import json
import re
import time
import urllib.parse
from typing import Any, Callable, Literal

import requests

from .constants import (
    CHAT_FORMAT_INSTRUCTION,
    DEFAULT_MODEL,
    DEFAULT_MODEL_CHAT,
    DEFAULT_MODEL_OPTIMIZE,
    DEFAULT_THINKING_BUDGET_CHAT,
    DEFAULT_THINKING_BUDGET_OPTIMIZE,
    GEMINI_API_HOST,
    GEMINI_API_PATH,
    GEMINI_STREAM_API_PATH,
    META_RULE_DYNAMIC,
)
from .i18n import tr

Purpose = Literal["optimize", "chat"]


class GeminiError(Exception):
    pass


class GeminiAuthError(GeminiError):
    pass


class GeminiRateLimitError(GeminiError):
    pass


class GeminiResponseError(GeminiError):
    pass


def strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:html|markdown|text)?\s*\n?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    return cleaned.strip()


def merge_system_instructions(
    config: dict[str, Any],
    *,
    include_meta_rule: bool = False,
) -> str:
    instruction = config.get("system_instruction", "")
    dynamic = (config.get("dynamic_instructions") or "").strip()
    if dynamic:
        instruction += (
            "\n\nREGOLE DINAMICHE AGGIUNTIVE PRECEDENTEMENTE MEMORIZZATE "
            "(Priorità inferiore rispetto alle regole sopra):\n"
            f"{dynamic}"
        )
    if include_meta_rule:
        instruction += CHAT_FORMAT_INSTRUCTION
        instruction += META_RULE_DYNAMIC
    return instruction


def resolve_model(config: dict[str, Any], purpose: Purpose) -> str:
    specific = (config.get(f"model_{purpose}") or "").strip()
    if specific:
        return specific
    legacy = (config.get("model") or "").strip()
    if legacy:
        return legacy
    return DEFAULT_MODEL_OPTIMIZE if purpose == "optimize" else DEFAULT_MODEL_CHAT


def resolve_thinking_budget(config: dict[str, Any], purpose: Purpose) -> int:
    key = f"thinking_budget_{purpose}"
    default = DEFAULT_THINKING_BUDGET_OPTIMIZE if purpose == "optimize" else DEFAULT_THINKING_BUDGET_CHAT
    raw = config.get(key, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def build_api_url(model: str, *, stream: bool = False) -> str:
    path_template = GEMINI_STREAM_API_PATH if stream else GEMINI_API_PATH
    path = path_template.format(model=model)
    query = urllib.parse.urlencode({"alt": "sse"}) if stream else ""
    return urllib.parse.urlunparse(("https", GEMINI_API_HOST, path, "", query, ""))


def build_generation_config(config: dict[str, Any], temperature: float, purpose: Purpose) -> dict[str, Any]:
    return {
        "temperature": temperature,
        "thinkingConfig": {"thinkingBudget": resolve_thinking_budget(config, purpose)},
    }


def build_request_payload(
    *,
    config: dict[str, Any],
    user_text: str,
    history: list[dict[str, Any]] | None,
    temperature: float,
    include_meta_rule: bool,
    purpose: Purpose,
) -> dict[str, Any]:
    contents = list(history or [])
    contents.append({"role": "user", "parts": [{"text": user_text}]})
    return {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": merge_system_instructions(config, include_meta_rule=include_meta_rule)}]
        },
        "generationConfig": build_generation_config(config, temperature, purpose),
    }


def _parse_response_payload(data: dict[str, Any], config: dict[str, Any]) -> str:
    if feedback := data.get("promptFeedback"):
        block_reason = feedback.get("blockReason")
        if block_reason:
            raise GeminiResponseError(tr("gemini.blocked", config=config, reason=block_reason))

    candidates = data.get("candidates") or []
    if not candidates:
        raise GeminiResponseError(tr("gemini.no_candidates", config=config))

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    if finish_reason and finish_reason not in ("STOP", "MAX_TOKENS"):
        raise GeminiResponseError(tr("gemini.interrupted", config=config, reason=finish_reason))

    content = candidate.get("content") or {}
    parts = content.get("parts") or []
    if not parts:
        raise GeminiResponseError(tr("gemini.empty_response", config=config))

    texts = [part.get("text", "") for part in parts if part.get("text")]
    if not texts:
        raise GeminiResponseError(tr("gemini.no_text", config=config))

    return "".join(texts)


def _extract_stream_text(data: dict[str, Any], config: dict[str, Any]) -> str:
    if feedback := data.get("promptFeedback"):
        block_reason = feedback.get("blockReason")
        if block_reason:
            raise GeminiResponseError(tr("gemini.blocked", config=config, reason=block_reason))

    candidates = data.get("candidates") or []
    if not candidates:
        return ""

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    if finish_reason and finish_reason not in ("STOP", "MAX_TOKENS"):
        raise GeminiResponseError(tr("gemini.interrupted", config=config, reason=finish_reason))

    parts = (candidate.get("content") or {}).get("parts") or []
    return "".join(part.get("text", "") for part in parts if part.get("text"))


def _iter_stream_text_deltas(response: requests.Response, config: dict[str, Any]):
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        payload = line[6:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        text = _extract_stream_text(data, config)
        if text:
            yield text


def _classify_http_error(status_code: int, response_text: str, config: dict[str, Any]) -> GeminiError:
    if status_code in (401, 403):
        return GeminiAuthError(tr("gemini.auth_error", config=config))
    if status_code == 429:
        return GeminiRateLimitError(tr("gemini.rate_limit", config=config))
    return GeminiError(
        tr("gemini.http_error", config=config, status=status_code, detail=response_text[:300])
    )


def _request_headers(api_key: str) -> dict[str, str]:
    return {"x-goog-api-key": api_key, "Content-Type": "application/json"}


def call_gemini(
    *,
    config: dict[str, Any],
    user_text: str,
    history: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    include_meta_rule: bool = False,
    purpose: Purpose = "chat",
) -> str:
    api_key = (config.get("api_key") or "").strip()
    model = resolve_model(config, purpose)
    timeout = int(config.get("timeout_seconds") or 30)
    max_retries = int(config.get("max_retries") or 2)
    temp = temperature if temperature is not None else float(config.get("temperature_chat") or 0.2)

    url = build_api_url(model, stream=False)
    headers = _request_headers(api_key)
    payload = build_request_payload(
        config=config,
        user_text=user_text,
        history=history,
        temperature=temp,
        include_meta_rule=include_meta_rule,
        purpose=purpose,
    )

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if not response.ok:
                raise _classify_http_error(response.status_code, response.text, config)
            data = response.json()
            return _parse_response_payload(data, config)
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = GeminiError(tr("gemini.network_error", config=config, error=exc))
        except GeminiError as exc:
            if isinstance(exc, (GeminiAuthError, GeminiRateLimitError)):
                raise
            last_error = exc

        if attempt < max_retries:
            time.sleep(1.5 * (attempt + 1))

    raise last_error or GeminiError(tr("gemini.unknown_error", config=config))


def stream_gemini(
    *,
    config: dict[str, Any],
    user_text: str,
    history: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    include_meta_rule: bool = False,
    on_chunk: Callable[[str], None] | None = None,
) -> str:
    api_key = (config.get("api_key") or "").strip()
    model = resolve_model(config, "chat")
    timeout = int(config.get("timeout_seconds") or 30)
    max_retries = int(config.get("max_retries") or 2)
    temp = temperature if temperature is not None else float(config.get("temperature_chat") or 0.2)

    url = build_api_url(model, stream=True)
    headers = _request_headers(api_key)
    payload = build_request_payload(
        config=config,
        user_text=user_text,
        history=history,
        temperature=temp,
        include_meta_rule=include_meta_rule,
        purpose="chat",
    )

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout, stream=True)
            if not response.ok:
                raise _classify_http_error(response.status_code, response.text, config)

            accumulated = ""
            for delta in _iter_stream_text_deltas(response, config):
                accumulated += delta
                if on_chunk is not None:
                    on_chunk(accumulated)

            if not accumulated.strip():
                raise GeminiResponseError(tr("gemini.empty_response", config=config))
            return accumulated
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = GeminiError(tr("gemini.network_error", config=config, error=exc))
        except GeminiError as exc:
            if isinstance(exc, (GeminiAuthError, GeminiRateLimitError)):
                raise
            last_error = exc

        if attempt < max_retries:
            time.sleep(1.5 * (attempt + 1))

    raise last_error or GeminiError(tr("gemini.unknown_error", config=config))


def extract_dynamic_rules(text: str) -> tuple[str, str | None]:
    match = re.search(r"<UPDATE_DYNAMIC_RULES>(.*?)</UPDATE_DYNAMIC_RULES>", text, re.DOTALL)
    if not match:
        return text, None

    rules = match.group(1).strip()
    cleaned = re.sub(
        r"<UPDATE_DYNAMIC_RULES>.*?</UPDATE_DYNAMIC_RULES>",
        "",
        text,
        flags=re.DOTALL,
    ).strip()
    return cleaned, rules


def trim_history(history: list[dict[str, Any]], max_turns: int) -> list[dict[str, Any]]:
    if max_turns <= 0:
        return []
    max_messages = max_turns * 2
    if len(history) <= max_messages:
        return history
    return history[-max_messages:]
