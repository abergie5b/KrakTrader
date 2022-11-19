import math
from typing import List

from quote import Quote

def vwap(quotes:List[Quote], depth:int = 10) -> Quote:
    nQuotes:int = len(quotes)
    if depth > nQuotes:
        depth = nQuotes
    quote = Quote(-math.inf, 0, time.time())

    qty = 0
    accumPrice = 0
    for x in range(depth):
        qty += quotes[x].volume
        accumPrice += quotes[x].volume * quotes[x].price

    if qty > 0:
        quote.volume = qty
        quote.price = accumPrice / qty
    return quote

