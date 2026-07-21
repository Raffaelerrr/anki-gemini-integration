from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from .config import ADDON_DIR
from .constants import DEFAULT_PROMPT_CACHE_MIN_CHARS, GEMINI_API_HOST
from .gemini_client import Purpose, resolve_model
from .i18n import (
    card_templates_format_addon,
    effective_card_templates_format_prompt,
    effective_chat_system_addon,
    effective_dynamic_rules_prefix,
    effective_system_instruction,
    effective_wrapper_layout,
    tr,
)
from .chat_context_wrapper import (
    build_cache_safe_wrapper,
    build_live_request_message,
)
from .prompt_compose import join_prompt_blocks, join_prompt_header_body
from .token_estimate import estimate_text_tokens, payload_char_count

PROMPT_CACHE_SEGMENT_ORDER: tuple[str, ...] = (
    "system_instruction",
    "dynamic_rules",
    "chat_system_addon",
    "custom_cache_text",
    "imported_note",
    "card_templates_format_guide",
    "card_templates",
    "notetype_css",
    "context_wrapper",
)

CHAT_ONLY_SEGMENTS: frozenset[str] = frozenset(
    {
        "chat_system_addon",
        "imported_note",
        "card_templates_format_guide",
        "card_templates",
        "notetype_css",
        "context_wrapper",
    }
)

DEFAULT_PROMPT_CACHE_SEGMENTS: dict[str, bool] = {
    "system_instruction": True,
    "dynamic_rules": False,
    "chat_system_addon": True,
    "custom_cache_text": False,
    "imported_note": False,
    "card_templates_format_guide": False,
    "card_templates": False,
    "notetype_css": False,
    "context_wrapper": False,
}

DEFAULT_PROMPT_CACHE_SEGMENTS_OPTIMIZE: dict[str, bool] = {
    "system_instruction": True,
    "dynamic_rules": False,
    "custom_cache_text": False,
}

# Shown in settings; context_wrapper is auto-derived when note-related segments are cached.
PROMPT_CACHE_USER_SEGMENT_ORDER: tuple[str, ...] = tuple(
    segment_id for segment_id in PROMPT_CACHE_SEGMENT_ORDER if segment_id != "context_wrapper"
)

PROMPT_CACHE_OPTIMIZE_USER_SEGMENT_ORDER: tuple[str, ...] = tuple(
    segment_id
    for segment_id in PROMPT_CACHE_USER_SEGMENT_ORDER
    if segment_id not in CHAT_ONLY_SEGMENTS
)


def normalize_prompt_cache_segments_for_purpose(
    raw: Any,
    *,
    purpose: Purpose,
    default: dict[str, bool] | None = None,
) -> dict[str, bool]:
    if default is None:
        default = (
            DEFAULT_PROMPT_CACHE_SEGMENTS
            if purpose == "chat"
            else DEFAULT_PROMPT_CACHE_SEGMENTS_OPTIMIZE
        )
    merged = dict(default)
    if isinstance(raw, dict):
        allowed = set(PROMPT_CACHE_SEGMENT_ORDER)
        if purpose == "optimize":
            allowed -= CHAT_ONLY_SEGMENTS
        for key in allowed:
            if key in raw:
                merged[key] = bool(raw[key])
    if purpose == "chat":
        merged["context_wrapper"] = bool(
            merged.get("imported_note")
            or merged.get("card_templates")
            or merged.get("notetype_css")
        )
    else:
        merged.pop("context_wrapper", None)
    return merged


GEMINI_CACHED_CONTENTS_PATH = "/v1beta/cachedContents"
ADDON_CACHE_DISPLAY_PREFIX = "anki-ai-"
PROMPT_CACHE_PURPOSES: tuple[Purpose, ...] = ("chat", "optimize")
PROMPT_CACHE_STATE_PATH = Path(ADDON_DIR) / "prompt_cache_state.json"


@dataclass(frozen=True)
class PromptCacheSessionContext:
    note_context: str = ""
    templates_block: str = ""
    styling_block: str = ""
    include_note_context: bool = False
    wrapper_section_order: list[str] | None = None
    wrapper_section_prefixes: dict[str, str] | None = None
    wrapper_format_guide: str | None = None


@dataclass(frozen=True)
class PromptCacheBundle:
    fingerprint: str
    cached_system_text: str
    cached_contents: list[dict[str, Any]]
    live_system_text: str
    cached_char_count: int
    estimated_cached_tokens: int
    enabled_segment_ids: tuple[str, ...]


@dataclass(frozen=True)
class PromptCacheEnsureResult:
    active: ActivePromptCache | None = None
    created: bool = False


@dataclass
class ActivePromptCache:
    name: str
    fingerprint: str
    model: str
    purpose: str
    expire_at: float
    ttl_seconds: int
    cached_char_count: int = 0


@dataclass
class PromptCacheStore:
    purpose: str
    active: ActivePromptCache | None = None
    last_error: str = ""


@dataclass(frozen=True)
class RemotePromptCacheEntry:
    name: str
    display_name: str
    purpose: str | None
    model: str
    expire_at: float
    tracked: bool


_stores: dict[str, PromptCacheStore] = {}
_stores_hydrated = False
_orphans_reconciled = False


def display_name_for_purpose(purpose: Purpose) -> str:
    return f"{ADDON_CACHE_DISPLAY_PREFIX}{purpose}"


def purpose_from_display_name(display_name: str) -> str | None:
    prefix = ADDON_CACHE_DISPLAY_PREFIX
    if not display_name.startswith(prefix):
        return None
    purpose = display_name[len(prefix) :].strip()
    if purpose in PROMPT_CACHE_PURPOSES:
        return purpose
    return None


def _active_to_dict(active: ActivePromptCache) -> dict[str, Any]:
    return {
        "name": active.name,
        "fingerprint": active.fingerprint,
        "model": active.model,
        "purpose": active.purpose,
        "expire_at": active.expire_at,
        "ttl_seconds": active.ttl_seconds,
        "cached_char_count": active.cached_char_count,
    }


def _active_from_dict(data: dict[str, Any] | None) -> ActivePromptCache | None:
    if not isinstance(data, dict):
        return None
    name = str(data.get("name") or "").strip()
    if not name:
        return None
    try:
        return ActivePromptCache(
            name=name,
            fingerprint=str(data.get("fingerprint") or ""),
            model=str(data.get("model") or ""),
            purpose=str(data.get("purpose") or ""),
            expire_at=float(data.get("expire_at") or 0.0),
            ttl_seconds=int(data.get("ttl_seconds") or 0),
            cached_char_count=int(data.get("cached_char_count") or 0),
        )
    except (TypeError, ValueError):
        return None


def _persist_stores() -> None:
    payload: dict[str, Any] = {}
    for purpose in PROMPT_CACHE_PURPOSES:
        store = _stores.get(purpose)
        if store is not None and store.active is not None:
            payload[purpose] = _active_to_dict(store.active)
    try:
        Path(PROMPT_CACHE_STATE_PATH).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def _hydrate_stores_from_disk() -> None:
    global _stores_hydrated
    if _stores_hydrated:
        return
    _stores_hydrated = True
    for purpose in PROMPT_CACHE_PURPOSES:
        _stores.setdefault(purpose, PromptCacheStore(purpose=purpose))
    state_path = Path(PROMPT_CACHE_STATE_PATH)
    if not state_path.is_file():
        return
    try:
        stored = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(stored, dict):
        return
    for purpose in PROMPT_CACHE_PURPOSES:
        active = _active_from_dict(stored.get(purpose))
        if active is not None:
            _stores[purpose].active = active


def hydrate_prompt_cache_stores() -> None:
    _hydrate_stores_from_disk()


def _set_store_active(store: PromptCacheStore, active: ActivePromptCache | None) -> None:
    store.active = active
    _persist_stores()


def get_prompt_cache_store(purpose: Purpose) -> PromptCacheStore:
    _hydrate_stores_from_disk()
    if purpose not in _stores:
        _stores[purpose] = PromptCacheStore(purpose=purpose)
    return _stores[purpose]


def clear_prompt_cache_store(purpose: Purpose | None = None) -> None:
    global _stores_hydrated, _orphans_reconciled
    if purpose is None:
        _stores.clear()
        _stores_hydrated = False
        _orphans_reconciled = False
        try:
            Path(PROMPT_CACHE_STATE_PATH).unlink(missing_ok=True)
        except OSError:
            pass
        return
    store = _stores.get(purpose)
    if store is not None:
        store.active = None
        store.last_error = ""
    _persist_stores()


def prompt_cache_enabled(config: dict[str, Any], purpose: Purpose | None = None) -> bool:
    if purpose == "chat":
        return bool(config.get("prompt_cache_enabled_chat", False))
    if purpose == "optimize":
        return bool(config.get("prompt_cache_enabled_optimize", False))
    return bool(config.get("prompt_cache_enabled_chat", False)) or bool(
        config.get("prompt_cache_enabled_optimize", False)
    )


def prompt_cache_segments(config: dict[str, Any], purpose: Purpose = "chat") -> dict[str, bool]:
    key = f"prompt_cache_segments_{purpose}"
    return normalize_prompt_cache_segments_for_purpose(
        config.get(key),
        purpose=purpose,
    )


def prompt_cache_ttl_seconds(config: dict[str, Any], purpose: Purpose = "chat") -> int:
    key = f"prompt_cache_ttl_seconds_{purpose}"
    try:
        return max(60, int(config.get(key, 3600)))
    except (TypeError, ValueError):
        return 3600


def prompt_cache_change_ttl_seconds(config: dict[str, Any]) -> int:
    try:
        return max(60, int(config.get("prompt_cache_change_ttl_seconds", 3600)))
    except (TypeError, ValueError):
        return 3600


def any_tracked_active_cache() -> bool:
    for purpose in PROMPT_CACHE_PURPOSES:
        if get_prompt_cache_store(purpose).active is not None:
            return True
    return False


def prompt_cache_min_chars(config: dict[str, Any], purpose: Purpose = "chat") -> int:
    key = f"prompt_cache_min_chars_{purpose}"
    try:
        return max(1, int(config.get(key, DEFAULT_PROMPT_CACHE_MIN_CHARS)))
    except (TypeError, ValueError):
        return DEFAULT_PROMPT_CACHE_MIN_CHARS


def segment_label_key(segment_id: str) -> str:
    return f"settings.prompt_cache.segment.{segment_id}"


def _segment_texts(
    config: dict[str, Any],
    *,
    purpose: Purpose,
    session: PromptCacheSessionContext | None,
    enabled_segments: dict[str, bool] | None = None,
) -> dict[str, str]:
    session = session or PromptCacheSessionContext()
    enabled_segments = enabled_segments or prompt_cache_segments(config, purpose)
    texts: dict[str, str] = {}

    instruction = effective_system_instruction(config, purpose=purpose)
    if instruction.strip():
        texts["system_instruction"] = instruction

    dynamic = (config.get("dynamic_instructions") or "").strip()
    if dynamic:
        prefix = effective_dynamic_rules_prefix(config)
        texts["dynamic_rules"] = join_prompt_header_body(prefix, dynamic)

    if purpose == "chat":
        addon = effective_chat_system_addon(config)
        if addon.strip():
            texts["chat_system_addon"] = addon

    from .prompt_cache_policy import effective_custom_cache_text

    custom = effective_custom_cache_text(config, purpose=purpose)
    if custom:
        texts["custom_cache_text"] = custom

    if purpose == "chat" and session.include_note_context:
        if session.note_context.strip():
            texts["imported_note"] = session.note_context.strip()
        templates_block = session.templates_block.strip()
        styling_block = session.styling_block.strip()
        if templates_block or styling_block:
            guide = card_templates_format_addon(
                config,
                templates=templates_block,
                styling=styling_block,
            )
            if guide:
                texts["card_templates_format_guide"] = guide
        if templates_block:
            texts["card_templates"] = templates_block
        if styling_block:
            texts["notetype_css"] = styling_block
        if enabled_segments.get("context_wrapper"):
            order, prefixes = effective_wrapper_layout(config)
            if session.wrapper_section_order:
                order = list(session.wrapper_section_order)
            if session.wrapper_section_prefixes is not None:
                prefixes = dict(session.wrapper_section_prefixes)
            format_guide = (
                session.wrapper_format_guide
                if session.wrapper_format_guide is not None
                else effective_card_templates_format_prompt(config)
            )
            cache_safe = build_cache_safe_wrapper(
                config,
                section_order=order,
                section_prefixes=prefixes,
                cache_imported_note=bool(enabled_segments.get("imported_note")),
                cache_format_guide=bool(enabled_segments.get("card_templates_format_guide")),
                cache_templates=bool(enabled_segments.get("card_templates")),
                cache_styling=bool(enabled_segments.get("notetype_css")),
                context_content=session.note_context.strip(),
                templates_content=templates_block,
                styling_content=styling_block,
                format_guide=format_guide,
            )
            if cache_safe.strip():
                texts["context_wrapper"] = cache_safe

    return texts


def _format_cached_section(config: dict[str, Any], segment_id: str, text: str) -> str:
    title = tr(segment_label_key(segment_id), config=config)
    return f"=== {title} ===\n{text.strip()}"


def cached_segment_texts(
    config: dict[str, Any],
    *,
    purpose: Purpose,
    session: PromptCacheSessionContext | None,
    enabled_segment_ids: tuple[str, ...] | list[str],
) -> dict[str, str]:
    """Raw (unformatted) text for each cached segment in *enabled_segment_ids*."""
    enabled_set = set(enabled_segment_ids)
    texts = _segment_texts(config, purpose=purpose, session=session)
    return {
        segment_id: texts[segment_id]
        for segment_id in PROMPT_CACHE_SEGMENT_ORDER
        if segment_id in enabled_set and texts.get(segment_id, "").strip()
    }


def rebuild_prompt_cache_bundle(
    config: dict[str, Any],
    *,
    purpose: Purpose,
    enabled_segment_ids: tuple[str, ...] | list[str],
    segment_texts: dict[str, str],
    live_system_text: str,
) -> PromptCacheBundle | None:
    enabled_set = set(enabled_segment_ids)
    cached_system_sections: list[str] = []
    cached_contents: list[dict[str, Any]] = []
    enabled_ids: list[str] = []

    for segment_id in PROMPT_CACHE_SEGMENT_ORDER:
        if purpose == "optimize" and segment_id in CHAT_ONLY_SEGMENTS:
            continue
        if segment_id not in enabled_set:
            continue
        text = segment_texts.get(segment_id, "").strip()
        if not text:
            continue
        enabled_ids.append(segment_id)
        if segment_id == "custom_cache_text":
            cached_contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": _format_cached_section(
                                config,
                                segment_id,
                                text,
                            ),
                        }
                    ],
                }
            )
        else:
            cached_system_sections.append(
                _format_cached_section(config, segment_id, text)
            )

    cached_system_text = join_prompt_blocks(*cached_system_sections)
    total_cached_text = cached_system_text
    for content in cached_contents:
        for part in content.get("parts", []):
            total_cached_text += "\n" + str(part.get("text") or "")

    if not total_cached_text.strip():
        return None

    cached_chars = payload_char_count(total_cached_text)
    if cached_chars < prompt_cache_min_chars(config, purpose):
        return None

    fingerprint = _cached_fingerprint(
        purpose=purpose,
        model=resolve_model(config, purpose),
        enabled_ids=tuple(enabled_ids),
        cached_system_text=cached_system_text,
        cached_contents=cached_contents,
    )

    return PromptCacheBundle(
        fingerprint=fingerprint,
        cached_system_text=cached_system_text,
        cached_contents=cached_contents,
        live_system_text=live_system_text.strip(),
        cached_char_count=payload_char_count(total_cached_text),
        estimated_cached_tokens=estimate_text_tokens(total_cached_text),
        enabled_segment_ids=tuple(enabled_ids),
    )


def flattened_cache_upload_text(bundle: PromptCacheBundle) -> str:
    """Flatten cache upload fields (systemInstruction + contents) for preview."""
    parts: list[str] = []
    if bundle.cached_system_text.strip():
        parts.append(bundle.cached_system_text.strip())
    for content in bundle.cached_contents:
        for part in content.get("parts", []):
            text = str(part.get("text") or "").strip()
            if text:
                parts.append(text)
    return join_prompt_blocks(*parts)


def flatten_bundle_for_live_send(
    config: dict[str, Any],
    bundle: PromptCacheBundle,
    *,
    purpose: Purpose,
    include_meta_rule: bool,
    system_instruction_override: str | None = None,
    outgoing_payload_override: str | None = None,
    user_text: str = "",
    session: PromptCacheSessionContext | None = None,
) -> tuple[str, str]:
    """Merge cached bundle material into live system + payload for skip-cache sends."""
    live_system = (
        system_instruction_override.strip()
        if system_instruction_override is not None
        else bundle.live_system_text.strip()
    )

    system_parts: list[str] = []
    if live_system:
        system_parts.append(live_system)
    if bundle.cached_system_text.strip():
        system_parts.append(bundle.cached_system_text.strip())

    system_instruction = join_prompt_blocks(*system_parts)

    if purpose == "chat" and include_meta_rule and "chat_system_addon" not in bundle.enabled_segment_ids:
        addon = effective_chat_system_addon(config)
        if addon.strip():
            system_instruction = join_prompt_blocks(system_instruction, addon)

    cached_user_blocks: list[str] = []
    for content in bundle.cached_contents:
        for part in content.get("parts", []):
            text = str(part.get("text") or "").strip()
            if text:
                cached_user_blocks.append(text)

    if purpose == "chat" and session is not None:
        base_payload = (
            outgoing_payload_override
            if outgoing_payload_override is not None
            else build_live_chat_payload(
                config,
                user_text,
                session=session,
                bundle=bundle,
            )
        )
    else:
        base_payload = outgoing_payload_override if outgoing_payload_override is not None else user_text

    outgoing_payload = (
        join_prompt_blocks(*cached_user_blocks, base_payload)
        if cached_user_blocks
        else base_payload
    )
    return system_instruction, outgoing_payload


def prompt_cache_will_recreate(
    store: PromptCacheStore,
    bundle: PromptCacheBundle,
    config: dict[str, Any],
    *,
    purpose: Purpose,
) -> bool:
    model = resolve_model(config, purpose)
    active = store.active
    if active is not None and _cache_is_valid(active, model=model, fingerprint=bundle.fingerprint):
        return False
    if active is None:
        return False
    return True


def needs_prompt_cache_recreate_confirm(
    config: dict[str, Any],
    bundle: PromptCacheBundle | None,
    *,
    purpose: Purpose,
) -> bool:
    if bundle is None or not prompt_cache_enabled(config, purpose):
        return False
    store = get_prompt_cache_store(purpose)
    return prompt_cache_will_recreate(store, bundle, config, purpose=purpose)


def build_prompt_cache_bundle(
    config: dict[str, Any],
    *,
    purpose: Purpose,
    session: PromptCacheSessionContext | None = None,
) -> PromptCacheBundle | None:
    if not prompt_cache_enabled(config, purpose):
        return None

    enabled = prompt_cache_segments(config, purpose)
    texts = _segment_texts(config, purpose=purpose, session=session, enabled_segments=enabled)
    enabled_ids = [
        segment_id
        for segment_id in PROMPT_CACHE_SEGMENT_ORDER
        if (purpose != "optimize" or segment_id not in CHAT_ONLY_SEGMENTS)
        and enabled.get(segment_id)
        and texts.get(segment_id, "").strip()
    ]
    live_sections: list[str] = []
    for segment_id in PROMPT_CACHE_SEGMENT_ORDER:
        if purpose == "optimize" and segment_id in CHAT_ONLY_SEGMENTS:
            continue
        text = texts.get(segment_id, "").strip()
        if not text:
            continue
        if not enabled.get(segment_id) and segment_id in {
            "system_instruction",
            "dynamic_rules",
            "chat_system_addon",
        }:
            live_sections.append(text)

    live_system_text = join_prompt_blocks(*live_sections)
    return rebuild_prompt_cache_bundle(
        config,
        purpose=purpose,
        enabled_segment_ids=enabled_ids,
        segment_texts=texts,
        live_system_text=live_system_text,
    )


def _cached_fingerprint(
    *,
    purpose: str,
    model: str,
    enabled_ids: tuple[str, ...],
    cached_system_text: str,
    cached_contents: list[dict[str, Any]],
) -> str:
    """Fingerprint of the cached blob only (not live system instructions)."""
    payload = {
        "purpose": purpose,
        "model": model,
        "enabled_ids": list(enabled_ids),
        "cached_system_text": cached_system_text,
        "cached_contents": cached_contents,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_live_chat_payload(
    config: dict[str, Any],
    user_text: str,
    *,
    session: PromptCacheSessionContext,
    bundle: PromptCacheBundle | None,
) -> str:
    from .i18n import format_chat_context_message

    order, prefixes = effective_wrapper_layout(config)
    if session.wrapper_section_order:
        order = list(session.wrapper_section_order)
    if session.wrapper_section_prefixes is not None:
        prefixes = dict(session.wrapper_section_prefixes)
    format_guide = (
        session.wrapper_format_guide
        if session.wrapper_format_guide is not None
        else effective_card_templates_format_prompt(config)
    )

    if not session.include_note_context or not session.note_context.strip():
        return format_chat_context_message(
            config,
            context=session.note_context or "",
            request=user_text,
            section_order=order,
            section_prefixes=prefixes,
            format_guide=format_guide,
            include_context=False,
        )

    if bundle is None:
        return format_chat_context_message(
            config,
            context=session.note_context,
            request=user_text,
            templates=session.templates_block,
            styling=session.styling_block,
            section_order=order,
            section_prefixes=prefixes,
            format_guide=format_guide,
            include_context=True,
        )

    enabled = set(bundle.enabled_segment_ids)
    live_context = "" if "imported_note" in enabled else session.note_context
    live_templates = "" if "card_templates" in enabled else session.templates_block
    live_styling = "" if "notetype_css" in enabled else session.styling_block
    omit_format_guide = "card_templates_format_guide" in enabled

    omit_sections: set[str] | None = None
    if "context_wrapper" in enabled:
        omit_sections = set()
        if "imported_note" in enabled:
            omit_sections.add("context")
        if omit_format_guide:
            omit_sections.add("format_guide")
        if "card_templates" in enabled:
            omit_sections.add("templates")
        if "notetype_css" in enabled:
            omit_sections.add("styling")
        live_only_request = omit_sections >= {"context", "format_guide", "templates", "styling"}
        if live_only_request:
            return build_live_request_message(
                config,
                section_order=order,
                section_prefixes=prefixes,
                request=user_text,
            )

    return format_chat_context_message(
        config,
        context=live_context,
        request=user_text,
        templates=live_templates,
        styling=live_styling,
        section_order=order,
        section_prefixes=prefixes,
        format_guide=format_guide,
        omit_format_guide=omit_format_guide,
        include_context=True,
        omit_sections=omit_sections,
    )


def normalize_cache_model_name(model: str) -> str:
    cleaned = model.strip()
    if cleaned.startswith("models/"):
        return cleaned
    return f"models/{cleaned}"


def format_cache_ttl(seconds: int) -> str:
    return f"{max(60, int(seconds))}s"


def _cache_api_url(path: str = "") -> str:
    if path.startswith("/"):
        path = path[1:]
    return urllib.parse.urlunparse(("https", GEMINI_API_HOST, f"/{path}", "", "", ""))


def _request_headers(api_key: str) -> dict[str, str]:
    return {"x-goog-api-key": api_key, "Content-Type": "application/json"}


def _parse_expire_time(raw: str) -> float:
    if not raw:
        return 0.0
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return 0.0


def create_cached_content(
    *,
    api_key: str,
    model: str,
    bundle: PromptCacheBundle,
    ttl_seconds: int,
    display_name: str,
    purpose: Purpose,
    timeout: int,
    config: dict[str, Any] | None = None,
) -> ActivePromptCache:
    from .config import load_config
    from .dev_mock import is_dev_mock_enabled, mock_create_cached_content

    cfg = config if config is not None else load_config()
    if is_dev_mock_enabled(cfg):
        return mock_create_cached_content(
            model=model,
            bundle=bundle,
            ttl_seconds=ttl_seconds,
            display_name=display_name,
            purpose=purpose,
        )

    body: dict[str, Any] = {
        "model": normalize_cache_model_name(model),
        "displayName": display_name,
        "ttl": format_cache_ttl(ttl_seconds),
    }
    if bundle.cached_system_text.strip():
        body["systemInstruction"] = {
            "parts": [{"text": bundle.cached_system_text}],
        }
    if bundle.cached_contents:
        body["contents"] = bundle.cached_contents

    response = requests.post(
        _cache_api_url(GEMINI_CACHED_CONTENTS_PATH.lstrip("/")),
        headers=_request_headers(api_key),
        json=body,
        timeout=timeout,
    )
    if not response.ok:
        raise PromptCacheError(response.text[:500])

    data = response.json()
    name = str(data.get("name") or "").strip()
    if not name:
        raise PromptCacheError("missing cache name")

    expire_at = _parse_expire_time(str(data.get("expireTime") or ""))
    if expire_at <= 0:
        expire_at = time.time() + ttl_seconds

    return ActivePromptCache(
        name=name,
        fingerprint=bundle.fingerprint,
        model=model,
        purpose=purpose,
        expire_at=expire_at,
        ttl_seconds=ttl_seconds,
        cached_char_count=bundle.cached_char_count,
    )


def update_cached_content_ttl(
    *,
    api_key: str,
    cache_name: str,
    ttl_seconds: int,
    timeout: int,
    config: dict[str, Any] | None = None,
) -> float:
    from .config import load_config
    from .dev_mock import is_dev_mock_enabled, mock_update_cached_content_ttl

    cfg = config if config is not None else load_config()
    if is_dev_mock_enabled(cfg):
        return mock_update_cached_content_ttl(cache_name=cache_name, ttl_seconds=ttl_seconds)

    resource = cache_name.split("/")[-1]
    url = _cache_api_url(f"{GEMINI_CACHED_CONTENTS_PATH}/{resource}")
    response = requests.patch(
        url,
        headers=_request_headers(api_key),
        json={"ttl": format_cache_ttl(ttl_seconds)},
        timeout=timeout,
    )
    if not response.ok:
        raise PromptCacheError(response.text[:500])
    data = response.json()
    expire_at = _parse_expire_time(str(data.get("expireTime") or ""))
    if expire_at <= 0:
        expire_at = time.time() + ttl_seconds
    return expire_at


def delete_cached_content(
    *,
    api_key: str,
    cache_name: str,
    timeout: int,
    config: dict[str, Any] | None = None,
) -> None:
    from .config import load_config
    from .dev_mock import is_dev_mock_enabled, mock_delete_cached_content

    cfg = config if config is not None else load_config()
    if is_dev_mock_enabled(cfg):
        mock_delete_cached_content(cache_name=cache_name)
        return

    resource = cache_name.split("/")[-1]
    url = _cache_api_url(f"{GEMINI_CACHED_CONTENTS_PATH}/{resource}")
    response = requests.delete(
        url,
        headers=_request_headers(api_key),
        timeout=timeout,
    )
    if response.status_code not in (200, 204, 404):
        raise PromptCacheError(response.text[:500])


def get_cached_content(
    *,
    api_key: str,
    cache_name: str,
    timeout: int,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .config import load_config
    from .dev_mock import is_dev_mock_enabled, mock_get_cached_content

    cfg = config if config is not None else load_config()
    if is_dev_mock_enabled(cfg):
        return mock_get_cached_content(cache_name=cache_name)

    resource = cache_name.split("/")[-1]
    url = _cache_api_url(f"{GEMINI_CACHED_CONTENTS_PATH}/{resource}")
    response = requests.get(
        url,
        headers=_request_headers(api_key),
        timeout=timeout,
    )
    if response.status_code == 404:
        raise PromptCacheNotFoundError(cache_name)
    if not response.ok:
        raise PromptCacheError(response.text[:500])
    data = response.json()
    if not isinstance(data, dict):
        raise PromptCacheError("invalid cache response")
    return data


def list_remote_cached_contents(
    *,
    api_key: str,
    timeout: int,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    from .config import load_config
    from .dev_mock import is_dev_mock_enabled, mock_list_remote_cached_contents

    cfg = config if config is not None else load_config()
    if is_dev_mock_enabled(cfg):
        return mock_list_remote_cached_contents()

    items: list[dict[str, Any]] = []
    page_token = ""
    while True:
        query = urllib.parse.urlencode(
            {"pageSize": 100, **({"pageToken": page_token} if page_token else {})}
        )
        url = _cache_api_url(f"{GEMINI_CACHED_CONTENTS_PATH.lstrip('/')}?{query}")
        response = requests.get(
            url,
            headers=_request_headers(api_key),
            timeout=timeout,
        )
        if not response.ok:
            raise PromptCacheError(response.text[:500])
        data = response.json()
        batch = data.get("cachedContents") or []
        if isinstance(batch, list):
            items.extend(item for item in batch if isinstance(item, dict))
        page_token = str(data.get("nextPageToken") or "").strip()
        if not page_token:
            break
    return items


def _remote_entry_from_api(item: dict[str, Any], *, tracked_names: set[str]) -> RemotePromptCacheEntry | None:
    name = str(item.get("name") or "").strip()
    if not name:
        return None
    display_name = str(item.get("displayName") or "").strip()
    if not display_name.startswith(ADDON_CACHE_DISPLAY_PREFIX):
        return None
    model = str(item.get("model") or "").strip()
    if model.startswith("models/"):
        model = model[len("models/") :]
    return RemotePromptCacheEntry(
        name=name,
        display_name=display_name,
        purpose=purpose_from_display_name(display_name),
        model=model,
        expire_at=_parse_expire_time(str(item.get("expireTime") or "")),
        tracked=name in tracked_names,
    )


def list_addon_remote_caches(config: dict[str, Any]) -> list[RemotePromptCacheEntry]:
    from .dev_mock import is_dev_mock_enabled

    api_key = (config.get("api_key") or "").strip()
    if not api_key and not is_dev_mock_enabled(config):
        return []
    timeout = int(config.get("timeout_seconds") or 30)
    tracked_names = {
        store.active.name
        for purpose in PROMPT_CACHE_PURPOSES
        if (store := get_prompt_cache_store(purpose)).active is not None
    }
    entries: list[RemotePromptCacheEntry] = []
    for item in list_remote_cached_contents(api_key=api_key, timeout=timeout, config=config):
        entry = _remote_entry_from_api(item, tracked_names=tracked_names)
        if entry is not None:
            entries.append(entry)
    entries.sort(key=lambda item: (item.purpose or "", item.display_name, item.name))
    return entries


def _delete_remote_cache_best_effort(
    *,
    api_key: str,
    cache_name: str,
    timeout: int,
    config: dict[str, Any] | None = None,
) -> None:
    try:
        delete_cached_content(
            api_key=api_key,
            cache_name=cache_name,
            timeout=timeout,
            config=config,
        )
    except PromptCacheError:
        pass


def _clear_store_if_matches(store: PromptCacheStore, cache_name: str) -> None:
    if store.active is not None and store.active.name == cache_name:
        store.active = None
        store.last_error = ""


def delete_remote_prompt_cache(
    config: dict[str, Any],
    cache_name: str,
    *,
    purpose: Purpose | None = None,
) -> None:
    api_key = (config.get("api_key") or "").strip()
    timeout = int(config.get("timeout_seconds") or 30)
    if api_key:
        _delete_remote_cache_best_effort(
            api_key=api_key,
            cache_name=cache_name,
            timeout=timeout,
            config=config,
        )
    if purpose is not None:
        _clear_store_if_matches(get_prompt_cache_store(purpose), cache_name)
    else:
        for item in PROMPT_CACHE_PURPOSES:
            _clear_store_if_matches(get_prompt_cache_store(item), cache_name)
    _persist_stores()


def delete_untracked_addon_caches(config: dict[str, Any]) -> int:
    deleted = 0
    for entry in list(list_addon_remote_caches(config)):
        if entry.tracked:
            continue
        purpose = entry.purpose if entry.purpose in PROMPT_CACHE_PURPOSES else None
        delete_remote_prompt_cache(config, entry.name, purpose=purpose)
        deleted += 1
    return deleted


def cleanup_orphan_remote_caches(
    config: dict[str, Any],
    purpose: Purpose,
    *,
    keep_name: str | None = None,
) -> None:
    from .dev_mock import is_dev_mock_enabled

    api_key = (config.get("api_key") or "").strip()
    if not api_key and not is_dev_mock_enabled(config):
        return
    timeout = int(config.get("timeout_seconds") or 30)
    try:
        for entry in list_addon_remote_caches(config):
            if entry.purpose != purpose:
                continue
            if keep_name and entry.name == keep_name:
                continue
            if entry.tracked and keep_name != entry.name:
                continue
            _delete_remote_cache_best_effort(
                api_key=api_key,
                cache_name=entry.name,
                timeout=timeout,
                config=config,
            )
            _clear_store_if_matches(get_prompt_cache_store(purpose), entry.name)
    except PromptCacheError:
        pass
    _persist_stores()


def _verify_active_remote_cache(
    config: dict[str, Any],
    active: ActivePromptCache,
) -> bool:
    from .dev_mock import (
        is_dev_mock_cache_name,
        is_dev_mock_enabled,
        mock_get_cached_content,
    )

    if is_dev_mock_enabled(config):
        if not is_dev_mock_cache_name(active.name):
            return False
        try:
            mock_get_cached_content(cache_name=active.name)
            return True
        except PromptCacheNotFoundError:
            return False

    api_key = (config.get("api_key") or "").strip()
    if not api_key:
        return False
    timeout = int(config.get("timeout_seconds") or 30)
    try:
        get_cached_content(
            api_key=api_key,
            cache_name=active.name,
            timeout=timeout,
            config=config,
        )
        return True
    except PromptCacheNotFoundError:
        return False
    except PromptCacheError:
        return True


def abandon_stale_prompt_cache(
    config: dict[str, Any],
    *,
    purpose: Purpose,
    bundle: PromptCacheBundle | None,
) -> None:
    store = get_prompt_cache_store(purpose)
    active = store.active
    if active is None or bundle is None:
        return
    model = resolve_model(config, purpose)
    if _cache_is_valid(active, model=model, fingerprint=bundle.fingerprint):
        return
    from .dev_mock import is_dev_mock_enabled

    api_key = (config.get("api_key") or "").strip()
    timeout = int(config.get("timeout_seconds") or 30)
    if api_key or is_dev_mock_enabled(config):
        _delete_remote_cache_best_effort(
            api_key=api_key,
            cache_name=active.name,
            timeout=timeout,
            config=config,
        )
    _set_store_active(store, None)


class PromptCacheError(Exception):
    pass


class PromptCacheNotFoundError(PromptCacheError):
    def __init__(self, cache_name: str) -> None:
        super().__init__(cache_name)
        self.cache_name = cache_name


def _cache_is_valid(active: ActivePromptCache, *, model: str, fingerprint: str) -> bool:
    if active.model != model:
        return False
    if active.fingerprint != fingerprint:
        return False
    return active.expire_at > time.time()


def prompt_cache_created_stats(active: ActivePromptCache) -> tuple[int, int]:
    minutes = max(1, int(active.ttl_seconds) // 60)
    return int(active.cached_char_count), minutes


def ensure_prompt_cache(
    *,
    config: dict[str, Any],
    purpose: Purpose,
    bundle: PromptCacheBundle | None,
    store: PromptCacheStore | None = None,
    allow_create: bool = True,
) -> PromptCacheEnsureResult:
    from .dev_mock import is_dev_mock_enabled

    global _orphans_reconciled
    cache_store = store or get_prompt_cache_store(purpose)
    cache_store.last_error = ""
    if bundle is None:
        return PromptCacheEnsureResult()

    api_key = (config.get("api_key") or "").strip()
    if not api_key and not is_dev_mock_enabled(config):
        return PromptCacheEnsureResult()

    if prompt_cache_enabled(config) and not _orphans_reconciled:
        _orphans_reconciled = True
        try:
            delete_untracked_addon_caches(config)
        except PromptCacheError:
            pass

    model = resolve_model(config, purpose)
    active = cache_store.active
    if active is not None and not _verify_active_remote_cache(config, active):
        _set_store_active(cache_store, None)
        active = None

    if active is not None and _cache_is_valid(active, model=model, fingerprint=bundle.fingerprint):
        return PromptCacheEnsureResult(active=active, created=False)

    if not allow_create:
        if active is not None:
            abandon_stale_prompt_cache(config, purpose=purpose, bundle=bundle)
        return PromptCacheEnsureResult()

    timeout = int(config.get("timeout_seconds") or 30)
    ttl_seconds = prompt_cache_ttl_seconds(config, purpose)

    if active is not None:
        _delete_remote_cache_best_effort(
            api_key=api_key,
            cache_name=active.name,
            timeout=timeout,
            config=config,
        )
        _set_store_active(cache_store, None)

    cleanup_orphan_remote_caches(config, purpose, keep_name=None)

    try:
        created = create_cached_content(
            api_key=api_key,
            model=model,
            bundle=bundle,
            ttl_seconds=ttl_seconds,
            display_name=display_name_for_purpose(purpose),
            purpose=purpose,
            timeout=timeout,
            config=config,
        )
        _set_store_active(cache_store, created)
        cleanup_orphan_remote_caches(config, purpose, keep_name=created.name)
        return PromptCacheEnsureResult(active=created, created=True)
    except (PromptCacheError, requests.RequestException) as exc:
        cache_store.last_error = str(exc)
        _set_store_active(cache_store, None)
        return PromptCacheEnsureResult()


def extend_prompt_cache_ttl(
    *,
    config: dict[str, Any],
    purpose: Purpose,
    extra_seconds: int | None = None,
) -> bool:
    from .dev_mock import is_dev_mock_enabled

    store = get_prompt_cache_store(purpose)
    active = store.active
    if active is None:
        return False
    api_key = (config.get("api_key") or "").strip()
    if not api_key and not is_dev_mock_enabled(config):
        return False
    ttl_seconds = extra_seconds if extra_seconds is not None else prompt_cache_change_ttl_seconds(config)
    timeout = int(config.get("timeout_seconds") or 30)
    try:
        expire_at = update_cached_content_ttl(
            api_key=api_key,
            cache_name=active.name,
            ttl_seconds=ttl_seconds,
            timeout=timeout,
            config=config,
        )
        active.expire_at = expire_at
        active.ttl_seconds = ttl_seconds
        _persist_stores()
        return True
    except (PromptCacheError, requests.RequestException) as exc:
        store.last_error = str(exc)
    return False


def reset_local_prompt_cache_tracking() -> None:
    for purpose in PROMPT_CACHE_PURPOSES:
        store = get_prompt_cache_store(purpose)
        _set_store_active(store, None)
        store.last_error = ""
    _persist_stores()


def clear_prompt_cache(
    *,
    config: dict[str, Any],
    purpose: Purpose | None = None,
) -> None:
    from .dev_mock import is_dev_mock_enabled

    api_key = (config.get("api_key") or "").strip()
    timeout = int(config.get("timeout_seconds") or 30)
    purposes: list[Purpose] = [purpose] if purpose is not None else list(PROMPT_CACHE_PURPOSES)
    for item in purposes:
        store = get_prompt_cache_store(item)
        active = store.active
        if active is not None and (api_key or is_dev_mock_enabled(config)):
            _delete_remote_cache_best_effort(
                api_key=api_key,
                cache_name=active.name,
                timeout=timeout,
                config=config,
            )
        _set_store_active(store, None)
        store.last_error = ""
        if api_key:
            cleanup_orphan_remote_caches(config, item, keep_name=None)


def _purpose_status_label(config: dict[str, Any], purpose: Purpose) -> str:
    return tr(f"settings.prompt_cache.manager.purpose.{purpose}", config=config)


def prompt_cache_status_text(config: dict[str, Any], purpose: Purpose) -> str:
    store = get_prompt_cache_store(purpose)
    active = store.active
    purpose_label = _purpose_status_label(config, purpose)
    if active is None:
        if store.last_error:
            return tr(
                "settings.prompt_cache.status.error",
                config=config,
                purpose=purpose_label,
                error=store.last_error[:120],
            )
        return tr("settings.prompt_cache.status.inactive", config=config, purpose=purpose_label)
    remaining = max(0, int(active.expire_at - time.time()))
    minutes = remaining // 60
    return tr(
        "settings.prompt_cache.status.active",
        config=config,
        purpose=purpose_label,
        chars=active.cached_char_count,
        minutes=minutes,
    )


def invalidate_prompt_cache_for_config_change() -> None:
    for purpose in PROMPT_CACHE_PURPOSES:
        store = get_prompt_cache_store(purpose)
        store.active = None
        store.last_error = ""
    _persist_stores()


def build_live_system_instruction(
    config: dict[str, Any],
    *,
    purpose: Purpose,
    include_meta_rule: bool,
    bundle: PromptCacheBundle | None,
) -> str:
    if bundle is None:
        from .gemini_client import merge_system_instructions

        return merge_system_instructions(
            config,
            include_meta_rule=include_meta_rule,
            purpose=purpose,
        )

    live = bundle.live_system_text.strip()
    if purpose == "chat" and include_meta_rule and "chat_system_addon" not in bundle.enabled_segment_ids:
        addon = effective_chat_system_addon(config)
        if addon.strip():
            live = join_prompt_blocks(live, addon)
    return live
