from .krak_app import KrakApp
from .messages import (
    CancelAllOrdersAfterStatus,
    SubscriptionStatus,
    CancelAllStatus,
    bookUpdatePool,
    TradePayload,
    SystemStatus,
    BookSnapshot,
    OrderStatus,
    BookUpdate,
    Spread,
    Ticker,
    Ohlc
)
from .book import Book


class SymbolConfig:
    def __init__(self, name: str, ccy: str, tick_size: float, minimum_lot_size: float):
        self.name = name
        self.ccy = ccy
        self.tick_size = tick_size
        self.minimum_lot_size = minimum_lot_size


SymbolConfigMap: dict = {
    'XBT/USD': SymbolConfig('XBT/USD', 'USD', 0.1, 0.0001),
    'ETH/USD': SymbolConfig('ETH/USD', 'USD', 0.01, 0.01),
    'USDT/EUR': SymbolConfig('USDT/EUR', 'EUR', 0.0001, 0.0001),
    'NANO/USD': SymbolConfig('NANO/USD', 'USD', 0.0001, 0.0001),
    'ATOM/USD': SymbolConfig('ATOM/USD', 'USD', 0.0001, 0.01),
    'DOT/USD': SymbolConfig('DOT/USD', 'USD', 0.0001, 0.01),
    'EUR/USD': SymbolConfig('EUR/USD', 'USD', 0.0001, 0.0001)
}

