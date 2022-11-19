import json
import time
from typing import List, Union

from .book import Book
from kraken import (
    MarketDataSnapshot, 
    SubscriptionStatus, 
    MarketDataUpdate, 
    TradeUpdate, 
    SystemState,
    KrakApp
)


class KrakTrader(KrakApp):
    def __init__(self, url:str):
        super().__init__(url)
        self._book:Union[Book|None] = None

    def on_market_data_snapshot(self, snapshot:MarketDataSnapshot) -> None:
        self._book = Book(snapshot.quotes)

    def on_market_data(self, update:MarketDataUpdate) -> None:
        self._book.update(update)
        print(self._book)

    def on_trade(self, trade:TradeUpdate) -> None:
        print(trade)

    def on_subscription_status(self, status:SubscriptionStatus) -> None:
        print(status)

    def on_system_status(self, state:SystemState) -> None:
        print(state)

