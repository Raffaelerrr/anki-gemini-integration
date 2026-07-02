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
    GEMINI_MODELS_LIST_PATH,
    GEMINI_STREAM_API_PATH,
    META_RULE_DYNAMIC,
)
from .i18n import effective_system_instruction, tr

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
    purpose: Purpose = "chat",
) -> str:
    instruction = effective_system_instruction(config, purpose=purpose)
    dynamic = (config.get("dynamic_instructions") or "").strip()
    if dynamic:
        instruction += (
            "\n\nREGOLE DINAMICHE AGGIUNTIVE PRECEDENTEMENTE MEMORIZZATE "
            "(Priorità inferiore rispetto alle regole sopra):\n"
            f"{dynamic}"
        )
    if purpose == "optimize":
        instruction += tr("instructions.optimize_output", config=config)
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
            "parts": [
                {
                    "text": merge_system_instructions(
                        config,
                        include_meta_rule=include_meta_rule,
                        purpose=purpose,
                    )
                }
            ]
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


def build_models_list_url(*, page_token: str | None = None, page_size: int = 100) -> str:
    params: dict[str, str] = {"pageSize": str(page_size)}
    if page_token:
        params["pageToken"] = page_token
    query = urllib.parse.urlencode(params)
    return urllib.parse.urlunparse(("https", GEMINI_API_HOST, GEMINI_MODELS_LIST_PATH, "", query, ""))


def _model_id_from_list_entry(entry: dict[str, Any]) -> str | None:
    methods = entry.get("supportedGenerationMethods") or []
    if "generateContent" not in methods:
        return None

    base_model_id = (entry.get("baseModelId") or "").strip()
    if base_model_id:
        return base_model_id

    name = (entry.get("name") or "").strip()
    if name.startswith("models/"):
        return name[len("models/") :]
    return name or None


def model_sort_key(model_id: str) -> tuple[Any, ...]:
    lower = model_id.casefold()
    if "flash-lite" in lower or "flash_lite" in lower:
        tier = 0
    elif "flash" in lower:
        tier = 1
    elif "pro" in lower:
        tier = 2
    else:
        tier = 3

    numbers = [int(part) for part in re.findall(r"\d+", model_id)]
    version = tuple(-num for num in ((numbers + [0, 0, 0])[:3]))
    return (version, tier, lower)


def sort_model_ids(models: list[str]) -> list[str]:
    return sorted(set(models), key=model_sort_key)


def list_gemini_models(*, config: dict[str, Any]) -> list[str]:
    api_key = (config.get("api_key") or "").strip()
    if not api_key:
        raise GeminiAuthError(tr("gemini.auth_error", config=config))

    timeout = int(config.get("timeout_seconds") or 30)
    headers = _request_headers(api_key)
    discovered: set[str] = set()
    page_token: str | None = None

    while True:
        url = build_models_list_url(page_token=page_token)
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise GeminiError(tr("gemini.network_error", config=config, error=exc)) from exc

        if not response.ok:
            raise _classify_http_error(response.status_code, response.text, config)

        data = response.json()
        for entry in data.get("models") or []:
            if not isinstance(entry, dict):
                continue
            model_id = _model_id_from_list_entry(entry)
            if model_id:
                discovered.add(model_id)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    if not discovered:
        raise GeminiResponseError(tr("gemini.models_empty", config=config))

    return sort_model_ids(list(discovered))


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
