import time

from .book import Book
from kraken import SymbolConfig, KrakApp

from common import Side, Order, Quote, WorkingOrderBook

class StupidScalperStrategy:
    def __init__(self, app:KrakApp, symbol_config:SymbolConfig):
        self._app = app
        self._symbol_config = symbol_config

        #
        self.last_bid:Union[Quote|None] = None
        self.last_ask:Union[Quote|None] = None

        #
        self._has_sent_order = False
        self._orig_time = time.time()
        self._orig_clorderid = 100000000

    async def update(self):
        best_bid:Quote = self._app._book.best_bid()
        best_ask:Quote = self._app._book.best_ask()

        if not self._has_sent_order and  time.time() - self._orig_time > 5:
            order:Order = Order(
                self._symbol_config.name,
                Side.SELL,
                str(self._orig_clorderid + 1),
                0.0001,
                best_ask.price + 10,
                'limit',
                'pendingNew',
                'GTC'
            )
            await self._app.new_order_single(order)
            self._has_sent_order = True

        self.last_bid = best_bid
        self.last_ask = best_ask

