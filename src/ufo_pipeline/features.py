from dataclasses import dataclass

import pandas as pd

from .labels import HOAX_PATTERN


@dataclass(frozen=True)
class FeatureInfo:
    column: str
    source: str
    writer: str
    moment: str
    knows_hoax: bool


@dataclass(frozen=True)
class FeatureSet:
    frame: pd.DataFrame
    metadata: list[FeatureInfo]

    @property
    def leakage_rows(self) -> list[dict[str, str]]:
        return [
            {
                "column": info.column,
                "source": info.source,
                "writer": info.writer,
                "moment": info.moment,
                "knows_hoax": "oui" if info.knows_hoax else "non",
            }
            for info in self.metadata
        ]

    @property
    def clean_columns(self) -> list[str]:
        return [info.column for info in self.metadata if not info.knows_hoax]

    def without_leakage(self) -> pd.DataFrame:
        return self.frame[self.clean_columns].copy()


FEATURE_METADATA = [
    FeatureInfo("duration_seconds", "duration_seconds", "capteur", "au moment du releve", False),
    FeatureInfo("latitude", "latitude", "capteur", "au moment du releve", False),
    FeatureInfo("longitude", "longitude", "capteur", "au moment du releve", False),
    FeatureInfo("has_state", "state", "service de transmission", "au moment du releve", False),
    FeatureInfo("has_country", "country", "service de transmission", "au moment du releve", False),
    FeatureInfo("comment_length", "comments", "temoin", "apres observation", True),
    FeatureInfo("shape", "shape", "temoin", "au moment du releve", False),
    FeatureInfo("country", "country", "service de transmission", "au moment du releve", False),
    FeatureInfo("hour", "datetime", "temoin", "au moment du releve", False),
    FeatureInfo("month", "datetime", "temoin", "au moment du releve", False),
    FeatureInfo("comment_hoax_keyword", "comments", "temoin", "apres observation", True),
]


def build_feature_set(frame: pd.DataFrame) -> FeatureSet:
    features = pd.DataFrame(index=frame.index)
    features["duration_seconds"] = frame["duration_seconds"]
    features["latitude"] = frame["latitude"]
    features["longitude"] = frame["longitude"]
    features["has_state"] = frame["state"].fillna("").astype(str).str.strip().ne("")
    features["has_country"] = frame["country"].fillna("").astype(str).str.strip().ne("")
    features["comment_length"] = frame["comments"].fillna("").astype(str).str.len()
    features["shape"] = frame["shape"].fillna("unknown").astype(str).str.lower()
    features["country"] = frame["country"].fillna("unknown").astype(str).str.lower()

    dt = frame["datetime"]
    features["hour"] = dt.dt.hour
    features["month"] = dt.dt.month

    features["comment_hoax_keyword"] = frame["comments"].fillna("").astype(str).str.contains(HOAX_PATTERN, regex=True)

    return FeatureSet(frame=features, metadata=FEATURE_METADATA)


def add_basic_features(frame: pd.DataFrame, include_leaky: bool) -> pd.DataFrame:
    feature_set = build_feature_set(frame)
    if include_leaky:
        return feature_set.frame
    return feature_set.without_leakage()


def leakage_table(model_columns: list[str]) -> list[dict[str, str]]:
    metadata_by_column = {info.column: info for info in FEATURE_METADATA}
    return FeatureSet(
        frame=pd.DataFrame(columns=model_columns),
        metadata=[metadata_by_column[column] for column in model_columns],
    ).leakage_rows

