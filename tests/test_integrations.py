import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException, Response


_TEST_ENV = {
    "JIRA_BASE_URL": "https://jira.example.com",
    "JIRA_EMAIL": "test@example.com",
    "JIRA_API_TOKEN": "test-token",
    "MONGO_URI": "mongodb://localhost:27017",
    "JWT_SECRET_KEY": "test-jwt-secret",
    "JWT_ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "APP_DB_NAME": "test",
}
for key, value in _TEST_ENV.items():
    os.environ.setdefault(key, value)


from app.core.config import settings  # noqa: E402
from app.db.mongo import MongoClientManager  # noqa: E402
from app.routers.integrations import (  # noqa: E402
    list_incident_notification_recipients,
    require_incident_notify_api_key,
)


class _FakeCollection:
    async def find_one(self, query: dict) -> dict:
        return {
            "key": query["key"],
            "items": [
                {"label": "비활성", "value": "disabled@example.com", "sort_order": 0, "is_active": False},
                {"label": "김철수", "value": "kim@example.com", "sort_order": 2, "is_active": True},
                {"label": "홍길동", "value": "hong@example.com", "sort_order": 1, "is_active": True},
                {"label": "중복", "value": "HONG@example.com", "sort_order": 3, "is_active": True},
                {"label": "메일 없음", "value": "", "sort_order": 4, "is_active": True},
            ],
        }


class IncidentNotificationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_key_is_required(self) -> None:
        with patch.object(settings, "INCIDENT_NOTIFY_API_KEY", "expected-key"):
            with self.assertRaises(HTTPException) as context:
                await require_incident_notify_api_key("wrong-key")

        self.assertEqual(context.exception.status_code, 401)

    async def test_unconfigured_api_returns_service_unavailable(self) -> None:
        with patch.object(settings, "INCIDENT_NOTIFY_API_KEY", ""):
            with self.assertRaises(HTTPException) as context:
                await require_incident_notify_api_key("any-key")

        self.assertEqual(context.exception.status_code, 503)

    async def test_returns_only_active_unique_recipients_in_order(self) -> None:
        response = Response()
        with patch.object(
            MongoClientManager,
            "get_env_categories_collection",
            return_value=_FakeCollection(),
        ):
            result = await list_incident_notification_recipients(response)

        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(result.count, 2)
        self.assertEqual(
            [recipient.model_dump() for recipient in result.recipients],
            [
                {"name": "홍길동", "email": "hong@example.com"},
                {"name": "김철수", "email": "kim@example.com"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
