# Message Formats (A3)

All messages are UTF-8 **JSON** published to one RabbitMQ topic exchange named `pbt205` (`content_type: application/json`). A "topic" in the brief is a **routing key** on that exchange. Every subscriber binds its own private queue, so each subscriber receives every message (publish/subscribe).

JSON was chosen for readability in the RabbitMQ management UI, no schema tooling, and built-in support in Python (`json` module). Every message carries a `ts` (ISO-8601 UTC) so ordering can be audited.

| Task | Topic (routing key) | Publisher | Subscriber |
|------|---------------------|-----------|------------|
| Chat | `room.<roomName>` | chat | chat |
| Trading | `orders` | sendOrder | exchange |
| Trading | `trades` | exchange | any (GUI, `exchange` logs) |
| Tracing | `position` | person | tracker |
| Tracing | `query` | query | tracker |
| Tracing | `query-response` | tracker | query |

## 1. Chat – `room.<roomName>`

```json
{ "type": "chat", "room": "room", "user": "alice", "text": "hello everyone", "ts": "2026-10-12T01:00:00.000Z" }
```
| Field | Type | Notes |
|-------|------|-------|
| type | string | always `"chat"` (also `"join"` / `"leave"` for presence notices) |
| room | string | room name, matches routing key suffix |
| user | string | unique username |
| text | string | message body (empty for join/leave) |
| ts | string | ISO-8601 |

A client prints messages from other users and ignores its own (`user` equals own username).

## 2. Orders – `orders`

```json
{ "type": "order", "orderId": "alice-1760230800000-1", "user": "alice", "symbol": "XYZ", "side": "BUY", "quantity": 100, "price": 10.5, "ts": "..." }
```
| Field | Type | Notes |
|-------|------|-------|
| orderId | string | `<user>-<epochMs>-<seq>`, unique |
| user | string | trader identifier |
| symbol | string | default `XYZ`; extra symbols for the multi-stock extension |
| side | string | `BUY` or `SELL` |
| quantity | integer | fixed at 100 for this assignment |
| price | number | limit price (double) – no market orders |

## 3. Trades – `trades`

```json
{ "type": "trade", "tradeId": 1, "symbol": "XYZ", "price": 10.0, "quantity": 100,
  "buyer": "alice", "seller": "bob", "buyOrderId": "...", "sellOrderId": "...", "ts": "..." }
```
**Price rule:** a trade executes at the **resting** order's price (the order already in the book), the standard price-time convention.

**Matching rule:** BUY matches a resting SELL if `buy.price >= sell.price`; SELL matches a resting BUY if `sell.price <= buy.price`. Earliest resting order at the best price wins.

## 4. Positions – `position`

```json
{ "type": "position", "person": "alice", "x": 4, "y": 7, "ts": "..." }
```
| Field | Type | Notes |
|-------|------|-------|
| person | string | unique identifier (first name) |
| x, y | integer | 0-based; `0 <= x,y < BOARD_SIZE` |

The first message from a person is its random start position; each later message is one King-move (dx, dy in {-1,0,1}, not both 0), clamped so the person never leaves the board.

## 5. Queries – `query`

```json
{ "type": "query", "queryId": "q-1760230800000-ab12", "person": "alice", "ts": "..." }
```
`queryId` lets a `query` client pick out its own response on the shared `query-response` topic.

## 6. Query responses – `query-response`

```json
{ "type": "query-response", "queryId": "q-1760230800000-ab12", "person": "alice",
  "contacts": [ { "name": "bob", "x": 3, "y": 3, "ts": "..." }, { "name": "carol", "x": 1, "y": 2, "ts": "..." } ],
  "ts": "..." }
```
`contacts` is in **reverse-chronological** order (most recent first). An unknown person returns `"contacts": []` plus `"known": false`.

## Versioning / compatibility
Consumers ignore unknown fields. Messages that fail `JSON.parse` are dropped and logged, never crash the app.
