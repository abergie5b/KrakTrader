from .krak_app import KrakApp
from .messages import (
    MarketDataSnapshot, 
    SubscriptionStatus, 
    MarketDataUpdate, 
    SnapshotQuotes,
    TradeUpdate, 
    SystemState,
)

class SymbolConfig:
    def __init__(self, name:str, ccy:str, tick_size:float):
        self.name = name
        self.ccy = ccy
        self.tick_size = tick_size


SymbolConfigMap:dict = {
    'XBT/USD': SymbolConfig('XBT/USD', 'USD', 0.1)
}

