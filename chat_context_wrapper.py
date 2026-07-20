from __future__ import annotations

from .prompt_compose import join_prompt_blocks

WRAPPER_SECTION_IDS = ("context", "format_guide", "templates", "styling", "request")
# Request early so the model sees the task before long context/templates.
DEFAULT_WRAPPER_SECTION_ORDER = (
    "request",
    "context",
    "format_guide",
    "templates",
    "styling",
)
PLACEHOLDER_SECTIONS = ("context", "templates", "styling", "request")


def wrapper_content_tag(section: str) -> str:
    return f"{{{{{section}}}}}"


def import_templates_enabled(config: dict[str, Any] | None) -> bool:
    return bool((config or {}).get("brain_import_templates", False))


def import_css_enabled(config: dict[str, Any] | None) -> bool:
    return bool((config or {}).get("brain_import_css", False))


def apply_wrapper_placeholders(
    body: str,
    *,
    context: str,
    request: str,
    templates: str,
    styling: str,
) -> str:
    result = body
    for section, value in (
        ("context", context),
        ("request", request),
        ("templates", templates),
        ("styling", styling),
    ):
        tag = wrapper_content_tag(section)
        if tag in result:
            result = result.replace(tag, value)
    return result


def normalize_wrapper_section_order(order: list[str] | tuple[str, ...] | None) -> list[str]:
    seen: list[str] = []
    for section_id in order or ():
        if section_id in WRAPPER_SECTION_IDS and section_id not in seen:
            seen.append(section_id)
    for section_id in DEFAULT_WRAPPER_SECTION_ORDER:
        if section_id not in seen:
            seen.append(section_id)
    return seen


def wrapper_section_active(
    section_id: str,
    config: dict[str, Any] | None,
    *,
    include_context: bool,
    context: str,
    templates: str,
    styling: str,
    format_guide: str,
    omit_format_guide: bool,
    preview: bool = False,
    active_context: str | None = None,
    active_templates: str | None = None,
    active_styling: str | None = None,
    section_prefixes: dict[str, str] | None = None,
) -> bool:
    context_probe = active_context if active_context is not None else context
    templates_probe = active_templates if active_templates is not None else templates
    styling_probe = active_styling if active_styling is not None else styling
    prefixes = section_prefixes or {}

    def _prefix_allows_content(target_id: str) -> bool:
        if target_id not in PLACEHOLDER_SECTIONS:
            return True
        prefix = (prefixes.get(target_id) or "").strip()
        if not prefix:
            return True
        return wrapper_content_tag(target_id) in prefix

    if section_id == "context":
        if not include_context:
            return False
        prefix = (prefixes.get("context") or "").strip()
        if not prefix:
            return False
        if not _prefix_allows_content("context"):
            return False
        return preview or bool(context_probe.strip())
    if section_id == "format_guide":
        if omit_format_guide:
            return False
        if not format_guide.strip():
            return False
        templates_active = wrapper_section_active(
            "templates",
            config,
            include_context=include_context,
            context=context,
            templates=templates,
            styling=styling,
            format_guide=format_guide,
            omit_format_guide=True,
            preview=preview,
            active_context=active_context,
            active_templates=active_templates,
            active_styling=active_styling,
            section_prefixes=prefixes,
        )
        styling_active = wrapper_section_active(
            "styling",
            config,
            include_context=include_context,
            context=context,
            templates=templates,
            styling=styling,
            format_guide=format_guide,
            omit_format_guide=True,
            preview=preview,
            active_context=active_context,
            active_templates=active_templates,
            active_styling=active_styling,
            section_prefixes=prefixes,
        )
        return templates_active or styling_active
    if section_id == "templates":
        if not include_context:
            return False
        if not import_templates_enabled(config):
            return False
        prefix = (prefixes.get("templates") or "").strip()
        if not prefix:
            return False
        if not _prefix_allows_content("templates"):
            return False
        return preview or bool(templates_probe.strip())
    if section_id == "styling":
        if not include_context:
            return False
        if not import_css_enabled(config):
            return False
        prefix = (prefixes.get("styling") or "").strip()
        if not prefix:
            return False
        if not _prefix_allows_content("styling"):
            return False
        return preview or bool(styling_probe.strip())
    if section_id == "request":
        return True
    return False


def wrapper_section_missing_placeholders(section_id: str, text: str) -> bool:
    if section_id == "format_guide":
        return False
    if section_id not in PLACEHOLDER_SECTIONS:
        return False
    stripped = (text or "").strip()
    if not stripped:
        return False
    return wrapper_content_tag(section_id) not in stripped


def wrapper_sections_missing_required(
    sections: dict[str, str],
    *,
    order: list[str] | None = None,
) -> bool:
    for section_id in order or WRAPPER_SECTION_IDS:
        if section_id == "request" and wrapper_section_missing_placeholders(
            section_id, sections.get(section_id, "")
        ):
            return True
    return False


def wrapper_missing_import_placeholders(
    sections: dict[str, str],
    config: dict[str, Any] | None,
    *,
    default_sections: dict[str, str] | None = None,
) -> list[str]:
    missing: list[str] = []
    defaults = default_sections or {}
    for section_id in ("templates", "styling"):
        if section_id == "templates" and not import_templates_enabled(config):
            continue
        if section_id == "styling" and not import_css_enabled(config):
            continue
        text = (sections.get(section_id) or defaults.get(section_id) or "").strip()
        if text and wrapper_content_tag(section_id) not in text:
            missing.append(section_id)
    return missing


def _collapse_blank_lines(text: str, *, max_blank_lines: int = 2) -> str:
    collapsed: list[str] = []
    blank_run = 0
    for line in text.splitlines():
        if not line.strip():
            blank_run += 1
            if blank_run <= max_blank_lines:
                collapsed.append(line)
            continue
        blank_run = 0
        collapsed.append(line)
    return "\n".join(collapsed).strip()


def _render_section_text(
    section_id: str,
    prefix: str,
    *,
    context: str,
    request: str,
    templates: str,
    styling: str,
    format_guide: str,
) -> str:
    if section_id == "format_guide":
        return format_guide.strip()
    return apply_wrapper_placeholders(
        prefix,
        context=context,
        request=request,
        templates=templates,
        styling=styling,
    ).strip()


def assemble_wrapper_message(
    config: dict[str, Any] | None,
    *,
    section_order: list[str],
    section_prefixes: dict[str, str],
    context: str,
    request: str,
    templates: str = "",
    styling: str = "",
    format_guide: str = "",
    include_context: bool = True,
    omit_format_guide: bool = False,
    omit_sections: set[str] | None = None,
    preview: bool = False,
    active_context: str | None = None,
    active_templates: str | None = None,
    active_styling: str | None = None,
) -> str:
    omitted = omit_sections or set()
    parts: list[str] = []
    for section_id in normalize_wrapper_section_order(section_order):
        if section_id in omitted:
            continue
        prefix = (section_prefixes.get(section_id) or "").strip()
        if section_id != "format_guide" and not prefix:
            continue
        if not wrapper_section_active(
            section_id,
            config,
            include_context=include_context,
            context=context,
            templates=templates,
            styling=styling,
            format_guide=format_guide,
            omit_format_guide=omit_format_guide,
            preview=preview,
            active_context=active_context,
            active_templates=active_templates,
            active_styling=active_styling,
            section_prefixes=section_prefixes,
        ):
            continue
        rendered = _render_section_text(
            section_id,
            prefix,
            context=context,
            request=request,
            templates=templates,
            styling=styling,
            format_guide=format_guide,
        )
        if rendered:
            parts.append(rendered)
    return _join_wrapper_sections(parts)


def _join_wrapper_sections(parts: list[str]) -> str:
    collapsed = [_collapse_blank_lines(part.strip()) for part in parts if part and part.strip()]
    return join_prompt_blocks(*collapsed)


def build_cache_safe_wrapper(
    config: dict[str, Any] | None,
    *,
    section_order: list[str],
    section_prefixes: dict[str, str],
    cache_imported_note: bool,
    cache_format_guide: bool,
    cache_templates: bool,
    cache_styling: bool,
    context_content: str = "",
    templates_content: str = "",
    styling_content: str = "",
    format_guide: str = "",
) -> str:
    omit: set[str] = {"request"}
    if cache_imported_note:
        omit.add("context")
    if cache_format_guide:
        omit.add("format_guide")
    if cache_templates:
        omit.add("templates")
    if cache_styling:
        omit.add("styling")
    return assemble_wrapper_message(
        config,
        section_order=section_order,
        section_prefixes=section_prefixes,
        context=wrapper_content_tag("context") if context_content.strip() else "",
        request="",
        templates=wrapper_content_tag("templates") if templates_content.strip() else "",
        styling=wrapper_content_tag("styling") if styling_content.strip() else "",
        format_guide=format_guide,
        include_context=True,
        omit_format_guide=False,
        omit_sections=omit,
        active_context=context_content,
        active_templates=templates_content,
        active_styling=styling_content,
    )


def build_live_request_message(
    config: dict[str, Any] | None,
    *,
    section_order: list[str],
    section_prefixes: dict[str, str],
    request: str,
) -> str:
    rendered = assemble_wrapper_message(
        config,
        section_order=section_order,
        section_prefixes=section_prefixes,
        context="",
        request=request,
        include_context=False,
        omit_sections={"context", "format_guide", "templates", "styling"},
    )
    return rendered if rendered.strip() else request


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
    resolve_wrapper_layout: Callable[[dict[str, Any] | None], tuple[list[str], dict[str, str]]],
    resolve_format_guide: Callable[[dict[str, Any] | None], str],
) -> str:
    base_order, base_prefixes = resolve_wrapper_layout(config)
    order = normalize_wrapper_section_order(section_order) if section_order is not None else base_order
    prefixes = dict(base_prefixes)
    if section_prefixes is not None:
        prefixes.update(section_prefixes)
    guide = resolve_format_guide(config) if format_guide is None else format_guide

    if wrapper_sections_missing_required(prefixes, order=order):
        order = base_order
        prefixes = dict(base_prefixes)
        guide = resolve_format_guide(config) if format_guide is None else format_guide
        if wrapper_sections_missing_required(prefixes, order=order):
            order, prefixes = resolve_wrapper_layout(None)
            guide = resolve_format_guide(None) if format_guide is None else format_guide

    rendered = assemble_wrapper_message(
        config,
        section_order=order,
        section_prefixes=prefixes,
        context=context,
        request=request,
        templates=templates or "",
        styling=styling or "",
        format_guide=guide,
        include_context=include_context,
        omit_format_guide=omit_format_guide,
        omit_sections=omit_sections,
    )
    if rendered.strip():
        return rendered
    if not include_context or not context.strip():
        return build_live_request_message(
            config,
            section_order=order,
            section_prefixes=prefixes,
            request=request,
        )
    return request
