"""Call the Toss Payments confirm, cancel and get APIs with a test secret key.

The key is read from the development .env (TOSS_SECRET_KEY=test_sk_...): the file
named by DOTENV_PATH, else the repository root .env, else the main checkout's .env
when run from a git worktree (SDD 9). The file is git-ignored. Only test keys are accepted. Each call appends one JSON
line to results/calls.jsonl with the step label, HTTP status and a whitelist
of response fields; paymentKey is masked (SDD 4.6.5, 8.5).

Usage:
  python toss.py --step 2 confirm PAYMENT_KEY ORDER_ID AMOUNT
  python toss.py --step 3 cancel PAYMENT_KEY "reason" [--idem KEY]
  python toss.py --step 3 get PAYMENT_KEY
"""
import argparse
import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.tosspayments.com"
REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS = Path(__file__).parent / "results" / "calls.jsonl"
KEEP = (
    "code", "message", "status", "orderId", "totalAmount", "balanceAmount",
    "method", "approvedAt", "requestedAt", "type", "currency", "lastTransactionKey",
)


def env_file():
    if os.environ.get("DOTENV_PATH"):
        return Path(os.environ["DOTENV_PATH"])
    local = REPO_ROOT / ".env"
    if local.exists():
        return local
    # A worktree has no .env of its own; use the main checkout's.
    common = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    return Path(common).parent / ".env"


def secret_key():
    path = env_file()
    if not path.exists():
        raise SystemExit(f"{path} not found (set DOTENV_PATH or create the repo root .env)")
    for line in path.read_text(encoding="utf-8").splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "TOSS_SECRET_KEY":
            value = value.strip()
            if not value.startswith("test_"):
                raise SystemExit("TOSS_SECRET_KEY must be a test key (test_...)")
            return value
    raise SystemExit(f"TOSS_SECRET_KEY not found in {path}")


def mask(payment_key):
    return f"{payment_key[:6]}...{payment_key[-4:]}" if payment_key else payment_key


def call(method, path, body=None, idem=None):
    auth = base64.b64encode(f"{secret_key()}:".encode()).decode()
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Type", "application/json")
    if idem:
        req.add_header("Idempotency-Key", idem)
    data = json.dumps(body).encode() if body is not None else None
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, data=data, timeout=10) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    return status, json.loads(raw or b"{}"), round((time.perf_counter() - started) * 1000)


def summarize(payload):
    kept = {k: payload[k] for k in KEEP if k in payload}
    if "lastTransactionKey" in kept:
        kept["lastTransactionKey"] = mask(kept["lastTransactionKey"])
    if payload.get("cancels"):
        kept["cancels"] = [
            {k: c.get(k) for k in ("cancelAmount", "cancelReason", "canceledAt", "cancelStatus")}
            for c in payload["cancels"]
        ]
    return kept


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--step", required=True)
    p.add_argument("--note", default="")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("confirm")
    c.add_argument("payment_key")
    c.add_argument("order_id")
    c.add_argument("amount", type=int)
    x = sub.add_parser("cancel")
    x.add_argument("payment_key")
    x.add_argument("reason")
    x.add_argument("--idem")
    g = sub.add_parser("get")
    g.add_argument("payment_key")
    a = p.parse_args()

    if a.cmd == "confirm":
        body = {"paymentKey": a.payment_key, "orderId": a.order_id, "amount": a.amount}
        status, payload, ms = call("POST", "/v1/payments/confirm", body)
        request = {"orderId": a.order_id, "amount": a.amount}
    elif a.cmd == "cancel":
        status, payload, ms = call(
            "POST", f"/v1/payments/{a.payment_key}/cancel", {"cancelReason": a.reason}, a.idem
        )
        request = {"cancelReason": a.reason, "idempotencyKey": a.idem}
    else:
        status, payload, ms = call("GET", f"/v1/payments/{a.payment_key}")
        request = {}

    record = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "step": a.step,
        "note": a.note,
        "call": a.cmd,
        "paymentKey": mask(a.payment_key),
        "request": request,
        "http_status": status,
        "ms": ms,
        "response": summarize(payload),
    }
    RESULTS.parent.mkdir(exist_ok=True)
    with RESULTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
