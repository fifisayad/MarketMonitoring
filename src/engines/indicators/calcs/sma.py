import numpy as np
from numba import njit


@njit
def simple_moving_average(arr, window):
    n = len(arr)
    if window > n:
        return None

    result = np.empty(n - window + 1, dtype=np.float64)
    cumsum = 0.0

    # Initial window sum
    for i in range(window):
        cumsum += arr[i]
    result[0] = cumsum / window

    # Sliding window
    for i in range(window, n):
        cumsum += arr[i] - arr[i - window]
        result[i - window + 1] = cumsum / window

    return result


@njit
def regression_slope(series, window):
    n = len(series)
    if window > n:
        return None

    slopes = np.empty(n - window + 1, dtype=np.float64)

    # Precompute x values and mean
    x = np.arange(window, dtype=np.float64)
    x_mean = np.mean(x)
    denom = np.sum((x - x_mean) ** 2)

    for i in range(n - window + 1):
        y = series[i : i + window]
        y_mean = np.mean(y)
        numer = 0.0
        for j in range(window):
            numer += (x[j] - x_mean) * (y[j] - y_mean)
        slopes[i] = numer / denom

    return slopes


@njit
def detect_slope_segments(slopes, tol=1e-6):
    """
    Groups slopes into segments where direction is consistent.
    Returns segments with average slope for each.
    Each segment: (start_index, end_index, avg_slope)
    """
    if len(slopes) == 0:
        return np.empty((0, 3), dtype=np.float64)

    segments = []
    start = 0
    current_slope = slopes[0]

    for i in range(1, len(slopes)):
        if (slopes[i] * current_slope < 0) or (abs(slopes[i] - current_slope) > tol):
            # End segment → compute average slope
            avg_slope = np.mean(slopes[start:i])
            segments.append((start, i - 1, avg_slope))

            # Start new segment
            start = i
            current_slope = slopes[i]

    # Add final segment
    avg_slope = np.mean(slopes[start:])
    segments.append((start, len(slopes) - 1, avg_slope))

    return np.array(segments, dtype=np.float64)
