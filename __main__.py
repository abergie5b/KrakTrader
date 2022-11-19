import json
import asyncio
import websockets
from typing import List, Union


def bisect(quotes:List[Quote], quote:Quote) -> int:
    mid:int = len(quotes) // 2
    if quotes[mid].price > quote.price:
        return bisect(quotes[mid:], quote)
    else if quotes[mid].price < quote.price:
        return bisect(quotes[:mid], quote)
    return mid

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

    def _update_volume(self, 
            mdUpdate:Quote, 
            quotes:List[Quote], 
            is_bid:bool
    ) -> None:
        for order in quotes:
            if order.price == mdUpdate.price:
                if order.volume == 0:
                    quotes.remove(order)
                else:
                    order.volume = mdUpdate.volume

    def _update_bids(self, bids:MarketDataUpdate) -> None:
        for mdUpdate in bids.quotes:
            self._update_volume(mdUpdate, self.bids, True)

    def _update_asks(self, asks:MarketDataUpdate) -> None:
        for mdUpdate in asks.quotes:
            self._update_volume(mdUpdate, self.asks, False)

    def update(self, mdUpdate:MarketDataUpdate) -> None:
        if mdUpdate.is_bid:
            self._update_bids(mdUpdate)
        else:
            self._update_asks(mdUpdate)


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

async def subscribe(websocket:websockets.WebSocketClientProtocol) -> Book:
    await websocket.send(json.dumps({
        "event": "subscribe",
        "pair": [ "XBT/USD" ],
        "subscription": {
            "name": "book"
        }
    }))
    systemState:str = await websocket.recv() # systemState message
    print(systemState)

    subscriptionStatus:str = await websocket.recv()
    print(subscriptionStatus)

    message:str = await websocket.recv()
    js:Union[List, dict] = json.loads(message)
    while is_heartbeat(js):
        message = await websocket.recv()
        js = json.loads(message)

    snapshot:MarketDataSnapshot = MarketDataSnapshot(*js)
    book:Book = Book(snapshot.quotes)
    print(book)
    return book

async def read(websocket:websockets.WebSocketClientProtocol, book:Book):
    async for message in websocket:
        try:
            js:str = json.loads(message)
            if is_heartbeat(js):
                continue
            md_update:MarketDataUpdate = MarketDataUpdate(*js)
            book.update(md_update)
            print(book)
        except Exception as e:
            print('exception: ', e, message)

async def main():
    async with websockets.connect("wss://beta-ws.kraken.com") as websocket:
        book:Book = await subscribe(websocket) 
        await read(websocket, book)


if __name__ == '__main__':
    asyncio.run(main())
