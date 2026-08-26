"""Dataset V2, calibration and walk-forward utilities."""
from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Callable, Sequence


@dataclass(frozen=True)
class TargetV2:
    label: str
    future_return: float
    horizon: int


@dataclass(frozen=True)
class WalkForwardWindow:
    train: tuple[int, int]
    validation: tuple[int, int]
    test: tuple[int, int]


def make_target(current: float, future: float, horizon: int, threshold: float = 0.002) -> TargetV2:
    if current <= 0 or future <= 0 or horizon <= 0:
        raise ValueError("prices must be positive and horizon must be greater than zero")
    future_return = future / current - 1.0
    label = "LONG" if future_return >= threshold else "SHORT" if future_return <= -threshold else "NO_TRADE"
    return TargetV2(label, future_return, horizon)


def create_walk_forward_windows(
    length: int, train_size: int, validation_size: int, test_size: int, step: int | None = None
) -> list[WalkForwardWindow]:
    if min(length, train_size, validation_size, test_size) <= 0:
        raise ValueError("window sizes must be positive")
    step = test_size if step is None else step
    windows: list[WalkForwardWindow] = []
    start = 0
    while start + train_size + validation_size + test_size <= length:
        train_end = start + train_size
        validation_end = train_end + validation_size
        windows.append(WalkForwardWindow((start, train_end), (train_end, validation_end), (validation_end, validation_end + test_size)))
        start += step
    return windows


def brier_score(probabilities: Sequence[float], labels: Sequence[int]) -> float:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must have the same non-empty length")
    return sum((min(1.0, max(0.0, float(probability))) - int(label)) ** 2 for probability, label in zip(probabilities, labels)) / len(labels)


def expected_calibration_error(probabilities: Sequence[float], labels: Sequence[int], bins: int = 10) -> float:
    if len(probabilities) != len(labels) or not probabilities or bins <= 0:
        raise ValueError("invalid calibration inputs")
    error = 0.0
    total = len(labels)
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        members = [(float(probability), int(label)) for probability, label in zip(probabilities, labels) if lower <= probability < upper or (index == bins - 1 and probability == 1)]
        if members:
            error += len(members) / total * abs(sum(item[0] for item in members) / len(members) - sum(item[1] for item in members) / len(members))
    return error


def evaluate_walk_forward(
    values: Sequence[float], windows: Sequence[WalkForwardWindow], evaluator: Callable[[Sequence[float], Sequence[float]], float]
) -> list[dict[str, float]]:
    results = []
    for window in windows:
        train = values[window.train[0]:window.train[1]]
        test = values[window.test[0]:window.test[1]]
        results.append({"train_size": float(len(train)), "test_size": float(len(test)), "score": float(evaluator(train, test))})
    return results
