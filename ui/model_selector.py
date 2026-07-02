from __future__ import annotations

from typing import Any

from aqt.qt import QComboBox, QCompleter, QStringListModel, Qt, QWidget

from ..constants import GEMINI_MODEL_CHOICES
from ..i18n import tr

MAX_VISIBLE_MODELS = 12
_ALL_MODELS_PROP = "_gemini_all_models"


def model_choice_list(current: str) -> list[str]:
    current = current.strip()
    choices = list(GEMINI_MODEL_CHOICES)
    if current and current not in choices:
        choices.insert(0, current)
    return choices


def filter_model_choices(all_models: list[str], query: str) -> list[str]:
    needle = query.casefold().strip()
    if not needle:
        return list(all_models)

    filtered = [model for model in all_models if needle in model.casefold()]
    stripped = query.strip()
    if filtered:
        return filtered

    if stripped and stripped not in all_models:
        return [stripped]
    return list(all_models)


def model_selector_value(combo: QComboBox) -> str:
    return combo.currentText().strip()


def set_model_selector_value(combo: QComboBox, value: str) -> None:
    value = value.strip()
    all_models: list[str] = list(combo.property(_ALL_MODELS_PROP) or [])
    if value and value not in all_models:
        all_models.insert(0, value)
        combo.setProperty(_ALL_MODELS_PROP, all_models)
    _repopulate_combo(combo, filter_model_choices(all_models, ""), edit_text=value)


def merge_model_choice_lists(*lists: list[str]) -> list[str]:
    from ..gemini_client import sort_model_ids

    merged: list[str] = []
    seen: set[str] = set()
    for items in lists:
        for item in items:
            model_id = item.strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            merged.append(model_id)
    return sort_model_ids(merged)


def update_model_selector_choices(combo: QComboBox, models: list[str]) -> None:
    current = model_selector_value(combo)
    all_models = merge_model_choice_lists(models, list(GEMINI_MODEL_CHOICES))
    if current and current not in all_models:
        all_models.insert(0, current)
    combo.setProperty(_ALL_MODELS_PROP, all_models)
    _repopulate_combo(combo, filter_model_choices(all_models, ""), edit_text=current)


def create_model_selector(
    parent: QWidget,
    *,
    current: str,
    default: str,
    config: dict[str, Any],
) -> QComboBox:
    combo = QComboBox(parent)
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    combo.setMaxVisibleItems(MAX_VISIBLE_MODELS)

    selected = (current or default).strip() or default
    all_models = model_choice_list(selected)
    combo.setProperty(_ALL_MODELS_PROP, all_models)
    combo.addItems(all_models)
    combo.setCurrentText(selected)

    line_edit = combo.lineEdit()
    if line_edit is not None:
        line_edit.setPlaceholderText(tr("settings.model.placeholder", config=config))
        line_edit.textEdited.connect(lambda text, target=combo: _apply_model_filter(target, text))

        completer = QCompleter(all_models, combo)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setMaxVisibleItems(MAX_VISIBLE_MODELS)
        combo.setCompleter(completer)

    return combo


def _update_completer_models(combo: QComboBox, items: list[str]) -> None:
    completer = combo.completer()
    if completer is None:
        return
    completer.setModel(QStringListModel(items))
    completer.setMaxVisibleItems(MAX_VISIBLE_MODELS)


def _repopulate_combo(combo: QComboBox, items: list[str], *, edit_text: str) -> None:
    combo.blockSignals(True)
    combo.clear()
    combo.addItems(items)
    combo.setEditText(edit_text)
    combo.blockSignals(False)
    _update_completer_models(combo, items)


def _apply_model_filter(combo: QComboBox, text: str) -> None:
    all_models: list[str] = list(combo.property(_ALL_MODELS_PROP) or [])
    if not all_models:
        return

    filtered = filter_model_choices(all_models, text)
    _repopulate_combo(combo, filtered, edit_text=text)

    line_edit = combo.lineEdit()
    if line_edit is not None and line_edit.hasFocus():
        combo.showPopup()
