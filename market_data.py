from typing import List
from quote import Quote, SnapshotQuotes

class MarketDataUpdate:
    def __init__(
        self,
        channelID: int,
        quotes: List[Quote],
        channelName: str,
        pair: str
    ):
        self.keys:List[str] = quotes.keys()
        self.is_bid:bool = True if 'b' in self.keys else False

        self.channelID = channelID
        self.quotes = self._crack(quotes)
        self.channelName = channelName
        self.pair = pair

    def _crack(self, quotes: List) -> List[Quote]:
        if self.is_bid:
            return [ Quote(q[0], q[1], q[2]) for q in quotes['b'] ]
        else:
            return [ Quote(q[0], q[1], q[2]) for q in quotes['a'] ]

    def __repr__(self):
        return f'{self.quotes}'


class MarketDataSnapshot:
    def __init__(
        self,
        channelID: int,
        quotes: SnapshotQuotes,
        channelName: str,
        pair: str
    ):
        self.channelID = channelID
        self.quotes = SnapshotQuotes(quotes['bs'], quotes['as'])
        self.channelName = channelName
        self.pair = pair

    def __repr__(self):
        return f'{self.quotes.bids} {self.quotes.asks}'

