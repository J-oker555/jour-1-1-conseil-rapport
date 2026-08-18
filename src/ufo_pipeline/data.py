import csv
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import DATA_URL, HEADERS


@dataclass(frozen=True)
class ConversionSpec:
    column: str
    target_type: str
    origin: str


@dataclass(frozen=True)
class ConversionAnomaly:
    column: str
    target_type: str
    origin: str
    invalid_count: int
    missing_count: int
    nature_counts: dict[str, int]
    examples: list[str]


@dataclass(frozen=True)
class RejectedRecord:
    line_number: int
    field_count: int
    expected_field_count: int
    row: list[str]

    @property
    def reason(self) -> str:
        return f"{self.field_count} champs au lieu de {self.expected_field_count}"


@dataclass(frozen=True)
class LoadResult:
    frame: pd.DataFrame
    total_records: int
    loaded_records: int
    rejected_records: list[RejectedRecord]

    @property
    def rejected_records_count(self) -> int:
        return len(self.rejected_records)

    @property
    def rejection_reasons(self) -> dict[str, int]:
        reasons: dict[str, int] = {}
        for record in self.rejected_records:
            reasons[record.reason] = reasons.get(record.reason, 0) + 1
        return dict(sorted(reasons.items()))


def download_data(target: Path, url: str = DATA_URL) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return target
    urllib.request.urlretrieve(url, target)
    return target


def load_transmission(path: Path, headers: list[str] | None = None) -> LoadResult:
    expected_headers = headers or HEADERS
    rows: list[dict[str, str]] = []
    rejected: list[RejectedRecord] = []

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for line_number, row in enumerate(reader, start=1):
            if not row:
                continue
            if len(row) != len(expected_headers):
                rejected.append(
                    RejectedRecord(
                        line_number=line_number,
                        field_count=len(row),
                        expected_field_count=len(expected_headers),
                        row=row,
                    )
                )
                continue
            rows.append(dict(zip(expected_headers, row, strict=True)))

    frame = pd.DataFrame(rows, columns=expected_headers)
    return LoadResult(
        frame=frame,
        total_records=len(rows) + len(rejected),
        loaded_records=len(rows),
        rejected_records=rejected,
    )


CONVERSION_SPECS = [
    ConversionSpec("datetime", "date et heure", "temoin"),
    ConversionSpec("date_posted", "date", "service de transmission"),
    ConversionSpec("duration_seconds", "nombre", "capteur"),
    ConversionSpec("latitude", "nombre", "capteur"),
    ConversionSpec("longitude", "nombre", "capteur"),
]


def _convert_column(raw: pd.Series, target_type: str) -> pd.Series:
    if target_type in {"date", "date et heure"}:
        return pd.to_datetime(raw, errors="coerce")
    if target_type == "nombre":
        return pd.to_numeric(raw, errors="coerce")
    raise ValueError(f"Type cible inconnu: {target_type}")


def _classify_invalid_value(value: str, target_type: str) -> str:
    stripped = value.strip()
    if target_type in {"date", "date et heure"} and "24:00" in stripped:
        return "heure 24:00 non parseable"
    if target_type == "nombre" and "`" in stripped:
        return "caractere parasite dans un nombre"
    if target_type == "nombre" and any(char.isalpha() for char in stripped):
        return "lettre dans un nombre"
    return f"valeur incompatible avec le type {target_type}"


def _nature_counts(raw: pd.Series, invalid: pd.Series, missing: pd.Series, target_type: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    if int(missing.sum()):
        counts["valeur vide"] = int(missing.sum())
    for value in raw[invalid].dropna():
        nature = _classify_invalid_value(str(value), target_type)
        counts[nature] = counts.get(nature, 0) + 1
    return dict(sorted(counts.items()))


def convert_types(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, ConversionAnomaly]]:
    converted = frame.copy()
    anomalies: dict[str, ConversionAnomaly] = {}

    for spec in CONVERSION_SPECS:
        raw = converted[spec.column].astype("string")
        result = _convert_column(raw, spec.target_type)
        missing = raw.isna() | raw.str.strip().eq("")
        invalid = ~missing & result.isna()
        converted[spec.column] = result
        anomalies[spec.column] = ConversionAnomaly(
            column=spec.column,
            target_type=spec.target_type,
            origin=spec.origin,
            invalid_count=int(invalid.sum()),
            missing_count=int(missing.sum()),
            nature_counts=_nature_counts(raw, invalid, missing, spec.target_type),
            examples=raw[invalid].drop_duplicates().head(10).tolist(),
        )

    return converted, anomalies

