from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..i18n import tr


@dataclass
class CardTemplateData:
    name: str
    front: str
    back: str


def extract_notetype_context(note) -> tuple[list[CardTemplateData], str]:
    from aqt import mw

    model = mw.col.models.get(note.mid)
    templates = [
        CardTemplateData(
            name=str(template.get("name") or "").strip() or f"Card {index + 1}",
            front=str(template.get("qfmt") or ""),
            back=str(template.get("afmt") or ""),
        )
        for index, template in enumerate(model.get("tmpls") or [])
    ]
    styling = str(model.get("css") or "")
    return templates, styling


def format_card_templates_block(
    templates: list[CardTemplateData],
    config: dict[str, Any] | None = None,
) -> str:
    blocks: list[str] = []
    for index, template in enumerate(templates, start=1):
        blocks.append(
            f"{tr('chat.context.card_type_header', config=config, index=index, name=template.name)}\n"
            f"{tr('chat.context.front_template', config=config)}\n"
            f"{template.front}\n"
            f"{tr('chat.context.back_template', config=config)}\n"
            f"{template.back}"
        )
    return "\n\n".join(blocks)
