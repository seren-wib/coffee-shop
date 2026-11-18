**Question:** with SQLite (WAL) and 3 gunicorn workers, do 10 concurrent orders for an option with stock 1 end in exactly one 201, stock 0 and nine 409s with no lock errors (NFR-15)? **Answer:** yes with `transaction_mode="IMMEDIATE"`: 30 of 30 rounds gave 1 × 201, 9 × 409, 0 × 500, stock 0 and 1 order row. With the default DEFERRED mode, 29 of 30 rounds had `database is locked` 500s (68 of 300 requests), though stock never went wrong.

# sqlite-concurrent-order

Spike for SDD 3.1. Run on 2026-11-19.

## What it runs

- A minimal Django project (`spike/`, `shop/`) with only the tables `create_order` touches.
  `shop/services.py` is SDD 4.5.3 `create_order` with `decrease_stock` and `_sync_sold_out`
  (4.7.6), `next_order_id` (4.5.2) and `shipping_fee_for` (4.4) as written in the SDD.
- `DATABASES` copies SDD 9.1 (`transaction_mode`, `timeout=20`, `init_command` setting WAL and
  `synchronous=NORMAL`). `SPIKE_TX_MODE` switches between `IMMEDIATE` and `DEFERRED`.
- No auth. The `X-User-Id` header picks the member. `CONN_MAX_AGE` is the default 0, so each
  request opens its own connection, as the real settings will.
- `run.sh` starts gunicorn with 3 sync workers, then for each round reseeds (one option with
  stock 1, members 1 to 10 each with that option in the cart), fires 10 requests released by one
  `threading.Barrier` (`load.py`), and records the responses and the table state afterwards.
- `SPARE=1` adds a second option of the same product with stock 100 that nobody orders, so the
  product stays `ON_SALE` after the first order. Without it, `_sync_sold_out` marks the product
  `SOLD_OUT` and the losing requests stop at the `ON_SALE` check (409 `NOT_AVAILABLE`) before
  reaching the conditional UPDATE. With it they reach the UPDATE and get 409 `OUT_OF_STOCK`.

## Environment

| Item | Value |
| --- | --- |
| OS | WSL2 Ubuntu 26.04.1 on Windows 11, 16 logical CPUs |
| Python | 3.14.4 (SDD plans 3.12; WSL had only 3.14) |
| Django / gunicorn | 6.1.1 / 27.0.1 |
| SQLite library | 3.46.1 |
| DB file | `/tmp` on the WSL ext4 disk, not a Windows mount |
| Client | same machine, `load.py` (urllib, 10 threads) |

Not measured: an EC2 t3.micro (2 vCPU). Response times below are local and say nothing about
production latency.

## Results (30 rounds × 10 requests per condition)

| Condition | 201 | 409 | 500 | `database is locked` | Rounds with 201 ≠ 1 | Final stock | p95 (ms, 300 req) | max (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IMMEDIATE | 30 | 270 (`NOT_AVAILABLE`) | 0 | 0 | 0 | 0 in 30/30 | 41.96 | 61.73 |
| IMMEDIATE, SPARE | 30 | 270 (`OUT_OF_STOCK`) | 0 | 0 | 0 | 0 in 30/30 | 54.96 | 91.75 |
| DEFERRED | 30 | 202 (`NOT_AVAILABLE`) | 68 | 68 | 0 | 0 in 30/30 | 48.70 | 63.16 |
| DEFERRED, SPARE | 30 | 198 (`OUT_OF_STOCK`) | 72 | 72 | 0 | 0 in 30/30 | 34.44 | 42.38 |

- Round 1 alone (the SDD 3.1 table): IMMEDIATE 201 × 1, 409 × 9, 500 × 0, stock 0, 1 order row,
  1 order item, 9 cart rows left, p95 51.72 ms. DEFERRED round 1 happened to have no lock error;
  rounds 2 to 30 had 1 to 4 each.
- In every round of every condition the table state matched the responses: orders = number of
  201s = 1, stock = 0. No oversell even in DEFERRED: the lock errors fail the whole transaction.
- DEFERRED lock errors come back fast (server time at most 16.86 ms), not after the 20 s
  `timeout`: a DEFERRED transaction that has read and then tries to write while another
  connection has committed cannot upgrade its lock, and SQLite returns `SQLITE_BUSY` at once
  without using the busy timeout.
- p95 is nearest-rank over all 300 requests of a condition, measured at the client. With 10
  requests in a round, a per-round p95 is the slowest request.

Raw data: `results/*.jsonl` (one line per round), `results/summary.json` (`summarize.py`).

## Run it again

```bash
python3 -m venv ~/.venvs/coffee-spike
~/.venvs/coffee-spike/bin/pip install django==6.1.1 gunicorn
./run.sh IMMEDIATE 30
./run.sh DEFERRED 30
SPARE=1 ./run.sh IMMEDIATE 30
SPARE=1 ./run.sh DEFERRED 30
~/.venvs/coffee-spike/bin/python summarize.py > results/summary.json
```

gunicorn does not run on Windows, so run this on Linux, macOS or WSL.
