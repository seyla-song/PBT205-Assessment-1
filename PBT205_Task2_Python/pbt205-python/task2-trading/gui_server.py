"""C3 - GUI showing "Last price: X" taken from the 'trades' topic.

Usage:  python task2-trading/gui_server.py <endpoint> [port=3002]
Then open http://localhost:3002  (the exchange must be running separately).

Standard library only (http.server + Server-Sent Events) plus pika:
  * a background thread subscribes to 'trades' and 'orders' and keeps the latest state;
  * each browser keeps an event stream open (/api/stream) and is pushed every new trade/order;
  * POST /api/order publishes an order, exactly like send_order.py (quantity fixed at 100).
"""
import json
import math
import os
import queue
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.broker import connect, publish, subscribe, close, now_iso  # noqa: E402

HERE = Path(__file__).resolve().parent
DEFAULT_SYMBOLS = ["XYZ"]

state_lock = threading.Lock()
last_price = {}   # symbol -> {"price": ..., "ts": ...}
trades = []       # newest first, max 50
orders = []       # newest first, max 50
clients = set()   # one queue.Queue per open browser stream
endpoint = None


def snapshot():
    with state_lock:
        symbols = list(dict.fromkeys(DEFAULT_SYMBOLS + list(last_price)))
        return {"last": dict(last_price), "trades": list(trades), "orders": list(orders), "symbols": symbols}


def broadcast(event, data):
    with state_lock:
        targets = list(clients)
    for q in targets:
        q.put((event, data))


def listen_to_broker():
    """Background thread: its own connection, receives 'trades' and 'orders'."""
    connection, channel = connect(endpoint)

    def on_trade(trade, _key):
        with state_lock:
            last_price[trade["symbol"]] = {"price": trade["price"], "ts": trade["ts"]}
            trades.insert(0, trade)
            del trades[50:]
        broadcast("trade", trade)

    def on_order(order, _key):
        with state_lock:
            orders.insert(0, order)
            del orders[50:]
        broadcast("order", order)

    subscribe(channel, "trades", on_trade)
    subscribe(channel, "orders", on_order)
    try:
        channel.start_consuming()
    finally:
        close(connection)


def send_order(body):
    """Validate an order from the browser form and publish it. Returns an error text or None."""
    side = str(body.get("side", "")).upper()
    symbol = str(body.get("symbol") or "XYZ").upper()
    user = str(body.get("user", "")).strip()
    try:
        price = float(body.get("price"))
    except (TypeError, ValueError):
        price = float("nan")

    if not re.fullmatch(r"[\w-]{1,20}", user):
        return "Trader name: 1-20 letters, digits, _ or -"
    if side not in ("BUY", "SELL"):
        return "Side must be BUY or SELL"
    if not re.fullmatch(r"[A-Z]{1,6}", symbol):
        return "Symbol: 1-6 letters"
    if not math.isfinite(price) or price <= 0:
        return "Price must be a positive number"

    millis = int(time.time() * 1000)
    order = {"type": "order", "orderId": f"{user}-{millis}-gui", "user": user, "symbol": symbol,
             "side": side, "quantity": 100, "price": price, "ts": now_iso()}
    connection, channel = connect(endpoint)      # short-lived connection: simple and thread-safe
    try:
        channel.confirm_delivery()
        publish(channel, "orders", order)
    finally:
        close(connection)
    return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):   # keep the terminal clean
        pass

    def _json(self, code, obj):
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            page = (HERE / "gui" / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        elif path == "/api/state":
            self._json(200, snapshot())
        elif path == "/api/stream":
            self._stream()
        else:
            self._json(404, {"error": "not found"})

    def _stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        q = queue.Queue()
        with state_lock:
            clients.add(q)
        try:
            self._event("state", snapshot())
            while True:
                try:
                    event, data = q.get(timeout=15)
                    self._event(event, data)
                except queue.Empty:
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            with state_lock:
                clients.discard(q)

    def _event(self, event, data):
        self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8"))
        self.wfile.flush()

    def do_POST(self):
        if urlparse(self.path).path != "/api/order":
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._json(400, {"error": "Invalid request"})
        error = send_order(body)
        if error:
            return self._json(400, {"error": error})
        self._json(200, {"ok": True})


def main():
    global endpoint
    if len(sys.argv) < 2:
        print("Usage: python task2-trading/gui_server.py <endpoint> [port]", file=sys.stderr)
        sys.exit(1)
    endpoint = sys.argv[1]
    port = int(sys.argv[2] if len(sys.argv) > 2 else os.environ.get("GUI_PORT", 3002))

    # Fail early with a clear message if the broker is not there.
    connection, _channel = connect(endpoint)
    close(connection)

    threading.Thread(target=listen_to_broker, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    print(f"Trading GUI on http://localhost:{port}  (broker endpoint {endpoint})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nGUI stopped.", flush=True)


if __name__ == "__main__":
    main()
