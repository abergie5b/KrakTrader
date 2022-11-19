import json
import asyncio
import websockets
import bisect
import time
import math
from typing import List, Union

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
        self.is_clean = False

    def __eq__(self, other):
        return self.price == other.price and \
               self.volume == other.volume and \
               self.timestamp == other.timestamp

    def __repr__(self):
        return f'{self.timestamp}: {self.volume} @ {self.price}'


class SnapshotQuotes:
    def __init__(
        self,
        asks: List[Quote],
        bids: List[Quote]
    ):
        self.asks = [ Quote(a[0], a[1], a[2]) for a in asks ]
        self.bids = [ Quote(b[0], b[1], b[2]) for b in bids ]


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
        self.trades = self._get_trades(trades)
        self.channelName = channelName
        self.pair = pair

    def _get_trades(self, trades: List) -> List[Trade]:
        return [ Trade(t[0], t[1], t[2], t[3], t[4]) for t in trades ]

    def __repr__(self):
        return f'{self.trades}'


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
        self.quotes = self._get_quotes(quotes)
        self.channelName = channelName
        self.pair = pair

    def _get_quotes(self, quotes: List) -> List[Quote]:
        if self.is_bid:
            return [ Quote(q[0], q[1], q[2]) for q in quotes['b'] ]
        else:
            return [ Quote(q[0], q[1], q[2]) for q in quotes['a'] ]

    def __repr__(self):
        return f'{self.quotes}'


class Book:
    def __init__(
        self,
        snapshot: SnapshotQuotes
    ):
        self.bids:List[Quote] = [ bid for bid in snapshot.bids if bid.volume != 0 ]
        self.asks:List[Quote] = [ ask for ask in snapshot.asks if ask.volume != 0 ]

    def __repr__(self):
        book:str = ''
        for ask in self.asks[::-1]:
            book += f'\t\t{ask.price}\t{ask.volume}\n'
        for bid in self.bids:
            book += f'{bid.volume}\t{bid.price}\n'
        return book

    def _update_book(self, 
            quote:Quote, 
            quotes:List[Quote], 
            is_bid:bool
    ) -> None:
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
            key:object = lambda q: -1 * q.price
        else:
            key:object = lambda q: q.price
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

    def update(self, md_update:MarketDataUpdate) -> None:
        if md_update.is_bid:
            self._update_bids(md_update)
        else:
            self._update_asks(md_update)

    def vwap(self, quotes:List[Quote], depth:int = 10) -> Quote:
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

    def best_bid(self) -> Quote:
        return self.bids[0]

    def best_ask(self) -> Quote:
        return self.asks[0]


class MarketDataSnapshot:
    def __init__(
        self,
        channelID: int,
        quotes: SnapshotQuotes,
        channelName: str,
        pair: str
    ):
        self.channelID = channelID
        self.quotes = SnapshotQuotes(quotes['as'], quotes['bs'])
        self.channelName = channelName
        self.pair = pair

    def __repr__(self):
        return f'{self.quotes.bids} {self.quotes.asks}'


def is_heartbeat(js: dict) -> bool:
    return isinstance(js, dict) and js['event'] == 'heartbeat'


class TradingSystem: pass
class SubscriptionManager:
    def __init__(
        self,
        websocket:websockets.WebSocketClientProtocol
    ):
        self._websocket = websocket
        self._subscriptions:List[SubscriptionStatus] = []

    async def subscribe_to_book(
        self,
        system:TradingSystem,
        symbols:List[str]
    ) -> SubscriptionStatus:
        await self._websocket.send(json.dumps({
            "event": "subscribe",
            "pair": symbols,
            "subscription": {
                "name": "book"
            }
        }))
        systemState:str = await self._websocket.recv() # systemState message
        print(systemState)

        subscription_status_str:str = await self._websocket.recv()
        js:dict = json.loads(subscription_status_str)
        subscription_status:SubscriptionStatus = SubscriptionStatus(js)
        self._subscriptions.append(subscription_status)

        message:str = await self._websocket.recv()
        js:Union[List|dict] = json.loads(message)
        while is_heartbeat(js):
            message = await self._websocket.recv()
            js = json.loads(message)

        snapshot:MarketDataSnapshot = MarketDataSnapshot(*js)
        system._book = Book(snapshot.quotes)
        system._book_channelIDs.append(subscription_status.channelID)

    async def subscribe_to_trades(
        self,
        system:TradingSystem,
        symbols:List[str]
    ) -> None:
        await self._websocket.send(json.dumps({
            "event": "subscribe",
            "pair": symbols,
            "subscription": {
                "name": "trade"
            }
        }))
        message:str = await self._websocket.recv()
        js:Union[List|dict] = json.loads(message)
        while is_heartbeat(js) or isinstance(js, list):
            #  might need to process this message if its a book message and we've already subscribed
            # todo handle this more smoothly
            if isinstance(js, list):
                system.step(message)
            message = await self._websocket.recv()
            js = json.loads(message)

        subscription_status:SubscriptionStatus = SubscriptionStatus(js)
        self._subscriptions.append(subscription_status)
        system._trade_channelIDs.append(subscription_status.channelID)


class TradingSystem:
    def __init__(
        self,
        websocket:websockets.WebSocketClientProtocol,
        subscription_manager:SubscriptionManager
    ):
        self._websocket = websocket
        self._subscription_manager = subscription_manager
        self._book:Union[Book|None] = None
        self._book_channelIDs:List[int] = []
        self._trade_channelIDs:List[int] = []

    def step(self, message:str) -> None:
        try:
            js:str = json.loads(message)
            if is_heartbeat(js):
                return
            if js[0] in self._book_channelIDs:
                md_update:MarketDataUpdate = MarketDataUpdate(*js)
                self._book.update(md_update)
                print(self._book)
            elif js[0] in self._trade_channelIDs:
                trade_update:TradeUpdate = TradeUpdate(*js)
                print(trade_update)
        except Exception as e:
            print('exception: ', e, message)

    async def process(self) -> None:
        async for message in self._websocket:
            #start:int = time.process_time_ns()
            self.step(message)
            #elapsed:int = time.process_time_ns() - start
            #print(f'update time: {elapsed/1000} mics')


async def main():
    symbols:List[string] = [ "XBT/USD" ]
    async with websockets.connect("wss://beta-ws.kraken.com") as websocket:
        subscription_manager:SubscriptionManager = SubscriptionManager(websocket)
        system:TradingSystem = TradingSystem(websocket, subscription_manager)

        await subscription_manager.subscribe_to_book(system, symbols) 
        await subscription_manager.subscribe_to_trades(system, symbols)

        await system.process()


if __name__ == '__main__':
    asyncio.run(main())
