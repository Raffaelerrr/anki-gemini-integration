from __future__ import annotations

import re
from typing import Any

from .chat_context_wrapper import (
    DEFAULT_WRAPPER_SECTION_ORDER,
    PLACEHOLDER_SECTIONS,
    WRAPPER_SECTION_IDS,
    apply_wrapper_placeholders,
    assemble_wrapper_message,
    format_chat_context_message as _format_chat_context_message_core,
    import_css_enabled,
    import_templates_enabled,
    normalize_wrapper_section_order,
    wrapper_content_tag,
    wrapper_missing_import_placeholders,
    wrapper_section_missing_placeholders,
    wrapper_sections_missing_required,
)
from .i18n_strings import _STRINGS

LANG_IT = "it"
LANG_EN = "en"
SUPPORTED_LANGUAGES = (LANG_IT, LANG_EN)
DEFAULT_LANGUAGE = LANG_EN

_ICON_PLACEHOLDER_RE = re.compile(r"\{icon:[^}]+\}")
_ICON_PLACEHOLDER_SENTINEL = "__ANKI_AI_ICON_{}__"


def _shield_icon_placeholders(text: str) -> tuple[str, list[str]]:
    icons: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        icons.append(match.group(0))
        return _ICON_PLACEHOLDER_SENTINEL.format(len(icons) - 1)

    return _ICON_PLACEHOLDER_RE.sub(_replace, text), icons


def _restore_icon_placeholders(text: str, icons: list[str]) -> str:
    for index, icon in enumerate(icons):
        text = text.replace(_ICON_PLACEHOLDER_SENTINEL.format(index), icon)
    return text


def normalize_language(language: str | None) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    normalized = str(language).lower()
    if normalized.startswith(LANG_IT):
        return LANG_IT
    if normalized.startswith(LANG_EN):
        return LANG_EN
    return DEFAULT_LANGUAGE


def get_language(config: dict[str, Any] | None = None) -> str:
    if config is None:
        from .config import load_config

        config = load_config()
    return normalize_language(config.get("language"))


def tr(key: str, *, config: dict[str, Any] | None = None, lang: str | None = None, **kwargs: Any) -> str:
    language = lang or get_language(config)
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(language) or entry.get(DEFAULT_LANGUAGE) or key
    if kwargs:
        text, icons = _shield_icon_placeholders(text)
        text = text.format(**kwargs)
        text = _restore_icon_placeholders(text, icons)
        return text
    return text


def default_brain_import_message(config: dict[str, Any] | None = None) -> str:
    return tr("defaults.brain_import_message", config=config)


def default_system_instruction(config: dict[str, Any] | None = None) -> str:
    return tr("defaults.system_instruction", config=config)


def system_instruction_shared(config: dict[str, Any] | None = None) -> bool:
    return bool((config or {}).get("system_instruction_shared", True))


def system_instruction_storage_key(purpose: str, config: dict[str, Any] | None = None) -> str:
    cfg = config or {}
    if system_instruction_shared(cfg):
        return "system_instruction"
    if purpose == "chat":
        return "system_instruction_chat"
    return "system_instruction_optimize"


def _builtin_brain_import_messages() -> frozenset[str]:
    return frozenset(
        message.strip()
        for message in (
            _STRINGS["defaults.brain_import_message"][LANG_IT],
            _STRINGS["defaults.brain_import_message"][LANG_EN],
        )
        if message.strip()
    )


def is_builtin_brain_import_message(text: str | None) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    return stripped in _builtin_brain_import_messages()


def effective_brain_import_message(config: dict[str, Any] | None = None) -> str:
    stored = ((config or {}).get("brain_import_message") or "").strip()
    if is_builtin_brain_import_message(stored):
        return default_brain_import_message(config)
    return stored


def normalize_brain_import_message_for_save(text: str, config: dict[str, Any]) -> str:
    stripped = (text or "").strip()
    if is_builtin_brain_import_message(stripped):
        return ""
    return stripped


def _builtin_prompt_texts(i18n_key: str) -> frozenset[str]:
    entry = _STRINGS.get(i18n_key) or {}
    return frozenset(
        message.strip()
        for message in (entry.get(LANG_IT), entry.get(LANG_EN))
        if message and message.strip()
    )


def _is_builtin_prompt(text: str | None, i18n_key: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    return stripped in _builtin_prompt_texts(i18n_key)


def _effective_prompt(config: dict[str, Any] | None, config_key: str, i18n_key: str) -> str:
    stored_raw = (config or {}).get(config_key) or ""
    if _is_builtin_prompt(stored_raw, i18n_key):
        return tr(i18n_key, config=config)
    return stored_raw


def _normalize_prompt_for_save(text: str, i18n_key: str) -> str:
    stripped = (text or "").strip()
    if _is_builtin_prompt(stripped, i18n_key):
        return ""
    return stripped


def default_optimize_user_prompt(config: dict[str, Any] | None = None) -> str:
    return tr("instructions.optimize_user_prompt", config=config)


def is_builtin_optimize_user_prompt(text: str | None) -> bool:
    return _is_builtin_prompt(text, "instructions.optimize_user_prompt")


def effective_optimize_user_prompt(config: dict[str, Any] | None = None) -> str:
    return _effective_prompt(config, "prompt_optimize_user", "instructions.optimize_user_prompt")


def normalize_optimize_user_prompt_for_save(text: str) -> str:
    return _normalize_prompt_for_save(text, "instructions.optimize_user_prompt")


def default_chat_system_addon(config: dict[str, Any] | None = None) -> str:
    return tr("instructions.chat_system_addon", config=config)


def is_builtin_chat_system_addon(text: str | None) -> bool:
    return _is_builtin_prompt(text, "instructions.chat_system_addon")


def effective_chat_system_addon(config: dict[str, Any] | None = None) -> str:
    return _effective_prompt(config, "prompt_chat_addon", "instructions.chat_system_addon")


def normalize_chat_system_addon_for_save(text: str) -> str:
    return _normalize_prompt_for_save(text, "instructions.chat_system_addon")


def default_dynamic_rules_prefix(config: dict[str, Any] | None = None) -> str:
    return tr("instructions.dynamic_rules_prefix", config=config)


def is_builtin_dynamic_rules_prefix(text: str | None) -> bool:
    return _is_builtin_prompt(text, "instructions.dynamic_rules_prefix")


def effective_dynamic_rules_prefix(config: dict[str, Any] | None = None) -> str:
    return _effective_prompt(config, "prompt_dynamic_rules_prefix", "instructions.dynamic_rules_prefix")


def normalize_dynamic_rules_prefix_for_save(text: str) -> str:
    return _normalize_prompt_for_save(text, "instructions.dynamic_rules_prefix")


def default_wrapper_section_text(section_id: str, config: dict[str, Any] | None = None) -> str:
    if section_id == "format_guide":
        return ""
    return tr(f"instructions.chat_context_section.{section_id}", config=config)


def default_wrapper_section_order(config: dict[str, Any] | None = None) -> list[str]:
    return list(DEFAULT_WRAPPER_SECTION_ORDER)


def default_wrapper_sections(config: dict[str, Any] | None = None) -> dict[str, str]:
    return {
        section_id: default_wrapper_section_text(section_id, config)
        for section_id in WRAPPER_SECTION_IDS
        if section_id != "format_guide"
    }


def is_builtin_wrapper_section(section_id: str, text: str | None) -> bool:
    if section_id == "format_guide":
        return not (text or "").strip()
    stripped = (text or "").strip()
    if not stripped:
        return True
    return stripped in _builtin_prompt_texts(
        f"instructions.chat_context_section.{section_id}"
    )


def normalize_wrapper_sections_for_save(
    sections: dict[str, str],
    config: dict[str, Any] | None = None,
) -> dict[str, str]:
    defaults = default_wrapper_sections(config)
    normalized: dict[str, str] = {}
    for section_id in WRAPPER_SECTION_IDS:
        if section_id == "format_guide":
            continue
        if section_id not in sections:
            continue
        raw = sections.get(section_id) or ""
        stripped = raw.strip()
        default_stripped = (defaults.get(section_id) or "").strip()
        if stripped == default_stripped:
            continue
        if not stripped:
            normalized[section_id] = ""
            continue
        if is_builtin_wrapper_section(section_id, stripped):
            continue
        normalized[section_id] = stripped
    return normalized


def normalize_wrapper_order_for_save(order: list[str] | None) -> list[str]:
    return normalize_wrapper_section_order(order)


def effective_wrapper_layout(
    config: dict[str, Any] | None = None,
) -> tuple[list[str], dict[str, str]]:
    cfg = config or {}
    order = normalize_wrapper_section_order(cfg.get("prompt_chat_context_order"))
    stored = cfg.get("prompt_chat_context_sections") or {}
    defaults = default_wrapper_sections(config)
    prefixes: dict[str, str] = {"format_guide": ""}
    for section_id in WRAPPER_SECTION_IDS:
        if section_id == "format_guide":
            continue
        if section_id not in stored:
            prefixes[section_id] = defaults.get(section_id, "")
            continue
        custom = (stored.get(section_id) or "").strip()
        if not custom:
            prefixes[section_id] = ""
        elif is_builtin_wrapper_section(section_id, custom):
            prefixes[section_id] = defaults.get(section_id, "")
        else:
            prefixes[section_id] = custom
    return order, prefixes


def is_builtin_wrapper_layout(
    config: dict[str, Any] | None,
    *,
    section_order: list[str] | None = None,
    section_prefixes: dict[str, str] | None = None,
) -> bool:
    cfg = config or {}
    order = normalize_wrapper_section_order(section_order or cfg.get("prompt_chat_context_order"))
    if order != list(DEFAULT_WRAPPER_SECTION_ORDER):
        return False
    stored = section_prefixes if section_prefixes is not None else (cfg.get("prompt_chat_context_sections") or {})
    for section_id in WRAPPER_SECTION_IDS:
        if section_id == "format_guide":
            continue
        text = (stored.get(section_id) or "").strip()
        if text and not is_builtin_wrapper_section(section_id, text):
            return False
    if not is_builtin_card_templates_format_prompt(cfg.get("prompt_card_templates_format")):
        stored_format = (cfg.get("prompt_card_templates_format") or "").strip()
        if stored_format:
            return False
    return True


def wrapper_layout_warnings(
    section_prefixes: dict[str, str],
    config: dict[str, Any] | None,
) -> list[str]:
    _, defaults = effective_wrapper_layout(config)
    warnings: list[str] = []
    request_text = (section_prefixes.get("request") or defaults.get("request") or "").strip()
    if wrapper_section_missing_placeholders("request", request_text):
        warnings.append("required")
    warnings.extend(
        wrapper_missing_import_placeholders(
            section_prefixes,
            config,
            default_sections=defaults,
        )
    )
    return warnings


def build_wrapper_preview(
    config: dict[str, Any] | None = None,
    *,
    section_order: list[str] | None = None,
    section_prefixes: dict[str, str] | None = None,
    format_guide: str | None = None,
    templates_content: str = "",
    styling_content: str = "",
) -> str:
    order, prefixes = effective_wrapper_layout(config)
    if section_order is not None:
        order = normalize_wrapper_section_order(section_order)
    if section_prefixes is not None:
        prefixes = dict(section_prefixes)
        prefixes.setdefault("format_guide", "")
    guide = (
        effective_card_templates_format_prompt(config)
        if format_guide is None
        else format_guide
    )
    return assemble_wrapper_message(
        config,
        section_order=order,
        section_prefixes=prefixes,
        context="…",
        request="…",
        templates=templates_content or "…",
        styling=styling_content or "…",
        format_guide=guide,
        include_context=True,
        preview=True,
    )


def default_card_templates_format_prompt(config: dict[str, Any] | None = None) -> str:
    return tr("instructions.card_templates_format", config=config)


def is_builtin_card_templates_format_prompt(text: str | None) -> bool:
    return _is_builtin_prompt(text, "instructions.card_templates_format")


def effective_card_templates_format_prompt(config: dict[str, Any] | None = None) -> str:
    return _effective_prompt(
        config,
        "prompt_card_templates_format",
        "instructions.card_templates_format",
    )


def normalize_card_templates_format_prompt_for_save(text: str) -> str:
    return _normalize_prompt_for_save(text, "instructions.card_templates_format")


def effective_mathjax_preview_preamble(config: dict[str, Any] | None = None) -> str:
    return str((config or {}).get("mathjax_preview_preamble") or "").strip()


def normalize_mathjax_preview_preamble_for_save(text: str) -> str:
    return (text or "").strip()


def card_templates_format_addon(
    config: dict[str, Any] | None,
    *,
    templates: str,
    styling: str,
) -> str:
    if not templates.strip() and not styling.strip():
        return ""
    return effective_card_templates_format_prompt(config).strip()


def chat_edit_wrapper_label_text(config: dict[str, Any] | None = None) -> str:
    config = config or {}
    if import_templates_enabled(config) or import_css_enabled(config):
        return tr("chat.edit_wrapper.wrapper_label.with_optional", config=config)
    return tr("chat.edit_wrapper.wrapper_label.basic", config=config)


def chat_edit_wrapper_hint_text(config: dict[str, Any] | None = None) -> str:
    config = config or {}
    if import_templates_enabled(config) or import_css_enabled(config):
        return tr("chat.edit_wrapper.wrapper_hint.with_optional", config=config)
    return tr("chat.edit_wrapper.wrapper_hint.basic", config=config)


def chat_edit_wrapper_invalid_text(config: dict[str, Any] | None = None) -> str:
    return tr("chat.edit_wrapper.wrapper_invalid", config=config)


def wrapper_import_warning_text(
    config: dict[str, Any] | None,
    *,
    sections: list[str],
    scope: str = "settings",
) -> str:
    parts: list[str] = []
    for section in sections:
        if section == "required" and scope == "chat":
            key = "chat.wrapper_import_warning.required"
        else:
            key = f"settings.wrapper_import_warning.{section}"
        parts.append(tr(key, config=config))
    return " ".join(parts)


def _resolve_wrapper_layout(config: dict[str, Any] | None) -> tuple[list[str], dict[str, str]]:
    return effective_wrapper_layout(config)


def _resolve_format_guide(config: dict[str, Any] | None) -> str:
    return effective_card_templates_format_prompt(config).strip()


def format_chat_context_message(
    config: dict[str, Any] | None,
    *,
    context: str,
    request: str,
    templates: str = "",
    styling: str = "",
    include_context: bool = True,
    omit_format_guide: bool = False,
    section_order: list[str] | None = None,
    section_prefixes: dict[str, str] | None = None,
    format_guide: str | None = None,
    omit_sections: set[str] | None = None,
) -> str:
    return _format_chat_context_message_core(
        config,
        context=context,
        request=request,
        templates=templates,
        styling=styling,
        include_context=include_context,
        omit_format_guide=omit_format_guide,
        section_order=section_order,
        section_prefixes=section_prefixes,
        format_guide=format_guide,
        omit_sections=omit_sections,
        resolve_wrapper_layout=_resolve_wrapper_layout,
        resolve_format_guide=_resolve_format_guide,
    )


def chat_edit_templates_title_text(
    config: dict[str, Any] | None = None,
    *,
    notetype_name: str | None = None,
) -> str:
    templates = import_templates_enabled(config)
    css = import_css_enabled(config)
    if templates and css:
        base = tr("chat.edit_templates.title", config=config)
    elif css and not templates:
        base = tr("chat.edit_templates.title.styling_only", config=config)
    else:
        base = tr("chat.edit_templates.title.templates_only", config=config)
    name = (notetype_name or "").strip()
    if name:
        return f"{base} {name}"
    return base


def chat_edit_templates_detail_text(config: dict[str, Any] | None = None) -> str:
    return tr("chat.edit_templates.detail", config=config)


def chat_edit_templates_hint_text(config: dict[str, Any] | None = None) -> str:
    templates = import_templates_enabled(config)
    css = import_css_enabled(config)
    if templates and css:
        return tr("chat.edit_templates.hint", config=config)
    if css and not templates:
        return tr("chat.edit_templates.hint.styling_only", config=config)
    return tr("chat.edit_templates.hint.templates_only", config=config)


def _builtin_system_instructions() -> frozenset[str]:
    return frozenset(
        message.strip()
        for message in (
            _STRINGS["defaults.system_instruction"][LANG_IT],
            _STRINGS["defaults.system_instruction"][LANG_EN],
        )
        if message.strip()
    )


def is_builtin_system_instruction(text: str | None) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    return stripped in _builtin_system_instructions()


def effective_system_instruction(
    config: dict[str, Any] | None = None,
    *,
    purpose: str = "optimize",
) -> str:
    cfg = config or {}
    key = system_instruction_storage_key(purpose, cfg)
    stored = (cfg.get(key) or "").strip()
    if is_builtin_system_instruction(stored):
        return default_system_instruction(cfg)
    return stored


def normalize_system_instruction_for_save(text: str, config: dict[str, Any], field_key: str) -> str:
    stripped = (text or "").strip()
    if is_builtin_system_instruction(stripped):
        return ""
    return stripped


def normalize_system_instruction_fields_for_save(
    *,
    shared: bool,
    shared_text: str,
    optimize_text: str,
    chat_text: str,
    config: dict[str, Any],
) -> dict[str, str | bool]:
    if shared:
        return {
            "system_instruction_shared": True,
            "system_instruction": normalize_system_instruction_for_save(
                shared_text, config, "system_instruction"
            ),
            "system_instruction_optimize": "",
            "system_instruction_chat": "",
        }
    return {
        "system_instruction_shared": False,
        "system_instruction": "",
        "system_instruction_optimize": normalize_system_instruction_for_save(
            optimize_text, config, "system_instruction_optimize"
        ),
        "system_instruction_chat": normalize_system_instruction_for_save(
            chat_text, config, "system_instruction_chat"
        ),
    }
