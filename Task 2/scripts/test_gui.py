"""C3 - GUI test: drives the GUI server's HTTP / event-stream API (what the browser page uses).

    python scripts/test_gui.py            (RabbitMQ must be running; port 3002 must be free)

Writes docs/test-evidence/gui-test.txt
"""
import http.client
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Session, ENDPOINT, sleep  # noqa: E402

PORT = 3002


def post_order(body):
    connection = http.client.HTTPConnection("localhost", PORT, timeout=10)
    connection.request("POST", "/api/order", json.dumps(body), {"Content-Type": "application/json"})
    response = connection.getresponse()
    data = json.loads(response.read() or b"{}")
    connection.close()
    return response.status, data


def get(path):
    connection = http.client.HTTPConnection("localhost", PORT, timeout=10)
    connection.request("GET", path)
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response.status, body


def listen_to_stream(events, stop):
    """Collect (event, data) pairs from /api/stream, as the browser's EventSource does."""
    connection = http.client.HTTPConnection("localhost", PORT, timeout=30)
    connection.request("GET", "/api/stream")
    response = connection.getresponse()
    event = None
    while not stop.is_set():
        line = response.fp.readline().decode("utf-8").rstrip("\r\n")
        if line.startswith("event: "):
            event = line[7:]
        elif line.startswith("data: ") and event:
            events.append((event, json.loads(line[6:])))
            event = None
    connection.close()


def until(predicate, seconds=6):
    end = time.time() + seconds
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def main():
    s = Session("C3 GUI test: GUI server shows the last price from the 'trades' topic")
    exchange = s.start("exchange", "task2-trading/exchange.py", [ENDPOINT])
    gui = s.start("trading-gui", "task2-trading/gui_server.py", [ENDPOINT, PORT])
    s.wait_for(exchange, r"Exchange running")
    s.wait_for(gui, r"Trading GUI on")

    status, page = get("/")
    s.check("GUI page is served and contains 'Last price'", status == 200 and b"Last price" in page)

    events, stop = [], threading.Event()
    threading.Thread(target=listen_to_stream, args=(events, stop), daemon=True).start()
    s.check("event stream opens with the current state", until(lambda: any(e == "state" for e, _ in events)))

    post_order({"user": "alice", "side": "BUY", "symbol": "XYZ", "price": 10.5})
    post_order({"user": "bob", "side": "SELL", "symbol": "XYZ", "price": 10})
    s.check("GUI receives the trade and the last XYZ price is 10.5",
            until(lambda: any(e == "trade" and d["symbol"] == "XYZ" and d["price"] == 10.5 for e, d in events)))

    post_order({"user": "carol", "side": "BUY", "symbol": "ABC", "price": 3})
    post_order({"user": "dave", "side": "SELL", "symbol": "ABC", "price": 3})
    s.check("multiple stocks: the ABC trade appears independently",
            until(lambda: any(e == "trade" and d["symbol"] == "ABC" and d["price"] == 3 for e, d in events)))

    _, body = get("/api/state")
    state = json.loads(body)
    s.check("state holds a last price per stock (XYZ 10.5, ABC 3)",
            state["last"].get("XYZ", {}).get("price") == 10.5 and state["last"].get("ABC", {}).get("price") == 3)
    s.check("a late-joining browser gets the trades so far", len(state["trades"]) == 2 and len(state["orders"]) >= 4)

    s.check("invalid order (price -1) is rejected with HTTP 400",
            post_order({"user": "x", "side": "BUY", "symbol": "XYZ", "price": -1})[0] == 400)
    s.check("invalid order (side HOLD) is rejected with HTTP 400",
            post_order({"user": "x", "side": "HOLD", "symbol": "XYZ", "price": 5})[0] == 400)

    stop.set()
    s.finish("gui-test.txt")


if __name__ == "__main__":
    main()
