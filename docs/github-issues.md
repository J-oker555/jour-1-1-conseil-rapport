# Issues GitHub a creer

## 1. Phase 7 - Regrouper les temoins d'un meme evenement

Identifier les colonnes qui definissent un evenement, compter les evenements multi-temoins, mesurer l'ancienne fuite train/test, refaire une decoupe groupee et traiter les doublons textuels exacts.

## 2. Phase 8 - Remplacer la decoupe aleatoire par une decoupe temporelle

Choisir la date de coupure defendable, garantir que l'apprentissage precede le test, comparer les proportions de canulars et refaire les deux metriques de la phase 4.

## 3. Phase 9 - Traiter les valeurs manquantes sans effacer leur signal

Trouver les trois colonnes les plus trouees, comparer les proportions de canulars avec/sans trou, puis ajouter un traitement qui conserve des indicateurs de manque.

## 4. Phase 10 - Construire un pipeline sans fuite de donnees

Deplacer tout apprentissage de moyenne, mediane, categories et vocabulaire apres la decoupe. Fournir une prediction en un seul appel pour un releve neuf.

## 5. Phase 11 - Reconstruire et controler les durees

Exploiter les deux colonnes de duree, compter les contradictions, conserver toutes les lignes, nommer au moins deux aberrations et decider du traitement des durees extremes.

## 6. Phase 12 - Encoder ville, heure et shape proprement

Ajouter ville et heure sans explosion de colonnes, encoder l'heure cycliquement, regrouper les villes rares, nettoyer `shape` et annoncer la largeur finale du tableau.

## 7. Validation finale - Rapport, tests et execution d'une traite

Executer `analyse.py` du chargement au dernier nombre, completer `RAPPORT.md`, lancer les tests et pousser seulement apres validation locale.

