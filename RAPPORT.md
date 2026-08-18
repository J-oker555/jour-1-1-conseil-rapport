# Rapport

## Phase 1 - Ouvrir la caisse

- Lignes logiques lues: 88875
- Lignes chargees: 88679
- Lignes traitees a part: 196

Les lignes mises a part sont celles dont le nombre de champs ne correspond pas aux onze champs du manifeste.

Repartition des problemes:

- 12 champs au lieu de 11: 196

Exemples:

- Ligne 877: 12 champs au lieu de 11. Extrait: `10/1/2006 12:00 |  |  |  |  | 0 |  |  | ((EDITORIAL COMMENT ABOUT THE UFO PHENOMEN))  ufo+alien+reptiles | 10/30/2006 | 0 | 0`
- Ligne 1712: 12 champs au lieu de 11. Extrait: `10/14/2004 13:00 |  |  |  |  | 0 |  |  | With all the guns in this country...why hasn&#39t anyone taken a shot at one? | 10/27/2004 | 0 | 0`
- Ligne 1814: 12 champs au lieu de 11. Extrait: `10/14/2011 22:30 |  | nv |  |  | 0 | light | 22 | 3 Green lights | 10/19/2011 | 0 | 0`

## Phase 2 - Types et anomalies

Les conversions sont appliquees sans supprimer de ligne. Les valeurs impossibles deviennent `NaN` ou `NaT`, puis sont comptees et conservees pour l'analyse.

- `datetime` -> date et heure: 1220 valeurs invalides, 0 valeurs vides. Origine probable: temoin. Exemples fautifs: ['10/10/2005 24:00', '10/11/1994 24:00', '10/11/2006 24:00', '10/11/2012 24:00', '10/1/1972 24:00', '10/1/1981 24:00', '10/1/2001 24:00', '10/1/2003 24:00', '10/1/2009 24:00', '10/1/2012 24:00']
  - Nature: heure 24:00 non parseable: 1220
- `date_posted` -> date: 0 valeurs invalides, 0 valeurs vides. Origine probable: service de transmission. Exemples fautifs: []
- `duration_seconds` -> nombre: 3 valeurs invalides, 2 valeurs vides. Origine probable: capteur. Exemples fautifs: ['2`', '8`', '0.5`']
  - Nature: caractere parasite dans un nombre: 3
  - Nature: valeur vide: 2
- `latitude` -> nombre: 1 valeurs invalides, 0 valeurs vides. Origine probable: capteur. Exemples fautifs: ['33q.200088']
  - Nature: lettre dans un nombre: 1
- `longitude` -> nombre: 0 valeurs invalides, 0 valeurs vides. Origine probable: capteur. Exemples fautifs: []

## Phase 3 - Etiquette canular

Regle: un releve est marque comme canular si le temoignage contient un mot explicite comme hoax, fake, prank, joke, joking ou balloon prank.

- Releves marques canulars: 827
- Proportion: 0.93 %

Mots declencheurs trouves:

- `hoax`: 798
- `fake`: 9
- `prank`: 2
- `joke`: 15
- `joking`: 3

Exemples de releves marques:

- `a flying colorful disc above my car&#44 near Erie. ((NUFORC Note: Possible hoax?? PD))`
- `((HOAX??)) Short encounter with space craft on my way into my parking lot area.`
- `Silver egg shape over six houses. ((NUFORC Note: Possible hoax?? PD))`
- `Lights in Irvine October 2007: Hoax`
- `((HOAX??)) abduction. 500 Lights On Object0: Yes`

Limite: Cette regle rate les canulars qui ne sont pas avoues dans le texte et peut attraper a tort un temoignage qui nie explicitement le canular.

## Phase 4 - Premier verdict

Split stratifie avec 25% des donnees en test, graine aleatoire 42. Apprentissage: 66509 releves (620 canulars, 65889 non-canulars). Test: 22170 releves (207 canulars, 21963 non-canulars).

- Sur 100 canulars reels, le systeme en attrape: 100.00
- Sur 100 releves signales, vraiment canulars: 100.00

Matrice de confusion sur le jeu de test:

| Reel \ Predit | Pas canular | Canular |
| --- | ---: | ---: |
| Pas canular | 21963 | 0 |
| Canular | 0 | 207 |

## Phase 5 - Fuite de donnees

Le premier modele utilise une information derivee du temoignage alors que l'etiquette de canular vient aussi du temoignage. Ce score n'a donc pas le droit d'etre presente comme une prediction disponible avant lecture/traitement du dossier.

| Colonne modele | Source | Qui ecrit | Quand | Savait deja si canular |
| --- | --- | --- | --- | --- |
| `duration_seconds` | `duration_seconds` | capteur | au moment du releve | non |
| `latitude` | `latitude` | capteur | au moment du releve | non |
| `longitude` | `longitude` | capteur | au moment du releve | non |
| `has_state` | `state` | service de transmission | au moment du releve | non |
| `has_country` | `country` | service de transmission | au moment du releve | non |
| `comment_length` | `comments` | temoin | apres observation | oui |
| `shape` | `shape` | temoin | au moment du releve | non |
| `country` | `country` | service de transmission | au moment du releve | non |
| `hour` | `datetime` | temoin | au moment du releve | non |
| `month` | `datetime` | temoin | au moment du releve | non |
| `comment_hoax_keyword` | `comments` | temoin | apres observation | oui |

| Mesure | Avant retrait | Apres retrait |
| --- | ---: | ---: |
| Rappel canular | 100.00 % | 61.35 % |
| Precision canular | 100.00 % | 1.40 % |
| Accuracy | 100.00 % | 59.43 % |

## Phase 6 - Modele naif

- Accuracy du stagiaire qui repond toujours `pas canular`: 99.07 %
- Accuracy du modele propre: 59.43 %
- Releves signales canular par le stagiaire: 0
- Rappel canular du stagiaire: 0.00 %
- Precision canular du stagiaire: 0.00 %

L'accuracy seule est trompeuse ici parce que les canulars sont rares. Un systeme peut obtenir un score eleve en ignorant tous les canulars. Pour defendre le modele, il faut presenter le rappel et la precision de la classe canular.

## Phase 7 - Plusieurs temoins, un seul evenement

Colonnes utilisees pour reconnaitre un meme evenement: `observation_date, city, state, country, shape`. Je regroupe donc les temoignages qui partagent le meme jour d'observation, la meme localisation normalisee et la meme forme normalisee.

- Evenements signales par plus d'un temoin: 1311
- Nombre de temoins du plus gros evenement: 26
- Releves a cheval sur les deux cotes dans la decoupe aleatoire de la phase 4: 1238
- Temoignages recopies a l'identique: 873 lignes dans 312 groupes.
- Phase 4 propre avant / apres decoupe groupee: rappel 61.35 %, precision 1.40 % -> rappel 53.21 %, precision 1.28 %

Les copies exactes ne sont pas supprimees a ce stade: elles restent des dossiers recus par le Bureau, mais le split par evenement les empeche de servir a la fois d'exemple et d'examen.

Exemple d'evenement entier, tous les temoins du meme cote:

| Date | Ville | Etat | Pays | Forme | Cote | Commentaire |
| --- | --- | --- | --- | --- | --- | --- |
| 2004-10-31 18:55:00 | tinley park | il | us | light | train | `3 BRIGHT RED LIGHTS IN TRAINGLE FORMATION SITTING STATIONARY IN THE NIGHT SKY` |
| 2004-10-31 19:00:00 | tinley park | il | us | light | train | `Three red lights return to Tinley Park&#44Il` |
| 2004-10-31 19:30:00 | tinley park | il | us | light | train | `I think this may have been man made because of the slow speed involved&#44 like driftin...` |
| 2004-10-31 19:30:00 | tinley park | il | us | light | train | `3 red lights moving slowy started in triangle and rotaed the form a spaced apart line` |
| 2004-10-31 19:30:00 | tinley park | il | us | light | train | `Three Red Lights Over Tinley Park&#44 10/31/04` |
| 2004-10-31 19:40:00 | tinley park | il | us | light | train | `Three red lights in a triangle formation moving toward the west and then moving toward ...` |
| 2004-10-31 19:45:00 | tinley park | il | us | light | train | `I reported this on august 21 about the ufo&#39s over Tinley Pk. and again&#44 they have...` |
| 2004-10-31 19:50:00 | tinley park | il | us | light | train | `Three red lights seen flying over Tinley Park&#44 IL on Halloween&#44 at least 12 witne...` |
| 2004-10-31 19:55:00 | tinley park | il | us | light | train | `3 small bright red lights evenly spaced but at a far distance moving in unison then com...` |
| 2004-10-31 20:00:00 | tinley park | il | us | light | train | `3red lights sitting still for 20 minutes then moved very slowly and vanished one after ...` |
| 2004-10-31 20:00:00 | tinley park | il | us | light | train | `3red lights sitting still for 20 minutes then moved very slowly and vanished one after ...` |
| 2004-10-31 20:00:00 | tinley park | il | us | light | train | `3 red lights movin E/SE` |

## Phase 8 - L'ordre des choses

- Date utilisee pour couper: `date_posted`.
- Justification: J'utilise la date de reception par le Bureau: elle represente le moment ou le dossier devient disponible pour apprendre, alors que l'observation peut etre declaree plus tard.
- Date de coupure: 2011-10-10
- Releves apprentissage / test: 66109 / 22570
- Proportion de canulars apprentissage / test: 0.98 % / 0.79 %
- Phase 4 apres decoupe temporelle: rappel 51.96 %, precision 1.26 %

Les proportions ne sont pas identiques: le test recent contient une densite de canulars differente, donc l'ancien split aleatoire masquait une derive temporelle.

## Phase 9 - Les cases vides

| Colonne | Trous | Canulars avec trou | Presents | Canulars sans trou |
| --- | ---: | ---: | ---: | ---: |
| `country` | 12365 | 1.17 % | 76314 | 0.89 % |
| `state` | 7409 | 1.31 % | 81270 | 0.90 % |
| `duration_hours_min` | 3017 | 2.55 % | 85662 | 0.88 % |

Traitement retenu: Les valeurs manquantes sont imputees dans le pipeline, mais chaque colonne importante garde un indicateur explicite `missing`, afin que le modele voie que la case etait vide.

## Phase 10 - La chaine de traitement du Bureau

- Proportion de canulars apprentissage / test: 0.98 % / 0.79 %
- Demonstration releve unique: un releve isole traverse `model.predict(build_corrected_features(ligne))` et ressort avec la prediction `False`.
- Phase 4 apres correction du pipeline: rappel 56.42 %, precision 1.25 %

Aucun calcul appris, comme les medianes, categories, villes frequentes ou vocabulaires, n'est calcule avant la decoupe. Ces calculs sont portes par le pipeline sklearn et ajustes sur l'apprentissage seul.

## Phase 11 - Combien de temps ca a dure

- Releves dont la duree reste inutilisable apres traitement: 6317
- Releves ou les deux colonnes de duree se contredisent: 943
- Duree mediane: 180 secondes
- Releves qui annoncent plus d'une journee d'observation: 189

Aberrations nommees:

- duree numerique nulle ou negative alors que le texte est lisible: 715
- duree numerique et texte contradictoires: 943
- duree superieure a une journee: 189

Trois durees les plus longues:

| Date | Ville | Pays | Secondes source | Duree temoin | Duree retenue |
| --- | --- | --- | ---: | --- | ---: |
| 1983-10-01 17:00:00 | birmingham (uk/england) | gb | 97836000.0 | 31 years | 97836000 |
| 2010-06-03 23:30:00 | ottawa (canada) | ca | 82800000.0 | 23000hrs | 82800000 |
| 1991-09-15 18:00:00 | greenbrier | us | 66276000.0 | 21 years | 66276000 |

Decision: Je conserve toutes les lignes, je remplace les secondes nulles par la duree lisible quand elle existe, et je plafonne les durees extremes dans le pipeline modele plutot que de les supprimer.

## Phase 12 - La ville et l'heure

- Nombre de colonnes du tableau avant / apres: 9 / 1275
- Regle appliquee aux villes: OneHotEncoder regroupe dans `infrequent` les villes vues moins de 10 fois dans l'apprentissage.
- Villes qui n'apparaissent qu'une seule fois dans toute la transmission: 14177
- Distance entre 23h et 0h dans l'encodage: 0.261
- Distance entre 23h et 20h dans l'encodage: 0.765
- `shape` avant / apres nettoyage: 29 / 26 formes.
- Modele final avec ville, heure cyclique et shape nettoyee: rappel 39.66 %, precision 1.35 %

L'heure est encodee par sinus/cosinus: 23h est bien plus proche de 0h que de 20h. Les categories rares sont apprises dans le pipeline sur l'apprentissage seul, sans utiliser la cible.

## Phase 13 - La facture du Bureau

La grille de cout est celle du Conseil: un canular laisse passer coute 30 credits, un releve honnete marque canular coute 2 credits, et les bonnes decisions coutent 0.

| Frontiere | Faux negatifs | Faux positifs | Facture |
| ---: | ---: | ---: | ---: |
| 0.50 | 108 | 5185 | 13610 |
| 0.90 | 171 | 108 | 5346 |
| 0.91 | 173 | 83 | 5356 |
| 0.92 | 173 | 57 | 5304 |
| 0.93 | 174 | 40 | 5300 |
| 0.95 | 177 | 21 | 5352 |
| 0.96 | 177 | 10 | 5330 |
| 0.97 | 178 | 2 | 5344 |
| 0.98 | 178 | 0 | 5340 |

- Frontiere par defaut: 0.50
- Facture a 0.5: 13610 credits
- Frontiere retenue: 0.93
- Facture retenue: 5300 credits
- Ecart: 8310 credits economises

La decision ne s'appuie donc pas sur un joli 0.5, mais sur la facture minimale pour le Bureau.

## Phase 14 - Une promesse a 80 %

Avant calibration:

| Tranche | Releves | Probabilite annoncee | Proportion observee |
| --- | ---: | ---: | ---: |
| [0.0; 0.1] | 6930 | 4.85 % | 0.51 % |
| [0.1; 0.2] | 1018 | 13.82 % | 1.38 % |
| [0.2; 0.3] | 1856 | 26.23 % | 0.16 % |
| [0.3; 0.4] | 3525 | 35.22 % | 0.48 % |
| [0.4; 0.5] | 3985 | 44.72 % | 0.98 % |
| [0.5; 0.6] | 2340 | 54.48 % | 1.11 % |
| [0.6; 0.7] | 1432 | 64.63 % | 1.40 % |
| [0.7; 0.8] | 868 | 74.76 % | 1.04 % |
| [0.8; 0.9] | 500 | 84.25 % | 1.60 % |
| [0.9; 1.0] | 116 | 92.87 % | 6.90 % |

Le systeme est trop confiant: les probabilites annoncees sont en moyenne au-dessus du taux observe.

Apres calibration sigmoid apprise sur l'apprentissage seul:

| Tranche | Releves | Probabilite annoncee | Proportion observee |
| --- | ---: | ---: | ---: |
| [0.0; 0.1] | 22570 | 0.95 % | 0.79 % |
| [0.1; 0.2] | 0 | 0.00 % | 0.00 % |
| [0.2; 0.3] | 0 | 0.00 % | 0.00 % |
| [0.3; 0.4] | 0 | 0.00 % | 0.00 % |
| [0.4; 0.5] | 0 | 0.00 % | 0.00 % |
| [0.5; 0.6] | 0 | 0.00 % | 0.00 % |
| [0.6; 0.7] | 0 | 0.00 % | 0.00 % |
| [0.7; 0.8] | 0 | 0.00 % | 0.00 % |
| [0.8; 0.9] | 0 | 0.00 % | 0.00 % |
| [0.9; 1.0] | 0 | 0.00 % | 0.00 % |

Les tranches restent bruitees quand elles contiennent peu de releves, mais les probabilites lues par le Conseil sont moins deconnectees de ce qui arrive vraiment.

## Phase 15 - Deux analystes, deux chiffres

- Nombre principal avec fourchette sur 10 decoupes: rappel entre 37.46 % et 48.57 %, precision entre 1.25 % et 1.66 %.
- Taille moyenne de la partie test: 22161
- Nombre moyen de canulars reels dans le test: 208
- Reponse au Conseil: Deux systemes annonces a 0.31 et 0.34 ne sont pas departageables si cet ecart reste plus petit que la largeur de la fourchette mesuree sur les decoupes.

Le chiffre nu est banni: avec aussi peu de canulars, quelques dossiers deplaces changent visiblement la mesure.

## Phase 16 - Trois dossiers sur le bureau

Explications locales:

- Dossier index `16150` (canular avec forte confiance): probabilite 98.14 %, prediction canular `True`, verite `True`. Le dossier est tire vers canular surtout par duration; les autres colonnes freinent peu la decision. Vers canular: duration (+2.12), city (+1.64), country (+0.39). Freins faibles: state (+0.07), shape (+0.07), latitude (+0.08).
- Dossier index `58955` (juste au-dessus de la frontiere): probabilite 93.07 %, prediction canular `True`, verite `True`. Le dossier est tire vers canular surtout par duration, et retenu dans l'autre sens par state. Vers canular: duration (+2.12), city (+1.64), longitude (+0.42). Contre: state (-0.68), country (-0.14), shape (-0.01).
- Dossier index `36807` (canular laisse passer): probabilite 93.00 %, prediction canular `False`, verite `True`. Le dossier est tire vers canular surtout par city, et retenu dans l'autre sens par country. Vers canular: city (+3.51), duration (+0.81), shape (+0.26). Contre: country (-0.57), longitude (-0.15), hour (-0.09).

Classement global des colonnes par permutation:

| Colonne | Chute moyenne du rappel |
| --- | ---: |
| `shape` | 0.0391 |
| `duration_missing` | 0.0358 |
| `city` | 0.0346 |
| `country` | 0.0324 |
| `longitude` | 0.0313 |
| `latitude` | 0.0112 |
| `hour_sin` | 0.0078 |
| `month` | 0.0067 |
| `country_missing` | 0.0000 |
| `latitude_missing` | 0.0000 |

La colonne dont la place me surprend le plus est `country`: elle rappelle que le modele capte aussi les habitudes de transmission, pas seulement la description physique de l'apparition.

## Phase 17 - L'angle mort du Bureau

| Zone | Releves | Proportion canulars | Rappel | Precision | Facture |
| --- | ---: | ---: | ---: | ---: | ---: |
| Global | 22570 | 0.79 % | 2.79 % | 11.11 % | 5300 |
| Etats-Unis | 19011 | 0.69 % | 1.52 % | 5.71 % | 3966 |
| Canada | 706 | 1.27 % | 0.00 % | 0.00 % | 270 |
| Europe | 247 | 4.05 % | 30.00 % | 50.00 % | 216 |
| Reste du monde | 2606 | 1.07 % | 0.00 % | 0.00 % | 848 |

Decision: Je garde une frontiere unique: hors Etats-Unis les effectifs et les canulars sont trop faibles pour apprendre une frontiere locale robuste sans fabriquer une decision instable.

L'ecart avec le global se lit surtout dans les effectifs: les Etats-Unis dominent le test, donc une moyenne globale peut cacher une zone mal mesuree ailleurs.

## Phase 18 - La transmission d'archive

Proportion de canulars par annee:

| Annee | Releves | Proportion canulars |
| ---: | ---: | ---: |
| 1998 | 982 | 0.00 % |
| 1999 | 5023 | 0.06 % |
| 2000 | 3367 | 0.03 % |
| 2001 | 3973 | 0.08 % |
| 2002 | 4758 | 0.06 % |
| 2003 | 5379 | 0.04 % |
| 2004 | 5779 | 0.07 % |
| 2005 | 5827 | 0.45 % |
| 2006 | 4891 | 1.23 % |
| 2007 | 5385 | 1.97 % |
| 2008 | 5611 | 2.83 % |
| 2009 | 6462 | 1.64 % |
| 2010 | 4867 | 1.60 % |
| 2011 | 6129 | 1.91 % |
| 2012 | 8756 | 0.55 % |
| 2013 | 8170 | 0.67 % |
| 2014 | 3320 | 1.69 % |

Epreuve ancien vers recent:

- Phase 8, decoupe temporelle de reference: rappel 51.96 %, precision 1.26 %
- Entrainement sur les releves les plus anciens, test sur les plus recents: rappel 39.66 %, precision 1.35 %

Surveillance sans connaitre la verite:

- part des releves au-dessus de la frontiere de decision
- distribution des probabilites predites par tranche
- part de pays, villes rares et champs manquants

- Frequence: revue mensuelle, avec un point hebdomadaire si le volume double
- Regle d'alerte: rappeler les analystes si un indicateur bouge de plus de 5 points de pourcentage ou de plus de 20 % relatif par rapport aux trois derniers mois

Ces indicateurs ne demandent pas l'etiquette de canular. Ils surveillent si les dossiers entrants ne ressemblent plus aux dossiers sur lesquels la decision a ete defendue.
