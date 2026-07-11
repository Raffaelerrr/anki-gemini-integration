from __future__ import annotations

import re
from typing import Any

from .chat_context_wrapper import (
    DEFAULT_WRAPPER_SECTION_ORDER,
    PLACEHOLDER_SECTIONS,
    WRAPPER_SECTION_IDS,
    apply_wrapper_placeholders,
    assemble_wrapper_message,
    format_chat_context_message as _format_chat_context_message_core,
    import_css_enabled,
    import_templates_enabled,
    normalize_wrapper_section_order,
    wrapper_content_tag,
    wrapper_missing_import_placeholders,
    wrapper_section_missing_placeholders,
    wrapper_sections_missing_required,
)

LANG_IT = "it"
LANG_EN = "en"
SUPPORTED_LANGUAGES = (LANG_IT, LANG_EN)
DEFAULT_LANGUAGE = LANG_EN

_ICON_PLACEHOLDER_RE = re.compile(r"\{icon:[^}]+\}")
_ICON_PLACEHOLDER_SENTINEL = "__ANKI_AI_ICON_{}__"


def _shield_icon_placeholders(text: str) -> tuple[str, list[str]]:
    icons: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        icons.append(match.group(0))
        return _ICON_PLACEHOLDER_SENTINEL.format(len(icons) - 1)

    return _ICON_PLACEHOLDER_RE.sub(_replace, text), icons


def _restore_icon_placeholders(text: str, icons: list[str]) -> str:
    for index, icon in enumerate(icons):
        text = text.replace(_ICON_PLACEHOLDER_SENTINEL.format(index), icon)
    return text

_STRINGS: dict[str, dict[str, str]] = {
    # Editor buttons & menu
    "editor.button.optimize": {
        "it": "Ottimizza",
        "en": "Optimize",
    },
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
    "menu.tools.dev_playground": {
        "it": "Anki AI: Dev playground",
        "en": "Anki AI: Dev playground",
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
    "settings.api_cost_tracking": {
        "it": (
            "Questo add-on non mostra importi in dollari. Monitora utilizzo e costi in "
            "<a href=\"{billing_url}\">AI Studio → Fatturazione</a> e "
            "<a href=\"{usage_url}\">AI Studio → Utilizzo</a> "
            "(saldo prepagato in pochi minuti; i grafici possono ritardare fino a 24 ore). "
            "Apri la <b>guida impostazioni (pulsante info)</b> → <b>Monitorare i costi API</b> o "
            "<b>Dimensioni payload nell'add-on</b> per i dettagli."
        ),
        "en": (
            "This add-on does not show dollar amounts. Track usage and spend in "
            "<a href=\"{billing_url}\">AI Studio → Billing</a> and "
            "<a href=\"{usage_url}\">AI Studio → Usage</a> "
            "(prepay balance updates within minutes; charts may lag up to 24 hours). "
            "Open the <b>settings guide (info button)</b> → <b>Track API costs</b> or "
            "<b>Add-on payload sizes</b> for details."
        ),
    },
    "settings.model_optimize": {
        "it": "Modello Gemini (ottimizzazione):",
        "en": "Gemini model (optimize):",
    },
    "settings.model_chat": {
        "it": "Modello Gemini (chat):",
        "en": "Gemini model (chat):",
    },
    "settings.model.placeholder": {
        "it": "Digita per filtrare o scegli un modello",
        "en": "Type to filter or choose a model",
    },
    "settings.model.refresh": {
        "it": "Aggiorna modelli da API",
        "en": "Refresh models from API",
    },
    "settings.model.refresh.no_key": {
        "it": "Inserisci una API Key prima di aggiornare l'elenco modelli.",
        "en": "Enter an API key before refreshing the model list.",
    },
    "settings.model.refresh.in_progress": {
        "it": "Aggiornamento elenco modelli…",
        "en": "Refreshing model list…",
    },
    "settings.model.refresh.done": {
        "it": "Elenco modelli aggiornato ({count} modelli con generateContent).",
        "en": "Model list updated ({count} models with generateContent).",
    },
    "settings.thinking_budget_optimize": {
        "it": "Thinking budget (ottimizzazione):",
        "en": "Thinking budget (optimize):",
    },
    "settings.thinking_budget_chat": {
        "it": "Thinking budget (chat):",
        "en": "Thinking budget (chat):",
    },
    "settings.thinking_budget.hint": {
        "it": "-1 = dinamico, 0 = più veloce (senza thinking), valori più alti = più ragionamento.",
        "en": "-1 = dynamic, 0 = fastest (no thinking), higher values = more reasoning.",
    },
    "settings.chat_streaming": {
        "it": "Streaming risposte in chat (mostra il testo man mano che arriva)",
        "en": "Stream chat replies (show text as it arrives)",
    },
    "settings.inspect_optimize_prompt": {
        "it": "Ispeziona prompt ottimizzazione",
        "en": "Inspect optimize prompt",
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
    "settings.show_text_newlines": {
        "it": "Mostra i ritorni a capo nelle caselle di testo",
        "en": "Show line breaks in text boxes",
    },
    "settings.show_text_newlines.hint": {
        "it": (
            "Mostra il simbolo ¶ a fine riga così puoi distinguere i a capo reali "
            "dall'avvolgimento automatico del testo."
        ),
        "en": (
            "Shows a ¶ marker at the end of each line so you can tell real line breaks "
            "from automatic word wrap."
        ),
    },
    "settings.brain_message": {
        "it": "Messaggio predefinito dopo import nota ({icon:brain}):",
        "en": "Default message after note import ({icon:brain}):",
    },
    "settings.brain_message.hint": {
        "it": (
            "Testo inserito nella casella chat quando clicchi {icon:brain} nell'editor "
            "(importa tutti i campi della nota in chat)."
        ),
        "en": (
            "Text placed in the chat input when you click {icon:brain} in the editor "
            "(imports all note fields into chat)."
        ),
    },
    "settings.brain_import_templates": {
        "it": "Includi template carte (chat)",
        "en": "Include card templates (chat)",
    },
    "settings.brain_import_css": {
        "it": "Includi CSS nota (chat)",
        "en": "Include note CSS (chat)",
    },
    "settings.chat_payload_warning_chars": {
        "it": "Avviso caratteri payload chat oltre",
        "en": "Chat payload warning above (characters)",
    },
    "settings.advanced": {
        "it": "Avanzate",
        "en": "Advanced",
    },
    "settings.advanced.title": {
        "it": "Impostazioni avanzate",
        "en": "Advanced settings",
    },
    "settings.advanced.hint": {
        "it": (
            "Testi extra, cache prompt e altre opzioni tecniche. Modifica solo se sai cosa stai facendo. "
            "Ripristina i valori predefiniti da Impostazioni → Ripristina predefiniti."
        ),
        "en": (
            "Extra prompt text, prompt caching, and other technical options. Edit only if you know what you are doing. "
            "Restore defaults from Settings → Restore defaults."
        ),
    },
    "settings.prompt_cache_enabled": {
        "it": "Abilita cache prompt (Gemini)",
        "en": "Enable prompt caching (Gemini)",
    },
    "settings.prompt_cache.hint": {
        "it": (
            "Memorizza su Gemini le parti del prompt che scegli, per un TTL impostato. "
            "Richiede abbastanza token (vedi soglia minima). Le modifiche al testo cached "
            "richiedono una nuova cache."
        ),
        "en": (
            "Store selected prompt parts on Gemini for a TTL you choose. "
            "Requires enough tokens (see minimum threshold). "
            "Changing cached text requires creating a new cache."
        ),
    },
    "settings.prompt_cache.billing_link": {
        "it": (
            "Per costi ufficiali (non stime dell'add-on), vedi "
            "<a href=\"{billing_url}\">AI Studio → Fatturazione</a>."
        ),
        "en": (
            "For official costs (not add-on estimates), see "
            "<a href=\"{billing_url}\">AI Studio → Billing</a>."
        ),
    },
    "settings.prompt_cache_ttl": {
        "it": "Durata cache (secondi)",
        "en": "Cache TTL (seconds)",
    },
    "settings.prompt_cache_min_chars": {
        "it": "Caratteri minimi per la cache (controllo interno)",
        "en": "Minimum characters to cache (internal check)",
    },
    "settings.prompt_cache.segment.context_wrapper.disabled": {
        "it": "Incluso automaticamente quando si cache nota, template o CSS.",
        "en": "Included automatically when caching note, templates, or CSS.",
    },
    "settings.prompt_cache.system_instruction_cache_info": {
        "it": (
            "Se le istruzioni di sistema sono separate per chat e ottimizzazione, "
            "quando la cache è usata per la chat verranno inviate solo le istruzioni "
            "specifiche della chat; per l'ottimizzazione solo quelle specifiche di ottimizzazione."
        ),
        "en": (
            "When system instructions are split between chat and optimize: "
            "cached system instructions for chat use the chat-only field, "
            "and cached system instructions for optimize use the optimize-only field."
        ),
    },
    "prompt_cache.recreate_confirm.title": {
        "it": "Ricreare la cache prompt?",
        "en": "Recreate prompt cache?",
    },
    "prompt_cache.recreate_confirm.message": {
        "it": (
            "Il contenuto cached è cambiato ({chars} caratteri, TTL {minutes} min)."
        ),
        "en": (
            "Cached content changed ({chars} characters, TTL {minutes} min)."
        ),
    },
    "prompt_cache.recreate_confirm.detail": {
        "it": (
            "Sì = ricrea la cache e invia. "
            "No = invia senza cache: viene inviato solo il prompt live (scheda Live prompt); "
            "il materiale in cache non è incluso. "
            "Annulla = non inviare. "
            "L'add-on non mostra importi: vedi "
            "<a href=\"{billing_url}\">AI Studio → Fatturazione</a>."
        ),
        "en": (
            "Yes = recreate the cache and send. "
            "No = send without cache: only the live prompt is sent (Live prompt tab); "
            "cached background material is omitted. "
            "Cancel = do not send. "
            "The add-on does not show dollar amounts — see "
            "<a href=\"{billing_url}\">AI Studio → Billing</a>."
        ),
    },
    "prompt_cache.recreate_default.title": {
        "it": "Azione predefinita",
        "en": "Default action",
    },
    "prompt_cache.recreate_default.message": {
        "it": "Quando il contenuto cached cambia di nuovo, cosa fare?",
        "en": "When cached content changes again, what should happen?",
    },
    "prompt_cache.recreate_default.detail": {
        "it": "Usata quando l'avviso di ricreazione è disattivato.",
        "en": "Used when the recreate warning is turned off.",
    },
    "prompt_cache.recreate_default.recreate": {
        "it": "Ricrea cache",
        "en": "Recreate cache",
    },
    "prompt_cache.recreate_default.skip_cache": {
        "it": "Invia senza cache",
        "en": "Send without cache",
    },
    "prompt_cache.new_conversation.title": {
        "it": "Cache chat attiva",
        "en": "Active chat cache",
    },
    "prompt_cache.new_conversation.message": {
        "it": "Hai una cache prompt chat attiva. Mantenerla o cancellarla?",
        "en": "You have an active chat prompt cache. Keep it or clear it?",
    },
    "prompt_cache.new_conversation.detail": {
        "it": (
            "Mantieni = la cache resta su Gemini per il prossimo messaggio. "
            "Cancella = elimina la cache remota."
        ),
        "en": (
            "Keep = the cache stays on Gemini for the next message. "
            "Clear = delete the remote cache."
        ),
    },
    "prompt_cache.new_conversation.keep": {
        "it": "Mantieni",
        "en": "Keep",
    },
    "prompt_cache.new_conversation.clear": {
        "it": "Cancella",
        "en": "Clear",
    },
    "prompt_cache.new_conversation.force_clear.message": {
        "it": "La cache chat include contenuto della nota e verrà cancellata.",
        "en": "The chat cache includes note content and will be cleared.",
    },
    "prompt_cache.new_conversation.force_clear.detail": {
        "it": "Non è possibile mantenerla dopo una nuova conversazione quando nota, template o CSS sono in cache.",
        "en": "It cannot be kept after a new conversation when note, templates, or CSS are cached.",
    },
    "prompt_cache.new_conversation_default.title": {
        "it": "Azione predefinita",
        "en": "Default action",
    },
    "prompt_cache.new_conversation_default.message": {
        "it": "Alle prossime nuove conversazioni, cosa fare con la cache chat?",
        "en": "On future new conversations, what should happen to the chat cache?",
    },
    "prompt_cache.new_conversation_default.detail": {
        "it": "Usata quando l'avviso è disattivato. Vale solo per cache globali (senza nota in cache).",
        "en": "Used when the warning is turned off. Only applies to global caches (no cached note).",
    },
    "prompt_cache.new_conversation_default.keep": {
        "it": "Mantieni cache",
        "en": "Keep cache",
    },
    "prompt_cache.new_conversation_default.clear": {
        "it": "Cancella cache",
        "en": "Clear cache",
    },
    "prompt_cache.import_note.title": {
        "it": "Importazione nota e cache",
        "en": "Note import and cache",
    },
    "prompt_cache.import_note.message": {
        "it": "Importare una nuova nota cancellerà la cache chat attiva.",
        "en": "Importing a new note will clear the active chat cache.",
    },
    "prompt_cache.import_note.detail": {
        "it": "La cache include contenuto della sessione (nota, template o CSS).",
        "en": "The cache includes session content (note, templates, or CSS).",
    },
    "settings.prompt_cache_custom_text": {
        "it": "Testo personalizzato per la cache",
        "en": "Custom cache text",
    },
    "settings.prompt_cache_custom_text.hint": {
        "it": (
            "Materiale di riferimento lungo (libro, glossario, regole del deck). Inviato come blocco "
            "cached, non come istruzione di sistema. Puoi caricarlo da un file di testo (.txt)."
        ),
        "en": (
            "Long reference material (book chapter, glossary, deck rules). Sent as a cached content "
            "block, not as system instruction. You can load it from a plain text file (.txt)."
        ),
    },
    "settings.prompt_cache_custom_text.load_file": {
        "it": "Carica da file…",
        "en": "Load from file…",
    },
    "settings.prompt_cache_custom_text.load_file.title": {
        "it": "Carica testo cache da file",
        "en": "Load cache text from file",
    },
    "settings.prompt_cache_custom_text.load_file.filter": {
        "it": "File di testo (*.txt);;Tutti i file (*.*)",
        "en": "Text files (*.txt);;All files (*.*)",
    },
    "settings.prompt_cache_custom_text.load_confirm.title": {
        "it": "Sostituire il testo personalizzato?",
        "en": "Replace custom text?",
    },
    "settings.prompt_cache_custom_text.load_confirm.message": {
        "it": "Il campo contiene già del testo. Sostituirlo con il contenuto del file?",
        "en": "The field already has text. Replace it with the file contents?",
    },
    "settings.prompt_cache_custom_text.load_error": {
        "it": "Impossibile leggere il file: {error}",
        "en": "Could not read file: {error}",
    },
    "settings.prompt_cache_segments": {
        "it": "Segmenti da includere nella cache",
        "en": "Segments to include in cache",
    },
    "settings.prompt_cache_segments.hint": {
        "it": (
            "Il wrapper contesto nota viene incluso automaticamente quando si cache "
            "nota importata, template o CSS. La sezione richiesta (segnaposto "
            "<code>request</code>) resta sempre live."
        ),
        "en": (
            "The note context wrapper is included automatically when caching an "
            "imported note, templates, or CSS. The request section "
            "(<code>request</code> placeholder) always stays live."
        ),
    },
    "settings.prompt_cache.segment.system_instruction": {
        "it": "Istruzioni di sistema",
        "en": "System instructions",
    },
    "settings.prompt_cache.segment.dynamic_rules": {
        "it": "Regole dinamiche",
        "en": "Dynamic rules",
    },
    "settings.prompt_cache.segment.chat_system_addon": {
        "it": "Istruzioni chat extra",
        "en": "Extra chat instructions",
    },
    "settings.prompt_cache.segment.custom_cache_text": {
        "it": "Testo personalizzato per la cache",
        "en": "Custom cache text",
    },
    "settings.prompt_cache.segment.imported_note": {
        "it": "Nota importata (chat)",
        "en": "Imported note (chat)",
    },
    "settings.prompt_cache.segment.card_templates": {
        "it": "Template carte importati (chat)",
        "en": "Imported card templates (chat)",
    },
    "settings.prompt_cache.segment.card_templates_format_guide": {
        "it": "Guida formato template carte (chat)",
        "en": "Card templates format guide (chat)",
    },
    "settings.prompt_cache.segment.notetype_css": {
        "it": "CSS nota importato (chat)",
        "en": "Imported note CSS (chat)",
    },
    "settings.prompt_cache.segment.context_wrapper": {
        "it": "Wrapper contesto nota (chat)",
        "en": "Note context wrapper (chat)",
    },
    "settings.prompt_cache.change_ttl": {
        "it": "Cambia TTL",
        "en": "Change TTL",
    },
    "settings.prompt_cache.change_ttl_seconds": {
        "it": "TTL per cambio (secondi)",
        "en": "TTL for change (seconds)",
    },
    "settings.prompt_cache.change_ttl.success": {
        "it": "TTL cache aggiornato.",
        "en": "Cache TTL updated.",
    },
    "settings.prompt_cache.change_ttl.none": {
        "it": "Nessuna cache tracciata da aggiornare.",
        "en": "No tracked cache to update.",
    },
    "settings.prompt_cache.change_ttl.partial": {
        "it": "TTL aggiornato per {count} cache.",
        "en": "TTL updated for {count} cache(s).",
    },
    "settings.prompt_cache.change_ttl.failed": {
        "it": "Impossibile aggiornare il TTL della cache.",
        "en": "Could not update cache TTL.",
    },
    "settings.prompt_cache.extend": {
        "it": "Cambia TTL",
        "en": "Change TTL",
    },
    "settings.prompt_cache.clear": {
        "it": "Elimina cache tracciate",
        "en": "Clear tracked caches",
    },
    "settings.prompt_cache.manage": {
        "it": "Gestisci cache…",
        "en": "Manage caches…",
    },
    "settings.prompt_cache.manager.title": {
        "it": "Cache prompt su Gemini",
        "en": "Gemini prompt caches",
    },
    "settings.prompt_cache.manager.intro": {
        "it": (
            "Elenca le cache remote create da questo add-on (nome <code>anki-ai-*</code> su Google).<br><br>"
            "<b>Tracciata</b> — l'add-on ricorda questa cache in locale (<code>prompt_cache_state.json</code>) "
            "come cache attuale per chat o ottimizzazione.<br>"
            "<b>Orfana</b> — esiste ancora su Google ma l'add-on non la traccia (es. dopo un crash o prima "
            "della persistenza); può costare fino a scadenza TTL.<br><br>"
            "Eliminare un'orfana non influisce sulla chat finché non era tracciata."
        ),
        "en": (
            "Lists remote caches created by this add-on (<code>anki-ai-*</code> display names on Google).<br><br>"
            "<b>Tracked</b> — the add-on remembers this cache locally (<code>prompt_cache_state.json</code>) "
            "as the current cache for chat or optimize.<br>"
            "<b>Orphan</b> — still on Google but not tracked locally (e.g. after a crash or before persistence); "
            "may incur storage cost until TTL expires.<br><br>"
            "Deleting an orphan does not affect chat unless it was the tracked cache."
        ),
    },
    "settings.prompt_cache.manager.empty": {
        "it": "Nessuna cache dell'add-on (prefisso anki-ai-) trovata sul tuo account.",
        "en": "No add-on caches (anki-ai- prefix) found on your account.",
    },
    "settings.prompt_cache.manager.no_api_key": {
        "it": "Imposta una chiave API per elencare o eliminare le cache remote.",
        "en": "Set an API key to list or delete remote caches.",
    },
    "settings.prompt_cache.manager.load_error": {
        "it": "Impossibile caricare le cache: {error}",
        "en": "Could not load caches: {error}",
    },
    "settings.prompt_cache.manager.summary": {
        "it": "{count} cache dell'add-on · {orphans} orfane (non tracciate localmente)",
        "en": "{count} add-on caches · {orphans} orphaned (not tracked locally)",
    },
    "settings.prompt_cache.manager.col.purpose": {
        "it": "Per",
        "en": "For",
    },
    "settings.prompt_cache.manager.col.model": {
        "it": "Modello",
        "en": "Model",
    },
    "settings.prompt_cache.manager.col.expires": {
        "it": "Scade",
        "en": "Expires",
    },
    "settings.prompt_cache.manager.col.tracked": {
        "it": "Tracciata",
        "en": "Tracked",
    },
    "settings.prompt_cache.manager.col.actions": {
        "it": "Azioni",
        "en": "Actions",
    },
    "settings.prompt_cache.manager.refresh": {
        "it": "Aggiorna",
        "en": "Refresh",
    },
    "settings.prompt_cache.manager.delete_orphans": {
        "it": "Elimina orfane",
        "en": "Delete orphans",
    },
    "settings.prompt_cache.manager.delete_orphans.title": {
        "it": "Eliminare le cache orfane?",
        "en": "Delete orphaned caches?",
    },
    "settings.prompt_cache.manager.delete_orphans.message": {
        "it": "Eliminare {count} cache remote non tracciate dall'add-on?",
        "en": "Delete {count} remote caches not tracked by the add-on?",
    },
    "settings.prompt_cache.manager.delete": {
        "it": "Elimina",
        "en": "Delete",
    },
    "settings.prompt_cache.manager.close": {
        "it": "Chiudi",
        "en": "Close",
    },
    "settings.prompt_cache.manager.tracked_yes": {
        "it": "Sì",
        "en": "Yes",
    },
    "settings.prompt_cache.manager.tracked_no": {
        "it": "No",
        "en": "No",
    },
    "settings.prompt_cache.manager.purpose.chat": {
        "it": "Chat",
        "en": "Chat",
    },
    "settings.prompt_cache.manager.purpose.optimize": {
        "it": "Ottimizzazione",
        "en": "Optimize",
    },
    "settings.prompt_cache.manager.purpose.unknown": {
        "it": "Sconosciuto",
        "en": "Unknown",
    },
    "settings.prompt_cache.manager.expired": {
        "it": "Scaduta",
        "en": "Expired",
    },
    "settings.prompt_cache.manager.minutes": {
        "it": "tra {minutes} min",
        "en": "in {minutes} min",
    },
    "settings.prompt_cache.status.inactive": {
        "it": "{purpose} — nessuna cache tracciata.",
        "en": "{purpose} — no tracked cache.",
    },
    "settings.prompt_cache.status.active": {
        "it": "{purpose} — cache attiva · {chars} caratteri cached · scade tra {minutes} min",
        "en": "{purpose} — cache active · {chars} cached characters · expires in {minutes} min",
    },
    "settings.prompt_cache.status.error": {
        "it": "{purpose} — cache non disponibile: {error}",
        "en": "{purpose} — cache unavailable: {error}",
    },
    "chat.prompt_cache.created": {
        "it": (
            "Cache prompt creata su Gemini ({chars} caratteri in cache, "
            "TTL {minutes} min)."
        ),
        "en": (
            "Prompt cache created on Gemini ({chars} cached characters, "
            "TTL {minutes} min)."
        ),
    },
    "settings.prompt_optimize_user": {
        "it": "Prefisso messaggio utente (ottimizzazione campo)",
        "en": "User message prefix (field optimize)",
    },
    "settings.prompt_optimize_user.hint": {
        "it": (
            "Anteposto al contenuto del campo quando ottimizzi. "
            "Specifica che Gemini deve restituire solo il campo aggiornato."
        ),
        "en": (
            "Prepended to the field content when you optimize. "
            "Tells Gemini to return only the updated field content."
        ),
    },
    "settings.prompt_chat_addon": {
        "it": "Istruzioni chat extra",
        "en": "Extra chat instructions",
    },
    "settings.prompt_chat_addon.hint": {
        "it": (
            "Regole solo per la chat: formattazione risposte, blocchi code per i campi, "
            "protocollo regole dinamiche (<UPDATE_DYNAMIC_RULES>), ecc."
        ),
        "en": (
            "Chat-only rules: reply formatting, field code blocks, "
            "dynamic rules protocol (<UPDATE_DYNAMIC_RULES>), etc."
        ),
    },
    "settings.prompt_dynamic_rules_prefix": {
        "it": "Prefisso regole dinamiche (sistema)",
        "en": "Dynamic rules prefix (system)",
    },
    "settings.prompt_dynamic_rules_prefix.hint": {
        "it": (
            "Inserito prima del testo delle regole dinamiche quando non è vuoto. "
            "Per impostazione predefinita indica che le regole dinamiche hanno priorità inferiore "
            "rispetto alle istruzioni statiche sopra; modifica questo testo per dichiarare "
            "esplicitamente una priorità diversa. Gli a capo tra i blocchi del prompt "
            "vengono aggiunti automaticamente."
        ),
        "en": (
            "Inserted before your dynamic rules text when that field is not empty. "
            "By default it states dynamic rules are lower priority than the static instructions "
            "above; edit this text to state a different priority explicitly. "
            "Line breaks between prompt blocks are added automatically."
        ),
    },
    "settings.prompt_chat_context": {
        "it": "Wrapper contesto nota (chat)",
        "en": "Note context wrapper (chat)",
    },
    "settings.prompt_chat_context_order": {
        "it": "Wrapper contesto nota — ordine sezioni (chat)",
        "en": "Note context wrapper — section order (chat)",
    },
    "settings.prompt_chat_context_sections": {
        "it": "Wrapper contesto nota — testo sezioni (chat)",
        "en": "Note context wrapper — section text (chat)",
    },
    "settings.prompt_chat_context.hint": {
        "it": (
            "Usato per ogni invio in chat. Cinque sezioni riordinabili: contesto nota, "
            "guida formato, template, CSS e richiesta. Ogni sezione ha un segnaposto colorato "
            "non eliminabile (pillola) sostituito al momento dell'invio. "
            "La sezione contesto è omessa senza nota importata o con "
            "{icon:barred_brain} Importa disattivo; template/CSS solo con le opzioni import attive. "
            "La richiesta è sempre inviata live (non cachata). "
            "Usa il pulsante <b>i</b> accanto al titolo per la guida."
        ),
        "en": (
            "Used for every chat send. Five reorderable sections: note context, "
            "format guide, templates, CSS, and request. Each section has a colored, "
            "undeletable placeholder pill that is expanded when you send. "
            "The context section is omitted with no imported note "
            "or when {icon:barred_brain} Import toggle is unchecked; templates/CSS only when those import "
            "options are enabled. The request section is always sent live (never cached). "
            "Use the <b>i</b> button beside the title for the guide."
        ),
    },
    "settings.prompt_card_templates_format": {
        "it": "Guida formato template carte (chat)",
        "en": "Card templates format guide (chat)",
    },
    "settings.prompt_card_templates_format.hint": {
        "it": (
            "Se nel messaggio sono inclusi template carte e/o CSS del tipo di nota, questo testo "
            "viene concatenato subito prima di quelle sezioni per spiegare come leggerle."
        ),
        "en": (
            "When card templates and/or note type CSS are included in the message, this text is "
            "chained immediately before those sections to explain how to read them."
        ),
    },
    "settings.mathjax_preview_preamble": {
        "it": "Preambolo MathJax anteprima nota",
        "en": "MathJax note preview preamble",
    },
    "settings.mathjax_preview_preamble.hint": {
        "it": (
            "HTML inserito prima dei campi nella finestra di anteprima nota (chat). "
            "Usato solo se il tipo di nota importato non fornisce un preambolo nei template. "
            "Utile per blocchi nascosti con <code>\\newcommand</code> come nei template carte."
        ),
        "en": (
            "HTML inserted before fields in the chat note preview window. "
            "Used only when the imported note type does not supply a preamble from its templates. "
            "Useful for hidden <code>\\newcommand</code> blocks like in card templates."
        ),
    },
    "settings.system_instruction": {
        "it": "Istruzioni di sistema",
        "en": "System instructions",
    },
    "settings.system_instruction.subtitle": {
        "it": "Alta priorità per impostazione predefinita — testo statico condiviso tra ottimizzazione e chat.",
        "en": "High priority by default — static text shared by optimize and chat.",
    },
    "settings.system_instruction_shared": {
        "it": "Usa le stesse istruzioni di sistema per ottimizzazione e chat",
        "en": "Use the same system instructions for optimize and chat",
    },
    "settings.system_instruction_optimize": {
        "it": "Istruzioni di sistema (ottimizzazione)",
        "en": "System instructions (optimize)",
    },
    "settings.system_instruction_optimize.subtitle": {
        "it": "Ottimizzazione campo (Ctrl+Shift+G). Alta priorità — testo statico.",
        "en": "Field optimize (Ctrl+Shift+G). High priority — static text.",
    },
    "settings.system_instruction_chat": {
        "it": "Istruzioni di sistema (chat)",
        "en": "System instructions (chat)",
    },
    "settings.system_instruction_chat.subtitle": {
        "it": "Alta priorità per impostazione predefinita — testo statico.",
        "en": "High priority by default — static text.",
    },
    "settings.restore_label.system_instruction": {
        "it": "Istruzioni di sistema (campo condiviso)",
        "en": "System instructions (shared text field)",
    },
    "settings.restore_label.system_instruction_optimize": {
        "it": "Istruzioni di sistema (solo ottimizzazione)",
        "en": "System instructions (optimize only)",
    },
    "settings.restore_label.system_instruction_chat": {
        "it": "Istruzioni di sistema (solo chat)",
        "en": "System instructions (chat only)",
    },
    "settings.dynamic_instructions": {
        "it": "Regole dinamiche",
        "en": "Dynamic rules",
    },
    "settings.dynamic_instructions.hint": {
        "it": (
            "Regole apprese via chat quando chiedi a Gemini di ricordarle. "
            "Priorità inferiore alle istruzioni statiche per impostazione predefinita. "
            "Per cambiarla, modifica il prefisso regole dinamiche in Avanzate."
        ),
        "en": (
            "Rules learned via chat when you ask Gemini to remember them. "
            "Lower priority than static instructions by default. "
            "To change priority, edit the dynamic rules prefix under Advanced."
        ),
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
    "settings.restore_defaults": {
        "it": "Ripristina predefiniti",
        "en": "Restore defaults",
    },
    "settings.restore.title": {
        "it": "Ripristina impostazioni predefinite",
        "en": "Restore default settings",
    },
    "settings.restore.hint": {
        "it": "Seleziona le impostazioni da ripristinare ai valori predefiniti, poi clicca Ripristina selezionati.",
        "en": "Select the settings to restore to their defaults, then click Restore selected.",
    },
    "settings.restore.toggle_all": {
        "it": "Seleziona / deseleziona tutto",
        "en": "Check / uncheck all",
    },
    "settings.restore.apply": {
        "it": "Ripristina selezionati",
        "en": "Restore selected",
    },
    "settings.restore.back": {
        "it": "Torna alle impostazioni",
        "en": "Back to settings",
    },
    "settings.restore.none_selected": {
        "it": "Seleziona almeno un'impostazione da ripristinare.",
        "en": "Select at least one setting to restore.",
    },
    "settings.restore_warnings": {
        "it": "Avvisi",
        "en": "Warnings",
    },
    "settings.warnings": {
        "it": "Avvisi",
        "en": "Warnings",
    },
    "settings.restore_warnings.title": {
        "it": "Avvisi",
        "en": "Warnings",
    },
    "settings.warnings.title": {
        "it": "Avvisi",
        "en": "Warnings",
    },
    "settings.restore_warnings.hint": {
        "it": (
            "Seleziona gli avvisi da ripristinare, oppure usa il pulsante sotto per "
            "selezionare tutti quelli attualmente ignorati. Apply selected salva anche le "
            "azioni predefinite."
        ),
        "en": (
            "Select warnings to restore, or use the button below to select all currently "
            "dismissed ones. Apply selected also saves default actions."
        ),
    },
    "settings.warnings.hint": {
        "it": (
            "Seleziona gli avvisi da ripristinare, oppure usa il pulsante sotto per "
            "selezionare tutti quelli attualmente ignorati. Apply selected salva anche le "
            "azioni predefinite."
        ),
        "en": (
            "Select warnings to restore, or use the button below to select all currently "
            "dismissed ones. Apply selected also saves default actions."
        ),
    },
    "settings.warnings.check_dismissed": {
        "it": "Seleziona avvisi ignorati",
        "en": "Check all dismissed warnings",
    },
    "settings.restore_warnings.apply": {
        "it": "Applica selezionati",
        "en": "Apply selected",
    },
    "settings.warnings.apply": {
        "it": "Applica selezionati",
        "en": "Apply selected",
    },
    "settings.restore_warnings.none_selected": {
        "it": "Seleziona almeno un avviso.",
        "en": "Select at least one warning.",
    },
    "settings.warnings.none_selected": {
        "it": "Seleziona almeno un avviso.",
        "en": "Select at least one warning.",
    },
    "settings.restore_warnings.none_dismissed": {
        "it": "Nessun avviso è attualmente ignorato.",
        "en": "No warnings are currently dismissed.",
    },
    "warnings.default_system_instruction": {
        "it": "Avviso: istruzioni di sistema predefinite non personalizzate",
        "en": "Default system instructions not customized warning",
    },
    "warnings.prompt_cache_created_optimize": {
        "it": "Avviso: cache prompt creata (ottimizzazione)",
        "en": "Prompt cache created notice (optimize)",
    },
    "warnings.prompt_cache_recreate_confirm": {
        "it": "Avviso: ricreare cache prompt",
        "en": "Recreate prompt cache warning",
    },
    "warnings.settings_save_cache_clear": {
        "it": "Avviso: salvataggio cancellerà cache prompt",
        "en": "Settings save will clear prompt cache warning",
    },
    "warnings.new_conversation_cache": {
        "it": "Avviso: cache chat su nuova conversazione",
        "en": "Chat cache on new conversation warning",
    },
    "warnings.import_note_cache": {
        "it": "Avviso: cache chat su importazione nota",
        "en": "Chat cache on note import warning",
    },
    "warnings.prompt_cache_custom_text_load": {
        "it": "Avviso: sostituire testo cache personalizzato",
        "en": "Replace custom cache text warning",
    },
    "warnings.prompt_cache_delete_orphans": {
        "it": "Avviso: eliminare cache orfane",
        "en": "Delete orphan caches warning",
    },
    "warnings.default_actions.title": {
        "it": "Azioni predefinite",
        "en": "Default actions",
    },
    "warnings.default_actions.hint": {
        "it": (
            "Usate quando l'avviso corrispondente è disattivato nella lista sopra. "
            "Si salvano con Applica selezionati o Salva nelle impostazioni principali."
        ),
        "en": (
            "Used when the matching warning is turned off in the list above. Saved via "
            "Apply selected or Save on the main settings page."
        ),
    },
    "warnings.default_action.recreate": {
        "it": "Quando il contenuto cached cambia",
        "en": "When cached content changes",
    },
    "warnings.default_action.recreate.recreate": {
        "it": "Ricrea cache",
        "en": "Recreate cache",
    },
    "warnings.default_action.recreate.skip_cache": {
        "it": "Invia senza cache",
        "en": "Send without cache",
    },
    "warnings.default_action.new_conversation_cache": {
        "it": "Nuova conversazione (cache globale)",
        "en": "New conversation (global cache)",
    },
    "warnings.default_action.new_conversation_cache.keep": {
        "it": "Mantieni cache",
        "en": "Keep cache",
    },
    "warnings.default_action.new_conversation_cache.clear": {
        "it": "Cancella cache",
        "en": "Clear cache",
    },
    "settings.save_cache_clear.title": {
        "it": "Cancellare le cache prompt?",
        "en": "Clear prompt caches?",
    },
    "settings.save_cache_clear.message": {
        "it": "Salvare modificherà contenuto o modello cached e invaliderà: {purposes}.",
        "en": "Saving will change cached content or model and invalidate: {purposes}.",
    },
    "settings.save_cache_clear.detail": {
        "it": "Le cache remote tracciate verranno eliminate. Continuare?",
        "en": "Tracked remote caches will be deleted. Continue?",
    },
    "settings.prompt_cache_presets": {
        "it": "Preset testo cache",
        "en": "Cache text presets",
    },
    "settings.prompt_cache_presets.hint": {
        "it": "Salva blocchi di testo riutilizzabili. Ogni preset può essere usato in chat, ottimizzazione o entrambi.",
        "en": "Save reusable text blocks. Each preset can be used for chat, optimize, or both.",
    },
    "settings.prompt_cache_presets.active": {
        "it": "Preset attivo",
        "en": "Active preset",
    },
    "settings.prompt_cache_presets.manual": {
        "it": "Testo manuale (sotto)",
        "en": "Manual text (below)",
    },
    "settings.prompt_cache_presets.add": {
        "it": "Aggiungi preset",
        "en": "Add preset",
    },
    "settings.prompt_cache_presets.remove": {
        "it": "Rimuovi preset",
        "en": "Remove preset",
    },
    "settings.prompt_cache_presets.name": {
        "it": "Nome preset",
        "en": "Preset name",
    },
    "settings.prompt_cache_presets.for_chat": {
        "it": "Chat",
        "en": "Chat",
    },
    "settings.prompt_cache_presets.for_optimize": {
        "it": "Ottimizza",
        "en": "Optimize",
    },
    "settings.prompt_cache_presets.limit": {
        "it": "Numero massimo di preset raggiunto ({max}).",
        "en": "Maximum number of presets reached ({max}).",
    },
    "settings.optimize_modify_prompt_before_send": {
        "it": "Modifica prompt prima di ottimizzare",
        "en": "Modify prompt before optimizing",
    },
    "settings.optimize_modify_prompt_before_send.hint": {
        "it": "Mostra l'editor del prompt (come in chat) prima di inviare l'ottimizzazione.",
        "en": "Show the prompt editor (like chat) before sending an optimization.",
    },
    "prompt.inspect.pre_send.optimize.title": {
        "it": "Prompt prima dell'ottimizzazione",
        "en": "Prompt before optimize",
    },
    "optimize.run": {
        "it": "Ottimizza",
        "en": "Optimize",
    },
    "settings.info": {
        "it": "Guida impostazioni",
        "en": "Settings guide",
    },
    "settings.help.title": {
        "it": "Guida alle impostazioni",
        "en": "Settings guide",
    },
    "settings.help.intro": {
        "it": "Clicca il pulsante <b>i</b> accanto a un'impostazione per leggerne la spiegazione.",
        "en": "Click the <b>i</b> button next to a setting to read its explanation.",
    },
    "settings.help.prompts_overview.link": {
        "it": "Come vengono costruiti i prompt…",
        "en": "How prompts are built…",
    },
    "settings.help.chat_live_settings.link": {
        "it": "Impostazioni chat applicabili subito…",
        "en": "Which chat settings apply immediately…",
    },
    "settings.help.chat_toolbar_icons.link": {
        "it": "Icone della barra chat…",
        "en": "Chat toolbar icons…",
    },
    "settings.help.chat_toolbar_icons.title": {
        "it": "Icone della barra chat",
        "en": "Chat toolbar icons",
    },
    "settings.help.chat_toolbar_icons": {
        "it": (
            "La barra in alto nella chat usa icone compatte; passa il mouse per i suggerimenti.<br><br>"
            "<b>{icon:brain} Import toggle</b> — Pulsante: include o esclude la nota importata nel prossimo messaggio "
            "({icon:brain} = inclusa, {icon:barred_brain} = esclusa).<br>"
            "<b>Edit menu</b> — {icon:pencil} menu: modifica nota, wrapper contesto o template (solo sessione).<br>"
            "<b>Preview</b> — {icon:eye}: apre l'anteprima della nota importata in una finestra separata.<br>"
            "<b>Inspect</b> — {icon:lens}: anteprima del prompt completo adesso, senza inviare.<br>"
            "<b>Stop / precedenza</b> — Pulsante commutabile: {icon:stop} = revisione pre-invio "
            "prima di Gemini; {icon:priority} = invio diretto.<br>"
            "<b>Download</b> — {icon:download}: salva la conversazione corrente come file di testo (.txt). "
            "La cartella scelta viene ricordata.<br>"
            "<b>{icon:plus} Nuova conversazione</b> — Azzera la chat e applica le impostazioni che richiedono "
            "una nuova sessione."
        ),
        "en": (
            "The chat toolbar uses compact icons; hover for tooltips.<br><br>"
            "<b>{icon:brain} Import toggle</b> — Button: include or exclude the imported note from the next message "
            "({icon:brain} = included, {icon:barred_brain} = excluded).<br>"
            "<b>Edit menu</b> — {icon:pencil} menu: edit note, context wrapper, or templates (session only).<br>"
            "<b>Preview</b> — {icon:eye}: open the imported note preview in a separate window.<br>"
            "<b>Inspect</b> — {icon:lens}: read-only preview of the full prompt now, without sending.<br>"
            "<b>Stop / priority</b> — Toggle: {icon:stop} = pre-send review before Gemini; "
            "{icon:priority} = send directly.<br>"
            "<b>Download</b> — {icon:download}: save the current conversation as a plain-text (.txt) file. "
            "The chosen folder is remembered.<br>"
            "<b>{icon:plus} New conversation</b> — Clear the chat and apply settings that require a new session."
        ),
    },
    "settings.help.track_api_costs.link": {
        "it": "Monitorare i costi API…",
        "en": "Track API costs…",
    },
    "settings.help.track_api_costs.title": {
        "it": "Monitorare i costi API",
        "en": "Track API costs",
    },
    "settings.help.track_api_costs": {
        "it": (
            "L'add-on <b>non mostra</b> quanto hai speso in dollari: invia richieste a Gemini "
            "con la tua chiave, ma la fatturazione è gestita da Google.<br><br>"
            "<b>Dove guardare</b><br>"
            "• <a href=\"{billing_url}\">Google AI Studio → Fatturazione</a> — saldo prepagato, "
            "costi giornalieri per progetto/modello, limiti di spesa.<br>"
            "• <a href=\"{usage_url}\">Google AI Studio → Utilizzo</a> — richieste al minuto/giorno, "
            "token, avvicinamento ai rate limit.<br>"
            "• <a href=\"{docs_url}\">Documentazione fatturazione Gemini</a> — prepagato vs postpagato, "
            "capping, tempi di aggiornamento.<br><br>"
            "<b>Piano gratuito vs a pagamento</b><br>"
            "Senza fatturazione collegata resti sul piano gratuito (limiti di quota, nessun addebito). "
            "Con fatturazione attiva paghi secondo le tariffe del modello (input, output, eventuale "
            "cache esplicita).<br><br>"
            "<b>Quanto è “in tempo reale”?</b><br>"
            "Il saldo prepagato di solito si aggiorna in pochi minuti. I grafici dei costi possono "
            "ritardare fino a ~24 ore. L'add-on non calcola importi in dollari.<br><br>"
            "<b>Controlli utili</b><br>"
            "Imposta limiti di spesa mensili per progetto in AI Studio (pagina Spend) e controlla "
            "il saldo prima di sessioni lunghe con note grandi o cache prompt attiva."
        ),
        "en": (
            "The add-on <b>does not show</b> how many dollars you spent: it sends requests to Gemini "
            "with your key, but billing is handled by Google.<br><br>"
            "<b>Where to look</b><br>"
            "• <a href=\"{billing_url}\">Google AI Studio → Billing</a> — prepay balance, "
            "daily cost by project/model, spend caps.<br>"
            "• <a href=\"{usage_url}\">Google AI Studio → Usage</a> — requests per minute/day, "
            "tokens, progress toward rate limits.<br>"
            "• <a href=\"{docs_url}\">Gemini API billing documentation</a> — prepay vs postpay, "
            "caps, and update delays.<br><br>"
            "<b>Free vs paid</b><br>"
            "Without billing linked you stay on the free tier (quota limits, no charges). "
            "With billing enabled you pay per model rates (input, output, and explicit prompt cache "
            "if enabled).<br><br>"
            "<b>How “live” is it?</b><br>"
            "Prepay credit balance usually updates within minutes. Cost charts may lag up to "
            "~24 hours. The add-on does not calculate dollar amounts.<br><br>"
            "<b>Useful controls</b><br>"
            "Set monthly project spend caps in AI Studio (Spend page) and check your balance before "
            "long sessions with large notes or prompt caching enabled."
        ),
    },
    "settings.help.addon_payload_sizes.link": {
        "it": "Dimensioni payload nell'add-on…",
        "en": "Add-on payload sizes…",
    },
    "settings.help.addon_payload_sizes.title": {
        "it": "Dimensioni payload nell'add-on",
        "en": "Add-on payload sizes",
    },
    "settings.help.addon_payload_sizes": {
        "it": (
            "L'add-on <b>non mostra</b> token Gemini né importi in dollari. Dove serve, "
            "usa il conteggio <b>esatto dei caratteri</b> (<code>len(testo)</code>).<br><br>"
            "<b>Avviso payload chat grande</b> — somma caratteri di istruzioni di sistema, "
            "cronologia e messaggio in uscita (contesto nota/template se attivi). "
            "Non include la risposta generata.<br><br>"
            "<b>Conferma ricreazione cache</b> — mostra caratteri del blocco cached e TTL; "
            "per i costi vedi <a href=\"{billing_url}\">AI Studio → Fatturazione</a>.<br><br>"
            "<b>Stato cache</b> — caratteri del testo cached al momento della creazione.<br><br>"
            "<b>Gestisci cache</b> (Impostazioni avanzate) — elenca le cache remote "
            "<code>anki-ai-*</code>. Vedi sotto <b>Tracciata</b> e <b>Orfana</b>.<br><br>"
            "<b>Tracciata</b> — l'add-on ha salvato il nome di questa cache in locale come cache "
            "corrente per chat o ottimizzazione.<br>"
            "<b>Orfana</b> — ancora su Google ma non più tracciata qui (es. riavvio Anki prima "
            "della persistenza); può costare fino a scadenza TTL. Usa «Elimina orfane» per pulire.<br><br>"
            "<b>Soglia minima token cache</b> — controllo interno (~4 caratteri/token) "
            "allineato al minimo Gemini; non è un prezzo né un conteggio mostrato altrove.<br><br>"
            "Per il prompt completo prima dell'invio usa {icon:lens} (<b>Ispeziona prompt</b>) in chat."
        ),
        "en": (
            "The add-on does <b>not</b> show Gemini token counts or dollar amounts. Where helpful, "
            "it uses the <b>exact character count</b> (<code>len(text)</code>).<br><br>"
            "<b>Large chat payload warning</b> — sums characters in system instructions, "
            "history, and outgoing message (note/templates when enabled). "
            "Does not include the generated reply.<br><br>"
            "<b>Cache recreate confirm</b> — shows cached block characters and TTL; "
            "for costs see <a href=\"{billing_url}\">AI Studio → Billing</a>.<br><br>"
            "<b>Cache status</b> — characters of cached text when the cache was created.<br><br>"
            "<b>Manage caches</b> (Advanced settings) — lists remote <code>anki-ai-*</code> caches. "
            "See <b>Tracked</b> and <b>Orphan</b> below.<br><br>"
            "<b>Tracked</b> — the add-on saved this cache name locally as the current cache "
            "for chat or optimize.<br>"
            "<b>Orphan</b> — still on Google but no longer tracked here (e.g. Anki restart before persistence); "
            "may cost until TTL expires. Use <b>Delete orphans</b> to clean up.<br><br>"
            "<b>Minimum tokens to cache</b> — internal check (~4 chars/token) aligned with "
            "Gemini's minimum; not a price and not shown elsewhere.<br><br>"
            "For the full prompt before sending, use {icon:lens} (<b>Inspect prompt</b>) in chat."
        ),
    },
    "settings.help.chat_live_settings.title": {
        "it": "Impostazioni chat applicabili subito",
        "en": "Which chat settings apply immediately",
    },
    "settings.help.prompts_overview.title": {
        "it": "Come vengono costruiti i prompt",
        "en": "How prompts are built",
    },
    "settings.help.prompts_overview": {
        "it": (
            "L'add-on invia a Gemini un <b>prompt di sistema</b> e uno o più <b>messaggi utente</b>. "
            "Quasi tutto il testo è modificabile nelle Impostazioni (e cinque blocchi in <b>Avanzate…</b>). "
            "I pezzi vengono concatenati nell'ordine sotto. L'add-on inserisce a capo tra i blocchi "
            "principali (di solito una riga vuota); non serve aggiungere a capo iniziali o finali "
            "nei testi personalizzati salvo per la formattazione interna.<br><br>"
            "<b>Ottimizzazione campo (Ctrl+Shift+G)</b><br>"
            "<b>Prompt di sistema</b> (in ordine):<br>"
            "1. <b>Istruzioni di sistema</b> — Impostazioni (condivise o solo ottimizzazione)<br>"
            "2. Se le <b>regole dinamiche</b> non sono vuote: "
            "<b>prefisso regole dinamiche</b> (Avanzate) + testo regole dinamiche (Impostazioni)<br><br>"
            "<b>Messaggio utente</b>:<br>"
            "1. <b>Prefisso messaggio utente</b> (Avanzate)<br>"
            "2. Contenuto grezzo del campo Anki attivo<br><br>"
            "Gemini deve restituire solo il campo ottimizzato; l'add-on rimuove eventuali fence Markdown.<br><br>"
            "<b>Chat (Ctrl+Alt+C)</b><br>"
            "<b>Prompt di sistema</b> (in ordine):<br>"
            "1. <b>Istruzioni di sistema</b> — Impostazioni (condivise o solo chat)<br>"
            "2. Se le regole dinamiche non sono vuote: prefisso + testo (come sopra)<br>"
            "3. <b>Istruzioni chat extra</b> — Avanzate "
            "(formattazione risposte, blocchi code, tag &lt;UPDATE_DYNAMIC_RULES&gt;, ecc.)<br><br>"
            "<b>Messaggi utente</b> (con storico fino a «Storico chat (turni)»):<br>"
            "• Di solito: solo ciò che scrivi nella chat<br>"
            "• Con {icon:brain} Importa in chat (dopo import con {icon:brain} dall'editor): "
            "il messaggio è avvolto dal <b>wrapper contesto nota (chat)</b> "
            "(Impostazioni → Avanzate, o <b>Modifica wrapper contesto</b> dal menu {icon:pencil} <b>Modifica</b>). "
            "Cinque sezioni riordinabili con segnaposto colorati non eliminabili "
            "(contesto, guida formato, template, CSS, richiesta). "
            "Obbligatori: segnaposto <code>context</code> e <code>request</code>. "
            "Le sezioni contesto, template e CSS vengono omesse automaticamente quando la nota non è importata, "
            "il pulsante {icon:barred_brain} Importa è disattivo o le relative opzioni import non sono attive.<br>"
            "I campi in <code>{{context}}</code> provengono dalla nota importata "
            "(modificabile con <b>Modifica nota</b>); "
            "ogni campo è formattato come "
            "<code>Campo [Nome]:</code> + HTML grezzo.<br>"
            "Se il wrapper personalizzato omette i segnaposto obbligatori, si usa il modello predefinito.<br>"
            "Se sono attivi import template e/o CSS e compaiono nel messaggio, subito prima delle "
            "sezioni template/CSS viene concatenata la "
            "<b>guida formato template carte (chat)</b> (Avanzate). Puoi metterla in cache "
            "separatamente con la voce omonima nei segmenti cache (consigliato se cache anche template e CSS).<br><br>"
            "<b>Non inviato a Gemini</b>: messaggio di benvenuto, "
            "nome del campo nel messaggio normale.<br><br>"
            "<b>Messaggio import nota</b>: dopo {icon:brain} nell'editor, precompila la casella di input; "
            "i campi compaiono nella finestra di anteprima nota (sola lettura; "
            "modifica con <b>Modifica nota</b> dal menu {icon:pencil} <b>Modifica</b>). "
            "Con {icon:brain} Importa attivo, il messaggio viene inviato come messaggio "
            "utente normale (eventualmente avvolto dal wrapper contesto nota (chat)).<br><br>"
            "Vedi anche <b>Impostazioni chat applicabili subito</b> nella guida impostazioni."
        ),
        "en": (
            "The add-on sends Gemini a <b>system prompt</b> and one or more <b>user messages</b>. "
            "Almost all text is editable in Settings (plus five blocks under <b>Advanced…</b>). "
            "Pieces are concatenated in the order below. The add-on inserts line breaks between "
            "major blocks (usually one blank line); you do not need leading or trailing line breaks "
            "in custom text unless you want them inside a block.<br><br>"
            "<b>Field optimize (Ctrl+Shift+G)</b><br>"
            "<b>System prompt</b> (in order):<br>"
            "1. <b>System instructions</b> — Settings (shared or optimize-only)<br>"
            "2. If <b>dynamic rules</b> are not empty: "
            "<b>dynamic rules prefix</b> (Advanced) + dynamic rules text (Settings)<br><br>"
            "<b>User message</b>:<br>"
            "1. <b>User message prefix</b> (Advanced)<br>"
            "2. Raw HTML of the active Anki field<br><br>"
            "Gemini should return only the optimized field; the add-on strips Markdown fences if present.<br><br>"
            "<b>Chat (Ctrl+Alt+C)</b><br>"
            "<b>System prompt</b> (in order):<br>"
            "1. <b>System instructions</b> — Settings (shared or chat-only)<br>"
            "2. If dynamic rules are not empty: prefix + text (as above)<br>"
            "3. <b>Extra chat instructions</b> — Advanced "
            "(reply formatting, code blocks, &lt;UPDATE_DYNAMIC_RULES&gt; tags, etc.)<br><br>"
            "<b>User messages</b> (with history up to “Chat history (turns)”):<br>"
            "• Usually: only what you type in chat<br>"
            "• With {icon:brain} Import toggle in chat (after {icon:brain} import from the editor): "
            "the message is wrapped by the <b>Note context wrapper (chat)</b> "
            "(Settings → Advanced, or <b>Edit context wrapper</b> from the {icon:pencil} <b>Edit menu</b>). "
            "Five reorderable sections with colored, undeletable placeholder pills "
            "(context, format guide, templates, styling, request). "
            "Required: <code>context</code> and <code>request</code> placeholders. "
            "Context, template, and CSS sections are omitted automatically when no note is imported, "
            "{icon:barred_brain} Import toggle is unchecked, or the matching import options are disabled.<br>"
            "Fields in <code>{{context}}</code> come from the imported note "
            "(editable via <b>Edit note</b>); "
            "each field is formatted as "
            "<code>Field [Name]:</code> + raw HTML.<br>"
            "If a custom wrapper omits required placeholders, the default template is used.<br>"
            "When template and/or CSS import is enabled and those sections appear in the message, "
            "the <b>Card templates format guide (chat)</b> (Advanced) is chained immediately before "
            "the template and styling sections. You can cache it separately under "
            "<b>Card templates format guide (chat)</b> in cache segments (recommended when templates "
            "and CSS are cached too).<br><br>"
            "<b>Not sent to Gemini</b>: welcome message, "
            "field name in a normal message.<br><br>"
            "<b>Note import message</b>: after you click {icon:brain} in the editor, pre-fills the input box; "
            "note fields appear in the separate note preview window (read-only; "
            "edit via <b>Edit note</b> from the {icon:pencil} <b>Edit menu</b>). "
            "When {icon:brain} Import toggle is on, the message is sent as a normal user message "
            "(optionally wrapped by the note context wrapper (chat)).<br><br>"
            "See also <b>Which chat settings apply immediately?</b> in the settings guide."
        ),
    },
    "settings.help.info_tooltip": {
        "it": "Mostra spiegazione",
        "en": "Show explanation",
    },
    "settings.help.back": {
        "it": "← Torna all'elenco",
        "en": "← Back to list",
    },
    "settings.help.close": {
        "it": "Chiudi",
        "en": "Close",
    },
    "settings.help.language": {
        "it": (
            "Lingua dell'interfaccia dell'add-on (menu, chat, messaggi e impostazioni). "
            "Non cambia la lingua delle risposte di Gemini: quella dipende da cosa scrivi tu "
            "e dalle istruzioni di sistema."
        ),
        "en": (
            "Language of the add-on interface (menus, chat, messages, and settings). "
            "It does not change Gemini's reply language — that depends on what you write "
            "and on the system instructions."
        ),
    },
    "settings.help.api_key": {
        "en": (
            "Your Google AI Studio API key used to call Gemini. "
            "It is stored locally in Anki and is not sent anywhere else. "
            "When saving, leave the field empty to keep the key already stored. "
            "Usage is billed to your Google account — see <b>Track API costs</b> in this guide "
            "or the link under the API key field."
        ),
        "it": (
            "Chiave API di Google AI Studio usata per chiamare Gemini. "
            "Viene salvata localmente in Anki e non viene mai inviata altrove. "
            "Puoi lasciare il campo vuoto al salvataggio per mantenere la chiave già memorizzata. "
            "L'utilizzo è addebitato sul tuo account Google — vedi <b>Monitorare i costi API</b> "
            "in questa guida o il link sotto il campo chiave."
        ),
    },
    "settings.help.model_optimize": {
        "it": (
            "Modello Gemini usato per <b>ottimizzare il campo attivo</b> (Ctrl+Shift+G). "
            "Modelli più leggeri (es. flash-lite) sono in genere più veloci; modelli più "
            "capaci possono dare risultati migliori su HTML/MathJax complesso. "
            "Usa <b>Aggiorna modelli da API</b> per scaricare l'elenco aggiornato da Google."
        ),
        "en": (
            "Gemini model used to <b>optimize the active field</b> (Ctrl+Shift+G). "
            "Lighter models (e.g. flash-lite) are usually faster; more capable models may "
            "do better on complex HTML/MathJax. "
            "Use <b>Refresh models from API</b> to fetch the latest list from Google."
        ),
    },
    "settings.help.model_chat": {
        "it": (
            "Modello Gemini usato nella <b>chat</b> (Ctrl+Alt+C) e nell'analisi note ({icon:brain}). "
            "Può essere più capace del modello di ottimizzazione, perché spesso serve "
            "ragionare e spiegare, non solo riformattare."
        ),
        "en": (
            "Gemini model used in <b>chat</b> (Ctrl+Alt+C) and note analysis ({icon:brain}). "
            "It can be more capable than the optimize model, since chat often requires "
            "reasoning and explanations, not just reformatting."
        ),
    },
    "settings.help.thinking_budget_optimize": {
        "it": (
            "Quanti token Gemini può usare per il <b>ragionamento interno</b> prima di "
            "rispondere durante l'ottimizzazione.<br>"
            "• <b>0</b> = nessun thinking (più veloce, consigliato per la riformattazione)<br>"
            "• <b>-1</b> = dinamico (Gemini decide)<br>"
            "• Valori più alti = più ragionamento, più lento"
        ),
        "en": (
            "How many tokens Gemini may spend on <b>internal reasoning</b> before answering "
            "during field optimization.<br>"
            "• <b>0</b> = no thinking (fastest, recommended for reformatting)<br>"
            "• <b>-1</b> = dynamic (Gemini decides)<br>"
            "• Higher values = more reasoning, slower"
        ),
    },
    "settings.help.thinking_budget_chat": {
        "it": (
            "Come sopra, ma per la <b>chat</b>. "
            "Per domande complesse o matematica può aiutare un budget più alto o -1; "
            "per domande semplici, 0 riduce l'attesa."
        ),
        "en": (
            "Same as above, but for <b>chat</b>. "
            "For complex or math questions, a higher budget or -1 can help; "
            "for simple questions, 0 reduces wait time."
        ),
    },
    "settings.help.chat_streaming": {
        "it": (
            "Se attivo, le risposte in chat appaiono <b>man mano</b> che Gemini scrive, "
            "invece di attendere l'intero messaggio. "
            "Non accorcia il tempo totale, ma rende la chat più reattiva."
        ),
        "en": (
            "When enabled, chat replies appear <b>incrementally</b> as Gemini writes, "
            "instead of waiting for the full message. "
            "It does not shorten total time, but makes chat feel more responsive."
        ),
    },
    "settings.help.timeout_seconds": {
        "it": (
            "Tempo massimo (in secondi) di attesa per una risposta API prima di segnalare "
            "un errore di timeout. Aumentalo se ottimizzi campi molto lunghi o se la rete è lenta."
        ),
        "en": (
            "Maximum wait time (in seconds) for an API response before reporting a timeout error. "
            "Increase it if you optimize very long fields or have a slow connection."
        ),
    },
    "settings.help.max_retries": {
        "it": (
            "Quante volte ritentare una chiamata fallita per errori di rete o risposta incompleta. "
            "Gli errori di API key o limite di richieste (429) non vengono ritentati."
        ),
        "en": (
            "How many times to retry a failed call for network errors or incomplete responses. "
            "API key errors and rate limits (429) are not retried."
        ),
    },
    "settings.help.max_history_turns": {
        "it": (
            "Quanti turni di conversazione inviare come contesto in chat. "
            "Un turno = un messaggio tuo + una risposta di Gemini (10 turni = 20 messaggi). "
            "Più storico = migliore memoria conversazionale, ma richieste più lente e costose. "
            "0 = nessuno storico (solo il messaggio corrente)."
        ),
        "en": (
            "How many conversation turns to send as chat context. "
            "One turn = one message from you plus one reply from Gemini (10 turns = 20 messages). "
            "More history = better conversational memory, but slower and costlier requests. "
            "0 = no history (current message only)."
        ),
    },
    "settings.help.prompt_optimize_user": {
        "it": (
            "Prefisso del messaggio utente inviato quando ottimizzi un campo (Ctrl+Shift+G). "
            "Viene anteposto al contenuto del campo. Modificabile in <b>Avanzate…</b>. "
            "Vedi anche <b>Come vengono costruiti i prompt</b> nella guida."
        ),
        "en": (
            "User message prefix sent when you optimize a field (Ctrl+Shift+G). "
            "Prepended to the field content. Editable under <b>Advanced…</b>. "
            "See also <b>How prompts are built</b> in this guide."
        ),
    },
    "settings.help.prompt_chat_addon": {
        "en": (
            "<b>Extra chat instructions</b> — chat-only rules appended to system instructions "
            "(reply formatting, code blocks, dynamic rules protocol). "
            "Editable under <b>Advanced…</b>."
        ),
        "it": (
            "<b>Istruzioni chat extra</b> — regole solo chat appese alle istruzioni di sistema "
            "(formattazione risposte, blocchi code, protocollo regole dinamiche). "
            "Modificabile in <b>Avanzate…</b>."
        ),
    },
    "settings.help.prompt_dynamic_rules_prefix": {
        "it": (
            "Intestazione inserita prima del testo delle regole dinamiche nel prompt di sistema "
            "(solo se le regole dinamiche non sono vuote). Modificabile in <b>Avanzate…</b>. "
            "Per impostazione predefinita indica priorità inferiore rispetto alle istruzioni statiche; "
            "modifica il testo per dichiarare esplicitamente una priorità diversa."
        ),
        "en": (
            "Header inserted before your dynamic rules text in the system prompt "
            "(only when dynamic rules are not empty). Editable under <b>Advanced…</b>. "
            "By default it states lower priority than static instructions; edit the text to state "
            "a different priority explicitly."
        ),
    },
    "settings.help.prompt_chat_context": {
        "it": (
            "Modello del messaggio utente per ogni invio in chat.<br><br>"
            "Cinque sezioni riordinabili con frecce su/giù. Ogni sezione ha un segnaposto colorato "
            "non eliminabile (pillola) che viene sostituito al momento dell'invio:<br>"
            "<b>Contesto nota</b> — segnaposto <code>context</code>; omessa senza nota importata "
            "o con {icon:barred_brain} Importa disattivo.<br>"
            "<b>Guida formato</b> — testo che spiega template/CSS Anki (stesso contenuto di "
            "«Guida formato template carte»); mostrata solo quando template o CSS sono inclusi.<br>"
            "<b>Template</b> — segnaposto <code>templates</code>; solo con import template attivo.<br>"
            "<b>CSS</b> — segnaposto <code>styling</code>; solo con import CSS attivo.<br>"
            "<b>Richiesta</b> — segnaposto <code>request</code>; sempre inviata live, mai in cache.<br><br>"
            "L'ordine delle sezioni nel messaggio finale segue l'ordine qui impostato. "
            "Per modifiche solo alla sessione corrente usa <b>Modifica wrapper contesto</b> "
            "nel menu {icon:pencil} <b>Modifica</b> della chat."
        ),
        "en": (
            "User message template for every chat send.<br><br>"
            "Five reorderable sections (up/down arrows). Each section has a colored, "
            "undeletable placeholder pill that is expanded when you send:<br>"
            "<b>Note context</b> — <code>context</code> placeholder; omitted with no imported note "
            "or when {icon:barred_brain} Import toggle is unchecked.<br>"
            "<b>Format guide</b> — explains Anki template/CSS syntax (same text as "
            "«Card templates format guide»); shown only when templates or CSS are included.<br>"
            "<b>Templates</b> — <code>templates</code> placeholder; only when template import is enabled.<br>"
            "<b>Styling</b> — <code>styling</code> placeholder; only when CSS import is enabled.<br>"
            "<b>Request</b> — <code>request</code> placeholder; always sent live, never cached.<br><br>"
            "The final message section order matches the order set here. "
            "For session-only edits use <b>Edit context wrapper</b> from the chat {icon:pencil} <b>Edit menu</b>."
        ),
    },
    "settings.help.prompt_chat_context_order": {
        "it": (
            "Ordine delle cinque sezioni del wrapper nel messaggio chat inviato a Gemini.<br><br>"
            "In <b>Avanzate…</b>, usa le frecce su/giù accanto a ogni sezione per riordinarle. "
            "L'ordine qui impostato è quello del messaggio finale.<br><br>"
            "Le sezioni omesse al momento dell'invio (nessuna nota importata, "
            "{icon:barred_brain} Importa disattivo, template/CSS non inclusi, ecc.) "
            "vengono saltate anche se compaiono nell'elenco."
        ),
        "en": (
            "Order of the five wrapper sections in the chat message sent to Gemini.<br><br>"
            "Under <b>Advanced…</b>, use the up/down arrows beside each section to reorder them. "
            "The order set here is the order in the final outgoing message.<br><br>"
            "Sections omitted at send time (no imported note, "
            "{icon:barred_brain} Import toggle off, templates/CSS not included, etc.) "
            "are skipped even if they still appear in the list."
        ),
    },
    "settings.help.prompt_chat_context_sections": {
        "it": (
            "Testo introduttivo prima di ogni segnaposto colorato (pillola) nelle sezioni del wrapper.<br><br>"
            "Esempio: le righe prima di <code>{{context}}</code> che diventano intestazioni "
            "<code>Campo [Nome]:</code>. I segnaposto obbligatori <code>context</code> e "
            "<code>request</code> non possono essere rimossi.<br><br>"
            "La sezione <b>Guida formato</b> modifica il testo di "
            "«Guida formato template carte (chat)» (concatenato prima dei template/CSS quando inclusi). "
            "Le altre sezioni definiscono solo il prefisso attorno al rispettivo segnaposto."
        ),
        "en": (
            "Introductory text before each colored placeholder pill in the wrapper sections.<br><br>"
            "Example: the lines before <code>{{context}}</code> that become "
            "<code>Field [Name]:</code> headers. Required placeholders <code>context</code> and "
            "<code>request</code> cannot be removed.<br><br>"
            "The <b>Format guide</b> section edits the "
            "«Card templates format guide (chat)» text (chained before templates/CSS when included). "
            "The other sections define only the prefix around their placeholder."
        ),
    },
    "settings.wrapper_section.context": {
        "it": "Contesto nota",
        "en": "Note context",
    },
    "settings.wrapper_section.format_guide": {
        "it": "Guida formato template/CSS",
        "en": "Templates/CSS format guide",
    },
    "settings.wrapper_section.templates": {
        "it": "Template carte",
        "en": "Card templates",
    },
    "settings.wrapper_section.styling": {
        "it": "CSS tipo di nota",
        "en": "Note type CSS",
    },
    "settings.wrapper_section.request": {
        "it": "Richiesta studente",
        "en": "Student request",
    },
    "settings.wrapper_section.move_up": {
        "it": "Sposta su",
        "en": "Move up",
    },
    "settings.wrapper_section.move_down": {
        "it": "Sposta giù",
        "en": "Move down",
    },
    "settings.wrapper_import_warning.templates": {
        "it": (
            "L'import template è attivo ma la sezione template non contiene il segnaposto "
            "<code>templates</code>. I template importati potrebbero non comparire nel messaggio."
        ),
        "en": (
            "Template import is enabled but the templates section is missing the "
            "<code>templates</code> placeholder. Imported templates may be omitted from the message."
        ),
    },
    "settings.wrapper_import_warning.styling": {
        "it": (
            "L'import CSS è attivo ma la sezione CSS non contiene il segnaposto "
            "<code>styling</code>. Lo stile importato potrebbe non comparire nel messaggio."
        ),
        "en": (
            "CSS import is enabled but the styling section is missing the "
            "<code>styling</code> placeholder. Imported styling may be omitted from the message."
        ),
    },
    "settings.wrapper_import_warning.required": {
        "it": (
            "La sezione richiesta deve includere il segnaposto <code>request</code>. "
            "Ripristino predefiniti."
        ),
        "en": (
            "The request section must include the <code>request</code> placeholder. "
            "Reverting to defaults."
        ),
    },
    "chat.wrapper_import_warning.required": {
        "it": (
            "La sezione richiesta deve includere {{request}}. "
            "Ripristino del wrapper delle impostazioni."
        ),
        "en": (
            "The request section must include {{request}}. "
            "Reverting to settings wrapper."
        ),
    },
    "settings.help.prompt_card_templates_format": {
        "it": (
            "Testo concatenato <b>prima delle sezioni template carte e CSS del tipo di nota</b> "
            "quando compaiono nel messaggio (import con {icon:brain} e le relative opzioni "
            "attive in Impostazioni). Spiega a Gemini come interpretare le sezioni "
            "<code>[TEMPLATE DELLE CARTE]</code> e <code>[STILE DEL TIPO DI NOTA]</code> "
            "che seguono. Modificabile in <b>Avanzate…</b>. Se vuoto, non viene inviato nulla."
        ),
        "en": (
            "Text chained <b>before the card template and note type CSS sections</b> when they "
            "appear in the message ({icon:brain} import with the corresponding Settings options enabled). "
            "Explains to Gemini how to read the "
            "<code>[CARD TEMPLATES]</code> and <code>[NOTE TYPE STYLING]</code> sections that follow. "
            "Editable under <b>Advanced…</b>. If empty, nothing extra is sent."
        ),
    },
    "settings.help.mathjax_preview_preamble": {
        "it": (
            "HTML opzionale per l'<b>anteprima nota</b> nella chat (finestra separata). "
            "All'import con {icon:brain}, se i template fronte/retro del tipo di nota contengono un preambolo "
            "MathJax (es. un <code>div</code> nascosto con <code>\\newcommand</code>), "
            "quello ha priorità. Altrimenti viene usato questo testo. "
            "Non influisce sui messaggi inviati a Gemini."
        ),
        "en": (
            "Optional HTML for the chat <b>note preview window</b>. "
            "On {icon:brain} import, if the note type's front/back templates contain a MathJax preamble "
            "(e.g. a hidden <code>div</code> with <code>\\newcommand</code>), that takes priority. "
            "Otherwise this text is used. Does not affect messages sent to Gemini."
        ),
    },
    "settings.help.temperature_optimize": {
        "it": (
            "Creatività del modello in ottimizzazione (0 = molto deterministico). "
            "Valori bassi sono consigliati per riformattare HTML/MathJax in modo coerente."
        ),
        "en": (
            "Model creativity during optimization (0 = highly deterministic). "
            "Low values are recommended for consistent HTML/MathJax reformatting."
        ),
    },
    "settings.help.temperature_chat": {
        "it": (
            "Creatività del modello in chat. "
            "Valori leggermente più alti possono rendere le spiegazioni più naturali; "
            "valori bassi rendono le risposte più prevedibili."
        ),
        "en": (
            "Model creativity in chat. "
            "Slightly higher values can make explanations more natural; "
            "lower values make replies more predictable."
        ),
    },
    "settings.help.confirm_before_apply": {
        "it": (
            "Se attivo, dopo l'ottimizzazione mostra un'<b>anteprima</b> affiancata "
            "(originale vs ottimizzato) e chiede conferma prima di sostituire il campo."
        ),
        "en": (
            "When enabled, after optimization shows a side-by-side <b>preview</b> "
            "(original vs optimized) and asks for confirmation before replacing the field."
        ),
    },
    "settings.help.brain_import_message": {
        "it": (
            "Quando clicchi {icon:brain} nell'editor, l'add-on importa tutti i campi della nota in chat e inserisce "
            "questo testo nella casella di input. I campi compaiono nella finestra di anteprima nota "
            "({icon:eye}); modificali con <b>Modifica nota</b> dal menu {icon:pencil} <b>Modifica</b>. "
            "Puoi personalizzarlo per chiedere sempre la stessa analisi (es. atomicità, semplificazione). "
            "Lascia il predefinito per il messaggio standard nella lingua scelta."
        ),
        "en": (
            "When you click {icon:brain} in the editor, the add-on imports all note fields into chat and places "
            "this text in the input box. Fields appear in the separate note preview window "
            "({icon:eye}); edit them via <b>Edit note</b> from the {icon:pencil} <b>Edit menu</b>. "
            "Customize it to always ask the same kind of analysis (e.g. atomicity, simplification). "
            "Keep the default for the standard message in your selected language."
        ),
    },
    "settings.help.brain_import_templates": {
        "it": (
            "Se attivo, quando invii in chat con {icon:brain} Importa attivo, il messaggio include "
            "tutti i template delle carte del tipo di nota (fronte e retro). "
            "Puoi modificarli con <b>Modifica template</b> dal menu {icon:pencil} <b>Modifica</b> nella chat. "
            "Disattivato per impostazione predefinita per limitare la dimensione del messaggio inviato a Gemini."
        ),
        "en": (
            "When enabled, sending chat with {icon:brain} Import toggle on adds all card templates "
            "from the note type (front and back) to the message. "
            "You can edit them via <b>Edit templates</b> from the {icon:pencil} <b>Edit menu</b> in chat. "
            "Off by default to keep Gemini message size smaller."
        ),
    },
    "settings.help.brain_import_css": {
        "it": (
            "Se attivo, include il CSS condiviso del tipo di nota in una sezione dedicata del messaggio chat. "
            "Disattivato per impostazione predefinita perché spesso è lungo e raramente necessario."
        ),
        "en": (
            "When enabled, includes the note type's shared CSS in a dedicated section of the chat message. "
            "Off by default because it is often long and rarely needed."
        ),
    },
    "settings.help.chat_payload_warning_chars": {
        "it": (
            "Prima di inviare in chat, conta i <b>caratteri</b> totali del payload inviato a Gemini "
            "(istruzioni di sistema, cronologia e messaggio in uscita). "
            "Se superi questa soglia, compare un avviso con possibilità di annullare l'invio. "
            "Non è un conteggio token né un costo. Si applica subito anche con chat aperta."
        ),
        "en": (
            "Before sending in chat, counts total <b>characters</b> in the payload sent to Gemini "
            "(system instructions, history, and outgoing message). "
            "Above this threshold, a warning appears and you can cancel the send. "
            "This is not a token count or a cost. Applies immediately even with an open chat."
        ),
    },
    "settings.help.inspect_optimize_prompt": {
        "it": (
            "Apre una finestra di sola lettura con il prompt completo usato per l'ottimizzazione campo "
            "(Ctrl+Shift+G): istruzioni di sistema, regole dinamiche, prefisso utente e segnaposto "
            "per il contenuto del campo attivo."
        ),
        "en": (
            "Opens a read-only window with the full prompt used for field optimize (Ctrl+Shift+G): "
            "system instructions, dynamic rules, user prefix, and a placeholder for the active field content."
        ),
    },
    "settings.help.chat_live_settings": {
        "it": (
            "<b>Impostazioni chat applicabili subito</b> (chat aperta): lingua interfaccia, "
            "soglia avviso caratteri payload, ispezione prompt, timeout, max retry.<br>"
            "<b>Richiedono nuova conversazione</b> (banner in chat): istruzioni di sistema, "
            "regole dinamiche, modello/temperatura/thinking chat, streaming, storico turni, "
            "prompt avanzati chat, import template/CSS. Usa {icon:plus} Nuova conversazione o chiudi e riapri la chat."
        ),
        "en": (
            "<b>Settings applied immediately</b> (open chat): interface language, "
            "chat payload character warning threshold, prompt inspection, timeout, max retries.<br>"
            "<b>Require a new conversation</b> (banner in chat): system instructions, dynamic rules, "
            "chat model/temperature/thinking, streaming, history turns, advanced chat prompts, "
            "template/CSS import. Use {icon:plus} <b>New conversation</b> or close and reopen chat."
        ),
    },
    "settings.help.system_instruction": {
        "it": (
            "Istruzioni di sistema <b>statiche</b> inviate a Gemini. Con l'opzione condivisa attiva, "
            "valgono sia per l'ottimizzazione del campo sia per la chat. Definiscono stile HTML, "
            "MathJax e regole metodologiche. Hanno priorità alta rispetto alle regole dinamiche "
            "per impostazione predefinita."
        ),
        "en": (
            "<b>Static</b> system instructions sent to Gemini. When shared is enabled, they apply "
            "to both field optimization and chat. They define HTML, MathJax, and methodology rules. "
            "They take priority over dynamic rules by default."
        ),
    },
    "settings.help.system_instruction_shared": {
        "it": (
            "Se attivo, un'unica casella di istruzioni vale per ottimizzazione e chat. "
            "Se disattivo, puoi definire istruzioni separate per ciascuna modalità."
        ),
        "en": (
            "When enabled, one instruction box applies to both optimize and chat. "
            "When disabled, you can define separate instructions for each mode."
        ),
    },
    "settings.help.system_instruction_optimize": {
        "it": (
            "Istruzioni statiche usate solo quando ottimizzi un campo con Gemini. "
            "Ideali per regole rigide su HTML, MathJax e output pronto da incollare nel campo."
        ),
        "en": (
            "Static instructions used only when optimizing a field with Gemini. "
            "Best for strict HTML, MathJax, and field-ready output rules."
        ),
    },
    "settings.help.system_instruction_chat": {
        "it": (
            "Istruzioni statiche usate solo nella chat con Gemini. "
            "Puoi includere preferenze su tono, spiegazioni e formattazione delle risposte."
        ),
        "en": (
            "Static instructions used only in the Gemini chat. "
            "You can include preferences for tone, explanations, and reply formatting."
        ),
    },
    "settings.help.dynamic_instructions": {
        "it": (
            "Regole apprese via chat e salvate dall'add-on (es. quando chiedi a Gemini di "
            "“ricordare globalmente” una preferenza). Priorità inferiore rispetto alle "
            "istruzioni statiche sopra per impostazione predefinita. Per cambiare la priorità, "
            "modifica il <b>prefisso regole dinamiche</b> in <b>Avanzate</b>. "
            "Puoi modificarle o cancellarle manualmente."
        ),
        "en": (
            "Rules learned via chat and saved by the add-on (e.g. when you ask Gemini to "
            "“remember globally” a preference). Lower priority than the static instructions above "
            "by default. To change priority, edit the <b>dynamic rules prefix</b> under "
            "<b>Advanced</b>. You can edit or clear them manually."
        ),
    },
    "settings.help.prompt_cache_enabled": {
        "it": (
            "Quando attivo, l'add-on crea cache esplicite su Gemini per le parti statiche "
            "dei prompt (istruzioni di sistema, addon chat, ecc.) e le riusa finché il contenuto "
            "e il modello restano invariati. Riduce i costi per input cached per la durata del TTL. "
            "Richiede che il testo cached superi la soglia minima di caratteri."
        ),
        "en": (
            "When enabled, the add-on creates explicit Gemini caches for static prompt parts "
            "(system instructions, chat addon text, etc.) and reuses them while content and model "
            "stay unchanged. Lowers cached-input cost for the TTL period. "
            "Requires cached text to exceed the minimum character threshold."
        ),
    },
    "settings.help.prompt_cache_ttl_seconds": {
        "it": (
            "Durata in secondi delle cache create su Gemini. Al termine, la cache scade e verrà "
            "ricreata al bisogno (con conferma se il contenuto è cambiato). Valori tipici: 3600 (1 ora)."
        ),
        "en": (
            "Lifetime in seconds of caches created on Gemini. After expiry, the cache is recreated "
            "when needed (with confirmation if content changed). Typical value: 3600 (1 hour)."
        ),
    },
    "settings.help.prompt_cache_min_chars": {
        "it": (
            "Soglia interna in <b>caratteri</b> (non token) prima di creare una cache. "
            "Allineata al minimo Gemini (~2048 token, ~4 caratteri per token). "
            "Se il materiale selezionato è più corto, la cache non viene creata."
        ),
        "en": (
            "Internal <b>character</b> threshold (not tokens) before creating a cache. "
            "Aligned with Gemini's minimum (~2048 tokens, ~4 characters per token). "
            "If selected material is shorter, no cache is created."
        ),
    },
    "settings.help.prompt_cache_custom_text": {
        "it": (
            "Testo opzionale aggiuntivo da includere nella cache (es. riferimenti lunghi che "
            "non rientrano nelle altre sezioni). Conta verso la soglia minima di caratteri."
        ),
        "en": (
            "Optional extra text to include in the cache (e.g. long reference material that "
            "does not fit other segments). Counts toward the minimum character threshold."
        ),
    },
    "settings.help.prompt_cache_segments": {
        "it": (
            "Scegli quali parti del prompt entrano nella cache: istruzioni di sistema, regole "
            "dinamiche, addon chat, testo custom, nota importata, template/CSS, wrapper contesto. "
            "Il wrapper contesto si attiva automaticamente quando si cache nota, template o CSS. "
            "Usa <b>Gestisci cache…</b> per vedere o eliminare le cache remote <code>anki-ai-*</code>."
        ),
        "en": (
            "Choose which prompt parts go into the cache: system instructions, dynamic rules, "
            "chat addon, custom text, imported note, templates/CSS, context wrapper. "
            "The context wrapper is included automatically when caching note, templates, or CSS. "
            "Use <b>Manage caches…</b> to view or delete remote <code>anki-ai-*</code> caches."
        ),
    },
    # Dev playground
    "dev.playground.title": {
        "it": "Anki AI — Dev playground",
        "en": "Anki AI — Dev playground",
    },
    "dev.playground.intro": {
        "it": (
            "<b>Dev mock mode</b> intercetta le chiamate API Gemini e le richieste HTTP della cache prompt. "
            "Usa chat, ottimizzazione e caching come al solito — nessun addebito.<br><br>"
            "Le risposte mock sono etichettate <code>[Dev mock]</code>. Le cache remote restano solo in memoria "
            "e si azzerano alla chiusura di Anki (o con <b>Reset mock state</b>)."
        ),
        "en": (
            "<b>Dev mock mode</b> intercepts Gemini API calls and prompt-cache HTTP requests. "
            "Use chat, optimize, and caching as usual — nothing is billed.<br><br>"
            "Mock replies are labeled <code>[Dev mock]</code>. Remote caches live in memory only "
            "and reset when Anki closes (or when you click <b>Reset mock state</b>)."
        ),
    },
    "dev.playground.enable": {
        "it": "Abilita dev mock mode (nessuna chiamata Gemini / cache API reale)",
        "en": "Enable dev mock mode (no real Gemini / cache API calls)",
    },
    "dev.playground.status.active": {
        "it": (
            "<span style='color:{success};'><b>Attivo</b> — chat, ottimizzazione, cache prompt "
            "e refresh modelli usano mock locali. Chiave API non richiesta.</span>"
        ),
        "en": (
            "<span style='color:{success};'><b>Active</b> — chat, optimize, prompt caching, "
            "and model refresh use local mocks. API key is not required.</span>"
        ),
    },
    "dev.playground.status.inactive": {
        "it": "Inattivo — chiamate Gemini normali. Abilita la casella sopra per test locali gratuiti.",
        "en": "Inactive — normal Gemini API calls. Enable the checkbox above for free local testing.",
    },
    "dev.playground.open_chat": {
        "it": "Apri chat",
        "en": "Open chat",
    },
    "dev.playground.reset": {
        "it": "Reset mock state",
        "en": "Reset mock state",
    },
    "dev.playground.clear_log": {
        "it": "Svuota log",
        "en": "Clear log",
    },
    "dev.playground.activity_log": {
        "it": "Log attività",
        "en": "Activity log",
    },
    "dev.playground.close": {
        "it": "Chiudi",
        "en": "Close",
    },
    "dev.playground.tooltip.enabled": {
        "it": "Dev mock mode abilitato",
        "en": "Dev mock mode enabled",
    },
    "dev.playground.tooltip.disabled": {
        "it": "Dev mock mode disabilitato",
        "en": "Dev mock mode disabled",
    },
    "dev.playground.tooltip.reset": {
        "it": "Stato mock reimpostato",
        "en": "Mock state reset",
    },
    "dev.playground.log.enabled": {
        "it": "Dev mock mode abilitato — tracking locale reimpostato.",
        "en": "Dev mock mode enabled — local tracking reset.",
    },
    "dev.playground.log.disabled": {
        "it": "Dev mock mode disabilitato — verranno usate chiamate API reali.",
        "en": "Dev mock mode disabled — real API calls will be used.",
    },
    "dev.playground.log.active": {
        "it": "Dev mock mode attivo.",
        "en": "Dev mock mode is active.",
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
        "it": "Errore: API Key mancante. Impostala con il pulsante impostazioni.",
        "en": "Error: API key missing. Set it with the settings button.",
    },
    "optimize.in_progress": {
        "it": "Ottimizzazione in corso…",
        "en": "Optimization in progress…",
    },
    "optimize.warning.dismiss": {
        "it": "Non mostrare più questo avviso",
        "en": "Do not show this again",
    },
    "optimize.default_instruction.title": {
        "it": "Istruzioni di sistema predefinite",
        "en": "Default system instructions",
    },
    "optimize.default_instruction.message": {
        "it": (
            "Le istruzioni di sistema statiche sono ancora quelle predefinite del componente "
            "aggiuntivo (regole generiche per HTML, MathJax e stile). Personalizzale nelle "
            "impostazioni per adattarle ai tuoi tipi di nota e alle tue preferenze."
        ),
        "en": (
            "Global system instructions are still the add-on's built-in default (generic rules "
            "for HTML, MathJax, and formatting). Customize them in Settings to match your note "
            "types and preferences."
        ),
    },
    "optimize.default_instruction.detail": {
        "it": "Continuare comunque con l'ottimizzazione?",
        "en": "Continue with optimization anyway?",
    },
    "optimize.prompt_cache.created.title": {
        "it": "Cache prompt creata",
        "en": "Prompt cache created",
    },
    "optimize.prompt_cache.created.message": {
        "it": (
            "È stata creata una cache prompt su Gemini per l'ottimizzazione campo "
            "({chars} caratteri in cache, TTL {minutes} min)."
        ),
        "en": (
            "A Gemini prompt cache was created for field optimize "
            "({chars} cached characters, TTL {minutes} min)."
        ),
    },
    "optimize.prompt_cache.created.detail": {
        "it": (
            "Le richieste successive useranno la cache finché il testo cached o il modello "
            "non cambiano. Puoi gestirla in Impostazioni → Avanzate."
        ),
        "en": (
            "Later requests will use the cache until cached text or the model changes. "
            "Manage it under Settings → Advanced."
        ),
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
        "it": (
            "Includi o escludi la nota importata dal prossimo messaggio. "
            "{icon:brain} = inclusa; {icon:barred_brain} = esclusa."
        ),
        "en": (
            "Include or exclude the imported note from the next message. "
            "{icon:brain} = included; {icon:barred_brain} = excluded."
        ),
    },
    "chat.include_context.short": {
        "it": "Importa",
        "en": "Import",
    },
    "chat.include_context.icon": {
        "it": "",
        "en": "",
    },
    "chat.include_context.icon.excluded": {
        "it": "",
        "en": "",
    },
    "chat.edit_wrapper": {
        "it": "Modifica wrapper contesto",
        "en": "Edit context wrapper",
    },
    "chat.edit_wrapper.tooltip": {
        "it": "Modifica wrapper contesto nota",
        "en": "Edit context wrapper",
    },
    "chat.edit_wrapper.wrapper_label": {
        "it": "Wrapper contesto (questa sessione)",
        "en": "Context wrapper (this session)",
    },
    "chat.edit_wrapper.wrapper_label.basic": {
        "it": "Wrapper contesto (questa sessione)",
        "en": "Context wrapper (this session)",
    },
    "chat.edit_wrapper.wrapper_label.with_optional": {
        "it": "Wrapper contesto (questa sessione; sezioni opzionali incluse)",
        "en": "Context wrapper (this session; optional sections included)",
    },
    "chat.edit_wrapper.wrapper_hint": {
        "it": (
            "Il messaggio in chat sostituisce il segnaposto request. "
            "Riordina e modifica le sezioni qui sotto; le modifiche valgono solo per questa sessione."
        ),
        "en": (
            "Your chat message replaces the request placeholder. "
            "Reorder and edit the sections below; changes apply for this session only."
        ),
    },
    "chat.edit_wrapper.wrapper_hint.basic": {
        "it": (
            "Il messaggio in chat sostituisce il segnaposto request. "
            "Riordina e modifica le sezioni qui sotto; le modifiche valgono solo per questa sessione."
        ),
        "en": (
            "Your chat message replaces the request placeholder. "
            "Reorder and edit the sections below; changes apply for this session only."
        ),
    },
    "chat.edit_wrapper.wrapper_hint.with_optional": {
        "it": (
            "Il messaggio in chat sostituisce il segnaposto request. "
            "Le sezioni template/CSS sono incluse in base alle opzioni import attive. "
            "Riordina e modifica le sezioni qui sotto; le modifiche valgono solo per questa sessione."
        ),
        "en": (
            "Your chat message replaces the request placeholder. "
            "Template and CSS sections are included for your current import settings. "
            "Reorder and edit the sections below; changes apply for this session only."
        ),
    },
    "chat.edit_wrapper.wrapper_invalid": {
        "it": (
            "Il wrapper deve includere {{context}} e {{request}}. "
            "Se mancano, il wrapper personalizzato potrebbe essere ignorato."
        ),
        "en": (
            "The wrapper must include {{context}} and {{request}}. "
            "If missing, the custom wrapper may be ignored."
        ),
    },
    "chat.edit_wrapper.wrapper_invalid.basic": {
        "it": "Il wrapper deve includere {{context}} e {{request}}. Ripristino del wrapper delle impostazioni.",
        "en": "The wrapper must include {{context}} and {{request}}. Reverting to settings wrapper.",
    },
    "chat.edit_wrapper.wrapper_invalid.with_optional": {
        "it": (
            "Il wrapper deve includere {{context}} e {{request}} (opzionali {optional}). "
            "Ripristino del wrapper delle impostazioni."
        ),
        "en": (
            "The wrapper must include {{context}} and {{request}} (optional {optional}). "
            "Reverting to settings wrapper."
        ),
    },
    "chat.edit_templates": {
        "it": "Modifica template",
        "en": "Edit templates",
    },
    "chat.edit_templates.tooltip": {
        "it": "Modifica template",
        "en": "Edit templates",
    },
    "chat.edit_templates.title": {
        "it": "Template carte e stile CSS del tipo di nota:",
        "en": "Note type card templates and CSS styling:",
    },
    "chat.edit_templates.title.templates_only": {
        "it": "Template carte del tipo di nota:",
        "en": "Note type card templates:",
    },
    "chat.edit_templates.title.styling_only": {
        "it": "Stile CSS del tipo di nota:",
        "en": "Note type CSS styling:",
    },
    "chat.edit_templates.detail": {
        "it": "Non compaiono nell'anteprima nota.",
        "en": "Not shown in the note preview.",
    },
    "chat.edit_templates.hint": {
        "it": "Template delle carte e stile CSS del tipo di nota. Non compaiono nell'anteprima nota.",
        "en": "Note type card templates and CSS styling. Not shown in the note preview.",
    },
    "chat.edit_templates.hint.templates_only": {
        "it": "Template delle carte del tipo di nota. Non compaiono nell'anteprima nota.",
        "en": "Note type card templates. Not shown in the note preview.",
    },
    "chat.edit_templates.hint.styling_only": {
        "it": "Stile CSS del tipo di nota. Non compare nell'anteprima nota.",
        "en": "Note type CSS styling. Not shown in the note preview.",
    },
    "chat.edit_templates.card_label": {
        "it": "Tipo carta {index}: {name}",
        "en": "Card type {index}: {name}",
    },
    "chat.edit_templates.jump": {
        "it": "Vai al tipo carta…",
        "en": "Go to card type…",
    },
    "chat.edit.menu": {
        "it": "Modifica",
        "en": "Edit",
    },
    "chat.edit.menu.icon": {
        "it": "",
        "en": "",
    },
    "chat.edit.menu.tooltip": {
        "it": "{icon:pencil} Modifica nota, wrapper contesto o template",
        "en": "{icon:pencil} Edit note, context wrapper, or templates",
    },
    "chat.edit_note": {
        "it": "Modifica nota",
        "en": "Edit note",
    },
    "chat.edit_note.send_empty_fields": {
        "it": "Invia campi vuoti",
        "en": "Send empty fields",
    },
    "chat.new_conversation": {
        "it": "{icon:plus} Nuova conversazione",
        "en": "{icon:plus} New conversation",
    },
    "chat.new_conversation.short": {
        "it": "Nuova conv.",
        "en": "New convo",
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
    "chat.stop": {
        "it": "Stop",
        "en": "Stop",
    },
    "chat.stopped": {
        "it": "Risposta interrotta. Puoi modificare il messaggio e reinviarlo.",
        "en": "Response stopped. You can edit your message and send again.",
    },
    "chat.welcome": {
        "it": "Ciao! Puoi chiedermi spiegazioni o dirmi di memorizzare nuove direttive di stile.",
        "en": "Hi! You can ask for explanations or tell me to remember new style directives.",
    },
    "chat.cleared": {
        "it": "Conversazione azzerata. Puoi iniziare una nuova chat.",
        "en": "Conversation cleared. You can start a new chat.",
    },
    "chat.new_conversation.confirm.title": {
        "it": "Nuova conversazione",
        "en": "New conversation",
    },
    "chat.new_conversation.confirm.message": {
        "it": "Azzerare la conversazione corrente?",
        "en": "Clear the current conversation?",
    },
    "chat.new_conversation.confirm.detail": {
        "it": (
            "I messaggi, la cronologia inviata a Gemini e il contesto importato "
            "andranno persi. Questa azione non può essere annullata."
        ),
        "en": (
            "Messages, history sent to Gemini, and imported note context will be lost. "
            "This cannot be undone."
        ),
    },
    "chat.note_empty": {
        "it": "La nota corrente è completamente vuota.",
        "en": "The current note is completely empty.",
    },
    "chat.note_imported": {
        "it": "Contenuto della nota importato con successo!",
        "en": "Note content imported successfully!",
    },
    "chat.preview.hide_imported_note": {
        "it": "Nascondi nota importata",
        "en": "Hide imported note",
    },
    "chat.preview.show_imported_note": {
        "it": "Mostra nota importata",
        "en": "Show imported note",
    },
    "chat.preview.open_window": {
        "it": "Anteprima",
        "en": "Preview",
    },
    "chat.preview.open_window.tooltip": {
        "it": "{icon:eye} Apri l'anteprima della nota importata in una finestra separata",
        "en": "{icon:eye} Open the imported note preview in a separate window",
    },
    "chat.preview.window_title": {
        "it": "Anteprima nota importata",
        "en": "Imported note preview",
    },
    "chat.preview.refresh": {
        "it": "Aggiorna anteprima",
        "en": "Refresh preview",
    },
    "chat.preview.empty": {
        "it": "Nessun contenuto da mostrare.",
        "en": "No content to show.",
    },
    "chat.preview.loading": {
        "it": "Rendering anteprima…",
        "en": "Rendering preview…",
    },
    "chat.api_key_missing": {
        "it": "Errore: API Key mancante (pulsante impostazioni).",
        "en": "Error: API key missing (settings button).",
    },
    "chat.large_payload.title": {
        "it": "Invio chat molto grande",
        "en": "Large chat send",
    },
    "chat.large_payload.message": {
        "it": (
            "La prossima richiesta chat invierà {count} caratteri di input totali "
            "(soglia {threshold}). Inviare comunque?"
        ),
        "en": (
            "The next chat request will send {count} total input characters "
            "(threshold {threshold}). Send anyway?"
        ),
    },
    "chat.large_payload.detail": {
        "it": (
            "Include tutto ciò che Gemini riceve come input: istruzioni di sistema "
            "(incluse regole dinamiche e meta-regola chat), cronologia chat e il messaggio utente "
            "in uscita (contesto nota, template/stile se attivi, ecc.). "
            "Conteggio caratteri esatto, non token né costo. "
            "Puoi alzare la soglia in Impostazioni → «Avviso caratteri payload chat oltre»."
        ),
        "en": (
            "Includes everything Gemini receives as input: system instructions "
            "(including dynamic rules and the chat meta-rule), chat history, and the outgoing user "
            "message (note context, templates/styling when enabled, etc.). "
            "Exact character count — not tokens or cost. "
            "You can raise the threshold in Settings → “Chat payload warning above (characters)”."
        ),
    },
    "chat.inspect_prompt": {
        "it": "",
        "en": "",
    },
    "chat.inspect_prompt.tooltip": {
        "it": "{icon:lens} Anteprima del prompt adesso (non invia)",
        "en": "{icon:lens} Preview the prompt now (does not send)",
    },
    "chat.stop_before_send.icon": {
        "it": "",
        "en": "",
    },
    "chat.modify_prompt_before_send": {
        "it": "",
        "en": "",
    },
    "chat.modify_prompt_before_send.tooltip": {
        "it": (
            "Attiva/disattiva la revisione del prompt prima dell'invio a Gemini. "
            "{icon:stop} (attivo): l'invio apre il dialogo pre-invio per rivedere e "
            "modificare prompt e cache (se attiva). {icon:priority} "
            "(disattivo): i messaggi partono subito. Usa {icon:lens} per un'anteprima del prompt "
            "in sola lettura in qualsiasi momento."
        ),
        "en": (
            "Toggle pre-send review before messages go to Gemini. "
            "{icon:stop} (on): sending opens the pre-send dialog so you can review and edit "
            "the prompt (and cached content when enabled). {icon:priority} (off): messages "
            "send directly. Use {icon:lens} anytime for a read-only prompt preview without sending."
        ),
    },
    "chat.edit_templates.include_templates": {
        "it": "Includi template carte nel messaggio",
        "en": "Include card templates in message",
    },
    "chat.edit_templates.include_css": {
        "it": "Includi CSS nota nel messaggio",
        "en": "Include note CSS in message",
    },
    "chat.settings_stale.message": {
        "it": "Avvia una nuova conversazione perché tutte le impostazioni vengano aggiornate.",
        "en": "Start a new conversation for all settings to be updated.",
    },
    "chat.settings_stale.dismiss": {
        "it": "×",
        "en": "×",
    },
    "prompt.inspect.refresh": {
        "it": "Aggiorna",
        "en": "Refresh",
    },
    "prompt.inspect.formula": {
        "it": "Composizione: {formula}",
        "en": "Composition: {formula}",
    },
    "prompt.inspect.optimize.title": {
        "it": "Ispezione prompt ottimizzazione",
        "en": "Optimize prompt inspection",
    },
    "prompt.inspect.chat.title": {
        "it": "Ispezione prompt chat",
        "en": "Chat prompt inspection",
    },
    "prompt.inspect.pre_send.title": {
        "it": "Modifica prompt prima dell'invio",
        "en": "Modify prompt before sending",
    },
    "prompt.inspect.preview.title": {
        "it": "Anteprima prompt chat",
        "en": "Chat prompt preview",
    },
    "prompt.inspect.pre_send.preview_hint": {
        "it": (
            "Anteprima sola lettura di ciò che verrebbe inviato. Usa Aggiorna dopo "
            "aver modificato il messaggio in chat. Per modificare prima dell'invio, "
            "attiva {icon:stop} nella barra chat."
        ),
        "en": (
            "Read-only preview of what would be sent. Use Refresh after editing the "
            "chat message. To edit before sending, enable {icon:stop} in the chat toolbar."
        ),
    },
    "prompt.inspect.pre_send.view_live": {
        "it": "Prompt live",
        "en": "Live prompt",
    },
    "prompt.inspect.pre_send.view_caching": {
        "it": "Caching",
        "en": "Caching",
    },
    "prompt.inspect.pre_send.jump": {
        "it": "Vai a…",
        "en": "Go to…",
    },
    "prompt.inspect.pre_send.full_live_prompt": {
        "it": "Prompt live completo",
        "en": "Full live prompt",
    },
    "prompt.inspect.pre_send.full_cached_prompt": {
        "it": "Prompt in cache completo",
        "en": "Full cached prompt",
    },
    "prompt.inspect.pre_send.live_hint": {
        "it": (
            "Questa scheda è ciò che viene inviato con il messaggio: istruzioni ancora "
            "live, cronologia chat e la tua richiesta. Il materiale riutilizzabile sta "
            "nella scheda Caching."
        ),
        "en": (
            "This tab is what goes out with your message: still-live instructions, chat "
            "history, and your request. Reusable background material lives on the Caching tab."
        ),
    },
    "prompt.inspect.pre_send.live_cache_tip": {
        "it": (
            "Suggerimento: le modifiche in questa scheda non invalidano la cache — "
            "solo quelle nella scheda Caching la fanno ricreare."
        ),
        "en": (
            "Tip: edits on this tab do not invalidate the cache — only changes on the "
            "Caching tab trigger recreation."
        ),
    },
    "prompt.inspect.pre_send.edit_live_sections": {
        "it": "Modifica le sezioni sotto; l'anteprima live sopra si aggiorna.",
        "en": "Edit the sections below; the live preview above updates as you type.",
    },
    "prompt.inspect.pre_send.edit_cached_sections": {
        "it": "Modifica le sezioni sotto; l'anteprima cache sopra si aggiorna.",
        "en": "Edit the sections below; the cached preview above updates as you type.",
    },
    "prompt.inspect.pre_send.cache_hint": {
        "it": (
            "Questa scheda è il primo passo quando la cache viene creata o ricreata: "
            "carichiamo su Gemini le parti grandi e riutilizzabili (regole, nota importata, "
            "template, testo cache personalizzato, ecc.). Le richieste successive inviano "
            "solo il prompt live, facendo riferimento a questo contenuto."
        ),
        "en": (
            "This tab is the first step when the cache is created or recreated: we upload "
            "the large reusable parts to Gemini (rules, imported note, templates, custom "
            "cache text, etc.). Later requests send only the live prompt, referencing this "
            "content."
        ),
    },
    "prompt.inspect.pre_send.cache_edit_tip": {
        "it": (
            "Suggerimento: se modifichi questo testo e una cache esiste già, quella cache "
            "non vale più. All'invio ti chiederemo di ricrearla (oppure di inviare senza cache)."
        ),
        "en": (
            "Tip: if you edit this text while a cache already exists, that cache is no longer "
            "valid. When you send, you'll be asked to recreate it (or send without cache)."
        ),
    },
    "prompt.inspect.pre_send.cached_content": {
        "it": "Contenuto in cache",
        "en": "Cached content",
    },
    "prompt.inspect.pre_send.live_system": {
        "it": "Istruzioni di sistema live",
        "en": "Live system instructions",
    },
    "prompt.inspect.system_instruction": {
        "it": "Istruzioni di sistema",
        "en": "System instructions",
    },
    "prompt.inspect.dynamic_rules_prefix": {
        "it": "Prefisso regole dinamiche",
        "en": "Dynamic rules prefix",
    },
    "prompt.inspect.dynamic_instructions": {
        "it": "Regole dinamiche",
        "en": "Dynamic rules",
    },
    "prompt.inspect.chat_system_addon": {
        "it": "Istruzioni chat extra",
        "en": "Extra chat instructions",
    },
    "prompt.inspect.optimize_user_prefix": {
        "it": "Prefisso messaggio utente (ottimizzazione)",
        "en": "User message prefix (optimize)",
    },
    "prompt.inspect.field_content": {
        "it": "Contenuto campo Anki",
        "en": "Anki field content",
    },
    "prompt.inspect.field_placeholder": {
        "it": "[Qui verrebbe inserito l'HTML del campo attivo in Anki]",
        "en": "[Active Anki field HTML would appear here]",
    },
    "prompt.inspect.chat_history": {
        "it": "Cronologia chat",
        "en": "Chat history",
    },
    "prompt.inspect.history_role": {
        "it": "Messaggio {index} ({role})",
        "en": "Message {index} ({role})",
    },
    "prompt.inspect.next_user_message": {
        "it": "Prossimo messaggio utente",
        "en": "Next user message",
    },
    "prompt.inspect.empty_next_message": {
        "it": "[Nessun testo da inviare]",
        "en": "[No text to send]",
    },
    "prompt.inspect.empty_draft": {
        "it": "[campo vuoto]",
        "en": "[empty input]",
    },
    "prompt.inspect.draft_input_note": {
        "it": "Bozza attuale nella casella di input (non inviata):\n{draft}",
        "en": "Current draft in the input box (not sent yet):\n{draft}",
    },
    "prompt.inspect.meta.model": {
        "it": "Modello: {model}",
        "en": "Model: {model}",
    },
    "prompt.inspect.meta.temperature": {
        "it": "Temperatura: {temperature}",
        "en": "Temperature: {temperature}",
    },
    "prompt.inspect.meta.thinking_budget": {
        "it": "Budget thinking: {budget}",
        "en": "Thinking budget: {budget}",
    },
    "prompt.inspect.meta.streaming": {
        "it": "Streaming: {enabled}",
        "en": "Streaming: {enabled}",
    },
    "prompt.inspect.meta.history_turns": {
        "it": "Cronologia inclusa: {turns} turni (max {max_turns})",
        "en": "History included: {turns} turns (max {max_turns})",
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
        "it": "Gemini sta scrivendo.",
        "en": "Gemini is typing.",
    },
    "chat.stopping": {
        "it": "Interruzione in corso.",
        "en": "Stopping.",
    },
    "chat.copied": {
        "it": "Contenuto del campo copiato negli appunti.",
        "en": "Field content copied to clipboard.",
    },
    "chat.download.tooltip": {
        "it": "{icon:download} Scarica la conversazione come file di testo",
        "en": "{icon:download} Download the conversation as a text file",
    },
    "chat.download.title": {
        "it": "Scarica conversazione",
        "en": "Download conversation",
    },
    "chat.download.filter": {
        "it": "File di testo (*.txt)",
        "en": "Text files (*.txt)",
    },
    "chat.download.saved": {
        "it": "Conversazione salvata.",
        "en": "Conversation saved.",
    },
    "chat.download.error": {
        "it": "Impossibile salvare la conversazione: {error}",
        "en": "Could not save the conversation: {error}",
    },
    "chat.download.meta.header": {
        "it": "Esportazione chat Anki AI",
        "en": "Anki AI chat export",
    },
    "chat.download.meta.exported_at": {
        "it": "Esportata il: {timestamp}",
        "en": "Exported at: {timestamp}",
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
        "it": "Campo [{name}]",
        "en": "Field [{name}]",
    },
    "chat.context.empty_field": {
        "it": "(Questo campo è vuoto)",
        "en": "(This field is empty)",
    },
    "chat.context.section.note": {
        "it": "[CONTESTO DELLA NOTA INTERA DA ANALIZZARE]",
        "en": "[FULL NOTE CONTEXT TO ANALYZE]",
    },
    "chat.context.section.templates": {
        "it": "[TEMPLATE DELLE CARTE]",
        "en": "[CARD TEMPLATES]",
    },
    "chat.context.section.styling": {
        "it": "[STILE DEL TIPO DI NOTA]",
        "en": "[NOTE TYPE STYLING]",
    },
    "chat.context.section.request": {
        "it": "[RICHIESTA DELLO STUDENTE]",
        "en": "[STUDENT REQUEST]",
    },
    "chat.context.card_type_header": {
        "it": "[TIPO CARTA {index} NOME] {name}",
        "en": "[CARD TYPE {index} NAME] {name}",
    },
    "chat.context.front_template": {
        "it": "[TEMPLATE FRONTE]",
        "en": "[FRONT TEMPLATE]",
    },
    "chat.context.back_template": {
        "it": "[TEMPLATE RETRO]",
        "en": "[BACK TEMPLATE]",
    },
    "instructions.chat_context_section.context": {
        "it": "[CONTESTO DELLA NOTA INTERA DA ANALIZZARE]\n{{context}}",
        "en": "[FULL NOTE CONTEXT TO ANALYZE]\n{{context}}",
    },
    "instructions.chat_context_section.templates": {
        "it": "[TEMPLATE DELLE CARTE]\n{{templates}}",
        "en": "[CARD TEMPLATES]\n{{templates}}",
    },
    "instructions.chat_context_section.styling": {
        "it": "[STILE DEL TIPO DI NOTA]\n{{styling}}",
        "en": "[NOTE TYPE STYLING]\n{{styling}}",
    },
    "instructions.chat_context_section.request": {
        "it": "[RICHIESTA DELLO STUDENTE]\n{{request}}",
        "en": "[STUDENT REQUEST]\n{{request}}",
    },
    "instructions.card_templates_format": {
        "it": (
            "[GUIDA AL FORMATO TEMPLATE E CSS ANKI]\n\n"
            "Le sezioni [TEMPLATE DELLE CARTE] e/o [STILE DEL TIPO DI NOTA] sotto provengono "
            "dal tipo di nota Anki importato:\n"
            "• Tipi di carta: un tipo di nota può avere più tipi di carta (es. Base, Inverso). "
            "Ognuno ha un template fronte e uno retro.\n"
            "• Template fronte/retro: frammenti HTML mostrati domanda e risposta. "
            "Usano segnaposto di campo Anki come {{Front}}, {{Back}} o qualsiasi nome campo "
            "tra doppie parentesi graffe.\n"
            "• Sintassi Anki: {{NomeCampo}}, {{c1::testo::hint}} per cloze, "
            "{{#Campo}}...{{/Campo}} per sezioni condizionali, filtri come |hint:, ecc. "
            "Sono sintassi template Anki — non testo letterale da riscrivere salvo richiesta.\n"
            "• Stile del tipo di nota: un unico blocco CSS condiviso da tutte le carte del tipo. "
            "I selettori nel CSS (es. .card, #front) si applicano al rendering delle carte.\n"
            "Usa questo riferimento per capire come i campi della nota verranno renderizzati; "
            "non trattare template HTML o CSS come la domanda dello studente salvo richiesta esplicita."
        ),
        "en": (
            "[HOW TO READ ANKI CARD TEMPLATES AND STYLING]\n\n"
            "The [CARD TEMPLATES] and/or [NOTE TYPE STYLING] sections below come from the imported Anki note type:\n"
            "• Card types: a note type may have several card types (e.g. Basic, Reversed). "
            "Each has a front template and a back template.\n"
            "• Front/back templates: HTML snippets shown on the question and answer sides. "
            "They use Anki field placeholders like {{Front}}, {{Back}}, or any custom field name "
            "in double curly braces.\n"
            "• Anki syntax: {{FieldName}}, {{c1::text::hint}} for clozes, "
            "{{#Field}}...{{/Field}} for conditional blocks, filters such as |hint:, etc. "
            "This is Anki template syntax—not literal text to rewrite unless asked.\n"
            "• Note type styling: one shared CSS block for all cards of that type. "
            "Selectors in the CSS (e.g. .card, #front) apply when cards render.\n"
            "Use this reference to understand how imported note fields will render as cards; "
            "do not treat template HTML or CSS as the student's question unless they ask about it."
        ),
    },
    "defaults.brain_import_message": {
        "it": "La nota qui sopra andrebbe scomposta in più note secondo il principio di atomicità? Se sì, come?",
        "en": "Should the note above be split into multiple notes following the atomicity principle? If so, how?",
    },
    "defaults.system_instruction": {
        "it": (
            "Sei un assistente esperto di Anki integrato nell'editor di uno studente.\n"
            "Ottimizza, ripulisci e formatta il contenuto dei campi Anki (HTML e MathJax), "
            "applicando RIGOROSAMENTE le preferenze metodologiche, di stile e notazione dell'utente.\n\n"
            "FORMATTAZIONE ANKI (obbligatoria):\n"
            "- Solo HTML nei campi, non Markdown.\n"
            "- Matematica inline: solo \\(...\\). Display: solo \\[...\\]. Mai $...$ o $$...$$.\n"
            "- Converti matematica plain o non formattata in MathJax con questi delimitatori.\n"
            "- Usa tag HTML (<b>, <i>, <ul>, <ol>, <p>, <div>) per struttura ed enfasi; "
            "preferisci blocchi a lunghe catene di <br>.\n"
            "- Cloze Anki: preserva esattamente {{c1::...}}, {{c2::...}}, ecc. (hint opzionale dopo ::). "
            "Non rimuovere, scoprire, rinumerare o appiattire le cloze; "
            "puoi ripulire HTML/MathJax dentro il testo cloze."
        ),
        "en": (
            "You are an expert Anki assistant integrated into a student's editor.\n"
            "Optimize, clean, and format Anki field content (HTML and MathJax), "
            "strictly applying the user's methodological, style, and notation preferences.\n\n"
            "ANKI FORMATTING (mandatory):\n"
            "- HTML only in fields, not Markdown.\n"
            "- Inline math: \\(...\\) only. Display math: \\[...\\] only. Never $...$ or $$...$$.\n"
            "- Convert unformatted or plain-text math to MathJax with those delimiters.\n"
            "- Use HTML tags (<b>, <i>, <ul>, <ol>, <p>, <div>) for structure and emphasis; "
            "prefer blocks over long <br> chains.\n"
            "- Anki clozes: preserve {{c1::...}}, {{c2::...}}, etc. exactly (optional hint after ::). "
            "Do not remove, unwrap, renumber, or flatten clozes; "
            "you may clean HTML/MathJax inside cloze text."
        ),
    },
    "instructions.optimize_user_prompt": {
        "it": (
            "Ottimizza il campo Anki qui sotto secondo le tue istruzioni di sistema. "
            "Restituisci SOLO l'HTML/MathJax aggiornato del campo, pronto da incollare—"
            "niente spiegazioni, commenti o preambolo. "
            "Non riscrivere, ampliare o cambiare il significato salvo quanto richiesto dalle tue istruzioni."
        ),
        "en": (
            "Optimize the Anki field below per your system instructions. "
            "Return ONLY the updated field HTML/MathJax, ready to paste back—"
            "no explanations, comments, or preamble. "
            "Do not rewrite, expand, or change meaning unless your instructions require it."
        ),
    },
    "instructions.dynamic_rules_prefix": {
        "it": (
            "REGOLE DINAMICHE AGGIUNTIVE PRECEDENTEMENTE MEMORIZZATE "
            "(Priorità inferiore rispetto alle regole sopra)"
        ),
        "en": (
            "ADDITIONAL DYNAMIC RULES PREVIOUSLY STORED "
            "(Lower priority than the rules above)"
        ),
    },
    "instructions.chat_system_addon": {
        "it": (
            "REGOLE DI FORMATTAZIONE PER LE RISPOSTE IN CHAT:\n"
            "- Per il testo esplicativo usa Markdown standard direttamente nel messaggio: **grassetto**, *corsivo*, `codice inline`, titoli con ##, elenchi, tabelle, separatori ---.\n"
            "- NON racchiudere l'intera risposta in un unico blocco ```markdown: scrivi il Markdown nel testo normale.\n"
            "- Nel testo esplicativo (fuori dai blocchi code), usa \\(...\\) per matematica inline e \\[...\\] "
            "per display, così la matematica viene renderizzata nella chat; non usare $...$ o $$...$$.\n"
            "- Quando proponi contenuto da incollare in un campo Anki, scrivi il NOME DEL CAMPO sulla riga immediatamente sopra il blocco code, seguito da due punti. Poi apri un blocco code con tre backtick.\n"
            "- Esempio (ripeti per ogni campo):\n\n"
            "Front:\n"
            "```\n"
            "(contenuto HTML/MathJax grezzo, pronto per essere incollato nel campo Front)\n"
            "```\n\n"
            "Back:\n"
            "```\n"
            "(contenuto HTML/MathJax grezzo)\n"
            "```\n\n"
            "- Il nome del campo va FUORI dal blocco code, mai dentro.\n"
            "- Dentro ogni blocco code metti SOLO ciò che va incollato nel campo: niente spiegazioni, niente Markdown (usa tag HTML <b>, <i> per grassetto/corsivo nei campi).\n"
            "- Nei campi Anki, usa \\(...\\) per matematica inline e \\[...\\] per display; non usare $...$ o $$...$$.\n"
            "- Ogni blocco code avrà un pulsante Copia: l'utente decide cosa incollare in Anki.\n"
            "- I blocchi code possono anche servire per esempi non legati a un campo; in quel caso non mettere un nome campo sulla riga sopra.\n\n"
            "[META-REGOLA DI SISTEMA]: Se l'utente ti chiede esplicitamente di memorizzare, ricordare, "
            "salvare o aggiungere una nuova regola globalmente o per il futuro, accetta la richiesta e includi "
            "TASSATIVAMENTE in fondo alla tua risposta l'elenco completo e aggiornato di TUTTE le regole dinamiche "
            "all'interno dei tag <UPDATE_DYNAMIC_RULES> e </UPDATE_DYNAMIC_RULES>. Includi sia le vecchie regole che la nuova."
        ),
        "en": (
            "CHAT REPLY FORMATTING RULES:\n"
            "- For explanatory text use standard Markdown in the message: **bold**, *italic*, `inline code`, ## headings, lists, tables, --- separators.\n"
            "- Do NOT wrap the entire reply in one ```markdown block; write Markdown as normal text.\n"
            "- In explanatory text (outside code blocks), use \\(...\\) for inline math and \\[...\\] for display math "
            "so equations render in the chat window; never $...$ or $$...$$.\n"
            "- When suggesting content for an Anki field, write the FIELD NAME on the line immediately above the code block, followed by a colon. Then open a three-backtick code block.\n"
            "- Example (repeat for each field):\n\n"
            "Front:\n"
            "```\n"
            "(raw HTML/MathJax ready to paste into the Front field)\n"
            "```\n\n"
            "Back:\n"
            "```\n"
            "(raw HTML/MathJax)\n"
            "```\n\n"
            "- The field name goes OUTSIDE the code block, never inside.\n"
            "- Inside each code block put ONLY field content: no explanations, no Markdown (use HTML <b>, <i> for bold/italic in fields).\n"
            "- In Anki fields use \\(...\\) for inline math and \\[...\\] for display; never $...$ or $$...$$.\n"
            "- Each code block gets a Copy button; the user chooses what to paste into Anki.\n"
            "- Code blocks may also show examples not tied to a field; then omit the field name line above.\n\n"
            "[META-SYSTEM RULE]: If the user explicitly asks you to memorize, remember, save, or add a new "
            "rule globally or for the future, accept the request and MUST include at the end of your reply the "
            "complete updated list of ALL dynamic rules inside <UPDATE_DYNAMIC_RULES> and </UPDATE_DYNAMIC_RULES> "
            "tags. Include both previous rules and the new one."
        ),
    },
    "settings.restore.api_key.title": {
        "it": "Ripristinare la chiave API?",
        "en": "Restore API key default?",
    },
    "settings.restore.api_key.message": {
        "it": (
            "Stai per ripristinare la chiave API al valore predefinito (vuoto). "
            "Dovrai incollare di nuovo la chiave per usare Gemini."
        ),
        "en": (
            "You are about to restore the API key to its default (empty). "
            "You will need to paste your key again to use Gemini."
        ),
    },
    "settings.restore.api_key.detail": {
        "it": "Continuare con il ripristino della chiave API?",
        "en": "Continue restoring the API key?",
    },
    "warnings.api_key_restore": {
        "it": "Avviso: ripristino chiave API",
        "en": "API key restore warning",
    },
    "warnings.settings_unsaved_close": {
        "it": "Avviso: modifiche non salvate alla chiusura delle impostazioni",
        "en": "Unsaved settings warning when closing",
    },
    "warnings.settings_save_confirm": {
        "it": "Avviso: conferma salvataggio impostazioni",
        "en": "Confirm save settings warning",
    },
    "warnings.settings_cancel_confirm": {
        "it": "Avviso: conferma annullamento modifiche impostazioni",
        "en": "Confirm cancel settings changes warning",
    },
    "warnings.chat_new_conversation_confirm": {
        "it": "Avviso: conferma nuova conversazione in chat",
        "en": "Confirm new chat conversation warning",
    },
    "settings.unsaved_close.title": {
        "it": "Modifiche non salvate",
        "en": "Unsaved changes",
    },
    "settings.unsaved_close.message": {
        "it": "Hai modifiche non salvate nelle impostazioni.",
        "en": "You have unsaved changes in Settings.",
    },
    "settings.unsaved_close.detail": {
        "it": "Chiudere senza salvare?",
        "en": "Close without saving?",
    },
    "settings.save_confirm.title": {
        "it": "Salvare le modifiche?",
        "en": "Save changes?",
    },
    "settings.save_confirm.message": {
        "it": "Hai modificato le impostazioni.",
        "en": "You made changes to the settings.",
    },
    "settings.save_confirm.detail": {
        "it": "Salvare le modifiche?",
        "en": "Save your changes?",
    },
    "settings.cancel_confirm.title": {
        "it": "Annullare le modifiche?",
        "en": "Cancel changes?",
    },
    "settings.cancel_confirm.message": {
        "it": "Hai modifiche non salvate.",
        "en": "You have unsaved changes.",
    },
    "settings.cancel_confirm.detail": {
        "it": "Annullare senza salvare?",
        "en": "Discard your changes?",
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
        "it": "API Key non valida o non autorizzata. Controlla la chiave nelle impostazioni (pulsante impostazioni).",
        "en": "Invalid or unauthorized API key. Check the key in settings (settings button).",
    },
    "gemini.rate_limit": {
        "it": "Limite di richieste raggiunto. Riprova tra qualche secondo.",
        "en": "Rate limit reached. Try again in a few seconds.",
    },
    "gemini.rate_limit_retry": {
        "it": "Limite di richieste raggiunto. Riprova tra circa {seconds} secondi.",
        "en": "Rate limit reached. Try again in about {seconds} seconds.",
    },
    "gemini.rate_limit_daily": {
        "it": "Quota giornaliera Gemini esaurita. Riprova domani o controlla i limiti su Google AI Studio.",
        "en": "Daily Gemini quota exceeded. Try again tomorrow or check your limits in Google AI Studio.",
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
    "gemini.cancelled": {
        "it": "Richiesta annullata.",
        "en": "Request cancelled.",
    },
    "gemini.models_empty": {
        "it": "L'API Gemini non ha restituito modelli utilizzabili per generateContent.",
        "en": "The Gemini API returned no usable generateContent models.",
    },
}


def normalize_language(language: str | None) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    normalized = str(language).lower()
    if normalized.startswith(LANG_IT):
        return LANG_IT
    if normalized.startswith(LANG_EN):
        return LANG_EN
    return DEFAULT_LANGUAGE


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
        text, icons = _shield_icon_placeholders(text)
        text = text.format(**kwargs)
        text = _restore_icon_placeholders(text, icons)
        return text
    return text


def default_brain_import_message(config: dict[str, Any] | None = None) -> str:
    return tr("defaults.brain_import_message", config=config)


def default_system_instruction(config: dict[str, Any] | None = None) -> str:
    return tr("defaults.system_instruction", config=config)


def system_instruction_shared(config: dict[str, Any] | None = None) -> bool:
    return bool((config or {}).get("system_instruction_shared", True))


def system_instruction_storage_key(purpose: str, config: dict[str, Any] | None = None) -> str:
    cfg = config or {}
    if system_instruction_shared(cfg):
        return "system_instruction"
    if purpose == "chat":
        return "system_instruction_chat"
    return "system_instruction_optimize"


def _builtin_brain_import_messages() -> frozenset[str]:
    return frozenset(
        message.strip()
        for message in (
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


def _builtin_prompt_texts(i18n_key: str) -> frozenset[str]:
    entry = _STRINGS.get(i18n_key) or {}
    return frozenset(
        message.strip()
        for message in (entry.get(LANG_IT), entry.get(LANG_EN))
        if message and message.strip()
    )


def _is_builtin_prompt(text: str | None, i18n_key: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    return stripped in _builtin_prompt_texts(i18n_key)


def _effective_prompt(config: dict[str, Any] | None, config_key: str, i18n_key: str) -> str:
    stored_raw = (config or {}).get(config_key) or ""
    if _is_builtin_prompt(stored_raw, i18n_key):
        return tr(i18n_key, config=config)
    return stored_raw


def _normalize_prompt_for_save(text: str, i18n_key: str) -> str:
    stripped = (text or "").strip()
    if _is_builtin_prompt(stripped, i18n_key):
        return ""
    return stripped


def default_optimize_user_prompt(config: dict[str, Any] | None = None) -> str:
    return tr("instructions.optimize_user_prompt", config=config)


def is_builtin_optimize_user_prompt(text: str | None) -> bool:
    return _is_builtin_prompt(text, "instructions.optimize_user_prompt")


def effective_optimize_user_prompt(config: dict[str, Any] | None = None) -> str:
    return _effective_prompt(config, "prompt_optimize_user", "instructions.optimize_user_prompt")


def normalize_optimize_user_prompt_for_save(text: str) -> str:
    return _normalize_prompt_for_save(text, "instructions.optimize_user_prompt")


def default_chat_system_addon(config: dict[str, Any] | None = None) -> str:
    return tr("instructions.chat_system_addon", config=config)


def is_builtin_chat_system_addon(text: str | None) -> bool:
    return _is_builtin_prompt(text, "instructions.chat_system_addon")


def effective_chat_system_addon(config: dict[str, Any] | None = None) -> str:
    return _effective_prompt(config, "prompt_chat_addon", "instructions.chat_system_addon")


def normalize_chat_system_addon_for_save(text: str) -> str:
    return _normalize_prompt_for_save(text, "instructions.chat_system_addon")


def default_dynamic_rules_prefix(config: dict[str, Any] | None = None) -> str:
    return tr("instructions.dynamic_rules_prefix", config=config)


def is_builtin_dynamic_rules_prefix(text: str | None) -> bool:
    return _is_builtin_prompt(text, "instructions.dynamic_rules_prefix")


def effective_dynamic_rules_prefix(config: dict[str, Any] | None = None) -> str:
    return _effective_prompt(config, "prompt_dynamic_rules_prefix", "instructions.dynamic_rules_prefix")


def normalize_dynamic_rules_prefix_for_save(text: str) -> str:
    return _normalize_prompt_for_save(text, "instructions.dynamic_rules_prefix")


def default_wrapper_section_text(section_id: str, config: dict[str, Any] | None = None) -> str:
    if section_id == "format_guide":
        return ""
    return tr(f"instructions.chat_context_section.{section_id}", config=config)


def default_wrapper_section_order(config: dict[str, Any] | None = None) -> list[str]:
    return list(DEFAULT_WRAPPER_SECTION_ORDER)


def default_wrapper_sections(config: dict[str, Any] | None = None) -> dict[str, str]:
    return {
        section_id: default_wrapper_section_text(section_id, config)
        for section_id in WRAPPER_SECTION_IDS
        if section_id != "format_guide"
    }


def is_builtin_wrapper_section(section_id: str, text: str | None) -> bool:
    if section_id == "format_guide":
        return not (text or "").strip()
    stripped = (text or "").strip()
    if not stripped:
        return True
    return stripped in _builtin_prompt_texts(
        f"instructions.chat_context_section.{section_id}"
    )


def normalize_wrapper_sections_for_save(
    sections: dict[str, str],
    config: dict[str, Any] | None = None,
) -> dict[str, str]:
    defaults = default_wrapper_sections(config)
    normalized: dict[str, str] = {}
    for section_id in WRAPPER_SECTION_IDS:
        if section_id == "format_guide":
            continue
        if section_id not in sections:
            continue
        raw = sections.get(section_id) or ""
        stripped = raw.strip()
        default_stripped = (defaults.get(section_id) or "").strip()
        if stripped == default_stripped:
            continue
        if not stripped:
            normalized[section_id] = ""
            continue
        if is_builtin_wrapper_section(section_id, stripped):
            continue
        normalized[section_id] = stripped
    return normalized


def normalize_wrapper_order_for_save(order: list[str] | None) -> list[str]:
    return normalize_wrapper_section_order(order)


def effective_wrapper_layout(
    config: dict[str, Any] | None = None,
) -> tuple[list[str], dict[str, str]]:
    cfg = config or {}
    order = normalize_wrapper_section_order(cfg.get("prompt_chat_context_order"))
    stored = cfg.get("prompt_chat_context_sections") or {}
    defaults = default_wrapper_sections(config)
    prefixes: dict[str, str] = {"format_guide": ""}
    for section_id in WRAPPER_SECTION_IDS:
        if section_id == "format_guide":
            continue
        if section_id not in stored:
            prefixes[section_id] = defaults.get(section_id, "")
            continue
        custom = (stored.get(section_id) or "").strip()
        if not custom:
            prefixes[section_id] = ""
        elif is_builtin_wrapper_section(section_id, custom):
            prefixes[section_id] = defaults.get(section_id, "")
        else:
            prefixes[section_id] = custom
    return order, prefixes


def is_builtin_wrapper_layout(
    config: dict[str, Any] | None,
    *,
    section_order: list[str] | None = None,
    section_prefixes: dict[str, str] | None = None,
) -> bool:
    cfg = config or {}
    order = normalize_wrapper_section_order(section_order or cfg.get("prompt_chat_context_order"))
    if order != list(DEFAULT_WRAPPER_SECTION_ORDER):
        return False
    stored = section_prefixes if section_prefixes is not None else (cfg.get("prompt_chat_context_sections") or {})
    for section_id in WRAPPER_SECTION_IDS:
        if section_id == "format_guide":
            continue
        text = (stored.get(section_id) or "").strip()
        if text and not is_builtin_wrapper_section(section_id, text):
            return False
    if not is_builtin_card_templates_format_prompt(cfg.get("prompt_card_templates_format")):
        stored_format = (cfg.get("prompt_card_templates_format") or "").strip()
        if stored_format:
            return False
    return True


def wrapper_layout_warnings(
    section_prefixes: dict[str, str],
    config: dict[str, Any] | None,
) -> list[str]:
    _, defaults = effective_wrapper_layout(config)
    warnings: list[str] = []
    request_text = (section_prefixes.get("request") or defaults.get("request") or "").strip()
    if wrapper_section_missing_placeholders("request", request_text):
        warnings.append("required")
    warnings.extend(
        wrapper_missing_import_placeholders(
            section_prefixes,
            config,
            default_sections=defaults,
        )
    )
    return warnings


def build_wrapper_preview(
    config: dict[str, Any] | None = None,
    *,
    section_order: list[str] | None = None,
    section_prefixes: dict[str, str] | None = None,
    format_guide: str | None = None,
    templates_content: str = "",
    styling_content: str = "",
) -> str:
    order, prefixes = effective_wrapper_layout(config)
    if section_order is not None:
        order = normalize_wrapper_section_order(section_order)
    if section_prefixes is not None:
        prefixes = dict(section_prefixes)
        prefixes.setdefault("format_guide", "")
    guide = (
        effective_card_templates_format_prompt(config)
        if format_guide is None
        else format_guide
    )
    return assemble_wrapper_message(
        config,
        section_order=order,
        section_prefixes=prefixes,
        context="…",
        request="…",
        templates=templates_content or "…",
        styling=styling_content or "…",
        format_guide=guide,
        include_context=True,
        preview=True,
    )


def default_card_templates_format_prompt(config: dict[str, Any] | None = None) -> str:
    return tr("instructions.card_templates_format", config=config)


def is_builtin_card_templates_format_prompt(text: str | None) -> bool:
    return _is_builtin_prompt(text, "instructions.card_templates_format")


def effective_card_templates_format_prompt(config: dict[str, Any] | None = None) -> str:
    return _effective_prompt(
        config,
        "prompt_card_templates_format",
        "instructions.card_templates_format",
    )


def normalize_card_templates_format_prompt_for_save(text: str) -> str:
    return _normalize_prompt_for_save(text, "instructions.card_templates_format")


def effective_mathjax_preview_preamble(config: dict[str, Any] | None = None) -> str:
    return str((config or {}).get("mathjax_preview_preamble") or "").strip()


def normalize_mathjax_preview_preamble_for_save(text: str) -> str:
    return (text or "").strip()


def card_templates_format_addon(
    config: dict[str, Any] | None,
    *,
    templates: str,
    styling: str,
) -> str:
    if not templates.strip() and not styling.strip():
        return ""
    return effective_card_templates_format_prompt(config).strip()


def chat_edit_wrapper_label_text(config: dict[str, Any] | None = None) -> str:
    config = config or {}
    if import_templates_enabled(config) or import_css_enabled(config):
        return tr("chat.edit_wrapper.wrapper_label.with_optional", config=config)
    return tr("chat.edit_wrapper.wrapper_label.basic", config=config)


def chat_edit_wrapper_hint_text(config: dict[str, Any] | None = None) -> str:
    config = config or {}
    if import_templates_enabled(config) or import_css_enabled(config):
        return tr("chat.edit_wrapper.wrapper_hint.with_optional", config=config)
    return tr("chat.edit_wrapper.wrapper_hint.basic", config=config)


def chat_edit_wrapper_invalid_text(config: dict[str, Any] | None = None) -> str:
    return tr("chat.edit_wrapper.wrapper_invalid", config=config)


def wrapper_import_warning_text(
    config: dict[str, Any] | None,
    *,
    sections: list[str],
    scope: str = "settings",
) -> str:
    parts: list[str] = []
    for section in sections:
        if section == "required" and scope == "chat":
            key = "chat.wrapper_import_warning.required"
        else:
            key = f"settings.wrapper_import_warning.{section}"
        parts.append(tr(key, config=config))
    return " ".join(parts)


def _resolve_wrapper_layout(config: dict[str, Any] | None) -> tuple[list[str], dict[str, str]]:
    return effective_wrapper_layout(config)


def _resolve_format_guide(config: dict[str, Any] | None) -> str:
    return effective_card_templates_format_prompt(config).strip()


def format_chat_context_message(
    config: dict[str, Any] | None,
    *,
    context: str,
    request: str,
    templates: str = "",
    styling: str = "",
    include_context: bool = True,
    omit_format_guide: bool = False,
    section_order: list[str] | None = None,
    section_prefixes: dict[str, str] | None = None,
    format_guide: str | None = None,
    omit_sections: set[str] | None = None,
) -> str:
    return _format_chat_context_message_core(
        config,
        context=context,
        request=request,
        templates=templates,
        styling=styling,
        include_context=include_context,
        omit_format_guide=omit_format_guide,
        section_order=section_order,
        section_prefixes=section_prefixes,
        format_guide=format_guide,
        omit_sections=omit_sections,
        resolve_wrapper_layout=_resolve_wrapper_layout,
        resolve_format_guide=_resolve_format_guide,
    )


def chat_edit_templates_title_text(config: dict[str, Any] | None = None) -> str:
    templates = import_templates_enabled(config)
    css = import_css_enabled(config)
    if templates and css:
        return tr("chat.edit_templates.title", config=config)
    if css and not templates:
        return tr("chat.edit_templates.title.styling_only", config=config)
    return tr("chat.edit_templates.title.templates_only", config=config)


def chat_edit_templates_detail_text(config: dict[str, Any] | None = None) -> str:
    return tr("chat.edit_templates.detail", config=config)


def chat_edit_templates_hint_text(config: dict[str, Any] | None = None) -> str:
    templates = import_templates_enabled(config)
    css = import_css_enabled(config)
    if templates and css:
        return tr("chat.edit_templates.hint", config=config)
    if css and not templates:
        return tr("chat.edit_templates.hint.styling_only", config=config)
    return tr("chat.edit_templates.hint.templates_only", config=config)


def _builtin_system_instructions() -> frozenset[str]:
    return frozenset(
        message.strip()
        for message in (
            _STRINGS["defaults.system_instruction"][LANG_IT],
            _STRINGS["defaults.system_instruction"][LANG_EN],
        )
        if message.strip()
    )


def is_builtin_system_instruction(text: str | None) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return True
    return stripped in _builtin_system_instructions()


def effective_system_instruction(
    config: dict[str, Any] | None = None,
    *,
    purpose: str = "optimize",
) -> str:
    cfg = config or {}
    key = system_instruction_storage_key(purpose, cfg)
    stored = (cfg.get(key) or "").strip()
    if is_builtin_system_instruction(stored):
        return default_system_instruction(cfg)
    return stored


def normalize_system_instruction_for_save(text: str, config: dict[str, Any], field_key: str) -> str:
    stripped = (text or "").strip()
    if is_builtin_system_instruction(stripped):
        return ""
    return stripped


def normalize_system_instruction_fields_for_save(
    *,
    shared: bool,
    shared_text: str,
    optimize_text: str,
    chat_text: str,
    config: dict[str, Any],
) -> dict[str, str | bool]:
    if shared:
        return {
            "system_instruction_shared": True,
            "system_instruction": normalize_system_instruction_for_save(
                shared_text, config, "system_instruction"
            ),
            "system_instruction_optimize": "",
            "system_instruction_chat": "",
        }
    return {
        "system_instruction_shared": False,
        "system_instruction": "",
        "system_instruction_optimize": normalize_system_instruction_for_save(
            optimize_text, config, "system_instruction_optimize"
        ),
        "system_instruction_chat": normalize_system_instruction_for_save(
            chat_text, config, "system_instruction_chat"
        ),
    }
