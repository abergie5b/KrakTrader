import queue
from abc import ABC, abstractmethod

from .logger import get_logger


class PooledObject(ABC):
    @staticmethod
    @abstractmethod
    def create_empty(*args) -> object: ...
    @abstractmethod
    def clean(self) -> None:  ...
    @abstractmethod
    def init(self, *args) -> object: ...


class Pool(object):
    instance = None

    def __new__(cls, size, create_empty_fn):
        if not cls.instance:
            cls.instance = super(Pool, cls).__new__(cls)
            cls._pool: queue.Queue[PooledObject] = queue.Queue(size)
            cls.acquired_size = size
            cls.size = size
            cls.create_empty = create_empty_fn
            cls._logger = get_logger(cls.__name__)

            for x in range(size):
                cls._pool.put(
                    create_empty_fn()
                )
        return cls.instance

    def get_stats(self):
        return {
            'size': self.size,
            'acquired_size': self.acquired_size,
            'gc.get_stats': gc.get_stats()
        }

    def resize(self):
        new_size: int = self.size * 2
        self._logger.info(f'resizing buffer from {self.size} to {new_size}')
        new_queue: queue.Queue[PooledObject] = queue.Queue(new_size)
        while not new_queue.full():
            if not self._pool.empty():
                new_queue.put(
                    self._pool.get()
                )
            else:
                new_queue.put(
                    self.create_empty()
                )
        self.acquired_size = self.size
        self._pool = new_queue
        self.size = new_size

    def acquire(self) -> PooledObject:
        self.acquired_size -= 1
        if self.acquired_size < 0:
            self.resize()
        return self._pool.get()

    def release(self, obj: PooledObject) -> None:
        obj.clean()
        self.acquired_size += 1
        self._pool.put(obj)
