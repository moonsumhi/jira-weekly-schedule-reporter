"""D-day 공개 범위와 작성 권한 회귀 테스트."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import HTTPException

from app.models.dday import DDayCreate, DDayPatch
from app.models.user import UserPublic
from app.routers.ddays import _audience_filter, _to_out, create_dday, list_dday_audience, patch_dday


def user(user_id: str, *, admin: bool = False, team: str | None = None) -> UserPublic:
    return UserPublic(id=user_id, email=f"{user_id}@example.com", is_admin=admin, team=team)


def matches(doc: dict, query: dict) -> bool:
    """Tests the small set of Mongo predicates used by the audience filter."""
    for key, value in query.items():
        if key == "$or":
            if not any(matches(doc, clause) for clause in value):
                return False
        elif key == "$and":
            if not all(matches(doc, clause) for clause in value):
                return False
        elif isinstance(value, dict) and "$exists" in value:
            if (key in doc) != value["$exists"]:
                return False
        elif isinstance(doc.get(key), list) and not isinstance(value, list):
            if value not in doc[key]:
                return False
        elif doc.get(key) != value:
            return False
    return True


class DDayVisibilityTests(unittest.TestCase):
    def test_private_is_creator_only_even_for_admin(self):
        private = {
            "created_by": "owner", "visible_to_all": False,
            "visible_user_ids": [], "visible_teams": [],
        }
        self.assertTrue(matches(private, _audience_filter(user("owner"))))
        self.assertFalse(matches(private, _audience_filter(user("other"))))
        self.assertFalse(matches(private, _audience_filter(user("admin", admin=True))))

    def test_shared_global_and_legacy_global(self):
        teammate = user("teammate", team="운영팀")
        shared = {"created_by": "owner", "visible_to_all": False,
                  "visible_user_ids": [], "visible_teams": ["운영팀"]}
        global_day = {"created_by": "owner", "visible_to_all": True,
                      "visible_user_ids": [], "visible_teams": []}
        legacy = {"created_by": "owner", "visible_user_ids": [], "visible_teams": []}
        self.assertTrue(matches(shared, _audience_filter(teammate)))
        self.assertFalse(matches(shared, _audience_filter(user("other"))))
        self.assertTrue(matches(global_day, _audience_filter(user("other"))))
        self.assertTrue(matches(legacy, _audience_filter(user("other"))))
        self.assertTrue(_to_out({"_id": ObjectId(), **legacy}).visible_to_all)


class DDayPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_audience_list_is_limited_to_own_team_for_regular_user(self):
        collection = SimpleNamespace(find=unittest.mock.MagicMock())
        cursor = unittest.mock.MagicMock()
        cursor.sort.return_value = cursor
        cursor.__aiter__.return_value = []
        collection.find.return_value = cursor
        with patch("app.routers.ddays.MongoClientManager.get_users_collection", return_value=collection):
            await list_dday_audience(user("owner", team="운영팀"))
        self.assertEqual(collection.find.call_args.args[0]["$and"][1], {"team": "운영팀"})

    async def test_regular_user_cannot_target_another_team_or_its_member(self):
        with self.assertRaises(HTTPException) as team_error:
            await create_dday(
                DDayCreate(title="타팀 일정", date="2026-10-08", visible_teams=["개발팀"]),
                user("owner", team="운영팀"),
            )
        self.assertEqual(team_error.exception.status_code, 403)
        collection = SimpleNamespace(find=unittest.mock.MagicMock())
        cursor = unittest.mock.MagicMock()
        cursor.__aiter__.return_value = [{"_id": "teammate"}]
        collection.find.return_value = cursor
        with patch("app.routers.ddays.MongoClientManager.get_users_collection", return_value=collection):
            with self.assertRaises(HTTPException) as member_error:
                await create_dday(
                    DDayCreate(title="타팀 일정", date="2026-10-08", visible_user_ids=["other"]),
                    user("owner", team="운영팀"),
                )
        self.assertEqual(member_error.exception.status_code, 403)

    async def test_regular_user_can_create_private_day(self):
        collection = SimpleNamespace(insert_one=AsyncMock(return_value=SimpleNamespace(inserted_id=ObjectId())))
        with patch("app.routers.ddays.MongoClientManager.get_ddays_collection", return_value=collection):
            result = await create_dday(DDayCreate(title="개인 일정", date="2026-10-08"), user("owner"))
        self.assertFalse(result.visible_to_all)
        self.assertEqual(result.created_by, "owner")

    async def test_regular_user_cannot_create_global_or_inspection_day(self):
        for title, global_day in (("전체 일정", True), ("서버 점검일 2026-10", False)):
            with self.subTest(title=title), self.assertRaises(HTTPException) as error:
                await create_dday(DDayCreate(title=title, date="2026-10-08", visible_to_all=global_day), user("owner"))
            self.assertEqual(error.exception.status_code, 403)

    async def test_regular_user_cannot_edit_other_day_or_make_own_day_global(self):
        day_id = str(ObjectId())
        collection = SimpleNamespace(find_one=AsyncMock(return_value={"created_by": "owner", "title": "개인 일정"}))
        with patch("app.routers.ddays.MongoClientManager.get_ddays_collection", return_value=collection):
            with self.assertRaises(HTTPException) as other_error:
                await patch_dday(day_id, DDayPatch(title="변경"), user("other"))
            with self.assertRaises(HTTPException) as global_error:
                await patch_dday(day_id, DDayPatch(visible_to_all=True), user("owner"))
        self.assertEqual(other_error.exception.status_code, 403)
        self.assertEqual(global_error.exception.status_code, 403)
