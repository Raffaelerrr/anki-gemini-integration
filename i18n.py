from __future__ import annotations

from typing import Any

from .constants import DEFAULT_BRAIN_IMPORT_MESSAGE

LANG_IT = "it"
LANG_EN = "en"
SUPPORTED_LANGUAGES = (LANG_IT, LANG_EN)
DEFAULT_LANGUAGE = LANG_IT

_STRINGS: dict[str, dict[str, str]] = {
    # Editor buttons & menu
    "editor.tip.optimize": {
        "it": "Ottimizza questo campo con Gemini (Ctrl+Shift+G)",
        "en": "Optimize this field with Gemini (Ctrl+Shift+G)",
    },
    "editor.tip.undo": {
        "it": "Annulla l'ultima ottimizzazione Gemini su questa nota",
        "en": "Undo the last Gemini optimization on this note",
    },
    "editor.tip.analyze_note": {
        "it": "Importa TUTTI i campi della nota in chat per analizzarla",
        "en": "Import ALL note fields into chat for analysis",
    },
    "editor.tip.chat": {
        "it": "Apri o porta in primo piano la Chat con Gemini (Ctrl+Alt+C)",
        "en": "Open or focus the Gemini chat (Ctrl+Alt+C)",
    },
    "editor.tip.settings": {
        "it": "Modifica al volo le istruzioni o l'API Key",
        "en": "Edit instructions or API key on the fly",
    },
    "menu.tools.chat": {
        "it": "Chat con Gemini",
        "en": "Gemini chat",
    },
    # Settings dialog
    "settings.title": {
        "it": "Impostazioni Avanzate Gemini",
        "en": "Gemini advanced settings",
    },
    "settings.language": {
        "it": "Lingua interfaccia:",
        "en": "Interface language:",
    },
    "settings.language.it": {
        "it": "Italiano",
        "en": "Italian",
    },
    "settings.language.en": {
        "it": "English",
        "en": "English",
    },
    "settings.api_key": {
        "it": "Chiave API Google AI Studio:",
        "en": "Google AI Studio API key:",
    },
    "settings.api_key.saved": {
        "it": "Chiave salvata. Lascia il campo vuoto per mantenerla, oppure incolla una nuova chiave.",
        "en": "Key saved. Leave the field empty to keep it, or paste a new key.",
    },
    "settings.api_key.missing": {
        "it": "Nessuna chiave salvata. Incolla la chiave da aistudio.google.com.",
        "en": "No key saved. Paste your key from aistudio.google.com.",
    },
    "settings.api_key.placeholder.saved": {
        "it": "••••••••  (chiave già salvata)",
        "en": "••••••••  (key already saved)",
    },
    "settings.api_key.placeholder.empty": {
        "it": "Incolla la chiave da aistudio.google.com",
        "en": "Paste your key from aistudio.google.com",
    },
    "settings.model": {
        "it": "Modello Gemini:",
        "en": "Gemini model:",
    },
    "settings.model.placeholder": {
        "it": "es. gemini-2.5-flash",
        "en": "e.g. gemini-2.5-flash",
    },
    "settings.timeout": {
        "it": "Timeout (s):",
        "en": "Timeout (s):",
    },
    "settings.max_retry": {
        "it": "Max retry:",
        "en": "Max retries:",
    },
    "settings.chat_history": {
        "it": "Storico chat (turni):",
        "en": "Chat history (turns):",
    },
    "settings.temp_optimize": {
        "it": "Temperatura ottimizzazione:",
        "en": "Optimization temperature:",
    },
    "settings.temp_chat": {
        "it": "Temperatura chat:",
        "en": "Chat temperature:",
    },
    "settings.confirm_preview": {
        "it": "Mostra anteprima prima di applicare l'ottimizzazione del campo",
        "en": "Show preview before applying field optimization",
    },
    "settings.brain_message": {
        "it": "Messaggio predefinito importazione nota (🧠):",
        "en": "Default note import message (🧠):",
    },
    "settings.brain_message.hint": {
        "it": "Testo inserito automaticamente nella chat quando importi una nota con il bottone 🧠.",
        "en": "Text inserted automatically in chat when you import a note with the 🧠 button.",
    },
    "settings.system_instruction": {
        "it": "System Instruction Globali (Alta Priorità - Statiche):",
        "en": "Global system instructions (high priority — static):",
    },
    "settings.dynamic_instructions": {
        "it": "Direttive Dinamiche Apprese (Bassa Priorità - Aggiornabili via Chat):",
        "en": "Learned dynamic directives (low priority — updatable via chat):",
    },
    "settings.dynamic_placeholder": {
        "it": "Le regole che dirai a Gemini di ricordare nella chat appariranno qui automaticamente...",
        "en": "Rules you ask Gemini to remember in chat will appear here automatically...",
    },
    "settings.shortcuts": {
        "it": "Scorciatoie da Tastiera:",
        "en": "Keyboard shortcuts:",
    },
    "settings.shortcuts.body": {
        "it": (
            "• <b>Ctrl + Shift + G</b> : Ottimizza il campo attivo nell'Editor.<br>"
            "• <b>Ctrl + Alt + C</b> : Apri / Porta in primo piano la Chat con Gemini."
        ),
        "en": (
            "• <b>Ctrl + Shift + G</b> : Optimize the active field in the editor.<br>"
            "• <b>Ctrl + Alt + C</b> : Open / focus the Gemini chat."
        ),
    },
    "settings.save": {
        "it": "Salva ed Applica",
        "en": "Save and apply",
    },
    "settings.cancel": {
        "it": "Annulla",
        "en": "Cancel",
    },
    # Optimize
    "optimize.no_undo": {
        "it": "Nessuna ottimizzazione recente da annullare in questa sessione.",
        "en": "No recent optimization to undo in this session.",
    },
    "optimize.undo_done": {
        "it": "Ottimizzazione annullata.",
        "en": "Optimization undone.",
    },
    "optimize.applied": {
        "it": "Campo ottimizzato con Gemini.",
        "en": "Field optimized with Gemini.",
    },
    "optimize.cancelled": {
        "it": "Ottimizzazione annullata.",
        "en": "Optimization cancelled.",
    },
    "optimize.error": {
        "it": "Errore durante l'ottimizzazione con Gemini:\n{error}",
        "en": "Error while optimizing with Gemini:\n{error}",
    },
    "optimize.click_field": {
        "it": "Per favore, fai clic dentro un campo di testo prima di usare Gemini.",
        "en": "Please click inside a text field before using Gemini.",
    },
    "optimize.field_empty": {
        "it": "Il campo attivo è vuoto!",
        "en": "The active field is empty!",
    },
    "optimize.api_key_missing": {
        "it": "Errore: API Key mancante. Impostala con il bottone ⚙️.",
        "en": "Error: API key missing. Set it with the ⚙️ button.",
    },
    "optimize.in_progress": {
        "it": "Ottimizzazione in corso…",
        "en": "Optimization in progress…",
    },
    # Preview dialog
    "preview.title": {
        "it": "Anteprima ottimizzazione Gemini",
        "en": "Gemini optimization preview",
    },
    "preview.intro": {
        "it": (
            "<b>Confronta il contenuto originale con la versione ottimizzata.</b> "
            "Clicca <i>Applica</i> per sostituire il campo, oppure <i>Annulla</i> per mantenere l'originale."
        ),
        "en": (
            "<b>Compare the original content with the optimized version.</b> "
            "Click <i>Apply</i> to replace the field, or <i>Cancel</i> to keep the original."
        ),
    },
    "preview.original": {
        "it": "Originale",
        "en": "Original",
    },
    "preview.optimized": {
        "it": "Ottimizzato",
        "en": "Optimized",
    },
    "preview.apply": {
        "it": "Applica",
        "en": "Apply",
    },
    "preview.cancel": {
        "it": "Annulla",
        "en": "Cancel",
    },
    # Chat
    "chat.title": {
        "it": "Chat con Gemini",
        "en": "Gemini chat",
    },
    "chat.include_context": {
        "it": "Includi contesto nota nel prossimo messaggio",
        "en": "Include note context in the next message",
    },
    "chat.new_conversation": {
        "it": "Nuova conversazione",
        "en": "New conversation",
    },
    "chat.log_placeholder": {
        "it": "La conversazione apparirà qui...",
        "en": "The conversation will appear here...",
    },
    "chat.input_placeholder": {
        "it": (
            "Chiedi a Gemini o digiti: 'Memorizza globalmente la regola X'...\n"
            "(Invio per inviare, Shift+Invio per andare a capo)"
        ),
        "en": (
            "Ask Gemini or type: 'Remember globally the rule X'...\n"
            "(Enter to send, Shift+Enter for a new line)"
        ),
    },
    "chat.send": {
        "it": "Invia",
        "en": "Send",
    },
    "chat.welcome": {
        "it": "Ciao! Puoi chiedermi spiegazioni o dirmi di memorizzare nuove direttive di stile.",
        "en": "Hi! You can ask for explanations or tell me to remember new style directives.",
    },
    "chat.cleared": {
        "it": "Conversazione azzerata. Puoi iniziare una nuova chat.",
        "en": "Conversation cleared. You can start a new chat.",
    },
    "chat.note_empty": {
        "it": "La nota corrente è completamente vuota.",
        "en": "The current note is completely empty.",
    },
    "chat.note_imported": {
        "it": "Contenuto della nota importato con successo!",
        "en": "Note content imported successfully!",
    },
    "chat.api_key_missing": {
        "it": "Errore: API Key mancante (⚙️).",
        "en": "Error: API key missing (⚙️).",
    },
    "chat.rules_updated": {
        "it": "Memoria dinamica dell'add-on aggiornata e salvata!",
        "en": "Add-on dynamic memory updated and saved!",
    },
    "chat.error": {
        "it": "Errore: {error}",
        "en": "Error: {error}",
    },
    "chat.unexpected_error": {
        "it": "Errore imprevisto: {error}",
        "en": "Unexpected error: {error}",
    },
    "chat.loading": {
        "it": "🤖 Gemini sta scrivendo.",
        "en": "🤖 Gemini is typing.",
    },
    "chat.copied": {
        "it": "Contenuto del campo copiato negli appunti.",
        "en": "Field content copied to clipboard.",
    },
    "chat.label.you": {
        "it": "Tu",
        "en": "You",
    },
    "chat.label.gemini": {
        "it": "Gemini",
        "en": "Gemini",
    },
    "chat.label.system": {
        "it": "Sistema",
        "en": "System",
    },
    "chat.context.field": {
        "it": "Campo [{name}]:",
        "en": "Field [{name}]:",
    },
    "chat.context.prefix": {
        "it": "[CONTESTO DELLA NOTA INTERA DA ANALIZZARE]:\n{context}\n\n[RICHIESTA DELLO STUDENTE]:\n{request}",
        "en": "[FULL NOTE CONTEXT TO ANALYZE]:\n{context}\n\n[STUDENT REQUEST]:\n{request}",
    },
    "defaults.brain_import_message": {
        "it": "La nota qui sopra andrebbe scomposta in più note secondo il principio di atomicità? Se sì, come?",
        "en": "Should the note above be split into multiple notes following the atomicity principle? If so, how?",
    },
    # Chat formatter
    "formatter.copy": {
        "it": "Copia",
        "en": "Copy",
    },
    "formatter.code_block": {
        "it": "Blocco code",
        "en": "Code block",
    },
    # Gemini API errors
    "gemini.blocked": {
        "it": "Richiesta bloccata da Gemini: {reason}",
        "en": "Request blocked by Gemini: {reason}",
    },
    "gemini.no_candidates": {
        "it": "Gemini non ha restituito candidati nella risposta.",
        "en": "Gemini returned no candidates in the response.",
    },
    "gemini.interrupted": {
        "it": "Generazione interrotta: {reason}",
        "en": "Generation interrupted: {reason}",
    },
    "gemini.empty_response": {
        "it": "Risposta vuota da Gemini.",
        "en": "Empty response from Gemini.",
    },
    "gemini.no_text": {
        "it": "Nessun testo nella risposta di Gemini.",
        "en": "No text in Gemini's response.",
    },
    "gemini.auth_error": {
        "it": "API Key non valida o non autorizzata. Controlla la chiave nelle impostazioni (⚙️).",
        "en": "Invalid or unauthorized API key. Check the key in settings (⚙️).",
    },
    "gemini.rate_limit": {
        "it": "Limite di richieste raggiunto. Riprova tra qualche secondo.",
        "en": "Rate limit reached. Try again in a few seconds.",
    },
    "gemini.http_error": {
        "it": "Errore HTTP {status}: {detail}",
        "en": "HTTP error {status}: {detail}",
    },
    "gemini.network_error": {
        "it": "Errore di rete o timeout: {error}",
        "en": "Network error or timeout: {error}",
    },
    "gemini.unknown_error": {
        "it": "Errore sconosciuto durante la chiamata a Gemini.",
        "en": "Unknown error while calling Gemini.",
    },
}


def normalize_language(language: str | None) -> str:
    if language and str(language).lower().startswith(LANG_EN):
        return LANG_EN
    return LANG_IT


def get_language(config: dict[str, Any] | None = None) -> str:
    if config is None:
        from .config import load_config

        config = load_config()
    return normalize_language(config.get("language"))


def tr(key: str, *, config: dict[str, Any] | None = None, lang: str | None = None, **kwargs: Any) -> str:
    language = lang or get_language(config)
    entry = _STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(language) or entry.get(DEFAULT_LANGUAGE) or key
    if kwargs:
        return text.format(**kwargs)
    return text


def default_brain_import_message(config: dict[str, Any] | None = None) -> str:
    return tr("defaults.brain_import_message", config=config)


def _builtin_brain_import_messages() -> frozenset[str]:
    return frozenset(
        message.strip()
        for message in (
            DEFAULT_BRAIN_IMPORT_MESSAGE,
            _STRINGS["defaults.brain_import_message"][LANG_IT],
            _STRINGS["defaults.brain_import_message"][LANG_EN],
        )
        if message.strip()
    )


def is_builtin_brain_import_message(text: str | None) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    return stripped in _builtin_brain_import_messages()


def effective_brain_import_message(config: dict[str, Any] | None = None) -> str:
    stored = ((config or {}).get("brain_import_message") or "").strip()
    if is_builtin_brain_import_message(stored):
        return default_brain_import_message(config)
    return stored


def normalize_brain_import_message_for_save(text: str, config: dict[str, Any]) -> str:
    stripped = (text or "").strip()
    if is_builtin_brain_import_message(stripped):
        return ""
    return stripped
