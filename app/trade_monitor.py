from queue import LifoQueue
from typing import Dict, Optional

from common import Trade
from kraken import SymbolConfig


class TradeMonitor:
    def __init__(self, symbol_config: SymbolConfig):
        self._symbol_config = symbol_config
        self._trades: LifoQueue[Trade] = LifoQueue(maxsize=100)

    def trades(self):
        return list(self._trades.queue)

    def get_aggregate(self) -> Dict[int, float]:
        aggregates: Dict[int, float] = {}
        for trade in list(self._trades.queue):
            price: int = int(trade.price / self._symbol_config.tick_size)
            qty: Optional[float] = aggregates.get(price, None)
            if not qty:
                aggregates[price] = trade.volume
            else:
                aggregates[price] += trade.volume
        return aggregates

    def update(self, trade: Trade):
        if self._trades.full():
            self._trades.get()
        self._trades.put(trade)
        #print(self.get_aggregate())
