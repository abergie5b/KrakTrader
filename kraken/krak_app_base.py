import json
import asyncio
from typing import (
    Optional,
    Dict,
    List,
    Any
)

from common import (
    WebsocketClient,
    WebsocketHandler,
    get_logger,
)


class KrakAppBase(WebsocketHandler):
    """
    simple base class for kraken API
        - inherit from this class to receive message callbacks as they are sent from kraken (dict/list)
        - clients can use public and/or private websocket methods including :
            - connect
            - send
            - recv
            - subscribe
            - unsubscribe
        - if authentication parameters are given, this class retrieves the token required to make subsequent requests
    """
    def __init__(
            self,
            url: Optional[str] = None,
            auth_url: Optional[str] = None,
            http_url: Optional[str] = None,
            key: Optional[str] = None,
            secret: Optional[str] = None
    ):
        self._http_url = http_url
        self._http_uri: str = '/0/private/GetWebSocketsToken'
        self._key = key
        self._secret = secret

        self._token: Optional[str] = None
        self._websocket_public: Optional[WebsocketClient] = None
        self._websocket_private: Optional[WebsocketClient] = None

        if self._key and self._secret and self._http_url and auth_url:
            self._token = self._get_token()

        if url:
            self._websocket_public = WebsocketClient(url)

        if self._token and auth_url:
            self._websocket_private = WebsocketClient(auth_url)

        #
        self._logger = get_logger(__name__)

    async def connect(self) -> None:
        if self._websocket_public:
            await self._websocket_public.connect()

        if self._websocket_private:
            await self._websocket_private.connect()

    async def start(self, tasks=None) -> None:
        if tasks is None:
            tasks = []
        if self._websocket_public:
            tasks.append(self._websocket_public.read_til_close(self))

        if self._websocket_private:
            tasks.append(self._websocket_private.read_til_close(self))

        await asyncio.gather(*tasks)

    async def subscribe_private(self, subscription: dict, req_id=None) -> None:
        subscription['token'] = self._token
        js: dict = {
            'event': 'subscribe',
            'subscription': subscription
        }
        if req_id:
            js['reqid'] = req_id
        await self.send_private(js)

    async def subscribe_public(self, subscription: dict, pair=None, req_id=None) -> None:
        js: dict = {
            'event': 'subscribe',
            'subscription': subscription
        }
        if pair:
            js['pair'] = pair
        if req_id:
            js['reqid'] = req_id
        await self.send_public(js)

    async def unsubscribe_private(self, subscription: dict) -> None:
        subscription['token'] = self._token
        await self.send_private({
            'event': 'unsubscribe',
            'subscription': subscription
        })

    async def unsubscribe_public(self, pair: List[str], subscription: dict) -> None:
        await self.send_public({
            'event': 'unsubscribe',
            'pair': pair,
            'subscription': subscription
        })

    async def send_public(self, js: dict):
        if self._websocket_public:
            await self._websocket_public.send(
                json.dumps(js)
            )
        else:
            self._logger.warning('request failed - not subscribed to public feed')

    async def send_private(self, js: dict):
        if self._websocket_private:
            await self._websocket_private.send(
                json.dumps(js)
            )
        else:
            self._logger.warning('request failed - not subscribed to private feed')

    async def on_message(self, message: str) -> None:
        match message[0]:
            case '[':
                js_list: List[Any] = json.loads(message)
                md_update: str = js_list[-2]
                order_update: str = js_list[1]
                if md_update in ('book-10', 'book-25', 'book-100', 'book-500', 'book-1000'):
                    if 'a' in js_list[1] or 'b' in js_list[1]:
                        await self.on_book(js_list)
                    else:
                        await self.on_book_snapshot(js_list)

                elif md_update == 'trade':
                    await self.on_trade_(js_list)

                elif md_update == 'spread':
                    await self.on_spread_(js_list)

                elif md_update in ('ohlc-1', 'ohlc-5', 'ohlc-15', 'ohlc-30', 'ohlc-60'):
                    await self.on_ohlc_(js_list)

                elif md_update == 'ticker':
                    await self.on_ticker_(js_list)

                elif order_update == 'openOrders':
                    await self.on_open_orders(js_list)

                elif order_update == 'ownTrades':
                    await self.on_own_trades(js_list)

                else:
                    self._logger.error(f'on_message -> unknown {type(js_list)} message {js_list[1]} -> {js_list}')

            case '{':
                js: Dict[Any, Any] = json.loads(message)
                match js['event']:
                    case 'heartbeat':
                        await self.on_heartbeat_(js)

                    case 'systemStatus':
                        await self.on_system_status_(js)

                    case 'subscriptionStatus':
                        await self.on_subscription_status_(js)

                    case 'addOrderStatus':
                        await self.on_add_order_status(js)

                    case 'editOrderStatus':
                        await self.on_edit_order_status(js)

                    case 'cancelOrderStatus':
                        await self.on_cancel_order_status(js)

                    case 'cancelAllStatus':
                        await self.on_cancel_all_status(js)

                    case 'cancelAllAfterStatus':
                        await self.on_cancel_all_after_status_(js)

                    case 'pong':
                        await self.on_pong_(js)

                    case _:
                        self._logger.error(f'on_message -> unknown {type(js)} message {js}')

            case _:
                self._logger.error(f'on_message -> unknown message {message}')

    @staticmethod
    def _warn_not_implemented(f):
        """
        a warning that the user is receiving a message for a callback they have not implemented
        """
        async def _wraps(*args):
            args[0]._logger.warning(f'cannot send callback for unimplemented method: {f.__name__} -> {args[1:]}')
            await f(*args)
        return _wraps

    async def on_heartbeat_(self, heartbeat: dict) -> None: ...

    @_warn_not_implemented
    async def on_book_snapshot(self, snapshot: list) -> None: ...

    @_warn_not_implemented
    async def on_book(self, book: list) -> None: ...

    @_warn_not_implemented
    async def on_ohlc_(self, ohlc: list) -> None: ...

    @_warn_not_implemented
    async def on_trade_(self, trade: list) -> None: ...

    @_warn_not_implemented
    async def on_spread_(self, spread: list) -> None: ...

    @_warn_not_implemented
    async def on_ticker_(self, ticker: list) -> None: ...

    @_warn_not_implemented
    async def on_open_orders(self, orders: list) -> None: ...

    @_warn_not_implemented
    async def on_own_trades(self, trades: list) -> None: ...

    @_warn_not_implemented
    async def on_subscription_status_(self, js: dict) -> None: ...

    @_warn_not_implemented
    async def on_pong_(self, pong: dict) -> None: ...

    @_warn_not_implemented
    async def on_system_status_(self, status: dict) -> None: ...

    @_warn_not_implemented
    async def on_add_order_status(self, status: dict) -> None: ...

    @_warn_not_implemented
    async def on_edit_order_status(self, status: dict) -> None: ...

    @_warn_not_implemented
    async def on_cancel_order_status(self, status: dict) -> None: ...

    @_warn_not_implemented
    async def on_cancel_all_status(self, status: dict) -> None: ...

    @_warn_not_implemented
    async def on_cancel_all_after_status_(self, status: dict) -> None: ...

    def _get_token(self) -> str:
        import time
        from requests import post
        data: dict = {
            'nonce': str(int(1000*time.time()))
        }
        headers: dict = {
            'API-Key': self._key,
            'API-Sign': self._get_signature(data)
        }
        js: dict = post(
            self._http_url + self._http_uri,
            headers=headers,
            data=data
        ).json()
        token: str = js['result']['token']
        return token

    def _get_signature(self, post_data: dict) -> str:
        import hmac
        import urllib
        from base64 import b64decode, b64encode
        from hashlib import sha256, sha512
        postdata: str = urllib.parse.urlencode(post_data)
        encoded: bytes = (str(post_data['nonce']) + postdata).encode()
        message = self._http_uri.encode() + sha256(encoded).digest()

        mac = hmac.new(b64decode(self._secret), message, sha512)
        sigdigest: bytes = b64encode(mac.digest())
        return sigdigest.decode()
