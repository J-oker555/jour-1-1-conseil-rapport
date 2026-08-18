from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.inspection import permutation_importance
from sklearn.metrics import precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit

from .advanced import (
    add_city_hour_shape_features,
    build_duration,
    make_event_ids,
    temporal_split_indices,
)
from .modeling import build_model, train_and_evaluate_indices

FALSE_NEGATIVE_COST = 30
FALSE_POSITIVE_COST = 2


@dataclass(frozen=True)
class FinalModelRun:
    features: pd.DataFrame
    target: pd.Series
    train_index: pd.Index
    test_index: pd.Index
    model: object
    probabilities: np.ndarray
    predictions: np.ndarray


@dataclass(frozen=True)
class CostRow:
    threshold: float
    false_negatives: int
    false_positives: int
    cost: int


@dataclass(frozen=True)
class Phase13Result:
    rows: list[CostRow]
    best_threshold: float
    default_threshold: float
    default_cost: int
    best_cost: int
    saved_credits: int


@dataclass(frozen=True)
class CalibrationRow:
    lower: float
    upper: float
    count: int
    mean_probability: float
    observed_rate: float


@dataclass(frozen=True)
class Phase14Result:
    before: list[CalibrationRow]
    after: list[CalibrationRow]
    error_direction: str
    calibrated_probabilities: np.ndarray


@dataclass(frozen=True)
class IntervalResult:
    recall_low: float
    recall_high: float
    precision_low: float
    precision_high: float
    split_count: int
    test_size: int
    test_hoax_count: int
    answer: str


@dataclass(frozen=True)
class LocalExplanation:
    index: int
    kind: str
    probability: float
    predicted_hoax: bool
    actual_hoax: bool
    top_for_hoax: list[tuple[str, float]]
    top_against_hoax: list[tuple[str, float]]
    summary: str


@dataclass(frozen=True)
class Phase16Result:
    cases: list[LocalExplanation]
    global_importance: list[tuple[str, float]]
    surprising_column: str


@dataclass(frozen=True)
class ZoneRow:
    zone: str
    count: int
    hoax_rate: float
    recall: float
    precision: float
    cost: int


@dataclass(frozen=True)
class Phase17Result:
    rows: list[ZoneRow]
    global_row: ZoneRow
    decision: str


@dataclass(frozen=True)
class YearRow:
    year: int
    count: int
    hoax_rate: float


@dataclass(frozen=True)
class Phase18Result:
    yearly_rates: list[YearRow]
    old_to_recent_recall: float
    old_to_recent_precision: float
    phase8_recall: float
    phase8_precision: float
    monitoring_indicators: list[str]
    monitoring_frequency: str
    alert_rule: str


@dataclass(frozen=True)
class DecisionResults:
    phase13: Phase13Result
    phase14: Phase14Result
    phase15: IntervalResult
    phase16: Phase16Result
    phase17: Phase17Result
    phase18: Phase18Result


def fit_final_model(frame: pd.DataFrame, target: pd.Series) -> FinalModelRun:
    duration = build_duration(frame).clip(upper=86400)
    features = add_city_hour_shape_features(frame, duration)
    train_index, test_index, _ = temporal_split_indices(frame)
    model = build_model(features, min_category_frequency=10)
    model.fit(features.loc[train_index], target.loc[train_index])
    probabilities = model.predict_proba(features.loc[test_index])[:, 1]
    predictions = probabilities >= 0.5
    return FinalModelRun(
        features=features,
        target=target,
        train_index=train_index,
        test_index=test_index,
        model=model,
        probabilities=probabilities,
        predictions=predictions,
    )


def decision_cost(y_true: pd.Series, probabilities: np.ndarray, threshold: float) -> CostRow:
    predicted = probabilities >= threshold
    y_bool = y_true.astype(bool).to_numpy()
    false_negatives = int((y_bool & ~predicted).sum())
    false_positives = int((~y_bool & predicted).sum())
    cost = false_negatives * FALSE_NEGATIVE_COST + false_positives * FALSE_POSITIVE_COST
    return CostRow(
        threshold=threshold,
        false_negatives=false_negatives,
        false_positives=false_positives,
        cost=cost,
    )


def phase13(run: FinalModelRun) -> Phase13Result:
    y_test = run.target.loc[run.test_index]
    thresholds = np.round(np.linspace(0.0, 1.0, 101), 2)
    rows = [decision_cost(y_test, run.probabilities, float(threshold)) for threshold in thresholds]
    best = min(rows, key=lambda row: (row.cost, -row.threshold))
    default = decision_cost(y_test, run.probabilities, 0.5)
    display = sorted(rows, key=lambda row: row.cost)[:8]
    if default not in display:
        display.append(default)
    return Phase13Result(
        rows=sorted(display, key=lambda row: row.threshold),
        best_threshold=best.threshold,
        default_threshold=0.5,
        default_cost=default.cost,
        best_cost=best.cost,
        saved_credits=default.cost - best.cost,
    )


def calibration_table(y_true: pd.Series, probabilities: np.ndarray, bins: int = 10) -> list[CalibrationRow]:
    labels = y_true.astype(bool).to_numpy()
    rows: list[CalibrationRow] = []
    edges = np.linspace(0.0, 1.0, bins + 1)
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        if upper == 1.0:
            mask = (probabilities >= lower) & (probabilities <= upper)
        else:
            mask = (probabilities >= lower) & (probabilities < upper)
        count = int(mask.sum())
        if count:
            mean_probability = float(probabilities[mask].mean())
            observed_rate = float(labels[mask].mean())
        else:
            mean_probability = 0.0
            observed_rate = 0.0
        rows.append(
            CalibrationRow(
                lower=float(lower),
                upper=float(upper),
                count=count,
                mean_probability=mean_probability,
                observed_rate=observed_rate,
            )
        )
    return rows


def phase14(run: FinalModelRun) -> Phase14Result:
    y_train = run.target.loc[run.train_index]
    y_test = run.target.loc[run.test_index]
    calibrated = CalibratedClassifierCV(
        estimator=build_model(run.features, min_category_frequency=10),
        method="sigmoid",
        cv=3,
    )
    calibrated.fit(run.features.loc[run.train_index], y_train)
    calibrated_probabilities = calibrated.predict_proba(run.features.loc[run.test_index])[:, 1]
    before = calibration_table(y_test, run.probabilities)
    after = calibration_table(y_test, calibrated_probabilities)
    weighted_gap = sum(
        row.count * (row.mean_probability - row.observed_rate)
        for row in before
    ) / max(1, sum(row.count for row in before))
    if weighted_gap > 0.01:
        direction = "trop confiant: les probabilites annoncees sont en moyenne au-dessus du taux observe"
    elif weighted_gap < -0.01:
        direction = "trop prudent: les probabilites annoncees sont en moyenne sous le taux observe"
    else:
        direction = "globalement proche, mais certaines tranches restent bruitees"
    return Phase14Result(
        before=before,
        after=after,
        error_direction=direction,
        calibrated_probabilities=calibrated_probabilities,
    )


def phase15(frame: pd.DataFrame, target: pd.Series, split_count: int = 10) -> IntervalResult:
    duration = build_duration(frame).clip(upper=86400)
    features = add_city_hour_shape_features(frame, duration)
    groups = make_event_ids(frame)
    recalls: list[float] = []
    precisions: list[float] = []
    test_sizes: list[int] = []
    test_hoaxes: list[int] = []
    splitter = GroupShuffleSplit(n_splits=split_count, test_size=0.25, random_state=2026)
    for train_pos, test_pos in splitter.split(features, target, groups=groups):
        train_index = features.index[train_pos]
        test_index = features.index[test_pos]
        metrics, _ = train_and_evaluate_indices(
            features,
            target,
            train_index,
            test_index,
            min_category_frequency=10,
        )
        recalls.append(metrics.recall)
        precisions.append(metrics.precision)
        test_sizes.append(metrics.test_size)
        test_hoaxes.append(metrics.test_positive)
    recall_low, recall_high = np.percentile(recalls, [5, 95])
    precision_low, precision_high = np.percentile(precisions, [5, 95])
    answer = (
        "Deux systemes annonces a 0.31 et 0.34 ne sont pas departageables si cet ecart "
        "reste plus petit que la largeur de la fourchette mesuree sur les decoupes."
    )
    return IntervalResult(
        recall_low=float(recall_low),
        recall_high=float(recall_high),
        precision_low=float(precision_low),
        precision_high=float(precision_high),
        split_count=split_count,
        test_size=int(round(float(np.mean(test_sizes)))),
        test_hoax_count=int(round(float(np.mean(test_hoaxes)))),
        answer=answer,
    )


def _clean_feature_name(name: str) -> str:
    if "__" in name:
        name = name.split("__", 1)[1]
    if "_" in name:
        root = name.split("_", 1)[0]
        if root in {"city", "country", "shape"}:
            return root
    for root in ["duration", "latitude", "longitude", "hour", "month", "state", "country", "shape", "city"]:
        if name.startswith(root):
            return root
    return name


def _local_contributions(run: FinalModelRun, index: int) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    row = run.features.loc[[index]]
    transformed = run.model.named_steps["preprocess"].transform(row)
    if hasattr(transformed, "toarray"):
        values = transformed.toarray()[0]
    else:
        values = np.asarray(transformed)[0]
    coefficients = run.model.named_steps["classifier"].coef_[0]
    names = run.model.named_steps["preprocess"].get_feature_names_out()
    contributions: dict[str, float] = {}
    for name, contribution in zip(names, values * coefficients, strict=True):
        clean_name = _clean_feature_name(str(name))
        contributions[clean_name] = contributions.get(clean_name, 0.0) + float(contribution)
    ordered = sorted(contributions.items(), key=lambda item: item[1], reverse=True)
    against = [item for item in sorted(contributions.items(), key=lambda item: item[1]) if item[1] < 0]
    if not against:
        against = sorted(contributions.items(), key=lambda item: abs(item[1]))
    return ordered[:5], against[:5]


def phase16(run: FinalModelRun, threshold: float) -> Phase16Result:
    y_test = run.target.loc[run.test_index]
    probabilities = pd.Series(run.probabilities, index=run.test_index)
    predicted = probabilities >= threshold
    high = probabilities[predicted].idxmax()
    borderline = (probabilities[predicted] - threshold).abs().idxmin()
    missed_candidates = probabilities[(~predicted) & y_test.astype(bool)]
    missed = missed_candidates.idxmax() if not missed_candidates.empty else probabilities[~predicted].idxmax()
    selected = [
        ("canular avec forte confiance", high),
        ("juste au-dessus de la frontiere", borderline),
        ("canular laisse passer", missed),
    ]
    cases = []
    for kind, index in selected:
        top_for, top_against = _local_contributions(run, int(index))
        proba = float(probabilities.loc[index])
        if top_against[0][1] < 0:
            summary = (
                f"Le dossier est tire vers canular surtout par {top_for[0][0]}, "
                f"et retenu dans l'autre sens par {top_against[0][0]}."
            )
        else:
            summary = (
                f"Le dossier est tire vers canular surtout par {top_for[0][0]}; "
                f"les autres colonnes freinent peu la decision."
            )
        cases.append(
            LocalExplanation(
                index=int(index),
                kind=kind,
                probability=proba,
                predicted_hoax=bool(proba >= threshold),
                actual_hoax=bool(run.target.loc[index]),
                top_for_hoax=top_for,
                top_against_hoax=top_against,
                summary=summary,
            )
        )
    permutation = permutation_importance(
        run.model,
        run.features.loc[run.test_index],
        y_test,
        scoring="recall",
        n_repeats=5,
        random_state=42,
    )
    importance = sorted(
        zip(run.features.columns, permutation.importances_mean, strict=True),
        key=lambda item: item[1],
        reverse=True,
    )[:10]
    surprising = "country" if any(name == "country" for name, _ in importance[:5]) else importance[0][0]
    return Phase16Result(
        cases=cases,
        global_importance=[(str(name), float(value)) for name, value in importance],
        surprising_column=surprising,
    )


def _zone(country: object) -> str:
    value = "" if pd.isna(country) else str(country).strip().lower()
    if value == "us":
        return "Etats-Unis"
    if value == "ca":
        return "Canada"
    if value in {"gb", "de", "fr", "es", "it", "nl", "be", "ie", "se", "no", "dk", "fi", "pt", "ch", "at"}:
        return "Europe"
    return "Reste du monde"


def phase17(frame: pd.DataFrame, run: FinalModelRun, threshold: float) -> Phase17Result:
    y_test = run.target.loc[run.test_index].astype(bool)
    probabilities = pd.Series(run.probabilities, index=run.test_index)
    predictions = probabilities >= threshold
    zones = frame.loc[run.test_index, "country"].map(_zone)
    rows = []
    for zone in ["Etats-Unis", "Canada", "Europe", "Reste du monde"]:
        mask = zones.eq(zone)
        if int(mask.sum()) == 0:
            continue
        zone_y = y_test[mask]
        zone_pred = predictions[mask]
        zone_prob = probabilities[mask].to_numpy()
        rows.append(
            ZoneRow(
                zone=zone,
                count=int(mask.sum()),
                hoax_rate=float(zone_y.mean()),
                recall=recall_score(zone_y, zone_pred, zero_division=0),
                precision=precision_score(zone_y, zone_pred, zero_division=0),
                cost=decision_cost(zone_y, zone_prob, threshold).cost,
            )
        )
    global_row = ZoneRow(
        zone="Global",
        count=len(y_test),
        hoax_rate=float(y_test.mean()),
        recall=recall_score(y_test, predictions, zero_division=0),
        precision=precision_score(y_test, predictions, zero_division=0),
        cost=decision_cost(y_test, probabilities.to_numpy(), threshold).cost,
    )
    decision = (
        "Je garde une frontiere unique: hors Etats-Unis les effectifs et les canulars sont trop faibles "
        "pour apprendre une frontiere locale robuste sans fabriquer une decision instable."
    )
    return Phase17Result(rows=rows, global_row=global_row, decision=decision)


def phase18(frame: pd.DataFrame, target: pd.Series, phase8_recall: float, phase8_precision: float) -> Phase18Result:
    years = frame["date_posted"].dt.year
    yearly_rates = []
    for year, group_target in target.groupby(years):
        if pd.isna(year):
            continue
        yearly_rates.append(
            YearRow(
                year=int(year),
                count=int(group_target.size),
                hoax_rate=float(group_target.mean()),
            )
        )
    valid = frame["date_posted"].notna()
    cut = frame.loc[valid, "date_posted"].quantile(0.75)
    train_index = frame.index[valid & (frame["date_posted"] < cut)]
    test_index = frame.index[valid & (frame["date_posted"] >= cut)]
    duration = build_duration(frame).clip(upper=86400)
    features = add_city_hour_shape_features(frame, duration)
    metrics, _ = train_and_evaluate_indices(
        features,
        target,
        train_index,
        test_index,
        min_category_frequency=10,
    )
    return Phase18Result(
        yearly_rates=yearly_rates,
        old_to_recent_recall=metrics.recall,
        old_to_recent_precision=metrics.precision,
        phase8_recall=phase8_recall,
        phase8_precision=phase8_precision,
        monitoring_indicators=[
            "part des releves au-dessus de la frontiere de decision",
            "distribution des probabilites predites par tranche",
            "part de pays, villes rares et champs manquants",
        ],
        monitoring_frequency="revue mensuelle, avec un point hebdomadaire si le volume double",
        alert_rule=(
            "rappeler les analystes si un indicateur bouge de plus de 5 points de pourcentage "
            "ou de plus de 20 % relatif par rapport aux trois derniers mois"
        ),
    )


def run_decision_phases(frame: pd.DataFrame, target: pd.Series, phase8_recall: float, phase8_precision: float) -> DecisionResults:
    run = fit_final_model(frame, target)
    p13 = phase13(run)
    p14 = phase14(run)
    # Le seuil metier reste calcule sur le modele deploye; la calibration sert a lire les probabilites.
    p15 = phase15(frame, target)
    p16 = phase16(run, p13.best_threshold)
    p17 = phase17(frame, run, p13.best_threshold)
    p18 = phase18(frame, target, phase8_recall, phase8_precision)
    return DecisionResults(phase13=p13, phase14=p14, phase15=p15, phase16=p16, phase17=p17, phase18=p18)
