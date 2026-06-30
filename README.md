# Anki AI Assistant (Gemini)

An Anki add-on that integrates **Google Gemini** into the note editor: optimize HTML/MathJax fields, chat about your notes, and analyze whether a note should be split for atomicity.

**Version:** 2.0.0  
**Author:** Raffaele  
**Requires:** Anki 2.1.49+ (point version 49)

---

## Features

### Field optimization (`Gemini` button · `Ctrl+Shift+G`)

Optimizes the **currently focused field** using your system instructions (HTML structure, MathJax notation, custom macros, etc.). Optionally shows a preview before applying changes.

### Undo (`↩` button)

Reverts the last optimization on the current note in this session.

### Note analysis (`🧠` button)

Imports **all fields** of the current note into the chat and asks Gemini whether the note should be decomposed into smaller atomic cards.

### Chat (`💬` button · `Ctrl+Alt+C`)

Opens a chat window with Gemini. Replies are formatted with Markdown; when Gemini suggests content for Anki fields, copy buttons are provided. Also available from **Tools → Chat con Gemini**.

### Settings (`⚙️` button)

Configure your API key, model, temperatures, timeouts, system instructions, dynamic rules, and other options.

---

## Installation

### From GitHub

1. Download or clone this repository.
2. Place the folder in your Anki add-ons directory:
   - **Windows:** `%APPDATA%\Anki2\addons21\`
   - **macOS:** `~/Library/Application Support/Anki2/addons21/`
   - **Linux:** `~/Anki/addons21/`
3. Rename the folder if needed (e.g. `Anki_AI_Addon`).
4. Restart Anki.
5. Open the add-on settings (⚙️ in the editor, or **Tools → Add-ons → Anki AI Assistant → Config**) and paste your API key.

### API key

1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Create an API key.
3. Paste it in the add-on settings (⚙️). The key is stored locally by Anki and is **not** committed to this repository.

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
| `model` | `gemini-2.5-flash` | Gemini model name |
| `temperature_optimize` | `0.1` | Creativity for field optimization |
| `temperature_chat` | `0.2` | Creativity for chat |
| `timeout_seconds` | `30` | API request timeout |
| `max_retries` | `2` | Retries on transient failures |
| `max_history_turns` | `20` | Chat history length (user + assistant pairs) |
| `confirm_before_apply` | `true` | Show preview before applying optimization |
| `system_instruction` | *(built-in)* | Rules for optimization (HTML, MathJax, macros) |
| `dynamic_instructions` | `""` | Extra rules learned during chat |
| `brain_import_message` | *(built-in)* | Prompt used when importing a note for analysis |

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

### Update vendored Markdown

From the add-on directory:

```bash
py -m pip install markdown --target vendor --upgrade
```

Remove old `*.dist-info` folders if duplicates appear after upgrading.

---

## Privacy

When you use this add-on, note field content and chat messages are sent to **Google’s Gemini API** using your API key. Review [Google’s terms and privacy policy](https://ai.google.dev/gemini-api/terms) before use.

---

## License

No license file is included yet. All rights reserved unless otherwise specified by the author.
