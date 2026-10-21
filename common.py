"""
PBT205 Task 3 - code shared by the tracker, person, query and GUI apps.

Topics (RabbitMQ exchanges):
  - "position"       fanout  Every person publishes their moves here. The
                             tracker and the GUI each get a copy.
  - "query"          fanout  A person identifier to look up. Read by the tracker.
  - "query-response" direct  The tracker's answer. The routing key is the
                             request id, so only the app that asked receives it.

All messages are JSON.
"""

import argparse
import sys

import pika

POSITION_EXCHANGE = "position"
QUERY_EXCHANGE = "query"
QUERY_RESPONSE_EXCHANGE = "query-response"

DEFAULT_BOARD_SIZE = 10
MAX_BOARD_SIZE = 1000


def board_size(text):
    """argparse type for the board size: a whole number from 1 to 1000."""
    try:
        size = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"board size must be a number, got '{text}'")
    if not 1 <= size <= MAX_BOARD_SIZE:
        raise argparse.ArgumentTypeError(
            f"board size must be between 1 and {MAX_BOARD_SIZE}, got {size}")
    return size


def add_endpoint_args(parser):
    """Add the middleware endpoint arguments every app takes."""
    parser.add_argument("port", type=int, help="RabbitMQ TCP port (normally 5672)")
    parser.add_argument("--host", default="localhost",
                        help="RabbitMQ host (default: localhost)")


def connect(host, port):
    """Connect to RabbitMQ, exiting with a clear error if it fails."""
    try:
        return pika.BlockingConnection(
            pika.ConnectionParameters(host=host, port=port)
        )
    except pika.exceptions.AMQPConnectionError:
        print(f"Error: could not connect to RabbitMQ on {host}:{port}.")
        print("Is RabbitMQ running? Start it with:")
        print("  docker run -it --rm --name rabbitmq -p 5672:5672 "
              "-p 15672:15672 rabbitmq:3-management")
        sys.exit(1)


def declare_exchanges(channel):
    """Create the three topics (does nothing if they already exist)."""
    channel.exchange_declare(exchange=POSITION_EXCHANGE, exchange_type="fanout")
    channel.exchange_declare(exchange=QUERY_EXCHANGE, exchange_type="fanout")
    channel.exchange_declare(exchange=QUERY_RESPONSE_EXCHANGE, exchange_type="direct")


def subscribe(channel, exchange, routing_key=""):
    """
    Create a private queue bound to an exchange and return its name.

    queue='' lets RabbitMQ pick a random name. exclusive=True means only this
    connection can use the queue and it is deleted when the app exits.
    """
    result = channel.queue_declare(queue="", exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange=exchange, queue=queue_name, routing_key=routing_key)
    return queue_name
