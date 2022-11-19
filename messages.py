from typing import Union, List

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


class SubscriptionStatus:
    def __init__(
        self,
        js: dict
    ):
        self._js:dict = js
        self.channelName:Union[str|None] = js['channelName'] if 'channelName' in js.keys() else None
        self.event:str = js['event']
        self.pair:List[str] = js['pair']
        self.status:str = js['status']

        self.channelID:Union[int|None] = js['channelID'] if 'channelID' in js.keys() else None
        self.errorMessage:Union[str|None] = js['errorMessage'] if 'errorMessage' in js.keys() else None

    def __repr__(self):
        string:str = f'{self.event}: {self.status} -> {self.channelName}|{self.pair}'
        if self.channelID:
            string += f' ({self.channelID})'
        if self.errorMessage:
            string += f' ({self.errorMessage})'
        return string


class SystemState:
    def __init__(
        self, 
        connectionID:int,
        event:str, 
        status:str, 
        version:str
    ):
        self.connectionID = connectionID
        self.event = event
        self.status = status
        self.version = version

    def __repr__(self):
        return f'{self.event}: {self.status} ({self.version})'

