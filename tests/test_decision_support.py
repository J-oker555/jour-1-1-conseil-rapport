import numpy as np
import pandas as pd
import pytest

from src.ufo_pipeline.decision_support import calibration_table, decision_cost


def test_decision_cost_uses_bureau_cost_grid() -> None:
    y_true = pd.Series([True, False, True, False])
    probabilities = np.array([0.4, 0.6, 0.9, 0.1])

    row = decision_cost(y_true, probabilities, threshold=0.5)

    assert row.false_negatives == 1
    assert row.false_positives == 1
    assert row.cost == 32


def test_calibration_table_reports_count_prediction_and_observation() -> None:
    y_true = pd.Series([False, True, True, False])
    probabilities = np.array([0.05, 0.15, 0.85, 0.95])

    rows = calibration_table(y_true, probabilities, bins=2)

    assert rows[0].count == 2
    assert rows[0].mean_probability == pytest.approx(0.1)
    assert rows[0].observed_rate == 0.5
    assert rows[1].count == 2
    assert rows[1].mean_probability == pytest.approx(0.9)
    assert rows[1].observed_rate == 0.5
