from typing import List

class Trade:
    def __init__(
        self,
        price: float,
        volume: float,
        time: float,
        side: str,
        orderType: str
    ):
        self.price = float(price)
        self.volume = float(volume)
        self.time = float(time)
        self.side = side
        self.orderType = orderType

    def __repr__(self):
        return f'{self.time}: {self.side} {self.volume} @ {self.price}'


class TradeUpdate:
    def __init__(
        self,
        channelID: int,
        trades: List[Trade],
        channelName: str,
        pair: str
    ):
        self.channelID = channelID
        self.trades = self._crack(trades)
        self.channelName = channelName
        self.pair = pair

    def _crack(self, trades: List) -> List[Trade]:
        return [ Trade(t[0], t[1], t[2], t[3], t[4]) for t in trades ]

    def __repr__(self):
        return f'{self.trades}'

