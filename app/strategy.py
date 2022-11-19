import time

from .book import Book
from kraken import SymbolConfig, KrakApp

from common import Quote, WorkingOrderBook

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

    async def update(self):
        best_bid:Quote = self._app._book.best_bid()
        best_ask:Quote = self._app._book.best_ask()

        if not self._has_sent_order and  time.time() - self._orig_time > 60:
            await self._app.new_order_single(
                'buy',
                'limit',
                self._symbol_config.name,
                best_bid.price - self._symbol_config.tick_size * 5,
                0.0001 
            )
            self._has_sent_order = True

        if (self.last_bid and self.last_ask):
            if best_bid != self.last_bid or best_ask != self.last_ask:
                print(best_bid, '|', best_ask)
        
        self.last_bid = best_bid
        self.last_ask = best_ask

