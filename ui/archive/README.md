# Archived styled UI (mode A)

This folder preserves the **styled** UI path (focus stripe frames, custom-painted
spinboxes/combos, lavender context panel with purple accent bar).

The addon uses **native Qt controls (mode B)** only. These files are kept for
reference or recovery; nothing here is imported at runtime.

To inspect the old implementation:

- `styled_widgets.py` — frame + stripe wrappers, styled control factories
- `styled_theme_full.py` — full theme module snapshot before native-only refactor

Do not import from this package in production code.
