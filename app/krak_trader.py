from typing import Any, List, Callable, Coroutine, Optional

import app
from .book import Book
from kraken import (
    BookSnapshot,
    SubscriptionStatus,
    BookUpdate,
    SymbolConfigMap,
    CancelAllStatus,
    OrderStatus,
    SystemStatus,
    KrakApp,
    Ticker,
    Ohlc
)
from common import (
    Side,
    Fill,
    Order, 
    Trade,
    WorkingOrderBook,
    get_logger
)


def log(f):
    async def _wraps(*args):
        args[0]._logger.info(f'{f.__name__} -> {args[1:]}')
        await f(*args)
    return _wraps


class KrakTrader(KrakApp):
    def __init__(
        self, 
        url: str,
        auth_url: str,
        http_url: str,
        key: str,
        secret: str
    ):
        super().__init__(url, auth_url, http_url, key, secret)
        self._book: Optional[Book] = None
        self._workingorders: WorkingOrderBook = WorkingOrderBook()
        self._strategy:app.StupidScalperStrategy = app.StupidScalperStrategy(self, SymbolConfigMap['XBT/USD'])
        self._trade_monitor: app.TradeMonitor = app.TradeMonitor(SymbolConfigMap['XBT/USD'])
        self._logger = get_logger(__name__)

    async def on_book_update_snapshot(self, snapshot: BookSnapshot) -> None:
        self._book = Book(snapshot)

    async def on_book_update(self, update: BookUpdate) -> None:
        if self._book:
            self._book.update(update)
            # await self._strategy.update()
        else:
            self._logger.warning(f'STALE QUOTES -> book update received before snapshot')

    @log
    async def on_ohlc(self, ohlc: Ohlc) -> None:
        pass

    @log
    async def on_trade(self, trade: Trade) -> None:
        self._trade_monitor.update(trade)

    @log
    async def on_ticker(self, ticker: Ticker) -> None:
        ...

    @log
    async def on_subscription_status(self, status: SubscriptionStatus) -> None:
        pass

    @log
    async def on_system_status(self, state: SystemStatus) -> None:
        pass

    @log
    async def on_open_order_pending(self, pending: Order) -> None:
        self._workingorders.on_open_order_pending(pending)

    @log
    async def on_open_order_new(self, order_id: str) -> None:
        self._workingorders.on_open_order_new(order_id)

    @log
    async def on_open_order_cancel(self, order_id: str) -> None:
        self._workingorders.on_open_order_cancel(order_id)

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

    @log
    async def on_cancel_order_ack(self, clorder_id: int) -> None:
        self._workingorders.cancel_order_ack(clorder_id)

    @log
    async def on_new_order_reject(self, status: OrderStatus) -> None:
        self._workingorders.remove_pending(status.reqid)

    @log
    async def on_replace_order_reject(self, status: OrderStatus) -> None:
        self._workingorders.remove_pending(status.reqid)

    @log
    async def on_cancel_order_reject(self, status: OrderStatus) -> None:
        self._workingorders.remove_pending(status.reqid)

    @log
    async def on_fill(self, fill: Fill) -> None:
        self._workingorders.fill(fill)

    @log
    async def on_cancel_all(self, status: CancelAllStatus) -> None:
        self._workingorders.cancel_all()

    @log
    async def on_cancel_all_reject(self, status: CancelAllStatus) -> None:
        pass
