"""C1 - the exchange.

Usage:  python task2-trading/exchange.py <endpoint>

Subscribes to the 'orders' topic, matches each order against the order book for its
stock and publishes every match to the 'trades' topic. Only ONE exchange may run.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.broker import connect, publish, subscribe, close, now_iso, fmt_price  # noqa: E402
from order_book import OrderBook  # noqa: E402


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_order(o):
    return (
        isinstance(o, dict)
        and o.get("type") == "order"
        and isinstance(o.get("user"), str)
        and isinstance(o.get("symbol"), str)
        and o.get("side") in ("BUY", "SELL")
        and isinstance(o.get("quantity"), int)
        and not isinstance(o.get("quantity"), bool)
        and o["quantity"] > 0
        and is_number(o.get("price"))
        and o["price"] > 0
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python task2-trading/exchange.py <endpoint>", file=sys.stderr)
        sys.exit(1)
    endpoint = sys.argv[1]

    books = {}        # stock symbol -> OrderBook (one independent book per stock)
    trade_seq = [0]

    connection, channel = connect(endpoint)

    def on_order(order, _key):
        if not valid_order(order):
            print("Rejected invalid order:", json.dumps(order), file=sys.stderr, flush=True)
            return
        book = books.setdefault(order["symbol"], OrderBook())
        print(f"ORDER  {order['user']} {order['side']} {order['quantity']} {order['symbol']} @ {fmt_price(order['price'])}", flush=True)

        match = book.submit(order)
        if match:
            trade_seq[0] += 1
            trade = {
                "type": "trade",
                "tradeId": trade_seq[0],
                "symbol": order["symbol"],
                "price": match["price"],
                "quantity": match["quantity"],
                "buyer": match["buy"]["user"],
                "seller": match["sell"]["user"],
                "buyOrderId": match["buy"].get("orderId"),
                "sellOrderId": match["sell"].get("orderId"),
                "ts": now_iso(),
            }
            publish(channel, "trades", trade)
            print(f"TRADE  #{trade['tradeId']} {trade['symbol']} {trade['quantity']} @ {fmt_price(trade['price'])} "
                  f"(buyer {trade['buyer']}, seller {trade['seller']})", flush=True)
        else:
            print(f"BOOK   {order['symbol']} {json.dumps(book.snapshot(), separators=(',', ':'))}", flush=True)

    subscribe(channel, "orders", on_order)
    print('Exchange running. Subscribed to "orders", publishing to "trades".', flush=True)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\nExchange stopped.", flush=True)
    finally:
        close(connection)


if __name__ == "__main__":
    main()
