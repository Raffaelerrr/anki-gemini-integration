from __future__ import annotations


def strip_prompt_part(text: str) -> str:
    return (text or "").strip()


def join_prompt_blocks(*parts: str) -> str:
    """Join major prompt sections with a single blank line between each."""
    cleaned = [strip_prompt_part(part) for part in parts]
    cleaned = [part for part in cleaned if part]
    return "\n\n".join(cleaned)


def join_prompt_header_body(header: str, body: str) -> str:
    """Join a short header line to the body that follows it."""
    head = strip_prompt_part(header)
    content = strip_prompt_part(body)
    if not head:
        return content
    if not content:
        return head
    return f"{head}\n{content}"
