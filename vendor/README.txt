Dipendenze incluse (vendoring)
==============================

Questo add-on include una copia locale della libreria Python "markdown"
(per formattare le risposte nella chat Gemini).

Versione attuale: 3.10.x (cartella vendor/markdown/)

Perché è qui
------------
Anki non gestisce dipendenze PyPI tra add-on. Includere markdown in vendor/
garantisce che la chat funzioni anche senza installazioni extra.

Conflitti con altri add-on
--------------------------
Se un altro add-on carica anch'esso "markdown", Python ne tiene una sola copia
in memoria. L'add-on Anki AI Assistant:

1. carica markdown solo quando serve (prima risposta chat da formattare);
2. preferisce la copia in vendor/ di questo add-on;
3. se non disponibile, usa una versione già in memoria (>= 3.0);
4. altrimenti usa formattazione semplificata (senza crash).

Aggiornare markdown
-------------------
Da terminale, nella cartella dell'add-on:

  py -m pip install markdown --target vendor --upgrade

Poi eliminare eventuali cartelle .dist-info vecchie se duplicate.
