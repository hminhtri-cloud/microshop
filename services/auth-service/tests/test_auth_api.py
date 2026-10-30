"""HTTP integration tests using an isolated SQLite database, never local MySQL."""
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
from fastapi import Depends
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.create_admin import create_admin
from app.dependencies import require_roles
from app.main import app
from app.models import User
from app.schemas import UserRegister
from app.security import ALGORITHM, AUDIENCE, ISSUER, password_context

TEST_SECRET = "integration-test-only-secret-not-for-deployment"


class AuthApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment = patch.dict(os.environ, {"JWT_SECRET": TEST_SECRET})
        cls.environment.start()
        cls.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        cls.sessions = sessionmaker(bind=cls.engine)
        cls.engine_patch = patch("app.main.engine", cls.engine)
        cls.engine_patch.start()

        def test_db():
            with cls.sessions() as session:
                yield session

        app.dependency_overrides[get_db] = test_db
        # Test-only route exercises the reusable role dependency.
        @app.get("/_test/admin")
        def admin(user=Depends(require_roles("admin"))):
            return {"id": user.id}

        cls.listener = socket.socket()
        cls.listener.bind(("127.0.0.1", 0))
        cls.base_url = f"http://127.0.0.1:{cls.listener.getsockname()[1]}"
        cls.server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        cls.thread = threading.Thread(
            target=cls.server.run, kwargs={"sockets": [cls.listener]}, daemon=True
        )
        cls.thread.start()
        for _ in range(100):
            if cls.server.started:
                break
            time.sleep(0.05)
        if not cls.server.started:
            raise RuntimeError("Test HTTP server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=5)
        cls.listener.close()
        app.dependency_overrides.clear()
        app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", "") != "/_test/admin"]
        cls.engine_patch.stop()
        cls.engine.dispose()
        cls.environment.stop()

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def request(self, path, payload=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers=headers,
        )
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def register(self):
        return self.request("/auth/register", {
            "username": "customer", "email": "customer@example.com", "password": "test-password-123"
        })

    def login(self):
        return self.request("/auth/login", {
            "email": "customer@example.com", "password": "test-password-123"
        })

    def test_register_login_me_and_hash(self):
        status, user = self.register()
        self.assertEqual(status, 201)
        self.assertEqual(user["role"], "customer")
        self.assertNotIn("hashed_password", user)
        with self.sessions() as db:
            saved = db.get(User, user["id"])
            self.assertNotEqual(saved.hashed_password, "test-password-123")
            self.assertTrue(password_context.verify("test-password-123", saved.hashed_password))
        status, token = self.login()
        self.assertEqual(status, 200)
        self.assertEqual(token["token_type"], "bearer")
        self.assertGreater(token["expires_in"], 0)
        status, me = self.request("/auth/me", token=token["access_token"])
        self.assertEqual(status, 200)
        self.assertEqual(me["id"], user["id"])
        self.assertNotIn("hashed_password", me)

    def test_duplicate_email_and_username(self):
        self.register()
        self.assertEqual(self.register()[0], 409)
        status, _ = self.request("/auth/register", {
            "username": "customer", "email": "different@example.com", "password": "test-password-123"
        })
        self.assertEqual(status, 409)

    def test_wrong_password_and_unknown_email_are_indistinguishable(self):
        self.register()
        wrong = self.request("/auth/login", {"email": "customer@example.com", "password": "wrong-password"})
        unknown = self.request("/auth/login", {"email": "unknown@example.com", "password": "wrong-password"})
        self.assertEqual(wrong, unknown)
        self.assertEqual(wrong[0], 401)

    def test_missing_invalid_expired_and_tampered_tokens(self):
        self.register()
        self.assertEqual(self.request("/auth/me")[0], 401)
        self.assertEqual(self.request("/auth/me", token="invalid")[0], 401)
        claims = {"sub": "1", "iat": int(time.time()) - 100, "exp": int(time.time()) - 10,
                  "iss": ISSUER, "aud": AUDIENCE}
        expired = jwt.encode(claims, TEST_SECRET, algorithm=ALGORITHM)
        self.assertEqual(self.request("/auth/me", token=expired)[0], 401)
        claims["exp"] = int(time.time()) + 3600
        tampered = jwt.encode(claims, "different-signing-secret", algorithm=ALGORITHM)
        self.assertEqual(self.request("/auth/me", token=tampered)[0], 401)

    def test_missing_claim_wrong_audience_and_deleted_user(self):
        self.register()
        claims = {"sub": "1", "iat": int(time.time()), "iss": ISSUER, "aud": AUDIENCE}
        missing_exp = jwt.encode(claims, TEST_SECRET, algorithm=ALGORITHM)
        self.assertEqual(self.request("/auth/me", token=missing_exp)[0], 401)
        claims.update(exp=int(time.time()) + 3600, aud="wrong-audience")
        wrong_audience = jwt.encode(claims, TEST_SECRET, algorithm=ALGORITHM)
        self.assertEqual(self.request("/auth/me", token=wrong_audience)[0], 401)
        _, token = self.login()
        with self.sessions() as db:
            db.query(User).delete()
            db.commit()
        self.assertEqual(self.request("/auth/me", token=token["access_token"])[0], 401)

    def test_role_gate_reads_current_database_role(self):
        self.register()
        _, response = self.login()
        token = response["access_token"]
        self.assertEqual(self.request("/_test/admin", token=token)[0], 403)
        with self.sessions() as db:
            user = db.query(User).first()
            user.role = "admin"
            db.commit()
        self.assertEqual(self.request("/_test/admin", token=token)[0], 200)
        with self.sessions() as db:
            user = db.query(User).first()
            user.role = "customer"
            db.commit()
        self.assertEqual(self.request("/_test/admin", token=token)[0], 403)

    def test_cannot_self_assign_admin_and_password_byte_limit(self):
        status, _ = self.request("/auth/register", {
            "username": "attacker", "email": "attacker@example.com",
            "password": "test-password-123", "role": "admin"
        })
        self.assertEqual(status, 422)
        status, _ = self.request("/auth/register", {
            "username": "unicode", "email": "unicode@example.com", "password": "ế" * 30
        })
        self.assertEqual(status, 422)
        self.assertEqual(self.request("/auth/login", {
            "email": "unicode@example.com", "password": "ế" * 30
        })[0], 422)

    def setup_seller_flow(self):
        self.register()
        _, customer = self.login()
        with self.sessions() as db:
            create_admin(db, UserRegister(
                username="administrator", email="admin@example.com", password="admin-test-password"
            ))
        status, admin = self.request("/auth/login", {
            "email": "admin@example.com", "password": "admin-test-password"
        })
        self.assertEqual(status, 200)
        return customer["access_token"], admin["access_token"]

    def submit_seller(self, token):
        return self.request("/seller/application", {
            "shop_name": "Demo Shop", "description": "Cua hang ban phu kien cong nghe"
        }, token=token)

    def review_seller(self, application_id, action, token):
        return self.request(f"/admin/seller-applications/{application_id}/review", {
            "action": action, "note": "Reviewed during integration test"
        }, token=token)

    def test_seller_approval_suspension_and_reactivation(self):
        customer, admin = self.setup_seller_flow()
        status, application = self.submit_seller(customer)
        self.assertEqual(status, 201)
        self.assertEqual(application["status"], "pending")
        self.assertEqual(self.request("/auth/me", token=customer)[1]["role"], "customer")
        self.assertEqual(self.request("/seller/profile", token=customer)[0], 403)

        status, approved = self.review_seller(application["id"], "approve", admin)
        self.assertEqual(status, 200)
        self.assertEqual(approved["status"], "approved")
        self.assertIsNotNone(approved["reviewed_by"])
        self.assertIsNotNone(approved["reviewed_at"])
        # Existing JWT reflects the new database role; no login required.
        self.assertEqual(self.request("/auth/me", token=customer)[1]["role"], "seller")
        self.assertEqual(self.request("/seller/profile", token=customer)[0], 200)
        self.assertEqual(self.review_seller(application["id"], "reject", admin)[0], 409)
        self.assertEqual(self.review_seller(application["id"], "approve", admin)[0], 409)

        self.assertEqual(self.review_seller(application["id"], "suspend", admin)[0], 200)
        self.assertEqual(self.request("/seller/profile", token=customer)[0], 403)
        self.assertEqual(self.request("/auth/me", token=customer)[1]["role"], "customer")
        self.assertEqual(self.submit_seller(customer)[0], 409)
        self.assertEqual(self.review_seller(application["id"], "approve", admin)[0], 200)
        self.assertEqual(self.request("/seller/profile", token=customer)[0], 200)

    def test_seller_rejection_and_resubmission(self):
        customer, admin = self.setup_seller_flow()
        _, application = self.submit_seller(customer)
        self.assertEqual(self.submit_seller(customer)[0], 409)
        self.assertEqual(self.review_seller(application["id"], "suspend", admin)[0], 409)
        status, rejected = self.review_seller(application["id"], "reject", admin)
        self.assertEqual(status, 200)
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(self.request("/auth/me", token=customer)[1]["role"], "customer")
        status, resubmitted = self.submit_seller(customer)
        self.assertEqual(status, 201)
        self.assertEqual(resubmitted["id"], application["id"])
        self.assertEqual(resubmitted["status"], "pending")
        self.assertIsNone(resubmitted["reviewed_by"])
        self.assertIsNone(resubmitted["review_note"])

    def test_seller_ownership_and_admin_authorization(self):
        customer, admin = self.setup_seller_flow()
        self.assertEqual(self.submit_seller(None)[0], 401)
        self.assertEqual(self.request("/seller/application", token=customer)[0], 404)
        _, application = self.submit_seller(customer)
        self.assertEqual(self.request("/seller/application", token=customer)[1]["id"], application["id"])
        self.assertEqual(self.request("/admin/seller-applications")[0], 401)
        self.assertEqual(self.request("/admin/seller-applications", token=customer)[0], 403)
        self.assertEqual(self.review_seller(application["id"], "approve", customer)[0], 403)
        self.assertEqual(self.submit_seller(admin)[0], 403)
        self.request("/auth/register", {
            "username": "otheruser", "email": "other@example.com", "password": "another-password"
        })
        _, other = self.request("/auth/login", {
            "email": "other@example.com", "password": "another-password"
        })
        self.assertEqual(self.request("/seller/application", token=other["access_token"])[0], 404)
        self.assertEqual(self.review_seller(application["id"], "approve", admin)[0], 200)
        self.assertEqual(self.request("/admin/seller-applications", token=customer)[0], 403)

    def test_admin_seller_list_filter_pagination_and_missing_application(self):
        customer, admin = self.setup_seller_flow()
        self.submit_seller(customer)
        status, page = self.request("/admin/seller-applications?status=pending&limit=1", token=admin)
        self.assertEqual(status, 200)
        self.assertEqual(page["total"], 1)
        self.assertEqual(len(page["items"]), 1)
        self.assertNotIn("hashed_password", page["items"][0])
        _, empty = self.request("/admin/seller-applications?status=approved", token=admin)
        self.assertEqual(empty["total"], 0)
        _, past_end = self.request("/admin/seller-applications?offset=1", token=admin)
        self.assertEqual(past_end["items"], [])
        self.assertEqual(past_end["total"], 1)
        self.assertEqual(self.request("/admin/seller-applications?limit=101", token=admin)[0], 422)
        self.assertEqual(self.request("/admin/seller-applications?status=anything", token=admin)[0], 422)
        self.assertEqual(self.review_seller(99999, "approve", admin)[0], 404)

    def test_seller_cannot_set_owner_status_or_submit_blank_data(self):
        customer, admin = self.setup_seller_flow()
        for extra in ({"user_id": 2}, {"status": "approved"}, {"role": "seller"}):
            status, _ = self.request("/seller/application", {
                "shop_name": "Demo Shop", "description": "A valid shop description", **extra
            }, token=customer)
            self.assertEqual(status, 422)
        self.assertEqual(self.request("/seller/application", {
            "shop_name": "   ", "description": "A valid shop description"
        }, token=customer)[0], 422)
        _, application = self.submit_seller(customer)
        self.assertEqual(self.request(f"/admin/seller-applications/{application['id']}/review", {
            "action": "approve", "note": "   "
        }, token=admin)[0], 422)

    def test_admin_bootstrap_never_promotes_existing_account(self):
        _, registered = self.register()
        with self.sessions() as db:
            with self.assertRaises(ValueError):
                create_admin(db, UserRegister(
                    username="differentname", email="customer@example.com", password="new-password-123"
                ))
            user = db.get(User, registered["id"])
            self.assertEqual(user.role, "customer")
            self.assertTrue(password_context.verify("test-password-123", user.hashed_password))


if __name__ == "__main__":
    unittest.main()
