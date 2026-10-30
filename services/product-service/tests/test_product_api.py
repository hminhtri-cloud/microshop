"""HTTP/API tests use an isolated in-memory database; local MySQL is not modified."""
import json
import os
import socket
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

import uvicorn
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import Identity, get_identity
from app.database import Base, get_db
from app.main import app
from app.models import Product


class ProductApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        cls.sessions = sessionmaker(bind=cls.engine, autoflush=False)
        cls.engine_patch = patch("app.main.engine", cls.engine)
        cls.engine_patch.start()

        def test_db():
            with cls.sessions() as session:
                yield session

        cls.identity = Identity(1, "seller")
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
            raise RuntimeError("Product HTTP test server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=5)
        cls.listener.close()
        app.dependency_overrides.clear()
        cls.engine_patch.stop()
        cls.engine.dispose()

    def setUp(self):
        self.__class__.identity = Identity(1, "seller")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def request(self, method, path, payload=None):
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            method=method, headers={"Content-Type": "application/json"},
        )
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    @property
    def fields(self):
        return {
            "name": "USB-C Adapter", "description": "Bộ chuyển đổi dành cho máy tính xách tay",
            "category": "Phụ kiện", "price": "125000.00", "quantity": 12,
            "image_url": "https://example.com/adapter.png",
        }

    def create(self):
        return self.request("POST", "/seller/products", self.fields)

    def test_catalog_search_seller_ownership_and_visibility(self):
        self.assertEqual(self.request("GET", "/products")[1]["total"], 0)
        status, item = self.create()
        self.assertEqual(status, 201)
        self.assertEqual(item["seller_id"], 1)
        self.assertEqual(item["price"], "125000.00")
        self.assertEqual(self.request("GET", f"/products/{item['id']}")[0], 200)
        self.assertEqual(self.request("GET", "/products?search=usb&category=Ph%E1%BB%A5%20ki%E1%BB%87n")[1]["total"], 1)
        self.assertEqual(self.request("GET", "/products?search=not-found")[1]["total"], 0)
        self.assertEqual(self.request("GET", "/products?search=%25")[1]["total"], 0)
        self.assertEqual(self.request("GET", "/products?seller_id=2")[1]["total"], 0)
        self.assertEqual(self.request("GET", "/seller/products")[1]["total"], 1)

        self.__class__.identity = Identity(2, "seller")
        self.assertEqual(self.request("PUT", f"/seller/products/{item['id']}", self.fields)[0], 404)
        self.assertEqual(self.request("PATCH", f"/seller/products/{item['id']}/visibility", {"status": "hidden"})[0], 404)
        self.assertEqual(self.request("GET", "/seller/products")[1]["total"], 0)
        self.__class__.identity = Identity(1, "seller")
        self.assertEqual(self.request("PATCH", f"/seller/products/{item['id']}/visibility", {"status": "hidden"})[0], 200)
        self.assertEqual(self.request("GET", f"/products/{item['id']}")[0], 404)
        self.assertEqual(self.request("GET", "/products")[1]["total"], 0)
        self.assertEqual(self.request("GET", "/seller/products")[1]["total"], 1)
        updated = {**self.fields, "price": "99000.00", "quantity": 5}
        self.assertEqual(self.request("PUT", f"/seller/products/{item['id']}", updated)[1]["price"], "99000.00")
        self.assertEqual(self.request("PATCH", f"/seller/products/{item['id']}/visibility", {"status": "active"})[0], 200)
        self.assertEqual(self.request("GET", "/products")[1]["total"], 1)

    def test_admin_moderation_and_role_boundaries(self):
        _, product = self.create()
        self.__class__.identity = Identity(1, "customer")
        self.assertEqual(self.create()[0], 403)
        self.assertEqual(self.request("GET", "/seller/products")[0], 403)
        self.assertEqual(self.request("GET", "/admin/products")[0], 403)
        self.__class__.identity = Identity(9, "admin")
        self.assertEqual(self.create()[0], 403)
        self.assertEqual(self.request("GET", "/admin/products")[1]["total"], 1)
        self.assertEqual(self.request("PATCH", f"/admin/products/{product['id']}/visibility", {"status": "blocked"})[0], 200)
        self.assertEqual(self.request("GET", "/products")[1]["total"], 0)
        self.assertEqual(self.request("GET", "/admin/products")[1]["total"], 1)
        self.__class__.identity = Identity(1, "seller")
        self.assertEqual(self.request("PATCH", f"/seller/products/{product['id']}/visibility", {"status": "active"})[0], 409)
        self.assertEqual(self.request("PUT", f"/seller/products/{product['id']}", self.fields)[0], 409)
        self.__class__.identity = Identity(9, "admin")
        self.assertEqual(self.request("PATCH", f"/admin/products/{product['id']}/visibility", {"status": "active"})[0], 200)
        self.assertEqual(self.request("PATCH", "/admin/products/999/visibility", {"status": "active"})[0], 404)

    def test_validation_and_no_client_settable_seller_or_status(self):
        for extra in ({"seller_id": 99}, {"status": "active"}):
            self.assertEqual(self.request("POST", "/seller/products", {**self.fields, **extra})[0], 422)
        for update in (
            {**self.fields, "price": -1}, {**self.fields, "price": 1.231},
            {**self.fields, "price": 100.1}, {**self.fields, "quantity": -1},
            {**self.fields, "name": "   "}, {**self.fields, "image_url": "javascript:alert(1)"},
        ):
            self.assertEqual(self.request("POST", "/seller/products", update)[0], 422)
        self.assertEqual(self.request("GET", "/products?limit=101")[0], 422)
        self.assertEqual(self.request("GET", "/products?offset=-1")[0], 422)
        self.assertEqual(self.request("GET", "/products/999")[0], 404)

    def test_public_list_pagination(self):
        self.create()
        self.create()
        status, first = self.request("GET", "/products?limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(first["total"], 2)
        self.assertEqual(len(first["items"]), 1)
        _, second = self.request("GET", "/products?limit=1&offset=1")
        self.assertNotEqual(first["items"][0]["id"], second["items"][0]["id"])


if __name__ == "__main__":
    unittest.main()
