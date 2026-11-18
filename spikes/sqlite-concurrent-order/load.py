"""Send N order requests at the same moment and print one JSON line.

Each thread is member i (X-User-Id: i). A barrier releases all threads
together so the requests overlap. Standard library only.
"""
import argparse
import json
import threading
import time
import urllib.error
import urllib.request


def post(url, user_id, barrier, results, idx):
    req = urllib.request.Request(url, data=b"{}", method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-User-Id", str(user_id))
    barrier.wait()
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    elapsed = (time.perf_counter() - started) * 1000
    try:
        body = json.loads(raw)
    except ValueError:
        body = {"raw": raw[:200].decode("utf-8", "replace")}
    results[idx] = {"user": user_id, "status": status, "ms": round(elapsed, 2), "body": body}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765/api/orders/")
    parser.add_argument("--n", type=int, default=10)
    args = parser.parse_args()

    barrier = threading.Barrier(args.n)
    results = [None] * args.n
    threads = [
        threading.Thread(target=post, args=(args.url, i + 1, barrier, results, i))
        for i in range(args.n)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(json.dumps(results))


if __name__ == "__main__":
    main()
