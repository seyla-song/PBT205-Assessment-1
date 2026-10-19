"""Order book for ONE stock (C1).

Resting orders are kept in two lists, each sorted by price priority and then by
arrival time:
    bids (BUY orders):  highest price first
    asks (SELL orders): lowest price first

A plain sorted list is the simplest structure that is clearly correct for the few
orders in this assignment (insertion is O(n)); a heap or tree would be the upgrade
if volume grew.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.broker import fmt_price  # noqa: E402


class OrderBook:
    def __init__(self):
        self.bids = []
        self.asks = []
        self._seq = 0

    def submit(self, order):
        """Match `order` against the opposite side.

        If a resting order has an acceptable price, remove it from the book and return
        a match dict {price, quantity, buy, sell}. The trade happens at the price of the
        order that was already waiting (the resting order). Otherwise the order is added
        to the book and None is returned.
        """
        is_buy = order["side"] == "BUY"
        opposite = self.asks if is_buy else self.bids
        best = opposite[0] if opposite else None

        if best is not None and (order["price"] >= best["price"] if is_buy else order["price"] <= best["price"]):
            opposite.pop(0)
            return {
                "price": best["price"],
                "quantity": min(order["quantity"], best["quantity"]),
                "buy": order if is_buy else best,
                "sell": best if is_buy else order,
            }

        self._seq += 1
        entry = dict(order, seq=self._seq)
        own = self.bids if is_buy else self.asks
        own.append(entry)
        if is_buy:
            own.sort(key=lambda o: (-o["price"], o["seq"]))
        else:
            own.sort(key=lambda o: (o["price"], o["seq"]))
        return None

    def snapshot(self):
        return {
            "bids": [f"{o['user']}@{fmt_price(o['price'])}" for o in self.bids],
            "asks": [f"{o['user']}@{fmt_price(o['price'])}" for o in self.asks],
        }
