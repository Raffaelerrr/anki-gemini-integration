from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IncludeNextMessageMask:
    """Session-only selection of what to attach on the next chat send."""

    note_fields: dict[int, bool] = field(default_factory=dict)
    schemas: dict[int, bool] = field(default_factory=dict)
    templates: dict[int, bool] = field(default_factory=dict)
    css: dict[int, bool] = field(default_factory=dict)

    def any_selected(self) -> bool:
        return (
            any(self.note_fields.values())
            or any(self.schemas.values())
            or any(self.templates.values())
            or any(self.css.values())
        )

    def clear_selections(self) -> None:
        self.note_fields = {key: False for key in self.note_fields}
        self.schemas = {key: False for key in self.schemas}
        self.templates = {key: False for key in self.templates}
        self.css = {key: False for key in self.css}

    def ensure_note(self, note_id: int) -> None:
        self.note_fields.setdefault(note_id, False)

    def ensure_notetype(self, notetype_id: int) -> None:
        self.schemas.setdefault(notetype_id, False)
        self.templates.setdefault(notetype_id, False)
        self.css.setdefault(notetype_id, False)

    def prune_to_note_ids(self, note_ids: set[int]) -> None:
        self.note_fields = {
            key: value for key, value in self.note_fields.items() if key in note_ids
        }

    def prune_to_notetype_ids(self, notetype_ids: set[int]) -> None:
        self.schemas = {key: value for key, value in self.schemas.items() if key in notetype_ids}
        self.templates = {
            key: value for key, value in self.templates.items() if key in notetype_ids
        }
        self.css = {key: value for key, value in self.css.items() if key in notetype_ids}

    def selected_note_ids(self) -> list[int]:
        return [key for key, enabled in self.note_fields.items() if enabled]

    def selected_schema_ids(self) -> list[int]:
        return [key for key, enabled in self.schemas.items() if enabled]

    def selected_template_ids(self) -> list[int]:
        return [key for key, enabled in self.templates.items() if enabled]

    def selected_css_ids(self) -> list[int]:
        return [key for key, enabled in self.css.items() if enabled]
