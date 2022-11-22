import time
from typing import Any, List, Callable, Coroutine, Optional

import app
from .book import Book
from kraken import (
    MarketDataSnapshot, 
    SubscriptionStatus, 
    MarketDataUpdate, 
    SymbolConfigMap,
    CancelAllStatus,
    OrderStatus,
    TradeUpdate, 
    SystemState,
    KrakApp
)
from common import (
    Side,
    Fill,
    Order, 
    Trade,
    Executor,
    WorkingOrderBook
)

def logger(f):
    async def _wraps(*args):
        print(f'{f.__name__} -> {args[1:]}')
        await f(*args)
    return _wraps

class KrakTrader(KrakApp):
    def __init__(
        self, 
        url:str,
        auth_url:str, 
        http_url:str, 
        key:str, 
        secret:str
    ):
        super().__init__(url, auth_url, http_url, key, secret)
        self._book:Optional[Book] = None
        self._workingorders:WorkingOrderBook = WorkingOrderBook()
        self._strategy:app.StupidScalperStrategy = app.StupidScalperStrategy(self, SymbolConfigMap['XBT/USD'])
        self._trade_monitor:app.TradeMonitor = app.TradeMonitor(SymbolConfigMap['XBT/USD'])

    @logger
    async def on_connect(self) -> None:
        pass

    async def on_market_data_snapshot(self, snapshot:MarketDataSnapshot) -> None:
        self._book = Book(snapshot.pair, snapshot.quotes)

    async def on_market_data(self, update:MarketDataUpdate) -> None:
        if self._book:
            self._book.update(update)
            await self._strategy.update()

    @logger
    async def on_trade(self, trade:Trade) -> None:
        self._trade_monitor.update(trade)

    @logger
    async def on_subscription_status(self, status:SubscriptionStatus) -> None:
        pass

    @logger
    async def on_system_status(self, state:SystemState) -> None:
        pass

    @logger
    async def on_pending_order(self, pending:Order) -> None: 
        pass

    @logger
    async def on_open_order(self, order_id:str) -> None:
        pass

    @logger
    async def on_replaced_order(self, order_id:str) -> None:
        pass

    @logger
    async def on_canceled_order(self, order_id:str) -> None:
        pass

    @logger
    async def on_new_order_single(self, pending:Order) -> None: 
        self._workingorders.add_pending(pending)

    @logger
    async def on_replace_order(self, pending:Order) -> None: 
        self._workingorders.add_pending(pending)

    @logger
    async def on_cancel_order(self, pending:Order) -> None: 
        self._workingorders.add_pending(pending)

    @logger
    async def on_new_order_ack(self, order_id:Optional[str], clorder_id: int) -> None:
        self._workingorders.new_order_ack(order_id, clorder_id)

    @logger
    async def on_replace_order_ack(self, order_id:Optional[str], clorder_id: int) -> None:
        self._workingorders.replace_order_ack(order_id, clorder_id)

    @logger
    async def on_cancel_order_ack(self, clorder_id: int) -> None:
        self._workingorders.cancel_order_ack(clorder_id)

    @logger
    async def on_new_order_reject(self, status: OrderStatus) -> None:
        self._workingorders.remove_pending(status.reqid)

    @logger
    async def on_replace_order_reject(self, status: OrderStatus) -> None:
        self._workingorders.remove_pending(status.reqid)

    @logger
    async def on_cancel_order_reject(self, status: OrderStatus) -> None:
        self._workingorders.remove_pending(status.reqid)

    @logger
    async def on_fill(self, fill:Fill) -> None:
        self._workingorders.fill(fill)

    @logger
    async def on_cancel_all(self, status: CancelAllStatus) -> None:
        pass

