#!/usr/bin/env python
"""
PBT205 Task 3 - contact tracing "person" app.

Usage:
    python person.py <port> <name> [speed] [--host HOST] [--size N]

    speed is moves per second, as a number (e.g. 0.5, 2) or one of
    slow (1 move every 2 s), normal (1 move per second), fast (2 per second).

Examples:
    python person.py 5672 alice
    python person.py 5672 bob fast --size 20

Behaviour:
  - Starts on a random square and publishes it to the "position" topic.
  - Then keeps moving one square in a random direction (like a king in chess)
    and publishes each new square. Moves that would leave the board are never
    chosen, so the person always stays on the board.
  - On Ctrl+C it publishes a "leave" message so the tracker removes it.
"""

import argparse
import json
import random
import time

import pika

from common import (POSITION_EXCHANGE, DEFAULT_BOARD_SIZE, add_endpoint_args,
                    board_size, connect, declare_exchanges)

SPEEDS = {"slow": 0.5, "normal": 1.0, "fast": 2.0}

# The 8 directions a king can move in.
DIRECTIONS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
              if (dx, dy) != (0, 0)]


def speed(text):
    """argparse type for the speed: a preset name or moves per second."""
    if text.lower() in SPEEDS:
        return SPEEDS[text.lower()]
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"speed must be slow, normal, fast or a number, got '{text}'")
    if value <= 0:
        raise argparse.ArgumentTypeError("speed must be greater than 0")
    return value


def next_square(x, y, size):
    """Pick a random neighbouring square that is still on the board."""
    moves = [(x + dx, y + dy) for dx, dy in DIRECTIONS
             if 0 <= x + dx < size and 0 <= y + dy < size]
    if not moves:
        # Only possible on a 1 x 1 board: there is nowhere to go.
        return x, y
    return random.choice(moves)


def main():
    parser = argparse.ArgumentParser(description="Contact tracing person")
    add_endpoint_args(parser)
    parser.add_argument("name", help="unique person identifier, e.g. a first name")
    parser.add_argument("speed", type=speed, nargs="?", default=SPEEDS["normal"],
                        help="moves per second, or slow/normal/fast (default normal)")
    parser.add_argument("--size", type=board_size, default=DEFAULT_BOARD_SIZE,
                        help=f"board width and height (default {DEFAULT_BOARD_SIZE})")
    args = parser.parse_args()

    connection = connect(args.host, args.port)
    channel = connection.channel()
    declare_exchanges(channel)

    def publish(message_type, x=None, y=None):
        body = {"type": message_type, "person": args.name, "timestamp": time.time()}
        if x is not None:
            body.update(x=x, y=y)
        channel.basic_publish(exchange=POSITION_EXCHANGE, routing_key="",
                              body=json.dumps(body))

    x = random.randrange(args.size)
    y = random.randrange(args.size)
    interval = 1 / args.speed

    print(f"{args.name} starts at ({x}, {y}) on a {args.size} x {args.size} board, "
          f"moving every {interval:g} s. Press Ctrl+C to quit.")
    try:
        publish("move", x, y)
        while True:
            # connection.sleep() keeps the connection alive while waiting,
            # unlike time.sleep().
            connection.sleep(interval)
            x, y = next_square(x, y, args.size)
            publish("move", x, y)
            print(f"{args.name} moved to ({x}, {y})")
    except KeyboardInterrupt:
        print(f"\n{args.name} is leaving...")
        if connection.is_open:
            publish("leave")
    except pika.exceptions.AMQPError:
        print("\nLost connection to RabbitMQ.")
    if connection.is_open:
        connection.close()


if __name__ == "__main__":
    main()
