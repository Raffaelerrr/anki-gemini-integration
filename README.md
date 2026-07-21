# Anki AI Assistant (Gemini)

An Anki add-on that integrates **Google Gemini** into the note editor: optimize HTML/MathJax fields, chat about your notes, and analyze whether a note should be split for atomicity.

**Repository:** [github.com/Raffaelerrr/anki-gemini-integration](https://github.com/Raffaelerrr/anki-gemini-integration)  
**Version:** 2.0.0 · see [CHANGELOG.md](CHANGELOG.md)  
**Author:** Raffaele  
**Requires:** Anki 2.1.49+ (point version 49; **Qt6** recommended — SVG toolbar icons use PyQt6)  
**License:** [MIT](LICENSE)

> **Disclaimer:** This add-on was developed with substantial assistance from AI coding tools (including Cursor and large language models). The author reviewed and tested the project, but errors or unexpected behavior may remain. Use at your own discretion.

---

## Features

### Field optimization (`Gemini` · `Ctrl+Shift+G` / `Cmd+Shift+G`)

Optimizes the **currently focused field** using your system instructions (HTML structure, MathJax `\(...\)` / `\[...\]`, plain-math conversion, custom rules). Uses a dedicated model and thinking budget tuned for fast edits. Optional **preview before apply** and **undo** (undo icon) for the last optimization in the session.

### Note analysis (brain icon)

Imports **all fields** of the current note into chat and asks Gemini whether the note should be decomposed into smaller atomic cards.

### Chat (chat icon · `Ctrl+Alt+C` / `Cmd+Alt+C`)

Streaming chat with Markdown replies. When Gemini suggests Anki field content, **copy buttons** appear on code blocks. Also in **Tools → Gemini chat**.

After **brain icon** note import, use the **include** panel to choose which imported notes and note types go into the next message. Check options there, then send; use **Edit wrapper** (pencil menu) to adjust the `{{context}}` / `{{request}}` template for that session.

**Chat toolbar (compact icons — hover for tooltips):**

- **Brain** — open include choices for imported notes / note types in the next message
- **Pencil menu** — edit note fields, context wrapper, card templates, **Apply to Anki**, undo last note apply, or apply a **prompt preset**
- **Import** — import note types (templates/CSS) into chat
- **Eye** — open imported-note preview in a separate window
- **Lens** — read-only **prompt inspect** (preview full outgoing prompt without sending)
- **Cache** — chat prompt-cache settings (TTL, segments, custom text)
- **Stop / priority** — toggle **pre-send review** (edit prompt before Gemini) vs send directly
- **Download** — export the conversation as plain text (last folder, quick folders, or browse)
- **Plus** — new conversation (applies settings that require a fresh session)

From **Edit note**, you can optionally **send empty fields** when building note context.

### Apply to Anki (chat · Edit → Apply to Anki…)

When Gemini rewrites a full note, it can emit a structured `<APPLY_NOTE>` block. Chat shows the proposed fields and enables **Edit → Apply to Anki…** to:

- **Update** an existing note — prefers notes imported into the chat session; you can also pick from the **collection** (compatible note types) or from the current **Browser** selection
- **Create** a new note — opens Anki’s Add window with note type / fields (and deck/tags when present) prefilled; you still press Add
- **Preview** before/after as formatted fields (MathJax)
- **Undo** the last successful update (dialog button or **Edit → Undo last note apply…**)
- **Duplicate warning** (Anki’s first-field + note type rule) before update — proceed/cancel, dismissible

Session history keeps recent proposals (configurable). Starting a **new conversation** clears apply history and undo. If an update target was deleted, the add-on falls back to opening Add. Reactivating the apply window refreshes targets from the current Browser selection.

### Settings (settings button)

- **API key**, models, thinking budgets, temperatures, timeouts
- **Shared or split system instructions** (optimize vs chat)
- **Dynamic rules** learned from chat
- **Prompt presets** — save/load/import/export instruction packs (optional models/temps/thinking); also from chat Edit menu
- **Settings guide** (info button) — help while you edit
- **Restore defaults** / **Restore warnings** — selective reset
- **Filterable model picker** with API refresh
- **English / Italian** interface
- **Light / dark** theme following Anki
- **Prompt caching** (Advanced) — Gemini explicit cache for large static prompts (system instructions, note context, templates); configurable TTL and segments
- **Cost tracking links** — under the API key and in the settings guide (info button); billing is on Google’s side, not in Anki

---

## Quick start

1. **Install** (see below) and restart Anki.
2. Open any note → click the **settings button** in the editor.
3. Paste your [Google AI Studio](https://aistudio.google.com/) API key → **Save and apply**.
4. Focus a field → **Gemini** (or `Ctrl+Shift+G`) to optimize.

> **Tools → Add-ons → Config** opens Anki’s raw JSON editor for this add-on. Prefer the **settings button** for the guided UI.

---

## Installation

### From GitHub

```bash
git clone https://github.com/Raffaelerrr/anki-gemini-integration.git
```

Or download a ZIP from the repository page.

Then:

1. Place the folder in your Anki add-ons directory:
   - **Windows:** `%APPDATA%\Anki2\addons21\`
   - **macOS:** `~/Library/Application Support/Anki2/addons21/`
   - **Linux:** `~/Anki/addons21/`
2. The folder name can be anything Anki accepts (e.g. `Anki_AI_Addon` or `anki-gemini-integration`).
3. Restart Anki.
4. Configure your API key in settings (settings button).

> **Not on AnkiWeb yet** — install from GitHub for now.

### API key

- Created at [Google AI Studio](https://aistudio.google.com/)
- Stored **locally** by Anki in `meta.json` (never committed — see `.gitignore`)
- Leave the key field **empty** when saving to keep the existing stored key
- **Restore defaults** leaves API key **unchecked** by default; clearing it shows a confirmation (dismissible)

---

## Configuration

Settings are saved in Anki’s local `meta.json`. Example schemas:

| File | Purpose |
|------|---------|
| `config.example.json` | Full settings schema |
| `meta.example.json` | Anki `{"config": …}` wrapper |
| `config_gemini.example.json` | Legacy format (auto-migrated) |

Use the **settings** dialog for normal setup; manual file copy is rarely needed.

### Main options

| Option | Default | Description |
|--------|---------|-------------|
| `language` | `en` | Interface language (`en` or `it`) |
| `model_optimize` | `gemini-2.5-flash-lite` | Model for field optimization |
| `model_chat` | `gemini-2.5-flash` | Model for chat / brain icon analysis |
| `thinking_budget_optimize` | `0` | Thinking tokens for optimize (`0` = off) |
| `thinking_budget_chat` | `-1` | Thinking tokens for chat (`-1` = dynamic) |
| `chat_streaming` | `true` | Stream chat replies |
| `temperature_optimize` | `0.1` | Creativity for optimization |
| `temperature_chat` | `0.2` | Creativity for chat |
| `timeout_seconds` | `30` | API timeout |
| `max_retries` | `2` | Retries on transient errors |
| `max_history_turns` | `10` | Chat history length (one turn = your message + Gemini reply) |
| `confirm_before_apply` | `true` | Preview before applying optimization |
| `system_instruction_shared` | `true` | One instruction set for optimize + chat |
| `system_instruction` | *(built-in)* | Shared static instructions (when shared) |
| `system_instruction_optimize` | *(built-in)* | Optimize-only instructions (when split) |
| `system_instruction_chat` | *(built-in)* | Chat-only instructions (when split) |
| `dynamic_instructions` | `""` | Lower-priority rules from chat |
| `brain_import_message` | *(built-in)* | Prompt for brain icon note import |
| `prompt_cache_enabled_chat` | `false` | Use Gemini explicit prompt caching for chat (configure in chat → cache button) |
| `prompt_cache_enabled_optimize` | `false` | Use Gemini explicit prompt caching for optimize |
| `prompt_cache_ttl_seconds_chat` / `_optimize` | `3600` | Cache lifetime per purpose (seconds) |
| `prompt_cache_min_chars_chat` / `_optimize` | `8192` | Minimum cached characters before creating a cache |
| `prompt_cache_custom_text_chat` / `_optimize` | `""` | Optional extra reference text to cache |
| `prompt_cache_segments_chat` / `_optimize` | *(see example)* | Which prompt parts to include in the cache |
| `chat_payload_warning_chars` | `12000` | Warn before chat send when total input characters exceed this |
| `chat_apply_history_max` | `7` | How many APPLY_NOTE proposals to keep in the chat session (1–30) |
| `settings_presets` / `active_settings_preset_id` | `[]` / `""` | Named prompt presets and which one is active |
| `brain_import_templates` / `brain_import_css` | `false` | Include card templates / note-type CSS when importing |
| `chat_export_quick_folders` | `[]` | Quick folders for chat transcript download |
| `chat_modify_prompt_before_send` | `false` | Default pre-send review toggle for chat |
| `dev_mock_mode` | `false` | Dev playground mock (no real Gemini billing) |

Enable prompt caching separately for **chat** and **optimize**. **Chat** caching is configured from the cache button in the chat window; **optimize** caching and preset libraries live under **Settings → Advanced prompts**. Cached content is billed at Gemini’s cached-input rate for the TTL; changing cached text or model invalidates the tracked cache and prompts you to confirm before recreating (with character count and a link to AI Studio Billing).

**Prompt presets** (Settings → Prompt presets, or chat Edit → Prompt presets) store instruction/wrapper packs; optionally include models, temperatures, and thinking budgets. Import/export uses JSON schema v2. See the in-app settings guide topic **Prompt presets…**.

Use **Manage caches…** in Advanced settings to list remote `anki-ai-*` caches, see which are tracked locally, delete individual caches, or remove orphaned ones. Tracked cache names persist in `prompt_cache_state.json` across Anki restarts; orphans are cleaned up automatically on the next cached request.

Built-in system instructions include Anki HTML/MathJax rules and **convert plain math to MathJax** (`\(...\)` / `\[...\]`, no `$`/`$$`).

Legacy single `model` / `thinking_budget` keys migrate automatically.

---

## Shortcuts

| Action | Windows / Linux | macOS |
|--------|-----------------|-------|
| Optimize field | `Ctrl+Shift+G` | `Cmd+Shift+G` |
| Open / focus chat | `Ctrl+Alt+C` | `Cmd+Alt+C` |

---

## Development

Git ignores secrets and generated files (`meta.json`, `config_gemini.json`, `__pycache__/`, etc.).

`vendor/` bundles [Python-Markdown](https://python-markdown.github.io/) 3.10.2 for chat formatting.

### Dev playground (no billing)

**Tools → Anki AI: Dev playground** enables **dev mock mode**: fake Gemini replies (with streaming and a sample `<APPLY_NOTE>` block), in-memory prompt caches, and model list refresh — no API key required. The playground can open chat or settings. See [TESTING.md](TESTING.md) §5.

### Run offline tests

```bash
py -3 tests/test_offline.py
```

See **[TESTING.md](TESTING.md)** for CI, live API tests, and how to keep secrets safe.

Optional live API check (real key, before releases):

```bash
py -3 tests/test_live_api.py
```

### Update vendored Markdown

```bash
py -m pip install markdown --target vendor --upgrade
```

Remove old `*.dist-info` folders if duplicates appear after upgrading.

---

## Privacy & cost

Note field content and chat messages are sent to **Google’s Gemini API** using **your** API key. Review [Google’s terms](https://ai.google.dev/gemini-api/terms). API usage may incur charges depending on your Google account and billing setup.

### Tracking API costs

**This add-on does not show dollar amounts.** Billing is handled entirely by Google. To see what you are spending:

| Where | What you see |
|--------|----------------|
| [Google AI Studio → Billing](https://aistudio.google.com/billing) | Prepay credit balance, daily cost by project/model, spend caps |
| [Google AI Studio → Usage](https://aistudio.google.com/usage) | Requests per minute/day, tokens, progress toward rate limits |
| [Gemini API billing docs](https://ai.google.dev/gemini-api/docs/billing) | Prepay vs postpay, tier caps, billing delays |

**In the add-on:** open **Settings** (settings button) — links appear under the API key field. Open the **settings guide** (info button) → **Track API costs…** for a full explanation. In **Advanced prompts**, prompt caching also links to Billing for official costs; before recreating a stale cache the add-on shows cached **character count** (not dollar amounts).

**Free tier:** no billing account linked → quota limits apply, no charges.

**Paid tier:** prepay accounts see credit drawdown within minutes; cost charts may lag up to ~24 hours. Set monthly **spend caps** per project in AI Studio if you want hard limits.

### Add-on payload sizes

The add-on does **not** show Gemini token counts or dollar amounts. Where helpful it uses exact **character counts** (`len(text)`):

| What | Function | Notes |
|------|----------|-------|
| Chat send warning | `estimate_chat_request_chars()` | Sum of system + history + outgoing message |
| Cache status / recreate confirm | `cached_char_count` on cache bundle | Characters of cached text |
| Cache minimum threshold | `prompt_cache_min_chars` | Character count; ~4 chars/token aligns with Gemini ~2048-token minimum |

In Anki: **Settings guide** (info button) → **Add-on payload sizes…** for the full explanation.

---

## License

[MIT License](LICENSE) — see [LICENSE](LICENSE) for full text.
