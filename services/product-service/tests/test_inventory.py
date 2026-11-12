import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Product
from app.reservation_models import InventoryReservation
from app.reservations import ReservationRequest, reserve, transition, require_internal


class InventoryTests(unittest.TestCase):
    database_url = "sqlite://"

    def setUp(self):
        self.engine = create_engine(self.database_url)
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False)
        with self.sessions() as db:
            db.add_all([Product(id=i, seller_id=i + 10, name=f"Product {i}", description="Description",
                                category="Test", price=Decimal("12.50"), quantity=1) for i in (1, 2)])
            db.commit()
        self.sellers = patch("app.reservations.check_sellers")
        self.sellers.start()
        self.addCleanup(self.sellers.stop)
        self.addCleanup(self.engine.dispose)

    def data(self, key="test-key", buyer=10, items=None):
        return ReservationRequest(buyer_id=buyer, request_key=key,
                                  items=items or [{"product_id": 1, "quantity": 1}])

    def stock(self, product_id=1):
        with self.sessions() as db:
            return db.get(Product, product_id).quantity

    def test_retry_snapshot_conflict_release_and_confirm(self):
        with self.sessions() as db:
            first = reserve(self.data(), db)
        with self.sessions() as db:
            db.get(Product, 1).price = Decimal("20.00")
            db.commit()
        with self.sessions() as db:
            replay = reserve(self.data(), db)
        self.assertEqual(first, replay)
        self.assertEqual(replay["items"][0]["price"], "12.50")
        with self.sessions() as db, self.assertRaises(HTTPException) as error:
            reserve(self.data(items=[{"product_id": 2, "quantity": 1}]), db)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(self.stock(), 0)
        for _ in range(2):
            with self.sessions() as db:
                transition(db, 10, "test-key", "released")
        self.assertEqual(self.stock(), 1)
        with self.sessions() as db, self.assertRaises(HTTPException):
            transition(db, 10, "test-key", "confirmed")

    def test_batch_failure_rolls_back_all_products_and_key(self):
        with self.sessions() as db, self.assertRaises(HTTPException):
            reserve(self.data(items=[{"product_id": 1, "quantity": 1}, {"product_id": 2, "quantity": 2}]), db)
        self.assertEqual((self.stock(1), self.stock(2)), (1, 1))
        with self.sessions() as db:
            self.assertIsNone(db.scalar(select(InventoryReservation)))

    def test_suspended_seller_rolls_back(self):
        with patch("app.reservations.check_sellers", side_effect=HTTPException(409, "Seller suspended")):
            with self.sessions() as db, self.assertRaises(HTTPException):
                reserve(self.data(), db)
        self.assertEqual(self.stock(), 1)

    def test_hidden_product_rejected(self):
        with self.sessions() as db:
            db.get(Product, 1).status = "hidden"
            db.commit()
        with self.sessions() as db, self.assertRaises(HTTPException):
            reserve(self.data(), db)
        self.assertEqual(self.stock(), 1)

    def test_confirm_cannot_release_or_decrement_twice(self):
        with self.sessions() as db:
            reserve(self.data(), db)
        for _ in range(2):
            with self.sessions() as db:
                transition(db, 10, "test-key", "confirmed")
        with self.sessions() as db, self.assertRaises(HTTPException):
            transition(db, 10, "test-key", "released")
        self.assertEqual(self.stock(), 0)

    def test_internal_auth_fails_closed(self):
        with patch.dict(os.environ, {"INTERNAL_SERVICE_TOKEN": "test-secret"}):
            with self.assertRaises(HTTPException):
                require_internal("")
            require_internal("test-secret")
        with patch.dict(os.environ, {"INTERNAL_SERVICE_TOKEN": ""}):
            with self.assertRaises(HTTPException):
                require_internal("test-secret")


@unittest.skipUnless(os.getenv("INVENTORY_TEST_DATABASE_URL"), "Requires disposable MySQL *_test database")
class MySQLInventoryTests(InventoryTests):
    def setUp(self):
        self.database_url = os.environ["INVENTORY_TEST_DATABASE_URL"]
        from sqlalchemy.engine import make_url
        url = make_url(self.database_url)
        if url.get_backend_name() != "mysql" or not (url.database or "").endswith("_test"):
            raise RuntimeError("Concurrency tests require a disposable MySQL database ending in _test")
        super().setUp()

    def concurrent_reservations(self, same_key):
        import threading
        barrier = threading.Barrier(2)

        def attempt(index):
            barrier.wait(timeout=5)
            try:
                with self.sessions() as db:
                    reserve(self.data(key="same" if same_key else f"key-{index}", buyer=10 if same_key else index + 10), db)
                return 200
            except HTTPException as error:
                return error.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(attempt, range(2)))

    def test_two_buyers_last_item(self):
        self.assertEqual(sorted(self.concurrent_reservations(False)), [200, 409])
        self.assertEqual(self.stock(), 0)

    def test_same_key_simultaneous_retry(self):
        self.assertEqual(self.concurrent_reservations(True), [200, 200])
        self.assertEqual(self.stock(), 0)
