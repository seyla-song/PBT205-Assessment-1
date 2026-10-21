# Task 2 (Trading, Python) – detailed run guide and screenshot instructions

| ID  | Task (from your checklist)                                                                                   | Where it is in the code                                        |
| --- | ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| C1  | exchange app: subscribe to `orders`, keep buy and sell lists, match on acceptable price, publish to `trades` | `task2-trading/exchange.py`, `task2-trading/order_book.py`     |
| C2  | sendOrder app: username, port, BUY/SELL, price, quantity fixed at 100, publish and exit                      | `task2-trading/send_order.py`                                  |
| C3  | GUI showing "Last price: X" from `trades`                                                                    | `task2-trading/gui_server.py` + `task2-trading/gui/index.html` |
| C4  | Integration test with several traders, save screenshots                                                      | this guide, plus `python scripts/test_trading.py`              |

**Command format for send_order:**

```
python task2-trading/send_order.py <username> <port> <BUY|SELL> <quantity> <price> [stock]
```

Quantity must be `100`. The stock is optional and defaults to `XYZ`. Example: `python task2-trading/send_order.py alice 5672 BUY 100 10.50`

On Windows, if `python` is not recognised, use `py` instead (for example `py task2-trading/exchange.py 5672`). Use the same word everywhere.

**How the pieces talk:** `send_order` → topic `orders` → `exchange` → topic `trades` → GUI. All of it goes through RabbitMQ on port 5672.

---

## Part A – Before you start

### A1. Install the tools (once)

1. **Python 3.8 or newer** from https://www.python.org/downloads. On Windows, tick **"Add python.exe to PATH"** in the installer. Check: open a terminal and run `python --version` (or `py --version`).
2. **Docker Desktop** from https://www.docker.com/products/docker-desktop. Start it and wait until it says it is running.
3. **VS Code** (optional but recommended) with the Python extension, and **Git** (optional, to commit your screenshots).

### A2. Open the project in a terminal

1. Unzip the project folder.
2. Open the folder in **VS Code** (File → Open Folder). You can split the terminal into side-by-side panes (see Part B).
3. Open a terminal inside VS Code: menu **Terminal → New Terminal**.
4. Install the one dependency (`pika`, the RabbitMQ client for Python):
   ```
   pip install -r requirements.txt
   ```
   Expected: it ends with "Successfully installed pika-…". If `pip` is not found, use `python -m pip install -r requirements.txt`.
   _Optional:_ use a virtual environment first: `python -m venv .venv`, then activate it (Windows PowerShell: `.venv\Scripts\Activate.ps1`; macOS/Linux: `source .venv/bin/activate`). If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or skip the virtual environment.

### A3. Start RabbitMQ

```
docker compose up -d
```

Expected: it shows the `rabbitmq` container as _Started_. Check with `docker ps` – you should see `rabbitmq` with ports `5672` and `15672`.
Then open **http://localhost:15672** in a browser and log in with `guest` / `guest`. If you see the RabbitMQ dashboard, the broker is working (the first start can take about 30 seconds).

Alternative (the command from the assessment brief), which keeps its terminal busy so use a separate terminal:

```
docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

### A4. Quick sanity check (optional)

```
python scripts/test_unit.py
```

Expected: `Ran 14 tests … OK` (no broker needed).

---

## Part B – Set up the screenshot workspace (do this once)

### B1. Where screenshots go

Save every screenshot inside the project at **`docs/screenshots/`** using the exact file names in Part D. Create no sub-folders.

### B2. How to take a screenshot

| System            | Capture a region                                                                        | Capture the whole screen                 |
| ----------------- | --------------------------------------------------------------------------------------- | ---------------------------------------- |
| **Windows 10/11** | `Win + Shift + S`, drag a rectangle, then click the notification that appears → Save as | `PrtScn`, then paste into Paint and save |
| **macOS**         | `Cmd + Shift + 4`, drag a rectangle (the file lands on the Desktop)                     | `Cmd + Shift + 3`                        |
| **Linux**         | `PrtScn` (GNOME opens a screenshot tool), or `Shift + PrtScn` for a region              | `PrtScn`                                 |

Save it, then **move or rename** the file to `docs/screenshots/<name>.png`. Tip: in VS Code, drag the file into the `docs/screenshots` folder in the Explorer panel. **Name the file after you have saved it, not by typing in the terminal** (typing the name into the screenshot tool while a terminal has focus puts the text into the terminal).

### B3. Arrange your terminals so each shot shows what the marker needs

Use VS Code's **split terminal** button (next to the `+` in the terminal panel). Give each terminal a name by right-clicking its tab → Rename:

- `EXCHANGE`
- `GUI SERVER`
- `TRADERS`

Make the text large enough to read: press `Ctrl` and `+` (or `Cmd` and `+`) in the terminal panel, and drag the panel's top edge up to make it tall. Before each screenshot you may clear the TRADERS terminal with `cls` (Windows) or `clear` (macOS/Linux). **Do not clear the EXCHANGE terminal** – it holds the evidence.

### B4. What a good screenshot looks like

- The whole command and its output are visible; nothing is cut off.
- The terminal tab shows which program it is (EXCHANGE, TRADERS).
- Where the guide says "beside", both windows are in the same picture.
- A clock or timestamp is visible if possible (the taskbar clock is enough).
- Nothing private is in the picture (close other browser tabs such as messaging apps, or crop them out).

---

## Part C – Run it, step by step

You need **three terminals** and **one browser window**. Keep all of them open until the end.

### C1/C3 – Start the exchange (terminal named EXCHANGE)

```
python task2-trading/exchange.py 5672
```

Expected output:

```
Exchange running. Subscribed to "orders", publishing to "trades".
```

Leave this running. **Only one exchange may run at a time.** If you see `Cannot reach RabbitMQ`, go back to A3.

### C3 – Start the GUI (terminal named GUI SERVER)

```
python task2-trading/gui_server.py 5672
```

Expected output: `Trading GUI on http://localhost:3002  (broker endpoint 5672)`.
Open **http://localhost:3002** in your browser. You should see "PBT205 Trading — latest prices" with a tile for XYZ showing `Last price: —`. Put the browser window **next to** the EXCHANGE terminal so you can capture both.

### C2/C4 – Send orders (terminal named TRADERS)

Run the commands one at a time. After each, look at the EXCHANGE terminal and the browser.

**Step 1 – a buy that cannot match yet**

```
python task2-trading/send_order.py alice 5672 BUY 100 10.50
```

- TRADERS prints `Sent BUY 100 XYZ @ 10.5 as alice` and the command returns immediately (it publishes and exits – the C2 requirement).
- EXCHANGE prints `ORDER  alice BUY 100 XYZ @ 10.5` and `BOOK   XYZ {"bids":["alice@10.5"],"asks":[]}`. That is the buy list.
- Browser: price still `—`; the Recent orders table shows alice's BUY.

**Step 2 – a sell that is too expensive (no trade)**

```
python task2-trading/send_order.py bob 5672 SELL 100 11.00
```

- EXCHANGE prints `ORDER` and `BOOK   XYZ {"bids":["alice@10.5"],"asks":["bob@11"]}`. **No TRADE line**, because the seller wants 11.00 but the buyer only pays 10.50.
- 📸 Take **`C1-exchange-order-book.png`** now (EXCHANGE terminal showing both BOOK lines).

**Step 3 – a sell that matches (first trade)**

```
python task2-trading/send_order.py carol 5672 SELL 100 10.00
```

- EXCHANGE prints `TRADE  #1 XYZ 100 @ 10.5 (buyer alice, seller carol)`. The price is 10.5 because the trade happens at the price of the order that was already waiting (alice's).
- Browser: the XYZ tile changes to **`Last price: 10.50`**; the Recent trades table gets a row.
- 📸 Take **`C1-exchange-trade.png`** (EXCHANGE terminal) and **`C3-gui-last-price.png`** (the **browser window showing "Last price: 10.50"**, with the EXCHANGE terminal beside it).

**Step 4 – a buy that matches the waiting sell**

```
python task2-trading/send_order.py dave 5672 BUY 100 11.50
```

- EXCHANGE prints `TRADE  #2 XYZ 100 @ 11 (buyer dave, seller bob)` (bob's price, because bob was waiting).
- Browser: **`Last price: 11.00`**, coloured green because the price went up.

**Step 5 – a sell that stays in the book**

```
python task2-trading/send_order.py dave 5672 BUY 100 11.50
```

- EXCHANGE prints `ORDER` and `BOOK   XYZ {"bids":[],"asks":["erin@12"]}`. No trade.

**Step 6 – rejected quantity (C2 validation)**

```
python task2-trading/send_order.py eve 5672 BUY 50 10
```

- TRADERS prints `QUANTITY is fixed at 100 for this assignment` plus the usage line. Nothing appears in EXCHANGE.
- 📸 Take **`C2-sendorder.png`**: the TRADERS terminal showing a `Sent …` line (from an earlier step) and this error.

**Step 7 – a second stock (multiple stocks extension)**

```
python task2-trading/send_order.py frank 5672 BUY 100 5 ABC
python task2-trading/send_order.py gina 5672 SELL 100 5 ABC
```

- EXCHANGE prints `TRADE  #3 ABC 100 @ 5 (buyer frank, seller gina)`.
- Browser: a second tile **ABC** appears with `Last price: 5.00`, and XYZ stays at 11.00.
- 📸 Take **`C3-gui-multi-stock.png`**: the **browser window** with both the XYZ and ABC tiles visible.

**Step 8 – place an order from the GUI (optional)**
In the browser's "Place an order" form enter Trader `hank`, Side `BUY`, Stock `XYZ`, Price `12`, then click **Send order**. The EXCHANGE terminal prints an order from hank, and it matches erin's SELL @ 12, so the GUI shows `Last price: 12.00`.

### C4 – Show the several-trader result

After the steps, the EXCHANGE terminal contains orders from alice, bob, carol, dave, erin, frank and gina (and hank if you did step 8).

- 📸 Take **`C4-several-traders.png`**: the EXCHANGE terminal (scroll to the top of the session so the most orders are visible).

### C4 – RabbitMQ dashboard evidence

With the exchange and GUI still running, in http://localhost:15672 (guest / guest):

1. **Exchanges** tab → find `pbt205` (type `topic`). 📸 **`C4-rabbitmq-exchange.png`**.
2. **Queues and Streams** tab → queues with random `amq.gen-…` names (one per running subscriber: the exchange, and the GUI's two subscriptions). 📸 **`C4-rabbitmq-queues.png`**. They disappear when the programs stop, so capture them while everything is running.

### C4 – Automated tests

1. Stop the manual programs: press `Ctrl + C` in the EXCHANGE and GUI SERVER terminals. (The tests start their own exchange, and two exchanges would double-match. `test_gui.py` also needs port 3002 free.)
2. Run:
   ```
   python scripts/test_trading.py
   ```
   Expected: 10 lines starting with `PASS`, then `Transcript saved: docs/test-evidence/trading-test.txt`.
3. 📸 **`C4-test-output.png`**: the terminal showing all the PASS lines.
4. Optional extra evidence for the GUI: `python scripts/test_gui.py` (8 PASS lines; saves `docs/test-evidence/gui-test.txt`).

If any line says `FAIL`, check that RabbitMQ is running, that no other exchange or GUI is running, and rerun.

---

## Part D – Screenshot checklist

| #   | File name (in `docs/screenshots/`) | What must be visible                                                             | When             |
| --- | ---------------------------------- | -------------------------------------------------------------------------------- | ---------------- |
| 1   | `C1-exchange-order-book.png`       | EXCHANGE terminal: `ORDER` and `BOOK` lines for alice and bob, **no TRADE**      | after step 2     |
| 2   | `C1-exchange-trade.png`            | EXCHANGE terminal: `TRADE #1 XYZ 100 @ 10.5 (buyer alice, seller carol)`         | after step 3     |
| 3   | `C2-sendorder.png`                 | TRADERS terminal: a `Sent BUY 100 XYZ …` line and the quantity-must-be-100 error | after step 6     |
| 4   | `C3-gui-last-price.png`            | **Browser** showing `Last price: 10.50`, EXCHANGE terminal beside it             | after step 3     |
| 5   | `C3-gui-multi-stock.png`           | **Browser** showing XYZ and ABC tiles                                            | after step 7     |
| 6   | `C4-several-traders.png`           | EXCHANGE terminal with orders from at least 5 different traders                  | after step 7/8   |
| 7   | `C4-rabbitmq-exchange.png`         | RabbitMQ UI → Exchanges → `pbt205`                                               | programs running |
| 8   | `C4-rabbitmq-queues.png`           | RabbitMQ UI → Queues list                                                        | programs running |
| 9   | `C4-test-output.png`               | `python scripts/test_trading.py` with 10 × PASS                                  | end              |

If Member A built their own sendOrder or GUI, add these two:

| #   | File name                          | What must be visible                                                                                 | When |
| --- | ---------------------------------- | ---------------------------------------------------------------------------------------------------- | ---- |
| 10  | `C4-member-a-app-order.png`        | Member A's app sending an order, with the EXCHANGE terminal beside it showing it received that order |      |
| 11  | `C4-member-a-app-latest-price.png` | Member A's app (or GUI) showing the new last price after a trade                                     |      |

**Check your screenshots before you finish:**

- You can read the text without zooming.
- The terminal shows **`python …`** commands (these programs are in Python).
- Each file name matches the table exactly.
- Screenshots 4 and 5 show the **browser**, not a terminal or the RabbitMQ page.

---

## Part E – Finish up

1. Stop the programs with `Ctrl + C` in each terminal, then stop RabbitMQ: `docker compose down`.
2. Commit the evidence so the team has it:
   ```
   git add docs/screenshots docs/test-evidence
   git commit -m "Task 2 evidence: screenshots and test transcripts"
   ```
3. Put the screenshots into the Task 2 report (`docs/reports/report-task2-trading.md`, section 3) and fill in the Result column.

---

## Troubleshooting

| Problem                                                        | Cause and fix                                                                                                                                      |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `python` is not recognised                                     | Reinstall Python with "Add to PATH" ticked, or use `py` instead of `python`.                                                                       |
| `ModuleNotFoundError: No module named 'pika'`                  | Run `pip install -r requirements.txt` (in the same Python you run the programs with; if you use a virtual environment, activate it first).         |
| `Cannot reach RabbitMQ at amqp://localhost:5672`               | Docker isn't running or the container isn't up. Start Docker Desktop, run `docker compose up -d`, check `docker ps`.                               |
| Port 5672 or 15672 already in use                              | Another RabbitMQ is running. Stop it, or change `5672:5672` in `docker-compose.yml` to `5673:5672` and use `5673` as the port argument everywhere. |
| Orders are sent but nothing happens                            | The exchange isn't running, or it was started with a different port than `send_order`.                                                             |
| Trades appear twice / odd results                              | Two exchanges are running. Keep exactly one.                                                                                                       |
| GUI shows no price                                             | The price only appears after a **trade**; unmatched orders appear only in Recent orders.                                                           |
| `OSError: [Errno 98/10048] Address already in use` for the GUI | Port 3002 is taken; stop the old GUI (`Ctrl + C`) or run `python task2-trading/gui_server.py 5672 3012` and open http://localhost:3012.            |
| Orders vanished after restart                                  | The order book is in memory and is lost when the exchange restarts. Re-send the orders.                                                            |
| `send_order` says QUANTITY is fixed at 100                     | By design (the brief fixes quantity at 100).                                                                                                       |
