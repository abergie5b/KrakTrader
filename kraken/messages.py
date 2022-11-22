from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, InitVar

from common import Quote, Trade, Side

@dataclass
class OrderStatus:
    _js:InitVar[dict]
    event:str = field(init=False)
    status:str = field(init=False)

    descr:Optional[str] = field(init=False)
    reqid:int = field(init=False)
    txid:Optional[str] = field(init=False)
    originaltxid:Optional[str] = field(init=False)
    errorMessage:Optional[str] = field(init=False)

    def __post_init__(self, _js):
        self.event = _js.get('event')
        self.status = _js.get('status')
        self.descr = _js.get('descr')
        self.txid = _js.get('txid')
        self.originaltxid = _js.get('originaltxid')
        self.reqid = int(_js.get('reqid'))
        self.errorMessage = _js.get('errorMessage')


@dataclass
class CancelAllStatus:
    count: int
    event: str
    status: str


@dataclass
class MarketDataUpdate:
    keys:List[str] = field(init=False)
    is_bid:bool = field(init=False)
    channelID: int
    _quotes: InitVar[List[Any]]
    quotes:List[Quote] = field(init=False)
    channelName: str
    pair: str

    def __post_init__(self, _quotes):
        self.keys = _quotes.keys()
        self.is_bid = True if 'b' in self.keys else False
        self.quotes = self._crack(_quotes)

    def _crack(self, quotes: Dict[str, List[Any]]) -> List[Quote]:
        if self.is_bid:
            return [ Quote(q[0], q[1], q[2]) for q in quotes['b'] ]
        else:
            return [ Quote(q[0], q[1], q[2]) for q in quotes['a'] ]

    def __repr__(self):
        return f'{self.quotes}'


@dataclass
class SnapshotQuotes:
    _bids:InitVar[List[Any]]
    _asks:InitVar[List[Any]]
    bids: List[Quote] = field(init=False)
    asks: List[Quote] = field(init=False)

    def __post_init__(self, _bids, _asks):
        self.bids = self._crack(_bids)
        self.asks = self._crack(_asks)

    def _crack(self, quotes:List[Any]) -> List[Quote]:
        return [ Quote(q[0], q[1], q[2]) for q in quotes ]


@dataclass
class MarketDataSnapshot:
    channelID: int
    _quotes:InitVar[List[Any]]
    quotes: SnapshotQuotes = field(init=False)
    channelName: str
    pair: str

    def __post_init__(self, _quotes):
        self.quotes = SnapshotQuotes(_quotes['bs'], _quotes['as'])

    def __repr__(self):
        return f'{self.quotes.bids} {self.quotes.asks}'


@dataclass
class TradeUpdate:
    channelID: int
    _trades:InitVar[List[Any]]
    trades: List[Trade] = field(init=False)
    channelName: str
    pair: str

    def __post_init__(self, _trades):
        self.trades = self._crack(_trades)

    def _crack(self, trades: List) -> List[Trade]:
        return [ Trade(t[0], t[1], t[2], t[3], t[4]) for t in trades ]

    def __repr__(self):
        return f'{self.trades}'


@dataclass
class SubscriptionStatus:
    subscription:Dict[str, str] = field(init=False)
    channelName:Optional[str] = field(init=False)
    event:Optional[str] = field(init=False)
    pair:Optional[List[str]] = field(init=False)
    status:Optional[str] = field(init=False)
    channelID:Optional[int] = field(init=False)
    errorMessage:Optional[str] = field(init=False)

    _js:InitVar[dict]
    def __post_init__(self, _js):
        self.subscription = _js.get('subscription')
        self.channelName = self.subscription.get('name')
        self.event = _js.get('event')
        self.pair = _js.get('pair')
        self.status = _js.get('status')
        self.channelID = _js.get('channelID')
        self.errorMessage = _js.get('errorMessage')

    def __repr__(self) -> str:
        string:str = f'{self.event}: {self.status} -> {self.channelName}'
        if self.pair:
            string += f'|{self.pair}'
        if self.channelID:
            string += f' ({self.channelID})'
        if self.errorMessage:
            string += f' ({self.errorMessage})'
        return string


@dataclass
class SystemState:
    connectionID:int
    event:str
    status:str
    version:str

    def __repr__(self):
        return f'{self.event}: {self.status} ({self.version})'


