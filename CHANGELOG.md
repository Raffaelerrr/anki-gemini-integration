# Changelog

All notable changes to this project are documented here.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- **Prompt presets** — save/load/import/export instruction packs (optional runtime models/temps/thinking); apply from Settings or chat Edit menu; in-app help topic.
- **Chat transcript download** — export conversation text with quick folders and remembered last directory.
- **Note-type import** — import note types (templates/CSS) into chat; selective include panel for notes and note types.
- **Apply to Anki from chat** — review Gemini `<APPLY_NOTE>` proposals, update imported or collection notes, or open prefilled Add; session history, before/after preview, and undo for the last update.
- **Collection update targets** — choose notes beyond the chat import list (compatible note types), including Browser selection when open.
- **Stale-note fallback** — if an update target was deleted, open Add with fields prefilled instead of failing hard.
- **Duplicate-update warning** — dismissible confirm when an update would match Anki’s first-field duplicate rule.
- **Browser selection sync** — reactivating the apply window refreshes update targets from the current Browser selection.
- **Dev playground** — Open settings shortcut; mock chat replies include a sample `<APPLY_NOTE>` for Apply-to-Anki smoke tests.

### Changed

- **Chat note import UI** — imported fields are editable; **Edit wrapper** for session wrapper template; include panel for notes and note types.
- Offline test harness updated for current Qt window flags / widgets and request-first wrapper defaults.
- Preset diff/preview strings and several fallback labels are localized (EN/IT).
- Empty API key is rejected in `gemini_client` after mock mode is considered (not only in the UI).
- README / settings guide / example configs aligned with presets and chat toolbar.
- Theme refresh unified via `register_themed_window` (chat/settings/playground included).
- `i18n` catalog split into `i18n_strings.py`; chat request lifecycle extracted to `ui/chat_request_lifecycle.py`.
- Path handling uses `pathlib` in config / prompt-cache / markdown loader; PyQt5 SVG fallback removed (PyQt6 only).
- Note-apply soft-fail handlers narrowed (no bare `except Exception`).

### Fixed

- Field name labels in the imported-note preview follow light/dark theme when Anki’s theme changes.
- Offline suite was failing on stale Qt stubs and outdated wrapper-order / config-version assertions.

---

## [2.0.0] — 2026-07-03

### Added

- **Split system instructions** — optional shared toggle; separate optimize and chat instructions when disabled.
- **Settings guide** — non-modal help dialog with per-setting explanations.
- **Model picker** — filterable dropdowns with refresh from the Gemini API.
- **Restore defaults** — selective reset with checkboxes; restore dismissed warnings separately.
- **Theme support** — light/dark UI that follows Anki’s theme.
- **Streaming chat** — replies appear as they arrive (configurable).
- **Per-purpose models & thinking budgets** — different settings for optimize vs chat.
- **Optimization preview** — optional confirm-before-apply dialog.
- **Undo** — revert last field optimization in the session.
- **Note analysis (brain icon)** — import all fields into chat for atomicity feedback.
- **Dynamic rules** — chat can persist learned preferences into settings.
- **Built-in defaults** — generic HTML/MathJax system instructions (EN/IT); language-aware.
- **Dismissible warnings** — default-instructions warning on optimize; API key restore warning.
- **Scroll-aware settings UI** — wheel/trackpad no longer changes spinboxes accidentally; text areas scroll by focus.
- **Offline tests** — `tests/test_offline.py` (automated logic tests).
- **CI** — GitHub Actions runs offline tests on push/PR.
- **Optional live API tests** — `tests/test_live_api.py` (see [TESTING.md](TESTING.md)).
- **Documentation** — README, CHANGELOG, example configs.

### Changed

- Default interface language: **English** (was Italian).
- Repository renamed to `anki-gemini-integration`.
- Gemini prompt strings (chat format, meta-rules, dynamic rules) are now **fully localized** (EN/IT).
- Restore defaults: API key is **unchecked by default**; clearing it requires confirmation.

### Fixed

- Chat crash when theme applied before widgets existed.
- Settings footer layout; button tooltips and alignment.
- Restore defaults for system instructions in split mode.
- Multiple simultaneous text selections across settings text areas.

### Security / privacy

- API key stored locally in Anki `meta.json` (gitignored).
- Card content sent to Google Gemini API when you use optimize or chat.

---

## [1.x] — earlier history

### Added

- Initial Gemini integration: field optimize, chat, settings dialog.
- Italian/English UI (`i18n`).
- Legacy config migration from `config_gemini.json`.
- Vendored Python-Markdown for chat formatting.
- MIT license and AI development disclaimer.

[2.0.0]: https://github.com/Raffaelerrr/anki-gemini-integration/compare/435d8d6...c2a992e
