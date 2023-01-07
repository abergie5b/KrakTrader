import time
from typing import (
    Any,
    Dict,
    Tuple,
    Callable,
    Optional
)

from .logger import get_logger


class Throttle:
    def __init__(self, max_messages_per_sec: int):
        self._cache: Dict[str, float] = {}
        self._max_messages_per_sec = max_messages_per_sec
        self._logger = get_logger(f'{__name__}.throttle')

    def _fire(self, func: Callable, *args: Tuple[Any, ...]) -> None:
        func(*args)
        self._cache[func.__name__] = time.time()

    def apply(self, func: Callable, *args) -> None:
        cached: Optional[float] = self._cache.get(func.__name__, None)
        if not cached:
            self._fire(func, args)
        else:
            elapsed: float = time.time() - cached
            if elapsed > 1 / self._max_messages_per_sec:
                self._fire(func, args)
            else:
                self._logger.warning(f'prevented {func.__name__} from running')


