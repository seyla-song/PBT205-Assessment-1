"""C2 - sendOrder.

Usage:  python task2-trading/send_order.py <username> <endpoint> <BUY|SELL> <quantity> <price> [stock]

Connects, publishes ONE order to the 'orders' topic and exits straight away.
The quantity is fixed at 100 shares for this assignment; the stock defaults to XYZ.
"""
import math
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.broker import connect, publish, close, now_iso, fmt_price  # noqa: E402

FIXED_QUANTITY = 100
USAGE = "Usage: python task2-trading/send_order.py <username> <endpoint> <BUY|SELL> <quantity=100> <price> [stock]"


def fail(message=None):
    if message:
        print(message, file=sys.stderr)
    print(USAGE, file=sys.stderr)
    sys.exit(1)


def to_number(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def main():
    args = sys.argv[1:]
    if len(args) < 5:
        fail()
    username, endpoint, side_arg, qty_arg, price_arg = args[:5]
    symbol = (args[5] if len(args) > 5 else "XYZ").upper()

    side = side_arg.upper()
    quantity = to_number(qty_arg)
    price = to_number(price_arg)

    if not username:
        fail()
    if side not in ("BUY", "SELL"):
        fail("SIDE must be BUY or SELL")
    if quantity is None or not float(quantity).is_integer():
        fail("QUANTITY must be an integer")
    quantity = int(quantity)
    if quantity != FIXED_QUANTITY:
        fail(f"QUANTITY is fixed at {FIXED_QUANTITY} for this assignment")
    if price is None or price <= 0:
        fail("PRICE must be a positive number")

    connection, channel = connect(endpoint)
    channel.confirm_delivery()   # wait until the broker has accepted the order before exiting
    millis = int(time.time() * 1000)
    order = {
        "type": "order",
        "orderId": f"{username}-{millis}-{os.getpid()}",
        "user": username,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price,
        "ts": now_iso(),
    }
    publish(channel, "orders", order)
    print(f"Sent {side} {quantity} {symbol} @ {fmt_price(price)} as {username}")
    close(connection)


if __name__ == "__main__":
    main()
