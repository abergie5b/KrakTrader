import time
from typing import Optional

import app
from .book import Book
from kraken import SymbolConfig

from common import Side, Order, Quote, WorkingOrderBook

class StupidScalperStrategy:
    def __init__(self, krak_app:app.KrakTrader, symbol_config:SymbolConfig):
        self._app = krak_app
        self._symbol_config = symbol_config

        #
        self.last_bid:Optional[Quote] = None
        self.last_ask:Optional[Quote] = None

        #
        self._has_sent_order = False
        self._has_replaced_order = False
        self._has_canceled_order = False

    async def update(self) -> None:
        if self._app._book:
            best_bid:Quote = self._app._book.best_bid()
            best_ask:Quote = self._app._book.best_ask()

            if not self._has_sent_order:
                order:Order = Order(
                    self._symbol_config.name,
                    Side.SELL,
                    None,
                    0.0001,
                    best_ask.price + 100,
                    'limit',
                    'pendingNew',
                    'GTC'
                )
                await self._app.new_order_single(order)
                self._has_sent_order = True

            elif not len(self._app._workingorders.pendings):
                if not self._has_replaced_order:
                    for order_id, order in self._app._workingorders.orders.items():
                        await self._app.replace_order(order, best_ask.price + 105, order.qty)
                        self._has_replaced_order = True

                elif self._has_replaced_order and not self._has_canceled_order:
                    for order_id, order in self._app._workingorders.orders.items():
                        await self._app.cancel_order(order)
                    self._has_canceled_order = True

            if self.last_bid and self.last_ask and \
               (self.last_bid != best_bid or self.last_ask != best_ask):
                print(best_bid, best_ask)

            self.last_bid = best_bid
            self.last_ask = best_ask

