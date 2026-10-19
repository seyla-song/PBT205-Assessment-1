"""Unit tests for Task 2 - no RabbitMQ needed.

    python scripts/test_unit.py
"""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "task2-trading"))

from common.broker import endpoint_to_url, fmt_price  # noqa: E402
from exchange import valid_order  # noqa: E402
from order_book import OrderBook  # noqa: E402


def order(user, side, price, **extra):
    return {"user": user, "side": side, "price": price, "quantity": 100, "orderId": f"{user}-{price}", **extra}


class OrderBookTests(unittest.TestCase):
    def test_buy_with_no_resting_sell_is_added_to_the_book(self):
        book = OrderBook()
        self.assertIsNone(book.submit(order("alice", "BUY", 10)))
        self.assertEqual(book.snapshot()["bids"], ["alice@10"])

    def test_buy_at_or_above_resting_sell_matches_at_the_resting_price(self):
        book = OrderBook()
        book.submit(order("bob", "SELL", 10))
        match = book.submit(order("alice", "BUY", 11))
        self.assertEqual(match["price"], 10)
        self.assertEqual(match["buy"]["user"], "alice")
        self.assertEqual(match["sell"]["user"], "bob")
        self.assertEqual(book.snapshot()["asks"], [])

    def test_sell_at_or_below_resting_buy_matches_at_the_resting_price(self):
        book = OrderBook()
        book.submit(order("alice", "BUY", 12))
        self.assertEqual(book.submit(order("bob", "SELL", 10))["price"], 12)

    def test_non_crossing_prices_do_not_match(self):
        book = OrderBook()
        book.submit(order("bob", "SELL", 12))
        self.assertIsNone(book.submit(order("alice", "BUY", 10)))
        snap = book.snapshot()
        self.assertEqual(len(snap["asks"]) + len(snap["bids"]), 2)

    def test_best_price_wins_then_earliest_arrival(self):
        book = OrderBook()
        book.submit(order("s1", "SELL", 11))
        book.submit(order("s2", "SELL", 10))
        book.submit(order("s3", "SELL", 10, orderId="s3b"))
        self.assertEqual(book.submit(order("buyer", "BUY", 11))["sell"]["user"], "s2")

    def test_matched_order_is_removed_and_cannot_trade_twice(self):
        book = OrderBook()
        book.submit(order("bob", "SELL", 10))
        book.submit(order("alice", "BUY", 10))
        self.assertIsNone(book.submit(order("carol", "BUY", 10)))

    def test_each_stock_has_its_own_book(self):
        books = {"XYZ": OrderBook(), "ABC": OrderBook()}
        books["XYZ"].submit(order("alice", "BUY", 10))
        self.assertIsNone(books["ABC"].submit(order("bob", "SELL", 10)))


class HelperTests(unittest.TestCase):
    def test_price_formatting(self):
        self.assertEqual(fmt_price(10.5), "10.5")
        self.assertEqual(fmt_price(11.0), "11")
        self.assertEqual(fmt_price(5), "5")

    def test_endpoint_forms(self):
        self.assertEqual(endpoint_to_url("5672"), "amqp://guest:guest@localhost:5672")
        self.assertEqual(endpoint_to_url("myhost:5673"), "amqp://guest:guest@myhost:5673")
        self.assertEqual(endpoint_to_url("amqp://u:p@h:1"), "amqp://u:p@h:1")

    def test_exchange_accepts_good_orders_and_rejects_bad_ones(self):
        good = {"type": "order", "user": "alice", "symbol": "XYZ", "side": "BUY", "quantity": 100, "price": 10.5}
        self.assertTrue(valid_order(good))
        for change in ({"side": "HOLD"}, {"price": -1}, {"price": 0}, {"quantity": 0},
                       {"quantity": 1.5}, {"symbol": 5}, {"type": "trade"}, {"price": True}):
            self.assertFalse(valid_order({**good, **change}), change)
        self.assertFalse(valid_order(None))


class SendOrderArgumentTests(unittest.TestCase):
    """send_order.py checks its arguments before it connects, so no broker is needed."""

    def run_send_order(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "task2-trading" / "send_order.py"), *args],
                              capture_output=True, text=True, timeout=20)

    def test_quantity_must_be_100(self):
        result = self.run_send_order("eve", "5672", "BUY", "50", "10")
        self.assertEqual(result.returncode, 1)
        self.assertIn("fixed at 100", result.stderr)

    def test_side_must_be_buy_or_sell(self):
        result = self.run_send_order("eve", "5672", "HOLD", "100", "10")
        self.assertEqual(result.returncode, 1)
        self.assertIn("BUY or SELL", result.stderr)

    def test_price_must_be_positive(self):
        result = self.run_send_order("eve", "5672", "BUY", "100", "-3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("PRICE", result.stderr)

    def test_missing_arguments_print_usage(self):
        result = self.run_send_order("eve")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
