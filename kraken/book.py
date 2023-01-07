import bisect
from typing import List, Callable

from . import (
    BookUpdate,
    BookSnapshot
)
from common import (
    Quote,
    get_logger
)


class Book:
    def __init__(
        self,
        snapshot: BookSnapshot
    ):
        self.symbol = snapshot.pair
        self.bids: List[Quote] = [bid for bid in snapshot.snapshot.bs if bid.volume != 0]
        self.asks: List[Quote] = [ask for ask in snapshot.snapshot.as_ if ask.volume != 0]

        self._logger = get_logger(__name__)

    def update(self, md_update: BookUpdate) -> None:
        for quote in md_update.b:
            self._update_book(quote, self.bids, True)
        for quote in md_update.a:
            self._update_book(quote, self.asks, False)

    def best_bid(self) -> Quote:
        return self.bids[0]

    def best_ask(self) -> Quote:
        return self.asks[0]

    def __repr__(self) -> str:
        book: str = ''
        for ask in self.asks[::-1]:
            book += f'\t\t{ask.price}\t{ask.volume}\n'
        for bid in self.bids:
            book += f'{bid.volume}\t{bid.price}\n'
        return book

    def _update_book(self, quote: Quote, quotes: List[Quote], is_bid: bool) -> None:
        for x in range(len(quotes)):
            order = quotes[x]
            # update volume on level
            if order.price == quote.price:
                if quote.volume == 0:
                    quotes.pop(x)
                else:
                    order.volume = quote.volume
                return

        # quote needs to be placed in book
        # todo organize bids / asks more efficiently
        key: Callable = lambda q: q.price
        if is_bid:
            key = lambda q: -1 * q.price
        bisect.insort(quotes, quote, key=key)

        # todo bisect first to find index
        self.bids = self.bids[:10]
        self.asks = self.asks[:10]
