import sys
from typing import Optional

import app
from .book import Book
from .publisher import Publisher
from kraken import (
    SubscriptionStatus,
    SymbolConfigMap,
    CancelAllStatus,
    SymbolConfig,
    SystemStatus,
    BookSnapshot,
    OrderStatus,
    BookUpdate,
    KrakApp,
    Spread,
    Ticker,
    Ohlc
)
from common import (
    WorkingOrderBook,
    PositionTracker,
    get_logger,
    quotePool,
    FinMath,
    Order,
    Trade,
    Side,
    Fill
)


def log(f):
    async def _wraps(*args):
        args[0]._logger.info(f'{f.__name__} -> {args[1:]}')
        await f(*args)
    return _wraps


class KrakTrader(KrakApp):
    def __init__(
        self,
        symbol: str,
        url: str,
        auth_url: str,
        http_url: str,
        key: str,
        secret: str,
        publisher: Publisher = None
    ):
        super().__init__(url, auth_url, http_url, key, secret)
        self._symbol = symbol
        self._symbol_config: SymbolConfig = SymbolConfigMap[symbol]
        self._book: Optional[Book] = None
        self._workingorders: WorkingOrderBook = WorkingOrderBook()
        self._position_tracker: PositionTracker = PositionTracker()
        self._subscriptions = []
        self._system_status = None
        self._strategy: app.StupidScalperStrategy = app.StupidScalperStrategy(self, self._symbol_config)
        self._trade_monitor: app.TradeMonitor = app.TradeMonitor(self._symbol_config)
        self._logger = get_logger(__name__)

        #
        if publisher:
            self._publisher = publisher
            self._publisher.on_new_connection(self.on_new_ui_connection)
            self._publisher.on_receive_message(self.on_receive_ui_nos, 'new_order_single')
            self._publisher.on_receive_message(self.on_receive_ui_cancel, 'cancel_order')

    async def on_new_ui_connection(self):
        await self._publisher.publish(
            self._symbol_config
        )
        await self._publisher.publish(
            self._workingorders.orders
        )

        for trade in self._trade_monitor.trades():
            await self._publisher.publish(trade)

        for sub in self._subscriptions:
            await self._publisher.publish(sub)

        await self._publisher.publish(self._system_status)

        await self._publisher.publish(
            self._position_tracker.get_position(self._symbol)
        )

    @log
    async def on_receive_ui_cancel(self, *args):
        message = args[0]
        order: Order = self._workingorders.get_order(message['order_id'])
        if order:
            await self.cancel_order(order)

    @log
    async def on_receive_ui_nos(self, *args):
        message = args[0]
        order: Order = Order(
            self._symbol,
            Side.SELL if message['side'] == 's' else Side.BUY,
            -sys.maxsize,
            self._symbol_config.minimum_lot_size,
            message['price'],
            'limit',
            'pendingNew',
            'GTC'
        )
        await self.new_order_single(order)

    async def start(self, tasks=None):
        tasks = []
        if self._publisher:
            tasks.append(self._publisher.start())
        await super().start(tasks=tasks)

    async def on_book_update_snapshot(self, snapshot: BookSnapshot) -> None:
        self._book = Book(snapshot)
        if self._publisher:
            await self._publisher.publish(self._book)

    async def on_book_update(self, update: BookUpdate) -> None:
        if self._book:
            self._book.update(update)

            #await self._strategy.update()

            if self._book.best_bid().price > self._book.best_ask().price:
                self._logger.warning(f"crossed book: {self._book.best_bid()}/{self._book.best_ask()}")

            if self._publisher:
                await self._publisher.publish(self._book)
                await self._publisher.publish([FinMath.vwap(self._book.asks, 3), FinMath.vwap(self._book.bids, 3)])
        else:
            self._logger.warning(f'STALE QUOTES -> book update received before snapshot')

    @log
    async def on_ohlc(self, ohlc: Ohlc) -> None:
        pass

    async def on_trade(self, trade: Trade) -> None:
        self._trade_monitor.update(trade)
        if self._publisher:
            await self._publisher.publish(trade)

    @log
    async def on_ticker(self, ticker: Ticker) -> None:
        ...

    @log
    async def on_spread(self, spread: Spread) -> None:
        ...

    @log
    async def on_subscription_status(self, status: SubscriptionStatus) -> None:
        self._subscriptions.append(status)
        if self._publisher:
            await self._publisher.publish(status)

    @log
    async def on_system_status(self, state: SystemStatus) -> None:
        self._system_status = state
        if self._publisher:
            await self._publisher.publish(state)

    @log
    async def on_open_order_pending(self, pending: Order) -> None:
        self._workingorders.on_open_order_pending(pending)

    @log
    async def on_open_order_new(self, order_id: str) -> None:
        self._workingorders.on_open_order_new(order_id)
        if self._publisher:
            await self._publisher.publish(self._workingorders.orders)

    @log
    async def on_open_order_cancel(self, order_id: str) -> None:
        self._workingorders.on_open_order_cancel(order_id)
        if self._publisher:
            await self._publisher.publish(self._workingorders.orders)

    @log
    async def on_new_order_single(self, pending: Order) -> None:
        self._workingorders.on_pending(pending)

    @log
    async def on_replace_order(self, pending: Order) -> None:
        self._workingorders.on_pending(pending)

    @log
    async def on_cancel_order(self, pending: Order) -> None:
        self._workingorders.on_pending(pending)

    @log
    async def on_new_order_ack(self, order_id: Optional[str], clorder_id: int) -> None:
        self._workingorders.new_order_ack(order_id, clorder_id)

    @log
    async def on_replace_order_ack(self, order_id: Optional[str], clorder_id: int) -> None:
        self._workingorders.replace_order_ack(order_id, clorder_id)
        if self._publisher:
            await self._publisher.publish(self._workingorders.orders)

    @log
    async def on_cancel_order_ack(self, clorder_id: int) -> None:
        self._workingorders.cancel_order_ack(clorder_id)
        if self._publisher:
            await self._publisher.publish(self._workingorders.orders)

    @log
    async def on_new_order_reject(self, status: OrderStatus) -> None:
        self._workingorders.remove_pending(status.reqid)
        if self._publisher:
            await self._publisher.publish(status)

    @log
    async def on_replace_order_reject(self, status: OrderStatus) -> None:
        self._workingorders.remove_pending(status.reqid)
        if self._publisher:
            await self._publisher.publish(status)

    @log
    async def on_cancel_order_reject(self, status: OrderStatus) -> None:
        self._workingorders.remove_pending(status.reqid)
        if self._publisher:
            await self._publisher.publish(status)

    @log
    async def on_fill(self, fill: Fill) -> None:
        self._workingorders.fill(fill)
        self._position_tracker.add_fill(fill)
        if self._publisher:
            await self._publisher.publish(self._workingorders.orders)
            await self._publisher.publish(
                self._position_tracker.get_position(self._symbol)
            )

    @log
    async def on_cancel_all(self, status: CancelAllStatus) -> None:
        self._workingorders.cancel_all()
        if self._publisher:
            await self._publisher.publish(self._workingorders.orders)

    @log
    async def on_cancel_all_reject(self, status: CancelAllStatus) -> None:
        if self._publisher:
            await self._publisher.publish(status)
