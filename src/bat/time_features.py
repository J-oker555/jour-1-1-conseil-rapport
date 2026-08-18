from __future__ import annotations

import math


def circular_hour(hour: float) -> tuple[float, float]:
    angle = 2 * math.pi * (hour % 24) / 24
    return math.sin(angle), math.cos(angle)


def circular_distance(hour_a: float, hour_b: float) -> float:
    ax, ay = circular_hour(hour_a)
    bx, by = circular_hour(hour_b)
    return math.dist((ax, ay), (bx, by))

