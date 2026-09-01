import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import HTTPException

from app.db.mongo import MongoClientManager
from app.models.sr.service_request import SRRequesterChange
from app.models.user import UserPublic
from app.routers.sr.admin_requests import change_sr_requester


class ChangeSrRequesterTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_system_admin_can_change_requester(self):
        user = UserPublic(
            id=str(ObjectId()),
            email="operator@example.com",
            full_name="운영자",
            is_admin=False,
            permissions=["sr_manager"],
        )

        with self.assertRaises(HTTPException) as raised:
            await change_sr_requester(
                str(ObjectId()),
                SRRequesterChange(requester_id=str(ObjectId())),
                user,
            )

        self.assertEqual(raised.exception.status_code, 403)

    async def test_requester_snapshot_and_history_are_updated_together(self):
        sr_id = ObjectId()
        old_requester_id = ObjectId()
        new_requester_id = ObjectId()
        admin_id = ObjectId()
        admin = UserPublic(
            id=str(admin_id),
            email="admin@example.com",
            full_name="관리자",
            is_admin=True,
            permissions=[],
        )
        sr_doc = {
            "_id": sr_id,
            "title": "요청자 변경 테스트",
            "requester_id": old_requester_id,
            "requester_name": "기존 요청자",
            "requester_department": "기존 부서",
            "requester_email": "old@example.com",
        }
        new_user = {
            "_id": new_requester_id,
            "full_name": "새 요청자",
            "team": "새 부서",
            "email": "new@example.com",
        }

        users_col = SimpleNamespace(find_one=AsyncMock(return_value=new_user))
        service_col = SimpleNamespace(
            update_one=AsyncMock(return_value=SimpleNamespace(modified_count=1)),
            find_one=AsyncMock(),
        )
        updated_doc = {
            **sr_doc,
            "requester_id": new_requester_id,
            "requester_name": "새 요청자",
            "requester_department": "새 부서",
            "requester_email": "new@example.com",
        }
        service_col.find_one.return_value = updated_doc
        db = {MongoClientManager.SERVICE_REQUESTS: service_col}

        with (
            patch(
                "app.routers.sr.admin_requests.get_sr_or_404",
                AsyncMock(return_value=sr_doc),
            ),
            patch.object(MongoClientManager, "get_users_collection", return_value=users_col),
            patch.object(MongoClientManager, "get_db", return_value=db),
            patch(
                "app.routers.sr.admin_requests.record_sr_history",
                AsyncMock(),
            ) as record_history,
            patch(
                "app.routers.sr.admin_requests.create_notification",
                AsyncMock(),
            ) as create_notification,
            patch("app.routers.sr.admin_requests.sr_to_out", side_effect=lambda doc: doc),
            patch("app.routers.sr.admin_requests.SROut", side_effect=lambda **doc: doc),
        ):
            result = await change_sr_requester(
                str(sr_id),
                SRRequesterChange(requester_id=str(new_requester_id)),
                admin,
            )

        update = service_col.update_one.await_args.args[1]["$set"]
        self.assertEqual(update["requester_id"], new_requester_id)
        self.assertEqual(update["requester_name"], "새 요청자")
        self.assertEqual(update["requester_department"], "새 부서")
        self.assertEqual(update["requester_email"], "new@example.com")
        self.assertEqual(record_history.await_count, 4)
        self.assertEqual(
            create_notification.await_args.kwargs["recipient_user_id"],
            str(new_requester_id),
        )
        self.assertEqual(result["requester_id"], new_requester_id)


if __name__ == "__main__":
    unittest.main()
