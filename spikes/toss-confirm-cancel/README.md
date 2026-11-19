**Question:** with a Toss Payments test key, do the payment window, `successUrl` return, server confirm, full cancel, double cancel, amount mismatch, `failUrl`, 10-minute expiry and `Idempotency-Key` behave as SDD 4.6 assumes? **Answer:** yes except two points (2026-11-19). A confirm with a different amount is refused with 403 `FORBIDDEN_REQUEST` instead of being approved, and closing the window rejects `requestPayment()` with `USER_CANCEL` instead of going to `failUrl`. The 10-minute expiry was not measured. See SDD 3.2.

# toss-confirm-cancel

Spike for SDD 3.2. Run on 2026-11-19 (all steps except 6, the 10-minute expiry). Raw calls are in `results/calls.jsonl`.

## Keys

Both keys come from the development `.env`, the same file `backend/config/settings.py` reads
(SDD 9): the file named by `DOTENV_PATH`, else the repository root `.env`, else the main
checkout's `.env` when run from a git worktree. Only test keys (`test_...`) are accepted.

```
TOSS_CLIENT_KEY=test_ck_...
TOSS_SECRET_KEY=test_sk_...
```

The secret key is used only by `toss.py`. The browser gets only the client key.

## What it runs

- `web/`: a Vite page on `http://localhost:5173` that opens the card payment window with the
  payment window SDK (SDD 4.6.2). `success.html` and `fail.html` show every query parameter Toss
  appends. The confirm call is not made from the browser.
- `toss.py`: calls confirm, cancel and get with the secret key. Each call appends one line to
  `results/calls.jsonl` with the step, HTTP status, time and a whitelist of response fields.
  `paymentKey` is masked. Only payments this spike created are confirmed, cancelled or read.

## Run

```
cd web
npm ci
npm run dev
```

```
python toss.py --step 2 confirm PAYMENT_KEY ORDER_ID AMOUNT
python toss.py --step 3 cancel PAYMENT_KEY "spike cancel" --idem KEY
python toss.py --step 3 get PAYMENT_KEY
```
