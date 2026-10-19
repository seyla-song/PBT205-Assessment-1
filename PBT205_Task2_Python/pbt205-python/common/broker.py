"""Shared RabbitMQ helper (used by every Task 2 program).

All topics are routing keys on ONE topic exchange called "pbt205", so a new topic
needs no broker-side set-up: it exists as soon as someone publishes or subscribes.

    Task 2 topics:  orders  (sendOrder -> exchange)
                    trades  (exchange  -> anyone interested, e.g. the GUI)

The exchange is declared non-durable, exactly as in the team's other programs, so
every program can declare it without a "PRECONDITION_FAILED" clash.
"""
import json
import sys
from datetime import datetime, timezone

import pika
from pika.exceptions import AMQPError

EXCHANGE = "pbt205"


def endpoint_to_url(endpoint):
    """Accept '5672', 'host:5672' or a full 'amqp://...' URL."""
    ep = str(endpoint)
    if ep.startswith(("amqp://", "amqps://")):
        return ep
    if ep.isdigit():
        return f"amqp://guest:guest@localhost:{ep}"
    return f"amqp://guest:guest@{ep}"


def connect(endpoint):
    """Return (connection, channel). Exits with a friendly message if the broker is unreachable."""
    url = endpoint_to_url(endpoint)
    try:
        connection = pika.BlockingConnection(pika.URLParameters(url))
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=False)
    except (AMQPError, OSError) as err:
        shown = url.split("@")[-1]
        reason = str(err) or "connection refused (is RabbitMQ running?)"
        print(f"Cannot reach RabbitMQ at amqp://{shown}: {reason}", file=sys.stderr)
        print("Start it with: docker compose up -d   (see README)", file=sys.stderr)
        sys.exit(1)
    return connection, channel


def publish(channel, topic, message):
    """Publish a dict as JSON to a topic (routing key)."""
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=topic,
        body=json.dumps(message).encode("utf-8"),
        properties=pika.BasicProperties(content_type="application/json"),
    )


def subscribe(channel, topic, handler):
    """Subscribe to a topic with a private queue, so every subscriber sees every message.

    handler(message_dict, routing_key) is called for each message. The binding is in
    place when this returns, so it is safe to publish afterwards. Messages are only
    delivered while the connection is being serviced (channel.start_consuming() or
    connection.process_data_events()).
    """
    queue = channel.queue_declare(queue="", exclusive=True, auto_delete=True).method.queue
    channel.queue_bind(exchange=EXCHANGE, queue=queue, routing_key=topic)

    def on_message(_channel, method, _properties, body):
        try:
            data = json.loads(body.decode("utf-8"))
        except ValueError:
            print(f"Dropped malformed JSON on {method.routing_key}", file=sys.stderr)
            return
        handler(data, method.routing_key)

    return channel.basic_consume(queue=queue, on_message_callback=on_message, auto_ack=True)


def close(connection):
    try:
        if connection.is_open:
            connection.close()
    except (AMQPError, OSError):
        pass


def now_iso():
    """UTC timestamp like 2026-10-19T09:00:00.000Z (same format as the other programs)."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def fmt_price(price):
    """10.5 -> '10.5', 11.0 -> '11' (so console output is tidy and identical to the original)."""
    text = f"{float(price):.10f}".rstrip("0").rstrip(".")
    return text or "0"
