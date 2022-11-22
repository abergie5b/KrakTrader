import datetime as dt
from typing import Dict, List, Optional

from common import Trade
from kraken import SymbolConfig

class TradeMonitor:
    def __init__(self, symbol_config:SymbolConfig):
        self._symbol_config = symbol_config
        self._trades:List[Trade] = []

    def get_aggregate(self, from_:int = 300) -> Dict[int, float]:
        from_timestamp:float = dt.datetime.now().timestamp() - from_
        aggregates:Dict[int, float] = {}
        for trade in filter(lambda t: t.time >= from_timestamp, self._trades):
            price:int = int(trade.price / self._symbol_config.tick_size)
            qty:Optional[float] = aggregates.get(price, None)
            if not qty:
                aggregates[price] = trade.volume
            else:
                aggregates[price] += trade.volume
        return aggregates

    def update(self, trade:Trade):
        self._trades.append(trade)

