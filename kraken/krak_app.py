import json
from typing import Union, List
from websockets import client, WebSocketClientProtocol

from .messages import (
    MarketDataSnapshot, 
    SubscriptionStatus, 
    MarketDataUpdate, 
    TradeUpdate, 
    SystemState
)

class KrakApp:
    def __init__(self, url:str):
        self._url = url
        self._websocket:Union[WebSocketClientProtocol|None] = None

    def on_market_data_snapshot(self, snapshot:MarketDataSnapshot) -> None: pass
    def on_market_data(self, update:MarketDataUpdate) -> None: pass
    def on_trade(self, trade:TradeUpdate) -> None: pass
    def on_subscription_status(self, status:SubscriptionStatus) -> None: pass
    def on_system_status(self, state:SystemState) -> None: pass

    async def connect(self) -> None:
        self._websocket = await client.connect(self._url)

    async def run(self) -> None:
        try:
            async for message in self._websocket:
                #start:int = time.process_time_ns()
                self.on_message(message)
                #elapsed:int = time.process_time_ns() - start
                #print(f'update time: {elapsed/1000} mics')
        finally:
            await self._websocket.close()

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

    async def subscribe(self, pair:str, name:str) -> None:
        await self._websocket.send(
            json.dumps({
                'event': 'subscribe',
                'pair': pair,
                'subscription': {
                    'name': name
                }
            })
        )

