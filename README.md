# PBT205 Task 3 – Contact Tracing

Command-line apps that model people moving around a board. A tracker records who has been on the same square at the same time. Everything talks through **RabbitMQ**.

| App          | What it does                                                                |
|--------------|-----------------------------------------------------------------------------|
| `tracker.py` | Keeps track of where everyone is and logs contacts. Answers queries         |
| `person.py`  | One person. Starts on a random square and keeps moving one square at a time |
| `query.py`   | Asks the tracker who a person has met, prints the answer and exits          |

## Requirements

- **Python 3.8+**
- **Docker** (to run RabbitMQ)
- The Python package `pika` (listed in `requirements.txt`)

## 1. Start RabbitMQ (middleware)

Use the same command as in Task 1 (an instance that is already running can be reused):

```bash
docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

- Port **5672** is where the apps connect.
- Port **15672** is the web management UI: open http://localhost:15672 and log in with `guest` / `guest`.

## 2. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Run the apps

Every app takes the middleware endpoint as its first argument (the RabbitMQ port), plus an optional `--host` (default `localhost`).

### Tracker

```bash
python tracker.py <port> [--size N]
```

| Argument | Required | Description                                      |
|----------|----------|--------------------------------------------------|
| `port`   | yes      | RabbitMQ TCP port (normally `5672`)              |
| `--size` | no       | Board width and height, 1–1000 (default `10`)    |

### Person

```bash
python person.py <port> <name> [speed] [--size N]
```

| Argument | Required | Description                                                                              |
|----------|----------|------------------------------------------------------------------------------------------|
| `port`   | yes      | RabbitMQ TCP port                                                                        |
| `name`   | yes      | Unique person identifier (e.g. a first name)                                             |
| `speed`  | no       | Moves per second: a number (`0.2`, `3`) or `slow` (0.5), `normal` (1, default), `fast` (2) |
| `--size` | no       | Board width and height. **Use the same size as the tracker**                             |

A speed of `0.2` means one move every 5 seconds, so "move once every *n* seconds" is a speed of `1/n`.

### Query

```bash
python query.py <port> <name> [--timeout SECONDS]
```

The app waits up to `--timeout` seconds (default 5) for the tracker's answer. If no answer arrives, it exits with an error.

## 4. Try it

Open a terminal for each command (activate the venv in each one). A small board makes contacts happen quickly:

```bash
# Terminal A
python tracker.py 5672 --size 5

# Terminals B, C, D
python person.py 5672 alice fast --size 5
python person.py 5672 bob normal --size 5
python person.py 5672 carol 0.5 --size 5

# Terminal E (any time)
python query.py 5672 alice
```

Sample output:

```
# tracker
Tracker running on a 5 x 5 board. Press Ctrl+C to quit.
CONTACT at (1, 1): bob met carol
CONTACT at (1, 2): alice met bob

# query
bob has come into contact with (most recent first):
  alice        last at (2, 1) at 20:14:56, 2 times
  carol        last at (1, 0) at 20:14:54, 3 times
```

Press **Ctrl+C** to stop a person. It tells the tracker it has left, so it no longer appears on the board (its contact history is kept).

## How it works

```
 person alice ─┐                         ┌─► tracker ─ logs contacts
 person bob   ─┼─► "position" (fanout) ──┘      ▲   │
 person carol ─┘                                │   │ answer, routing key = request id
                                                │   ▼
 query.py ──────► "query" (fanout) ─────────────┘  "query-response" (direct) ──► query.py
```

### Topics (exchanges)

| Exchange         | Type   | Published by | Read by  | Why this type |
|------------------|--------|--------------|----------|---------------|
| `position`       | fanout | person       | tracker  | Every subscriber gets every move. Other apps (e.g. a monitor) can be added later without any changes |
| `query`          | fanout | query        | tracker  | Same pattern as `position` |
| `query-response` | direct | tracker      | query    | The routing key is the request id, so each query app only gets its own answer, even with several running at once |

Each subscriber uses its own exclusive, auto-named queue, the same way as in Task 1.

### Messages (JSON)

```jsonc
// position: a move
{ "type": "move", "person": "alice", "x": 3, "y": 4, "timestamp": 1792573000.1 }
// position: a person stopped
{ "type": "leave", "person": "alice", "timestamp": 1792573010.0 }
// query
{ "person": "alice", "request_id": "6f1c…" }
// query-response
{ "request_id": "6f1c…", "person": "alice", "known": true,
  "contacts": [ { "name": "bob", "x": 3, "y": 4, "timestamp": 1792573005.2, "count": 2 } ] }
```

### Contact detection (`ContactTracker` in `tracker.py`)

- `positions`: person → `(x, y)`. This is the tracker's view of the board.
- `squares`: `(x, y)` → set of people on that square. A move only needs to check one square, so it costs the same on a 10 × 10 board as on a 1,000 × 1,000 board. Only occupied squares are stored, so a large board doesn't use extra memory.
- `contacts`: person → list of contacts (oldest first). A contact is logged for **both** people when one of them moves onto a square the other is on.
- A query lists each person met once, newest first, with the square and time of the latest contact and how many times they met.

### Boundaries and validation

- Coordinates go from `0` to `size - 1`. A person only picks from the king moves that stay on the board, so at a corner it has 3 choices and on an edge 5.
- The tracker ignores (and prints) any position message that is off the board or badly formed, so one faulty publisher can't crash it.
- A board size outside 1–1000 and an invalid speed are rejected at start-up.

### Limitations

- Names must be unique. If two people use the same name, the tracker treats them as one person who keeps jumping between squares.
- Contacts are kept in memory. Restarting the tracker clears them, and moves published while the tracker is down are not recorded.
- Use the same `--size` for the tracker and every person. The tracker ignores moves outside its own board.

## Tests

Unit tests for the contact logic and boundary handling (no RabbitMQ needed):

```bash
python -m unittest -v
```

The tests cover contacts in both directions, three people on one square, reverse-chronological order, repeated contacts, leaving, off-board moves, a 1,000 × 1,000 board, and king moves from every corner.

## Project files

| File               | Purpose                                                |
|--------------------|--------------------------------------------------------|
| `common.py`        | Exchange names, connection and subscribe helpers       |
| `tracker.py`       | Tracker app and the `ContactTracker` class             |
| `person.py`        | Person app                                             |
| `query.py`         | Query app                                              |
| `test_tracker.py`  | Unit tests                                             |
| `requirements.txt` | Python dependencies                                    |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `could not connect to RabbitMQ on localhost:5672` | RabbitMQ isn't running. Start it with the Docker command in step 1 |
| `no answer from the tracker within 5 s` | Start `tracker.py` first |
| Query says nobody has been seen | The tracker was started after that person stopped, or the name is spelled differently |
| `ModuleNotFoundError: No module named 'pika'` | Activate the venv and run `pip install -r requirements.txt` |
