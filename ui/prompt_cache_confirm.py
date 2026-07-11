from __future__ import annotations

from typing import Any, Literal

from aqt.qt import QMessageBox, QWidget

from ..constants import GEMINI_AI_STUDIO_BILLING_URL
from ..i18n import tr
from ..prompt_cache import (
    PromptCacheBundle,
    needs_prompt_cache_recreate_confirm,
    prompt_cache_ttl_seconds,
)
from ..gemini_client import Purpose

PromptCacheRecreateChoice = Literal["proceed", "skip_cache", "abort"]


def confirm_prompt_cache_recreate_if_needed(
    parent: QWidget,
    config: dict[str, Any],
    bundle: PromptCacheBundle | None,
    *,
    purpose: Purpose,
) -> PromptCacheRecreateChoice:
    if not needs_prompt_cache_recreate_confirm(config, bundle, purpose=purpose):
        return "proceed"

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
    result = box.exec()
    if result == QMessageBox.StandardButton.Cancel:
        return "abort"
    if result == QMessageBox.StandardButton.No:
        return "skip_cache"
    return "proceed"
