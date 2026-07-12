from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .gemini_client import (
    build_optimize_user_text,
    resolve_model,
    resolve_thinking_budget,
    trim_history,
)
from .i18n import (
    effective_chat_system_addon,
    effective_dynamic_rules_prefix,
    effective_optimize_user_prompt,
    effective_system_instruction,
    tr,
)

CHAT_SESSION_CONFIG_KEYS: tuple[str, ...] = (
    "system_instruction",
    "system_instruction_shared",
    "system_instruction_optimize",
    "system_instruction_chat",
    "dynamic_instructions",
    "model_chat",
    "thinking_budget_chat",
    "temperature_chat",
    "chat_streaming",
    "max_history_turns",
    "prompt_chat_addon",
    "prompt_dynamic_rules_prefix",
    "prompt_chat_context",
    "prompt_chat_context_order",
    "prompt_chat_context_sections",
    "prompt_card_templates_format",
    "prompt_cache_enabled_chat",
    "prompt_cache_enabled_optimize",
    "prompt_cache_ttl_seconds_chat",
    "prompt_cache_ttl_seconds_optimize",
    "prompt_cache_min_chars_chat",
    "prompt_cache_min_chars_optimize",
    "prompt_cache_custom_text_chat",
    "prompt_cache_custom_text_optimize",
    "prompt_cache_segments_chat",
    "prompt_cache_segments_optimize",
)

CHAT_LIVE_CONFIG_KEYS: tuple[str, ...] = (
    "language",
    "chat_payload_warning_chars",
    "timeout_seconds",
    "max_retries",
    "brain_import_templates",
    "brain_import_css",
    "chat_modify_prompt_before_send",
)


@dataclass
class PromptSegment:
    label_key: str
    text: str
    role: str


@dataclass
class PromptInspection:
    segments: list[PromptSegment] = field(default_factory=list)
    purpose: str = "chat"
    model: str = ""
    temperature: float = 0.0
    thinking_budget: int = 0
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    def formula_text(self, config: dict[str, Any] | None = None) -> str:
        if not self.segments:
            return ""
        names = [tr(segment.label_key, config=config) for segment in self.segments]
        return " + ".join(names)

    def full_text(self, config: dict[str, Any] | None = None) -> str:
        blocks: list[str] = []
        for segment in self.segments:
            title = tr(segment.label_key, config=config)
            blocks.append(f"=== {title} ===\n{segment.text}")
        return "\n\n".join(blocks)

    def plain_full_text(self, config: dict[str, Any] | None = None) -> str:
        from .prompt_compose import join_prompt_blocks

        parts: list[str] = []
        system = merge_inspection_system_text(self.segments)
        if system.strip():
            parts.append(system)
        for segment in self.segments:
            if segment.role == "history" and (segment.text or "").strip():
                parts.append(segment.text)
            elif segment.label_key == "prompt.inspect.next_user_message" and (segment.text or "").strip():
                parts.append(segment.text)
        return join_prompt_blocks(*parts)

    def metadata_lines(self, config: dict[str, Any] | None = None) -> list[str]:
        config = config or {}
        lines = [
            tr(
                "prompt.inspect.meta.model",
                config=config,
                model=self.model,
            ),
            tr(
                "prompt.inspect.meta.temperature",
                config=config,
                temperature=self.temperature,
            ),
            tr(
                "prompt.inspect.meta.thinking_budget",
                config=config,
                budget=self.thinking_budget,
            ),
        ]
        if self.purpose == "chat":
            lines.append(
                tr(
                    "prompt.inspect.meta.streaming",
                    config=config,
                    enabled="yes" if self.extra_metadata.get("streaming") else "no",
                )
            )
            lines.append(
                tr(
                    "prompt.inspect.meta.history_turns",
                    config=config,
                    turns=self.extra_metadata.get("history_turns", 0),
                    max_turns=self.extra_metadata.get("max_history_turns", 0),
                )
            )
        return lines

    def metadata_text(self, config: dict[str, Any] | None = None) -> str:
        return ", ".join(self.metadata_lines(config))


def merge_inspection_system_text(segments: list[PromptSegment]) -> str:
    from .prompt_compose import join_prompt_blocks, join_prompt_header_body

    base = ""
    prefix = ""
    dynamic = ""
    addon = ""
    for segment in segments:
        if segment.label_key == "prompt.inspect.system_instruction":
            base = segment.text
        elif segment.label_key == "prompt.inspect.dynamic_rules_prefix":
            prefix = segment.text
        elif segment.label_key == "prompt.inspect.dynamic_instructions":
            dynamic = segment.text
        elif segment.label_key == "prompt.inspect.chat_system_addon":
            addon = segment.text
    blocks: list[str] = [base]
    if dynamic.strip():
        blocks.append(join_prompt_header_body(prefix, dynamic))
    if addon.strip():
        blocks.append(addon)
    return join_prompt_blocks(*blocks)


def system_instruction_parts_from_segments(
    segments: list[PromptSegment],
) -> dict[str, str]:
    parts = {
        "prompt.inspect.system_instruction": "",
        "prompt.inspect.dynamic_rules_prefix": "",
        "prompt.inspect.dynamic_instructions": "",
        "prompt.inspect.chat_system_addon": "",
    }
    for segment in segments:
        if segment.label_key in parts:
            parts[segment.label_key] = segment.text
    return parts


def chat_session_config_fingerprint(config: dict[str, Any] | None) -> str:
    payload = {key: (config or {}).get(key) for key in CHAT_SESSION_CONFIG_KEYS}
    return json.dumps(payload, sort_keys=True, default=str)


def chat_session_config_changed(
    session_fingerprint: str,
    config: dict[str, Any] | None = None,
) -> bool:
    return session_fingerprint != chat_session_config_fingerprint(config)


def _append_system_instruction_segments(
    segments: list[PromptSegment],
    config: dict[str, Any],
    *,
    purpose: str,
) -> None:
    instruction = effective_system_instruction(config, purpose=purpose)
    segments.append(
        PromptSegment(
            label_key="prompt.inspect.system_instruction",
            text=instruction,
            role="system",
        )
    )
    dynamic = (config.get("dynamic_instructions") or "").strip()
    if not dynamic:
        return
    prefix = effective_dynamic_rules_prefix(config)
    if prefix:
        segments.append(
            PromptSegment(
                label_key="prompt.inspect.dynamic_rules_prefix",
                text=prefix,
                role="system",
            )
        )
    segments.append(
        PromptSegment(
            label_key="prompt.inspect.dynamic_instructions",
            text=dynamic,
            role="system",
        )
    )


def build_optimize_prompt_inspection(
    config: dict[str, Any],
    *,
    field_content: str | None = None,
) -> PromptInspection:
    segments: list[PromptSegment] = []
    _append_system_instruction_segments(segments, config, purpose="optimize")

    prefix = effective_optimize_user_prompt(config)
    segments.append(
        PromptSegment(
            label_key="prompt.inspect.optimize_user_prefix",
            text=prefix,
            role="user",
        )
    )
    field_text = (field_content or "").strip() or tr("prompt.inspect.field_placeholder", config=config)
    segments.append(
        PromptSegment(
            label_key="prompt.inspect.field_content",
            text=field_text,
            role="user",
        )
    )

    return PromptInspection(
        segments=segments,
        purpose="optimize",
        model=resolve_model(config, "optimize"),
        temperature=float(config.get("temperature_optimize", 0.1)),
        thinking_budget=resolve_thinking_budget(config, "optimize"),
    )


def build_chat_prompt_inspection(
    config: dict[str, Any],
    *,
    history: list[dict[str, Any]],
    next_user_text: str,
    outgoing_payload: str,
) -> PromptInspection:
    segments: list[PromptSegment] = []
    _append_system_instruction_segments(segments, config, purpose="chat")

    addon = effective_chat_system_addon(config)
    segments.append(
        PromptSegment(
            label_key="prompt.inspect.chat_system_addon",
            text=addon,
            role="system",
        )
    )

    max_turns = int(config.get("max_history_turns", 10))
    trimmed = trim_history(list(history), max_turns)
    if trimmed:
        history_lines: list[str] = []
        for index, turn in enumerate(trimmed, start=1):
            role = str(turn.get("role") or "user")
            parts = turn.get("parts") or []
            text = "\n".join(
                str(part.get("text") or "")
                for part in parts
                if str(part.get("text") or "").strip()
            )
            role_label = tr(
                "prompt.inspect.history_role",
                config=config,
                index=index,
                role=role,
            )
            history_lines.append(f"--- {role_label} ---\n{text}")
        segments.append(
            PromptSegment(
                label_key="prompt.inspect.chat_history",
                text="\n\n".join(history_lines),
                role="history",
            )
        )

    next_text = outgoing_payload.strip() or tr("prompt.inspect.empty_next_message", config=config)

    segments.append(
        PromptSegment(
            label_key="prompt.inspect.next_user_message",
            text=next_text,
            role="user",
        )
    )

    return PromptInspection(
        segments=segments,
        purpose="chat",
        model=resolve_model(config, "chat"),
        temperature=float(config.get("temperature_chat", 0.2)),
        thinking_budget=resolve_thinking_budget(config, "chat"),
        extra_metadata={
            "streaming": bool(config.get("chat_streaming", True)),
            "history_turns": len(trimmed) // 2 if trimmed else 0,
            "max_history_turns": max_turns,
        },
    )


def optimize_user_text_for_inspection(config: dict[str, Any], field_content: str) -> str:
    return build_optimize_user_text(config, field_content)
