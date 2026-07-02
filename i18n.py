from __future__ import annotations

from typing import Any

from .constants import DEFAULT_BRAIN_IMPORT_MESSAGE

LANG_IT = "it"
LANG_EN = "en"
SUPPORTED_LANGUAGES = (LANG_IT, LANG_EN)
DEFAULT_LANGUAGE = LANG_EN

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
        "it": "Istruzioni di sistema globali (alta priorità — statiche):",
        "en": "Global system instructions (high priority — static):",
    },
    "settings.system_instruction_shared": {
        "it": "Usa le stesse istruzioni di sistema per ottimizzazione e chat",
        "en": "Use the same system instructions for optimize and chat",
    },
    "settings.system_instruction_optimize": {
        "it": "Istruzioni di sistema per l'ottimizzazione (alta priorità — statiche):",
        "en": "System instructions for optimize (high priority — static):",
    },
    "settings.system_instruction_chat": {
        "it": "Istruzioni di sistema per la chat (alta priorità — statiche):",
        "en": "System instructions for chat (high priority — static):",
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
        "it": "Ripristina avvisi",
        "en": "Restore warnings",
    },
    "settings.restore_warnings.title": {
        "it": "Ripristina avvisi ignorati",
        "en": "Restore dismissed warnings",
    },
    "settings.restore_warnings.hint": {
        "it": (
            "Seleziona gli avvisi da mostrare di nuovo. Gli avvisi attualmente ignorati "
            "sono già selezionati."
        ),
        "en": (
            "Select the warnings to show again. Currently dismissed warnings are "
            "pre-selected."
        ),
    },
    "settings.restore_warnings.apply": {
        "it": "Ripristina selezionati",
        "en": "Restore selected",
    },
    "settings.restore_warnings.none_selected": {
        "it": "Seleziona almeno un avviso da ripristinare.",
        "en": "Select at least one warning to restore.",
    },
    "settings.restore_warnings.none_dismissed": {
        "it": "Nessun avviso è attualmente ignorato.",
        "en": "No warnings are currently dismissed.",
    },
    "warnings.default_system_instruction": {
        "it": "Avviso: istruzioni di sistema predefinite non personalizzate",
        "en": "Default system instructions not customized warning",
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
        "it": (
            "Chiave API di Google AI Studio usata per chiamare Gemini. "
            "Viene salvata localmente in Anki e non viene mai inviata altrove. "
            "Puoi lasciare il campo vuoto al salvataggio per mantenere la chiave già memorizzata."
        ),
        "en": (
            "Your Google AI Studio API key used to call Gemini. "
            "It is stored locally in Anki and is not sent anywhere else. "
            "When saving, leave the field empty to keep the key already stored."
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
            "Modello Gemini usato nella <b>chat</b> (Ctrl+Alt+C) e nell'analisi note 🧠. "
            "Può essere più capace del modello di ottimizzazione, perché spesso serve "
            "ragionare e spiegare, non solo riformattare."
        ),
        "en": (
            "Gemini model used in <b>chat</b> (Ctrl+Alt+C) and note analysis 🧠. "
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
            "Quanti scambi (tu + Gemini) inviare come contesto in chat. "
            "Più storico = migliore memoria conversazionale, ma richieste più lente e costose. "
            "0 = nessuno storico (solo il messaggio corrente)."
        ),
        "en": (
            "How many exchanges (you + Gemini) to send as chat context. "
            "More history = better conversational memory, but slower and costlier requests. "
            "0 = no history (current message only)."
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
            "Testo inserito automaticamente nella chat quando importi una nota con il bottone 🧠. "
            "Puoi personalizzarlo per chiedere sempre la stessa analisi (es. atomicità, "
            "semplificazione, ecc.). Lascia il testo predefinito per usare il messaggio "
            "standard nella lingua scelta."
        ),
        "en": (
            "Text automatically inserted in chat when you import a note with the 🧠 button. "
            "Customize it to always ask the same kind of analysis (e.g. atomicity, "
            "simplification). Keep the default text to use the standard message "
            "in your selected language."
        ),
    },
    "settings.help.system_instruction": {
        "it": (
            "Istruzioni di sistema <b>statiche</b> inviate a Gemini. Con l'opzione condivisa attiva, "
            "valgono sia per l'ottimizzazione del campo sia per la chat. Definiscono stile HTML, "
            "MathJax e regole metodologiche. Hanno priorità alta rispetto alle regole dinamiche."
        ),
        "en": (
            "<b>Static</b> system instructions sent to Gemini. When shared is enabled, they apply "
            "to both field optimization and chat. They define HTML, MathJax, and methodology rules. "
            "They take priority over dynamic rules."
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
            "istruzioni statiche sopra. Puoi modificarle o cancellarle manualmente."
        ),
        "en": (
            "Rules learned via chat and saved by the add-on (e.g. when you ask Gemini to "
            "“remember globally” a preference). Lower priority than the static instructions above. "
            "You can edit or clear them manually."
        ),
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
    "defaults.system_instruction": {
        "it": (
            "Sei un assistente esperto di Anki integrato nell'editor di uno studente.\n"
            "Il tuo compito è ottimizzare, ripulire e formattare il codice HTML e MathJax fornito nel campo, "
            "applicando RIGOROSAMENTE le preferenze metodologiche, di stile e di notazione dell'utente.\n\n"
            "FORMATTAZIONE ANKI (obbligatoria):\n"
            "- I campi nota contengono solo HTML, non Markdown.\n"
            "- Matematica inline: usa solo \\(...\\).\n"
            "- Matematica display: usa solo \\[...\\].\n"
            "- Non usare mai delimitatori $...$ o $$...$$.\n"
            "- Converti matematica non formattata o in plain text in MathJax con i delimitatori sopra indicati.\n"
            "- Usa tag HTML (<b>, <i>, <ul>, <ol>, <p>, <div>) per struttura ed enfasi."
        ),
        "en": (
            "You are an expert Anki assistant integrated into a student's editor.\n"
            "Your task is to optimize, clean, and format the HTML and MathJax code provided in the field, "
            "STRICTLY applying the user's methodological, style, and notation preferences.\n\n"
            "ANKI FORMATTING (mandatory):\n"
            "- Note fields contain HTML only, not Markdown.\n"
            "- Inline math: use \\(...\\) only.\n"
            "- Display math: use \\[...\\] only.\n"
            "- Never use $...$ or $$...$$ delimiters.\n"
            "- Convert unformatted or plain-text math to MathJax using the delimiters above.\n"
            "- Use HTML tags (<b>, <i>, <ul>, <ol>, <p>, <div>) for structure and emphasis."
        ),
    },
    "instructions.optimize_output": {
        "it": (
            "\n\nOTTIMIZZAZIONE CAMPO (obbligatorio):\n"
            "- Restituisci SOLO HTML/MathJax pronto da incollare nel campo.\n"
            "- Non aggiungere spiegazioni, commenti o testo introduttivo."
        ),
        "en": (
            "\n\nFIELD OPTIMIZATION (mandatory):\n"
            "- Return ONLY HTML/MathJax ready to paste into the field.\n"
            "- Do not add explanations, comments, or introductory text."
        ),
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
        return text.format(**kwargs)
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
