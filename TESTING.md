# Testing

This add-on uses three layers of tests. Run them at different times depending on what you changed.

## Quick reference

| When | Command | What it checks |
|------|---------|----------------|
| After most code changes | `py tests/test_offline.py` | Logic, config, API payloads, mocks (no Anki, no network) |
| On every push to GitHub | CI runs the same offline suite automatically | Same as above |
| Before a release / Reddit post | `py tests/test_live_api.py` | Real calls to Google Gemini (4 checks when keyed) |
| After UI changes | Manual checklist in Anki | Buttons, scroll, theme (see README) |

---

## 1. Offline tests (run often)

From the add-on folder:

```powershell
cd "$env:APPDATA\Anki2\addons21\Anki_AI_Addon"
py tests/test_offline.py
```

Or from anywhere:

```powershell
py -3 "$env:APPDATA\Anki2\addons21\Anki_AI_Addon\tests\test_offline.py"
```

**No API key required.** These tests mock Anki and the network.

**Run after changing:** `gemini_client.py`, `config.py`, `i18n.py`, `ui/optimize.py`, `ui/settings_dialog.py`, chat formatting, model selector, etc.

---

## 2. CI (Continuous Integration)

**CI** = GitHub automatically runs your test scripts when you push or open a pull request.

Workflow file: `.github/workflows/test.yml`

On each push/PR, CI runs **two commands**:

| Command | What happens in CI |
|---------|-------------------|
| `python tests/test_offline.py` | All tests **run** (real assertions, must pass) |
| `python tests/test_live_api.py` | Script **runs**, but live tests are **skipped** (no API key → no call to Google) |

So: CI **executes** the live test file, but it does **not** hit Gemini. That only happens on your machine when you set `GEMINI_API_KEY` or `.env.local`.

We intentionally do **not** put your API key in GitHub Actions, so CI never makes paid/network live calls.

Check the **Actions** tab on the repository for green ✅ or red ❌. A green run means offline tests passed and live tests were skipped as expected.

---

## 3. Live API tests (optional, before releases)

These make **real** requests to Google using **your** API key.

### Set up your key (choose one method)

**Method A — environment variable (session only)**

```powershell
$env:GEMINI_API_KEY = "your-google-ai-studio-key"
py tests/test_live_api.py
```

**Method B — `.env.local` file (persists on your machine)**

```powershell
Copy-Item .env.example .env.local
# Edit .env.local and paste your key after GEMINI_API_KEY=
py tests/test_live_api.py
```

### Protecting secrets

| File | Commit to Git? | Purpose |
|------|----------------|---------|
| `.env.example` | ✅ Yes | Template with empty key |
| `.env.local` | ❌ Never | Your real key (gitignored) |
| `meta.json` | ❌ Never | Anki’s stored settings (gitignored) |
| `config_gemini.json` | ❌ Never | Legacy local config (gitignored) |

**Rules:**

1. **Never** commit `.env.local`, `meta.json`, or paste API keys into issues, Reddit, or chat.
2. `.env.local` is listed in `.gitignore` — verify with `git status` before committing.
3. If you accidentally commit a key: revoke it in [Google AI Studio](https://aistudio.google.com/), create a new one, and remove the key from git history.
4. Do **not** add `GEMINI_API_KEY` to GitHub Actions unless you explicitly want paid live tests in CI (not recommended for this project).

### Run live tests

```powershell
py tests/test_live_api.py
```

Without a key, tests are **skipped** (exit code 0) — that is expected in CI.

With a key, the suite runs four checks: optimize call, model list, streaming chat, and prompt-cache create/use/clear (short TTL; remote cache is deleted in teardown).

**Cost note:** the cache test uploads ~8K characters once per run (~0.03¢ on paid tier at typical rates). The other three live tests together are much cheaper (~0.005¢).

**Run before:** tagging a release, posting on Reddit, or after changing API URLs, auth headers, model resolution, or prompt-cache HTTP helpers.

---

## 4. Manual Anki smoke tests

Automated tests cannot click editor buttons or verify scroll behavior. After UI work, run this checklist in Anki.

### Global

- [ ] Switch Anki **light/dark** theme — chat, settings, pre-send lens, optimize preview, dev playground, and prompt-cache manager stay readable.
- [ ] Switch add-on language **EN ↔ IT** — menu labels, settings, chat toolbar, and open dialogs update without restart.

### Optimize

- [ ] Editor **optimize** button — preview dialog opens; Apply writes the field; Undo restores.
- [ ] Settings → **Inspect optimize prompt** — window opens; Refresh updates content; theme/language changes apply while open.

### Chat

- [ ] Open chat from editor or **Tools → Gemini chat**.
- [ ] **Brain icon** — imported fields appear in preview; send with **Include note context** checked.
- [ ] **Lens / inspect prompt** — pre-send or read-only preview opens; cached vs live views switch when cache is active.
- [ ] **Modify prompt before send** (if enabled) — pre-send dialog blocks send until confirmed.
- [ ] Eye icon — hides/shows preview without losing edits.
- [ ] **Edit wrapper** — invalid placeholders show a warning; session template persists when unchecked.

### Settings

- [ ] Save settings — values persist after reopening the dialog.
- [ ] **Restore defaults** on a single field — only that field resets.
- [ ] **Prompt cache manager** — lists remote caches when API key is set; delete/orphan actions work.
- [ ] Settings help (?) icons — tooltips readable in both themes.

### Dev playground

- [ ] **Tools → Anki AI: Dev playground** — mock replies without billing; **Open chat** / **Open settings**; **Reset mock state** clears in-memory caches. Mock chat includes a sample `<APPLY_NOTE>` for Apply-to-Anki testing.
- [ ] Turn mock mode **off** before expecting real Gemini responses.

---

## 5. Dev playground (local UI testing, no billing)

**Tools → Anki AI: Dev playground** turns on **dev mock mode**. While active:

- Chat and optimize use fake replies (streaming included), including a sample `<APPLY_NOTE>` block for Apply-to-Anki smoke tests.
- Prompt caches are created in memory only — no Google HTTP calls.
- Model refresh returns the built-in model list.
- No API key is required.
- **Open chat** / **Open settings** shortcuts from the playground window.

Use this to exercise cache-created notices, recreate dialogs, chat import, optimize preview, Apply to Anki, etc. as often as you like.

Click **Reset mock state** to clear mock remote caches and local cache tracking without touching your real Google caches (when mock mode is off again).

Setting is stored in add-on config as `dev_mock_mode`. Turn it **off** before relying on real Gemini responses.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: support` | Run tests from the addon folder or use the full path shown above |
| Live tests always skipped | Set `GEMINI_API_KEY` or create `.env.local` |
| CI fails on GitHub | Run `py tests/test_offline.py` locally and fix failures |
| `git status` shows `.env.local` | Do not `git add` it — it should be ignored |
