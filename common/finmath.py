import math
import time
from typing import List

from . import Quote


class FinMath:
    @staticmethod
    def vwap(quotes: List[Quote], depth: int = 10) -> Quote:
        n_quotes: int = len(quotes)
        if depth > n_quotes:
            depth = n_quotes
        quote = Quote(-math.inf, 0, time.time())

        qty: float = 0
        accum_price: float = 0
        for x in range(depth):
            qty += quotes[x].volume
            accum_price += quotes[x].volume * quotes[x].price

        if qty > 0:
            quote.volume = qty
            quote.price = accum_price / qty
        return quote

