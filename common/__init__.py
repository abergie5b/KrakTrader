import sys
import time
import math
from enum import Enum
from dataclasses import dataclass, field, InitVar
from typing import (
    Any,
    List,
    Dict,
    Tuple,
    Union,
    Optional,
    Callable
)

from .websocket_client import WebsocketClient, WebsocketHandler
from .logger import get_logger


class Side(Enum):
    BUY = 1,
    SELL = 2


@dataclass
class Quote:
    _price: InitVar[float]
    _volume: InitVar[float]
    _timestamp: InitVar[float]

    price: float = field(init=False)
    volume: float = field(init=False)
    timestamp: float = field(init=False)

    def __post_init__(self, _price, _volume, _timestamp):
        self.price = float(_price)
        self.volume = float(_volume)
        self.timestamp = float(_timestamp)

    def __eq__(self, other):
        return self.price == other.price and \
               self.volume == other.volume and \
               self.timestamp == other.timestamp


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
class Order:
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

    def __post_init__(self, _qty, _price):
        self.qty = float(_qty)
        self.price = float(_price)
        self.order_id = None
        self.orig_qty = self.qty
        self.cum_qty = 0


@dataclass
class Fill:
    order_id: str
    side: Side
    qty: float
    symbol: str
    price: float
    time: float


class WorkingOrderBook:
    def __init__(self) -> None:
        self.orders: Dict[str, Order] = {}
        self.pendings: Dict[Union[int | str], Order] = {}
        self._canceled_order_ids: List[str] = []
        self._logger = get_logger(f'{__name__}.working_orders')

    def on_open_order_pending(self, order: Order) -> None:
        if order.order_id:
            self.pendings[order.order_id] = order
        else:
            self._logger.warning(f'received pending order with None order_id {order}')

    def on_open_order_new(self, order_id: str):
        order: Optional[Order] = self.pendings.pop(order_id, None)
        if order:
            self.orders[order_id] = order
        else:
            self._logger.warning(f'open_order_new: failed to find pending order_id for {order_id}')

    def on_open_order_cancel(self, order_id: str):
        if order_id not in self._canceled_order_ids:
            order: Optional[Order] = self.orders.pop(order_id, None)
            if order:
                self._canceled_order_ids.append(order_id)
            else:
                self._logger.warning(f'open_order_cancel: failed to find order_id {order_id}')

    def on_pending(self, order: Order) -> None:
        if order.clorder_id != -sys.maxsize:
            self.pendings[order.clorder_id] = order
        else:
            self._logger.warning(f'received pending order with None clorder_id {order}')

    def remove_pending(self, clorder_id: Optional[int]) -> None:
        if not clorder_id:
            self._logger.warning(f'failed to remove pending order with None clorder_id')
        else:
            order: Optional[Order] = self.pendings.pop(clorder_id, None)
            if not order:
                self._logger.warning(f'failed to remove pending order: {clorder_id}')

    def new_order_ack(self, order_id: Optional[str], clorder_id: int) -> None:
        pending: Optional[Order] = self.pendings.pop(clorder_id, None)
        if not pending:
            self._logger.warning(f'pending order not found for {clorder_id}')
        else:
            if order_id:
                pending.order_id = order_id
                self.orders[order_id] = pending
            else:
                self._logger.warning(f'new_order_ack received pending with None order_id {pending}')

    def replace_order_ack(self, order_id: Optional[str], clorder_id: int):
        pending: Optional[Order] = self.pendings.pop(clorder_id, None)
        if not pending or not pending.clorder_id:
            self._logger.warning(f'pending order not found for {clorder_id}')
        else:
            if pending.order_id:
                order: Optional[Order] = self.orders.get(pending.order_id, None)
                if not order:
                    self._logger.warning(f'failed to find replaced order {pending.order_id}')
                else:
                    order.order_status = 'replaced'
                    order.order_id = order_id
                    order.clorder_id = pending.clorder_id
                    order.qty = pending.qty
                    order.price = pending.price
            else:
                self._logger.warning(f'replace_order_ack received pending with None order_id {pending}')

    def cancel_order_ack(self, clorder_id: int) -> None:
        pending: Optional[Order] = self.pendings.pop(clorder_id, None)
        if not pending:
            self._logger.warning(f'pending order not found for {clorder_id}')
        else:
            if pending.order_id:
                if pending.order_id not in self._canceled_order_ids:
                    order: Optional[Order] = self.orders.pop(pending.order_id, None)
                    if not order:
                        self._logger.warning(f'failed to find canceled order {pending.order_id}')
                    else:
                        self._canceled_order_ids.append(pending.order_id)
            else:
                self._logger.warning(f'cancel_order_ack received pending with None order_id {pending}')

    def fill(self, fill: Fill) -> None:
        if fill.order_id:
            order: Optional[Order] = self.orders.get(fill.order_id)
            if order and order.order_id:
                order.qty -= fill.qty
                order.cum_qty += fill.qty
                if order.qty == 0:
                    self.orders.pop(order.order_id)
                elif order.qty < 0:
                    self._logger.warning(f'fill order has < 0 qty {order.order_id}')
            else:
                self._logger.warning(f'failed to find order for fill: {fill}')
        else:
            self._logger.warning(f'received fill without an order id: {fill}')

    def cancel_all(self) -> None:
        self.orders.clear()


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


class Executor:
    def __init__(self, workingorders: WorkingOrderBook):
        self._workingorders = workingorders
        self._throttle = Throttle(2)
        self._logger = get_logger(f'{__name__}.executor')

    def new_order(self, fn: Callable, order: Order):
        if order.clorder_id and not self._workingorders.pendings.get(order.clorder_id):
            self._throttle.apply(fn, order)
        else:
            self._logger.warning(f'tried to send a new order that has a pending change')

    def replace_order(self, fn: Callable, order: Order):
        if order.clorder_id and not self._workingorders.pendings.get(order.clorder_id):
            self._throttle.apply(fn, order)
        else:
            self._logger.warning(f'tried to send a replace order that has a pending change')

    def cancel_order(self, fn: Callable, order: Order):
        if order.clorder_id and not self._workingorders.pendings.get(order.clorder_id):
            self._throttle.apply(fn, order)
        else:
            self._logger.warning(f'tried to send a cancel order that has a pending change')


class FinMath:
    @staticmethod
    def vwap(quotes: List[Quote], depth: int = 10) -> Quote:
        n_quotes: int = len(quotes)
        if depth > n_quotes:
            depth = n_quotes
        quote = Quote(-math.inf, 0, time.time())

        qty: float = 0
        accum_price: float = 0
        for x in range(depth):
            qty += quotes[x].volume
            accum_price += quotes[x].volume * quotes[x].price

        if qty > 0:
            quote.volume = qty
            quote.price = accum_price / qty
        return quote

