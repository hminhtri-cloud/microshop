# Order backend — implemented local runtime

Order is a FastAPI service on host `127.0.0.1:8004` (container port 8000).
Swagger: `http://127.0.0.1:8004/docs`. Frontend URLs use `/api/orders`,
`/api/seller/orders`, `/api/admin/orders` via Vite. Checkout UI is a separate
frontend task; the existing cart button has not been enabled by this backend change.

## Start

1. Keep existing MySQL/JWT credentials in `.env`.
2. Generate another secret with `openssl rand -hex 32` and add
   `INTERNAL_SERVICE_TOKEN=<generated value>` to `.env`. Do not commit it.
3. Run `docker compose config --quiet` then `docker compose up -d --build --wait`.
4. Open Order Swagger, authorize with a customer/seller JWT from Auth.

Auth, Product and Order share this internal credential for **local** service
calls. `/internal/*` requires `X-Service-Token`, is excluded from Vite routing,
and must stay excluded from any public gateway. Host ports are loopback-only.
`order-db-setup` creates `order_db` without changing existing Auth/Product data.
New local tables bootstrap with `create_all`; schema changes to an existing Order
DB require a versioned migration. Do not delete the MySQL volume to update schema.

## Public endpoints

| Method | Path | Permission |
|---|---|---|
| POST | `/orders` | customer or seller; UUID-v4 `Idempotency-Key` required |
| GET | `/orders`, `/orders/{id}` | buyer's own orders |
| POST | `/orders/{id}/cancel` | owner, unpaid only |
| POST | `/orders/{id}/mock-payment` | owner; `{ "outcome": "success" \| "failure" }` |
| GET | `/seller/orders`, `/seller/orders/{id}` | current seller; own seller orders only |
| PATCH | `/seller/orders/{id}/status` | own paid part; confirmed → shipping → completed |
| GET | `/admin/orders`, `/admin/orders/{id}` | admin, read-only |
| GET | `/health`, `/ready` | liveness / Order DB readiness |

List endpoints accept `offset=0`, `limit=20` (max 100), newest first, returning
`items/total/offset/limit`. IDs in seller paths refer to **seller_order.id**.
Other users' resources return 404. Roles are re-checked through Auth on requests.
Prices are decimal strings, UTC creation timestamps end with `Z`. Errors use
`code/message/details/request_id`; request bodies are not echoed in validation errors.

Example `POST /orders` body (use IDs from your own catalog):

```json
{
  "items": [{ "product_id": 1, "quantity": 2 }],
  "shipping": {
    "receiver_name": "Nguyễn An",
    "phone": "0912345678",
    "address": "123 Đường ABC, Quận 1, TP.HCM",
    "note": null
  }
}
```

Generate an idempotency key with `python3 -c 'import uuid; print(uuid.uuid4())'`.
First successful create returns 201; replay with the same buyer/key/body returns
200 and the same order ID. Different body under the same key returns 409.
Item ordering does not affect the fingerprint; shipping changes do.
Rejected attempts retain their key and appear as `rejected` in order reads. After
fixing the cart, use a **new** key. After a timeout/503, use the **original** key
or read the buyer's orders: the worker may already have finished the request.

## Durable checkout saga

1. Commit an Order intent (`creating`) with request payload and unique buyer/key.
2. Lock that order row, request a Product reservation with the same buyer/key.
3. Product claims the unique reservation key, locks products by ascending ID,
   checks active/stock and current seller approval via Auth, then subtracts the
   whole batch and saves product/price/seller snapshots in one Product transaction.
4. Order groups the receipt by seller and saves all order lines + totals in one
   Order transaction (`pending`, `unpaid`). Inventory stays **reserved** until payment.
5. Payment success persists `confirming`, then confirms the reservation and marks
   the order paid. Cancel/failure persists `cancelling`/`failing`, then releases
   inventory and marks all seller parts cancelled.

Order runs a reconciliation worker every 10 seconds. It resumes durable in-flight
states after process restart or ambiguous HTTP/DB failures using the **same key**.
There is no SQL transaction spanning services and no blind release after an
ambiguous Order commit. If Order DB fails after reservation, the `creating` intent
is replayed to finish the order instead of losing the stock hold.

Unpaid orders expire 30 minutes after intent creation. Order's worker durably
initiates cancellation/release; a payment started after expiry is rejected.
Confirmation already durably started before expiry is allowed to finish.
Product does not expire reservations independently: it cannot know whether a
payment/Order commit succeeded. While Order or its DB is unavailable, recovery and
expiry wait until it returns. Never remove durable intents/reservations manually.
For sustained service outages, monitor in-flight states and reconciliation logs.

Seller stock replacement is rejected while that product has active reservations
if the requested quantity differs from current available stock; this avoids
overwriting checkout deductions with a stale seller form. Price/name changes are
allowed, but existing reservation/order snapshots remain unchanged.

`service.py`/`products_client.py` retain the earlier teaching quote helper; the
checkout endpoints use `checkout.py` + `stock_client.py`, not the read-only quote.

## Internal endpoints

- Auth: `POST /internal/sellers/eligibility` with `seller_ids` → `eligible` boolean.
- Product: `POST /internal/stock/reservations` with `buyer_id/request_key/items`.
- Product: `POST /internal/stock/reservations/{buyer_id}/{key}/confirm` or `/release`.

All require `X-Service-Token`. Confirm/release are idempotent; released cannot
be confirmed and confirmed cannot be released. Product retry returns original
snapshots rather than the catalog's latest prices.

## Tests

Service tests use temporary SQLite and test doubles; CI also runs real HTTP between
Auth/Product/Order on temporary SQLite DBs, plus MySQL concurrency tests for last-item
stock, simultaneous key reuse and cancel/payment races. Only dedicated disposable
MySQL database names ending in `_test` are allowed by the concurrency suites.

```bash
docker compose run --rm --no-deps -e DATABASE_URL=sqlite:// \
  -v "$PWD/services/order-service/tests:/tests:ro" \
  order-service python -m unittest discover -s /tests -v
docker compose run --rm --no-deps -e DATABASE_URL=sqlite:// \
  -v "$PWD/services/product-service/tests:/tests:ro" \
  product-service python -m unittest discover -s /tests -v
docker compose run --rm --no-deps -v "$PWD:/workspace:ro" -w /workspace \
  auth-service python -m unittest discover -s tests -v
```

MySQL race tests skip locally unless `INVENTORY_TEST_DATABASE_URL` or
`ORDER_TEST_DATABASE_URL` points to a disposable MySQL `*_test` DB. CI provisions
these separately from application data; see `.github/workflows/ci.yml`.
