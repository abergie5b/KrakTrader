import json
import asyncio
from typing import Union, List

from common import WebsocketClient, WebsocketHandler, Order, Side
from .messages import (
    MarketDataSnapshot, 
    SubscriptionStatus, 
    MarketDataUpdate, 
    TradeUpdate, 
    SystemState,
    OrderStatus
)


class KrakApp(WebsocketHandler):
    def __init__(
        self, 
        url:str, 
        auth_url:str, 
        http_url:str, 
        key:str, 
        secret:str
    ):
        self._url = url
        self._auth_url = auth_url
        self._http_url = http_url
        self._http_uri = '/0/private/GetWebSocketsToken'
        self._key = key
        self._secret = secret
        self._token = self._get_token()
        #
        self._websocket_public = WebsocketClient(self._url)
        self._websocket_private = WebsocketClient(self._auth_url)

    async def connect(self) -> None:
        await self._websocket_public.connect()
        await self._websocket_private.connect()

    async def start(self) -> None:
        await asyncio.gather(
            self._websocket_public.start(self),
            self._websocket_private.start(self)
        )

    async def on_market_data_snapshot(self, snapshot:MarketDataSnapshot) -> None: pass
    async def on_market_data(self, update:MarketDataUpdate) -> None: pass
    async def on_trade(self, trade:TradeUpdate) -> None: pass
    async def on_subscription_status(self, status:SubscriptionStatus) -> None: pass
    async def on_system_status(self, state:SystemState) -> None: pass
    async def on_new_order(self, order:Order) -> None: pass
    async def on_replace_order(self, order:Order) -> None: pass
    async def on_cancel_order(self, order:Order) -> None: pass

    #  debug
    async def on_fill(self, js:dict) -> None: 
        print(order)

    async def on_order_status(self, js:dict) -> None:
        print(js)
    #

    async def on_message(self, message:str) -> None:
        js:Union[List|dict] = json.loads(message)
        match message[0]:
            case '{':
                match js['event']:
                    case 'heartbeat': return
                    case 'systemStatus': 
                        await self.on_system_status(SystemState(**js))
                    case 'subscriptionStatus': 
                        await self.on_subscription_status(SubscriptionStatus(js))

                    case 'openOrders':
                        await self._on_order(js)

                    case 'addOrderStatus':
                        await self.on_order_status(js)

                    case 'editOrderStatus':
                        await self.on_order_status(js)

                    case 'cancelOrderStatus':
                        await self.on_order_status(js)

            case '[':
                match js[2]:
                    case 'book-10':
                        try:
                            js[1]['as']
                            await self.on_market_data_snapshot(MarketDataSnapshot(*js))
                        except:
                            await self.on_market_data(MarketDataUpdate(*js))

                    case 'trade':
                        await self.on_trade(TradeUpdate(*js))

                    case 'ownTrades':
                        await self.on_fill(js)

    async def new_order_single(self, side:str, order_type:str, pair:str, price:float, qty:float):
        await self._websocket_private.send(
            json.dumps({
                'event': 'addOrder',
                'token': self._token,
                'ordertype': order_type,
                'pair': pair,
                'price': price,
                'type': 'buy' if side == Side.BUY else 'sell',
                'volume': qty
            })
        )

    async def replace_order(self, order_id:str, pair:str, order_type:str, price:float, qty:float):
        await self._websocket_private.send(
            json.dumps({
                'event': 'editOrder',
                'token': self._token,
                'orderid': order_id,
                'price': price,
                'volume': qty,
                'pair': pair
            })
        )

    async def cancel_order(self, order_id:str):
        await self._websocket_private.send(
            json.dumps({
                'event': 'cancelOrder',
                'token': self._token,
                'txtid': [ order_id ],
            })
        )

    async def cancel_all(self):
        await self._websocket_private.send(
            json.dumps({
                'event': 'cancelAll',
                'token': self._token
            })
        )

    async def subscribe_private(self, name:str) -> None:
        await self._websocket_private.send(
            json.dumps({
                'event': 'subscribe',
                'subscription': {
                    'name': name,
                    'token': self._token
                }
            })
        )

    async def subscribe_public(self, pair:str, name:str) -> None:
        await self._websocket_public.send(
            json.dumps({
                'event': 'subscribe',
                'pair': pair,
                'subscription': {
                    'name': name
                }
            })
        )

    def _on_order_status(self, js:dict) -> None:
        print(js)

    def _on_order(self, js:dict) -> None:
        print(js)

    def _get_token(self) -> str:
        import time
        from requests import post
        data:dict = {
            'nonce': str(int(1000*time.time()))
        }
        headers:dict = {
            'API-Key': self._key,
            'API-Sign': self._get_signature(data),
        }
        js:dict = post(
            self._http_url + self._http_uri, 
            headers=headers, 
            data=data
        ).json()
        token:str = js['result']['token']
        print(f"{self._http_uri} -> {token}")
        return token

    def _get_signature(self, post_data:dict) -> str:
        import hmac
        import urllib
        from base64 import b64decode, b64encode
        from hashlib import sha256, sha512
        postdata:str = urllib.parse.urlencode(post_data)
        encoded:str = (str(post_data['nonce']) + postdata).encode()
        message:str = self._http_uri.encode() + sha256(encoded).digest()

        mac:str = hmac.new(b64decode(self._secret), message, sha512)
        sigdigest:str = b64encode(mac.digest())
        return sigdigest.decode()

