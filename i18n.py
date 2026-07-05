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
    "settings.advanced": {
        "it": "Avanzate…",
        "en": "Advanced…",
    },
    "settings.advanced.title": {
        "it": "Prompt avanzati",
        "en": "Advanced prompts",
    },
    "settings.advanced.hint": {
        "it": (
            "Testi aggiuntivi inviati a Gemini. Modifica solo se sai cosa stai facendo. "
            "Ripristina i valori predefiniti da Impostazioni → Ripristina predefiniti."
        ),
        "en": (
            "Extra text sent to Gemini. Edit only if you know what you are doing. "
            "Restore defaults from Settings → Restore defaults."
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
        "it": "Istruzioni aggiuntive di sistema (chat)",
        "en": "Extra system instructions (chat)",
    },
    "settings.prompt_chat_addon.hint": {
        "it": (
            "Appeso alle istruzioni di sistema in chat: formattazione risposte, blocchi code per i campi, "
            "regole dinamiche (<UPDATE_DYNAMIC_RULES>), ecc."
        ),
        "en": (
            "Appended to chat system instructions: reply formatting, field code blocks, "
            "dynamic rules (<UPDATE_DYNAMIC_RULES>), etc."
        ),
    },
    "settings.prompt_dynamic_rules_prefix": {
        "it": "Prefisso regole dinamiche (sistema)",
        "en": "Dynamic rules prefix (system)",
    },
    "settings.prompt_dynamic_rules_prefix.hint": {
        "it": (
            "Inserito prima del testo delle regole dinamiche quando non è vuoto. "
            "Deve terminare con un a capo."
        ),
        "en": (
            "Inserted before your dynamic rules text when that field is not empty. "
            "Should end with a newline."
        ),
    },
    "settings.prompt_chat_context": {
        "it": "Wrapper contesto nota (chat)",
        "en": "Note context wrapper (chat)",
    },
    "settings.prompt_chat_context.hint": {
        "it": (
            "Usato quando invii in chat con «Includi contesto nota» dopo l'import 🧠. "
            "Segnaposto obbligatori: {context} (campi nota), {request} (tuo messaggio)."
        ),
        "en": (
            "Used when you send chat with “include note context” after 🧠 import. "
            "Required placeholders: {context} (note fields), {request} (your message)."
        ),
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
            "Ripristina gli avvisi ignorati o attiva quelli nuovi. Gli avvisi attualmente "
            "ignorati sono già selezionati."
        ),
        "en": (
            "Restore dismissed warnings or activate new ones. Currently dismissed warnings "
            "are pre-selected."
        ),
    },
    "settings.warnings.hint": {
        "it": (
            "Ripristina gli avvisi ignorati o attiva quelli nuovi. Gli avvisi attualmente "
            "ignorati sono già selezionati."
        ),
        "en": (
            "Restore dismissed warnings or activate new ones. Currently dismissed warnings "
            "are pre-selected."
        ),
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
    "settings.help.prompts_overview.title": {
        "it": "Come vengono costruiti i prompt",
        "en": "How prompts are built",
    },
    "settings.help.prompts_overview": {
        "it": (
            "L'add-on invia a Gemini un <b>prompt di sistema</b> e uno o più <b>messaggi utente</b>. "
            "Quasi tutto il testo è modificabile nelle Impostazioni (e quattro blocchi in <b>Avanzate…</b>). "
            "I pezzi vengono concatenati nell'ordine sotto — non vengono aggiunti spazi o a capo automatici "
            "tra un blocco e l'altro, salvo dove indicato.<br><br>"
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
            "3. <b>Istruzioni aggiuntive di sistema (chat)</b> — Avanzate "
            "(formattazione risposte, blocchi code, tag &lt;UPDATE_DYNAMIC_RULES&gt;, ecc.)<br><br>"
            "<b>Messaggi utente</b> (con storico fino a «Storico chat (turni)»):<br>"
            "• Di solito: solo ciò che scrivi nella chat<br>"
            "• Con «Includi contesto nota» dopo import 🧠: "
            "<b>wrapper contesto nota</b> (Avanzate, o «Modifica wrapper» nella chat) con segnaposto "
            "<code>{context}</code> (campi nota) e <code>{request}</code> (tuo messaggio). "
            "I campi in <code>{context}</code> provengono dall'anteprima modificabile sopra la chat; "
            "ogni campo è formattato come "
            "<code>Campo [Nome]:</code> + HTML grezzo.<br>"
            "Se il wrapper personalizzato omette un segnaposto, si usa il modello predefinito.<br><br>"
            "<b>Non inviato a Gemini</b>: messaggio di benvenuto, "
            "nome del campo nel messaggio normale.<br><br>"
            "<b>Messaggio import 🧠</b>: precompila la casella di input; i campi nota compaiono "
            "nell'anteprima sopra la chat (modificabile). Il messaggio viene inviato come messaggio "
            "utente normale (eventualmente avvolto dal wrapper contesto).<br><br>"
            "<b>Prefisso regole dinamiche</b>: il predefinito inizia con due a capo (<code>\\n\\n</code>) "
            "e termina con uno. In un prefisso personalizzato, includi tu stesso gli a capo "
            "prima/dopo il testo, altrimenti il blocco si attacca a quello precedente."
        ),
        "en": (
            "The add-on sends Gemini a <b>system prompt</b> and one or more <b>user messages</b>. "
            "Almost all text is editable in Settings (plus four blocks under <b>Advanced…</b>). "
            "Pieces are concatenated in the order below — the add-on does not insert extra spaces "
            "or line breaks between blocks unless noted.<br><br>"
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
            "3. <b>Extra system instructions (chat)</b> — Advanced "
            "(reply formatting, code blocks, &lt;UPDATE_DYNAMIC_RULES&gt; tags, etc.)<br><br>"
            "<b>User messages</b> (with history up to “Chat history (turns)”):<br>"
            "• Usually: only what you type in chat<br>"
            "• With “include note context” after 🧠 import: "
            "<b>note context wrapper</b> (Advanced, or <b>Edit wrapper</b> in chat) with placeholders "
            "<code>{context}</code> (note fields) and <code>{request}</code> (your message). "
            "Fields in <code>{context}</code> come from the editable preview above the chat; "
            "each field is formatted as "
            "<code>Field [Name]:</code> + raw HTML.<br>"
            "If a custom wrapper omits a placeholder, the default template is used.<br><br>"
            "<b>Not sent to Gemini</b>: welcome message, "
            "field name in a normal message.<br><br>"
            "<b>🧠 import message</b>: pre-fills the input box; note fields appear in the "
            "editable preview above the chat. The message is sent as a normal user message "
            "(optionally wrapped by the note context wrapper).<br><br>"
            "<b>Dynamic rules prefix</b>: the default starts with two line breaks (<code>\\n\\n</code>) "
            "and ends with one. In a custom prefix, include line breaks before/after your text yourself, "
            "or the block will run into the text above or below."
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
        "it": (
            "Blocco aggiuntivo appeso alle istruzioni di sistema durante la chat "
            "(formattazione risposte, blocchi code, regole dinamiche). "
            "Modificabile in <b>Avanzate…</b>."
        ),
        "en": (
            "Extra block appended to chat system instructions "
            "(reply formatting, code blocks, dynamic rules). "
            "Editable under <b>Advanced…</b>."
        ),
    },
    "settings.help.prompt_dynamic_rules_prefix": {
        "it": (
            "Intestazione inserita prima del testo delle regole dinamiche nel prompt di sistema "
            "(solo se le regole dinamiche non sono vuote). Modificabile in <b>Avanzate…</b>. "
            "Includi tu gli a capo nel testo personalizzato; vedi <b>Come vengono costruiti i prompt</b>."
        ),
        "en": (
            "Header inserted before your dynamic rules text in the system prompt "
            "(only when dynamic rules are not empty). Editable under <b>Advanced…</b>. "
            "Include line breaks in custom text yourself; see <b>How prompts are built</b>."
        ),
    },
    "settings.help.prompt_chat_context": {
        "it": (
            "Modello del messaggio utente quando invii in chat con «Includi contesto nota» dopo import 🧠. "
            "Segnaposto: <code>{context}</code>, <code>{request}</code>. "
            "Modificabile in <b>Avanzate…</b> o temporaneamente con «Modifica wrapper» nella chat "
            "(i campi nota si modificano nell'anteprima sopra la chat)."
        ),
        "en": (
            "User message template when you send chat with “include note context” after 🧠 import. "
            "Placeholders: <code>{context}</code>, <code>{request}</code>. "
            "Editable under <b>Advanced…</b> or temporarily via <b>Edit wrapper</b> in chat "
            "(note fields are edited in the preview above the chat)."
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
            "Testo inserito automaticamente nella casella di input quando importi una nota con il bottone 🧠. "
            "I campi nota compaiono nell'anteprima modificabile sopra la chat. "
            "Puoi personalizzare il messaggio per chiedere sempre la stessa analisi (es. atomicità, "
            "semplificazione, ecc.). Lascia il testo predefinito per usare il messaggio "
            "standard nella lingua scelta."
        ),
        "en": (
            "Text automatically inserted in the input box when you import a note with the 🧠 button. "
            "Note fields appear in the editable preview above the chat. "
            "Customize the message to always ask the same kind of analysis (e.g. atomicity, "
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
    "chat.edit_context": {
        "it": "Modifica wrapper",
        "en": "Edit wrapper",
    },
    "chat.edit_wrapper": {
        "it": "Modifica wrapper",
        "en": "Edit wrapper",
    },
    "chat.edit_wrapper.wrapper_label": {
        "it": "Testo wrapper ({context}, {request}):",
        "en": "Wrapper text ({context}, {request}):",
    },
    "chat.edit_wrapper.wrapper_hint": {
        "it": "Il tuo messaggio in basso sostituisce {request}.",
        "en": "Your message below replaces {request}.",
    },
    "chat.edit_wrapper.wrapper_invalid": {
        "it": "Formato wrapper errato. Ripristino predefiniti.",
        "en": "The wrapper format is wrong. Reverting to defaults.",
    },
    "chat.edit_context.fields_label": {
        "it": "Campi nota (modificabili nell'anteprima sopra la chat):",
        "en": "Note fields (editable in the preview above the chat):",
    },
    "chat.edit_context.note_label": {
        "it": "Contenuto nota inviato come {context} (modificabile nell'anteprima):",
        "en": "Note content sent as {context} (editable in the preview):",
    },
    "chat.edit_context.wrapper_label": {
        "it": "Testo wrapper ({context}, {request}):",
        "en": "Wrapper text ({context}, {request}):",
    },
    "chat.edit_context.wrapper_hint": {
        "it": "Il tuo messaggio in basso sostituisce {request}.",
        "en": "Your message below replaces {request}.",
    },
    "chat.edit_context.wrapper_invalid": {
        "it": "Formato wrapper errato. Ripristino predefiniti.",
        "en": "The wrapper format is wrong. Reverting to defaults.",
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
        "it": "Apri l'anteprima della nota importata in una finestra separata",
        "en": "Open the imported note preview in a separate window",
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
    "chat.stopping": {
        "it": "⏹️ Interruzione in corso.",
        "en": "⏹️ Stopping.",
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
    "instructions.chat_context_wrapper": {
        "it": (
            "[CONTESTO DELLA NOTA INTERA DA ANALIZZARE]:\n{context}\n\n[RICHIESTA DELLO STUDENTE]:\n{request}"
        ),
        "en": (
            "[FULL NOTE CONTEXT TO ANALYZE]:\n{context}\n\n[STUDENT REQUEST]:\n{request}"
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
            "\n\nREGOLE DINAMICHE AGGIUNTIVE PRECEDENTEMENTE MEMORIZZATE "
            "(Priorità inferiore rispetto alle regole sopra):\n"
        ),
        "en": (
            "\n\nADDITIONAL DYNAMIC RULES PREVIOUSLY STORED "
            "(Lower priority than the rules above):\n"
        ),
    },
    "instructions.chat_system_addon": {
        "it": (
            "\nREGOLE DI FORMATTAZIONE PER LE RISPOSTE IN CHAT:\n"
            "- Per il testo esplicativo usa Markdown standard direttamente nel messaggio: **grassetto**, *corsivo*, `codice inline`, titoli con ##, elenchi, tabelle, separatori ---.\n"
            "- NON racchiudere l'intera risposta in un unico blocco ```markdown: scrivi il Markdown nel testo normale.\n"
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
            "\nCHAT REPLY FORMATTING RULES:\n"
            "- For explanatory text use standard Markdown in the message: **bold**, *italic*, `inline code`, ## headings, lists, tables, --- separators.\n"
            "- Do NOT wrap the entire reply in one ```markdown block; write Markdown as normal text.\n"
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
        "it": "API Key non valida o non autorizzata. Controlla la chiave nelle impostazioni (⚙️).",
        "en": "Invalid or unauthorized API key. Check the key in settings (⚙️).",
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


def default_chat_context_wrapper(config: dict[str, Any] | None = None) -> str:
    return tr("instructions.chat_context_wrapper", config=config)


def is_builtin_chat_context_wrapper(text: str | None) -> bool:
    return _is_builtin_prompt(text, "instructions.chat_context_wrapper")


def effective_chat_context_wrapper(config: dict[str, Any] | None = None) -> str:
    return _effective_prompt(config, "prompt_chat_context", "instructions.chat_context_wrapper")


def normalize_chat_context_wrapper_for_save(text: str) -> str:
    return _normalize_prompt_for_save(text, "instructions.chat_context_wrapper")


def chat_context_wrapper_missing_placeholders(text: str | None) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    return "{context}" not in stripped or "{request}" not in stripped


def format_chat_context_message(
    config: dict[str, Any] | None,
    *,
    context: str,
    request: str,
    template: str | None = None,
) -> str:
    resolved = (template or "").strip() or effective_chat_context_wrapper(config)
    if "{context}" not in resolved or "{request}" not in resolved:
        resolved = default_chat_context_wrapper(config)
    return resolved.format(context=context, request=request)


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
