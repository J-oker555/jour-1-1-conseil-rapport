import pandas as pd

from src.ufo_pipeline.advanced import make_event_ids, parse_duration_text, phase9


def test_event_id_groups_same_day_place_and_shape() -> None:
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2020-01-01 20:00", "2020-01-01 22:00", "2020-01-02 20:00"]),
            "city": ["Paris", " paris ", "Paris"],
            "state": ["IDF", "idf", "IDF"],
            "country": ["FR", "fr", "FR"],
            "shape": ["Triangle", "triangular", "Triangle"],
        }
    )

    event_ids = make_event_ids(frame)

    assert event_ids.iloc[0] == event_ids.iloc[1]
    assert event_ids.iloc[0] != event_ids.iloc[2]


def test_phase9_counts_empty_strings_as_missing_values() -> None:
    frame = pd.DataFrame(
        {
            "country": ["", "fr", " "],
            "state": ["", "", "idf"],
            "duration_hours_min": ["5 min", "", ""],
        }
    )
    target = pd.Series([True, False, False])

    result = phase9(frame, target)

    counts = {row.column: row.missing_count for row in result.columns}
    assert counts == {"country": 2, "state": 2, "duration_hours_min": 2}


def test_parse_duration_text_handles_common_units_and_ranges() -> None:
    assert parse_duration_text("5 minutes") == 300
    assert parse_duration_text("1-2 hrs") == 5400
    assert parse_duration_text("about half an hour") == 1800

