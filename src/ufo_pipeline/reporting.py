from pathlib import Path

from .advanced import AdvancedResults
from .data import ConversionAnomaly, LoadResult
from .labels import HoaxLabelResult
from .modeling import BaselineMetrics, ModelMetrics


def pct(value: float) -> str:
    return f"{value * 100:.2f} %"


def _format_rejected_examples(load_result: LoadResult, limit: int = 3) -> str:
    if not load_result.rejected_records:
        return "Aucune ligne traitee a part."

    lines = []
    for record in load_result.rejected_records[:limit]:
        preview = " | ".join(record.row)
        if len(preview) > 180:
            preview = f"{preview[:177]}..."
        lines.append(f"- Ligne {record.line_number}: {record.reason}. Extrait: `{preview}`")
    return "\n".join(lines)


def _format_rejection_reasons(load_result: LoadResult) -> str:
    if not load_result.rejection_reasons:
        return "- Aucun rejet"
    return "\n".join(f"- {reason}: {count}" for reason, count in load_result.rejection_reasons.items())


def _format_conversion_anomalies(anomalies: dict[str, ConversionAnomaly]) -> str:
    lines = []
    for info in anomalies.values():
        lines.append(
            f"- `{info.column}` -> {info.target_type}: {info.invalid_count} valeurs invalides, "
            f"{info.missing_count} valeurs vides. Origine probable: {info.origin}. "
            f"Exemples fautifs: {info.examples}"
        )
        for nature, count in info.nature_counts.items():
            lines.append(f"  - Nature: {nature}: {count}")
    return "\n".join(lines)


def _format_trigger_counts(label_result: HoaxLabelResult) -> str:
    if not label_result.trigger_counts:
        return "- Aucun mot declencheur trouve"
    return "\n".join(f"- `{term}`: {count}" for term, count in label_result.trigger_counts.items())


def _format_hoax_examples(label_result: HoaxLabelResult) -> str:
    if not label_result.examples:
        return "- Aucun exemple positif"
    lines = []
    for example in label_result.examples:
        compact = " ".join(example.split())
        if len(compact) > 180:
            compact = f"{compact[:177]}..."
        lines.append(f"- `{compact}`")
    return "\n".join(lines)


def _format_evaluation_protocol(metrics: ModelMetrics) -> str:
    return (
        f"Split stratifie avec {metrics.test_fraction:.0%} des donnees en test, "
        f"graine aleatoire {metrics.random_seed}. "
        f"Apprentissage: {metrics.train_size} releves "
        f"({metrics.train_positive} canulars, {metrics.train_negative} non-canulars). "
        f"Test: {metrics.test_size} releves "
        f"({metrics.test_positive} canulars, {metrics.test_negative} non-canulars)."
    )


def _metric_pair(metrics: ModelMetrics) -> str:
    return f"rappel {pct(metrics.recall)}, precision {pct(metrics.precision)}"


def _format_missing_table(results: AdvancedResults) -> str:
    lines = [
        "| Colonne | Trous | Canulars avec trou | Presents | Canulars sans trou |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in results.phase9.columns:
        lines.append(
            f"| `{row.column}` | {row.missing_count} | {pct(row.missing_hoax_rate)} | "
            f"{row.present_count} | {pct(row.present_hoax_rate)} |"
        )
    return "\n".join(lines)


def _format_event_example(results: AdvancedResults) -> str:
    lines = [
        "| Date | Ville | Etat | Pays | Forme | Cote | Commentaire |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in results.phase7.example_event.head(12).iterrows():
        comment = " ".join(str(row["comments"]).split())
        if len(comment) > 90:
            comment = f"{comment[:87]}..."
        lines.append(
            f"| {row['datetime']} | {row['city']} | {row['state']} | {row['country']} | "
            f"{row['shape']} | {row['split']} | `{comment}` |"
        )
    return "\n".join(lines)


def _format_longest_durations(results: AdvancedResults) -> str:
    lines = [
        "| Date | Ville | Pays | Secondes source | Duree temoin | Duree retenue |",
        "| --- | --- | --- | ---: | --- | ---: |",
    ]
    for _, row in results.phase11.longest.iterrows():
        lines.append(
            f"| {row['datetime']} | {row['city']} | {row['country']} | {row['duration_seconds']} | "
            f"{row['duration_hours_min']} | {row['duration_final']:.0f} |"
        )
    return "\n".join(lines)


def _format_aberrations(results: AdvancedResults) -> str:
    return "\n".join(f"- {name}: {count}" for name, count in results.phase11.aberration_counts.items())


def render_report(
    load_result: LoadResult,
    anomalies: dict[str, ConversionAnomaly],
    label_result: HoaxLabelResult,
    leakage_rows: list[dict[str, str]],
    leaky_metrics: ModelMetrics,
    clean_metrics: ModelMetrics,
    baseline_metrics: BaselineMetrics,
    advanced: AdvancedResults,
) -> str:
    anomaly_lines = _format_conversion_anomalies(anomalies)
    leakage_lines = "\n".join(
        f"| `{row['column']}` | `{row['source']}` | {row['writer']} | {row['moment']} | {row['knows_hoax']} |"
        for row in leakage_rows
    )
    rejected_examples = _format_rejected_examples(load_result)
    rejection_reasons = _format_rejection_reasons(load_result)
    trigger_counts = _format_trigger_counts(label_result)
    hoax_examples = _format_hoax_examples(label_result)
    evaluation_protocol = _format_evaluation_protocol(leaky_metrics)

    return f"""# Rapport

## Phase 1 - Ouvrir la caisse

- Lignes logiques lues: {load_result.total_records}
- Lignes chargees: {load_result.loaded_records}
- Lignes traitees a part: {load_result.rejected_records_count}

Les lignes mises a part sont celles dont le nombre de champs ne correspond pas aux onze champs du manifeste.

Repartition des problemes:

{rejection_reasons}

Exemples:

{rejected_examples}

## Phase 2 - Types et anomalies

Les conversions sont appliquees sans supprimer de ligne. Les valeurs impossibles deviennent `NaN` ou `NaT`, puis sont comptees et conservees pour l'analyse.

{anomaly_lines}

## Phase 3 - Etiquette canular

Regle: {label_result.rule}.

- Releves marques canulars: {label_result.positive_count}
- Proportion: {pct(label_result.positive_rate)}

Mots declencheurs trouves:

{trigger_counts}

Exemples de releves marques:

{hoax_examples}

Limite: {label_result.limitation}

## Phase 4 - Premier verdict

{evaluation_protocol}

- Sur 100 canulars reels, le systeme en attrape: {leaky_metrics.recall * 100:.2f}
- Sur 100 releves signales, vraiment canulars: {leaky_metrics.precision * 100:.2f}

Matrice de confusion sur le jeu de test:

| Reel \\ Predit | Pas canular | Canular |
| --- | ---: | ---: |
| Pas canular | {leaky_metrics.true_negative} | {leaky_metrics.false_positive} |
| Canular | {leaky_metrics.false_negative} | {leaky_metrics.true_positive} |

## Phase 5 - Fuite de donnees

Le premier modele utilise une information derivee du temoignage alors que l'etiquette de canular vient aussi du temoignage. Ce score n'a donc pas le droit d'etre presente comme une prediction disponible avant lecture/traitement du dossier.

| Colonne modele | Source | Qui ecrit | Quand | Savait deja si canular |
| --- | --- | --- | --- | --- |
{leakage_lines}

| Mesure | Avant retrait | Apres retrait |
| --- | ---: | ---: |
| Rappel canular | {pct(leaky_metrics.recall)} | {pct(clean_metrics.recall)} |
| Precision canular | {pct(leaky_metrics.precision)} | {pct(clean_metrics.precision)} |
| Accuracy | {pct(leaky_metrics.accuracy)} | {pct(clean_metrics.accuracy)} |

## Phase 6 - Modele naif

- Accuracy du stagiaire qui repond toujours `pas canular`: {pct(baseline_metrics.accuracy)}
- Accuracy du modele propre: {pct(clean_metrics.accuracy)}
- Releves signales canular par le stagiaire: {baseline_metrics.predicted_positive}
- Rappel canular du stagiaire: {pct(baseline_metrics.recall)}
- Precision canular du stagiaire: {pct(baseline_metrics.precision)}

L'accuracy seule est trompeuse ici parce que les canulars sont rares. Un systeme peut obtenir un score eleve en ignorant tous les canulars. Pour defendre le modele, il faut presenter le rappel et la precision de la classe canular.

## Phase 7 - Plusieurs temoins, un seul evenement

Colonnes utilisees pour reconnaitre un meme evenement: `{', '.join(advanced.phase7.event_columns)}`. Je regroupe donc les temoignages qui partagent le meme jour d'observation, la meme localisation normalisee et la meme forme normalisee.

- Evenements signales par plus d'un temoin: {advanced.phase7.multi_witness_events}
- Nombre de temoins du plus gros evenement: {advanced.phase7.largest_witness_count}
- Releves a cheval sur les deux cotes dans la decoupe aleatoire de la phase 4: {advanced.phase7.old_split_leaking_records}
- Temoignages recopies a l'identique: {advanced.phase7.duplicate_comment_rows} lignes dans {advanced.phase7.duplicate_comment_groups} groupes.
- Phase 4 propre avant / apres decoupe groupee: {_metric_pair(clean_metrics)} -> {_metric_pair(advanced.phase7.grouped_metrics)}

Les copies exactes ne sont pas supprimees a ce stade: elles restent des dossiers recus par le Bureau, mais le split par evenement les empeche de servir a la fois d'exemple et d'examen.

Exemple d'evenement entier, tous les temoins du meme cote:

{_format_event_example(advanced)}

## Phase 8 - L'ordre des choses

- Date utilisee pour couper: `{advanced.phase8.cut_column}`.
- Justification: {advanced.phase8.cut_reason}
- Date de coupure: {advanced.phase8.cut_date.date()}
- Releves apprentissage / test: {advanced.phase8.train_size} / {advanced.phase8.test_size}
- Proportion de canulars apprentissage / test: {pct(advanced.phase8.train_hoax_rate)} / {pct(advanced.phase8.test_hoax_rate)}
- Phase 4 apres decoupe temporelle: {_metric_pair(advanced.phase8.temporal_metrics)}

Les proportions ne sont pas identiques: le test recent contient une densite de canulars differente, donc l'ancien split aleatoire masquait une derive temporelle.

## Phase 9 - Les cases vides

{_format_missing_table(advanced)}

Traitement retenu: {advanced.phase9.treatment}

## Phase 10 - La chaine de traitement du Bureau

- Proportion de canulars apprentissage / test: {pct(advanced.phase10.train_hoax_rate)} / {pct(advanced.phase10.test_hoax_rate)}
- Demonstration releve unique: un releve isole traverse `model.predict(build_corrected_features(ligne))` et ressort avec la prediction `{advanced.phase10.single_prediction}`.
- Phase 4 apres correction du pipeline: {_metric_pair(advanced.phase10.corrected_metrics)}

Aucun calcul appris, comme les medianes, categories, villes frequentes ou vocabulaires, n'est calcule avant la decoupe. Ces calculs sont portes par le pipeline sklearn et ajustes sur l'apprentissage seul.

## Phase 11 - Combien de temps ca a dure

- Releves dont la duree reste inutilisable apres traitement: {advanced.phase11.unusable_count}
- Releves ou les deux colonnes de duree se contredisent: {advanced.phase11.contradiction_count}
- Duree mediane: {advanced.phase11.median_seconds:.0f} secondes
- Releves qui annoncent plus d'une journee d'observation: {advanced.phase11.over_one_day_count}

Aberrations nommees:

{_format_aberrations(advanced)}

Trois durees les plus longues:

{_format_longest_durations(advanced)}

Decision: {advanced.phase11.decision}

## Phase 12 - La ville et l'heure

- Nombre de colonnes du tableau avant / apres: {advanced.phase12.width_before} / {advanced.phase12.width_after}
- Regle appliquee aux villes: {advanced.phase12.city_rule}
- Villes qui n'apparaissent qu'une seule fois dans toute la transmission: {advanced.phase12.singleton_cities}
- Distance entre 23h et 0h dans l'encodage: {advanced.phase12.distance_23_0:.3f}
- Distance entre 23h et 20h dans l'encodage: {advanced.phase12.distance_23_20:.3f}
- `shape` avant / apres nettoyage: {advanced.phase12.shape_count_before} / {advanced.phase12.shape_count_after} formes.
- Modele final avec ville, heure cyclique et shape nettoyee: {_metric_pair(advanced.phase12.final_metrics)}

L'heure est encodee par sinus/cosinus: 23h est bien plus proche de 0h que de 20h. Les categories rares sont apprises dans le pipeline sur l'apprentissage seul, sans utiliser la cible.
"""


def write_report(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")

