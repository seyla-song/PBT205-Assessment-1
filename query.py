#!/usr/bin/env python
"""
PBT205 Task 3 - contact tracing "query" app.

Usage:
    python query.py <port> <name> [--host HOST] [--timeout SECONDS]

Example:
    python query.py 5672 alice

Behaviour:
  - Publishes the person identifier to the "query" topic.
  - Waits for the tracker's answer on the "query-response" topic, prints it
    and exits.

Each query has a random request id. The app only listens on "query-response"
for that id, so several query apps can run at once without seeing each
other's answers.
"""

import argparse
import json
import sys
import uuid

from common import (QUERY_EXCHANGE, QUERY_RESPONSE_EXCHANGE, add_endpoint_args,
                    connect, declare_exchanges, subscribe)
from tracker import format_contacts


def main():
    parser = argparse.ArgumentParser(description="Contact tracing query")
    add_endpoint_args(parser)
    parser.add_argument("name", help="person identifier to look up")
    parser.add_argument("--timeout", type=float, default=5,
                        help="seconds to wait for the tracker (default 5)")
    args = parser.parse_args()

    connection = connect(args.host, args.port)
    channel = connection.channel()
    declare_exchanges(channel)

    # Subscribe before publishing, so the answer can't arrive before we listen.
    request_id = str(uuid.uuid4())
    response_queue = subscribe(channel, QUERY_RESPONSE_EXCHANGE, routing_key=request_id)

    channel.basic_publish(exchange=QUERY_EXCHANGE, routing_key="",
                          body=json.dumps({"person": args.name,
                                           "request_id": request_id}))

    # consume() with inactivity_timeout yields (None, None, None) if nothing
    # arrives in time.
    response = None
    for method, properties, body in channel.consume(
            response_queue, auto_ack=True, inactivity_timeout=args.timeout):
        if body is not None:
            response = json.loads(body)
        break
    channel.cancel()
    connection.close()

    if response is None:
        print(f"Error: no answer from the tracker within {args.timeout:g} s. "
              "Is tracker.py running?")
        sys.exit(1)

    print("\n".join(format_contacts(response["person"], response["contacts"],
                                    response["known"])))


if __name__ == "__main__":
    main()
