# Anki AI Assistant (Gemini)

An Anki add-on that integrates **Google Gemini** into the note editor: optimize HTML/MathJax fields, chat about your notes, and analyze whether a note should be split for atomicity.

**Repository:** [github.com/Raffaelerrr/anki-gemini-integration](https://github.com/Raffaelerrr/anki-gemini-integration)  
**Version:** 2.0.0  
**Author:** Raffaele  
**Requires:** Anki 2.1.49+ (point version 49)  
**License:** [MIT](LICENSE)

> **Disclaimer:** This add-on was developed with substantial assistance from AI coding tools (including Cursor and large language models). The author reviewed and tested the project, but errors or unexpected behavior may remain. Use at your own discretion.

---

## Features

### Field optimization (`Gemini` button · `Ctrl+Shift+G`)

Optimizes the **currently focused field** using your system instructions (HTML structure, MathJax notation, custom macros, etc.). Uses a dedicated model and thinking-budget settings tuned for fast, precise edits. Optionally shows a preview before applying changes.

### Undo (`↩` button)

Reverts the last optimization on the current note in this session.

### Note analysis (`🧠` button)

Imports **all fields** of the current note into the chat and asks Gemini whether the note should be decomposed into smaller atomic cards.

### Chat (`💬` button · `Ctrl+Alt+C`)

Opens a chat window with Gemini. Replies are formatted with Markdown; when Gemini suggests content for Anki fields, copy buttons are provided. Streaming replies are supported (text appears as it arrives). Also available from **Tools → Chat con Gemini** / **Tools → Chat with Gemini**.

### Settings (`⚙️` button)

Configure your API key, models, thinking budgets, temperatures, timeouts, system instructions, dynamic rules, interface language, and more. Includes:

- **Settings guide** — scrollable help with per-setting explanations (open while editing settings)
- **Restore defaults** — reset selected settings with checkboxes and “check/uncheck all”
- **Model picker** — filterable dropdowns with optional refresh from the Gemini API
- **Light/dark theme support** — UI adapts when Anki’s theme changes

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
4. Open the add-on settings (⚙️ in the editor, or **Tools → Add-ons → Anki AI Assistant → Config**) and paste your API key.

### API key

1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Create an API key.
3. Paste it in the add-on settings (⚙️). The key is stored locally by Anki in `meta.json` and is **not** committed to this repository.

---

## Configuration

Settings are saved by Anki in `meta.json` (local only). For reference, see the example files in the repo:

| File | Purpose |
|------|---------|
| `config.example.json` | Full settings schema |
| `meta.example.json` | Same settings in Anki’s `{"config": …}` format |
| `config_gemini.example.json` | Legacy config format (migration only) |

You normally configure everything through the in-editor **⚙️** dialog; copying these files manually is rarely needed.

### Main options

| Option | Default | Description |
|--------|---------|-------------|
| `language` | `it` | Interface language (`it` or `en`) |
| `model_optimize` | `gemini-2.5-flash-lite` | Gemini model for field optimization |
| `model_chat` | `gemini-2.5-flash` | Gemini model for chat |
| `thinking_budget_optimize` | `0` | Thinking tokens for optimization (`0` = off; faster) |
| `thinking_budget_chat` | `-1` | Thinking tokens for chat (`-1` = dynamic) |
| `chat_streaming` | `true` | Stream chat replies as they arrive |
| `temperature_optimize` | `0.1` | Creativity for field optimization |
| `temperature_chat` | `0.2` | Creativity for chat |
| `timeout_seconds` | `30` | API request timeout |
| `max_retries` | `2` | Retries on transient failures |
| `max_history_turns` | `20` | Chat history length (user + assistant pairs) |
| `confirm_before_apply` | `true` | Show preview before applying optimization |
| `system_instruction` | *(built-in)* | High-priority static rules for optimization (HTML, MathJax, macros) |
| `dynamic_instructions` | `""` | Lower-priority rules learned or updated during chat |
| `brain_import_message` | *(built-in)* | Prompt used when importing a note for analysis |

Legacy installs with a single `model` or `thinking_budget` key are migrated automatically on load.

---

## Editor shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+G` | Optimize current field |
| `Ctrl+Alt+C` | Open / focus chat |

---

## Development

This repo uses Git. Local secrets and generated files are excluded via `.gitignore`:

- `config.json`, `meta.json` — contain your API key and personal settings
- `__pycache__/`, editor files, scratch notes

The `vendor/` folder bundles the [Python-Markdown](https://python-markdown.github.io/) library so the chat formatter works without extra dependencies.

### Run offline tests

From the add-on directory:

```bash
py -3 tests/test_offline.py
```

### Update vendored Markdown

```bash
py -m pip install markdown --target vendor --upgrade
```

Remove old `*.dist-info` folders if duplicates appear after upgrading.

---

## Privacy

When you use this add-on, note field content and chat messages are sent to **Google’s Gemini API** using your API key. Review [Google’s terms and privacy policy](https://ai.google.dev/gemini-api/terms) before use.

---

## License

This project is licensed under the [MIT License](LICENSE).

You may use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the software, as long as you include the copyright notice and license text. The software is provided **“as is”**, without warranty of any kind.

Other common permissive options (not used here):

| License | In short |
|---------|----------|
| **MIT** *(this repo)* | Do almost anything; keep the license notice. Simple and very common. |
| **Apache 2.0** | Like MIT, plus an explicit patent grant. Slightly longer text. |
| **BSD 2/3-Clause** | Very similar to MIT. |
| **Unlicense / CC0** | Public domain–style; no attribution required. |

Copyleft licenses such as **GPL** require derivative works to stay open source under the same license — stricter than what most people mean by “do whatever you want.”
