from src.bat.time_features import circular_distance


def test_midnight_is_closer_to_23h_than_to_20h() -> None:
    assert circular_distance(23, 0) < circular_distance(20, 0)

