from __future__ import annotations


def assert_group_is_not_split(group_ids_train: set[str], group_ids_test: set[str]) -> None:
    overlap = group_ids_train & group_ids_test
    if overlap:
        sample = ", ".join(sorted(overlap)[:5])
        raise AssertionError(f"Evenements presents des deux cotes: {sample}")


def assert_train_before_test(max_train_date, min_test_date) -> None:
    if max_train_date >= min_test_date:
        raise AssertionError(
            f"Fuite temporelle: max train={max_train_date}, min test={min_test_date}"
        )

