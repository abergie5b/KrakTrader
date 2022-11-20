import time
from enum import Enum
from dataclasses import dataclass, field, InitVar
from typing import Dict, Callable, Optional

from .websocket_client import WebsocketClient, WebsocketHandler

class Side(Enum):
    BUY = 1,
    SELL = 2
    

@dataclass
class Quote:
    price: InitVar[float]
    volume: InitVar[float]
    timestamp: InitVar[float]

    def __post_init__(self, price, volume, timestamp):
        self.price = float(price)
        self.volume = float(volume)
        self.timestamp = float(timestamp)

    def __eq__(self, other):
        return self.price == other.price and \
               self.volume == other.volume and \
               self.timestamp == other.timestamp


@dataclass
class Trade:
    price: InitVar[float]
    volume: InitVar[float]
    time: InitVar[float]
    side: InitVar[str]
    orderType: InitVar[str]

    def __post_init__(self, price, volume, time, side, orderType):
        self.price = float(price)
        self.volume = float(volume)
        self.time = float(time)
        self.side = side
        self.orderType = orderType


@dataclass
class Order:
    symbol:str
    side:Side
    clorder_id:str
    qty:int
    price:float
    order_type:str
    order_status:str
    time_in_force:Optional[str]

    order_id:Optional[str] = field(init=False)
    orig_qty:int = field(init=False)
    cum_qty:int = field(init=False)

    def __post_init__(self):
        self.order_id = None
        self.orig_qty = self.qty
        self.cum_qty = 0


class WorkingOrderBook:
    def __init__(self): 
        self.orders:Dict[str, Order] = {}
        self.pendings:Dict[str, Order] = {}

    def add_pending(self, order:Order) -> None:
        print(f'workingorders -> add_pending {order}')
        self.pendings[order.order_id] = order

    def new_order_ack(self, order_id:str) -> None: 
        print(f'workingorders -> new_order {order_id}')
        pending:Order = self.pendings.pop(order_id, None)
        if not pending:
            print(f'workingorders -> pending order not found for {order_id}')
        else:
            pending.order_id = order_id
            self.orders[order_id] = pending

    def replace_order_ack(self, order_id:str): 
        print(f'workingorders -> replace_order {order_id}')
        pending:Order = self.pendings.pop(order_id, None)
        if not pending:
            print(f'workingorders -> pending order not found for {order_id}')
        else:
            order:Order = self.orders.get(order_id)
            if not order:
                print(f'workingorders -> failed to find replaced order {order_id}')
            else:
                order.order_status = 'replaced'
                order.clorder_id = pending.clorder_id
                order.qty = pending.qty
                order.price = pending.price

    def cancel_order_ack(self, order_id:str) -> None: 
        print(f'workingorders -> cancel_order {order_id}')
        pending:Order = self.pendings.pop(order_id, None)
        if not pending:
            print(f'workingorders -> pending order not found for {order_id}')
        else:
            if not self.orders.pop(cancel.order_id, None):
                print(f'workingorders -> failed to find canceled order {order_id}')

    def fill(self, fill:Order) -> None:
        print(f'workingorders -> fill_order {fill}')
        order:Order = self.orders.get(fill.order_id)
        order.qty -= fill.qty
        order.cum_qty += fill.qty
        if order.qty == 0:
            orders.pop(order.order_id)
        elif order.qty < 0:
            print(f'workingorders -> fill order has < 0 qty {order.order_id}')


class Throttle:
    def __init__(self, max_messages_per_sec:int):
        self._cache:Dict[str, float] = {}
        self._max_messages_per_sec = max_messages_per_sec

    def _fire(self, func:Callable, *args):
        func(*args)
        self._cache[func.__name__] = time.time()
    
    def apply(self, func:Callable, *args):
        cached:int = self._cache.get(func.__name__, None)
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
        pendings:Dict[str, Order] = self._workingorders.pendings(order.side)
        if not pendings.get(order.order_id):
            self._throttle.apply(fn, order)
        else:
            print(f'executor -> tried to send a new order that has a pending change')

    def replace_order(self, fn:Callable, order:Order):
        pendings:Dict[str, Order] = self._workingorders.pendings(order.side)  
        if not pendings.get(order.order_id):
            self._throttle.apply(fn, order)
        else:
            print(f'executor -> tried to send a replace order that has a pending change')

    def cancel_order(self, fn:Callable, order:Order):
        pendings:Dict[str, Order] = self._workingorders.pendings(order.side)  
        if not pendings.get(order.order_id):
            self._throttle.apply(fn, order)
        else:
            print(f'executor -> tried to send a cancel order that has a pending change')


