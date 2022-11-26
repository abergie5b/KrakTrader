import sys
from typing import (
    Optional,
    Dict,
    List, 
    Any
)

from .krak_app_base import KrakAppBase
from common import (
    get_logger,
    Trade,
    Order, 
    Fill, 
    Side
)
from .messages import (
    CancelAllOrdersAfterStatus,
    BookSnapshot,
    SubscriptionStatus,
    BookUpdate,
    CancelAllStatus,
    TickerPayload,
    SpreadPayload,
    TradePayload,
    SystemStatus,
    OrderStatus,
    Heartbeat,
    Spread,
    Ticker,
    Ping,
    Pong,
    Ohlc
)


class KrakApp(KrakAppBase):
    """
    FIX API abstraction of KrakAppBase
        - inherit from this class to receive FIX protocol-like messages based on the callbacks from kraken
        - example:
            > app.new_order_single(order)  # send an order to kraken, then based on the response:
                # on_new_order_ack(order: Order) will be triggered to confirm your order is working on the exchange
                # on_new_order_reject(order_status: OrderStatus) will be triggered meaning the order was rejected
    """
    def __init__(
        self, 
        url: Optional[str] = None,
        auth_url: Optional[str] = None,
        http_url: Optional[str] = None,
        key: Optional[str] = None,
        secret: Optional[str] = None
    ):
        super().__init__(url, auth_url, http_url, key, secret)
        self._logger = get_logger(__name__)

        #
        self._req_count: int = 0
        self._orig_req_id: int = 10000000000

    def _get_req_id(self) -> int:
        self._req_count += 1
        return self._orig_req_id + self._req_count

    async def _on_trade(self, trade_update: TradePayload) -> None:
        for trade in trade_update.trades:
            await self.on_trade(trade)

    async def _on_own_trades(self, messages: List[Dict[str, Any]]) -> None:
        for message in messages:
            order_id: str = next(iter(message))
            trade: Dict[str, Any] = message[order_id]
            fill: Fill = Fill(
                trade['ordertxid'],
                Side.BUY if trade['type'] == 'buy' else Side.SELL,
                float(trade['vol']),
                trade['pair'],
                float(trade['price']),
                float(trade['time'])
            )
            await self.on_fill(fill)

    async def _on_open_orders(self, messages: List[Dict[str, Any]]) -> None:
        for message in messages:
            order_id: str = next(iter(message))
            krak_order: dict = message[order_id]
            status: Optional[str] = krak_order.get('status')
            match status:
                case 'pending':
                    order: Order = Order(
                        krak_order['descr']['pair'],
                        Side.BUY if krak_order['descr']['type'] == 'buy' else Side.SELL,
                        -sys.maxsize,
                        krak_order['vol'],
                        krak_order['descr']['price'],
                        krak_order['descr']['ordertype'],
                        krak_order['status'],
                        krak_order['timeinforce']
                    )
                    order.order_id = order_id
                    await self.on_open_order_pending(order)
                case 'open':
                    await self.on_open_order_new(order_id)
                case 'canceled':
                    await self.on_open_order_cancel(order_id)
                case _:
                    self._logger.error(f'openOrders -> unknown order status: {krak_order["status"]} ({message})')

    async def new_order_single(self, order: Order) -> None:
        req_id: int = self._get_req_id()
        order.clorder_id = req_id
        js: dict = {
            'pair': order.symbol,
            'type': 'buy' if order.side == Side.BUY else 'sell',
            'token': self._token,
            'volume': str(order.qty),
            'price': str(order.price),
            'ordertype': order.order_type,
            'event': 'addOrder',
            'timeinforce': 'GTC',
            'reqid': req_id
        }
        await self.send_private(js)
        await self.on_new_order_single(order)

    async def replace_order(self, order: Order, price: float, qty: float) -> None:
        req_id: int = self._get_req_id()
        order.clorder_id = req_id
        js: dict = {
            'pair': order.symbol,
            'event': 'editOrder',
            'token': self._token,
            'orderid': order.order_id,
            'price': str(price),
            'volume': str(qty),
            'reqid': req_id
        }
        await self.send_private(js)
        pending: Order = Order(
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

    async def cancel_order(self, order: Order) -> None:
        req_id: int = self._get_req_id()
        order.clorder_id = req_id
        js: dict = {
            'event': 'cancelOrder',
            'token': self._token,
            'txid': [order.order_id],
            'reqid': req_id
        }
        await self.send_private(js)
        pending: Order = Order(
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

    async def subscribe(self, subscription: dict, is_private: bool = False, pair=None):
        if is_private:
            await self.subscribe_private(subscription, req_id=self._get_req_id())
        else:
            await self.subscribe_public(subscription, pair=pair)

    async def ping(self, is_private: bool) -> None:
        js: dict = {
            'event': 'ping',
            'reqid': self._get_req_id()
        }
        if is_private:
            await self.send_private(js)
        else:
            await self.send_public(js)

    async def cancel_all(self) -> None:
        await self.send_private({
            'event': 'cancelAll',
            'token': self._token,
            'reqid': self._get_req_id()
        })

    async def cancel_all_after(self, timeout: int) -> None:
        await self.send_private({
            'event': 'cancelAllOrdersAfter',
            'token': self._token,
            'timeout': timeout,
            'reqid': self._get_req_id()
        })

    async def on_book_snapshot(self, snapshot: list) -> None:
        await self.on_book_update_snapshot(BookSnapshot(*snapshot))

    async def on_book(self, update: list) -> None:
        await self.on_book_update(BookUpdate(*update))

    async def on_ohlc_(self, ohlc: list) -> None:
        await self.on_ohlc(Ohlc(*ohlc))

    async def on_trade_(self, trade: list) -> None:
        await self._on_trade(TradePayload(*trade))

    async def on_spread_(self, spread: list) -> None:
        await self.on_spread(SpreadPayload(*spread).spread)

    async def on_ticker_(self, ticker: list) -> None:
        await self.on_ticker(TickerPayload(*ticker).ticker)

    async def on_open_orders(self, orders: list) -> None:
        await self._on_open_orders(orders[0])

    async def on_own_trades(self, trades: list) -> None:
        await self._on_own_trades(trades[0])

    async def on_subscription_status_(self, js: dict) -> None:
        await self.on_subscription_status(SubscriptionStatus(js))

    async def on_heartbeat_(self, heartbeat: dict) -> None:
        await self.on_heartbeat(Heartbeat(*heartbeat))

    async def on_ping_(self, ping: dict) -> None:
        await self.on_ping(Ping(*ping))

    async def on_pong_(self, pong: dict) -> None:
        await self.on_pong(Pong(*pong))

    async def on_system_status_(self, js: dict) -> None:
        await self.on_system_status(SystemStatus(**js))

    async def on_add_order_status(self, js: dict) -> None:
        add_order_status: OrderStatus = OrderStatus(js)
        if add_order_status.status != 'ok':
            await self.on_new_order_reject(add_order_status)
        else:
            await self.on_new_order_ack(add_order_status.txid, add_order_status.reqid)

    async def on_edit_order_status(self, js: dict) -> None:
        replace_order_status: OrderStatus = OrderStatus(js)
        if replace_order_status.status != 'ok':
            await self.on_replace_order_reject(replace_order_status)
        else:
            await self.on_replace_order_ack(replace_order_status.txid, replace_order_status.reqid)

    async def on_cancel_order_status(self, js: dict) -> None:
        cancel_order_status: OrderStatus = OrderStatus(js)
        if cancel_order_status.status != 'ok':
            await self.on_cancel_order_reject(cancel_order_status)
        else:
            await self.on_cancel_order_ack(cancel_order_status.reqid)

    async def on_cancel_all_status(self, js: dict) -> None:
        status: CancelAllStatus = CancelAllStatus(js)
        if status.status != 'ok':
            await self.on_cancel_all_reject(status)
        else:
            await self.on_cancel_all(status)

    async def on_cancel_all_after_status_(self, js: dict) -> None:
        status: CancelAllOrdersAfterStatus = CancelAllOrdersAfterStatus(js)
        if status.status != 'ok':
            await self.on_cancel_all_after_status_reject(status)
        else:
            await self.on_cancel_all_after_status(status)

    @KrakAppBase._warn_not_implemented
    async def on_book_update_snapshot(self, snapshot: BookSnapshot) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_book_update(self, update: BookUpdate) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_ohlc(self, ohlc: Ohlc) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_trade(self, trade: Trade) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_spread(self, spread: Spread) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_subscription_status(self, status: SubscriptionStatus) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_system_status(self, state: SystemStatus) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_open_order_pending(self, order: Order) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_open_order_new(self, order_id: str) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_open_order_cancel(self, order_id: str) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_new_order_ack(self, order_id: Optional[str], clorder_id: int) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_replace_order_ack(self, order_id: Optional[str], clorder_id: int) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_cancel_order_ack(self, clorder_id: int) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_new_order_reject(self, order_status: OrderStatus) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_replace_order_reject(self, order_status: OrderStatus) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_cancel_order_reject(self, order_status: OrderStatus) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_cancel_all(self, status: CancelAllStatus) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_cancel_all_after_status(self, status: CancelAllOrdersAfterStatus) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_cancel_all_after_status_reject(self, status: CancelAllOrdersAfterStatus) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_cancel_all_reject(self, status: CancelAllStatus) -> None: ...
    @KrakAppBase._warn_not_implemented
    async def on_fill(self, fill: Fill) -> None: ...

    ''' optional (no warning) '''
    async def on_new_order_single(self, order: Order) -> None:
        """
        triggered immediately after the client sends a new order via new_order_single
        :param order:
        :return:
        """
        ...

    async def on_replace_order(self, order: Order) -> None:
        """
        triggered immediately after the client edits an order via replace_order
        :param order:
        :return:
        """

    async def on_cancel_order(self, order: Order) -> None:
        """
        triggered immediately after the client cancels an order via cancel_order
        :param order:
        :return:
        """

    async def on_ticker(self, ticker: Ticker) -> None:
        """
        triggered after receiving a ticker message
        :param ticker:
        :return:
        """

    async def on_heartbeat(self, heartbeat: Heartbeat) -> None:
        """
        triggered after receiving a heartbeat message
        :param heartbeat:
        :return:
        """

    async def on_pong(self, pong: Pong) -> None:
        """
        triggered after receiving a pong message
        :param pong:
        :return:
        """

    async def on_ping(self, ping: Ping) -> None:
        """
        triggered after sending a ping message
        :param ping:
        :return:
        """
