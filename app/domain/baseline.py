"""Is this count normal for this series? Pure functions: no I/O, no DB, no clock (PLAN §4, §7).

- Baseline: the median of the BASELINE_WEEKS complete weeks before the judged period, robust
  to a single extreme week.
- Expected range: Poisson 0.5% / 99.5% quantiles (99%, two-sided) around the expected count
  lambda. Weekly counts here have variance close to their mean, so the noise width follows from
  the volume alone.
"""

import math
import statistics
from collections.abc import Sequence
from typing import Final, Literal

BASELINE_WEEKS: Final = 8
LOWER_TAIL: Final = 0.005
UPPER_TAIL: Final = 0.995

Verdict = Literal["not_enough_history", "too_little_volume", "high", "low", "within_expected_range"]


def median(counts: Sequence[int]) -> float:
    """Median of the baseline weeks. Raises ValueError on an empty sequence."""
    return float(statistics.median(counts))


def poisson_range(lam: float) -> tuple[int, int]:
    """(lo, hi): the smallest k whose Poisson(lam) CDF reaches 0.5%, and the one reaching 99.5%.

    Matches the definition in docs/analysis/03. The pmf is computed in log space with
    math.lgamma, so large lambdas don't overflow. lam = 0 returns (0, 0) without log(0).
    """
    if lam < 0:
        raise ValueError(f"lambda must be >= 0, got {lam}")
    if lam == 0:
        return (0, 0)
    log_lam = math.log(lam)
    cdf = 0.0
    lo: int | None = None
    k = 0
    while True:
        cdf += math.exp(-lam + k * log_lam - math.lgamma(k + 1))
        if lo is None and cdf >= LOWER_TAIL:
            lo = k
        if cdf >= UPPER_TAIL:
            return (lo if lo is not None else k, k)
        k += 1


def verdict(count: int, lam: float, weeks_of_history: int) -> Verdict:
    """Apply the PLAN §4 precedence table exactly; the first matching row wins."""
    if weeks_of_history < BASELINE_WEEKS:
        return "not_enough_history"
    if lam == 0:
        # A zero baseline says nothing about volume: never "high".
        return "too_little_volume"
    lo, hi = poisson_range(lam)
    if count > hi:
        # Still reported when lo = 0: rises remain detectable at small volume.
        return "high"
    if count < lo:
        return "low"
    if lo == 0:
        # A drop can't be detected, so "within expected range" would claim too much.
        return "too_little_volume"
    return "within_expected_range"
