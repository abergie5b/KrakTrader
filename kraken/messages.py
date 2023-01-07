import sys
from typing import Optional, Final, Dict, List, Any
from dataclasses import dataclass, field, InitVar

from common import (
    Pool,
    Quote,
    Trade,
    PooledObject
)


@dataclass
class OrderStatus:
    _js: InitVar[dict]
    event: str = field(init=False)
    status: str = field(init=False)

    descr: Optional[str] = field(init=False)
    reqid: int = field(init=False)
    txid: Optional[str] = field(init=False)
    originaltxid: Optional[str] = field(init=False)
    errorMessage: Optional[str] = field(init=False)

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
    _js: InitVar[dict]
    event: str = field(init=False)
    count: int = field(init=False)
    status: str = field(init=False)
    reqid: int = field(init=False)
    errorMessage: str = field(init=False)

    def __post_init__(self, _js):
        self.event = _js.get('event')
        self.count = _js.get('count')
        self.status = _js.get('status')
        self.reqid = _js.get('reqid')
        self.errorMessage = _js.get('errorMessage')


@dataclass
class BookUpdate(PooledObject):
    channelID: int
    _quotes: InitVar[Dict[str, List[Any]]]
    b: List[Quote] = field(init=False)
    a: List[Quote] = field(init=False)
    channelName: str
    pair: str

    @staticmethod
    def create_empty():
        return BookUpdate(-sys.maxsize, {'b': [], 'a': []}, '', '')

    def init(self, _channelID, quotes, _channelName, pair):
        self.channelID = _channelID
        self.__post_init__(quotes)
        self.channelName = _channelName
        self.pair = pair
        return self

    def clean(self):
        self.channelID = -sys.maxsize
        self.b = []
        self.a = []
        self.channelName = ''
        self.pair = ''

    def __post_init__(self, _quotes):
        bids = _quotes.get('b')
        asks = _quotes.get('a')
        self.b = [Quote(q[0], q[1], q[2]) for q in bids] if bids else []
        self.a = [Quote(q[0], q[1], q[2]) for q in asks] if asks else []


@dataclass
class BookSnapshot:
    @dataclass
    class _Snapshot:
        _bids: InitVar[List[Any]]
        _asks: InitVar[List[Any]]
        bs: List[Quote] = field(init=False)
        as_: List[Quote] = field(init=False)

        def __post_init__(self, _bids, _asks):
            self.bs = BookSnapshot._Snapshot._crack(_bids)
            self.as_ = BookSnapshot._Snapshot._crack(_asks)

        @staticmethod
        def _crack(_quotes: List[Any]) -> List[Quote]:
            return [Quote(q[0], q[1], q[2]) for q in _quotes]

    channelID: int
    _snapshot: InitVar[Dict[str, Any]]
    snapshot: _Snapshot = field(init=False)
    channelName: str
    pair: str

    def __post_init__(self, _snapshot):
        self.snapshot = BookSnapshot._Snapshot(
            _snapshot['bs'] or [],
            _snapshot['as'] or []
        )


@dataclass
class Ticker:
    @dataclass
    class _Quote:
        price: float
        wholeLotVolume: int
        lotVolume: float

    @dataclass
    class _DailyPriceDiff:
        today: float
        last24Hours: float

    @dataclass
    class Ask(_Quote):
        ...

    @dataclass
    class Bid(_Quote):
        ...

    @dataclass
    class Close:
        price: float
        lotVolume: float

    @dataclass
    class Volume(_DailyPriceDiff):
        ...

    @dataclass
    class Price(_DailyPriceDiff):
        ...

    @dataclass
    class NumberOfTrades(_DailyPriceDiff):
        ...

    @dataclass
    class LowPrice(_DailyPriceDiff):
        ...

    @dataclass
    class HighPrice(_DailyPriceDiff):
        ...

    @dataclass
    class OpenPrice(_DailyPriceDiff):
        ...

    a: Ask
    b: Bid
    c: Close
    v: Volume
    p: Price
    t: NumberOfTrades
    l: LowPrice
    h: HighPrice
    o: OpenPrice


@dataclass
class Event:
    event: str


@dataclass
class Heartbeat(Event):
    ...


@dataclass
class Ping(Event):
    ...


@dataclass
class Pong(Event):
    reqid: int


@dataclass
class TickerPayload:
    channelID: str
    _js: InitVar[dict]
    ticker: Ticker = field(init=False)
    channelName: str
    pair: str

    def __post_init__(self, _js: dict):
        self.ticker = Ticker(
            Ticker.Ask(*_js['a']),
            Ticker.Bid(*_js['b']),
            Ticker.Close(*_js['c']),
            Ticker.Volume(*_js['v']),
            Ticker.Price(*_js['p']),
            Ticker.NumberOfTrades(*_js['t']),
            Ticker.LowPrice(*_js['l']),
            Ticker.HighPrice(*_js['h']),
            Ticker.OpenPrice(*_js['o'])
        )


@dataclass
class TradePayload:
    channelID: int
    _trades: InitVar[List[Any]]
    trades: List[Trade] = field(init=False)
    channelName: str
    pair: str

    def __post_init__(self, _trades):
        self.trades = [Trade(t[0], t[1], t[2], t[3], t[4]) for t in _trades]


@dataclass
class SubscriptionStatus:
    subscription: Dict[str, str] = field(init=False)
    channelName: Optional[str] = field(init=False)
    event: Optional[str] = field(init=False)
    pair: Optional[List[str]] = field(init=False)
    status: Optional[str] = field(init=False)
    channelID: Optional[int] = field(init=False)
    errorMessage: Optional[str] = field(init=False)

    _js: InitVar[dict]

    def __post_init__(self, _js):
        self.subscription = _js.get('subscription')
        self.channelName = self.subscription.get('name')
        self.event = _js.get('event')
        self.pair = _js.get('pair')
        self.status = _js.get('status')
        self.channelID = _js.get('channelID')
        self.errorMessage = _js.get('errorMessage')


@dataclass
class SystemStatus:
    connectionID: int
    event: str
    status: str
    version: str


@dataclass
class Candle:
    time: float
    etime: float
    open: float
    high: float
    low: float
    close: float
    vwap: float
    volume: float
    count: int


@dataclass
class Ohlc:
    channelID: int
    _candle: InitVar[List[Any]]
    candle: Candle = field(init=False)
    channelName: str
    pair: str

    def __post_init__(self, _candle):
        self.candle = Candle(*_candle)


@dataclass
class CancelAllOrdersAfterStatus:
    _js: InitVar[dict]
    event: str = field(init=False)
    status: str = field(init=False)
    currentTime: str = field(init=False)
    triggerTime: str = field(init=False)
    reqid: Optional[int] = field(init=False)
    errorMessage: Optional[str] = field(init=False)

    def __post_init__(self, _js):
        self.event = _js.get('event')
        self.status = _js.get('status')
        self.currentTime = _js.get('currentTime')
        self.triggerTime = _js.get('triggerTime')
        self.reqid = _js.get('reqid')
        self.errorMessage = _js.get('errorMessage')


@dataclass
class Spread:
    bid: float
    ask: float
    timestamp: float
    bidVolume: float
    askVolume: float


@dataclass
class SpreadPayload:
    channelID: int
    _spread: InitVar[dict]
    spread: Spread = field(init=False)
    channelName: str
    pair: str

    def __post_init__(self, _spread):
        self.spread = Spread(*_spread)


bookUpdatePool: Final[Pool] = Pool(128, BookUpdate.create_empty)
