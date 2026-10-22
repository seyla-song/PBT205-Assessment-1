"""C4 - Trading integration test: the real exchange and several real send_order
processes talk through RabbitMQ, while this script listens on the 'trades' topic.

    python scripts/test_trading.py        (RabbitMQ must be running)

Writes docs/test-evidence/trading-test.txt
"""
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from harness import Session, ENDPOINT, sleep  # noqa: E402
from common.broker import connect, subscribe, close  # noqa: E402


def run_order(session, label, args):
    proc = session.start(label, "task2-trading/send_order.py", args)
    return session.wait_exit(proc)


def main():
    s = Session("C4 Trading integration test: sendOrder -> exchange -> trades")
    trades = []
    ready, stop = threading.Event(), threading.Event()

    def listen_to_trades():
        connection, channel = connect(ENDPOINT)

        def on_trade(trade, _key):
            trades.append(trade)
            s.log_line(f"[trades topic] {json.dumps(trade, separators=(',', ':'))}")

        subscribe(channel, "trades", on_trade)
        ready.set()
        while not stop.is_set():
            connection.process_data_events(time_limit=0.1)
        close(connection)

    listener = threading.Thread(target=listen_to_trades, daemon=True)
    listener.start()
    ready.wait(10)

    exchange = s.start("exchange", "task2-trading/exchange.py", [ENDPOINT])
    s.check("exchange started", s.wait_for(exchange, r"Exchange running"))

    s.check("sendOrder exits immediately after sending (alice BUY 100 @ 10.50)",
            run_order(s, "alice", ["alice", ENDPOINT, "BUY", "100", "10.50"]) == 0)
    s.check("unmatched BUY rests in the order book", s.wait_for(exchange, r"BOOK.*alice@10\.5"))
    sleep(0.3)
    s.check("no trade yet", len(trades) == 0)

    run_order(s, "bob", ["bob", ENDPOINT, "SELL", "100", "11.00"])
    sleep(0.5)
    s.check("SELL above best BUY does not trade", len(trades) == 0)

    run_order(s, "carol", ["carol", ENDPOINT, "SELL", "100", "10.00"])
    sleep(0.8)
    s.check("SELL below BUY price produces one trade", len(trades) == 1)
    s.check("trade price is the resting (buyer) price 10.5, buyer=alice, seller=carol",
            len(trades) >= 1 and trades[0]["price"] == 10.5 and trades[0]["buyer"] == "alice"
            and trades[0]["seller"] == "carol" and trades[0]["quantity"] == 100)

    run_order(s, "dave", ["dave", ENDPOINT, "BUY", "100", "11.50"])
    sleep(0.8)
    s.check("BUY above resting SELL (bob @ 11) trades at 11",
            len(trades) == 2 and trades[1]["price"] == 11 and trades[1]["seller"] == "bob")

    bad = s.start("bad-qty", "task2-trading/send_order.py", ["eve", ENDPOINT, "BUY", "50", "10"])
    s.check("quantity other than 100 is rejected", s.wait_exit(bad) == 1)

    # multi-stock extension
    run_order(s, "f1", ["frank", ENDPOINT, "BUY", "100", "5.00", "ABC"])
    run_order(s, "g1", ["gina", ENDPOINT, "SELL", "100", "5.00", "ABC"])
    sleep(0.8)
    s.check("multi-stock: ABC order pair trades independently of XYZ",
            len(trades) == 3 and trades[2]["symbol"] == "ABC")

    stop.set()
    listener.join(3)
    s.finish("trading-test.txt")


if __name__ == "__main__":
    main()
