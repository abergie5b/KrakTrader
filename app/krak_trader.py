import time
from typing import Union

from .strategy import StupidScalperStrategy
from .book import Book
from kraken import (
    MarketDataSnapshot, 
    SubscriptionStatus, 
    MarketDataUpdate, 
    SymbolConfigMap,
    TradeUpdate, 
    SystemState,
    KrakApp
)
from common import (
    Order, 
    Executor,
    WorkingOrderBook
)


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
        self._book:Union[Book|None] = None
        self._workingorders:WorkingOrderBook = WorkingOrderBook()
        self._executor:Executor = Executor(self._workingorders)
        self._strategy = StupidScalperStrategy(self, SymbolConfigMap['XBT/USD'])

    async def on_market_data_snapshot(self, snapshot:MarketDataSnapshot) -> None:
        self._book = Book(snapshot.pair, snapshot.quotes)

    async def on_market_data(self, update:MarketDataUpdate) -> None:
        self._book.update(update)
        await self._strategy.update()

    async def on_trade(self, trade:TradeUpdate) -> None:
        pass

    async def on_subscription_status(self, status:SubscriptionStatus) -> None:
        print(status)

    async def on_system_status(self, state:SystemState) -> None:
        print(state)

    async def on_new_order(self, order:Order) -> None: 
        pass

    async def on_replace_order(self, order:Order) -> None: 
        pass

    async def on_cancel_order(self, order:Order) -> None: 
        pass

    async def on_fill(self, order:Order) -> None:
        pass

    async def new_order(self, order:Order) -> None:
        self._workingorders.new_order(order)

    async def replace_order(self, order:Order) -> None:
        self._workingorders.new_order(order)

    async def cancel_order(self, order:Order) -> None:
        self._workingorders.new_order(order)

    async def new_order_single(self, side:str, order_type:str, pair:str, price:float, qty:float):
        await super().new_order_single(side, order_type, pair, price, qty)
        order:Order = Order(pair, side, time.time(), qty, price, order_type)
        self._workingorders.add_pending(order)
        print(f'new order single -> {order}')

    async def replace_order(self, order_id:str, pair:str, order_type:str, price:float, qty:float):
        await super().replace_order(order_id, pair, order_type, price, qty)
        order:Order = Order(pair, side, time.time(), qty, price, order_type)
        self._workingorders.add_pending(order)

    async def cancel_order(self, order_id:str):
        await super().cancel_order(order_id)
        order:Order = Order(pair, side, time.time(), qty, price, order_type)
        self._workingorders.add_pending(order)

