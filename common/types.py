import sys
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field, InitVar

from .pools import PooledObject


class Side(Enum):
    NONE = 0,
    BUY = 1,
    SELL = 2


@dataclass
class Quote(PooledObject):
    _price: InitVar[float]
    _volume: InitVar[float]
    _timestamp: InitVar[float]

    price: float = field(init=False)
    volume: float = field(init=False)
    timestamp: float = field(init=False)

    @staticmethod
    def create_empty(*args):
        return Quote(-sys.maxsize, 0, -sys.maxsize)

    def __post_init__(self, _price, _volume, _timestamp):
        self.price = float(_price)
        self.volume = float(_volume)
        self.timestamp = float(_timestamp)

    def __eq__(self, other):
        return self.price == other.price and \
            self.volume == other.volume and \
            self.timestamp == other.timestamp

    def init(self, _price, _volume, _timestamp):
        self.price = float(_price)
        self.volume = float(_volume)
        self.timestamp = float(_timestamp)
        return self

    def clean(self):
        self.price = -sys.maxsize
        self.volume = 0
        self.timestamp = -sys.maxsize


@dataclass
class Trade:
    _price: InitVar[float]
    _volume: InitVar[float]
    _time: InitVar[float]
    _side: InitVar[str]
    _order_type: InitVar[str]

    price: float = field(init=False)
    volume: float = field(init=False)
    time: float = field(init=False)
    side: str = field(init=False)
    order_type: str = field(init=False)

    def __post_init__(self, _price, _volume, _time, _side, _order_type):
        self.price = float(_price)
        self.volume = float(_volume)
        self.time = float(_time)
        self.side = _side
        self.order_type = _order_type


@dataclass
class Order(PooledObject):
    symbol: str
    side: Side
    clorder_id: int

    _qty: InitVar[float]
    qty: float = field(init=False)

    _price: InitVar[float]
    price: float = field(init=False)

    order_type: str
    order_status: str
    time_in_force: Optional[str]

    order_id: Optional[str] = field(init=False)
    orig_qty: float = field(init=False)
    cum_qty: float = field(init=False)

    @staticmethod
    def create_empty(*args):
        return Order('', Side.NONE, -sys.maxsize, 0, -sys.maxsize, '', '', None)

    def __post_init__(self, _qty, _price):
        self.qty = float(_qty)
        self.price = float(_price)
        self.order_id = None
        self.orig_qty = self.qty
        self.cum_qty = 0

    def init(self, symbol, side, clorder_id, qty, price, order_type, order_status, time_in_force):
        self.symbol = symbol
        self.side = side
        self.clorder_id = clorder_id
        self.qty = float(qty)
        self.price = float(price)
        self.order_type = order_type
        self.order_status = order_status
        self.time_in_force = time_in_force
        self.orig_qty = self.qty
        self.cum_qty = 0
        return self

    def clean(self):
        self.symbol = ''
        self.side = Side.NONE
        self.clorder_id = -sys.maxsize
        self.qty = 0
        self.price = -sys.maxsize
        self.order_type = ''
        self.order_status = ''
        self.time_in_force = None
        self.order_id = None
        self.orig_qty = 0
        self.cum_qty = 0


@dataclass
class Fill(PooledObject):
    order_id: str
    side: Side
    qty: float
    symbol: str
    price: float
    time: float

    @staticmethod
    def create_empty(*args):
        return Fill('', Side.NONE, 0, '', -sys.maxsize, -sys.maxsize)

    def init(self, order_id, side, qty, symbol, price, _time):
        self.order_id = order_id
        self.side = side
        self.qty = qty
        self.symbol = symbol
        self.price = price
        self.time = _time
        return self

    def clean(self):
        self.order_id = ''
        self.side = Side.NONE
        self.qty = 0
        self.symbol = ''
        self.price = -sys.maxsize
        self.time = -sys.maxsize


@dataclass
class Position:
    qty: float
    symbol: str
    avg_price: Optional[float]

