"""
백오피스(Admin) API 테스트

Covers:
  GET  /admin/users/pending
  POST /admin/users/{id}/approve
  POST /admin/users/{id}/reject
"""
import pytest


# ═══════════════════════════════════════════════════════════════
# GET /admin/users/pending
# ═══════════════════════════════════════════════════════════════

class TestListPendingUsers:
    def test_admin_can_list_all_pending(self, admin_client, pending_user_id):
        res = admin_client.get("/admin/users/pending")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        ids = [item["id"] for item in data]
        assert pending_user_id in ids

    def test_filter_by_pending_status(self, admin_client, pending_user_id, approved_user_id):
        res = admin_client.get("/admin/users/pending?status=PENDING")
        assert res.status_code == 200
        data = res.json()
        assert all(item["status"] == "PENDING" for item in data)
        assert pending_user_id in [item["id"] for item in data]
        assert approved_user_id not in [item["id"] for item in data]

    def test_filter_by_approved_status(self, admin_client, approved_user_id, pending_user_id):
        res = admin_client.get("/admin/users/pending?status=APPROVED")
        assert res.status_code == 200
        data = res.json()
        assert all(item["status"] == "APPROVED" for item in data)
        assert approved_user_id in [item["id"] for item in data]
        assert pending_user_id not in [item["id"] for item in data]

    def test_filter_by_rejected_status(self, admin_client, rejected_user_id, pending_user_id):
        res = admin_client.get("/admin/users/pending?status=REJECTED")
        assert res.status_code == 200
        data = res.json()
        assert all(item["status"] == "REJECTED" for item in data)
        assert rejected_user_id in [item["id"] for item in data]
        assert pending_user_id not in [item["id"] for item in data]

    def test_non_admin_gets_403(self, user_client):
        res = user_client.get("/admin/users/pending")
        assert res.status_code == 403

    def test_unauthenticated_gets_401(self, anon_client):
        res = anon_client.get("/admin/users/pending")
        assert res.status_code == 401

    def test_response_fields(self, admin_client, pending_user_id):
        res = admin_client.get("/admin/users/pending")
        assert res.status_code == 200
        item = next(i for i in res.json() if i["id"] == pending_user_id)
        assert "id" in item
        assert "email" in item
        assert "status" in item
        assert item["status"] == "PENDING"


# ═══════════════════════════════════════════════════════════════
# POST /admin/users/{id}/approve
# ═══════════════════════════════════════════════════════════════

class TestApproveUser:
    def test_admin_can_approve_pending_user(self, admin_client, pending_user_id):
        res = admin_client.post(f"/admin/users/{pending_user_id}/approve")
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "pending@test.com"
        assert "id" in data

    def test_approve_creates_user_in_users_collection(
        self, admin_client, pending_user_id, mock_mongo
    ):
        import asyncio, os
        admin_client.post(f"/admin/users/{pending_user_id}/approve")
        db = mock_mongo[os.environ["APP_DB_NAME"]]
        user = asyncio.get_event_loop().run_until_complete(
            db["users"].find_one({"email": "pending@test.com"})
        )
        assert user is not None
        assert user["email"] == "pending@test.com"
        assert user["is_admin"] is False
        assert user["approved_by"] == "admin@test.com"

    def test_approve_updates_pending_status(
        self, admin_client, pending_user_id, mock_mongo
    ):
        import asyncio, os
        from bson import ObjectId
        admin_client.post(f"/admin/users/{pending_user_id}/approve")
        db = mock_mongo[os.environ["APP_DB_NAME"]]
        doc = asyncio.get_event_loop().run_until_complete(
            db["pending_users"].find_one({"_id": ObjectId(pending_user_id)})
        )
        assert doc["status"] == "APPROVED"
        assert doc["reviewed_by"] == "admin@test.com"

    def test_approve_already_approved_returns_409(self, admin_client, approved_user_id):
        res = admin_client.post(f"/admin/users/{approved_user_id}/approve")
        assert res.status_code == 409

    def test_approve_rejected_user_returns_409(self, admin_client, rejected_user_id):
        res = admin_client.post(f"/admin/users/{rejected_user_id}/approve")
        assert res.status_code == 409

    def test_approve_nonexistent_id_returns_404(self, admin_client):
        from bson import ObjectId
        fake_id = str(ObjectId())
        res = admin_client.post(f"/admin/users/{fake_id}/approve")
        assert res.status_code == 404

    def test_approve_invalid_id_returns_400(self, admin_client):
        res = admin_client.post("/admin/users/not-an-objectid/approve")
        assert res.status_code == 400

    def test_non_admin_cannot_approve(self, user_client, pending_user_id):
        res = user_client.post(f"/admin/users/{pending_user_id}/approve")
        assert res.status_code == 403

    def test_duplicate_email_returns_409(self, admin_client, pending_user_id, mock_mongo):
        """Approving when email already exists in users collection returns 409."""
        import asyncio, os
        db = mock_mongo[os.environ["APP_DB_NAME"]]
        asyncio.get_event_loop().run_until_complete(
            db["users"].insert_one({"email": "pending@test.com", "hashed_password": "x"})
        )
        res = admin_client.post(f"/admin/users/{pending_user_id}/approve")
        assert res.status_code == 409


# ═══════════════════════════════════════════════════════════════
# POST /admin/users/{id}/reject
# ═══════════════════════════════════════════════════════════════

class TestRejectUser:
    def test_admin_can_reject_pending_user(self, admin_client, pending_user_id):
        res = admin_client.post(
            f"/admin/users/{pending_user_id}/reject",
            json={"reason": "Policy violation"},
        )
        assert res.status_code == 204

    def test_reject_updates_pending_status(
        self, admin_client, pending_user_id, mock_mongo
    ):
        import asyncio, os
        from bson import ObjectId
        admin_client.post(
            f"/admin/users/{pending_user_id}/reject",
            json={"reason": "Not eligible"},
        )
        db = mock_mongo[os.environ["APP_DB_NAME"]]
        doc = asyncio.get_event_loop().run_until_complete(
            db["pending_users"].find_one({"_id": ObjectId(pending_user_id)})
        )
        assert doc["status"] == "REJECTED"
        assert doc["reject_reason"] == "Not eligible"
        assert doc["reviewed_by"] == "admin@test.com"

    def test_reject_without_reason(self, admin_client, pending_user_id):
        res = admin_client.post(
            f"/admin/users/{pending_user_id}/reject",
            json={},
        )
        assert res.status_code == 204

    def test_reject_already_approved_returns_409(self, admin_client, approved_user_id):
        res = admin_client.post(
            f"/admin/users/{approved_user_id}/reject",
            json={"reason": "Mistake"},
        )
        assert res.status_code == 409

    def test_reject_already_rejected_returns_409(self, admin_client, rejected_user_id):
        res = admin_client.post(
            f"/admin/users/{rejected_user_id}/reject",
            json={"reason": "Again"},
        )
        assert res.status_code == 409

    def test_reject_nonexistent_id_returns_404(self, admin_client):
        from bson import ObjectId
        fake_id = str(ObjectId())
        res = admin_client.post(f"/admin/users/{fake_id}/reject", json={})
        assert res.status_code == 404

    def test_reject_invalid_id_returns_400(self, admin_client):
        res = admin_client.post("/admin/users/bad-id/reject", json={})
        assert res.status_code == 400

    def test_non_admin_cannot_reject(self, user_client, pending_user_id):
        res = user_client.post(
            f"/admin/users/{pending_user_id}/reject",
            json={"reason": "x"},
        )
        assert res.status_code == 403
