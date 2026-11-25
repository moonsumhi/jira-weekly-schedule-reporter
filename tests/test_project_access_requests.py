"""Project catalog and membership request flow against isolated MongoDB collections."""
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.pm.projects import router


@unittest.skipUnless(os.environ.get("WORK_DOCUMENT_TEST_MONGO") == "1", "Requires isolated MongoDB test run")
class ProjectAccessRequestTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.real_db = M.get_db()
        prefix = "test_project_access_" + uuid4().hex + "_"
        self.names = set()

        class TestDB:
            def __getitem__(_, name):
                self.names.add(prefix + name)
                return self.real_db[prefix + name]

        self.db_patch = patch.object(M, "get_db", return_value=TestDB())
        self.db_patch.start()
        self.member = UserPublic(id=str(ObjectId()), email="member@example.com")
        self.app = FastAPI()
        self.app.include_router(router, prefix="/pm/projects")
        self.app.dependency_overrides[get_current_user] = lambda: self.member
        self.client = AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test")
        self.project_id = ObjectId()
        now = datetime.now(timezone.utc)
        await M.get_pm_projects_collection().insert_one({
            "_id": self.project_id, "org_id": ObjectId(), "name": "Private project",
            "key": "PRIVATE", "description": "internal detail", "created_at": now,
            "updated_at": now,
        })
        await M.get_users_collection().insert_one({
            "_id": ObjectId(self.member.id), "email": self.member.email, "full_name": "Applicant",
        })

    async def asyncTearDown(self):
        await self.client.aclose()
        for name in self.names:
            await self.real_db.drop_collection(name)
        self.db_patch.stop()
        M.get_client().close()
        M._client = None

    async def test_catalog_request_and_approval(self):
        pid = str(self.project_id)
        catalog = (await self.client.get("/pm/projects")).json()
        self.assertEqual(catalog[0]["name"], "Private project")
        self.assertFalse(catalog[0]["has_access"])
        self.assertIsNone(catalog[0]["description"])
        self.assertEqual((await self.client.get(f"/pm/projects/{pid}")).status_code, 403)
        self.assertEqual((await self.client.get(f"/pm/projects/{pid}/members")).status_code, 403)

        requested = await self.client.post(f"/pm/projects/{pid}/access-requests")
        self.assertEqual(requested.status_code, 200, requested.text)
        request_id = requested.json()["id"]
        repeated = await self.client.post(f"/pm/projects/{pid}/access-requests")
        self.assertEqual(repeated.json()["id"], request_id)
        self.assertEqual((await self.client.get("/pm/projects")).json()[0]["access_request_status"], "PENDING")
        self.assertEqual((await self.client.get(f"/pm/projects/{pid}/access-requests")).status_code, 403)

        admin = UserPublic(id=str(ObjectId()), email="admin@example.com", is_admin=True)
        self.app.dependency_overrides[get_current_user] = lambda: admin
        pending = await self.client.get(f"/pm/projects/{pid}/access-requests")
        self.assertEqual(len(pending.json()), 1)
        approved = await self.client.post(f"/pm/projects/{pid}/access-requests/{request_id}/approve")
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["role"], "VIEWER")
        self.app.dependency_overrides[get_current_user] = lambda: self.member
        self.assertTrue((await self.client.get("/pm/projects")).json()[0]["has_access"])
        self.assertEqual((await self.client.get(f"/pm/projects/{pid}")).status_code, 200)
