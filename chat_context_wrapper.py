from __future__ import annotations

import re
from typing import Any, Callable

REQUIRED_WRAPPER_SECTIONS = ("context", "request")
CONDITIONAL_WRAPPER_SECTIONS = ("templates", "styling")

_CONDITIONAL_TAG_RE = re.compile(
    r"\{\{#(templates|styling)\}\}|\{\{/(templates|styling)\}\}"
)
_CONDITIONAL_BLOCK_RE: dict[str, re.Pattern[str]] = {}
_CONDITIONAL_BLOCK_RE_INACTIVE: dict[str, re.Pattern[str]] = {}


def _conditional_block_pattern(section: str) -> re.Pattern[str]:
    cached = _CONDITIONAL_BLOCK_RE.get(section)
    if cached is not None:
        return cached
    open_tag = re.escape(wrapper_open_tag(section))
    close_tag = re.escape(wrapper_close_tag(section))
    pattern = re.compile(open_tag + r"(.*?)" + close_tag, re.DOTALL)
    _CONDITIONAL_BLOCK_RE[section] = pattern
    return pattern


def _conditional_block_pattern_inactive(section: str) -> re.Pattern[str]:
    """Pattern for when a conditional block is removed.

    Besides removing the open tag, inner content, and close tag, it also
    consumes the blank separator lines that belong to the removed block.
    If the block ends the wrapper, the trailing newline is optional.
    """
    cached = _CONDITIONAL_BLOCK_RE_INACTIVE.get(section)
    if cached is not None:
        return cached
    open_tag = re.escape(wrapper_open_tag(section))
    close_tag = re.escape(wrapper_close_tag(section))
    pattern = re.compile(
        open_tag + r"(.*?)" + close_tag + r"[ \t]*(?:\n(?:[ \t]*\n)*)?",
        re.DOTALL,
    )
    _CONDITIONAL_BLOCK_RE_INACTIVE[section] = pattern
    return pattern


def wrapper_open_tag(section: str) -> str:
    return f"{{{{#{section}}}}}"


def wrapper_close_tag(section: str) -> str:
    return f"{{{{/{section}}}}}"


def wrapper_content_tag(section: str) -> str:
    return f"{{{{{section}}}}}"


def repair_wrapper_brace_escaping(text: str) -> str:
    """Collapse mistaken quadruple-brace wrapper tags from a past i18n escaping bug."""
    if "{{{{" not in text:
        return text
    return text.replace("{{{{", "{{").replace("}}}}", "}}")


def wrapper_has_conditional_blocks(text: str | None) -> bool:
    return bool(text and _CONDITIONAL_TAG_RE.search(text))


def import_templates_enabled(config: dict[str, Any] | None) -> bool:
    return bool((config or {}).get("brain_import_templates", False))


def import_css_enabled(config: dict[str, Any] | None) -> bool:
    return bool((config or {}).get("brain_import_css", False))


def chat_context_wrapper_missing_placeholders(text: str | None) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    return any(
        wrapper_content_tag(section) not in stripped
        for section in REQUIRED_WRAPPER_SECTIONS
    )


def chat_context_wrapper_has_unbalanced_conditionals(text: str | None) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    stack: list[str] = []
    for match in _CONDITIONAL_TAG_RE.finditer(stripped):
        if match.group(1):
            stack.append(match.group(1))
            continue
        section = match.group(2)
        if not stack or stack[-1] != section:
            return True
        stack.pop()
    return bool(stack)


def chat_context_wrapper_should_fallback(text: str | None) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    return (
        chat_context_wrapper_missing_placeholders(stripped)
        or chat_context_wrapper_has_unbalanced_conditionals(stripped)
    )


def wrapper_includes_section(text: str | None, section: str) -> bool:
    return wrapper_content_tag(section) in (text or "")


def wrapper_includes_any_import_section(text: str | None) -> bool:
    return wrapper_includes_section(text, "templates") or wrapper_includes_section(text, "styling")


def _card_templates_format_guide_for_message(
    resolved: str,
    config: dict[str, Any] | None,
    *,
    templates_out: str,
    styling_out: str,
    card_templates_format_addon: Callable[..., str],
) -> str:
    if not wrapper_includes_any_import_section(resolved):
        return ""
    return card_templates_format_addon(
        config,
        templates=templates_out,
        styling=styling_out,
    )


def wrapper_missing_import_placeholders(
    text: str | None,
    config: dict[str, Any] | None,
) -> list[str]:
    stripped = (text or "").strip()
    if not stripped:
        return []
    missing: list[str] = []
    if import_templates_enabled(config) and wrapper_content_tag("templates") not in stripped:
        missing.append("templates")
    if import_css_enabled(config) and wrapper_content_tag("styling") not in stripped:
        missing.append("styling")
    return missing


def _section_active(
    section: str,
    config: dict[str, Any] | None,
    content: str,
    *,
    preview: bool,
    wrapper_text: str,
) -> bool:
    if not wrapper_includes_section(wrapper_text, section):
        return False
    if section == "templates":
        enabled = import_templates_enabled(config)
    else:
        enabled = import_css_enabled(config)
    if not enabled:
        return False
    if preview:
        return True
    return bool((content or "").strip())


def process_wrapper_conditionals(
    text: str,
    config: dict[str, Any] | None,
    *,
    templates_content: str = "",
    styling_content: str = "",
    preview: bool = False,
    wrapper_text: str | None = None,
) -> str:
    source = wrapper_text if wrapper_text is not None else text
    result = text
    for section in CONDITIONAL_WRAPPER_SECTIONS:
        content = templates_content if section == "templates" else styling_content
        active = _section_active(
            section,
            config,
            content,
            preview=preview,
            wrapper_text=source,
        )
        result = _apply_conditional_blocks(result, section, active=active)
    return _collapse_blank_lines(result, max_blank_lines=2)


def _apply_conditional_blocks(text: str, section: str, *, active: bool) -> str:
    pattern = _conditional_block_pattern(section) if active else _conditional_block_pattern_inactive(section)

    def replacer(match: re.Match[str]) -> str:
        if not active:
            return ""
        inner = match.group(1)
        # If the open/close tags were on their own lines, the boundary newlines end
        # up inside `inner` (because we don't include \n in the tag match).
        # Strip one leading and one trailing newline to match "delete tag-only lines".
        if inner.startswith("\n"):
            inner = inner[1:]
        if inner.endswith("\n"):
            inner = inner[:-1]
        return inner

    return pattern.sub(replacer, text)


def _collapse_blank_lines(text: str, *, max_blank_lines: int) -> str:
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
        result = result.replace(wrapper_content_tag(section), value)
    # Legacy single-brace placeholders from older custom wrappers.
    result = result.replace("{context}", context)
    result = result.replace("{request}", request)
    result = result.replace("{templates}", templates)
    result = result.replace("{styling}", styling)
    return result


def _inject_before_marker(body: str, marker: str, insert: str) -> str:
    if not insert.strip():
        return body
    if not marker:
        return f"{body.rstrip()}\n\n{insert}"
    index = body.find(marker)
    if index < 0:
        return f"{body.rstrip()}\n\n{insert}"
    return f"{body[:index].rstrip()}\n\n{insert}\n\n{body[index:]}"


def expand_chat_context_wrapper(
    config: dict[str, Any] | None,
    *,
    source: str,
    templates_content: str = "",
    styling_content: str = "",
) -> str:
    stripped = repair_wrapper_brace_escaping((source or "").strip())
    if not stripped:
        return ""
    if not wrapper_has_conditional_blocks(stripped):
        return stripped
    return process_wrapper_conditionals(
        stripped,
        config,
        templates_content=templates_content,
        styling_content=styling_content,
        preview=True,
    )


def _format_resolved_wrapper_message(
    resolved: str,
    config: dict[str, Any] | None,
    *,
    context: str,
    request: str,
    templates: str,
    styling: str,
    card_templates_format_addon: Callable[..., str],
) -> str:
    templates_out = templates if wrapper_includes_section(resolved, "templates") else ""
    styling_out = styling if wrapper_includes_section(resolved, "styling") else ""

    if wrapper_has_conditional_blocks(resolved):
        body = process_wrapper_conditionals(
            resolved,
            config,
            templates_content=templates_out,
            styling_content=styling_out,
            preview=False,
            wrapper_text=resolved,
        )
    else:
        body = resolved

    format_addon = _card_templates_format_guide_for_message(
        resolved,
        config,
        templates_out=templates_out,
        styling_out=styling_out,
        card_templates_format_addon=card_templates_format_addon,
    )
    if format_addon:
        marker = wrapper_content_tag("templates")
        if marker in body:
            body = _inject_before_marker(body, marker, format_addon)
        elif wrapper_content_tag("styling") in body:
            body = _inject_before_marker(body, wrapper_content_tag("styling"), format_addon)

    return apply_wrapper_placeholders(
        body,
        context=context,
        request=request,
        templates=templates_out,
        styling=styling_out,
    )


def format_chat_context_message(
    config: dict[str, Any] | None,
    *,
    context: str,
    request: str,
    templates: str = "",
    styling: str = "",
    template: str | None = None,
    effective_wrapper: Callable[[dict[str, Any] | None], str],
    default_wrapper: Callable[[dict[str, Any] | None], str],
    is_builtin_wrapper: Callable[[str | None], bool],
    assemble_builtin_message: Callable[..., str],
    card_templates_format_addon: Callable[..., str],
) -> str:
    session_template = (template or "").strip() or None
    resolved = session_template or effective_wrapper(config)
    templates = templates or ""
    styling = styling or ""

    if is_builtin_wrapper(resolved):
        return assemble_builtin_message(
            config,
            context=context,
            request=request,
            templates=templates,
            styling=styling,
        )

    if chat_context_wrapper_should_fallback(resolved):
        if session_template is not None:
            resolved = effective_wrapper(config)
        if is_builtin_wrapper(resolved) or chat_context_wrapper_should_fallback(resolved):
            return assemble_builtin_message(
                config,
                context=context,
                request=request,
                templates=templates,
                styling=styling,
            )

    return _format_resolved_wrapper_message(
        resolved,
        config,
        context=context,
        request=request,
        templates=templates,
        styling=styling,
        card_templates_format_addon=card_templates_format_addon,
    )
