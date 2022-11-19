import time
from enum import Enum
from typing import Dict, Callable

from .websocket_client import WebsocketClient, WebsocketHandler

class Quote:
    def __init__(
        self,
        price: float,
        volume: float,
        timestamp: float
    ):
        self.price = float(price)
        self.volume = float(volume)
        self.timestamp = float(timestamp)

    def __eq__(self, other):
        return self.price == other.price and \
               self.volume == other.volume and \
               self.timestamp == other.timestamp

    def __repr__(self):
        return f'{self.timestamp}: {self.volume} @ {self.price}'


class Trade:
    def __init__(
        self,
        price: float,
        volume: float,
        time: float,
        side: str,
        orderType: str
    ):
        self.price = float(price)
        self.volume = float(volume)
        self.time = float(time)
        self.side = side
        self.orderType = orderType

    def __repr__(self):
        return f'{self.time}: {self.side} {self.volume} @ {self.price}'


class Side(Enum):
    BUY = 1,
    SELL = 2
    

class OrderStatus(Enum):
    NONE = None,
    NEW = 'new',
    REPLACED = 'replaced',
    CANCELED = 'canceled'

class Order:
    def __init__(
        self,
        symbol:str,
        side:Side,
        clorder_id:int,
        qty:int,
        price:float,
        order_type:str
    ):
        self.symbol = symbol
        self.side = side
        self.clorder_id = int(clorder_id)
        self.orig_qty = qty
        self.qty = qty
        self.cum_qty = 0
        self.price = price
        self.order_type = order_type

        #  todo
        self.time_in_force:None = None

        self.order_status:OrderStatus = OrderStatus.NONE
        self.order_id:Union[str|None] = None

    def __repr__(self):
        side_str:str = 'buy' if self.side == Side.BUY else 'sell'
        return f'{self.order_type} {side_str} {self.qty} {self.symbol} @ {self.price}'


class WorkingOrderBook:
    def __init__(self): 
        self.bids:Dict[str, Order] = {}
        self.asks:Dict[str, Order] = {}
        self.pending_bids:Dict[str, Order] = {}
        self.pending_asks:Dict[str, Order] = {}

    def get_orders(self, side:Side) -> Dict[str, Order]:
        return self.bids if side == Side.BUY else self.asks

    def get_pending_orders(self, side:Side) -> Dict[str, Order]:
        return self.pending_bids if side == Side.BUY else self.pending_asks

    def add_pending(self, order:Order) -> None:
        orders:Dict[str, Order] = self.get_pending_orders(order.side)
        orders[order.clorder_id] = order

    def new_order(self, order:Order) -> None: 
        pendings:Dict[str, Order] = self.get_pending_orders(order.side)
        pending:Order = pendings.pop(order.clorder_id, None)
        if not pending:
            print(f'pending order not found for {order.order_id}')
        else:
            orders:Dict[str, Order] = self.get_orders(order.side)
            orders[order.order_id] = order

    def replace_order(self, replace:Order): 
        pendings:Dict[str, Order] = self.get_pending_orders(replace.side)
        pending:Order = pendings.pop(replace.clorder_id, None)
        if not pending:
            print(f'pending order not found for {order.order_id}')
        else:
            orders:Dict[str, Order] = self.get_orders(order.side)
            order:Order = orders.get(order.order_id)

            order.order_status = OrderStatus.REPLACED
            order.clorder_id = replace.clorder_id
            order.qty = replace.qty
            order.price = replace.price

    def cancel_order(self, cancel:Order) -> None: 
        pendings:Dict[str, Order] = self.get_pending_orders(cancel.side)
        pending:Order = pendings.pop(cancel.clorder_id, None)
        if not pending:
            print(f'pending order not found for {order.order_id}')
        else:
            orders:Dict[str, Order] = self.get_orders(order.side)
            orders.pop(cancel.order_id, None)

    def fill(self, fill:Order) -> None:
        orders:Dict[str, Order] = self.get_orders(fill.side)
        order:Order = orders.get(fill.order_id)
        order.qty -= fill.qty
        order.cum_qty += fill.qty
        if order.qty == 0:
            orders.pop(order.order_id)
        elif order.qty < 0:
            print(f'fill order has < 0 qty {order.order_id}')


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
                print(f'throttle prevented {func.__name__} from running')


class Executor:
    def __init__(self, workingorders:WorkingOrderBook):
        self._workingorders = workingorders
        self._throttle = Throttle(2)

    def new_order(self, fn:Callable, order:Order):
        pendings:Dict[str, Order] = self._workingorders.get_pending_orders(order.side)
        if not pendings.get(order.order_id):
            self._throttle.apply(fn, order)
        else:
            print(f'executor tried to send a new order that has a pending change')

    def replace_order(self, fn:Callable, order:Order):
        pendings:Dict[str, Order] = self._workingorders.get_pending_orders(order.side)  
        if not pendings.get(order.order_id):
            self._throttle.apply(fn, order)
        else:
            print(f'executor tried to send a replace order that has a pending change')

    def cancel_order(self, fn:Callable, order:Order):
        pendings:Dict[str, Order] = self._workingorders.get_pending_orders(order.side)  
        if not pendings.get(order.order_id):
            self._throttle.apply(fn, order)
        else:
            print(f'executor tried to send a cancel order that has a pending change')


