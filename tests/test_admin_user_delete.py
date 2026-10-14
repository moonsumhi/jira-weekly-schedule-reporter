import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from app.db.mongo import MongoClientManager
from app.models.user import UserPublic
from app.routers.admin import delete_user
from app.services.pm.issue_service import assignee_display_name


class AsyncRows:
    def __init__(self, rows):
        self.rows = rows

    def __aiter__(self):
        self.iterator = iter(self.rows)
        return self

    async def __anext__(self):
        try:
            return next(self.iterator)
        except StopIteration:
            raise StopAsyncIteration


class DeleteUserTests(unittest.IsolatedAsyncioTestCase):
    async def test_deletion_keeps_assignee_names_and_records_history(self):
        user_id, admin_id, issue_id, sr_id = (ObjectId() for _ in range(4))
        admin = UserPublic(
            id=str(admin_id), email="admin@example.com", full_name="관리자",
            is_admin=True, permissions=[],
        )
        users = SimpleNamespace(
            find_one=AsyncMock(return_value={
                "_id": user_id, "email": "former@example.com", "full_name": "김담당",
            }),
            delete_one=AsyncMock(),
        )
        issues = SimpleNamespace(
            find=lambda *_args: AsyncRows([{"_id": issue_id}]),
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
        )
        srs = SimpleNamespace(
            find=lambda *_args: AsyncRows([{"_id": sr_id, "assignee_name": "김담당"}]),
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
        )
        history = SimpleNamespace(update_many=AsyncMock())
        members = SimpleNamespace(delete_many=AsyncMock())

        with (
            patch.object(MongoClientManager, "get_users_collection", return_value=users),
            patch.object(MongoClientManager, "get_pm_issues_collection", return_value=issues),
            patch.object(MongoClientManager, "get_pm_issue_history_collection", return_value=history),
            patch.object(MongoClientManager, "get_pm_org_members_collection", return_value=members),
            patch.object(MongoClientManager, "get_pm_project_members_collection", return_value=members),
            patch.object(MongoClientManager, "get_db", return_value={MongoClientManager.SERVICE_REQUESTS: srs}),
            patch("app.services.pm.issue_service.record_history", new_callable=AsyncMock) as pm_history,
            patch("app.services.sr.sr_service.record_sr_history", new_callable=AsyncMock) as sr_history,
        ):
            await delete_user(str(user_id), admin)

        self.assertEqual(issues.update_one.await_args.args[0]["assignee_id"], user_id)
        self.assertEqual(issues.update_one.await_args.args[1]["$set"], {"assignee_name_snapshot": "김담당"})
        self.assertEqual(srs.update_one.await_args.args[1]["$set"], {"assignee_name": "김담당 (삭제된 회원)"})
        pm_history.assert_awaited_once_with(issue_id, admin_id, "assignee_id", "김담당", "김담당 (삭제된 회원)")
        sr_history.assert_awaited_once_with(str(sr_id), "ASSIGNEE_CHANGE", "김담당", "김담당 (삭제된 회원)", "관리자")
        history.update_many.assert_awaited_once()
        users.delete_one.assert_awaited_once_with({"_id": user_id})

    def test_deleted_assignee_uses_snapshot_without_selecting_another_user(self):
        issue = {"assignee_id": ObjectId(), "assignee_name_snapshot": "김담당"}
        self.assertEqual(assignee_display_name(issue, None), "김담당 (삭제된 회원)")
        self.assertEqual(assignee_display_name(issue, {"full_name": "새 담당자"}), "새 담당자")
