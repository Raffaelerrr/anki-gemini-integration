from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

ADDON_DIR = Path(__file__).resolve().parent
VENDOR_DIR = ADDON_DIR / "vendor"
MIN_MARKDOWN_VERSION = (3, 0)

_md_converter: Any | None = None
_load_attempted = False
_using_fallback = False


def _parse_version(version_str: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in (version_str or "").split("."):
        if not piece.isdigit():
            break
        parts.append(int(piece))
    return tuple(parts) if parts else (0,)


def _version_ok(version_str: str) -> bool:
    return _parse_version(version_str) >= MIN_MARKDOWN_VERSION


def _module_from_vendor(module: Any) -> bool:
    module_file = getattr(module, "__file__", "") or ""
    if not module_file:
        return False
    vendor_path = str(VENDOR_DIR).replace("\\", "/").lower()
    return vendor_path in module_file.replace("\\", "/").lower()


def _load_markdown_module() -> Any | None:
    if not VENDOR_DIR.is_dir():
        print("[Anki AI Add-on] Cartella vendor/ non trovata; Markdown chat in modalità semplificata.")
        return None

    if VENDOR_DIR not in sys.path:
        sys.path.insert(0, str(VENDOR_DIR))

    try:
        existing = sys.modules.get("markdown")
        if existing is not None:
            version = getattr(existing, "__version__", "0")
            if _module_from_vendor(existing):
                return existing
            if _version_ok(version):
                print(
                    f"[Anki AI Add-on] Uso markdown {version} già caricato da un altro add-on."
                )
                return existing
            print(
                f"[Anki AI Add-on] markdown {version} in memoria non compatibile; "
                "provo la copia in vendor/."
            )
            sys.modules.pop("markdown", None)
            for key in list(sys.modules):
                if key == "markdown" or key.startswith("markdown."):
                    sys.modules.pop(key, None)

        return importlib.import_module("markdown")
    except ImportError as exc:
        print(f"[Anki AI Add-on] Import markdown da vendor/ fallito: {exc}")
        existing = sys.modules.get("markdown")
        if existing is not None and _version_ok(getattr(existing, "__version__", "0")):
            return existing
        return None


def get_markdown_converter() -> Any | None:
    global _md_converter, _load_attempted, _using_fallback

    if _load_attempted:
        return _md_converter

    _load_attempted = True
    module = _load_markdown_module()
    if module is None:
        _using_fallback = True
        return None

    version = getattr(module, "__version__", "sconosciuta")
    source = "vendor/" if _module_from_vendor(module) else "add-on esterno"
    print(f"[Anki AI Add-on] Markdown chat attivo ({version}, origine: {source}).")

    try:
        _md_converter = module.Markdown(
            extensions=["extra", "nl2br", "sane_lists"],
            output_format="html5",
        )
    except Exception as exc:
        print(f"[Anki AI Add-on] Inizializzazione markdown fallita: {exc}")
        _md_converter = None
        _using_fallback = True

    return _md_converter


def using_markdown_fallback() -> bool:
    get_markdown_converter()
    return _using_fallback
