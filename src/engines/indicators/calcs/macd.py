import numpy as np
from numba import njit


@njit
def _ema_numba(values: np.ndarray, period: int) -> np.ndarray:
    ema = np.empty(len(values), dtype=np.float64)
    alpha = 2 / (period + 1)
    ema[0] = values[0]
    for i in range(1, len(values)):
        ema[i] = alpha * values[i] + (1 - alpha) * ema[i - 1]
    return ema


@njit
def _macd_numba(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = _ema_numba(prices, fast)
    ema_slow = _ema_numba(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema_numba(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line[-1], signal_line[-1], histogram[-1]
