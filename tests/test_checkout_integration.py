"""Real HTTP between three processes; temporary SQLite DBs, no existing data.

Run in a venv with Auth + Order requirements installed:
    python -m unittest discover -s tests -v
MySQL locking is tested separately by the service concurrency suites in CI.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]


class CheckoutIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="microshop-integration-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.urls = {}
        cls.envs = {}
        cls.processes = []
        cls.addClassCleanup(cls.stop_services)
        for name in ("auth", "product", "order"):
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            cls.urls[name] = f"http://127.0.0.1:{port}"
            cls.envs[name] = {**os.environ, "DATABASE_URL": f"sqlite:///{cls.temp.name}/{name}.db",
                              "JWT_SECRET": "integration-only-jwt-secret-at-least-32-bytes",
                              "INTERNAL_SERVICE_TOKEN": "integration-only-service-token",
                              "PYTHONPATH": str(ROOT / "services" / f"{name}-service")}
        for name in cls.envs:
            cls.envs[name].update(AUTH_SERVICE_URL=cls.urls["auth"], PRODUCT_SERVICE_URL=cls.urls["product"])
        # Bootstrap an admin only in the temporary auth DB, never through a public API.
        subprocess.run([sys.executable, "-c", "\n".join([
            "from app.database import Base, engine, SessionLocal",
            "from app.models import User",
            "from app.security import password_context",
            "Base.metadata.create_all(engine)",
            "with SessionLocal() as db:",
            "    db.add(User(username='testadmin', email='admin@example.com', role='admin', hashed_password=password_context.hash('Password123!')))",
            "    db.commit()",
        ])], env=cls.envs["auth"], check=True, timeout=30)
        for name in cls.envs:
            port = cls.urls[name].rsplit(":", 1)[1]
            process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                        "--port", port, "--log-level", "error"], env=cls.envs[name],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cls.processes.append(process)
            for _ in range(100):
                try:
                    with urlopen(cls.urls[name] + "/ready", timeout=1):
                        break
                except (URLError, TimeoutError):
                    if process.poll() is not None:
                        raise RuntimeError(f"{name} exited during startup")
                    time.sleep(0.1)
            else:
                raise RuntimeError(f"{name} did not become ready")

    @classmethod
    def stop_services(cls):
        for process in reversed(cls.processes):
            process.terminate()
        for process in cls.processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def request(self, service, method, path, body=None, token=None, key=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if key:
            headers["Idempotency-Key"] = key
        req = Request(self.urls[service] + path, method=method, headers=headers,
                      data=json.dumps(body).encode() if body is not None else None)
        try:
            response = urlopen(req, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def login(self, email):
        status, result = self.request("auth", "POST", "/auth/login", {"email": email, "password": "Password123!"})
        self.assertEqual(status, 200, result)
        return result["access_token"]

    def register(self, name):
        status, result = self.request("auth", "POST", "/auth/register", {
            "username": name, "email": name + "@example.com", "password": "Password123!"})
        self.assertEqual(status, 201, result)
        return self.login(name + "@example.com")

    def test_full_checkout_with_real_auth_product_order(self):
        admin = self.login("admin@example.com")
        buyer = self.register("buyer")
        products = []
        applications = []
        for name in ("sellerone", "sellertwo"):
            seller = self.register(name)
            status, application = self.request("auth", "POST", "/seller/application",
                                               {"shop_name": name, "description": "Integration test shop"}, seller)
            self.assertEqual(status, 201, application)
            applications.append(application)
            status, result = self.request("auth", "POST", f'/admin/seller-applications/{application["id"]}/review',
                                          {"action": "approve", "note": "Integration approval"}, admin)
            self.assertEqual(status, 200, result)
            status, product = self.request("product", "POST", "/seller/products", {
                "name": name + " item", "description": "Integration test product", "category": "Test",
                "price": "125000.00", "quantity": 3}, seller)
            self.assertEqual(status, 201, product)
            products.append(product)
        body = {"items": [{"product_id": p["id"], "quantity": 1} for p in products],
                "shipping": {"receiver_name": "Test Buyer", "phone": "0912345678", "address": "123 Integration Street"}}
        key = str(uuid4())
        status, order = self.request("order", "POST", "/orders", body, buyer, key)
        self.assertEqual(status, 201, order)
        self.assertEqual(order["total_amount"], "250000.00")
        self.assertEqual(len(order["seller_orders"]), 2)
        self.assertEqual(self.request("order", "POST", "/orders", body, buyer, key)[0], 200)
        for product in products:
            self.assertEqual(self.request("product", "GET", f'/products/{product["id"]}')[1]["quantity"], 2)
        status, cancelled = self.request("order", "POST", f'/orders/{order["id"]}/cancel', {}, buyer)
        self.assertEqual((status, cancelled["status"]), (200, "cancelled"))
        for product in products:
            self.assertEqual(self.request("product", "GET", f'/products/{product["id"]}')[1]["quantity"], 3)
        status, order = self.request("order", "POST", "/orders", body, buyer, str(uuid4()))
        self.assertEqual(status, 201, order)
        status, paid = self.request("order", "POST", f'/orders/{order["id"]}/mock-payment', {"outcome": "success"}, buyer)
        self.assertEqual((status, paid["payment_status"]), (200, "paid"))
        # Suspension is checked server-to-server, not merely via product.active.
        application = applications[0]
        self.assertEqual(self.request("auth", "POST", f'/admin/seller-applications/{application["id"]}/review',
                                     {"action": "suspend", "note": "Integration suspension"}, admin)[0], 200)
        status, error = self.request("order", "POST", "/orders", body, buyer, str(uuid4()))
        self.assertEqual((status, error["code"]), (409, "SELLER_NOT_APPROVED"))
        self.assertEqual(self.request("order", "POST", "/orders", body, key=str(uuid4()))[0], 401)
        self.assertEqual(self.request("product", "POST", "/internal/stock/reservations", {})[0], 403)
        self.assertEqual(self.request("auth", "POST", "/internal/sellers/eligibility", {})[0], 403)
