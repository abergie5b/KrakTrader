from typing import Optional

from . import Side, Fill, Position


class PositionManager:
    def __init__(self) -> None:
        self.fills = []

    def add_fill(self, fill: Fill):
        self.fills.append(fill)

    def get_position(self, symbol: str) -> Position:
        total_qty: float = 0
        avg_price: Optional[float] = None
        position: Position = Position(total_qty, symbol, None)
        for fill in self.fills:
            if fill.side == Side.SELL:
                total_qty += fill.qty * -1
            else:
                total_qty += fill.qty
            avg_price = total_qty * fill.price
        if total_qty != 0:
            position.avg_price = avg_price / total_qty
            position.qty = total_qty
        return position


