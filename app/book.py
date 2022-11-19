import bisect
from typing import List, Callable

from kraken import (
    MarketDataUpdate,
    SnapshotQuotes,
    Quote, 
)

class Book:
    def __init__(
        self,
        snapshot: SnapshotQuotes
    ):
        self.bids:List[Quote] = [ bid for bid in snapshot.bids if bid.volume != 0 ]
        self.asks:List[Quote] = [ ask for ask in snapshot.asks if ask.volume != 0 ]

    def update(self, md_update:MarketDataUpdate) -> None:
        if md_update.is_bid:
            self._update_bids(md_update)
        else:
            self._update_asks(md_update)

    def best_bid(self) -> Quote:
        return self.bids[0]

    def best_ask(self) -> Quote:
        return self.asks[0]

    def __repr__(self):
        book:str = ''
        for ask in self.asks[::-1]:
            book += f'\t\t{ask.price}\t{ask.volume}\n'
        for bid in self.bids:
            book += f'{bid.volume}\t{bid.price}\n'
        return book

    def _update_book(self, quote:Quote, quotes:List[Quote], is_bid:bool) -> None:
        for order in quotes:
            # update volume on level
            if order.price == quote.price:
                if quote.volume == 0:
                    quotes.remove(order)
                else:
                    order.volume = quote.volume
                return

        # quote needs to be placed in book
        # todo organize bids / asks more efficiently
        if is_bid:
            key:Callable = lambda q: -1 * q.price
        else:
            key:Callable = lambda q: q.price
        bisect.insort(quotes, quote, key=key)

        # todo bisect first to find index
        self.bids = self.bids[:10]
        self.asks = self.asks[:10]

    def _update_bids(self, bids:MarketDataUpdate) -> None:
        for quote in bids.quotes:
            self._update_book(quote, self.bids, True)

    def _update_asks(self, asks:MarketDataUpdate) -> None:
        for quote in asks.quotes:
            self._update_book(quote, self.asks, False)

