import numpy as np

from numba import njit
from typing import Any, Union


@njit
def _rsi_numba(prices: np.ndarray, period: int = 14) -> Union[float, Any]:
    n = prices.size
    deltas = np.empty(n - 1, dtype=prices.dtype)
    for i in range(n - 1):
        deltas[i] = prices[i + 1] - prices[i]

    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
