import time
from typing import Optional

from .strategy import StupidScalperStrategy
from .book import Book
from kraken import (
    MarketDataSnapshot, 
    SubscriptionStatus, 
    MarketDataUpdate, 
    SymbolConfigMap,
    CancelAllStatus,
    TradeUpdate, 
    SystemState,
    KrakApp
)
from common import (
    Side,
    Order, 
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
        self._executor:Executor = Executor(self._workingorders)
        self._strategy:StupidScalperStrategy = StupidScalperStrategy(self, SymbolConfigMap['XBT/USD'])

    @logger
    async def on_connect(self) -> None:
        pass

    async def on_market_data_snapshot(self, snapshot:MarketDataSnapshot) -> None:
        self._book = Book(snapshot.pair, snapshot.quotes)

    async def on_market_data(self, update:MarketDataUpdate) -> None:
        self._book.update(update)
        await self._strategy.update()

    async def on_trade(self, trade:TradeUpdate) -> None:
        pass

    @logger
    async def on_subscription_status(self, status:SubscriptionStatus) -> None:
        pass

    @logger
    async def on_system_status(self, state:SystemState) -> None:
        pass

    @logger
    async def on_new_order_single(self, order:Order) -> None: 
        pass

    @logger
    async def on_replace_order(self, order:Order) -> None: 
        pass

    @logger
    async def on_cancel_order(self, order:Order) -> None: 
        pass

    @logger
    async def on_pending_order(self, pending:Order) -> None: 
        self._workingorders.add_pending(pending)

    @logger
    async def on_new_order_ack(self, order_id: str) -> None:
        self._workingorders.new_order_ack(order_id)

    @logger
    async def on_replace_order_ack(self, order_id: str) -> None:
        self._workingorders.replace_order_ack(order_id)

    @logger
    async def on_cancel_order_ack(self, order_id: str) -> None:
        self._workingorders.cancel_order_ack(order_id)

    @logger
    async def on_new_order_reject(self, OrderStatus: str) -> None:
        pass

    @logger
    async def on_replace_order_reject(self, OrderStatus: str) -> None:
        pass

    @logger
    async def on_cancel_order_reject(self, OrderStatus: str) -> None:
        pass

    @logger
    async def on_fill(self, js:str) -> None:
        pass

    @logger
    async def on_cancel_all(self, status: CancelAllStatus) -> None:
        pass

