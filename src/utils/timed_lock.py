import multiprocessing
import time


class TimedLock:
    """
    A wrapper around multiprocessing.Lock that waits a fixed amount of time
    (default 20 seconds) after releasing the lock before it can be acquired again.
    """

    def __init__(self, wait_time: int):
        self._lock = multiprocessing.Lock()
        self._wait_time = wait_time

    def acquire(self, blocking=True, timeout=None):
        # Acquire the actual lock
        return self._lock.acquire(blocking, timeout)

    def release(self):
        time.sleep(self._wait_time)
        self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
