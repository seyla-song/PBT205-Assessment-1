# PBT205 Task 1 – Chat Application

A command-line chat app. Several users can join a room and send messages to each other through **RabbitMQ**.

## Requirements

- **Python 3.8+**
- **Docker** (to run RabbitMQ)
- The Python package `pika` (listed in `requirements.txt`)

## 1. Start RabbitMQ (middleware)

Run RabbitMQ in Docker using the command from the assessment brief:

```bash
docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

Leave this terminal open. RabbitMQ is ready when the log shows `Server startup complete`.

- Port **5672** is where the chat app connects.
- Port **15672** is the web management UI: open http://localhost:15672 and log in with `guest` / `guest`.

> **Port already in use?** Another RabbitMQ may already be running. On macOS with Homebrew, stop it with
> `brew services stop rabbitmq`. Or remove an old container with `docker rm -f rabbitmq`.

## 2. Install dependencies

In a new terminal, from the project folder:

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Run the chat app

```bash
python chat.py <username> <port> [room]
```

| Argument   | Required | Description                                                   |
|------------|----------|---------------------------------------------------------------|
| `username` | yes      | The name other users see next to your messages                |
| `port`     | yes      | RabbitMQ TCP port (normally `5672`)                           |
| `room`     | no       | Room to join. If you leave it out, the app asks for one (default `general`) |

Examples:

```bash
python chat.py seyla 5672 general
python chat.py alex 5672           # asks which room to join
```

Type a message and press **Enter** to send it. Press **Ctrl+C** to leave.

## 4. Try it with several users

Open three terminals (activate the venv in each one) and run:

```bash
# Terminal A
python chat.py alice 5672 general

# Terminal B
python chat.py bob 5672 general

# Terminal C
python chat.py carol 5672 sport
```

- Messages from Alice appear for Bob, and the other way round.
- Carol is in a different room and sees none of them.

You can watch the exchange and queues live in the management UI (**Exchanges → chat_rooms** and **Queues**).

## How it works

```
 alice ──publish(routing_key="general")──►┐
                                          │  exchange "chat_rooms" (direct)
 bob   ◄── queue (bound to "general") ◄───┤
 carol ◄── queue (bound to "sport")   ◄───┘
```

- **Exchange:** all messages go to one `direct` exchange named `chat_rooms`.
- **Rooms:** the room name is the routing key, so a message only reaches queues bound to that room.
- **Queues:** each user gets their own exclusive, auto-named queue. Every user in a room therefore gets a copy of every message. The queue is deleted when the user leaves.
- **Message format (JSON):**
  ```json
  { "username": "alice", "message": "hi", "timestamp": "2026-10-20T14:05:00" }
  ```
- **Threads:** a background thread receives messages while the main thread reads what you type. Sending is passed to the connection thread with `add_callback_threadsafe`, because pika connections are not thread-safe.

## Project files

| File               | Purpose                                              |
|--------------------|------------------------------------------------------|
| `chat.py`          | Task 1 chat application                              |
| `requirements.txt` | Python dependencies                                  |
| `send.py`, `receive.py` | RabbitMQ "Hello World" tutorial scripts (not part of Task 1) |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `could not connect to RabbitMQ on localhost:5672` | RabbitMQ isn't running. Start it with the Docker command in step 1 |
| `port is already allocated` when starting Docker | Something else is using port 5672 (see the note in step 1) |
| `ModuleNotFoundError: No module named 'pika'` | Activate the venv and run `pip install -r requirements.txt` |
