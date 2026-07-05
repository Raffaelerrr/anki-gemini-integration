from __future__ import annotations

import json
import math
import re
import time
import urllib.parse
from typing import Any, Callable, Literal, Mapping

import requests

from .constants import (
    DEFAULT_MODEL,
    DEFAULT_MODEL_CHAT,
    DEFAULT_MODEL_OPTIMIZE,
    DEFAULT_THINKING_BUDGET_CHAT,
    DEFAULT_THINKING_BUDGET_OPTIMIZE,
    GEMINI_API_HOST,
    GEMINI_API_PATH,
    GEMINI_MODELS_LIST_PATH,
    GEMINI_STREAM_API_PATH,
)
from .i18n import (
    effective_chat_system_addon,
    effective_dynamic_rules_prefix,
    effective_optimize_user_prompt,
    effective_system_instruction,
    tr,
)

Purpose = Literal["optimize", "chat"]


class GeminiError(Exception):
    pass


class GeminiAuthError(GeminiError):
    pass


class GeminiRateLimitError(GeminiError):
    pass


class GeminiResponseError(GeminiError):
    pass


class GeminiCancelledError(GeminiError):
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
        instruction += effective_dynamic_rules_prefix(config)
        instruction += dynamic
    if include_meta_rule:
        instruction += effective_chat_system_addon(config)
    return instruction


def build_optimize_user_text(config: dict[str, Any], user_text: str) -> str:
    prefix = effective_optimize_user_prompt(config)
    return f"{prefix}\n\n{user_text}"


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
    if purpose == "optimize":
        user_text = build_optimize_user_text(config, user_text)
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


def _decode_stream_line(raw_line: bytes) -> str | None:
    if not raw_line:
        return None
    try:
        return raw_line.decode("utf-8")
    except UnicodeDecodeError:
        return raw_line.decode("utf-8", errors="replace")


def _check_cancelled(
    should_cancel: Callable[[], bool] | None,
    config: dict[str, Any],
) -> None:
    if should_cancel is not None and should_cancel():
        raise GeminiCancelledError(tr("gemini.cancelled", config=config))


def _iter_stream_text_deltas(
    response: requests.Response,
    config: dict[str, Any],
    *,
    should_cancel: Callable[[], bool] | None = None,
):
    try:
        for raw_line in response.iter_lines(decode_unicode=False):
            _check_cancelled(should_cancel, config)
            line = _decode_stream_line(raw_line)
            if not line or not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            _raise_if_stream_error_payload(data, config)
            text = _extract_stream_text(data, config)
            if text:
                yield text
    except (AttributeError, requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError) as exc:
        if should_cancel is not None and should_cancel():
            raise GeminiCancelledError(tr("gemini.cancelled", config=config)) from exc
        raise
    finally:
        try:
            response.close()
        except Exception:
            pass


def _parse_error_json(response_text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        return None
    error = data.get("error")
    return error if isinstance(error, dict) else None


def _retry_after_seconds(
    headers: Mapping[str, str] | None,
    error: dict[str, Any] | None,
) -> float | None:
    if headers is not None:
        for key in ("Retry-After", "retry-after"):
            raw = headers.get(key)
            if not raw:
                continue
            try:
                return float(raw)
            except (TypeError, ValueError):
                continue

    if error is None:
        return None

    for detail in error.get("details") or []:
        if not isinstance(detail, dict):
            continue
        if not str(detail.get("@type", "")).endswith("RetryInfo"):
            continue
        match = re.match(r"([\d.]+)", str(detail.get("retryDelay", "")))
        if match:
            return float(match.group(1))
    return None


def _is_daily_quota_error(error: dict[str, Any]) -> bool:
    for detail in error.get("details") or []:
        if not isinstance(detail, dict):
            continue
        if not str(detail.get("@type", "")).endswith("QuotaFailure"):
            continue
        for violation in detail.get("violations") or []:
            if not isinstance(violation, dict):
                continue
            quota_id = str(violation.get("quotaId") or "").casefold()
            if "perday" in quota_id or "daily" in quota_id:
                return True
    message = str(error.get("message") or "").casefold()
    return "per day" in message or "daily quota" in message or "per-day" in message


def _is_rate_limit_error(
    status_code: int,
    error: dict[str, Any] | None,
    response_text: str,
) -> bool:
    if status_code == 429:
        return True
    if error is None:
        lowered = response_text.casefold()
        return "resource_exhausted" in lowered or "rate limit" in lowered

    if error.get("status") == "RESOURCE_EXHAUSTED" or error.get("code") == 429:
        return True

    for detail in error.get("details") or []:
        if not isinstance(detail, dict):
            continue
        reason = str(detail.get("reason") or "").casefold()
        if reason in {"rate_limit_exceeded", "quota_exceeded"}:
            return True

    message = str(error.get("message") or "").casefold()
    return "quota" in message and ("exceeded" in message or "exhausted" in message)


def _build_rate_limit_error(
    config: dict[str, Any],
    error: dict[str, Any] | None,
    retry_seconds: float | None,
) -> GeminiRateLimitError:
    if error is not None and _is_daily_quota_error(error):
        return GeminiRateLimitError(tr("gemini.rate_limit_daily", config=config))
    if retry_seconds is not None and retry_seconds > 0:
        seconds = max(1, int(math.ceil(retry_seconds)))
        return GeminiRateLimitError(tr("gemini.rate_limit_retry", config=config, seconds=seconds))
    return GeminiRateLimitError(tr("gemini.rate_limit", config=config))


def _raise_if_stream_error_payload(data: dict[str, Any], config: dict[str, Any]) -> None:
    error = data.get("error")
    if not isinstance(error, dict):
        return

    retry_seconds = _retry_after_seconds(None, error)
    status_code = int(error.get("code") or 429)
    payload_text = json.dumps(data, ensure_ascii=False)
    if _is_rate_limit_error(status_code, error, payload_text):
        raise _build_rate_limit_error(config, error, retry_seconds)

    message = str(error.get("message") or "").strip()
    if not message:
        message = tr(
            "gemini.http_error",
            config=config,
            status=status_code,
            detail=payload_text[:300],
        )
    raise GeminiError(message)


def _classify_http_error(
    status_code: int,
    response_text: str,
    config: dict[str, Any],
    *,
    headers: Mapping[str, str] | None = None,
) -> GeminiError:
    error = _parse_error_json(response_text)
    retry_seconds = _retry_after_seconds(headers, error)
    if _is_rate_limit_error(status_code, error, response_text):
        return _build_rate_limit_error(config, error, retry_seconds)
    if status_code in (401, 403):
        return GeminiAuthError(tr("gemini.auth_error", config=config))
    return GeminiError(
        tr("gemini.http_error", config=config, status=status_code, detail=response_text[:300])
    )


def _request_headers(api_key: str) -> dict[str, str]:
    return {"x-goog-api-key": api_key, "Content-Type": "application/json"}


def _run_streaming_request(
    *,
    config: dict[str, Any],
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int,
    max_retries: int,
    should_cancel: Callable[[], bool] | None = None,
    register_response: Callable[[requests.Response | None], None] | None = None,
    on_chunk: Callable[[str], None] | None = None,
) -> str:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        _check_cancelled(should_cancel, config)
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout,
                stream=True,
            )
            if register_response is not None:
                register_response(response)
            if not response.ok:
                raise _classify_http_error(
                    response.status_code,
                    response.text,
                    config,
                    headers=response.headers,
                )

            accumulated = ""
            for delta in _iter_stream_text_deltas(response, config, should_cancel=should_cancel):
                accumulated += delta
                if on_chunk is not None:
                    on_chunk(accumulated)

            if register_response is not None:
                register_response(None)

            if not accumulated.strip():
                raise GeminiResponseError(tr("gemini.empty_response", config=config))
            return accumulated
        except GeminiCancelledError:
            if register_response is not None:
                register_response(None)
            raise
        except (requests.Timeout, requests.ConnectionError) as exc:
            if register_response is not None:
                register_response(None)
            if should_cancel is not None and should_cancel():
                raise GeminiCancelledError(tr("gemini.cancelled", config=config)) from exc
            last_error = GeminiError(tr("gemini.network_error", config=config, error=exc))
        except GeminiError as exc:
            if register_response is not None:
                register_response(None)
            if isinstance(exc, (GeminiAuthError, GeminiRateLimitError)):
                raise
            last_error = exc
        except Exception as exc:
            if register_response is not None:
                register_response(None)
            if should_cancel is not None and should_cancel():
                raise GeminiCancelledError(tr("gemini.cancelled", config=config)) from exc
            raise

        if attempt < max_retries:
            time.sleep(1.5 * (attempt + 1))

    raise last_error or GeminiError(tr("gemini.unknown_error", config=config))


def call_gemini(
    *,
    config: dict[str, Any],
    user_text: str,
    history: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    include_meta_rule: bool = False,
    purpose: Purpose = "chat",
    should_cancel: Callable[[], bool] | None = None,
    register_response: Callable[[requests.Response | None], None] | None = None,
) -> str:
    api_key = (config.get("api_key") or "").strip()
    model = resolve_model(config, purpose)
    timeout = int(config.get("timeout_seconds") or 30)
    max_retries = int(config.get("max_retries") or 2)
    temp = temperature if temperature is not None else float(config.get("temperature_chat") or 0.2)

    payload = build_request_payload(
        config=config,
        user_text=user_text,
        history=history,
        temperature=temp,
        include_meta_rule=include_meta_rule,
        purpose=purpose,
    )
    headers = _request_headers(api_key)

    if should_cancel is not None:
        url = build_api_url(model, stream=True)
        return _run_streaming_request(
            config=config,
            url=url,
            headers=headers,
            payload=payload,
            timeout=timeout,
            max_retries=max_retries,
            should_cancel=should_cancel,
            register_response=register_response,
        )

    url = build_api_url(model, stream=False)

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if not response.ok:
                raise _classify_http_error(
                    response.status_code,
                    response.text,
                    config,
                    headers=response.headers,
                )
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
    should_cancel: Callable[[], bool] | None = None,
    register_response: Callable[[requests.Response | None], None] | None = None,
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

    return _run_streaming_request(
        config=config,
        url=url,
        headers=headers,
        payload=payload,
        timeout=timeout,
        max_retries=max_retries,
        should_cancel=should_cancel,
        register_response=register_response,
        on_chunk=on_chunk,
    )


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
            raise _classify_http_error(
                response.status_code,
                response.text,
                config,
                headers=response.headers,
            )

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
