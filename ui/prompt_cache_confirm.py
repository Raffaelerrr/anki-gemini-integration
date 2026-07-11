from __future__ import annotations

from typing import Any, Literal

from aqt.qt import QCheckBox, QMessageBox, QWidget

from ..config import is_warning_dismissed, load_config, save_config
from ..constants import GEMINI_AI_STUDIO_BILLING_URL
from ..gemini_client import Purpose
from ..i18n import tr
from ..prompt_cache import (
    PromptCacheBundle,
    needs_prompt_cache_recreate_confirm,
    prompt_cache_ttl_seconds,
)
from ..prompt_cache_policy import (
    cache_enabled_segments_are_global_only,
    chat_cache_includes_session_content,
    has_tracked_active_cache,
)

PromptCacheRecreateChoice = Literal["proceed", "skip_cache", "abort"]
NewConversationCacheChoice = Literal["keep", "clear", "abort"]
ImportNoteCacheChoice = Literal["proceed", "abort"]


def _save_dismiss_flag(config: dict[str, Any], key: str) -> None:
    updated = load_config()
    updated[key] = True
    save_config(updated)
    config[key] = True


def _save_default_action(config: dict[str, Any], key: str, value: str) -> None:
    updated = load_config()
    updated[key] = value
    save_config(updated)
    config[key] = value


def _ask_default_action(
    parent: QWidget,
    config: dict[str, Any],
    *,
    title_key: str,
    message_key: str,
    detail_key: str,
    options: tuple[tuple[str, str], tuple[str, str]],
) -> str | None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(tr(title_key, config=config))
    box.setText(tr(message_key, config=config))
    box.setInformativeText(tr(detail_key, config=config))
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No
        | QMessageBox.StandardButton.Cancel
    )
    yes_button = box.button(QMessageBox.StandardButton.Yes)
    no_button = box.button(QMessageBox.StandardButton.No)
    if yes_button is not None:
        yes_button.setText(tr(options[0][1], config=config))
    if no_button is not None:
        no_button.setText(tr(options[1][1], config=config))
    box.setDefaultButton(QMessageBox.StandardButton.Yes)
    result = box.exec()
    if result == QMessageBox.StandardButton.Yes:
        return options[0][0]
    if result == QMessageBox.StandardButton.No:
        return options[1][0]
    return None


def _recreate_default_choice(config: dict[str, Any]) -> PromptCacheRecreateChoice:
    default = str(config.get("prompt_cache_recreate_default") or "recreate")
    if default == "skip_cache":
        return "skip_cache"
    return "proceed"


def confirm_prompt_cache_recreate_if_needed(
    parent: QWidget,
    config: dict[str, Any],
    bundle: PromptCacheBundle | None,
    *,
    purpose: Purpose,
) -> PromptCacheRecreateChoice:
    if not needs_prompt_cache_recreate_confirm(config, bundle, purpose=purpose):
        return "proceed"

    if is_warning_dismissed(config, "suppress_prompt_cache_recreate_confirm"):
        return _recreate_default_choice(config)

    ttl_seconds = prompt_cache_ttl_seconds(config)
    ttl_minutes = max(1, ttl_seconds // 60)
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(tr("prompt_cache.recreate_confirm.title", config=config))
    box.setText(
        tr(
            "prompt_cache.recreate_confirm.message",
            config=config,
            chars=bundle.cached_char_count if bundle else 0,
            minutes=ttl_minutes,
        )
    )
    box.setInformativeText(
        tr(
            "prompt_cache.recreate_confirm.detail",
            config=config,
            billing_url=GEMINI_AI_STUDIO_BILLING_URL,
        )
    )
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No
        | QMessageBox.StandardButton.Cancel
    )
    box.setDefaultButton(QMessageBox.StandardButton.Yes)
    dismiss = QCheckBox(tr("optimize.warning.dismiss", config=config), box)
    box.setCheckBox(dismiss)

    result = box.exec()
    if result == QMessageBox.StandardButton.Cancel:
        return "abort"

    choice: PromptCacheRecreateChoice = (
        "skip_cache" if result == QMessageBox.StandardButton.No else "proceed"
    )

    if dismiss.isChecked():
        default_value = _ask_default_action(
            parent,
            config,
            title_key="prompt_cache.recreate_default.title",
            message_key="prompt_cache.recreate_default.message",
            detail_key="prompt_cache.recreate_default.detail",
            options=(
                ("recreate", "prompt_cache.recreate_default.recreate"),
                ("skip_cache", "prompt_cache.recreate_default.skip_cache"),
            ),
        )
        if default_value is not None:
            _save_default_action(config, "prompt_cache_recreate_default", default_value)
            _save_dismiss_flag(config, "suppress_prompt_cache_recreate_confirm")

    return choice


def _new_conversation_cache_default(config: dict[str, Any]) -> NewConversationCacheChoice:
    default = str(config.get("prompt_cache_new_conversation_cache_default") or "clear")
    if default == "keep" and cache_enabled_segments_are_global_only(config):
        return "keep"
    return "clear"


def confirm_new_conversation_cache_if_needed(
    parent: QWidget,
    config: dict[str, Any],
) -> NewConversationCacheChoice | None:
    """Returns None when no cache decision is needed (no active chat cache)."""
    if not has_tracked_active_cache("chat"):
        return None

    if is_warning_dismissed(config, "suppress_new_conversation_cache_warning"):
        return _new_conversation_cache_default(config)

    global_only = cache_enabled_segments_are_global_only(config)
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(tr("prompt_cache.new_conversation.title", config=config))
    if global_only:
        box.setText(tr("prompt_cache.new_conversation.message", config=config))
        box.setInformativeText(tr("prompt_cache.new_conversation.detail", config=config))
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel
        )
        box.button(QMessageBox.StandardButton.Yes).setText(
            tr("prompt_cache.new_conversation.keep", config=config)
        )
        box.button(QMessageBox.StandardButton.No).setText(
            tr("prompt_cache.new_conversation.clear", config=config)
        )
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
    else:
        box.setText(tr("prompt_cache.new_conversation.force_clear.message", config=config))
        box.setInformativeText(
            tr("prompt_cache.new_conversation.force_clear.detail", config=config)
        )
        box.setStandardButtons(
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Ok)

    dismiss = QCheckBox(tr("optimize.warning.dismiss", config=config), box)
    box.setCheckBox(dismiss)

    result = box.exec()
    if result == QMessageBox.StandardButton.Cancel:
        return "abort"

    if global_only:
        choice: NewConversationCacheChoice = (
            "keep" if result == QMessageBox.StandardButton.Yes else "clear"
        )
    else:
        if result != QMessageBox.StandardButton.Ok:
            return "abort"
        choice = "clear"

    if dismiss.isChecked():
        if global_only:
            default_value = _ask_default_action(
                parent,
                config,
                title_key="prompt_cache.new_conversation_default.title",
                message_key="prompt_cache.new_conversation_default.message",
                detail_key="prompt_cache.new_conversation_default.detail",
                options=(
                    ("keep", "prompt_cache.new_conversation_default.keep"),
                    ("clear", "prompt_cache.new_conversation_default.clear"),
                ),
            )
            if default_value is not None:
                _save_default_action(
                    config,
                    "prompt_cache_new_conversation_cache_default",
                    default_value,
                )
                _save_dismiss_flag(config, "suppress_new_conversation_cache_warning")
        else:
            _save_dismiss_flag(config, "suppress_new_conversation_cache_warning")

    return choice


def confirm_import_note_cache_if_needed(
    parent: QWidget,
    config: dict[str, Any],
) -> ImportNoteCacheChoice | None:
    """Returns None when import may proceed without a cache warning."""
    if not has_tracked_active_cache("chat"):
        return None
    if not chat_cache_includes_session_content(config):
        return None

    if is_warning_dismissed(config, "suppress_import_note_cache_warning"):
        return "proceed"

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(tr("prompt_cache.import_note.title", config=config))
    box.setText(tr("prompt_cache.import_note.message", config=config))
    box.setInformativeText(tr("prompt_cache.import_note.detail", config=config))
    box.setStandardButtons(
        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
    )
    box.setDefaultButton(QMessageBox.StandardButton.Ok)

    dismiss = QCheckBox(tr("optimize.warning.dismiss", config=config), box)
    box.setCheckBox(dismiss)

    result = box.exec()
    if result != QMessageBox.StandardButton.Ok:
        return "abort"

    if dismiss.isChecked():
        _save_dismiss_flag(config, "suppress_import_note_cache_warning")

    return "proceed"


def confirm_custom_text_load_replace(parent: QWidget, config: dict[str, Any]) -> bool:
    if is_warning_dismissed(config, "suppress_prompt_cache_custom_text_load_confirm"):
        return True
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(
        tr("settings.prompt_cache_custom_text.load_confirm.title", config=config)
    )
    box.setText(
        tr("settings.prompt_cache_custom_text.load_confirm.message", config=config)
    )
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    box.setDefaultButton(QMessageBox.StandardButton.No)
    dismiss = QCheckBox(tr("optimize.warning.dismiss", config=config), box)
    box.setCheckBox(dismiss)
    if box.exec() != QMessageBox.StandardButton.Yes:
        return False
    if dismiss.isChecked():
        _save_dismiss_flag(config, "suppress_prompt_cache_custom_text_load_confirm")
    return True


def confirm_delete_orphan_caches(parent: QWidget, config: dict[str, Any], *, count: int) -> bool:
    if is_warning_dismissed(config, "suppress_prompt_cache_delete_orphans_confirm"):
        return True
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(
        tr("settings.prompt_cache.manager.delete_orphans.title", config=config)
    )
    box.setText(
        tr(
            "settings.prompt_cache.manager.delete_orphans.message",
            config=config,
            count=count,
        )
    )
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    box.setDefaultButton(QMessageBox.StandardButton.No)
    dismiss = QCheckBox(tr("optimize.warning.dismiss", config=config), box)
    box.setCheckBox(dismiss)
    if box.exec() != QMessageBox.StandardButton.Yes:
        return False
    if dismiss.isChecked():
        _save_dismiss_flag(config, "suppress_prompt_cache_delete_orphans_confirm")
    return True
