import json
import time
from typing import List, Union
from websockets import client, WebSocketClientProtocol

from market_data import MarketDataUpdate, MarketDataSnapshot
from quote import Quote, SnapshotQuotes
from trade import Trade, TradeUpdate
from subscription import SubscriptionStatus
from book import Book
from system_state import SystemState


class KrakTrader:
    def __init__(self, url:str):
        self._url = url
        self._websocket:Union[WebSocketClientProtocol|None] = None
        self._book:Union[Book|None] = None

    async def connect(self) -> None:
        self._websocket = await client.connect(self._url)

    def on_message(self, message:str) -> None:
        js:Union[List|dict] = json.loads(message)
        match message[0]:
            case '{':
                match js['event']:
                    case 'heartbeat': return
                    case 'systemStatus': self.on_system_status(SystemState(**js))
                    case 'subscriptionStatus': self.on_subscription_status(SubscriptionStatus(js))

            case '[':
                match js[2]:
                    case 'book-10':
                        try:
                            js[1]['as']
                            self.on_market_data_snapshot(MarketDataSnapshot(*js))
                        except:
                            self.on_market_data(MarketDataUpdate(*js))

                    case 'trade':
                        self.on_trade(TradeUpdate(*js))

    def on_market_data_snapshot(self, snapshot:MarketDataSnapshot) -> None:
        self._book = Book(snapshot.quotes)

    def on_market_data(self, md_update:MarketDataUpdate) -> None:
        self._book.update(md_update)
        print(self._book)

    def on_trade(self, trade:TradeUpdate) -> None:
        print(trade)

    def on_subscription_status(self, status:SubscriptionStatus) -> None:
        print(status)

    def on_system_status(self, state:SystemState) -> None:
        print(state)

    async def _subscribe(self, pair:str, name:str) -> None:
        await self._websocket.send(
            json.dumps({
                'event': 'subscribe',
                'pair': pair,
                'subscription': {
                    'name': name
                }
            })
        )

    async def subscribe_to_book(self, symbols:List[str]) -> None:
        await self._subscribe(symbols, 'book')

    async def subscribe_to_trades(self, symbols:List[str]) -> None:
        await self._subscribe(symbols, 'trade')

    async def run(self) -> None:
        try:
            async for message in self._websocket:
                #start:int = time.process_time_ns()
                self.on_message(message)
                #elapsed:int = time.process_time_ns() - start
                #print(f'update time: {elapsed/1000} mics')
        finally:
            await self._websocket.close()

