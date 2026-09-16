import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from starlette.requests import Request
from starlette.responses import Response

from app.middleware import activity_logger as activity
from app.db.mongo import MongoClientManager
from app.models.sr.service_request import SRPatch
from app.models.user import UserPublic
from app.routers.sr import requests, admin_requests


class ActivityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        activity._cache.clear()

    async def log(self, method, path, status=200, token=True, payload=None):
        headers = [(b"authorization", b"Bearer test")] if token else []
        if payload is not None:
            headers.append((b"content-type", b"application/json"))
        scope = dict(type="http", method=method, path=path, query_string=b"",
                     headers=headers,
                     path_params={"sr_id": "target"})
        middleware = activity.ActivityLoggerMiddleware(None)
        request = Request(scope)
        if payload is not None:
            raw_body = json.dumps(payload).encode()

            async def receive():
                return {"type": "http.request", "body": raw_body, "more_body": False}

            request = Request(scope, receive)
        await middleware.dispatch(request, AsyncMock(return_value=Response(status_code=status)))

    async def test_mutations_are_not_deduplicated_and_failures_are_excluded(self):
        col = SimpleNamespace(insert_one=AsyncMock())
        with patch.object(MongoClientManager, "get_activity_logs_collection", return_value=col), patch.object(activity, "decode_token", return_value="user@example.com"):
            for path in ("/schedule/service-requests/abc", "/admin/schedule/service-requests/abc", "/pm/projects/abc/issues/def"):
                await self.log("PATCH", path)
                await self.log("PATCH", path)
                await self.log("PATCH", path, 403)
                await self.log("PATCH", path, 422)
                await self.log("PATCH", path, token=False)
            await self.log("POST", "/pm/projects", 201)
            await self.log("DELETE", "/pm/projects/abc", 204)
        docs = [c.args[0] for c in col.insert_one.await_args_list]
        self.assertEqual(len(docs), 8)
        self.assertEqual([d["action"] for d in docs[-2:]], ["CREATE", "DELETE"])
        self.assertEqual({d["category"] for d in docs}, {"SR", "스케줄 관리"})
        self.assertTrue(all(d["changed_by"] == "user@example.com" for d in docs))

    async def test_mutation_diff_contains_payload_and_redacts_secrets(self):
        col = SimpleNamespace(insert_one=AsyncMock())
        with patch.object(MongoClientManager, "get_activity_logs_collection", return_value=col), patch.object(activity, "decode_token", return_value="user@example.com"):
            await self.log(
                "PATCH", "/pm/projects/0123456789abcdef01234567/issues/abcdefabcdefabcdefabcdef",
                payload={"title": "SR 제목", "password": "do-not-store", "enabled": True},
            )
        diff = col.insert_one.await_args.args[0]["diff"]
        values = {item["path"]: item["after"] for item in diff}
        self.assertEqual(values["입력.title"], "SR 제목")
        self.assertEqual(values["입력.password"], "[REDACTED]")
        self.assertTrue(values["입력.enabled"])

    async def test_json_body_is_replayed_to_downstream_handler(self):
        col = SimpleNamespace(insert_one=AsyncMock())
        raw_body = json.dumps({"title": "SR 제목"}).encode()
        scope = dict(
            type="http", method="PATCH", path="/pm/projects/0123456789abcdef01234567/issues/abcdefabcdefabcdefabcdef",
            query_string=b"", headers=[(b"authorization", b"Bearer test"), (b"content-type", b"application/json")],
            path_params={"project_id": "0123456789abcdef01234567", "issue_id": "abcdefabcdefabcdefabcdef"},
        )

        async def receive():
            return {"type": "http.request", "body": raw_body, "more_body": False}

        seen = []

        async def downstream(request):
            seen.append(await request.body())
            return Response(status_code=200)

        with patch.object(MongoClientManager, "get_activity_logs_collection", return_value=col), patch.object(activity, "decode_token", return_value="user@example.com"):
            await activity.ActivityLoggerMiddleware(None).dispatch(Request(scope, receive), downstream)
        self.assertEqual(seen, [raw_body])

    async def test_views_deduplicate_but_polling_is_not_logged(self):
        col = SimpleNamespace(insert_one=AsyncMock())
        with patch.object(MongoClientManager, "get_activity_logs_collection", return_value=col), patch.object(activity, "decode_token", return_value="user@example.com"):
            for _ in range(2):
                await self.log("GET", "/schedule/service-requests")
                await self.log("GET", "/pm/projects")
                await self.log("GET", "/pm/projects/abc/issues/def/history")
        self.assertEqual(col.insert_one.await_count, 2)


class SrHistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_requester_and_admin_record_previously_omitted_fields(self):
        user = UserPublic(id=str(ObjectId()), email="admin@example.com", is_admin=True, permissions=[])
        before = dict(requester_id=user.id, status="SUBMITTED", title="same", attachments=[{"name": "old"}],
                      type_detail={"a": "old"}, compliance_related=True, reviewer_name="old")
        body = SRPatch(title="same", attachments=[], type_detail={"a": "new"}, compliance_related=False, reviewer_name="new")
        for module, handler in ((requests, requests.update_sr), (admin_requests, admin_requests.update_sr_admin)):
            col = SimpleNamespace(update_one=AsyncMock(), find_one=AsyncMock(return_value=before))
            with patch.object(module, "get_sr_or_404", AsyncMock(return_value=before)), patch.object(MongoClientManager, "get_db", return_value={MongoClientManager.SERVICE_REQUESTS: col}), patch.object(module, "record_sr_history", AsyncMock()) as history, patch.object(module, "sr_to_out", return_value={}), patch.object(module, "SROut", return_value=None):
                await handler(str(ObjectId()), body, user)
            fields = {call.args[1] for call in history.await_args_list}
            self.assertEqual(fields, {"FIELD_CHANGE:attachments", "FIELD_CHANGE:type_detail", "FIELD_CHANGE:compliance_related", "FIELD_CHANGE:reviewer_name"})

    async def test_due_date_collection_is_included_in_history(self):
        sr_id = str(ObjectId())
        now = datetime.now(timezone.utc)
        async def cursor(docs):
            for doc in docs:
                yield doc
        db = {key: SimpleNamespace(find=lambda q: cursor([])) for key in (MongoClientManager.SR_HISTORIES, MongoClientManager.SR_STATUS_HISTORIES)}
        db[MongoClientManager.SR_DUE_DATE_HISTORIES] = SimpleNamespace(find=lambda q: cursor([dict(_id=ObjectId(), new_due_date=now, changed_at=now, changed_by="user")]))
        with patch.object(requests, "get_sr_or_404", AsyncMock()), patch.object(MongoClientManager, "get_db", return_value=db):
            result = await requests.list_history(sr_id, None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].action_type, "FIELD_CHANGE:desired_due_date")
