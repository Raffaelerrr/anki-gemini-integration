DEFAULT_BRAIN_IMPORT_MESSAGE = (
    "La nota qui sopra andrebbe scomposta in più note secondo il principio di atomicità? Se sì, come?"
)

CHAT_FORMAT_INSTRUCTION = """
REGOLE DI FORMATTAZIONE PER LE RISPOSTE IN CHAT:
- Per il testo esplicativo usa Markdown standard direttamente nel messaggio: **grassetto**, *corsivo*, `codice inline`, titoli con ##, elenchi, tabelle, separatori ---.
- NON racchiudere l'intera risposta in un unico blocco ```markdown: scrivi il Markdown nel testo normale.
- Quando proponi contenuto da incollare in un campo Anki, scrivi il NOME DEL CAMPO sulla riga immediatamente sopra il blocco code, seguito da due punti. Poi apri un blocco code con tre backtick.
- Esempio (ripeti per ogni campo):

Front:
```
(contenuto HTML/MathJax grezzo, pronto per essere incollato nel campo Front)
```

Back:
```
(contenuto HTML/MathJax grezzo)
```

Shared front:
```
(contenuto HTML/MathJax grezzo)
```

- Il nome del campo va FUORI dal blocco code, mai dentro.
- Dentro ogni blocco code metti SOLO ciò che va incollato nel campo: niente spiegazioni, niente Markdown (usa tag HTML <b>, <i> per grassetto/corsivo nei campi).
- Nei campi Anki, usa \\(...\\) per matematica inline e \\[...\\] per display; non usare $...$ o $$...$$.
- Ogni blocco code avrà un pulsante Copia: l'utente decide cosa incollare in Anki.
- I blocchi code possono anche servire per esempi non legati a un campo; in quel caso non mettere un nome campo sulla riga sopra.
"""

META_RULE_DYNAMIC = (
    "\n\n[META-REGOLA DI SISTEMA]: Se l'utente ti chiede esplicitamente di memorizzare, ricordare, "
    "salvare o aggiungere una nuova regola globalmente o per il futuro, accetta la richiesta e includi "
    "TASSATIVAMENTE in fondo alla tua risposta l'elenco completo e aggiornato di TUTTE le regole dinamiche "
    "all'interno dei tag <UPDATE_DYNAMIC_RULES> e </UPDATE_DYNAMIC_RULES>. Includi sia le vecchie regole che la nuova."
)

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_MODEL_OPTIMIZE = "gemini-2.5-flash-lite"
DEFAULT_MODEL_CHAT = "gemini-2.5-flash"
DEFAULT_THINKING_BUDGET_OPTIMIZE = 0
DEFAULT_THINKING_BUDGET_CHAT = -1
GEMINI_API_HOST = "generativelanguage.googleapis.com"
GEMINI_API_PATH = "/v1beta/models/{model}:generateContent"
GEMINI_STREAM_API_PATH = "/v1beta/models/{model}:streamGenerateContent"
GEMINI_MODELS_LIST_PATH = "/v1beta/models"

# Stable / common Gemini text models, newest first; lite before flash before pro.
GEMINI_MODEL_CHOICES: tuple[str, ...] = (
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
)
