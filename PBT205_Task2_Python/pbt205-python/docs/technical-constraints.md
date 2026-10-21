# Technical Constraints (E4)

Covers SLO c) (evaluate middleware) and SLO d) (hardware/software constraints of the middleware solution and their impact on development).

## 1. Hardware requirements

| Item | Minimum used for this project | Notes |
|------|-------------------------------|-------|
| CPU | 2 cores | RabbitMQ broker + several Python processes run on one machine. |
| RAM | 4 GB free (8 GB recommended) | The `rabbitmq:3-management` container plus Docker overhead. RabbitMQ blocks publishers when memory use passes its high watermark (default 40% of system RAM), so a very small machine will stall producers rather than crash. |
| Disk | ~1 GB | Docker image, Python packages, test evidence. Broker alarms if free disk drops below its limit (default 50 MB). |
| Network | Loopback only | All apps connect to `localhost`; for several lab machines, one host runs RabbitMQ and others connect by `host:5672`. |

## 2. Software requirements

| Software | Version / detail | Purpose |
|----------|------------------|---------|
| Docker (or Podman) | Docker Engine / Docker Desktop, able to run Linux containers | Runs RabbitMQ per the brief. |
| RabbitMQ | image `rabbitmq:3-management` | Prescribed middleware, with management UI. |
| Python | 3.8+ (developed and tested on 3.13) | Runs all the programs. On Windows the launcher is `py` or `python`. |
| pika | >=1.3 (`pip install -r requirements.txt`) | AMQP 0-9-1 client for Python. |
| Git | any recent | Shared repository. |
| OS | Windows 10/11 (WSL2 backend), macOS, Linux | Docker Desktop on Windows/macOS needs virtualisation enabled in BIOS/firmware. |

## 3. Docker and ports

Launch (from the brief), or use `docker compose up -d`:

```
docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

| Port | Protocol | Used by |
|------|----------|---------|
| 5672 | AMQP 0-9-1 | **All prototype apps** – the "middleware endpoint (TCP port)" start-up argument. |
| 3002 | HTTP | Trading GUI server (`GUI_PORT` or the 2nd CLI argument changes it). |
| 15672 | HTTP | Management UI / API – http://localhost:15672 (user `guest`, password `guest`) to inspect the `pbt205` exchange, queues and message rates. |

Constraints that follow from this setup:
- **Port clashes:** if another service (or another RabbitMQ) holds 5672 or 15672 the container fails to start. Remap with `-p 5673:5672` and pass `5673` as the endpoint argument.
- **`guest` account is localhost-only** in RabbitMQ by default. Apps on another machine need a dedicated user created in the broker.
- **`--rm` container is disposable:** stopping it discards all broker state. This is fine for the prototype because exchanges and queues are declared non-durable and recreated by the apps on connect.
- **Firewalls:** multi-machine demos need inbound TCP 5672 allowed on the broker host.

## 4. Middleware design constraints and their impact

| Constraint | Impact on the prototypes | Mitigation in this project |
|-----------|--------------------------|----------------------------|
| Pub/sub needs a queue per subscriber | A subscriber that is not connected when a message is published never sees it, e.g. an order sent before the exchange is running is lost. | Start order documented (exchange first, then the GUI, then traders). Each subscriber binds its own private queue **before** it starts consuming. |
| Non-durable exchange and queues | Messages and the order book are lost if the broker or the exchange restarts. | Acceptable for a prototype; durable queues + persistent messages would be the production change. |
| Ordering is guaranteed only per publisher | Orders from different traders can interleave; the exchange matches them in the order it receives them. | The exchange is the single consumer of `orders`, so there is one well-defined arrival order; every message carries `ts` and `orderId`. |
| One exchange (`pbt205`), many routing keys | New topics need no broker set-up, so the same helper is reused across tasks. | `common/broker.py` is shared by every program. |
| JSON serialisation | Human-readable but larger than binary formats; no schema enforcement. | Fields validated on receipt (the exchange); malformed messages are dropped and logged. See `message-formats.md`. |
| pika's `BlockingConnection` is not thread-safe | The GUI needs to receive trades while also publishing orders from web requests. | The GUI server gives its listener thread its own connection and uses a short-lived connection for each order it publishes. |

## 5. Scalability

- **Single exchange:** the brief requires exactly one exchange. It keeps the order books in memory, so it is a single point of failure and a throughput ceiling. Running two would make both match the same orders, so scaling out would need orders partitioned by stock (one exchange process per set of stocks) or a shared store.
- **Message rate:** each order is one small JSON message in and, when it matches, one trade out. A single RabbitMQ node handles thousands of messages per second at this size, so the Python exchange's per-order matching, not the broker, is the first limit; it should be load-tested before relying on it.
- **Order book:** sorted lists per stock (insertion is O(n)). Fine at assignment scale; a heap or tree is the upgrade path. Adding stocks needs no code change: each symbol gets its own book on first use.
- **Quantity fixed at 100:** there are no partial fills, which keeps matching simple.
- **GUI clients:** the GUI server keeps one open event stream per browser (one thread each). Hundreds of browsers are fine; thousands would call for an asynchronous web framework.
- **Client count:** each program opens one connection and one channel; RabbitMQ handles thousands, but the operating system's file-descriptor limit on the broker host caps connections.

## References (APA 7th)

Pika. (n.d.). *Pika documentation*. https://pika.readthedocs.io/en/stable/

Docker Inc. (n.d.). *Docker documentation*. https://docs.docker.com/

RabbitMQ. (n.d.). *RabbitMQ documentation*. https://www.rabbitmq.com/docs
