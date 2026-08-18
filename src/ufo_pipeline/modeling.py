from dataclasses import dataclass

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass(frozen=True)
class ModelMetrics:
    recall: float
    precision: float
    accuracy: float
    train_size: int
    test_size: int
    train_positive: int
    train_negative: int
    test_positive: int
    test_negative: int
    true_negative: int
    false_positive: int
    false_negative: int
    true_positive: int
    test_fraction: float
    random_seed: int


@dataclass(frozen=True)
class BaselineMetrics:
    accuracy: float
    recall: float
    precision: float
    predicted_positive: int
    predicted_negative: int


def build_model(features: pd.DataFrame, min_category_frequency: int | None = None) -> Pipeline:
    numeric = [c for c in features.columns if pd.api.types.is_numeric_dtype(features[c])]
    categorical = [c for c in features.columns if c not in numeric]
    if min_category_frequency is None:
        encoder = OneHotEncoder(handle_unknown="ignore")
    else:
        encoder = OneHotEncoder(
            handle_unknown="infrequent_if_exist",
            min_frequency=min_category_frequency,
        )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), numeric),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", encoder)]), categorical),
        ]
    )
    return Pipeline(
        [
            ("preprocess", preprocessor),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )


def _metrics_from_predictions(
    y_train: pd.Series,
    y_test: pd.Series,
    predictions,
    test_fraction: float,
    seed: int,
) -> ModelMetrics:
    tn, fp, fn, tp = confusion_matrix(y_test, predictions, labels=[False, True]).ravel()
    return ModelMetrics(
        recall=recall_score(y_test, predictions, zero_division=0),
        precision=precision_score(y_test, predictions, zero_division=0),
        accuracy=accuracy_score(y_test, predictions),
        train_size=len(y_train),
        test_size=len(y_test),
        train_positive=int(y_train.sum()),
        train_negative=int((~y_train.astype(bool)).sum()),
        test_positive=int(y_test.sum()),
        test_negative=int((~y_test.astype(bool)).sum()),
        true_negative=int(tn),
        false_positive=int(fp),
        false_negative=int(fn),
        true_positive=int(tp),
        test_fraction=test_fraction,
        random_seed=seed,
    )


def train_and_evaluate(
    features: pd.DataFrame,
    target: pd.Series,
    seed: int = 42,
    test_size: float = 0.25,
) -> ModelMetrics:
    stratify = target if target.nunique() == 2 and target.value_counts().min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=seed,
        stratify=stratify,
    )
    model = build_model(features)
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    return _metrics_from_predictions(y_train, y_test, predictions, test_size, seed)


def train_and_evaluate_indices(
    features: pd.DataFrame,
    target: pd.Series,
    train_index,
    test_index,
    seed: int = 42,
    min_category_frequency: int | None = None,
) -> tuple[ModelMetrics, Pipeline]:
    x_train = features.loc[train_index]
    x_test = features.loc[test_index]
    y_train = target.loc[train_index]
    y_test = target.loc[test_index]
    model = build_model(features, min_category_frequency=min_category_frequency)
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    metrics = _metrics_from_predictions(y_train, y_test, predictions, len(y_test) / len(target), seed)
    return metrics, model


def grouped_split_indices(features: pd.DataFrame, target: pd.Series, groups: pd.Series, seed: int = 42, test_size: float = 0.25):
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_pos, test_pos = next(splitter.split(features, target, groups=groups))
    return features.index[train_pos], features.index[test_pos]


def baseline_always_not_hoax(target: pd.Series) -> float:
    return baseline_always_not_hoax_metrics(target).accuracy


def baseline_always_not_hoax_metrics(target: pd.Series) -> BaselineMetrics:
    labels = target.astype(bool)
    predictions = pd.Series(False, index=labels.index)
    return BaselineMetrics(
        accuracy=accuracy_score(labels, predictions),
        recall=recall_score(labels, predictions, zero_division=0),
        precision=precision_score(labels, predictions, zero_division=0),
        predicted_positive=int(predictions.sum()),
        predicted_negative=int((~predictions).sum()),
    )

