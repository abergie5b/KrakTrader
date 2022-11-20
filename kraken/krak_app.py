import json
import asyncio
from abc import ABC, abstractmethod
from typing import List, Any

from common import WebsocketClient, WebsocketHandler, Order, Side
from .messages import (
    MarketDataSnapshot, 
    SubscriptionStatus, 
    MarketDataUpdate, 
    CancelAllStatus,
    TradeUpdate, 
    SystemState,
    OrderStatus
)


class KrakApp(ABC, WebsocketHandler):
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
        await self.on_connect()

    async def start(self) -> None:
        await asyncio.gather(
            self._websocket_public.start(self),
            self._websocket_private.start(self)
        )

    @abstractmethod
    async def on_connect(self) -> None:
        ...

    @abstractmethod
    async def on_market_data_snapshot(self, snapshot:MarketDataSnapshot) -> None:
        ...

    @abstractmethod
    async def on_market_data(self, update:MarketDataUpdate) -> None:
        ...

    @abstractmethod
    async def on_trade(self, trade:TradeUpdate) -> None:
        ...

    @abstractmethod
    async def on_subscription_status(self, status:SubscriptionStatus) -> None:
        ...

    @abstractmethod
    async def on_system_status(self, state:SystemState) -> None:
        ...

    @abstractmethod
    async def on_pending_order(self, order:Order) -> None:
        ...

    @abstractmethod
    async def on_new_order_single(self, order:Order) -> None:
        ...

    @abstractmethod
    async def on_replace_order(self, order:Order) -> None:
        ...

    @abstractmethod
    async def on_cancel_order(self, order:Order) -> None: 
        ...

    @abstractmethod
    async def on_new_order_ack(self, order_id:str) -> None:
        ...

    @abstractmethod
    async def on_replace_order_ack(self, order_id:str) -> None:
        ...

    @abstractmethod
    async def on_cancel_order_ack(self, order_id:str) -> None:
        ...

    @abstractmethod
    async def on_new_order_reject(self, OrderStatus: str) -> None:
        ...

    @abstractmethod
    async def on_replace_order_reject(self, OrderStatus: str) -> None:
        ...

    @abstractmethod
    async def on_cancel_order_reject(self, OrderStatus: str) -> None:
        ...

    @abstractmethod
    async def on_cancel_all(self, status: CancelAllStatus) -> None:
        ...

    @abstractmethod
    async def on_fill(self, js:dict) -> None: 
        ...

    async def on_message(self, message:str) -> None:
        match message[0]:
            case '{':
                js:Dict[Any, Any] = json.loads(message)
                match js['event']:
                    case 'heartbeat': return

                    case 'systemStatus': 
                        await self.on_system_status(SystemState(**js))

                    case 'subscriptionStatus': 
                        await self.on_subscription_status(SubscriptionStatus(js))

                    case 'addOrderStatus':
                        ordStatus:OrderStatus = OrderStatus(js)
                        if ordStatus.status != 'ok':
                            await self.on_new_order_reject(ordStatus)

                    case 'editOrderStatus':
                        ordStatus:OrderStatus = OrderStatus(js)
                        if ordStatus.status != 'ok':
                            await self.on_replace_order_reject(ordStatus)

                    case 'cancelOrderStatus':
                        ordStatus:OrderStatus = OrderStatus(js)
                        if ordStatus.status != 'ok':
                            await self.on_cancel_order_reject(ordStatus)

                    case 'cancelAllStatus':
                        await self.on_cancel_all(CancelAllStatus(**js))

            case '[':
                js:List[Any] = json.loads(message)
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

                match js[1]:
                    case 'openOrders':
                        await self._on_open_orders(js[0])
                
    async def _on_open_orders(self, messages:List[Any]) -> None:
        for message in messages:
            order_id:str = next(iter(message))
            krakOrder:dict = message[order_id]
            match krakOrder['status']:
                case 'pending':
                    order:Order = Order(
                        krakOrder['descr']['pair'],
                        Side.BUY if krakOrder['descr']['type'] == 'buy' else Side.SELL,
                        str(0),  # todo
                        krakOrder['vol'],
                        krakOrder['descr']['price'],
                        krakOrder['descr']['ordertype'],
                        krakOrder['status'],
                        krakOrder['timeinforce']
                    )
                    order.order_id = order_id
                    await self.on_pending_order(order)
                case 'open':
                    await self.on_new_order_ack(order_id)
                case 'replaced':
                    await self.on_replace_order_ack(order_id)
                case 'canceled':
                    await self.on_cancel_order_ack(order_id)
                case _:
                    print(f'openOrders -> unknown order status: {krakOrder["status"]} ({message})')

    async def new_order_single(self, order:Order) -> None:
        js:dict = {
            'pair': order.symbol,
            'type': 'buy' if order.side == Side.BUY else 'sell',
            'token': self._token,
            'volume': str(order.qty),
            'price': str(order.price),
            'ordertype': order.order_type,
            'event': 'addOrder',
            'timeinforce': 'GTC'
        }
        await self._websocket_private.send(
            json.dumps(js)
        )
        await self.on_new_order_single(order)

    async def replace_order(self, order:Order, price:float, qty:float) -> None:
        js:dict = {
            'pair': order.symbol,
            'event': 'editOrder',
            'token': self._token,
            'orderid': order.order_id,
            'price': str(price),
            'volume': str(qty)
        }
        await self._websocket_private.send(
            json.dumps(js)
        )
        pending:Order = Order(
            order.symbol,
            order.side,
            order.clorder_id,
            qty,
            price,
            'editOrder',
            order.time_in_force
        )
        await self.on_replace_order(pending)

    async def cancel_order(self, order:Order) -> None:
        await self._websocket_private.send(
            json.dumps({
                'event': 'cancelOrder',
                'token': self._token,
                'txtid': [ order.order_id ],
            })
        )
        pending:Order = Order(
            order.symbol,
            order.side,
            order.clorder_id,
            qty,
            price,
            'cancelOrder',
            order.time_in_force
        )
        await self.on_cancel_order(pending)

    async def cancel_all(self) -> None:
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

