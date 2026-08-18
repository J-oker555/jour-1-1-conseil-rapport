# Le Conseil renvoie le rapport

Projet d'analyse pour les phases 7 a 12 de l'enonce `partie1-2_le_conseil_renvoie_le_rapport.pdf`.

## Objectif

Reprendre l'analyse de detection des canulars en supprimant les fuites methodologiques signalees par le Conseil :

- plusieurs temoins pour un meme evenement ;
- decoupe temporelle ;
- valeurs manquantes sans effacer leur trace ;
- pipeline appris uniquement sur l'apprentissage ;
- durees reconstruites sans supprimer de lignes ;
- encodage raisonnable de la ville, de l'heure et de `shape`.

## Commandes

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe analyse.py
```

Quand les donnees seront disponibles :

```powershell
.\.venv\Scripts\python.exe analyse.py
```

## Structure

- `analyse.py` : point d'entree unique demande par l'enonce, du telechargement au rapport.
- `src/ufo_pipeline/` : fonctions reutilisables pour charger, decouper, transformer et evaluer.
- `src/bat/` : premiers garde-fous conserves pendant l'initialisation.
- `RAPPORT.md` : rapport humain, phase par phase, avec les nombres avant/apres.
- `docs/github-issues.md` : issues a creer sur GitHub.
- `tests/` : tests concentres sur les regles qui evitent les fuites.
