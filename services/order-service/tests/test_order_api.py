"""HTTP tests against an isolated DB and an idempotent inventory test double."""
import copy
import json
import os
import socket
import threading
import tempfile
import time
import unittest
from datetime import timedelta
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import uvicorn
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from app import checkout
from app.auth import Identity, get_identity
from app.database import Base, get_db
from app.main import app
from app.models import Order
from app.stock_client import Receipt


class InventoryDouble:
    def __init__(self):
        self.records = {}
        self.deductions = 0
        self.releases = 0
        self.timeout_after_reserve = False
        self.timeout_after_finalize = False
        self.reject = False

    def reserve(self, customer, key, items):
        if self.reject:
            raise HTTPException(409, {"code": "INSUFFICIENT_STOCK", "message": "Out of stock"})
        if (customer, key) not in self.records:
            self.deductions += 1
            self.records[customer, key] = Receipt(id=1, status="reserved", items=[
                {**item, "seller_id": 20 if item["product_id"] == 1 else 30,
                 "price": "12.50", "name": "Original name"} for item in items])
        if self.timeout_after_reserve:
            self.timeout_after_reserve = False
            raise HTTPException(503, "Timeout after inventory committed")
        return self.records[customer, key]

    def finalize(self, customer, key, action):
        result = self.records[customer, key]
        target = "confirmed" if action == "confirm" else "released"
        if result.status == "reserved":
            result.status = target
            self.releases += action == "release"
        elif result.status != target:
            raise HTTPException(409, "Already finalized")
        if self.timeout_after_finalize:
            self.timeout_after_finalize = False
            raise HTTPException(503, "Timeout after inventory finalized")


class OrderApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if cls.__name__ == "MySQLOrderTests":
            from sqlalchemy.engine import make_url
            url = make_url(os.environ["ORDER_TEST_DATABASE_URL"])
            if url.get_backend_name() != "mysql" or not (url.database or "").endswith("_test"):
                raise RuntimeError("Use only disposable MySQL *_test database")
            cls.engine = create_engine(url)
        else:
            # Separate real connections prevent HTTP dependency cleanup from
            # rolling back a test setup transaction on a shared StaticPool connection.
            cls.temp = tempfile.TemporaryDirectory(prefix="microshop-order-tests-")
            cls.addClassCleanup(cls.temp.cleanup)
            cls.engine = create_engine(f"sqlite:///{cls.temp.name}/orders.db")
        cls.sessions = sessionmaker(bind=cls.engine, autoflush=False)
        Base.metadata.create_all(cls.engine)

        def test_db():
            with cls.sessions() as db:
                yield db

        cls.patches = [patch("app.main.engine", cls.engine), patch("app.main.reconcile_once"),
                       patch.dict(os.environ, {"INTERNAL_SERVICE_TOKEN": "unit-test-only"})]
        for item in cls.patches:
            item.start()
        cls.identity = Identity(10, "customer")
        app.dependency_overrides[get_db] = test_db
        app.dependency_overrides[get_identity] = lambda: cls.identity
        cls.listener = socket.socket()
        cls.listener.bind(("127.0.0.1", 0))
        cls.base_url = f"http://127.0.0.1:{cls.listener.getsockname()[1]}"
        cls.server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        cls.thread = threading.Thread(target=cls.server.run, kwargs={"sockets": [cls.listener]}, daemon=True)
        cls.thread.start()
        for _ in range(100):
            if cls.server.started:
                break
            time.sleep(0.05)
        if not cls.server.started:
            raise RuntimeError("Order test server failed to start")

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=5)
        cls.listener.close()
        app.dependency_overrides.clear()
        for item in reversed(cls.patches):
            item.stop()
        cls.engine.dispose()

    def setUp(self):
        self.__class__.identity = Identity(10, "customer")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.inventory = InventoryDouble()
        self.reserve_patch = patch("app.stock_client.reserve", self.inventory.reserve)
        self.finalize_patch = patch("app.stock_client.finalize", self.inventory.finalize)
        self.reserve_patch.start()
        self.finalize_patch.start()
        self.addCleanup(self.reserve_patch.stop)
        self.addCleanup(self.finalize_patch.stop)
        self.key = str(uuid4())
        self.body = {"items": [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}],
                     "shipping": {"receiver_name": "Test Buyer", "phone": "0912345678",
                                  "address": "123 Test Street"}}

    def request(self, method, path, body=None, key=None):
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Idempotency-Key"] = key
        request = Request(self.base_url + path, data=json.dumps(body).encode() if body is not None else None,
                          headers=headers, method=method)
        try:
            response = urlopen(request, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def create(self):
        status, order = self.request("POST", "/orders", self.body, self.key)
        self.assertEqual(status, 201, order)
        return order

    def reconcile(self):
        with patch("app.checkout.SessionLocal", self.sessions):
            checkout.reconcile_once()

    def test_multiseller_and_idempotency(self):
        order = self.create()
        self.assertEqual(order["total_amount"], "37.50")
        self.assertEqual(len(order["seller_orders"]), 2)
        self.assertTrue(order["created_at"].endswith("Z"))
        self.body["items"].reverse()
        status, replay = self.request("POST", "/orders", self.body, self.key)
        self.assertEqual((status, replay["id"], self.inventory.deductions), (200, order["id"], 1))
        self.body["shipping"]["address"] = "456 Other Street"
        status, error = self.request("POST", "/orders", self.body, self.key)
        self.assertEqual((status, error["code"]), (409, "IDEMPOTENCY_CONFLICT"))

    def test_untrusted_fields_duplicate_items_and_key_validation(self):
        for field in ("total_amount", "seller_id", "customer_id"):
            body = copy.deepcopy(self.body)
            body[field] = 123
            self.assertEqual(self.request("POST", "/orders", body, self.key)[0], 422)
        self.assertEqual(self.request("POST", "/orders", self.body)[0], 422)
        self.assertEqual(self.request("POST", "/orders", self.body, "wrong-key")[0], 422)
        self.body["items"].append(self.body["items"][0])
        self.assertEqual(self.request("POST", "/orders", self.body, self.key)[0], 422)
        self.assertEqual(self.inventory.deductions, 0)

    def test_ownership_roles_and_pages(self):
        order = self.create()
        self.assertEqual(self.request("GET", "/orders")[1]["total"], 1)
        self.__class__.identity = Identity(11, "customer")
        self.assertEqual(self.request("GET", f'/orders/{order["id"]}')[0], 404)
        self.assertEqual(self.request("POST", f'/orders/{order["id"]}/cancel', {})[0], 404)
        self.assertEqual(self.request("GET", "/orders")[1]["total"], 0)
        self.__class__.identity = Identity(99, "admin")
        self.assertEqual(self.request("GET", "/admin/orders")[1]["total"], 1)
        self.assertEqual(self.request("POST", "/orders", self.body, str(uuid4()))[0], 403)
        self.assertEqual(self.request("GET", "/orders?limit=101")[0], 403)

    def test_cancel_releases_once_and_blocks_payment(self):
        order = self.create()
        path = f'/orders/{order["id"]}'
        for _ in range(2):
            status, result = self.request("POST", path + "/cancel", {})
            self.assertEqual((status, result["payment_status"]), (200, "cancelled"))
        self.assertEqual(self.inventory.releases, 1)
        self.assertEqual(self.request("POST", path + "/mock-payment", {"outcome": "success"})[0], 409)

    def test_payment_and_seller_fulfillment(self):
        order = self.create()
        part = order["seller_orders"][0]
        self.__class__.identity = Identity(part["seller_id"], "seller")
        path = f'/seller/orders/{part["id"]}/status'
        self.assertEqual(self.request("PATCH", path, {"status": "confirmed"})[0], 409)
        self.__class__.identity = Identity(10, "customer")
        payment = f'/orders/{order["id"]}/mock-payment'
        for _ in range(2):
            self.assertEqual(self.request("POST", payment, {"outcome": "success"})[1]["payment_status"], "paid")
        self.assertEqual(self.request("POST", payment, {"outcome": "failure"})[0], 409)
        self.assertEqual(self.request("POST", f'/orders/{order["id"]}/cancel', {})[0], 409)
        for part in order["seller_orders"]:
            self.__class__.identity = Identity(part["seller_id"], "seller")
            self.assertEqual(self.request("GET", "/seller/orders")[1]["total"], 1)
            path = f'/seller/orders/{part["id"]}/status'
            self.assertEqual(self.request("PATCH", path, {"status": "completed"})[0], 409)
            for state in ("confirmed", "shipping", "completed"):
                self.assertEqual(self.request("PATCH", path, {"status": state})[0], 200)
        self.__class__.identity = Identity(10, "customer")
        self.assertEqual(self.request("GET", f'/orders/{order["id"]}')[1]["status"], "completed")

    def test_seller_cannot_read_other_seller_or_suspended(self):
        order = self.create()
        part_id = order["seller_orders"][0]["id"]
        self.__class__.identity = Identity(999, "seller")
        self.assertEqual(self.request("GET", f"/seller/orders/{part_id}")[0], 404)
        self.__class__.identity = Identity(20, "customer")
        self.assertEqual(self.request("GET", "/seller/orders")[0], 403)

    def test_timeout_after_reserve_recovers_without_second_deduction(self):
        self.inventory.timeout_after_reserve = True
        self.assertEqual(self.request("POST", "/orders", self.body, self.key)[0], 503)
        self.reconcile()
        status, order = self.request("POST", "/orders", self.body, self.key)
        self.assertEqual((status, order["status"], self.inventory.deductions), (200, "pending", 1))

    def test_order_db_failure_after_reserve_recovers(self):
        commit = Session.commit
        count = 0

        def fail_second_commit(db):
            nonlocal count
            count += 1
            if count == 2:
                raise SQLAlchemyError("Simulated order DB write failure")
            return commit(db)

        with patch.object(Session, "commit", fail_second_commit):
            self.assertEqual(self.request("POST", "/orders", self.body, self.key)[0], 503)
        with self.sessions() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Order)), 1)
            self.assertEqual(db.scalar(select(Order.status)), "creating")
        self.reconcile()
        self.assertEqual(self.inventory.deductions, 1)
        self.assertEqual(self.request("GET", "/orders")[1]["items"][0]["status"], "pending")

    def test_ambiguous_release_and_confirm_are_reconciled(self):
        for outcome, terminal in (("failure", "failed"), ("success", "paid")):
            self.key = str(uuid4())
            order = self.create()
            self.inventory.timeout_after_finalize = True
            self.assertEqual(self.request("POST", f'/orders/{order["id"]}/mock-payment', {"outcome": outcome})[0], 503)
            self.reconcile()
            self.assertEqual(self.request("GET", f'/orders/{order["id"]}')[1]["payment_status"], terminal)
        self.assertEqual(self.inventory.releases, 1)

    def test_expired_order_cannot_be_paid_and_worker_returns_stock(self):
        order = self.create()
        with self.sessions() as db:
            saved = db.get(Order, order["id"])
            saved.created_at = checkout.utc_now() - timedelta(minutes=31)
            db.commit()
        status, error = self.request("POST", f'/orders/{order["id"]}/mock-payment', {"outcome": "success"})
        self.assertEqual(status, 409, error)
        self.assertEqual((status, error["code"]), (409, "RESERVATION_EXPIRED"))
        self.assertEqual(self.inventory.releases, 1)
        self.reconcile()
        self.assertEqual(self.inventory.releases, 1)

    def test_rejected_checkout_is_stable(self):
        self.inventory.reject = True
        self.assertEqual(self.request("POST", "/orders", self.body, self.key)[1]["code"], "INSUFFICIENT_STOCK")
        self.inventory.reject = False
        self.assertEqual(self.request("POST", "/orders", self.body, self.key)[0], 409)
        self.assertEqual(self.inventory.deductions, 0)

    def test_worker_expires_abandoned_unpaid_order(self):
        order = self.create()
        with self.sessions() as db:
            db.get(Order, order["id"]).created_at = checkout.utc_now() - timedelta(minutes=31)
            db.commit()
        self.reconcile()
        self.assertEqual(self.request("GET", f'/orders/{order["id"]}')[1]["payment_status"], "cancelled")
        self.assertEqual(self.inventory.releases, 1)


@unittest.skipUnless(os.getenv("ORDER_TEST_DATABASE_URL"), "Requires disposable MySQL *_test database")
class MySQLOrderTests(OrderApiTests):
    def race(self, calls):
        from concurrent.futures import ThreadPoolExecutor
        barrier = threading.Barrier(2)

        def run(call):
            barrier.wait(timeout=5)
            return call()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, calls))

    def test_same_key_concurrent_checkout(self):
        results = self.race([lambda: self.request("POST", "/orders", self.body, self.key)] * 2)
        self.assertEqual(sorted(result[0] for result in results), [200, 201])
        self.assertEqual(results[0][1]["id"], results[1][1]["id"])
        self.assertEqual(self.inventory.deductions, 1)

    def test_cancel_and_payment_race_has_one_winner(self):
        order = self.create()
        base = f'/orders/{order["id"]}'
        results = self.race([lambda: self.request("POST", base + "/cancel", {}),
                             lambda: self.request("POST", base + "/mock-payment", {"outcome": "success"})])
        self.assertEqual(sorted(result[0] for result in results), [200, 409])
        state = self.request("GET", base)[1]["payment_status"]
        self.assertIn(state, ("paid", "cancelled"))
        self.assertEqual(self.inventory.releases, int(state == "cancelled"))


if __name__ == "__main__":
    unittest.main()
