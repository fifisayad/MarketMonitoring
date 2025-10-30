from numba import njit
import numpy as np


@njit
def wma_kahan(values: np.ndarray) -> float:
    n = len(values)
    if n == 0:
        return np.nan
    sum_ = 0.0
    c = 0.0
    weight_sum = n * (n + 1) / 2.0
    for i in range(n):
        yi = values[i] * (i + 1) - c
        t = sum_ + yi
        c = (t - sum_) - yi
        sum_ = t
    return sum_ / weight_sum


@njit
def _hma_numba(prices: np.ndarray, period: int) -> float:
    length = len(prices)
    if length == 0:
        return np.nan

    # Step 1 & 2: WMA series
    wma_half = np.empty(length, dtype=np.float64)
    wma_full = np.empty(length, dtype=np.float64)
    wma_half[:] = np.nan
    wma_full[:] = np.nan

    for i in range(length):
        end = i + 1
        start_half = max(0, end - (period // 2) - 1)
        start_full = max(0, end - period)
        wma_half[i] = wma_kahan(prices[start_half:end])
        wma_full[i] = wma_kahan(prices[start_full:end])

    # Step 3: diff
    diff = 2.0 * wma_half - wma_full

    # Step 4: HMA = WMA of last hma_period valid values
    hma_period = int(np.sqrt(period))
    return wma_kahan(diff[-hma_period:])
