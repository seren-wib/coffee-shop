"""Summarize results/*.jsonl into the numbers SDD 3.1 asks for."""
import json
import math
import sys
from collections import Counter
from pathlib import Path


def p95(values):
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]  # nearest-rank


def summarize(path):
    rounds = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    statuses, codes, locked = Counter(), Counter(), 0
    ms_all, bad_rounds = [], []
    per_round_p95 = []
    first = rounds[0]
    for r in rounds:
        res = r["responses"]
        statuses.update(x["status"] for x in res)
        codes.update(x["body"].get("code", "OK") for x in res)
        locked += sum("database is locked" in x["body"].get("message", "") for x in res)
        ms = [x["ms"] for x in res]
        ms_all += ms
        per_round_p95.append(p95(ms))
        s = r["state"]
        created = sum(x["status"] == 201 for x in res)
        if not (s["stock_quantity"] == 1 - created and s["orders"] == created):
            bad_rounds.append(r["round"])
    first_status = Counter(x["status"] for x in first["responses"])
    return {
        "mode": first["mode"],
        "spare": first.get("spare", 0),
        "rounds": len(rounds),
        "requests": len(ms_all),
        "round1": {
            "status": dict(first_status),
            "state": first["state"],
            "p95_ms": p95([x["ms"] for x in first["responses"]]),
        },
        "status_total": dict(statuses),
        "codes_total": dict(codes),
        "database_is_locked": locked,
        "rounds_with_201_not_1": sum(
            sum(x["status"] == 201 for x in r["responses"]) != 1 for r in rounds
        ),
        "rounds_state_mismatch": bad_rounds,
        "final_stock_values": dict(Counter(r["state"]["stock_quantity"] for r in rounds)),
        "journal_modes": dict(Counter(r["state"]["journal_mode"] for r in rounds)),
        "p95_ms_all": p95(ms_all),
        "p50_ms_all": sorted(ms_all)[len(ms_all) // 2],
        "max_ms_all": max(ms_all),
        "round_p95_ms_median": sorted(per_round_p95)[len(per_round_p95) // 2],
    }


if __name__ == "__main__":
    here = Path(__file__).parent / "results"
    paths = [Path(p) for p in sys.argv[1:]] or sorted(here.glob("*.jsonl"))
    for path in paths:
        print(json.dumps(summarize(path), ensure_ascii=False, indent=2))
