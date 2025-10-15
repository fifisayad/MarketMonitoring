from typing import Any
import numpy as np
from numba import njit


@njit
def _atr_numba(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14
) -> float | Any:
    tr = np.zeros(len(highs))
    for i in range(1, len(highs)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr[i] = max(hl, hc, lc)
    atr = np.mean(tr[1 : period + 1])
    for i in range(period + 1, len(highs)):
        atr = (atr * (period - 1) + tr[i]) / period
    return atr
