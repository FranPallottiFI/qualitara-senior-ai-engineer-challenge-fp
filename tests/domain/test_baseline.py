"""Domain tests: pure, no DB. Each test is named for the belief it would falsify (PLAN §9)."""

import pytest

from app.domain.baseline import median, poisson_range, verdict


def test_single_extreme_week_does_not_move_the_baseline() -> None:
    assert median([12, 14, 11, 13, 800, 12, 14, 13]) == pytest.approx(13)
    # The mean of the same weeks would be ~111; the median ignores the burst.
    assert median([12, 14, 11, 13, 12, 14, 13, 13]) == pytest.approx(13)


# Reference: ./scripts/sql-ro.sh "$(cat docs/analysis/03-min-detectable-change.sql)",
# column normal_range.
@pytest.mark.parametrize(
    ("lam", "expected"),
    [(4, (0, 10)), (8, (2, 16)), (15, (6, 26)), (30, (17, 45)), (70, (49, 92))],
)
def test_poisson_range_matches_reference_table(lam: float, expected: tuple[int, int]) -> None:
    assert poisson_range(lam) == expected


@pytest.mark.parametrize(
    ("count", "expected"),
    [(16, "low"), (17, "within_expected_range"), (45, "within_expected_range"), (46, "high")],
)
def test_verdict_boundaries(count: int, expected: str) -> None:
    # lambda = 30 -> range 17..45, lower bound > 0.
    assert verdict(count, 30, 8) == expected


def test_low_impossible_at_small_baseline_gives_too_little_volume() -> None:
    # lambda = 4 -> range 0..10: no count can be "low".
    assert poisson_range(4) == (0, 10)
    assert verdict(0, 4, 8) == "too_little_volume"
    assert verdict(4, 4, 8) == "too_little_volume"
    assert verdict(10, 4, 8) == "too_little_volume"
    # A rise is still detectable.
    assert verdict(11, 4, 8) == "high"


def test_zero_baseline_gives_too_little_volume_never_high() -> None:
    assert poisson_range(0) == (0, 0)
    assert verdict(0, 0, 8) == "too_little_volume"
    assert verdict(500, 0, 8) == "too_little_volume"


@pytest.mark.parametrize("weeks_of_history", [0, 1, 7])
def test_fewer_than_8_baseline_weeks_gives_not_enough_history(weeks_of_history: int) -> None:
    # Counts that would otherwise be low, within and high.
    for count in (0, 30, 500):
        assert verdict(count, 30, weeks_of_history) == "not_enough_history"
    assert verdict(500, 30, 8) == "high"
