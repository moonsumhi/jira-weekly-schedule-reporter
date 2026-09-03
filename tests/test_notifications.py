import unittest
from datetime import datetime, timezone

from bson import ObjectId

from app.routers.notifications import _to_out


def notification_doc(notification_type: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": ObjectId(),
        "recipient_user_id": str(ObjectId()),
        "sender_user_id": None,
        "sender_name": None,
        "notification_type": notification_type,
        "title": "테스트 알림",
        "message": "테스트 메시지",
        "target_type": "SR",
        "target_id": str(ObjectId()),
        "target_url": "/pm/sr/test",
        "is_read": False,
        "read_at": None,
        "is_archived": False,
        "created_at": now,
        "updated_at": now,
    }


class NotificationOutputTests(unittest.TestCase):
    def test_requester_changed_notification_is_supported(self):
        result = _to_out(notification_doc("REQUESTER_CHANGED"))

        self.assertEqual(result.notification_type, "REQUESTER_CHANGED")

    def test_unknown_notification_type_falls_back_to_system(self):
        result = _to_out(notification_doc("FUTURE_NOTIFICATION_TYPE"))

        self.assertEqual(result.notification_type, "SYSTEM")


if __name__ == "__main__":
    unittest.main()
