from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from .features import build_feature_set
from .modeling import ModelMetrics, grouped_split_indices, train_and_evaluate_indices

EVENT_COLUMNS = ["observation_date", "city", "state", "country", "shape"]
SHAPE_NORMALIZATION = {
    "changed": "changing",
    "changing": "changing",
    "chevron": "triangle",
    "triangular": "triangle",
    "unknown": "other",
    "": "other",
}


@dataclass(frozen=True)
class Phase7Result:
    event_columns: list[str]
    multi_witness_events: int
    largest_witness_count: int
    old_split_leaking_records: int
    duplicate_comment_rows: int
    duplicate_comment_groups: int
    example_event: pd.DataFrame
    grouped_metrics: ModelMetrics


@dataclass(frozen=True)
class Phase8Result:
    cut_column: str
    cut_reason: str
    cut_date: pd.Timestamp
    train_size: int
    test_size: int
    train_hoax_rate: float
    test_hoax_rate: float
    temporal_metrics: ModelMetrics


@dataclass(frozen=True)
class MissingColumnResult:
    column: str
    missing_hoax_rate: float
    present_hoax_rate: float
    missing_count: int
    present_count: int


@dataclass(frozen=True)
class Phase9Result:
    columns: list[MissingColumnResult]
    treatment: str


@dataclass(frozen=True)
class Phase10Result:
    train_hoax_rate: float
    test_hoax_rate: float
    single_prediction: bool
    corrected_metrics: ModelMetrics


@dataclass(frozen=True)
class Phase11Result:
    unusable_count: int
    contradiction_count: int
    median_seconds: float
    over_one_day_count: int
    longest: pd.DataFrame
    aberration_counts: dict[str, int]
    decision: str


@dataclass(frozen=True)
class Phase12Result:
    width_before: int
    width_after: int
    city_rule: str
    singleton_cities: int
    distance_23_0: float
    distance_23_20: float
    shape_count_before: int
    shape_count_after: int
    final_metrics: ModelMetrics


@dataclass(frozen=True)
class AdvancedResults:
    phase7: Phase7Result
    phase8: Phase8Result
    phase9: Phase9Result
    phase10: Phase10Result
    phase11: Phase11Result
    phase12: Phase12Result


def _clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.lower()


def make_event_ids(frame: pd.DataFrame) -> pd.Series:
    observed_date = frame["datetime"].dt.date.astype("string").fillna("date_unknown")
    parts = [
        observed_date,
        _clean_text(frame["city"]).replace("", "city_unknown"),
        _clean_text(frame["state"]).replace("", "state_unknown"),
        _clean_text(frame["country"]).replace("", "country_unknown"),
        normalize_shape(frame["shape"]),
    ]
    return parts[0].str.cat(parts[1:], sep="|")


def normalize_shape(shape: pd.Series) -> pd.Series:
    cleaned = _clean_text(shape)
    cleaned = cleaned.replace(SHAPE_NORMALIZATION)
    rare_or_empty = cleaned.eq("") | cleaned.eq("nan")
    return cleaned.mask(rare_or_empty, "other")


def old_random_split_indices(target: pd.Series, seed: int = 42, test_size: float = 0.25):
    stratify = target if target.nunique() == 2 and target.value_counts().min() >= 2 else None
    positions = np.arange(len(target))
    train_pos, test_pos = train_test_split(
        positions,
        test_size=test_size,
        random_state=seed,
        stratify=stratify,
    )
    return target.index[train_pos], target.index[test_pos]


def count_records_crossing_split(event_ids: pd.Series, train_index, test_index) -> int:
    train_events = set(event_ids.loc[train_index])
    test_events = set(event_ids.loc[test_index])
    leaking_events = train_events & test_events
    return int(event_ids.isin(leaking_events).sum())


def phase7(frame: pd.DataFrame, target: pd.Series) -> Phase7Result:
    feature_set = build_feature_set(frame).without_leakage()
    event_ids = make_event_ids(frame)
    event_sizes = event_ids.value_counts()
    old_train, old_test = old_random_split_indices(target)
    grouped_train, grouped_test = grouped_split_indices(feature_set, target, event_ids)
    grouped_metrics, _ = train_and_evaluate_indices(feature_set, target, grouped_train, grouped_test)

    duplicated_comments = _clean_text(frame["comments"])
    non_empty = duplicated_comments.ne("")
    duplicate_mask = non_empty & duplicated_comments.duplicated(keep=False)
    duplicate_group_count = int(duplicated_comments[duplicate_mask].nunique())

    example_event_id = event_sizes[event_sizes > 1].index[0]
    example_columns = ["datetime", "city", "state", "country", "shape", "comments"]
    example_event = frame.loc[event_ids.eq(example_event_id), example_columns].copy()
    side = pd.Series("train", index=frame.index)
    side.loc[grouped_test] = "test"
    example_event["split"] = side.loc[example_event.index]

    return Phase7Result(
        event_columns=EVENT_COLUMNS,
        multi_witness_events=int((event_sizes > 1).sum()),
        largest_witness_count=int(event_sizes.max()),
        old_split_leaking_records=count_records_crossing_split(event_ids, old_train, old_test),
        duplicate_comment_rows=int(duplicate_mask.sum()),
        duplicate_comment_groups=duplicate_group_count,
        example_event=example_event,
        grouped_metrics=grouped_metrics,
    )


def temporal_split_indices(frame: pd.DataFrame, test_fraction: float = 0.25):
    valid_dates = frame["date_posted"].dropna().sort_values()
    cut_date = valid_dates.iloc[int(len(valid_dates) * (1 - test_fraction))]
    train_index = frame.index[frame["date_posted"].notna() & (frame["date_posted"] < cut_date)]
    test_index = frame.index[frame["date_posted"].notna() & (frame["date_posted"] >= cut_date)]
    return train_index, test_index, cut_date


def phase8(frame: pd.DataFrame, target: pd.Series) -> Phase8Result:
    features = build_feature_set(frame).without_leakage()
    train_index, test_index, cut_date = temporal_split_indices(frame)
    metrics, _ = train_and_evaluate_indices(features, target, train_index, test_index)
    y_train = target.loc[train_index]
    y_test = target.loc[test_index]
    return Phase8Result(
        cut_column="date_posted",
        cut_reason=(
            "J'utilise la date de reception par le Bureau: elle represente le moment ou "
            "le dossier devient disponible pour apprendre, alors que l'observation peut etre declaree plus tard."
        ),
        cut_date=cut_date,
        train_size=len(train_index),
        test_size=len(test_index),
        train_hoax_rate=float(y_train.mean()),
        test_hoax_rate=float(y_test.mean()),
        temporal_metrics=metrics,
    )


def phase9(frame: pd.DataFrame, target: pd.Series) -> Phase9Result:
    missing_counts = pd.Series(
        {
            column: int((frame[column].isna() | frame[column].astype("string").str.strip().fillna("").eq("")).sum())
            for column in frame.columns
        }
    ).sort_values(ascending=False)
    top_columns = missing_counts.head(3).index.tolist()
    rows = []
    for column in top_columns:
        missing = frame[column].isna() | frame[column].astype("string").str.strip().fillna("").eq("")
        present = ~missing
        rows.append(
            MissingColumnResult(
                column=column,
                missing_hoax_rate=float(target[missing].mean()) if int(missing.sum()) else 0.0,
                present_hoax_rate=float(target[present].mean()) if int(present.sum()) else 0.0,
                missing_count=int(missing.sum()),
                present_count=int(present.sum()),
            )
        )
    return Phase9Result(
        columns=rows,
        treatment=(
            "Les valeurs manquantes sont imputees dans le pipeline, mais chaque colonne importante garde "
            "un indicateur explicite `missing`, afin que le modele voie que la case etait vide."
        ),
    )


def build_corrected_features(frame: pd.DataFrame, duration: pd.Series | None = None) -> pd.DataFrame:
    features = pd.DataFrame(index=frame.index)
    duration_values = duration if duration is not None else frame["duration_seconds"]
    features["duration_seconds"] = duration_values
    features["duration_missing"] = duration_values.isna()
    features["latitude"] = frame["latitude"]
    features["latitude_missing"] = frame["latitude"].isna()
    features["longitude"] = frame["longitude"]
    features["longitude_missing"] = frame["longitude"].isna()
    features["country"] = _clean_text(frame["country"]).replace("", "missing")
    features["country_missing"] = features["country"].eq("missing")
    features["state_missing"] = _clean_text(frame["state"]).eq("")
    features["shape"] = normalize_shape(frame["shape"])
    features["month"] = frame["datetime"].dt.month
    return features


def phase10(frame: pd.DataFrame, target: pd.Series, train_index, test_index) -> Phase10Result:
    features = build_corrected_features(frame)
    metrics, model = train_and_evaluate_indices(features, target, train_index, test_index, min_category_frequency=10)
    sample = frame.loc[[train_index[0]]].copy()
    sample_features = build_corrected_features(sample)
    prediction = bool(model.predict(sample_features)[0])
    return Phase10Result(
        train_hoax_rate=float(target.loc[train_index].mean()),
        test_hoax_rate=float(target.loc[test_index].mean()),
        single_prediction=prediction,
        corrected_metrics=metrics,
    )


DURATION_PATTERNS = [
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|sec|s)\b", re.I), 1),
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|min|m)\b", re.I), 60),
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|hr|h)\b", re.I), 3600),
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:days?|day|d)\b", re.I), 86400),
]


def parse_duration_text(value: object) -> float:
    if pd.isna(value):
        return math.nan
    text = str(value).strip().lower()
    if not text:
        return math.nan
    if "half" in text and ("hour" in text or "hr" in text):
        return 1800.0
    if "few" in text and ("minute" in text or "min" in text):
        return 180.0
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*[-/]\s*(\d+(?:\.\d+)?)\s*(hours?|hrs?|hr|minutes?|mins?|min|seconds?|secs?|sec)", text)
    if range_match:
        value_avg = (float(range_match.group(1)) + float(range_match.group(2))) / 2
        unit = range_match.group(3)
        if unit.startswith(("hour", "hr")):
            return value_avg * 3600
        if unit.startswith(("min", "minute")):
            return value_avg * 60
        return value_avg
    for pattern, multiplier in DURATION_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1)) * multiplier
    bare = re.fullmatch(r"\d+(?:\.\d+)?", text)
    if bare:
        return float(text)
    return math.nan


def build_duration(frame: pd.DataFrame) -> pd.Series:
    raw_seconds = frame["duration_seconds"]
    parsed_text = frame["duration_hours_min"].map(parse_duration_text)
    valid_seconds = raw_seconds.where(raw_seconds > 0)
    return valid_seconds.fillna(parsed_text)


def phase11(frame: pd.DataFrame) -> Phase11Result:
    raw_seconds = frame["duration_seconds"]
    parsed_text = frame["duration_hours_min"].map(parse_duration_text)
    duration = build_duration(frame)
    both = raw_seconds.notna() & parsed_text.notna() & (raw_seconds > 0)
    contradictions = both & ((raw_seconds - parsed_text).abs() > np.maximum(60, raw_seconds.abs() * 0.5))
    longest_columns = ["datetime", "city", "country", "duration_seconds", "duration_hours_min", "comments"]
    longest = frame.assign(duration_final=duration).sort_values("duration_final", ascending=False).head(3)
    aberrations = {
        "duree numerique nulle ou negative alors que le texte est lisible": int(
            (((raw_seconds <= 0) | raw_seconds.isna()) & parsed_text.notna()).sum()
        ),
        "duree numerique et texte contradictoires": int(contradictions.sum()),
        "duree superieure a une journee": int((duration > 86400).sum()),
    }
    return Phase11Result(
        unusable_count=int(duration.isna().sum()),
        contradiction_count=int(contradictions.sum()),
        median_seconds=float(duration.dropna().median()),
        over_one_day_count=int((duration > 86400).sum()),
        longest=longest[longest_columns + ["duration_final"]],
        aberration_counts=aberrations,
        decision=(
            "Je conserve toutes les lignes, je remplace les secondes nulles par la duree lisible quand elle existe, "
            "et je plafonne les durees extremes dans le pipeline modele plutot que de les supprimer."
        ),
    )


def add_city_hour_shape_features(frame: pd.DataFrame, duration: pd.Series) -> pd.DataFrame:
    features = build_corrected_features(frame, duration=duration)
    city = _clean_text(frame["city"]).replace("", "missing")
    features["city"] = city
    hour = frame["datetime"].dt.hour
    angle = 2 * np.pi * hour / 24
    features["hour_sin"] = np.sin(angle)
    features["hour_cos"] = np.cos(angle)
    features = features.drop(columns=["month"]).assign(month=frame["datetime"].dt.month)
    return features


def transformed_width(model) -> int:
    output = model.named_steps["preprocess"].get_feature_names_out()
    return len(output)


def circular_distance(hour_a: int, hour_b: int) -> float:
    angle_a = 2 * math.pi * hour_a / 24
    angle_b = 2 * math.pi * hour_b / 24
    return math.dist((math.sin(angle_a), math.cos(angle_a)), (math.sin(angle_b), math.cos(angle_b)))


def phase12(frame: pd.DataFrame, target: pd.Series, train_index, test_index, duration: pd.Series) -> Phase12Result:
    before = build_feature_set(frame).without_leakage()
    after = add_city_hour_shape_features(frame, duration)
    metrics, model = train_and_evaluate_indices(
        after,
        target,
        train_index,
        test_index,
        min_category_frequency=10,
    )
    city_counts = _clean_text(frame["city"]).replace("", "missing").value_counts()
    shape_before = _clean_text(frame["shape"]).replace("", "unknown")
    shape_after = normalize_shape(frame["shape"])
    return Phase12Result(
        width_before=before.shape[1],
        width_after=transformed_width(model),
        city_rule="OneHotEncoder regroupe dans `infrequent` les villes vues moins de 10 fois dans l'apprentissage.",
        singleton_cities=int((city_counts == 1).sum()),
        distance_23_0=circular_distance(23, 0),
        distance_23_20=circular_distance(23, 20),
        shape_count_before=int(shape_before.nunique()),
        shape_count_after=int(shape_after.nunique()),
        final_metrics=metrics,
    )


def run_advanced_phases(frame: pd.DataFrame, target: pd.Series) -> AdvancedResults:
    phase7_result = phase7(frame, target)
    phase8_result = phase8(frame, target)
    train_index, test_index, _ = temporal_split_indices(frame)
    phase9_result = phase9(frame, target)
    phase10_result = phase10(frame, target, train_index, test_index)
    phase11_result = phase11(frame)
    duration = build_duration(frame).clip(upper=86400)
    phase12_result = phase12(frame, target, train_index, test_index, duration)
    return AdvancedResults(
        phase7=phase7_result,
        phase8=phase8_result,
        phase9=phase9_result,
        phase10=phase10_result,
        phase11=phase11_result,
        phase12=phase12_result,
    )
