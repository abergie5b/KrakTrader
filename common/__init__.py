import time
from enum import Enum
from dataclasses import dataclass, field, InitVar
from typing import Any, List, Dict, Tuple, Callable, Optional

from .websocket_client import WebsocketClient, WebsocketHandler

class Side(Enum):
    BUY = 1,
    SELL = 2
    

@dataclass
class Quote:
    _price: InitVar[float]
    _volume: InitVar[float]
    _timestamp: InitVar[float]

    price:float = field(init=False)
    volume:float = field(init=False)
    timestamp:float = field(init=False)

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
    _orderType: InitVar[str]

    price:float = field(init=False)
    volume:float = field(init=False)
    time:float = field(init=False)
    side:str = field(init=False)
    orderType:str = field(init=False)

    def __post_init__(self, _price, _volume, _time, _side, _orderType):
        self.price = float(_price)
        self.volume = float(_volume)
        self.time = float(_time)
        self.side = _side
        self.orderType = _orderType


@dataclass
class Order:
    symbol:str
    side:Side
    clorder_id:Optional[int]
    _qty:InitVar[float]
    qty:float = field(init=False)
    _price:InitVar[float]
    price:float = field(init=False)
    order_type:str
    order_status:str
    time_in_force:Optional[str]

    order_id:Optional[str] = field(init=False)
    orig_qty:float = field(init=False)
    cum_qty:float = field(init=False)

    def __post_init__(self, _qty, _price):
        self.qty = float(_qty)
        self.price = float(_price)
        self.order_id = None
        self.orig_qty = self.qty
        self.cum_qty = 0


@dataclass
class Fill:
    order_id:str
    side:Side
    qty:float
    symbol:str
    price:float
    time:float


class WorkingOrderBook:
    def __init__(self) -> None:
        self.orders:Dict[str, Order] = {}
        self.pendings:Dict[int, Order] = {}

    def add_pending(self, order:Order) -> None:
        print(f'workingorders -> add_pending {order}')
        if order.clorder_id:
            self.pendings[order.clorder_id] = order
        else:
            print(f'workingorders -> received pending order with None clorder_id')

    def remove_pending(self, clorder_id:Optional[int]) -> None:
        if not clorder_id:
            print(f'workingorders -> failed to remove pending order with None clorder_id')
        else:
            order:Optional[Order] = self.pendings.pop(clorder_id, None)
            if not order:
                print(f'workingorders -> failed to remove pending order: {clorder_id}')
            else:
                print(f'workingorders -> remove_pending {clorder_id}')

    def new_order_ack(self, order_id:Optional[str], clorder_id:int) -> None: 
        pending:Optional[Order] = self.pendings.pop(clorder_id, None)
        if not pending:
            print(f'workingorders -> pending order not found for {clorder_id}')
        else:
            if order_id:
                pending.order_id = order_id
                self.orders[order_id] = pending
                print(f'workingorders -> new_order {pending}')
            else:
                print(f'workingorders -> new_order_ack received pending with None order_id {pending}')

    def replace_order_ack(self, order_id:Optional[str], clorder_id:int): 
        pending:Optional[Order] = self.pendings.pop(clorder_id, None)
        if not pending or not pending.clorder_id:
            print(f'workingorders -> pending order not found for {clorder_id}')
        else:
            if pending.order_id:
                order:Optional[Order] = self.orders.get(pending.order_id, None)
                if not order:
                    print(f'workingorders -> failed to find replaced order {pending.order_id}')
                else:
                    print(f'workingorders -> replace_order {order}')
                    order.order_status = 'replaced'
                    order.order_id = order_id
                    order.clorder_id = pending.clorder_id
                    order.qty = pending.qty
                    order.price = pending.price
            else:
                print(f'workingorders -> replace_order_ack received pending with None order_id {pending}')

    def cancel_order_ack(self, clorder_id:int) -> None: 
        pending:Optional[Order] = self.pendings.pop(clorder_id, None)
        if not pending:
            print(f'workingorders -> pending order not found for {clorder_id}')
        else:
            if pending.order_id:
                order:Optional[Order] = self.orders.pop(pending.order_id, None)
                if not order:
                    print(f'workingorders -> failed to find canceled order {pending.order_id}')
                else:
                    print(f'workingorders -> cancel_order {order}')
            else:
                print(f'workingorders -> cancel_order_ack received pending with None order_id {pending}')

    def fill(self, fill:Fill) -> None:
        if fill.order_id:
            order:Optional[Order] = self.orders.get(fill.order_id)
            if order and order.order_id:
                order.qty -= fill.qty
                order.cum_qty += fill.qty
                print(f'workingorders -> fill_order {order}')
                if order.qty == 0:
                    self.orders.pop(order.order_id)
                elif order.qty < 0:
                    print(f'workingorders -> fill order has < 0 qty {order.order_id}')
            else:
                print(f'workingorders -> failed to find order for fill: {fill}')
        else:
            print(f'workingorders -> received fill without an order id: {fill}')


class Throttle:
    def __init__(self, max_messages_per_sec:int):
        self._cache:Dict[str, float] = {}
        self._max_messages_per_sec = max_messages_per_sec

    def _fire(self, func:Callable, *args: Tuple[Any, ...]) -> None:
        func(*args)
        self._cache[func.__name__] = time.time()
    
    def apply(self, func:Callable, *args) -> None:
        cached:Optional[float] = self._cache.get(func.__name__, None)
        if not cached:
            self._fire(func, args)
        else:
            elapsed:float = time.time() - cached
            if elapsed > 1 / self._max_messages_per_sec:
                self._fire(func, args)
            else:
                print(f'throttle -> prevented {func.__name__} from running')


class Executor:
    def __init__(self, workingorders:WorkingOrderBook):
        self._workingorders = workingorders
        self._throttle = Throttle(2)

    def new_order(self, fn:Callable, order:Order):
        if order.clorder_id and not self._workingorders.pendings.get(order.clorder_id):
            self._throttle.apply(fn, order)
        else:
            print(f'executor -> tried to send a new order that has a pending change')

    def replace_order(self, fn:Callable, order:Order):
        if order.clorder_id and not self._workingorders.pendings.get(order.clorder_id):
            self._throttle.apply(fn, order)
        else:
            print(f'executor -> tried to send a replace order that has a pending change')

    def cancel_order(self, fn:Callable, order:Order):
        if order.clorder_id and not self._workingorders.pendings.get(order.clorder_id):
            self._throttle.apply(fn, order)
        else:
            print(f'executor -> tried to send a cancel order that has a pending change')


