from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aqt.qt import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QEvent,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTimer,
    QVBoxLayout,
    Qt,
)
from aqt.utils import showWarning

from ..config import is_warning_dismissed, load_config, save_config
from ..i18n import tr
from ..note_apply import (
    ApplyHistoryItem,
    ApplyNoteHistory,
    AvailableNotetype,
    FieldMappingReport,
    ImportedNoteTarget,
    NoteApplyExecutionResult,
    NoteApplyPlan,
    collect_available_notetypes,
    fields_after_apply_preview,
    fields_as_tuples,
    filter_existing_update_targets,
    has_apply_undo,
    load_browser_selected_notes,
    load_collection_notes_for_notetypes,
    load_note_fields_for_preview,
    merge_update_targets,
    proposal_with_fields,
    rank_imported_update_targets,
    rank_notetypes_for_create,
    rank_update_targets,
    update_would_create_anki_duplicate,
)
from ..note_context_fields import ImportedNoteData, ordered_imported_notes
from .note_apply_collection_picker import pick_collection_note
from .note_apply_diff_preview import NoteApplyDiffPreviewWindow
from .note_fields_editor import NoteFieldsEditor
from .settings_compact_controls import create_settings_hint_label
from .theme import muted_hint_html
from .themed_windows import configure_snappable_window, register_themed_window

_OnApply = Callable[[NoteApplyPlan], NoteApplyExecutionResult]
_OnUndo = Callable[[], NoteApplyExecutionResult]


class NoteApplyDialog(QDialog):
    """Apply Gemini proposals from session history; stays open while unapplied remain."""

    def __init__(
        self,
        parent,
        history: ApplyNoteHistory,
        *,
        on_apply: _OnApply,
        on_undo: _OnUndo | None = None,
        imported_notes: dict[int, ImportedNoteData] | None = None,
        session_notetypes: list[Any] | None = None,
        available_notetypes: list[AvailableNotetype] | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config or load_config()
        self._history = history
        self._on_apply = on_apply
        self._on_undo = on_undo
        self._imported_notes = dict(imported_notes or {})
        self._available_notetypes = list(
            available_notetypes
            if available_notetypes is not None
            else collect_available_notetypes(
                session_notetypes=session_notetypes,
                include_collection=True,
            )
        )
        self._update_targets: list[ImportedNoteTarget] = []
        self._create_matches: list[Any] = []
        self._syncing_ui = False
        self._applied_any = False
        self._diff_preview: NoteApplyDiffPreviewWindow | None = None
        self._extra_collection_notes: dict[int, ImportedNoteData] = {}

        # Modeless (show(), not exec()) so AddCards / other windows can take focus.
        configure_snappable_window(self, application_modal=False)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        register_themed_window(self)
        self.setWindowTitle(tr("chat.apply_note.title", config=self._config))
        self.resize(720, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._intro_label = create_settings_hint_label(
            self,
            tr("chat.apply_note.intro", config=self._config),
        )
        root.addWidget(self._intro_label)

        proposal_row = QHBoxLayout()
        self._proposal_label = QLabel(
            tr("chat.apply_note.proposal", config=self._config),
            self,
        )
        proposal_row.addWidget(self._proposal_label)
        self._proposal_combo = QComboBox(self)
        _prefer_combo_without_native_check(self._proposal_combo)
        self._proposal_combo.currentIndexChanged.connect(self._on_proposal_changed)
        proposal_row.addWidget(self._proposal_combo, 1)
        root.addLayout(proposal_row)

        self._meta_label = QLabel(self)
        self._meta_label.setWordWrap(True)
        self._meta_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        root.addWidget(self._meta_label)

        self._mode_group = QButtonGroup(self)
        self._update_radio = QRadioButton(
            tr("chat.apply_note.mode.update", config=self._config),
            self,
        )
        self._create_radio = QRadioButton(
            tr("chat.apply_note.mode.create", config=self._config),
            self,
        )
        self._mode_group.addButton(self._update_radio)
        self._mode_group.addButton(self._create_radio)
        self._update_radio.toggled.connect(self._on_mode_changed)
        self._create_radio.toggled.connect(self._on_mode_changed)
        root.addWidget(self._update_radio)
        root.addWidget(self._create_radio)

        target_row = QHBoxLayout()
        self._target_label = QLabel(self)
        target_row.addWidget(self._target_label)
        self._target_combo = QComboBox(self)
        _prefer_combo_without_native_check(self._target_combo)
        self._target_combo.currentIndexChanged.connect(self._on_target_changed)
        target_row.addWidget(self._target_combo, 1)
        self._collection_btn = QPushButton(self)
        self._collection_btn.clicked.connect(self._choose_collection_note)
        target_row.addWidget(self._collection_btn)
        root.addLayout(target_row)

        self._warning_label = create_settings_hint_label(self, "")
        self._warning_label.setVisible(False)
        root.addWidget(self._warning_label)

        self._editor = NoteFieldsEditor(self)
        root.addWidget(self._editor, 1)

        self._footer_hint = create_settings_hint_label(
            self,
            tr("chat.apply_note.apply_hint", config=self._config),
        )
        root.addWidget(self._footer_hint)

        buttons = QHBoxLayout()
        self._preview_btn = QPushButton(self)
        self._preview_btn.clicked.connect(self._open_diff_preview)
        buttons.addWidget(self._preview_btn)
        self._undo_btn = QPushButton(self)
        self._undo_btn.clicked.connect(self._undo_last_apply)
        buttons.addWidget(self._undo_btn)
        buttons.addStretch(1)
        self._cancel_btn = QPushButton(
            tr("preview.cancel", config=self._config),
            self,
        )
        self._cancel_btn.clicked.connect(self.reject)
        self._confirm_btn = QPushButton(
            tr("chat.apply_note.apply", config=self._config),
            self,
        )
        self._confirm_btn.setDefault(True)
        self._confirm_btn.clicked.connect(self._apply_current)
        buttons.addWidget(self._cancel_btn)
        buttons.addWidget(self._confirm_btn)
        root.addLayout(buttons)

        self._rebuild_proposal_combo(select_suggested=True)
        self.apply_theme()
        self._refresh_action_buttons()

    def applied_any(self) -> bool:
        return self._applied_any

    def refresh_from_history(self, *, select_suggested: bool = True) -> None:
        """Reload proposals from the shared history (e.g. dialog already open)."""
        self._rebuild_proposal_combo(select_suggested=select_suggested)

    def refresh_actions(self) -> None:
        """Refresh Preview / Undo / Collection button enabled state."""
        self._refresh_action_buttons()

    def changeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().changeEvent(event)
        try:
            if event.type() != QEvent.Type.ActivationChange:
                return
            if not self.isActiveWindow():
                return
        except Exception:
            return
        self._refresh_browser_targets_on_focus()

    def _refresh_browser_targets_on_focus(self) -> None:
        """Refresh Browser-selected update targets when this window is reactivated."""
        item = self._current_item()
        if item is None or self._syncing_ui:
            return
        selected_id = self._target_combo.currentData()
        proposal = proposal_with_fields(item.proposal, self._editor.get_fields())
        before = [(t.note_id, t.source) for t in self._update_targets]
        self._rebuild_update_targets(proposal)
        after = [(t.note_id, t.source) for t in self._update_targets]
        if before == after:
            return
        was_update = self._update_radio.isChecked()
        self._syncing_ui = True
        try:
            if was_update or self._update_targets:
                self._update_radio.setChecked(True)
            self._populate_targets()
            if selected_id is not None:
                for row in range(self._target_combo.count()):
                    if self._target_combo.itemData(row) == selected_id:
                        self._target_combo.setCurrentIndex(row)
                        break
        finally:
            self._syncing_ui = False
        self._refresh_mode_labels()
        self._refresh_warning()
        self._update_confirm_enabled()

    def _confirm_duplicate_update(self, plan: NoteApplyPlan) -> bool:
        if plan.mode != "update" or plan.target_note_id is None:
            return True
        config = load_config()
        if is_warning_dismissed(config, "suppress_apply_note_duplicate_warning"):
            return True
        try:
            is_dupe = update_would_create_anki_duplicate(
                int(plan.target_note_id),
                plan.proposal.fields,
            )
        except Exception:
            is_dupe = False
        if not is_dupe:
            return True

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(
            tr("chat.apply_note.duplicate.title", config=config)
        )
        box.setText(tr("chat.apply_note.duplicate.message", config=config))
        box.setInformativeText(
            tr("chat.apply_note.duplicate.detail", config=config)
        )
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
            updated["suppress_apply_note_duplicate_warning"] = True
            save_config(updated)
            self._config = updated
        return True

    def apply_theme(self) -> None:
        self._editor.apply_theme()
        self._intro_label.setText(
            muted_hint_html(tr("chat.apply_note.intro", config=self._config))
        )
        self._footer_hint.setText(
            muted_hint_html(tr("chat.apply_note.apply_hint", config=self._config))
        )
        self._refresh_warning()
        self._refresh_action_buttons()

    def apply_language(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or load_config()
        self.setWindowTitle(tr("chat.apply_note.title", config=self._config))
        self._proposal_label.setText(tr("chat.apply_note.proposal", config=self._config))
        self._update_radio.setText(
            tr("chat.apply_note.mode.update", config=self._config)
        )
        self._create_radio.setText(
            tr("chat.apply_note.mode.create", config=self._config)
        )
        self._collection_btn.setText(
            tr("chat.apply_note.collection.button", config=self._config)
        )
        self._preview_btn.setText(
            tr("chat.apply_note.diff.button", config=self._config)
        )
        self._undo_btn.setText(tr("chat.apply_note.undo.button", config=self._config))
        self._cancel_btn.setText(tr("preview.cancel", config=self._config))
        self._confirm_btn.setText(tr("chat.apply_note.apply", config=self._config))
        self._rebuild_proposal_combo(select_suggested=False)
        self.apply_theme()
        self._refresh_mode_labels()
        self._refresh_warning()
        self._refresh_action_buttons()

    def _current_item(self) -> ApplyHistoryItem | None:
        item_id = self._proposal_combo.currentData()
        if item_id is None:
            return None
        return self._history.get(str(item_id))

    def _proposal_item_label(self, item: ApplyHistoryItem) -> str:
        note = item.proposal
        parts = [
            tr(
                "chat.apply_note.proposal_item",
                config=self._config,
                n=item.seq,
            )
        ]
        if note.notetype:
            parts.append(note.notetype)
        field_names = ", ".join(note.fields.keys())
        if field_names:
            parts.append(field_names)
        label = " — ".join(parts)
        if item.applied:
            # ASCII suffix — avoid Unicode checkmarks (Windows combo fonts often break them)
            # and avoid competing with the native "current item" check some styles draw.
            applied = tr("chat.apply_note.meta.applied", config=self._config)
            return f"{label} · {applied}"
        return label

    def _rebuild_proposal_combo(self, *, select_suggested: bool) -> None:
        items = self._history.items
        current_id = None if select_suggested else self._proposal_combo.currentData()
        suggested = self._history.suggest_focus_item() if select_suggested else None
        self._syncing_ui = True
        try:
            self._proposal_combo.clear()
            select_row = 0
            for row, item in enumerate(items):
                self._proposal_combo.addItem(
                    self._proposal_item_label(item),
                    item.item_id,
                )
                if suggested is not None and item.item_id == suggested.item_id:
                    select_row = row
                elif (
                    suggested is None
                    and current_id is not None
                    and item.item_id == current_id
                ):
                    select_row = row
            visible = len(items) > 0
            self._proposal_combo.setVisible(visible)
            self._proposal_label.setVisible(visible)
            if items:
                self._proposal_combo.setCurrentIndex(select_row)
        finally:
            self._syncing_ui = False

        item = self._current_item()
        if item is not None:
            self._history.remember_offered(item.item_id)
            self._reload_for_item(item)
        else:
            self._editor.set_fields([])
            self._update_confirm_enabled()

    def _on_proposal_changed(self, _index: int) -> None:
        if self._syncing_ui:
            return
        item = self._current_item()
        if item is None:
            return
        self._history.remember_offered(item.item_id)
        self._reload_for_item(item)

    def _on_mode_changed(self, _checked: bool = False) -> None:
        if self._syncing_ui:
            return
        self._populate_targets()
        self._refresh_mode_labels()
        self._refresh_warning()
        self._update_confirm_enabled()
        self._refresh_action_buttons()

    def _on_target_changed(self, _index: int) -> None:
        if self._syncing_ui:
            return
        self._refresh_warning()
        self._update_confirm_enabled()
        self._refresh_action_buttons()

    def _rebuild_update_targets(self, proposal) -> None:
        imported = rank_imported_update_targets(
            proposal,
            ordered_imported_notes(self._imported_notes),
        )
        browser_notes = load_browser_selected_notes(
            exclude_ids={t.note_id for t in imported}
        )
        browser = rank_update_targets(
            proposal,
            browser_notes,
            source="browser",
            require_overlap=False,
        )
        extras = rank_update_targets(
            proposal,
            list(self._extra_collection_notes.values()),
            source="collection",
            require_overlap=False,
        )
        # Prefer imported, then browser selection, then manually picked collection notes.
        merged = merge_update_targets(imported, browser, extras)
        self._update_targets = filter_existing_update_targets(merged)

    def _reload_for_item(self, item: ApplyHistoryItem) -> None:
        proposal = item.proposal
        self._rebuild_update_targets(proposal)
        self._create_matches = rank_notetypes_for_create(
            proposal,
            self._available_notetypes,
        )

        self._syncing_ui = True
        try:
            self._meta_label.setText(self._format_meta(proposal, item.applied))
            self._editor.set_fields(fields_as_tuples(proposal))

            can_create = bool(self._create_matches)
            can_update = (
                bool(self._update_targets)
                or can_create
                or bool(self._available_notetypes)
            )
            self._update_radio.setEnabled(can_update)
            self._create_radio.setEnabled(can_create)

            if self._update_targets:
                self._update_radio.setChecked(True)
            elif can_create:
                self._create_radio.setChecked(True)
            elif can_update:
                self._update_radio.setChecked(True)
            else:
                self._update_radio.setChecked(False)
                self._create_radio.setChecked(False)

            self._populate_targets()
        finally:
            self._syncing_ui = False

        self._refresh_mode_labels()
        self._refresh_warning()
        self._update_confirm_enabled()
        self._refresh_action_buttons()

    def _populate_targets(self) -> None:
        self._syncing_ui = True
        try:
            self._target_combo.clear()
            if self._update_radio.isChecked():
                self._target_label.setText(
                    tr("chat.apply_note.target.note", config=self._config)
                )
                preferred_row = 0
                for row, target in enumerate(self._update_targets):
                    bits = [target.label]
                    if target.notetype_name and target.notetype_name not in target.label:
                        bits[0] = f"{target.label} ({target.notetype_name})"
                    if target.source == "browser":
                        bits.append(
                            tr(
                                "chat.apply_note.target.from_browser",
                                config=self._config,
                            )
                        )
                    elif target.source == "collection":
                        bits.append(
                            tr(
                                "chat.apply_note.target.from_collection",
                                config=self._config,
                            )
                        )
                    if target.preferred:
                        bits.append(
                            tr("chat.apply_note.target.suggested", config=self._config)
                        )
                    self._target_combo.addItem(" — ".join(bits), target.note_id)
                    if target.preferred:
                        preferred_row = row
                if self._target_combo.count() > 0:
                    self._target_combo.setCurrentIndex(preferred_row)
            elif self._create_radio.isChecked():
                self._target_label.setText(
                    tr("chat.apply_note.target.notetype", config=self._config)
                )
                for match in self._create_matches:
                    label = match.notetype.name
                    overlap = int(round(match.report.overlap_score * 100))
                    label = tr(
                        "chat.apply_note.target.notetype_item",
                        config=self._config,
                        name=label,
                        overlap=overlap,
                    )
                    self._target_combo.addItem(label, match.notetype.notetype_id)
                if self._target_combo.count() > 0:
                    self._target_combo.setCurrentIndex(0)
            else:
                self._target_label.setText(
                    tr("chat.apply_note.target.unavailable", config=self._config)
                )
            has_targets = self._target_combo.count() > 0
            self._target_combo.setVisible(has_targets)
            self._target_label.setVisible(True)
            self._collection_btn.setVisible(self._update_radio.isChecked())
        finally:
            self._syncing_ui = False

    def _refresh_mode_labels(self) -> None:
        update_count = len(self._update_targets)
        create_count = len(self._create_matches)
        self._update_radio.setText(
            tr(
                "chat.apply_note.mode.update_count",
                config=self._config,
                count=update_count,
            )
            if update_count
            else tr("chat.apply_note.mode.update", config=self._config)
        )
        self._create_radio.setText(
            tr(
                "chat.apply_note.mode.create_count",
                config=self._config,
                count=create_count,
            )
            if create_count
            else tr("chat.apply_note.mode.create", config=self._config)
        )

    def _current_report(self) -> FieldMappingReport | None:
        if self._update_radio.isChecked():
            note_id = self._target_combo.currentData()
            for target in self._update_targets:
                if target.note_id == note_id:
                    return target.report
            return None
        if self._create_radio.isChecked():
            notetype_id = self._target_combo.currentData()
            for match in self._create_matches:
                if match.notetype.notetype_id == notetype_id:
                    return match.report
        return None

    def _refresh_warning(self) -> None:
        parts: list[str] = []
        item = self._current_item()
        if item is not None and item.applied:
            parts.append(
                tr("chat.apply_note.warn.already_applied", config=self._config)
            )
        report = self._current_report()
        if report is not None and report.has_mismatches:
            if report.missing_in_proposal:
                parts.append(
                    tr(
                        "chat.apply_note.warn.missing",
                        config=self._config,
                        fields=", ".join(report.missing_in_proposal),
                    )
                )
            if report.extra_in_proposal:
                parts.append(
                    tr(
                        "chat.apply_note.warn.extra",
                        config=self._config,
                        fields=", ".join(report.extra_in_proposal),
                    )
                )
        if not parts:
            self._warning_label.setVisible(False)
            self._warning_label.setText("")
            return
        self._warning_label.setText(muted_hint_html(" ".join(parts)))
        self._warning_label.setVisible(True)

    def _update_confirm_enabled(self) -> None:
        item = self._current_item()
        if item is None:
            self._confirm_btn.setEnabled(False)
            self._refresh_action_buttons()
            return
        has_mode = self._update_radio.isChecked() or self._create_radio.isChecked()
        has_target = self._target_combo.currentData() is not None
        # Update mode can still proceed via collection picker even with empty combo.
        if self._update_radio.isChecked() and not has_target:
            self._confirm_btn.setEnabled(False)
        else:
            self._confirm_btn.setEnabled(
                has_mode and has_target and self._editor.has_fields()
            )
        self._refresh_action_buttons()

    def _refresh_action_buttons(self) -> None:
        self._collection_btn.setText(
            tr("chat.apply_note.collection.button", config=self._config)
        )
        self._preview_btn.setText(
            tr("chat.apply_note.diff.button", config=self._config)
        )
        self._undo_btn.setText(tr("chat.apply_note.undo.button", config=self._config))
        self._collection_btn.setEnabled(self._update_radio.isChecked())
        self._preview_btn.setEnabled(
            self._update_radio.isChecked()
            and self._target_combo.currentData() is not None
            and self._editor.has_fields()
        )
        self._undo_btn.setEnabled(bool(self._on_undo) and has_apply_undo())

    def _choose_collection_note(self) -> None:
        item = self._current_item()
        if item is None:
            return
        proposal = proposal_with_fields(item.proposal, self._editor.get_fields())
        notetype_ids = [
            match.notetype.notetype_id for match in self._create_matches
        ]
        if not notetype_ids:
            notetype_ids = [nt.notetype_id for nt in self._available_notetypes]
        exclude = set(self._imported_notes) | set(self._extra_collection_notes)
        notes = load_collection_notes_for_notetypes(
            notetype_ids,
            exclude_ids=exclude,
        )
        # Also allow re-picking notes already listed so the filter UI is useful.
        already = {
            nid: data
            for nid, data in {
                **self._imported_notes,
                **self._extra_collection_notes,
            }.items()
        }
        for data in already.values():
            if all(n.note_id != data.note_id for n in notes):
                notes.append(data)
        if not notes:
            showWarning(
                tr("chat.apply_note.collection.empty", config=self._config),
                parent=self,
            )
            return
        note_id = pick_collection_note(
            self,
            notes,
            proposal=proposal,
            config=self._config,
        )
        if note_id is None:
            return
        chosen = next((n for n in notes if n.note_id == note_id), None)
        if chosen is None:
            return
        self._extra_collection_notes[chosen.note_id] = chosen
        self._rebuild_update_targets(proposal)
        if not self._update_radio.isChecked():
            self._update_radio.setChecked(True)
        self._populate_targets()
        # Select the chosen note.
        for row in range(self._target_combo.count()):
            if self._target_combo.itemData(row) == chosen.note_id:
                self._target_combo.setCurrentIndex(row)
                break
        self._refresh_mode_labels()
        self._refresh_warning()
        self._update_confirm_enabled()

    def _open_diff_preview(self) -> None:
        if not self._update_radio.isChecked():
            return
        note_id = self._target_combo.currentData()
        if note_id is None:
            return
        item = self._current_item()
        if item is None:
            return
        before, notetype_id = load_note_fields_for_preview(int(note_id))
        if not before:
            # Fall back to imported/extra session copy.
            data = self._imported_notes.get(int(note_id)) or self._extra_collection_notes.get(
                int(note_id)
            )
            if data is None:
                showWarning(
                    tr("chat.apply_note.error.missing_note", config=self._config),
                    parent=self,
                )
                return
            before = list(data.fields)
            notetype_id = data.notetype_id
        proposal = proposal_with_fields(item.proposal, self._editor.get_fields())
        after = fields_after_apply_preview(proposal, before)
        if self._diff_preview is None:
            self._diff_preview = NoteApplyDiffPreviewWindow(self)
            self._diff_preview.destroyed.connect(
                lambda *_: setattr(self, "_diff_preview", None)
            )
        self._diff_preview.show_diff(
            before=before,
            after=after,
            notetype_id=notetype_id,
            config=self._config,
        )

    def _undo_last_apply(self) -> None:
        if self._on_undo is None:
            return
        result = self._on_undo()
        if not result.ok:
            showWarning(
                tr(
                    result.message_key,
                    config=self._config,
                    **result.message_kwargs,
                ),
                parent=self,
            )
        self._refresh_action_buttons()

    def _format_meta(self, proposal, applied: bool) -> str:
        bits: list[str] = []
        if applied:
            bits.append(tr("chat.apply_note.meta.applied", config=self._config))
        if proposal.notetype:
            bits.append(
                tr(
                    "chat.apply_note.meta.notetype",
                    config=self._config,
                    name=proposal.notetype,
                )
            )
        if proposal.deck:
            bits.append(
                tr(
                    "chat.apply_note.meta.deck",
                    config=self._config,
                    name=proposal.deck,
                )
            )
        if proposal.tags:
            bits.append(
                tr(
                    "chat.apply_note.meta.tags",
                    config=self._config,
                    tags=", ".join(proposal.tags),
                )
            )
        if not bits:
            return tr("chat.apply_note.meta.none", config=self._config)
        return " · ".join(bits)

    def _build_plan(self) -> NoteApplyPlan | None:
        item = self._current_item()
        if item is None:
            return None
        proposal = proposal_with_fields(item.proposal, self._editor.get_fields())
        report = self._current_report()
        if self._update_radio.isChecked():
            note_id = self._target_combo.currentData()
            if note_id is None:
                return None
            target = next(
                (entry for entry in self._update_targets if entry.note_id == note_id),
                None,
            )
            return NoteApplyPlan(
                mode="update",
                proposal_index=item.seq - 1,
                proposal=proposal,
                target_note_id=int(note_id),
                target_notetype_id=target.notetype_id if target else None,
                target_notetype_name=target.notetype_name if target else None,
                field_report=report,
                history_item_id=item.item_id,
            )
        if self._create_radio.isChecked():
            notetype_id = self._target_combo.currentData()
            if notetype_id is None:
                return None
            match = next(
                (
                    entry
                    for entry in self._create_matches
                    if entry.notetype.notetype_id == notetype_id
                ),
                None,
            )
            return NoteApplyPlan(
                mode="create",
                proposal_index=item.seq - 1,
                proposal=proposal,
                target_notetype_id=int(notetype_id),
                target_notetype_name=match.notetype.name if match else None,
                field_report=report,
                history_item_id=item.item_id,
            )
        return None

    def _apply_current(self) -> None:
        plan = self._build_plan()
        if plan is None:
            return
        if not self._confirm_duplicate_update(plan):
            return
        item = self._current_item()
        was_unapplied = item is not None and not item.applied
        result = self._on_apply(plan)
        if not result.ok:
            showWarning(
                tr(
                    result.message_key,
                    config=self._config,
                    **result.message_kwargs,
                ),
                parent=self,
            )
            return

        if plan.history_item_id:
            self._history.mark_applied(plan.history_item_id)
        self._applied_any = True
        self._refresh_action_buttons()

        # Re-applying an already-applied note must not close the window (AddCards focus).
        all_done = was_unapplied and not self._history.has_unapplied()
        if all_done:
            # Defer close on create so AddCards can take focus first.
            if plan.mode == "create":
                QTimer.singleShot(150, self.accept)
            else:
                self.accept()
            return

        self._rebuild_proposal_combo(select_suggested=was_unapplied)
        self._refresh_action_buttons()


def _prefer_combo_without_native_check(combo: QComboBox) -> None:
    """Hide the Windows/QSS 'current item' checkmark in combo popups.

    Native Windows styles (and some QSS paths) draw a check next to the current
    value. Fusion alone is not enough once stylesheets are involved.
    """
    combo.setObjectName("ankiAiNoCheckCombo")
    # Zero-size indicator — the reliable QSS fix when list styling is active.
    combo.setStyleSheet(
        "#ankiAiNoCheckCombo::indicator,"
        "#ankiAiNoCheckCombo QAbstractItemView::indicator {"
        "  width: 0px;"
        "  height: 0px;"
        "  border: none;"
        "  background: transparent;"
        "  image: none;"
        "}"
        "#ankiAiNoCheckCombo::item:checked {"
        "  font-weight: normal;"
        "}"
    )

    try:
        from aqt.qt import (  # type: ignore
            QListView,
            QProxyStyle,
            QStyle,
            QStyledItemDelegate,
            QStyleOptionMenuItem,
            QStyleOptionViewItem,
        )
    except Exception:
        return

    def _clear_check_state(option) -> None:
        try:
            features = getattr(QStyleOptionViewItem, "ViewItemFeature", None)
            has_check = getattr(features, "HasCheckIndicator", None) if features else None
            if has_check is not None and hasattr(option, "features"):
                option.features &= ~has_check
        except Exception:
            pass
        try:
            option.checkState = Qt.CheckState.Unchecked
        except Exception:
            pass
        try:
            state_enum = getattr(QStyle, "StateFlag", QStyle)
            state_on = getattr(state_enum, "State_On", 0)
            if state_on and hasattr(option, "state"):
                option.state &= ~state_on
        except Exception:
            pass

    class _NoCheckDelegate(QStyledItemDelegate):
        def initStyleOption(self, option, index) -> None:  # noqa: N802
            super().initStyleOption(option, index)
            _clear_check_state(option)

        def paint(self, painter, option, index) -> None:  # noqa: N802
            opt = QStyleOptionViewItem(option)
            _clear_check_state(opt)
            super().paint(painter, opt, index)

    class _NoCheckComboStyle(QProxyStyle):
        def drawPrimitive(self, element, option, painter, widget=None):  # noqa: N802
            pe = getattr(QStyle, "PrimitiveElement", QStyle)
            skip = {
                getattr(pe, "PE_IndicatorItemViewItemCheck", None),
                getattr(pe, "PE_IndicatorViewItemCheck", None),
                getattr(pe, "PE_IndicatorMenuCheckMark", None),
            }
            if element in skip:
                return
            return super().drawPrimitive(element, option, painter, widget)

        def drawControl(self, element, option, painter, widget=None):  # noqa: N802
            ce = getattr(QStyle, "ControlElement", QStyle)
            if element == getattr(ce, "CE_MenuItem", None):
                try:
                    opt = QStyleOptionMenuItem(option)
                    opt.checked = False
                    check_type = getattr(
                        QStyleOptionMenuItem, "CheckType", None
                    )
                    not_checkable = getattr(check_type, "NotCheckable", None)
                    if not_checkable is not None:
                        opt.checkType = not_checkable
                    return super().drawControl(element, opt, painter, widget)
                except Exception:
                    pass
            if element == getattr(ce, "CE_ItemViewItem", None):
                try:
                    opt = QStyleOptionViewItem(option)
                    _clear_check_state(opt)
                    return super().drawControl(element, opt, painter, widget)
                except Exception:
                    pass
            return super().drawControl(element, option, painter, widget)

        def styleHint(self, hint, option=None, widget=None, returnData=None):  # noqa: N802
            sh = getattr(QStyle, "StyleHint", QStyle)
            # Prefer list popup over menu-style popup (menu style draws checks).
            if hint == getattr(sh, "SH_ComboBox_Popup", None):
                return 0
            return super().styleHint(hint, option, widget, returnData)

    try:
        view = QListView(combo)
        delegate = _NoCheckDelegate(view)
        view.setItemDelegate(delegate)
        combo.setView(view)
        combo.setItemDelegate(_NoCheckDelegate(combo))
    except Exception:
        pass

    try:
        style = _NoCheckComboStyle("Fusion")
        style.setParent(combo)
        combo.setStyle(style)
    except Exception:
        pass


def open_note_apply_dialog(
    parent,
    history: ApplyNoteHistory,
    *,
    on_apply: _OnApply,
    on_undo: _OnUndo | None = None,
    imported_notes: dict[int, ImportedNoteData] | None = None,
    session_notetypes: list[Any] | None = None,
    available_notetypes: list[AvailableNotetype] | None = None,
    config: dict[str, Any] | None = None,
    existing: NoteApplyDialog | None = None,
) -> NoteApplyDialog | None:
    """Show the apply dialog modelessly. Returns the dialog, or None if history empty."""
    if len(history) == 0:
        return None
    if existing is not None:
        try:
            if existing.isVisible():
                existing.refresh_from_history(select_suggested=True)
                existing.raise_()
                existing.activateWindow()
                return existing
        except RuntimeError:
            pass
    dialog = NoteApplyDialog(
        parent,
        history,
        on_apply=on_apply,
        on_undo=on_undo,
        imported_notes=imported_notes,
        session_notetypes=session_notetypes,
        available_notetypes=available_notetypes,
        config=config,
    )
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog
