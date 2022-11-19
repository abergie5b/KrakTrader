from typing import List

class Quote:
    def __init__(
        self,
        price: float,
        volume: float,
        timestamp: float
    ):
        self.price = float(price)
        self.volume = float(volume)
        self.timestamp = float(timestamp)

    def __eq__(self, other):
        return self.price == other.price and \
               self.volume == other.volume and \
               self.timestamp == other.timestamp

    def __repr__(self):
        return f'{self.timestamp}: {self.volume} @ {self.price}'


class SnapshotQuotes:
    def __init__(
        self,
        bids: List[Quote],
        asks: List[Quote]
    ):
        self.bids = self._crack(bids)
        self.asks = self._crack(asks)

    def _crack(self, quotes:List[float]) -> List[Quote]:
        return [ Quote(q[0], q[1], q[2]) for q in quotes ]


