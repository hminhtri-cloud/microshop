import os
import unittest
from unittest.mock import patch

from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from fastapi import HTTPException

from app.config import database_url


class ConfigTests(unittest.TestCase):
    def test_special_characters_in_password(self):
        environment = {
            "MYSQL_USER": "test_user",
            "MYSQL_PASSWORD": "p@ss:/word#%",
            "MYSQL_DATABASE": "test_db",
        }
        with patch.dict(os.environ, environment, clear=True):
            url = database_url()
        parsed = make_url(url.render_as_string(hide_password=False))
        self.assertEqual(parsed.password, environment["MYSQL_PASSWORD"])
        self.assertEqual(parsed.host, "mysql")
        self.assertEqual(parsed.port, 3306)

    def test_missing_configuration_fails_without_secret(self):
        with patch.dict(os.environ, {"MYSQL_PASSWORD": "private-value"}, clear=True):
            with self.assertRaises(RuntimeError) as result:
                database_url()
        self.assertIn("MYSQL_USER", str(result.exception))
        self.assertNotIn("private-value", str(result.exception))

    def test_explicit_url_override(self):
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite://"}, clear=True):
            self.assertEqual(database_url(), "sqlite://")


class ReadinessTests(unittest.TestCase):
    def test_ready_with_database(self):
        from app.main import readiness

        with patch("app.main.engine") as engine:
            self.assertEqual(readiness(), {"status": "ready"})
            engine.connect.return_value.__enter__.return_value.execute.assert_called_once()

    def test_database_failure_returns_503_without_connection_details(self):
        from app.main import readiness, health

        with patch("app.main.engine") as engine:
            engine.connect.side_effect = OperationalError("private-query", {}, Exception("secret"))
            with self.assertRaises(HTTPException) as result:
                readiness()
            self.assertEqual(result.exception.status_code, 503)
            self.assertEqual(result.exception.detail, "Database unavailable")
            self.assertEqual(health(), {"status": "healthy"})


if __name__ == "__main__":
    unittest.main()
