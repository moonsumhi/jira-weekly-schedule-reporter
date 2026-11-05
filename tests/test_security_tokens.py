import os
import unittest
from unittest.mock import patch

os.environ.setdefault("JIRA_BASE_URL", "https://jira.example.com")
os.environ.setdefault("JIRA_EMAIL", "test@example.com")
os.environ.setdefault("JIRA_API_TOKEN", "test-token")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-at-least-32-bytes")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("APP_DB_NAME", "test")

import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_token


class JwtSecurityTests(unittest.TestCase):
    def test_created_token_round_trips_subject(self) -> None:
        with (
            patch.object(settings, "JWT_SECRET_KEY", "test-jwt-secret-at-least-32-bytes"),
            patch.object(settings, "JWT_ALGORITHM", "HS256"),
        ):
            token = create_access_token("person@example.com")
            self.assertEqual(decode_token(token), "person@example.com")

    def test_decode_rejects_unconfigured_algorithm(self) -> None:
        token = jwt.encode(
            {"sub": "person@example.com"},
            "test-jwt-secret-at-least-32-bytes",
            algorithm="HS512",
        )
        with (
            patch.object(settings, "JWT_SECRET_KEY", "test-jwt-secret-at-least-32-bytes"),
            patch.object(settings, "JWT_ALGORITHM", "HS256"),
        ):
            self.assertIsNone(decode_token(token))

    def test_decode_rejects_non_string_subject(self) -> None:
        token = jwt.encode(
            {"sub": {"unexpected": "object"}},
            "test-jwt-secret-at-least-32-bytes",
            algorithm="HS256",
        )
        with (
            patch.object(settings, "JWT_SECRET_KEY", "test-jwt-secret-at-least-32-bytes"),
            patch.object(settings, "JWT_ALGORITHM", "HS256"),
        ):
            self.assertIsNone(decode_token(token))


if __name__ == "__main__":
    unittest.main()
