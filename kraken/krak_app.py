import json
import asyncio
from abc import ABC, abstractmethod
from typing import (
    Optional, 
    Union, 
    Dict, 
    List, 
    Any
)

from common import (
    WebsocketClient, 
    WebsocketHandler, 
    Trade,
    Order, 
    Fill, 
    Side
)
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

        self._reqid_count = 0
        self._orig_reqid:int = 10000000000

    async def connect(self) -> None:
        await self._websocket_public.connect()
        await self._websocket_private.connect()
        await self.on_connect()

    async def start(self) -> None:
        await asyncio.gather(
            self._websocket_public.start(self),
            self._websocket_private.start(self)
        )

    def _get_reqid(self):
        self._reqid_count += 1
        return self._orig_reqid + self._reqid_count

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
    async def on_trade(self, trade:Trade) -> None:
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
    async def on_open_order(self, order_id:str) -> None:
        ...

    @abstractmethod
    async def on_replaced_order(self, order_id:str) -> None:
        ...

    @abstractmethod
    async def on_canceled_order(self, order_id:str) -> None:
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
    async def on_new_order_ack(self, order_id:Optional[str], clorder_id:int) -> None:
        ...

    @abstractmethod
    async def on_replace_order_ack(self, order_id:Optional[str], clorder_id:int) -> None:
        ...

    @abstractmethod
    async def on_cancel_order_ack(self, clorder_id:int) -> None:
        ...

    @abstractmethod
    async def on_new_order_reject(self, order_status: OrderStatus) -> None:
        ...

    @abstractmethod
    async def on_replace_order_reject(self, order_status: OrderStatus) -> None:
        ...

    @abstractmethod
    async def on_cancel_order_reject(self, order_status: OrderStatus) -> None:
        ...

    @abstractmethod
    async def on_cancel_all(self, status: CancelAllStatus) -> None:
        ...

    @abstractmethod
    async def on_fill(self, fill:Fill) -> None: 
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
                        add_order_status:OrderStatus = OrderStatus(js)
                        if add_order_status.status != 'ok':
                            await self.on_new_order_reject(add_order_status)
                        else:
                            await self.on_new_order_ack(add_order_status.txid, add_order_status.reqid)

                    case 'editOrderStatus':
                        edit_order_status:OrderStatus = OrderStatus(js)
                        if edit_order_status.status != 'ok':
                            await self.on_replace_order_reject(edit_order_status)
                        else:
                            await self.on_replace_order_ack(edit_order_status.txid, edit_order_status.reqid)

                    case 'cancelOrderStatus':
                        cancel_order_status:OrderStatus = OrderStatus(js)
                        if cancel_order_status.status != 'ok':
                            await self.on_cancel_order_reject(cancel_order_status)
                        else:
                            await self.on_cancel_order_ack(cancel_order_status.reqid)

                    case 'cancelAllStatus':
                        await self.on_cancel_all(CancelAllStatus(**js))

                    case _:
                        print(f'on_message -> unknown {type(js)} message {js}')

            case '[':
                js_list:List[Any] = json.loads(message)
                md_update:str = js_list[2]
                order_update:str = js_list[1]
                if md_update == 'book-10':
                    try:
                        js_list[1]['as']
                        await self.on_market_data_snapshot(MarketDataSnapshot(*js_list))
                    except:
                        await self.on_market_data(MarketDataUpdate(*js_list))

                elif md_update == 'trade':
                    await self._on_trade(TradeUpdate(*js_list))

                elif order_update == 'openOrders':
                    await self._on_open_orders(js_list[0])

                elif order_update == 'ownTrades':
                    await self._on_own_trades(js_list[0])

                else:
                    print(f'on_message -> unknown {type(js_list)} message {js_list[1]} -> {js_list}')

            case _:
                print(f'on_message -> unknown message {message}')

    async def _on_trade(self, trade_update:TradeUpdate) -> None:
        for trade in trade_update.trades:
            await self.on_trade(trade)

    async def _on_own_trades(self, messages:List[Dict[str, Any]]) -> None:
        for message in messages:
            order_id:str = next(iter(message))
            trade:Dict[str, Any] = message[order_id]
            fill:Fill = Fill(
                trade['ordertxid'],
                Side.BUY if trade['type'] == 'buy' else Side.SELL,
                float(trade['vol']),
                trade['pair'],
                float(trade['price']),
                float(trade['time'])
            )
            await self.on_fill(fill)

    async def _on_open_orders(self, messages:List[Dict[str, Any]]) -> None:
        for message in messages:
            order_id:str = next(iter(message))
            krak_order:dict = message[order_id]
            status:Optional[str] = krak_order.get('status')
            match status:
                case 'pending':
                    order:Order = Order(
                        krak_order['descr']['pair'],
                        Side.BUY if krak_order['descr']['type'] == 'buy' else Side.SELL,
                        krak_order['userref'],
                        krak_order['vol'],
                        krak_order['descr']['price'],
                        krak_order['descr']['ordertype'],
                        krak_order['status'],
                        krak_order['timeinforce']
                    )
                    order.order_id = order_id
                    await self.on_pending_order(order)
                case 'open':
                    await self.on_open_order(order_id)
                case 'replaced':
                    await self.on_replaced_order(order_id)
                case 'canceled':
                    await self.on_canceled_order(order_id)
                case _:
                    print(f'openOrders -> unknown order status: {krak_order["status"]} ({message})')

    async def new_order_single(self, order:Order) -> None:
        reqid:int = self._get_reqid()
        order.clorder_id = reqid
        js:dict = {
            'pair': order.symbol,
            'type': 'buy' if order.side == Side.BUY else 'sell',
            'token': self._token,
            'volume': str(order.qty),
            'price': str(order.price),
            'ordertype': order.order_type,
            'event': 'addOrder',
            'timeinforce': 'GTC',
            'reqid': reqid
        }
        await self._websocket_private.send(
            json.dumps(js)
        )
        await self.on_new_order_single(order)

    async def replace_order(self, order:Order, price:float, qty:float) -> None:
        reqid:int = self._get_reqid()
        order.clorder_id = reqid
        js:dict = {
            'pair': order.symbol,
            'event': 'editOrder',
            'token': self._token,
            'orderid': order.order_id,
            'price': str(price),
            'volume': str(qty),
            'reqid': reqid
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
            order.order_type,
            'editOrder',
            order.time_in_force
        )
        pending.order_id = order.order_id
        await self.on_replace_order(pending)

    async def cancel_order(self, order:Order) -> None:
        reqid:int = self._get_reqid()
        order.clorder_id = reqid
        await self._websocket_private.send(
            json.dumps({
                'event': 'cancelOrder',
                'token': self._token,
                'txid': [ order.order_id ],
                'reqid': reqid
            })
        )
        pending:Order = Order(
            order.symbol,
            order.side,
            order.clorder_id,
            order.qty,
            order.price,
            order.order_type,
            'cancelOrder',
            order.time_in_force
        )
        pending.order_id = order.order_id
        await self.on_cancel_order(pending)

    async def cancel_all(self) -> None:
        try:
            await self._websocket_private.send(
                json.dumps({
                    'event': 'cancelAll',
                    'token': self._token
                })
            )
        except Exception as e:
            print(f'app -> CANCEL_ALL FAILED')

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

    async def subscribe_public(self, pair:List[str], name:str) -> None:
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
        encoded:bytes = (str(post_data['nonce']) + postdata).encode()
        message = self._http_uri.encode() + sha256(encoded).digest()

        mac = hmac.new(b64decode(self._secret), message, sha512)
        sigdigest:bytes = b64encode(mac.digest())
        return sigdigest.decode()

