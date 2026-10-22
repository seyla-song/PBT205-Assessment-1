# PBT205 Assessment 1 – Task 2: Trading System (Python + RabbitMQ)

A simple market with one exchange and many traders. Traders send BUY/SELL orders for a stock (XYZ by default); the exchange matches them and publishes the trades; a GUI shows the last price. The programs communicate only through RabbitMQ (Python client: [pika](https://pika.readthedocs.io/)).

| ID | Task | Where |
|----|------|-------|
| C1 | exchange: subscribe `orders`, keep buy and sell lists, match on acceptable price, publish `trades` | `task2-trading/exchange.py`, `task2-trading/order_book.py` |
| C2 | sendOrder: username, port, BUY/SELL, quantity fixed at 100, price; publish and exit | `task2-trading/send_order.py` |
| C3 | GUI showing "Last price: X" from `trades` | `task2-trading/gui_server.py`, `task2-trading/gui/index.html` |
| C4 | Integration test with several traders, screenshots | `scripts/test_trading.py`, `docs/screenshots/`, `docs/test-evidence/` |

## Layout
```
common/broker.py        Shared RabbitMQ helper (connect / publish / subscribe)
task2-trading/          exchange.py, order_book.py, send_order.py, gui_server.py, gui/index.html
scripts/                test_unit.py (no broker needed), test_trading.py, test_gui.py, harness.py
docs/                   message-formats.md, technical-constraints.md, task2-guide.md,
                        reports/ (Task 2 report, contribution statement template),
                        screenshots/ (evidence), test-evidence/ (test transcripts)
docker-compose.yml      RabbitMQ 3-management
requirements.txt        pika
```

## Run it
Needs Python 3.8 or newer and Docker. On Windows you can use `py` instead of `python`.

```bash
pip install -r requirements.txt
docker compose up -d        # RabbitMQ; UI http://localhost:15672 (guest/guest)
                            # or: docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management

python task2-trading/exchange.py 5672                          # terminal 1 (only one exchange at a time)
python task2-trading/gui_server.py 5672                        # terminal 2 -> open http://localhost:3002
python task2-trading/send_order.py alice 5672 BUY 100 10.50    # terminal 3
python task2-trading/send_order.py carol 5672 SELL 100 10.00   # -> TRADE #1 XYZ 100 @ 10.5
```
`send_order.py <username> <port> <BUY|SELL> <quantity=100> <price> [stock]`. The trade price is the price of the order that was already waiting. A BUY matches a SELL when the buy price is at least the sell price. Step-by-step instructions with expected output: [docs/task2-guide.md](docs/task2-guide.md).

## Tests
```bash
python scripts/test_unit.py      # 14 unit tests, no broker needed
python scripts/test_trading.py   # integration: real exchange + several real send_order processes (needs RabbitMQ)
python scripts/test_gui.py       # GUI server API and event stream (needs RabbitMQ; stop other GUI first, port 3002)
```
The integration tests write transcripts to `docs/test-evidence/`.

## Docs
- [Task 2 run guide](docs/task2-guide.md)
- [Message formats](docs/message-formats.md)
- [Technical constraints](docs/technical-constraints.md)
- [Task 2 group report](docs/reports/report-task2-trading.md)
