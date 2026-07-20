from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ..i18n import tr


@dataclass
class CardTemplateData:
    name: str
    front: str
    back: str
    notetype_name: str | None = None


@dataclass
class ImportedNotetypeData:
    notetype_id: int
    name: str
    field_names: list[str] = field(default_factory=list)
    templates: list[CardTemplateData] = field(default_factory=list)
    css: str = ""


def _field_names_from_model(model: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for fld in model.get("flds") or []:
        name = str(fld.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def _templates_from_model(model: dict[str, Any]) -> list[CardTemplateData]:
    notetype_name = str(model.get("name") or "").strip()
    templates: list[CardTemplateData] = []
    for index, template in enumerate(model.get("tmpls") or []):
        templates.append(
            CardTemplateData(
                name=str(template.get("name") or "").strip() or f"Card {index + 1}",
                front=str(template.get("qfmt") or ""),
                back=str(template.get("afmt") or ""),
                notetype_name=notetype_name or None,
            )
        )
    return templates


def imported_notetype_from_model(
    model: dict[str, Any],
    *,
    include_templates: bool = True,
    include_css: bool = True,
) -> ImportedNotetypeData:
    notetype_id = int(model.get("id") or 0)
    name = str(model.get("name") or "").strip() or f"Note type {notetype_id}"
    return ImportedNotetypeData(
        notetype_id=notetype_id,
        name=name,
        field_names=_field_names_from_model(model),
        templates=_templates_from_model(model) if include_templates else [],
        css=str(model.get("css") or "") if include_css else "",
    )


def imported_notetype_from_id(
    notetype_id: int,
    *,
    include_templates: bool = True,
    include_css: bool = True,
) -> ImportedNotetypeData | None:
    from aqt import mw

    model = mw.col.models.get(notetype_id)
    if not model:
        return None
    return imported_notetype_from_model(
        model,
        include_templates=include_templates,
        include_css=include_css,
    )


def extract_notetype_context(note) -> tuple[list[CardTemplateData], str]:
    from aqt import mw

    model = mw.col.models.get(note.mid)
    if not model:
        return [], ""
    data = imported_notetype_from_model(model)
    return data.templates, data.css


def merge_imported_notetypes(
    existing: dict[int, ImportedNotetypeData],
    incoming: Iterable[ImportedNotetypeData],
) -> dict[int, ImportedNotetypeData]:
    merged = dict(existing)
    for item in incoming:
        current = merged.get(item.notetype_id)
        if current is None:
            merged[item.notetype_id] = item
            continue
        merged[item.notetype_id] = ImportedNotetypeData(
            notetype_id=item.notetype_id,
            name=item.name or current.name,
            field_names=item.field_names or current.field_names,
            templates=item.templates if item.templates else current.templates,
            css=item.css if item.css.strip() else current.css,
        )
    return merged


def format_notetype_schema_block(
    data: ImportedNotetypeData,
    config: dict[str, Any] | None = None,
) -> str:
    fields_text = ", ".join(data.field_names)
    if not fields_text:
        fields_text = tr("chat.import_notetype.no_fields", config=config)
    return tr(
        "chat.import_notetype.schema_block",
        config=config,
        name=data.name,
        fields=fields_text,
    )


def format_notetype_schemas_block(
    notetypes: Iterable[ImportedNotetypeData],
    config: dict[str, Any] | None = None,
    *,
    exclude_notetype_ids: set[int] | None = None,
) -> str:
    excluded = exclude_notetype_ids or set()
    blocks: list[str] = []
    for data in sorted(notetypes, key=lambda item: item.name.lower()):
        if data.notetype_id in excluded:
            continue
        block = format_notetype_schema_block(data, config)
        if block.strip():
            blocks.append(block)
    return "\n\n".join(blocks)


def format_card_templates_block(
    templates: list[CardTemplateData],
    config: dict[str, Any] | None = None,
) -> str:
    if not templates:
        return ""
    notetype_names = {template.notetype_name for template in templates if template.notetype_name}
    if len(notetype_names) <= 1:
        return _format_card_templates_flat(templates, config)
    blocks: list[str] = []
    grouped: dict[str, list[CardTemplateData]] = {}
    for template in templates:
        key = template.notetype_name or ""
        grouped.setdefault(key, []).append(template)
    for notetype_name in sorted(grouped, key=lambda value: value.lower()):
        group = grouped[notetype_name]
        inner = _format_card_templates_flat(group, config)
        if not inner.strip():
            continue
        if notetype_name:
            header = tr(
                "chat.import_notetype.templates_header",
                config=config,
                name=notetype_name,
            )
            blocks.append(f"{header}\n{inner}")
        else:
            blocks.append(inner)
    return "\n\n".join(blocks)


def _format_card_templates_flat(
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


def format_imported_notetype_templates(
    notetypes: dict[int, ImportedNotetypeData],
    config: dict[str, Any] | None = None,
    *,
    include_notetype_ids: set[int] | None = None,
) -> str:
    templates: list[CardTemplateData] = []
    for data in sorted(notetypes.values(), key=lambda item: item.name.lower()):
        if include_notetype_ids is not None and data.notetype_id not in include_notetype_ids:
            continue
        templates.extend(data.templates)
    return format_card_templates_block(templates, config)


def format_imported_notetype_styling(
    notetypes: dict[int, ImportedNotetypeData],
    config: dict[str, Any] | None = None,
    *,
    include_notetype_ids: set[int] | None = None,
) -> str:
    blocks: list[str] = []
    for data in sorted(notetypes.values(), key=lambda item: item.name.lower()):
        if include_notetype_ids is not None and data.notetype_id not in include_notetype_ids:
            continue
        css = data.css.strip()
        if not css:
            continue
        if data.name:
            # Avoid str.format on CSS — note-type CSS is full of { }.
            header = tr(
                "chat.import_notetype.styling_header",
                config=config,
                name=data.name,
            )
            blocks.append(f"{header}\n{css}")
        else:
            blocks.append(css)
    return "\n\n".join(blocks)


def imported_notetype_has_templates(notetypes: dict[int, ImportedNotetypeData]) -> bool:
    return any(data.templates for data in notetypes.values())


def imported_notetype_has_styling(notetypes: dict[int, ImportedNotetypeData]) -> bool:
    return any(data.css.strip() for data in notetypes.values())


def editable_templates_notetypes(
    notetypes: dict[int, ImportedNotetypeData],
) -> list[ImportedNotetypeData]:
    """Imported note types that have templates and/or CSS to edit (name-sorted)."""
    pool = [
        data
        for data in notetypes.values()
        if data.templates or data.css.strip()
    ]
    pool.sort(key=lambda item: item.name.lower())
    return pool


def primary_templates_notetype_id(
    notetypes: dict[int, ImportedNotetypeData],
    *,
    preferred_id: int | None = None,
) -> int | None:
    if not notetypes:
        return None
    if preferred_id is not None and preferred_id in notetypes:
        return preferred_id
    with_content = editable_templates_notetypes(notetypes)
    pool = with_content or list(notetypes.values())
    pool.sort(key=lambda item: item.name.lower())
    return pool[0].notetype_id


def templates_and_styling_for_editor(
    notetypes: dict[int, ImportedNotetypeData],
    *,
    preferred_id: int | None = None,
    notetype_id: int | None = None,
) -> tuple[list[CardTemplateData], str]:
    """Return templates/CSS for one imported note type (explicit id or primary)."""
    if not notetypes:
        return [], ""
    if notetype_id is not None and notetype_id in notetypes:
        data = notetypes[notetype_id]
        return list(data.templates), data.css
    primary_id = primary_templates_notetype_id(
        notetypes,
        preferred_id=preferred_id,
    )
    if primary_id is None:
        return [], ""
    # One note type at a time: multi-type CSS cannot round-trip through the
    # single styling editor without lossy merges.
    data = notetypes[primary_id]
    return list(data.templates), data.css
