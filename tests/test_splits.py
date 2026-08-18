import pytest

from src.bat.splits import assert_group_is_not_split


def test_detects_event_split_across_train_and_test() -> None:
    with pytest.raises(AssertionError):
        assert_group_is_not_split({"event-a", "event-b"}, {"event-b", "event-c"})

