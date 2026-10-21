#!/usr/bin/env python
"""
PBT205 Task 3 - contact tracing "tracker" app.

Usage:
    python tracker.py <port> [--host HOST] [--size N]

Example:
    python tracker.py 5672 --size 10

Behaviour:
  - Subscribes to the "position" topic and keeps a view of where everyone is.
    When a person moves onto a square that someone else is already on, the
    contact is logged for both of them.
  - Subscribes to the "query" topic. When a person identifier arrives, it
    prints everyone that person has met (most recent first) and publishes the
    same list to the "query-response" topic.
"""

import argparse
import json
import time
from datetime import datetime

import pika

from common import (POSITION_EXCHANGE, QUERY_EXCHANGE, QUERY_RESPONSE_EXCHANGE,
                    DEFAULT_BOARD_SIZE, add_endpoint_args, board_size, connect,
                    declare_exchanges, subscribe)


class ContactTracker:
    """
    The tracker's data, kept separate from RabbitMQ so it can be unit tested.

    positions: person -> (x, y)            where everyone is now
    squares:   (x, y) -> set of people     who is on each occupied square
    contacts:  person -> list of contacts  oldest first; each contact is a dict
                                           {"name", "x", "y", "timestamp"}

    The squares dict means checking for a contact only looks at one square,
    so a move costs the same on a 10 x 10 board as on a 1,000 x 1,000 board.
    """

    def __init__(self, size=DEFAULT_BOARD_SIZE):
        self.size = size
        self.positions = {}
        self.squares = {}
        self.contacts = {}

    def on_board(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size

    def move(self, person, x, y, timestamp=None):
        """
        Record that a person is now at (x, y).

        Returns the names of the people they came into contact with.
        Raises ValueError if (x, y) is off the board.
        """
        if not self.on_board(x, y):
            raise ValueError(f"({x}, {y}) is off the {self.size} x {self.size} board")
        if timestamp is None:
            timestamp = time.time()

        new_square = (x, y)
        if self.positions.get(person) == new_square:
            # Already there, so nobody new has been met.
            return []

        self._leave_square(person)
        self.positions[person] = new_square

        people_here = self.squares.setdefault(new_square, set())
        met = sorted(people_here)
        for other in met:
            # A contact goes both ways.
            self._log(person, other, x, y, timestamp)
            self._log(other, person, x, y, timestamp)
        people_here.add(person)
        return met

    def leave(self, person):
        """Remove a person from the board (their contact history is kept)."""
        self._leave_square(person)
        self.positions.pop(person, None)

    def query(self, person):
        """
        Everyone this person has met, most recent contact first.

        Each name appears once, with the time and square of the latest contact
        and how many times they have met in total.
        """
        latest = {}
        for contact in self.contacts.get(person, []):
            name = contact["name"]
            count = latest[name]["count"] + 1 if name in latest else 1
            latest[name] = dict(contact, count=count)
        # Contacts are stored oldest first, so sort newest first.
        return sorted(latest.values(), key=lambda c: c["timestamp"], reverse=True)

    def _leave_square(self, person):
        old_square = self.positions.get(person)
        if old_square is None:
            return
        people_there = self.squares[old_square]
        people_there.discard(person)
        if not people_there:
            del self.squares[old_square]

    def _log(self, person, other, x, y, timestamp):
        self.contacts.setdefault(person, []).append(
            {"name": other, "x": x, "y": y, "timestamp": timestamp})


def format_contacts(person, contacts, known=True):
    """Turn a query result into lines of text for the console."""
    if not known:
        return [f"No one called '{person}' has been seen by the tracker."]
    if not contacts:
        return [f"{person} has not come into contact with anyone."]
    lines = [f"{person} has come into contact with (most recent first):"]
    for c in contacts:
        when = datetime.fromtimestamp(c["timestamp"]).strftime("%H:%M:%S")
        times = "1 time" if c["count"] == 1 else f"{c['count']} times"
        lines.append(f"  {c['name']:<12} last at ({c['x']}, {c['y']}) "
                     f"at {when}, {times}")
    return lines


def main():
    parser = argparse.ArgumentParser(description="Contact tracing tracker")
    add_endpoint_args(parser)
    parser.add_argument("--size", type=board_size, default=DEFAULT_BOARD_SIZE,
                        help=f"board width and height (default {DEFAULT_BOARD_SIZE})")
    args = parser.parse_args()

    tracker = ContactTracker(args.size)

    connection = connect(args.host, args.port)
    channel = connection.channel()
    declare_exchanges(channel)
    position_queue = subscribe(channel, POSITION_EXCHANGE)
    query_queue = subscribe(channel, QUERY_EXCHANGE)

    def on_position(ch, method, properties, body):
        try:
            data = json.loads(body)
            person = data["person"]
            if data.get("type") == "leave":
                tracker.leave(person)
                print(f"{person} left the board")
                return
            met = tracker.move(person, int(data["x"]), int(data["y"]))
        except (ValueError, KeyError, TypeError) as error:
            # Bad JSON, a missing field or an off-board move: ignore it.
            print(f"Ignored position message {body!r}: {error}")
            return
        if met:
            x, y = tracker.positions[person]
            print(f"CONTACT at ({x}, {y}): {person} met {', '.join(met)}")

    def on_query(ch, method, properties, body):
        try:
            data = json.loads(body)
            person = data["person"]
            request_id = data["request_id"]
        except (ValueError, KeyError, TypeError) as error:
            print(f"Ignored query message {body!r}: {error}")
            return

        known = person in tracker.positions or person in tracker.contacts
        contacts = tracker.query(person)
        print("\n".join(format_contacts(person, contacts, known)))

        response = json.dumps({
            "request_id": request_id,
            "person": person,
            "known": known,
            "contacts": contacts,
        })
        channel.basic_publish(exchange=QUERY_RESPONSE_EXCHANGE,
                              routing_key=request_id, body=response)

    channel.basic_consume(queue=position_queue, on_message_callback=on_position,
                          auto_ack=True)
    channel.basic_consume(queue=query_queue, on_message_callback=on_query,
                          auto_ack=True)

    print(f"Tracker running on a {args.size} x {args.size} board. "
          "Press Ctrl+C to quit.")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\nStopping tracker...")
    except pika.exceptions.AMQPError:
        print("\nLost connection to RabbitMQ.")
    if connection.is_open:
        connection.close()


if __name__ == "__main__":
    main()
