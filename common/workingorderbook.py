import sys
from typing import (
    List,
    Dict,
    Union,
    Optional
)

from . import Order, Fill
from .logger import get_logger


class WorkingOrderBook:
    def __init__(self) -> None:
        self.orders: Dict[str, Order] = {}
        self.pendings: Dict[Union[int | str], Order] = {}
        self._canceled_order_ids: List[str] = []
        self._logger = get_logger(f'{__name__}.working_orders')

    def get_order(self, order_id: str):
        return self.orders.get(order_id)

    def on_open_order_pending(self, order: Order) -> None:
        if order.order_id:
            self.pendings[order.order_id] = order
        else:
            self._logger.warning(f'received pending order with None order_id {order}')

    def on_open_order_new(self, order_id: str):
        order: Optional[Order] = self.pendings.pop(order_id, None)
        if order:
            self.orders[order_id] = order
        else:
            self._logger.warning(f'open_order_new: failed to find pending order_id for {order_id}')

    def on_open_order_cancel(self, order_id: str):
        if order_id not in self._canceled_order_ids:
            order: Optional[Order] = self.orders.pop(order_id, None)
            if order:
                self._canceled_order_ids.append(order_id)
            else:
                self._logger.warning(f'open_order_cancel: failed to find order_id {order_id}')

    def on_pending(self, order: Order) -> None:
        if order.clorder_id != -sys.maxsize:
            self.pendings[order.clorder_id] = order
        else:
            self._logger.warning(f'received pending order with None clorder_id {order}')

    def remove_pending(self, clorder_id: Optional[int]) -> None:
        if not clorder_id:
            self._logger.warning(f'failed to remove pending order with None clorder_id')
        else:
            order: Optional[Order] = self.pendings.pop(clorder_id, None)
            if not order:
                self._logger.warning(f'failed to remove pending order: {clorder_id}')

    def new_order_ack(self, order_id: Optional[str], clorder_id: int) -> None:
        pending: Optional[Order] = self.pendings.pop(clorder_id, None)
        if not pending:
            self._logger.warning(f'pending order not found for {clorder_id}')
        else:
            if order_id:
                pending.order_id = order_id
                self.orders[order_id] = pending
            else:
                self._logger.warning(f'new_order_ack received pending with None order_id {pending}')

    def replace_order_ack(self, order_id: Optional[str], clorder_id: int):
        pending: Optional[Order] = self.pendings.pop(clorder_id, None)
        if not pending or not pending.clorder_id:
            self._logger.warning(f'pending order not found for {clorder_id}')
        else:
            if pending.order_id:
                order: Optional[Order] = self.orders.get(pending.order_id, None)
                if not order:
                    self._logger.warning(f'failed to find replaced order {pending.order_id}')
                else:
                    order.order_status = 'replaced'
                    order.order_id = order_id
                    order.clorder_id = pending.clorder_id
                    order.qty = pending.qty
                    order.price = pending.price
            else:
                self._logger.warning(f'replace_order_ack received pending with None order_id {pending}')

    def cancel_order_ack(self, clorder_id: int) -> None:
        pending: Optional[Order] = self.pendings.pop(clorder_id, None)
        if not pending:
            self._logger.warning(f'pending order not found for {clorder_id}')
        else:
            if pending.order_id:
                if pending.order_id not in self._canceled_order_ids:
                    order: Optional[Order] = self.orders.pop(pending.order_id, None)
                    if not order:
                        self._logger.warning(f'failed to find canceled order {pending.order_id}')
                    else:
                        self._canceled_order_ids.append(pending.order_id)
            else:
                self._logger.warning(f'cancel_order_ack received pending with None order_id {pending}')

    def fill(self, fill: Fill) -> None:
        if fill.order_id:
            order: Optional[Order] = self.orders.get(fill.order_id)
            if order and order.order_id:
                order.qty -= fill.qty
                order.cum_qty += fill.qty
                if order.qty == 0:
                    self.orders.pop(order.order_id)
                elif order.qty < 0:
                    self._logger.warning(f'fill order has < 0 qty {order.order_id}')
            else:
                self._logger.warning(f'failed to find order for fill: {fill}')
        else:
            self._logger.warning(f'received fill without an order id: {fill}')

    def cancel_all(self) -> None:
        self.orders.clear()

