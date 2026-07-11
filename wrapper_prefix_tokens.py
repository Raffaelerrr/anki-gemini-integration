from __future__ import annotations

from .chat_context_wrapper import PLACEHOLDER_SECTIONS, wrapper_content_tag

Segment = tuple[str, str]


def wrapper_token_display_label(section_id: str) -> str:
    return section_id


def parse_wrapper_prefix_segments(text: str, section_id: str) -> list[Segment]:
    tag = wrapper_content_tag(section_id)
    if not tag:
        return [("text", text or "")]
    segments: list[Segment] = []
    remaining = text or ""
    while remaining:
        index = remaining.find(tag)
        if index < 0:
            segments.append(("text", remaining))
            break
        if index > 0:
            segments.append(("text", remaining[:index]))
        segments.append(("token", section_id))
        remaining = remaining[index + len(tag) :]
    return segments


def ensure_newline_before_wrapper_tag(text: str, section_id: str) -> str:
    tag = wrapper_content_tag(section_id)
    if not tag or tag not in text:
        return text
    index = text.find(tag)
    if index <= 0:
        return text
    before = text[:index]
    if before.endswith("\n"):
        return text
    return f"{before}\n{text[index:]}"


def _append_text_segment(segments: list[Segment], text: str) -> None:
    if not text:
        return
    if segments and segments[-1][0] == "text":
        segments[-1] = ("text", segments[-1][1] + text)
    else:
        segments.append(("text", text))


def normalize_wrapper_prefix_segments(
    segments: list[Segment],
    section_id: str,
    *,
    allow_token: bool = True,
) -> list[Segment]:
    """Keep at most one placeholder token for *section_id*."""
    tag = wrapper_content_tag(section_id)
    if not tag:
        return segments
    normalized: list[Segment] = []
    token_seen = not allow_token
    for kind, content in segments:
        if kind == "token":
            if content != section_id or token_seen:
                continue
            normalized.append(("token", section_id))
            token_seen = True
            continue
        remaining = content
        while remaining:
            index = remaining.find(tag)
            if index < 0:
                _append_text_segment(normalized, remaining)
                break
            if index > 0:
                _append_text_segment(normalized, remaining[:index])
            if not token_seen:
                normalized.append(("token", section_id))
                token_seen = True
            remaining = remaining[index + len(tag) :]
    return normalized


def serialize_wrapper_prefix_segments(segments: list[Segment]) -> str:
    parts: list[str] = []
    for kind, content in segments:
        if kind == "text":
            parts.append(content)
        elif kind == "token":
            parts.append(wrapper_content_tag(content))
    return "".join(parts)


def wrapper_prefix_requires_token(section_id: str) -> bool:
    return section_id in PLACEHOLDER_SECTIONS


def wrapper_prefix_user_text(segments: list[Segment]) -> str:
    return "".join(content for kind, content in segments if kind == "text")


def wrapper_prefix_has_token(segments: list[Segment], section_id: str) -> bool:
    return any(kind == "token" and content == section_id for kind, content in segments)
