# PBT205 Assessment 1 – Group Report: Prototype 2 (Trading)

**Team:** [team name] | **Members:** [names / IDs] | **Repository:** [URL] | **Date:** [date]

> Replace every [bracketed] item with your own results. Figures must come from **your** run of the Python programs against RabbitMQ (see `docs/task2-guide.md`).

## 1. Technical requirements analysis (Criterion 1)

| Area | Requirement | Constraint / decision | Link |
|------|-------------|------------------------|------|
| Middleware | RabbitMQ, run with Docker | One container; ports 5672 (AMQP) and 15672 (management UI) | `docker-compose.yml` |
| Language / client | Python (instructor requirement) | Python 3.8+ with the `pika` AMQP client; no other dependencies (the GUI uses only the standard library) | `requirements.txt`, `common/broker.py` |
| Topics | `orders` and `trades` | Routing keys on one topic exchange `pbt205`. `orders`: send_order → exchange. `trades`: exchange → any subscriber (the GUI) | `docs/message-formats.md` §2–3 |
| Protocol | `sendOrder`: username, endpoint, SIDE, QUANTITY (fixed 100), price; `exchange`: endpoint | `send_order.py` validates its arguments before connecting and rejects any quantity other than 100; it publishes one order and exits | `send_order.py`, `exchange.py` |
| Serialisation | – | JSON; price is a JSON number (floating point); `orderId` is unique per order; timestamps are ISO-8601 UTC | `docs/message-formats.md` |
| Integration | Exactly one exchange; many traders | The exchange is the only consumer of `orders`. Two exchanges would each match the same orders, so a single instance is a documented operating constraint | `exchange.py` |
| Matching / boundary | Limit orders only; a BUY matches a SELL if buy price ≥ sell price | The trade executes at the **resting** order's price; best price first, then earliest arrival; a matched order leaves the book | `order_book.py` |
| Invalid input | – | The exchange rejects orders with a bad side, price or quantity and logs them; the GUI validates the order form | `exchange.py`, `gui_server.py` |
| Thread safety | The GUI receives and publishes at the same time | pika's `BlockingConnection` is not thread-safe, so the listener thread owns its connection and each order from the browser uses a short-lived connection | `gui_server.py` |

**Relationship between requirements.** Because orders are limit orders only, a trade price is well defined by the book. Because the exchange is a single consumer, the order book needs no locking. Because every program uses the same helper and the same exchange declaration, a program written by another team member (for example Member A's) interoperates as long as it follows the message format.

## 2. Prototype design and creation (Criterion 2)

- **`send_order.py` (C2):** parse and validate the arguments, connect, publish one order with broker confirmation, print `Sent …`, exit.
- **`exchange.py` (C1):** subscribes to `orders`, keeps one `OrderBook` per stock, publishes each match to `trades`, and prints `ORDER` / `BOOK` / `TRADE` lines.
- **`order_book.py` (C1):** the buy list (bids, highest price first) and sell list (asks, lowest price first), each tie-broken by arrival sequence. Sorted lists were chosen for simplicity and clarity at assignment scale; a heap is the upgrade path.
- **`gui_server.py` + `gui/index.html` (C3):** a web page, served by a small Python HTTP server, that shows **"Last price: X"** for each stock, the recent trades and orders, and a form to place an order (quantity fixed at 100). A background thread subscribes to `trades` and `orders`; each open browser receives updates through a Server-Sent Events stream (MDN Web Docs, n.d.).
- **Multiple stocks (extension):** orders carry a `symbol` (default `XYZ`); the exchange creates an independent book for each new symbol and the GUI shows one tile per symbol.
- **Shared helper (`common/broker.py`):** `connect`, `publish`, `subscribe`; reused by every program.

Run: `python task2-trading/exchange.py 5672`, `python task2-trading/gui_server.py 5672` → http://localhost:3002.

## 3. Technical solution, testing and justification (Criterion 3)

Test environment: [RabbitMQ version, Python version, date]. Integration transcripts are in `docs/test-evidence/`.

| Test | Expected | Result |
|------|----------|--------|
| Unit: `python scripts/test_unit.py` (14 tests: matching rules, helpers, argument validation) | Cross → trade at resting price; non-cross rests; best price then earliest wins; no double trade; one book per stock | [Pass/Fail, e.g. 14/14] |
| C1 manual: alice BUY 10.50, then bob SELL 11.00 | Both rest in the book, no trade | [ ] – Figure 1 |
| C1 manual: carol SELL 10.00 | `TRADE #1 XYZ 100 @ 10.5 (buyer alice, seller carol)` | [ ] – Figure 2 |
| C2: `send_order.py` with quantity 50 | Rejected: "QUANTITY is fixed at 100"; valid orders print `Sent …` and the program exits | [ ] – Figure 3 |
| C3: GUI shows "Last price: X" | Price updates after each trade; a second stock gets its own tile | [ ] – Figures 4 and 5 |
| C4: several traders (alice, bob, carol, dave, erin, frank, gina) | dave BUY 11.50 trades with bob at 11; erin SELL 12 rests; ABC pair trades at 5 independently of XYZ | [ ] – Figure 6 |
| C4: `python scripts/test_trading.py` | 10 of 10 checks | [ ] – Figure 9 |
| GUI API: `python scripts/test_gui.py` | 8 of 8 checks (page, event stream, last price per stock, validation) | [ ] |
| RabbitMQ side: exchange `pbt205` (topic) and one private queue per subscriber | Visible in the management UI | [ ] – Figures 7 and 8 |
| Integration with Member A's application | Their orders are matched and their app displays the latest price | [Pass/Fail and screenshots] |

[Insert your screenshots here, each with a caption, in this order:]

**Figure 1** – order book after alice BUY 10.50 and bob SELL 11.00 (no trade): `![Figure 1](../screenshots/C1-exchange-order-book.png)`
**Figure 2** – first trade `TRADE #1 XYZ 100 @ 10.5`: `![Figure 2](../screenshots/C1-exchange-trade.png)`
**Figure 3** – send_order rejects quantity 50: `![Figure 3](../screenshots/C2-sendorder.png)`
**Figure 4** – GUI showing "Last price: 10.50" next to the exchange terminal: `![Figure 4](../screenshots/C3-gui-last-price.png)`
**Figure 5** – GUI with two stocks (XYZ and ABC): `![Figure 5](../screenshots/C3-gui-multi-stock.png)`
**Figure 6** – several traders in the exchange terminal: `![Figure 6](../screenshots/C4-several-traders.png)`
**Figure 7** – RabbitMQ UI, exchange `pbt205`: `![Figure 7](../screenshots/C4-rabbitmq-exchange.png)`
**Figure 8** – RabbitMQ UI, queues: `![Figure 8](../screenshots/C4-rabbitmq-queues.png)`
**Figure 9** – integration test output: `![Figure 9](../screenshots/C4-test-output.png)`

**How evidence shaped the solution.** [Your own words, for example what the integration test with Member A's application showed about message-format agreement and what you changed; or what the thread-safety problem with a shared pika connection taught you about the GUI design.]

**Justification.** Trading at the resting order's price is the standard price-time-priority rule and gives deterministic prices. Separating the matching logic (`order_book.py`) from the messaging (`exchange.py`) allowed fast unit tests with no broker. Python with pika keeps the whole system to one language and one dependency, and the web GUI needs only the standard library, which keeps setup short for every team member.

**Limitations.** Quantity is fixed so there are no partial fills; the book and the GUI's history are in memory and are lost on restart; exactly one exchange instance may run; messages sent while a subscriber is offline are not replayed.

## 4. Conventions (Criterion 4)

Shared Git repository, README usage, message contract in `docs/message-formats.md`, docstrings and comments explaining design decisions, consistent naming (PEP 8 style), and APA 7th references.

## References

MDN Web Docs. (n.d.). *Using server-sent events*. Mozilla. https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events

Pika. (n.d.). *Pika documentation*. https://pika.readthedocs.io/en/stable/

RabbitMQ. (n.d.). *RabbitMQ documentation*. https://www.rabbitmq.com/docs
