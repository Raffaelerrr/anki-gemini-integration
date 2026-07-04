from __future__ import annotations

import html
import re

from .html_utils import closing_tags_suffix

_TRAILING_EMPTY_HTML = re.compile(
    r"(?:"
    r"\s|"
    r"<br\s*/?>|"
    r"<p>\s*(?:<br\s*/?>)?\s*</p>|"
    r"<div>\s*(?:<br\s*/?>)?\s*</div>"
    r")+$",
    re.IGNORECASE,
)

_LEADING_EMPTY_HTML = re.compile(
    r"^(?:"
    r"\s|"
    r"<br\s*/?>|"
    r"<p>\s*(?:<br\s*/?>|&nbsp;|\u00a0|\s)*</p>|"
    r"<div>\s*(?:<br\s*/?>|&nbsp;|\u00a0|\s)*</div>"
    r")+",
    re.IGNORECASE,
)

_HTML_TAG = re.compile(r"<\/?[a-zA-Z][^>]*>", re.IGNORECASE)


def strip_field_html_edges(value: str) -> str:
    cleaned = value.strip()
    while True:
        new = _LEADING_EMPTY_HTML.sub("", cleaned, count=1)
        if new == cleaned:
            break
        cleaned = new.strip()
    cleaned = re.sub(r"^(<br\s*/?>|<div>\s*<br\s*/?>\s*</div>|<p>\s*</p>)+", "", cleaned)
    cleaned = _TRAILING_EMPTY_HTML.sub("", cleaned)
    return cleaned.strip()


def field_inner_html(value: str) -> str:
    cleaned = strip_field_html_edges(value)
    if _HTML_TAG.search(cleaned):
        return cleaned + closing_tags_suffix(cleaned)
    normalized = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    return html.escape(normalized).replace("\n", "<br>")
