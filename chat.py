#!/usr/bin/env python
"""
PBT205 Task 1 - command-line chat app using RabbitMQ.

Usage:
    python chat.py <username> <port> [room]

Examples:
    python chat.py seyla 5672            (asks which room to join)
    python chat.py seyla 5672 general    (joins the "general" room)

How it works:
  - All messages go to one "direct" exchange called "chat_rooms".
  - The room name is used as the routing key, so a message sent to room
    "general" is only delivered to queues bound with the key "general".
  - Every user gets their own private (exclusive, auto-named) queue bound to
    their room. Because each user has their own queue, every message in a
    room is copied to every user in that room (a broadcast), and users in
    other rooms never see it.
"""

import json
import sys
import threading
from datetime import datetime

import pika

EXCHANGE_NAME = "chat_rooms"
DEFAULT_ROOM = "general"


def parse_args():
    """Read username, port and (optional) room from the command line."""
    if len(sys.argv) not in (3, 4):
        print("Usage: python chat.py <username> <port> [room]")
        print("Example: python chat.py seyla 5672 general")
        sys.exit(1)

    username = sys.argv[1]

    try:
        port = int(sys.argv[2])
    except ValueError:
        print(f"Error: port must be a number, got '{sys.argv[2]}'")
        sys.exit(1)

    # Room can be given as the 3rd argument, otherwise ask for it.
    if len(sys.argv) == 4:
        room = sys.argv[3]
    else:
        room = input(f"Room to join [{DEFAULT_ROOM}]: ").strip() or DEFAULT_ROOM

    return username, port, room


def connect(port):
    """Connect to RabbitMQ on localhost, exiting with a clear error if it fails."""
    try:
        return pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost", port=port)
        )
    except pika.exceptions.AMQPConnectionError:
        print(f"Error: could not connect to RabbitMQ on localhost:{port}.")
        print("Is RabbitMQ running? Start it with:")
        print("  docker run -it --rm --name rabbitmq -p 5672:5672 "
              "-p 15672:15672 rabbitmq:3-management")
        sys.exit(1)


def main():
    username, port, room = parse_args()

    connection = connect(port)
    channel = connection.channel()

    # Create the exchange (does nothing if it already exists).
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="direct")

    # queue='' lets RabbitMQ pick a random name for us. exclusive=True means
    # only this connection can use the queue and it is deleted when we leave.
    result = channel.queue_declare(queue="", exclusive=True)
    queue_name = result.method.queue

    # Only receive messages whose routing key matches our room.
    channel.queue_bind(exchange=EXCHANGE_NAME, queue=queue_name, routing_key=room)

    def on_message(ch, method, properties, body):
        """Called (in the consumer thread) for every message in our room."""
        data = json.loads(body)

        # We receive our own messages too, because we are subscribed to the
        # room. Skip them, since the user already sees what they typed.
        if data["username"] == username:
            return

        time = datetime.fromisoformat(data["timestamp"]).strftime("%H:%M")
        # \r moves to the start of the line so the message doesn't appear
        # after the "> " prompt; then the prompt is printed again.
        print(f"\r[{time}] {data['username']}: {data['message']}")
        print("> ", end="", flush=True)

    channel.basic_consume(queue=queue_name, on_message_callback=on_message,
                          auto_ack=True)

    def consume():
        """Runs in a background thread so input() doesn't block receiving."""
        try:
            channel.start_consuming()
        except pika.exceptions.AMQPError:
            print("\nLost connection to RabbitMQ. Press Enter to exit.")

    consumer_thread = threading.Thread(target=consume, daemon=True)
    consumer_thread.start()

    def publish(text):
        """Send a message to everyone in the room as JSON."""
        body = json.dumps({
            "username": username,
            "message": text,
            "timestamp": datetime.now().isoformat(),
        })
        channel.basic_publish(exchange=EXCHANGE_NAME, routing_key=room, body=body)

    print(f"Joined room '{room}' as {username}. Type a message and press Enter.")
    print("Press Ctrl+C to quit.")

    try:
        while consumer_thread.is_alive():
            text = input("> ").strip()
            if not text or not consumer_thread.is_alive():
                continue
            # pika connections are not thread-safe: only the consumer thread
            # may use the channel. add_callback_threadsafe() is the one method
            # that is safe to call from another thread. It asks the consumer
            # thread to run publish() for us.
            connection.add_callback_threadsafe(lambda t=text: publish(t))
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C (or Ctrl+D) pressed.
        pass

    # Clean shutdown: ask the consumer thread to stop, wait for it, then close.
    print("\nLeaving chat...")
    if connection.is_open:
        connection.add_callback_threadsafe(channel.stop_consuming)
        consumer_thread.join(timeout=5)
        connection.close()


if __name__ == "__main__":
    main()
