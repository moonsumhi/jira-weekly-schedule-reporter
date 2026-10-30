"""Space requests are recorded and selectable in the administrator audit log."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager
from app.middleware import activity_logger
from app.models.user import UserPublic
from app.routers import admin, spaces
from app.routers.auth import get_current_user


class SpacesAuditTests(unittest.IsolatedAsyncioTestCase):
    async def test_space_routes_record_successes_and_skip_failures(self):
        activity_logger._cache.clear()
        user = UserPublic(id=str(ObjectId()), email="admin@example.com", is_admin=True)
        logs = SimpleNamespace(insert_one=AsyncMock())
        app = FastAPI()
        app.include_router(spaces.router, prefix="/spaces")
        app.add_middleware(activity_logger.ActivityLoggerMiddleware)
        app.dependency_overrides[get_current_user] = lambda: user

        with patch.object(MongoClientManager, "get_activity_logs_collection", return_value=logs), \
             patch.object(activity_logger, "decode_token", return_value=user.email), \
             patch.object(spaces.service, "snapshot", AsyncMock(return_value={})), \
             patch.object(spaces.service, "save_entity", AsyncMock(return_value={"id": "p1"})), \
             patch.object(spaces.service, "delete_entity", AsyncMock(return_value={})), \
             patch.object(spaces.service, "save_plan", AsyncMock(return_value={"version": 1})), \
             patch.object(spaces.service, "publish_plan", AsyncMock(return_value={})), \
             patch.object(spaces.service, "assign", AsyncMock(return_value={})), \
             patch.object(spaces.service, "unassign", AsyncMock(side_effect=HTTPException(403))):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"Authorization": "Bearer test"}) as client:
                self.assertEqual((await client.get("/spaces")).status_code, 200)
                self.assertEqual((await client.get("/spaces")).status_code, 200)
                person = {"name": "홍길동", "teamId": "team1"}
                self.assertEqual((await client.post("/spaces/people?revision=0", json=person)).status_code, 201)
                self.assertEqual((await client.put("/spaces/people/p1?revision=1", json=person)).status_code, 200)
                self.assertEqual((await client.delete("/spaces/people/p1?revision=2")).status_code, 200)
                self.assertEqual((await client.put("/spaces/rooms/r1/plan", json={"version": 0})).status_code, 200)
                self.assertEqual((await client.post("/spaces/rooms/r1/plan/publish", json={"version": 1})).status_code, 200)
                self.assertEqual((await client.put("/spaces/seats/s1/assignment", json={"personId": "p1", "revision": 3})).status_code, 200)
                self.assertEqual((await client.delete("/spaces/seats/s1/assignment?revision=4")).status_code, 403)
                self.assertEqual((await client.post("/spaces/people?revision=0", json={})).status_code, 422)

        docs = [call.args[0] for call in logs.insert_one.await_args_list]
        self.assertEqual([doc["action"] for doc in docs], ["VIEW", "CREATE", "UPDATE", "DELETE", "UPDATE", "UPDATE", "UPDATE"])
        self.assertTrue(all(doc["category"] == "인적자원 관리" and doc["changed_by"] == user.email for doc in docs))
        self.assertEqual([doc["asset_id"] for doc in docs[2:]], ["p1", "p1", "r1", "r1", "s1"])
        self.assertIn({"path": "입력.name", "before": None, "after": "홍길동"}, docs[1]["diff"])
        self.assertIn({"path": "쿼리.revision", "before": None, "after": "2"}, docs[3]["diff"])

    async def test_admin_category_filter_includes_space_logs(self):
        queries = []

        class Collection:
            def find(self, query, *_args):
                queries.append(query)
                async def rows():
                    if query.get("category") == "인적자원 관리":
                        from datetime import datetime
                        yield {"_id": ObjectId(), "category": "인적자원 관리", "action": "UPDATE", "changed_at": datetime(2026, 1, 1), "changed_by": "admin@example.com"}
                return rows()

        user = UserPublic(id=str(ObjectId()), email="admin@example.com", is_admin=True)
        collection = Collection()
        with patch.object(MongoClientManager, "get_db", return_value={MongoClientManager.ACTIVITY_LOGS: collection}), \
             patch.object(MongoClientManager, "get_users_collection", return_value=collection):
            result = await admin.get_audit_log(page=1, page_size=50, actor=None, action=None, category="인적자원 관리", category_group=None, from_date=None, to_date=None, admin=user)
        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].category, "인적자원 관리")
        self.assertIn({"category": "인적자원 관리"}, queries)

    async def test_work_document_category_reads_history_and_activity(self):
        from datetime import datetime

        class Collection:
            def __init__(self, docs):
                self.docs = docs

            def find(self, query, *_args):
                async def rows():
                    for doc in self.docs:
                        if "category" not in query or query["category"] == doc.get("category"):
                            yield doc
                return rows()

        def doc(category=None):
            return {"_id": ObjectId(), "category": category, "action": "UPDATE", "changed_at": datetime(2026, 1, 1), "changed_by": "admin@example.com"}

        user = UserPublic(id=str(ObjectId()), email="admin@example.com", is_admin=True)
        db = {
            MongoClientManager.JOB_RESULTS_HISTORY: Collection([doc()]),
            MongoClientManager.ACTIVITY_LOGS: Collection([doc("작업결과서")]),
        }
        with patch.object(MongoClientManager, "get_db", return_value=db), \
             patch.object(MongoClientManager, "get_users_collection", return_value=Collection([])):
            result = await admin.get_audit_log(page=1, page_size=50, actor=None, action=None, category="작업결과서", category_group=None, from_date=None, to_date=None, admin=user)
        self.assertEqual(result.total, 2)
        self.assertEqual([item.category for item in result.items], ["작업결과서", "작업결과서"])
