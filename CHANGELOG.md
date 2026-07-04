# Changelog

All notable changes to this project are documented here.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Changed

- **Chat note import UI** — imported fields are editable in the preview above the chat log; **Edit wrapper** replaces the old “Edit imported context” panel (wrapper template only). Smaller default chat window (`520×520`).

### Fixed

- Field name labels in the imported-note preview follow light/dark theme when Anki’s theme changes.

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
- **Note analysis (🧠)** — import all fields into chat for atomicity feedback.
- **Dynamic rules** — chat can persist learned preferences into settings.
- **Built-in defaults** — generic HTML/MathJax system instructions (EN/IT); language-aware.
- **Dismissible warnings** — default-instructions warning on optimize; API key restore warning.
- **Scroll-aware settings UI** — wheel/trackpad no longer changes spinboxes accidentally; text areas scroll by focus.
- **Offline tests** — `tests/test_offline.py` (automated logic tests).
- **CI** — GitHub Actions runs offline tests on push/PR.
- **Optional live API tests** — `tests/test_live_api.py` (see [TESTING.md](TESTING.md)).
- **Documentation** — README, CHANGELOG, example configs, screenshots.

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
