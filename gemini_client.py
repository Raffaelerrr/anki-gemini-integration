from __future__ import annotations

import re
import time
import urllib.parse
from typing import Any

import requests

from .constants import CHAT_FORMAT_INSTRUCTION, GEMINI_API_HOST, GEMINI_API_PATH, META_RULE_DYNAMIC


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


def build_api_url(model: str) -> str:
    path = GEMINI_API_PATH.format(model=model)
    return urllib.parse.urlunparse(("https", GEMINI_API_HOST, path, "", "", ""))


def _parse_response_payload(data: dict[str, Any]) -> str:
    if feedback := data.get("promptFeedback"):
        block_reason = feedback.get("blockReason")
        if block_reason:
            raise GeminiResponseError(f"Richiesta bloccata da Gemini: {block_reason}")

    candidates = data.get("candidates") or []
    if not candidates:
        raise GeminiResponseError("Gemini non ha restituito candidati nella risposta.")

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    if finish_reason and finish_reason not in ("STOP", "MAX_TOKENS"):
        raise GeminiResponseError(f"Generazione interrotta: {finish_reason}")

    content = candidate.get("content") or {}
    parts = content.get("parts") or []
    if not parts:
        raise GeminiResponseError("Risposta vuota da Gemini.")

    texts = [part.get("text", "") for part in parts if part.get("text")]
    if not texts:
        raise GeminiResponseError("Nessun testo nella risposta di Gemini.")

    return "".join(texts)


def _classify_http_error(status_code: int, response_text: str) -> GeminiError:
    if status_code in (401, 403):
        return GeminiAuthError(
            "API Key non valida o non autorizzata. Controlla la chiave nelle impostazioni (⚙️)."
        )
    if status_code == 429:
        return GeminiRateLimitError(
            "Limite di richieste raggiunto. Riprova tra qualche secondo."
        )
    return GeminiError(f"Errore HTTP {status_code}: {response_text[:300]}")


def call_gemini(
    *,
    config: dict[str, Any],
    user_text: str,
    history: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    include_meta_rule: bool = False,
) -> str:
    api_key = (config.get("api_key") or "").strip()
    model = config.get("model") or "gemini-2.5-flash"
    timeout = int(config.get("timeout_seconds") or 30)
    max_retries = int(config.get("max_retries") or 2)
    temp = temperature if temperature is not None else float(config.get("temperature_chat") or 0.2)

    url = build_api_url(model)
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    contents = list(history or [])
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": merge_system_instructions(config, include_meta_rule=include_meta_rule)}]},
        "generationConfig": {"temperature": temp},
    }

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if not response.ok:
                raise _classify_http_error(response.status_code, response.text)
            data = response.json()
            return _parse_response_payload(data)
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = GeminiError(f"Errore di rete o timeout: {exc}")
        except GeminiError as exc:
            if isinstance(exc, (GeminiAuthError, GeminiRateLimitError)):
                raise
            last_error = exc

        if attempt < max_retries:
            time.sleep(1.5 * (attempt + 1))

    raise last_error or GeminiError("Errore sconosciuto durante la chiamata a Gemini.")


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
