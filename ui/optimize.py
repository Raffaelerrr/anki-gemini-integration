from __future__ import annotations

from typing import Any

from aqt import mw
from aqt.qt import QCheckBox, QDialog, QMessageBox
from aqt.utils import showInfo, showWarning, tooltip

from ..config import api_key_configured, is_warning_dismissed, load_config, save_config, uses_default_system_instruction
from ..gemini_client import (
    GeminiAuthError,
    GeminiError,
    GeminiRateLimitError,
    build_optimize_user_text,
    call_gemini,
    merge_system_instructions,
    resolve_model,
    strip_markdown_fences,
)
from ..i18n import tr
from ..prompt_cache import (
    build_live_system_instruction,
    build_prompt_cache_bundle,
    flatten_bundle_for_live_send,
)
from ..prompt_inspection import build_optimize_prompt_inspection
from .pre_send_prompt_dialog import PreSendPromptContext, PreSendPromptOverrides, confirm_pre_send_prompt
from .prompt_cache_confirm import confirm_prompt_cache_recreate_if_needed
from .preview_dialog import PreviewDialog

_last_undo: dict[int, tuple[int, str]] = {}


def _editor_key(editor) -> int:
    return id(editor)


def store_undo(editor, field_index: int, original_text: str) -> None:
    _last_undo[_editor_key(editor)] = (field_index, original_text)


def undo_last_optimization(editor) -> None:
    config = load_config()
    key = _editor_key(editor)
    backup = _last_undo.get(key)
    if not backup:
        showInfo(tr("optimize.no_undo", config=config))
        return

    field_index, original_text = backup
    editor.note.fields[field_index] = original_text
    editor.loadNoteKeepingFocus()
    del _last_undo[key]
    tooltip(tr("optimize.undo_done", config=config))


def _apply_optimized_text(editor, field_index: int, original: str, optimized: str) -> None:
    config = load_config()
    store_undo(editor, field_index, original)
    editor.note.fields[field_index] = optimized
    editor.loadNoteKeepingFocus()
    tooltip(tr("optimize.applied", config=config))


def _show_optimize_info(
    editor,
    config: dict[str, Any],
    *,
    title_key: str,
    message_key: str,
    detail_key: str,
    dismiss_config_key: str,
    message_kwargs: dict[str, Any] | None = None,
) -> None:
    box = QMessageBox(editor.parentWindow)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(tr(title_key, config=config))
    box.setText(tr(message_key, config=config, **(message_kwargs or {})))
    box.setInformativeText(tr(detail_key, config=config))
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.setDefaultButton(QMessageBox.StandardButton.Ok)

    dismiss = QCheckBox(tr("optimize.warning.dismiss", config=config), box)
    box.setCheckBox(dismiss)
    box.exec()

    if dismiss.isChecked():
        updated = load_config()
        updated[dismiss_config_key] = True
        save_config(updated)


def _notify_optimize_prompt_cache_created(editor, config: dict[str, Any], active) -> None:
    if is_warning_dismissed(config, "suppress_prompt_cache_created_optimize_notice"):
        return
    from ..prompt_cache import prompt_cache_created_stats

    chars, minutes = prompt_cache_created_stats(active)
    _show_optimize_info(
        editor,
        config,
        title_key="optimize.prompt_cache.created.title",
        message_key="optimize.prompt_cache.created.message",
        detail_key="optimize.prompt_cache.created.detail",
        dismiss_config_key="suppress_prompt_cache_created_optimize_notice",
        message_kwargs={"chars": chars, "minutes": minutes},
    )


def _schedule_optimize_prompt_cache_created(editor, config: dict[str, Any], active) -> None:
    mw.taskman.run_on_main(
        lambda: _notify_optimize_prompt_cache_created(editor, config, active)
    )


def _confirm_optimize_warning(
    editor,
    config: dict[str, Any],
    *,
    title_key: str,
    message_key: str,
    detail_key: str,
    dismiss_config_key: str,
) -> bool:
    box = QMessageBox(editor.parentWindow)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(tr(title_key, config=config))
    box.setText(tr(message_key, config=config))
    box.setInformativeText(tr(detail_key, config=config))
    box.setStandardButtons(
        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
    )
    box.setDefaultButton(QMessageBox.StandardButton.Cancel)

    dismiss = QCheckBox(tr("optimize.warning.dismiss", config=config), box)
    box.setCheckBox(dismiss)

    if box.exec() != QMessageBox.StandardButton.Ok:
        return False

    if dismiss.isChecked():
        updated = load_config()
        updated[dismiss_config_key] = True
        save_config(updated)

    return True


def _passes_optimize_warnings(editor, config: dict[str, Any]) -> bool:
    if (
        uses_default_system_instruction(config)
        and not is_warning_dismissed(config, "suppress_default_system_instruction_warning")
        and not _confirm_optimize_warning(
            editor,
            config,
            title_key="optimize.default_instruction.title",
            message_key="optimize.default_instruction.message",
            detail_key="optimize.default_instruction.detail",
            dismiss_config_key="suppress_default_system_instruction_warning",
        )
    ):
        return False

    return True


def build_optimize_pre_send_context(
    config: dict[str, Any],
    field_content: str,
) -> PreSendPromptContext:
    bundle = build_prompt_cache_bundle(config, purpose="optimize")
    if bundle is not None:
        system_instruction = build_live_system_instruction(
            config,
            purpose="optimize",
            include_meta_rule=False,
            bundle=bundle,
        )
    else:
        system_instruction = merge_system_instructions(
            config,
            include_meta_rule=False,
            purpose="optimize",
        )
    inspection = build_optimize_prompt_inspection(config, field_content=field_content)
    return PreSendPromptContext(
        inspection=inspection,
        outgoing_payload=field_content,
        system_instruction=system_instruction,
        bundle=bundle,
        model=resolve_model(config, "optimize"),
        cache_session=None,
        purpose="optimize",
    )


def _handle_optimize_result(future, editor, field_index: int, original: str, config: dict[str, Any]) -> None:
    from .window_lifecycle import is_shutting_down

    if is_shutting_down():
        return
    try:
        result = future.result()
        optimized = strip_markdown_fences(result)

        if config.get("confirm_before_apply", True):
            dialog = PreviewDialog(editor.parentWindow, original, optimized, config=config)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                tooltip(tr("optimize.cancelled", config=config))
                return

        _apply_optimized_text(editor, field_index, original, optimized)
    except (GeminiRateLimitError, GeminiAuthError) as exc:
        showWarning(str(exc))
    except GeminiError as exc:
        showWarning(tr("optimize.error", config=config, error=exc))
    except Exception as exc:
        showWarning(tr("optimize.error", config=config, error=exc))


def optimize_field_with_gemini(editor) -> None:
    config = load_config()
    field_index = editor.currentField
    if field_index is None:
        showInfo(tr("optimize.click_field", config=config))
        return

    original = editor.note.fields[field_index]
    if not original.strip():
        showInfo(tr("optimize.field_empty", config=config))
        return

    if not api_key_configured(config):
        showInfo(tr("optimize.api_key_missing", config=config))
        return

    if not _passes_optimize_warnings(editor, config):
        return

    pre_send_context = build_optimize_pre_send_context(config, original)
    pre_send_overrides: PreSendPromptOverrides | None = None
    if bool(config.get("optimize_modify_prompt_before_send", False)):
        pre_send_overrides = confirm_pre_send_prompt(
            editor.parentWindow,
            context=pre_send_context,
        )
        if pre_send_overrides is None:
            return

    bundle = (
        pre_send_overrides.bundle
        if pre_send_overrides is not None and pre_send_overrides.bundle is not None
        else pre_send_context.bundle
    )
    user_text = (
        pre_send_overrides.outgoing_payload
        if pre_send_overrides is not None
        else original
    )
    system_instruction = (
        pre_send_overrides.system_instruction
        if pre_send_overrides is not None
        else pre_send_context.system_instruction
    )

    cache_choice = confirm_prompt_cache_recreate_if_needed(
        editor.parentWindow,
        config,
        bundle,
        purpose="optimize",
    )
    if cache_choice == "abort":
        return
    allow_cache_create = cache_choice != "skip_cache"
    allow_cache_use = cache_choice != "skip_cache"
    if bundle is not None and not allow_cache_use:
        system_instruction, user_text = flatten_bundle_for_live_send(
            config,
            bundle,
            purpose="optimize",
            include_meta_rule=False,
            system_instruction_override=(
                system_instruction if pre_send_overrides is not None else None
            ),
            outgoing_payload_override=user_text if pre_send_overrides is not None else None,
            user_text=user_text,
        )

    tooltip(tr("optimize.in_progress", config=config))

    temperature = float(config.get("temperature_optimize", 0.1))
    api_user_text = build_optimize_user_text(config, user_text)

    call_kwargs: dict[str, Any] = {
        "config": config,
        "user_text": api_user_text,
        "temperature": temperature,
        "include_meta_rule": False,
        "purpose": "optimize",
        "allow_prompt_cache_create": allow_cache_create,
        "allow_prompt_cache_use": allow_cache_use,
        "on_prompt_cache_created": lambda active: _schedule_optimize_prompt_cache_created(
            editor,
            config,
            active,
        ),
    }
    if pre_send_overrides is not None or (not allow_cache_use and bundle is not None):
        call_kwargs["override_outgoing_payload"] = api_user_text
        call_kwargs["override_system_instruction"] = system_instruction
        if allow_cache_use and bundle is not None:
            call_kwargs["override_bundle"] = bundle

    mw.taskman.run_in_background(
        lambda: call_gemini(**call_kwargs),
        lambda future: _handle_optimize_result(future, editor, field_index, original, config),
    )
