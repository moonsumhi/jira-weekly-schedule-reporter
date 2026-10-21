"""Space integration tests: disposable collections, real Mongo CAS and HTTP permissions."""
import asyncio
import os
import unittest
from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db.mongo import MongoClientManager as M
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.routers.spaces import router
from app.services import spaces as svc


@unittest.skipUnless(
    os.getenv("WORK_DOCUMENT_TEST_MONGO") == "1", "Explicit isolated Mongo tests only"
)
class SpaceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        M._client = None
        self.db = M.get_db()
        self.prefix = "test_spaces_" + uuid4().hex + "_"
        self.names = set()

        class TestDB:
            def __getitem__(_, name):
                full = self.prefix + name
                self.names.add(full)
                return self.db[full]

        self.db_patch = patch.object(M, "get_db", return_value=TestDB())
        self.db_patch.start()
        self.admin = UserPublic(
            id=str(ObjectId()), email="admin@spaces.example.com", is_admin=True
        )
        self.user = self.admin
        self.team_user = UserPublic(
            id=str(ObjectId()),
            email="team@spaces.example.com",
            team="데이터운영팀",
            permissions=["spaces"],
        )
        self.manager = UserPublic(
            id=str(ObjectId()), email="room@spaces.example.com", permissions=["spaces"]
        )
        self.viewer = UserPublic(
            id=str(ObjectId()),
            email="viewer@spaces.example.com",
            permissions=["spaces"],
        )
        for user in [self.admin, self.team_user, self.manager, self.viewer]:
            await M.get_users_collection().insert_one(
                {"_id": ObjectId(user.id), "email": user.email, "team": user.team}
            )
        app = FastAPI()
        app.include_router(router, prefix="/spaces")
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )
        await svc.initialize()
        state = await svc.load()
        self.t1, self.t2 = state["teams"][:2]
        self.t1["manager_ids"] = [self.team_user.id]
        await M.get_db()[svc.REGISTRY].replace_one({"_id": "directory"}, state)
        self.b = await self.create("buildings", {"name": "본관"})
        self.f = await self.create("floors", {"name": "7층", "buildingId": self.b})
        self.r = await self.create(
            "rooms",
            {
                "name": "701호",
                "floorId": self.f,
                "teamIds": [self.t1["id"], self.t2["id"]],
                "managerIds": [self.manager.id],
            },
        )
        self.r2 = await self.create(
            "rooms", {"name": "702호", "floorId": self.f, "teamIds": [self.t1["id"]]}
        )
        self.p = await self.create(
            "people", {"name": "홍길동", "teamId": self.t1["id"], "roomId": self.r}
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        for name in self.names:
            await self.db.drop_collection(name)
        self.db_patch.stop()
        M.get_client().close()
        M._client = None

    async def revision(self):
        return (await svc.load())["revision"]

    async def create(self, kind, data):
        res = await self.client.post(
            f"/spaces/{kind}", params={"revision": await self.revision()}, json=data
        )
        self.assertEqual(res.status_code, 201, res.text)
        return res.json()["id"]

    def plan(self, version=0):
        return {
            "version": version,
            "width": 1600,
            "height": 1000,
            "objects": [
                {
                    "id": "wall-1",
                    "kind": "wall",
                    "x": 10,
                    "y": 10,
                    "width": 400,
                    "height": 8,
                },
                *[
                    {
                        "id": "desk-" + str(n),
                        "kind": "desk",
                        "x": 100 * n,
                        "y": 120,
                        "width": 100,
                        "height": 60,
                        "seatId": "seat-" + str(n),
                    }
                    for n in range(1, 4)
                ],
            ],
            "seats": [
                {
                    "id": "seat-" + str(n),
                    "number": f"A-0{n}",
                    "teamId": self.t1["id"] if n < 3 else self.t2["id"],
                }
                for n in range(1, 4)
            ],
        }

    async def save(self, data=None, room=None):
        res = await self.client.put(
            f"/spaces/rooms/{room or self.r}/plan", json=data or self.plan()
        )
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()["version"]

    async def publish(self, version=1, room=None):
        res = await self.client.post(
            f"/spaces/rooms/{room or self.r}/plan/publish", json={"version": version}
        )
        self.assertEqual(res.status_code, 200, res.text)

    async def assign(self, seat="seat-1", person=None, status=200):
        res = await self.client.put(
            f"/spaces/seats/{seat}/assignment",
            json={"personId": person or self.p, "revision": await self.revision()},
        )
        self.assertEqual(res.status_code, status, res.text)

    async def test_empty_plan_save_reload_and_publish(self):
        blank = (
            await self.client.get(
                f"/spaces/rooms/{self.r}/plan", params={"draft": True}
            )
        ).json()
        self.assertEqual(blank["objects"], [])
        await self.save()
        self.user = self.viewer
        self.assertEqual(
            (await self.client.get(f"/spaces/rooms/{self.r}/plan")).json()["objects"],
            [],
        )
        draft = (await self.client.get(f"/spaces/rooms/{self.r}/plan?draft=true")).json()
        self.assertEqual(len(draft["objects"]), 4)
        self.assertTrue(draft["has_draft"])
        self.assertEqual((await self.client.get("/spaces")).json()["seats"], [])
        self.user = self.admin
        await self.publish()
        self.user = self.viewer
        published = (await self.client.get(f"/spaces/rooms/{self.r}/plan")).json()
        self.assertEqual(len(published["objects"]), 4)
        self.assertEqual(published["seats"][0]["number"], "A-01")

    async def test_draft_move_preserves_published_and_assignment(self):
        await self.save()
        await self.publish()
        await self.assign()
        changed = self.plan(2)
        changed["objects"][1]["x"] = 650
        await self.save(changed)
        published = (await self.client.get(f"/spaces/rooms/{self.r}/plan")).json()
        self.assertEqual(published["objects"][1]["x"], 100)
        await self.publish(3)
        self.assertEqual((await svc.load())["assignments"][0]["person_id"], self.p)
        self.assertEqual(
            (await self.client.get(f"/spaces/rooms/{self.r}/plan")).json()["objects"][
                1
            ]["x"],
            650,
        )

    async def test_move_person_is_atomic_and_no_plan_edit(self):
        await self.save()
        await self.publish()
        await self.assign()
        before = deepcopy((await svc.load())["plans"])
        await self.assign("seat-2")
        state = await svc.load()
        self.assertEqual(len(state["assignments"]), 1)
        self.assertEqual(state["assignments"][0]["seat_id"], "seat-2")
        self.assertEqual(before, state["plans"])

    async def test_shared_room_and_team_across_rooms(self):
        await self.save()
        await self.publish()
        state = (await self.client.get("/spaces")).json()
        self.assertEqual(len(state["rooms"][0]["team_ids"]), 2)
        self.assertEqual(sum(self.t1["id"] in r["team_ids"] for r in state["rooms"]), 2)
        self.assertEqual(len(state["plans"]), 1)

    async def test_menu_user_can_manage_other_team_and_geometry(self):
        await self.save()
        await self.publish()
        self.user = self.team_user
        await self.assign()
        # A different team remains a data constraint, not an authorization error.
        await self.assign("seat-3", status=422)
        person = await self.create("people", {"name": "다른 팀", "teamId": self.t2["id"]})
        await self.assign("seat-3", person)
        await self.save(self.plan(2))
        await self.publish(3)

    async def test_menu_user_can_assign_but_cannot_remove_occupied_seats(self):
        await self.save()
        await self.publish()
        await self.assign()
        self.user = self.manager
        await self.assign("seat-2")
        changed = self.plan(2)
        changed["objects"].pop(2)
        changed["seats"].pop(1)
        await self.save(changed)
        res = await self.client.post(
            f"/spaces/rooms/{self.r}/plan/publish", json={"version": 3}
        )
        self.assertEqual(res.status_code, 409)
        self.assertEqual(len((await svc.load())["seats"]), 3)
        self.assertEqual(len((await svc.load())["assignments"]), 1)

    async def test_clone_changes_ids_and_has_no_assignments(self):
        await self.save()
        await self.publish()
        await self.assign()
        res = await self.client.post(
            f"/spaces/rooms/{self.r}/plan/clone",
            json={"version": 2, "targetRoomId": self.r2},
        )
        self.assertEqual(res.status_code, 201, res.text)
        clone = (
            await self.client.get(f"/spaces/rooms/{self.r2}/plan?draft=true")
        ).json()
        self.assertTrue(
            all(
                o["id"] not in [x["id"] for x in self.plan()["objects"]]
                for o in clone["objects"]
            )
        )
        self.assertEqual(clone["objects"][1]["x"], 100)
        self.assertNotIn("seat-1", [s["id"] for s in clone["seats"]])
        await self.publish(1, self.r2)
        self.assertEqual(len((await svc.load())["assignments"]), 1)

    async def test_concurrent_edit_one_wins(self):
        results = await asyncio.gather(
            *[
                self.client.put(f"/spaces/rooms/{self.r}/plan", json=self.plan())
                for _ in range(2)
            ]
        )
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])
        self.assertEqual((await svc.load())["plans"][0]["version"], 1)

    async def test_concurrent_assignment_one_wins(self):
        await self.save()
        await self.publish()
        revision = await self.revision()
        results = await asyncio.gather(
            *[
                self.client.put(
                    f"/spaces/seats/seat-{i}/assignment",
                    json={"personId": self.p, "revision": revision},
                )
                for i in (1, 2)
            ]
        )
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])
        self.assertEqual(len((await svc.load())["assignments"]), 1)

    async def test_deactivation_releases_seat(self):
        await self.save()
        await self.publish()
        await self.assign()
        res = await self.client.put(
            f"/spaces/people/{self.p}",
            params={"revision": await self.revision()},
            json={"name": "홍길동", "teamId": self.t1["id"], "active": False},
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual((await svc.load())["assignments"], [])
        await self.assign(status=422)

    async def delete_person(self, person=None, status=200, revision=None):
        result = await self.client.delete(
            f"/spaces/people/{person or self.p}",
            params={"revision": await self.revision() if revision is None else revision},
        )
        self.assertEqual(result.status_code, status, result.text)
        return result

    async def test_delete_person_releases_only_their_seat_and_keeps_login_account(self):
        await self.save()
        await self.publish()
        result = await self.client.put(
            f"/spaces/people/{self.p}",
            params={"revision": await self.revision()},
            json={"name": "홍길동", "teamId": self.t1["id"], "roomId": self.r, "userId": self.viewer.id},
        )
        self.assertEqual(result.status_code, 200)
        await self.assign()
        person2 = await self.create("people", {"name": "둘째", "teamId": self.t1["id"]})
        await self.assign("seat-2", person2)
        before = await svc.load()
        account = await M.get_users_collection().find_one({"_id": ObjectId(self.viewer.id)})
        await self.delete_person()
        after = await svc.load()
        self.assertNotIn(self.p, [p["id"] for p in after["people"]])
        self.assertEqual(after["assignments"], [a for a in before["assignments"] if a["person_id"] == person2])
        for kind in ("seats", "plans", "rooms", "teams", "buildings", "floors"):
            self.assertEqual(after[kind], before[kind])
        self.assertEqual(await M.get_users_collection().find_one({"_id": ObjectId(self.viewer.id)}), account)
        # Removing the directory person also releases their optional account link.
        await self.create("people", {"name": "새 인원", "teamId": self.t1["id"], "userId": self.viewer.id})

    async def test_team_manager_can_delete_inactive_and_active_own_team_people(self):
        inactive = await self.create("people", {"name": "퇴사 인원", "teamId": self.t1["id"], "active": False})
        self.user = self.team_user
        await self.delete_person(inactive)
        await self.delete_person()
        self.assertEqual((await svc.load())["people"], [])

    async def test_menu_access_allows_person_deletion_without_scoped_roles(self):
        for user in (self.team_user, self.manager, self.viewer):
            with self.subTest(user=user.email):
                self.user = user
                person = await self.create("people", {"name": "다른 팀", "teamId": self.t2["id"]})
                await self.delete_person(person)
                self.assertNotIn(person, [p["id"] for p in (await svc.load())["people"]])

    async def test_person_deletion_releases_legacy_assignment_from_another_team(self):
        await self.save()
        await self.publish()
        state = await svc.load()
        state["assignments"].append({"id": "legacy", "seat_id": "seat-3", "person_id": self.p})
        await M.get_db()[svc.REGISTRY].replace_one({"_id": "directory"}, state)
        self.user = self.viewer
        await self.delete_person()
        after = await svc.load()
        self.assertEqual(after["assignments"], [])
        self.assertEqual(after["seats"], state["seats"])

    async def test_stale_person_delete_does_not_remove_changed_person(self):
        revision = await self.revision()
        result = await self.client.put(
            f"/spaces/people/{self.p}", params={"revision": revision},
            json={"name": "변경된 이름", "teamId": self.t1["id"]},
        )
        self.assertEqual(result.status_code, 200)
        before = await svc.load()
        await self.delete_person(status=409, revision=revision)
        self.assertEqual(await svc.load(), before)

    async def test_concurrent_person_delete_and_seat_assignment_one_wins(self):
        await self.save()
        await self.publish()
        revision = await self.revision()
        results = await asyncio.gather(
            self.client.delete(f"/spaces/people/{self.p}", params={"revision": revision}),
            self.client.put("/spaces/seats/seat-1/assignment", json={"personId": self.p, "revision": revision}),
        )
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])
        state = await svc.load()
        exists = any(p["id"] == self.p for p in state["people"])
        self.assertEqual(len(state["assignments"]), 1 if exists else 0)
        self.assertEqual(len(state["seats"]), 3)
        self.assertEqual(svc.plan_meta(state, self.r)["version"], 2)

    async def test_failed_person_delete_commit_leaves_assignment_and_person(self):
        from fastapi import HTTPException

        await self.save()
        await self.publish()
        await self.assign()
        before = await svc.load()
        with patch.object(svc, "commit", side_effect=HTTPException(409, "충돌")):
            await self.delete_person(status=409)
        self.assertEqual(await svc.load(), before)

    async def test_missing_person_and_invalid_delete_revision(self):
        before = await svc.load()
        await self.delete_person("missing", status=404)
        await self.delete_person(status=422, revision=-1)
        self.assertEqual(await svc.load(), before)

    async def test_duplicates_invalid_refs_and_occupied_target(self):
        bad = self.plan()
        bad["seats"][1]["number"] = "A-01"
        self.assertEqual(
            (
                await self.client.put(f"/spaces/rooms/{self.r}/plan", json=bad)
            ).status_code,
            422,
        )
        bad = self.plan()
        bad["objects"][1]["seatId"] = "missing"
        self.assertEqual(
            (
                await self.client.put(f"/spaces/rooms/{self.r}/plan", json=bad)
            ).status_code,
            422,
        )
        await self.save()
        await self.publish()
        await self.assign()
        p2 = await self.create("people", {"name": "둘째", "teamId": self.t1["id"]})
        await self.assign(person=p2, status=409)

    async def test_hierarchy_deletion_and_legacy_room_visibility(self):
        for kind, ident in [
            ("buildings", self.b),
            ("floors", self.f),
            ("rooms", self.r),
        ]:
            res = await self.client.delete(
                f"/spaces/{kind}/{ident}", params={"revision": await self.revision()}
            )
            self.assertEqual(res.status_code, 409)
        res = await self.client.put(
            f"/spaces/rooms/{self.r}",
            params={"revision": await self.revision()},
            json={
                "name": "701호",
                "floorId": self.f,
                "teamIds": [self.t1["id"], self.t2["id"]],
                "visibility": "members",
            },
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.user = self.viewer
        self.assertEqual(
            (await self.client.get(f"/spaces/rooms/{self.r}/plan")).status_code, 200
        )
        state = (await self.client.get("/spaces")).json()
        self.assertIn(self.r, [r["id"] for r in state["rooms"]])
        self.assertIn(self.p, [p["id"] for p in state["people"]])

    async def test_menu_permission_is_enforced_for_every_endpoint_and_old_role(self):
        await self.save()
        await self.publish()
        revision = await self.revision()
        requests = [("GET", "/spaces", {})]
        entities = {
            "teams": (self.t1["id"], {"name": self.t1["name"]}),
            "buildings": (self.b, {"name": "별관"}),
            "floors": (self.f, {"name": "8층", "buildingId": self.b}),
            "rooms": (self.r, {"name": "사무실", "floorId": self.f}),
            "people": (self.p, {"name": "인원", "teamId": self.t1["id"]}),
        }
        for kind, (ident, payload) in entities.items():
            requests += [
                ("POST", f"/spaces/{kind}", {"params": {"revision": revision}, "json": payload}),
                ("PUT", f"/spaces/{kind}/{ident}", {"params": {"revision": revision}, "json": payload}),
                ("DELETE", f"/spaces/{kind}/{ident}", {"params": {"revision": revision}}),
            ]
        plan_url = f"/spaces/rooms/{self.r}/plan"
        requests += [
            ("GET", plan_url, {}),
            ("GET", plan_url + "/pdf", {}),
            ("GET", plan_url, {"params": {"draft": True}}),
            ("PUT", plan_url, {"json": self.plan(2)}),
            ("DELETE", plan_url, {"params": {"version": 2}}),
            ("DELETE", plan_url, {"params": {"version": 2, "revision": revision, "release_assignments": True}}),
            ("POST", plan_url + "/publish", {"json": {"version": 2}}),
            ("POST", plan_url + "/clone", {"json": {"version": 2, "targetRoomId": self.r2}}),
            ("PUT", "/spaces/seats/seat-1/assignment", {"json": {"personId": self.p, "revision": revision}}),
            ("DELETE", "/spaces/seats/seat-1/assignment", {"params": {"revision": revision}}),
        ]
        before = await svc.load()
        for user in (self.viewer, self.team_user, self.manager):
            self.user = user.model_copy(update={"permissions": []})
            for method, url, kwargs in requests:
                with self.subTest(user=user.email, method=method, url=url):
                    response = await self.client.request(method, url, **kwargs)
                    self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(await svc.load(), before)

    async def test_login_link_unique_and_optional(self):
        data = {"name": "계정 연결", "teamId": self.t1["id"], "userId": self.viewer.id}
        await self.create("people", data)
        res = await self.client.post(
            "/spaces/people", params={"revision": await self.revision()}, json=data
        )
        self.assertEqual(res.status_code, 409)

    async def test_space_menu_consolidation_preserves_customization(self):
        from app.db.startup import migrate_space_plan_submenu, seed_system_menu_extras

        menus = M.get_menus_collection()
        retained = [
            {"title": "공간 설정", "link": "/spaces/rooms", "icon": "custom", "require_admin": True},
            {"title": "좌석 배정", "link": "/spaces/seats"},
            {"title": "내 바로가기", "link": "/custom"},
        ]
        await menus.insert_one({
            "slug": "spaces", "title": "내 공간 메뉴",
            "submenus": [*retained, {"title": "배치도 관리", "link": "/spaces/plans"}],
        })
        await menus.insert_one({"slug": "custom", "submenus": [{"link": "/spaces/plans"}]})
        for _ in range(2):
            await seed_system_menu_extras()
            await migrate_space_plan_submenu()
        result = await menus.find_one({"slug": "spaces"})
        self.assertEqual(result["title"], "내 공간 메뉴")
        self.assertEqual(result["submenus"], retained)
        self.assertEqual((await menus.find_one({"slug": "custom"}))["submenus"], [{"link": "/spaces/plans"}])
        await menus.delete_one({"slug": "spaces"})
        await menus.insert_one({"slug": "spaces"})
        await seed_system_menu_extras()
        self.assertEqual(
            [s["link"] for s in (await menus.find_one({"slug": "spaces"}))["submenus"]],
            ["/spaces/people", "/spaces/rooms", "/spaces/seats"],
        )

    async def test_initializer_is_idempotent(self):
        before = await svc.load()
        await svc.initialize()
        self.assertEqual(await svc.load(), before)

    async def test_cross_room_move_and_unassign(self):
        await self.save()
        await self.publish()
        await self.assign()
        res = await self.client.post(
            f"/spaces/rooms/{self.r}/plan/clone",
            json={"version": 2, "targetRoomId": self.r2},
        )
        self.assertEqual(res.status_code, 201)
        await self.publish(1, self.r2)
        seat = next(
            s
            for s in (await svc.load())["seats"]
            if s["room_id"] == self.r2 and s["team_id"] == self.t1["id"]
        )
        self.user = self.team_user
        await self.assign(seat["id"])
        state = await svc.load()
        self.assertEqual(len(state["assignments"]), 1)
        self.assertEqual(svc.find(state, "people", self.p)["room_id"], self.r2)
        res = await self.client.delete(
            f'/spaces/seats/{seat["id"]}/assignment',
            params={"revision": await self.revision()},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual((await svc.load())["assignments"], [])

    async def test_foreign_seat_ids_team_changes_and_missing_references(self):
        await self.save()
        await self.publish()
        await self.assign()
        second = self.plan()
        second["seats"][2]["teamId"] = self.t1["id"]
        res = await self.client.put(f"/spaces/rooms/{self.r2}/plan", json=second)
        self.assertEqual(res.status_code, 422)
        changed = self.plan(2)
        changed["seats"][0]["teamId"] = self.t2["id"]
        await self.save(changed)
        res = await self.client.post(
            f"/spaces/rooms/{self.r}/plan/publish", json={"version": 3}
        )
        self.assertEqual(res.status_code, 409)
        self.assertEqual(
            svc.find(await svc.load(), "seats", "seat-1")["team_id"], self.t1["id"]
        )
        res = await self.client.post(
            "/spaces/floors",
            params={"revision": await self.revision()},
            json={"name": "층", "buildingId": "missing"},
        )
        self.assertEqual(res.status_code, 404)

    async def test_stale_publish_and_stale_person_update(self):
        await self.save()
        await self.save(self.plan(1))
        res = await self.client.post(
            f"/spaces/rooms/{self.r}/plan/publish", json={"version": 1}
        )
        self.assertEqual(res.status_code, 409)
        self.assertEqual((await svc.load())["seats"], [])
        res = await self.client.put(
            f"/spaces/people/{self.p}",
            params={"revision": 0},
            json={"name": "잘못된 덮어쓰기", "teamId": self.t1["id"]},
        )
        self.assertEqual(res.status_code, 409)
        self.assertEqual(svc.find(await svc.load(), "people", self.p)["name"], "홍길동")

    async def test_menu_user_can_publish_assign_and_unassign(self):
        self.user = self.viewer
        await self.save()
        await self.publish()
        await self.assign()
        res = await self.client.delete(
            "/spaces/seats/seat-1/assignment",
            params={"revision": await self.revision()},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual((await svc.load())["assignments"], [])

    async def delete_plan(self, version, room=None, status=200, release_assignments=False, revision=None):
        params = {"version": version}
        if release_assignments:
            params["release_assignments"] = True
        if revision is not None:
            params["revision"] = revision
        result = await self.client.delete(
            f"/spaces/rooms/{room or self.r}/plan", params=params
        )
        self.assertEqual(result.status_code, status, result.text)
        return result

    async def test_delete_plan_removes_published_draft_and_seats_only(self):
        await self.save()
        await self.publish()
        changed = self.plan(2)
        changed["objects"][1]["x"] = 650
        await self.save(changed)
        before = await svc.load()
        result = await self.delete_plan(3)
        self.assertEqual(result.json()["version"], 4)
        after = await svc.load()
        for kind in ("buildings", "floors", "rooms", "teams", "people"):
            self.assertEqual(after[kind], before[kind])
        self.assertEqual(after["seats"], [])
        self.assertEqual(after["assignments"], [])
        self.assertEqual((await self.client.get("/spaces")).json()["plans"], [])
        for draft in (False, True):
            plan = await svc.get_plan(self.r, self.admin, draft)
            self.assertFalse(plan["published"])
            self.assertFalse(plan["has_draft"])
            self.assertEqual(plan["objects"], [])
            self.assertEqual(plan["seats"], [])
            self.assertEqual(plan["version"], 4)
        self.assertEqual(svc.plan_meta(after, self.r)["deleted_by"], self.admin.email)
        self.assertEqual(await M.get_db()[svc.VERSIONS].count_documents({"room_id": self.r}), 2)

    async def test_delete_draft_only_and_recreate_keeps_monotonic_version(self):
        await self.save()
        await self.delete_plan(1)
        await self.delete_plan(1, status=409)
        await self.delete_plan(2, status=404)
        stale = await self.client.put(f"/spaces/rooms/{self.r}/plan", json=self.plan(1))
        self.assertEqual(stale.status_code, 409)
        await self.save(self.plan(2))
        await self.publish(3)
        self.assertEqual(len((await svc.load())["seats"]), 3)

    async def test_menu_access_allows_deleting_plans_without_room_roles(self):
        for user in (self.team_user, self.viewer, self.manager):
            with self.subTest(user=user.email):
                self.user = user
                version = svc.plan_meta(await svc.load(), self.r2)["version"]
                plan = self.plan(version)
                for seat in plan["seats"]:
                    seat["teamId"] = self.t1["id"]
                await self.save(plan, self.r2)
                await self.publish(version + 1, self.r2)
                await self.delete_plan(version + 2, room=self.r2)

    async def test_delete_plan_requires_assignment_release(self):
        await self.save()
        await self.publish()
        await self.assign()
        before = await svc.load()
        result = await self.delete_plan(2, status=409)
        self.assertIn("배정을 먼저 해제", result.json()["detail"])
        self.assertEqual(await svc.load(), before)
        self.user = self.team_user
        release = await self.client.delete(
            "/spaces/seats/seat-1/assignment", params={"revision": await self.revision()}
        )
        self.assertEqual(release.status_code, 200)
        self.user = self.manager
        await self.delete_plan(2)

    async def test_confirmed_plan_delete_releases_all_teams_and_preserves_people(self):
        await self.save()
        await self.publish()
        await self.assign()
        other = await self.create("people", {"name": "다른 팀 인원", "teamId": self.t2["id"]})
        await self.assign("seat-3", other)
        draft = self.plan(2)
        draft["objects"][1]["x"] = 650
        await self.save(draft)
        before = await svc.load()
        self.user = self.viewer
        result = await self.delete_plan(3, release_assignments=True, revision=before["revision"])
        self.assertEqual(result.json()["released_assignments"], 2)
        after = await svc.load()
        self.assertEqual(after["assignments"], [])
        self.assertEqual(after["seats"], [])
        for kind in ("people", "rooms", "teams", "floors", "buildings"):
            self.assertEqual(after[kind], before[kind])
        meta = svc.plan_meta(after, self.r)
        self.assertIsNone(meta["draft_id"])
        self.assertIsNone(meta["published_id"])
        self.assertEqual(meta["version"], 4)
        self.assertEqual(meta["deleted_by"], self.viewer.email)

    async def test_confirmed_plan_delete_preserves_other_room_assignments(self):
        await self.save()
        await self.publish()
        clone = await self.client.post(f"/spaces/rooms/{self.r}/plan/clone", json={
            "version": 2, "targetRoomId": self.r2,
        })
        self.assertEqual(clone.status_code, 201)
        await self.publish(1, self.r2)
        other = await self.create("people", {"name": "다른 사무실 인원", "teamId": self.t1["id"]})
        await self.assign()
        seat = next(s for s in (await svc.load())["seats"] if s["room_id"] == self.r2)
        await self.assign(seat["id"], other)
        before = await svc.load()
        result = await self.delete_plan(2, release_assignments=True, revision=before["revision"])
        self.assertEqual(result.json()["released_assignments"], 1)
        after = await svc.load()
        self.assertEqual(after["assignments"], [a for a in before["assignments"] if a["seat_id"] == seat["id"]])
        self.assertEqual(after["seats"], [s for s in before["seats"] if s["room_id"] == self.r2])
        self.assertEqual(after["people"], before["people"])
        self.assertEqual(svc.plan_meta(after, self.r2), svc.plan_meta(before, self.r2))

    async def test_confirmed_plan_delete_requires_current_revision_and_version(self):
        await self.save()
        await self.publish()
        await self.assign()
        before = await svc.load()
        await self.delete_plan(2, status=422, release_assignments=True)
        self.assertEqual(await svc.load(), before)
        await self.assign("seat-2")
        changed = await svc.load()
        await self.delete_plan(2, status=409, release_assignments=True, revision=before["revision"])
        await self.delete_plan(1, status=409, release_assignments=True, revision=changed["revision"])
        self.assertEqual(await svc.load(), changed)

    async def test_confirmed_plan_delete_failure_preserves_every_assignment(self):
        from fastapi import HTTPException

        await self.save()
        await self.publish()
        await self.assign()
        before = await svc.load()
        with patch.object(svc, "commit", side_effect=HTTPException(409, "충돌")):
            await self.delete_plan(2, status=409, release_assignments=True, revision=before["revision"])
        self.assertEqual(await svc.load(), before)

    async def test_concurrent_confirmed_plan_delete_and_assignment_one_wins(self):
        await self.save()
        await self.publish()
        await self.assign()
        before = await svc.load()
        results = await asyncio.gather(
            self.client.delete(f"/spaces/rooms/{self.r}/plan", params={
                "version": 2, "revision": before["revision"], "release_assignments": True,
            }),
            self.client.put("/spaces/seats/seat-2/assignment", json={
                "personId": self.p, "revision": before["revision"],
            }),
        )
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])
        after = await svc.load()
        deleted = not svc.plan_meta(after, self.r)["published_id"]
        self.assertEqual(len(after["seats"]), 0 if deleted else 3)
        self.assertEqual(len(after["assignments"]), 0 if deleted else 1)
        if not deleted:
            self.assertEqual(after["assignments"][0]["seat_id"], "seat-2")
        self.assertEqual(after["people"], before["people"])

    async def test_deleting_one_plan_preserves_other_room_assignments(self):
        await self.save()
        await self.publish()
        clone = await self.client.post(f"/spaces/rooms/{self.r}/plan/clone", json={
            "version": 2, "targetRoomId": self.r2,
        })
        self.assertEqual(clone.status_code, 201)
        await self.publish(1, self.r2)
        seat = next(s for s in (await svc.load())["seats"] if s["room_id"] == self.r2)
        await self.assign(seat["id"])
        before = await svc.load()
        await self.delete_plan(2)
        after = await svc.load()
        self.assertEqual(after["assignments"], before["assignments"])
        self.assertEqual(after["people"], before["people"])
        self.assertEqual(after["seats"], [s for s in before["seats"] if s["room_id"] == self.r2])

    async def test_deleted_plan_allows_clone_and_room_deletion(self):
        await self.save()
        await self.publish()
        for _ in range(2):
            clone = await self.client.post(f"/spaces/rooms/{self.r}/plan/clone", json={
                "version": 2, "targetRoomId": self.r2,
            })
            self.assertEqual(clone.status_code, 201, clone.text)
            version = svc.plan_meta(await svc.load(), self.r2)["version"]
            await self.delete_plan(version, room=self.r2)
        result = await self.client.delete(
            f"/spaces/rooms/{self.r2}", params={"revision": await self.revision()}
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertNotIn(self.r2, [p["room_id"] for p in (await svc.load())["plans"]])

    async def test_concurrent_delete_and_edit_one_wins(self):
        await self.save()
        await self.publish()
        results = await asyncio.gather(
            self.client.delete(f"/spaces/rooms/{self.r}/plan", params={"version": 2}),
            self.client.put(f"/spaces/rooms/{self.r}/plan", json=self.plan(2)),
        )
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])
        state = await svc.load()
        meta = svc.plan_meta(state, self.r)
        self.assertEqual(meta["version"], 3)
        self.assertEqual(len(state["seats"]), 3 if meta["published_id"] else 0)
        await self.delete_plan(2, status=409)

    async def test_failed_delete_commit_leaves_plan_and_seats_unchanged(self):
        from fastapi import HTTPException

        await self.save()
        await self.publish()
        before = await svc.load()
        with patch.object(svc, "commit", side_effect=HTTPException(409, "충돌")):
            await self.delete_plan(2, status=409)
        self.assertEqual(await svc.load(), before)

    async def test_delete_nonexistent_plan_and_invalid_version(self):
        before = await svc.load()
        await self.delete_plan(0, status=404)
        await self.delete_plan(-1, status=422)
        self.assertEqual(await svc.load(), before)

    async def publish_unowned_seat(self):
        plan = self.plan()
        plan["seats"][0]["teamId"] = None
        await self.save(plan)
        await self.publish()

    async def configure_and_assign(self, status=200, **overrides):
        payload = {
            "personId": self.p,
            "teamId": self.t1["id"],
            "revision": await self.revision(),
            **overrides,
        }
        res = await self.client.put("/spaces/seats/seat-1/assignment", json=payload)
        self.assertEqual(res.status_code, status, res.text)
        return res

    async def test_assign_unowned_seat_configures_team_without_changing_geometry(self):
        await self.publish_unowned_seat()
        before = await svc.load()
        original = await svc.get_plan(self.r, self.admin)
        await self.assign(status=422)
        await self.configure_and_assign()
        after = await svc.load()
        published = await svc.get_plan(self.r, self.admin)
        self.assertEqual(published["objects"], original["objects"])
        self.assertEqual(published["seats"][0]["team_id"], self.t1["id"])
        self.assertEqual(svc.find(after, "seats", "seat-1")["team_id"], self.t1["id"])
        self.assertEqual(after["assignments"][0]["person_id"], self.p)
        self.assertEqual(published["version"], original["version"] + 1)
        old = await M.get_db()[svc.VERSIONS].find_one({"_id": before["plans"][0]["published_id"]})
        self.assertIsNone(old["seats"][0]["team_id"])
        await self.assign("seat-2")
        self.assertEqual((await svc.load())["plans"], after["plans"])

    async def test_configuring_team_preserves_unpublished_draft_geometry(self):
        await self.publish_unowned_seat()
        draft = self.plan(2)
        draft["seats"][0]["teamId"] = None
        draft["objects"][1]["x"] = 650
        await self.save(draft)
        await self.configure_and_assign()
        published = await svc.get_plan(self.r, self.admin)
        saved = await svc.get_plan(self.r, self.admin, True)
        self.assertEqual(published["objects"][1]["x"], 100)
        self.assertEqual(saved["objects"][1]["x"], 650)
        self.assertTrue(saved["has_draft"])
        self.assertEqual(saved["seats"][0]["team_id"], self.t1["id"])
        stale = await self.client.put(f"/spaces/rooms/{self.r}/plan", json={**draft, "version": 3})
        self.assertEqual(stale.status_code, 409)
        await self.publish(saved["version"])
        self.assertEqual((await svc.get_plan(self.r, self.admin))["objects"][1]["x"], 650)
        self.assertEqual(len((await svc.load())["assignments"]), 1)

    async def test_menu_access_allows_configuring_and_assigning_unowned_seats(self):
        await self.publish_unowned_seat()
        for user in (self.team_user, self.manager, self.viewer):
            with self.subTest(user=user.email):
                self.user = user
                await self.configure_and_assign()
                after = await svc.load()
                self.assertEqual(after["assignments"][0]["person_id"], self.p)
                self.assertEqual(svc.find(after, "seats", "seat-1")["team_id"], self.t1["id"])
                release = await self.client.delete(
                    "/spaces/seats/seat-1/assignment", params={"revision": await self.revision()}
                )
                self.assertEqual(release.status_code, 200)

    async def test_unowned_seat_does_not_overwrite_conflicting_draft(self):
        for change in ("other_team", "removed"):
            with self.subTest(change=change):
                self.user = self.admin
                if change == "other_team":
                    await self.publish_unowned_seat()
                meta = svc.plan_meta(await svc.load(), self.r)
                draft = self.plan(meta["version"])
                if change == "other_team":
                    draft["seats"][0]["teamId"] = self.t2["id"]
                else:
                    draft["seats"].pop(0)
                    draft["objects"].pop(1)
                await self.save(draft)
                before = await svc.load()
                await self.configure_and_assign(status=409)
                self.assertEqual(await svc.load(), before)

    async def test_unowned_seat_rejects_invalid_team_and_inactive_person(self):
        await self.publish_unowned_seat()
        before = await svc.load()
        await self.configure_and_assign(status=422, teamId="missing")
        await self.configure_and_assign(status=422, teamId=self.t2["id"])
        self.assertEqual(await svc.load(), before)
        await self.client.put(
            f"/spaces/people/{self.p}",
            params={"revision": await self.revision()},
            json={"name": "홍길동", "teamId": self.t1["id"], "active": False},
        )
        before = await svc.load()
        await self.configure_and_assign(status=422)
        self.assertEqual(await svc.load(), before)

    async def test_unowned_seat_cannot_change_an_existing_team(self):
        await self.save()
        await self.publish()
        before = await svc.load()
        await self.configure_and_assign(status=409, teamId=self.t2["id"])
        self.assertEqual(await svc.load(), before)

    async def test_concurrent_team_configuration_and_assignment_is_atomic(self):
        await self.publish_unowned_seat()
        person2 = await self.create("people", {"name": "둘째", "teamId": self.t1["id"]})
        revision = await self.revision()
        results = await asyncio.gather(*[
            self.client.put("/spaces/seats/seat-1/assignment", json={
                "personId": person, "teamId": self.t1["id"], "revision": revision,
            }) for person in (self.p, person2)
        ])
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])
        state = await svc.load()
        self.assertEqual(len(state["assignments"]), 1)
        self.assertEqual(svc.find(state, "seats", "seat-1")["team_id"], self.t1["id"])
        self.assertEqual(svc.plan_meta(state, self.r)["version"], 3)

    async def test_failed_commit_does_not_partially_configure_team(self):
        from fastapi import HTTPException

        await self.publish_unowned_seat()
        before = await svc.load()
        with patch.object(svc, "commit", side_effect=HTTPException(409, "충돌")):
            await self.configure_and_assign(status=409)
        self.assertEqual(await svc.load(), before)

    async def test_invalid_geometry_and_extra_fields_rejected(self):
        for change in [
            {"width": -1},
            {"rotation": 361},
            {"kind": "script"},
            {"assignedPersonId": self.p},
        ]:
            payload = self.plan()
            payload["objects"][1].update(change)
            res = await self.client.put(f"/spaces/rooms/{self.r}/plan", json=payload)
            self.assertEqual(res.status_code, 422)

    async def test_menu_access_grants_all_entities_without_changing_login_permissions(self):
        before_users = await M.get_users_collection().find({}).to_list(None)
        self.user = self.viewer
        team = await self.create("teams", {"name": "추가 팀"})
        building = await self.create("buildings", {"name": "별관"})
        floor = await self.create("floors", {"name": "1층", "buildingId": building})
        room = await self.create("rooms", {"name": "101호", "floorId": floor, "teamIds": [team]})
        person = await self.create("people", {"name": "신규 인원", "teamId": team, "roomId": room, "userId": self.team_user.id})
        updates = [
            ("teams", team, {"name": "추가 팀", "color": "#123456"}),
            ("buildings", building, {"name": "신관"}),
            ("floors", floor, {"name": "2층", "buildingId": building}),
            ("rooms", room, {"name": "201호", "floorId": floor, "teamIds": [team]}),
            ("people", person, {"name": "수정 인원", "teamId": team, "roomId": room, "userId": self.team_user.id, "active": False}),
        ]
        for kind, ident, payload in updates:
            response = await self.client.put(f"/spaces/{kind}/{ident}", params={"revision": await self.revision()}, json=payload)
            self.assertEqual(response.status_code, 200, response.text)
        snapshot = (await self.client.get("/spaces")).json()
        self.assertTrue(snapshot["can_manage"])
        self.assertFalse(snapshot["is_admin"])
        self.assertEqual(set(snapshot["editable_room_ids"]), {r["id"] for r in snapshot["rooms"]})
        self.assertEqual(set(snapshot["managed_team_ids"]), {t["id"] for t in snapshot["teams"]})
        self.assertIn(person, [p["id"] for p in snapshot["people"]])
        self.assertIn(self.team_user.id, [a["id"] for a in snapshot["accounts"]])
        for kind, ident in [("people", person), ("rooms", room), ("floors", floor), ("buildings", building), ("teams", team)]:
            response = await self.client.delete(f"/spaces/{kind}/{ident}", params={"revision": await self.revision()})
            self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(await M.get_users_collection().find({}).to_list(None), before_users)
        self.assertEqual(self.viewer.permissions, ["spaces"])
        self.assertFalse(self.viewer.is_admin)

    async def test_pdf_exports_published_geometry_and_live_people_only(self):
        import pymupdf
        from urllib.parse import unquote

        await self.save()
        await self.publish()
        await self.assign()
        other = await self.create("people", {"name": "김다른팀", "teamId": self.t2["id"], "title": "책임"})
        await self.assign("seat-3", other)
        await self.create("people", {"name": "배정되지않은인원", "teamId": self.t1["id"]})
        self.user = self.viewer
        url = f"/spaces/rooms/{self.r}/plan/pdf"
        original = await self.client.get(url)
        self.assertEqual(original.status_code, 200, original.content[:100])
        draft = self.plan(2)
        draft["objects"][0]["x"] = -500
        draft["objects"].append({"id": "draft-only", "kind": "text", "name": "임시저장전용", "x": 200, "y": 400, "width": 200, "height": 30})
        draft["seats"][0]["number"] = "DRAFT-01"
        await self.save(draft)
        before = await svc.load()
        result = await self.client.get(url)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers["content-type"], "application/pdf")
        self.assertIn("701호_좌석배치도.pdf", unquote(result.headers["content-disposition"]))
        self.assertEqual(result.headers["cache-control"], "private, no-store")
        self.assertTrue(result.content.startswith(b"%PDF-"))
        with pymupdf.open(stream=result.content, filetype="pdf") as doc, pymupdf.open(stream=original.content, filetype="pdf") as old:
            text = "\n".join(page.get_text() for page in doc)
            for expected in ("701호", "본관", "7층", "A-01", "A-02", "A-03", "홍길동", "김다른팀", "책임", self.t1["name"], self.t2["name"], "미배정", "KST"):
                self.assertIn(expected, text)
            for hidden in ("임시저장전용", "DRAFT-01", "배정되지않은인원", "702호"):
                self.assertNotIn(hidden, text)
            self.assertEqual(len(doc), 2)
            self.assertEqual(doc[0].get_drawings(), old[0].get_drawings())
            self.assertTrue(all(doc.extract_font(font[0])[3] for font in doc[0].get_fonts()))
        self.assertEqual(await svc.load(), before)

    async def test_pdf_tracks_assignment_changes_without_republishing(self):
        import pymupdf

        await self.save()
        await self.publish()
        await self.assign()
        plans = deepcopy((await svc.load())["plans"])
        self.user = self.viewer
        release = await self.client.delete("/spaces/seats/seat-1/assignment", params={"revision": await self.revision()})
        self.assertEqual(release.status_code, 200)
        response = await self.client.get(f"/spaces/rooms/{self.r}/plan/pdf")
        with pymupdf.open(stream=response.content, filetype="pdf") as doc:
            self.assertNotIn("홍길동", "\n".join(page.get_text() for page in doc))
        await self.assign("seat-2")
        response = await self.client.get(f"/spaces/rooms/{self.r}/plan/pdf")
        with pymupdf.open(stream=response.content, filetype="pdf") as doc:
            self.assertIn("홍길동", doc[0].get_text())
            self.assertIn("홍길동", doc[1].get_text())
        self.assertEqual((await svc.load())["plans"], plans)

    async def test_pdf_requires_published_plan_and_existing_room(self):
        self.user = self.viewer
        self.assertEqual((await self.client.get("/spaces/rooms/missing/plan/pdf")).status_code, 404)
        url = f"/spaces/rooms/{self.r}/plan/pdf"
        self.assertEqual((await self.client.get(url)).status_code, 409)
        await self.save()
        response = await self.client.get(url)
        self.assertEqual(response.status_code, 409)
        self.assertIn("게시", response.json()["detail"])
        await self.publish()
        await self.delete_plan(2)
        self.assertEqual((await self.client.get(url)).status_code, 409)

    async def test_pdf_handles_published_empty_plan(self):
        import pymupdf

        await self.save({"version": 0, "width": 600, "height": 1000, "objects": [], "seats": []})
        await self.publish()
        response = await self.client.get(f"/spaces/rooms/{self.r}/plan/pdf")
        self.assertEqual(response.status_code, 200)
        with pymupdf.open(stream=response.content, filetype="pdf") as doc:
            self.assertEqual(len(doc), 1)
            self.assertGreater(doc[0].rect.height, doc[0].rect.width)
            self.assertIn("등록된 배치도 객체가 없습니다.", doc[0].get_text())

    async def test_pdf_rotated_objects_unicode_long_labels_and_pagination(self):
        import pymupdf
        from app.models.spaces import PlanInput
        from app.services.spaces.pdf import render_plan_pdf

        state = await svc.load()
        plan = self.plan()
        for obj in plan["objects"]:
            obj.update(x=-300 + obj["x"], rotation=35)
        for i, kind in enumerate(("door", "cabinet", "text", "zone")):
            plan["objects"].append({"id": kind, "kind": kind, "name": "한글 <배치> & 안전", "x": 400 + i * 150, "y": -200 + i * 80, "width": 130, "height": 80, "rotation": 90 if i % 2 else -45, "teamId": self.t2["id"] if kind == "zone" else None})
        for i in range(4, 85):
            seat_id = f"seat-{i}"
            plan["seats"].append({"id": seat_id, "number": f"A-{i:02}", "teamId": self.t1["id"]})
            plan["objects"].append({"id": f"desk-{i}", "kind": "desk", "seatId": seat_id, "x": (i % 10) * 150, "y": (i // 10) * 100, "width": 100, "height": 60, "rotation": i * 17 % 360})
        long_name = "가나다라마바사아자차" * 10
        state["people"][0].update(name=long_name, title="긴직책" * 30)
        state["assignments"] = [{"seat_id": "seat-1", "person_id": self.p}]
        content = render_plan_pdf(state, svc.find(state, "rooms", self.r), PlanInput.model_validate(plan).model_dump(), None)
        with pymupdf.open(stream=content, filetype="pdf") as doc:
            self.assertGreater(len(doc), 3)
            text = "".join("".join(doc[i].get_text().split()) for i in range(1, len(doc)))
            self.assertIn(long_name, text)
            self.assertIn("긴직책" * 30, text)
            self.assertIn("A-84", text)
            for page in doc:
                for drawing in page.get_drawings():
                    self.assertTrue((page.rect + (-1, -1, 1, 1)).contains(drawing["rect"]))
            self.assertGreater(len(doc[0].get_pixmap(matrix=pymupdf.Matrix(0.5, 0.5)).samples), 0)

    async def test_concurrent_pdf_exports_leave_registry_unchanged(self):
        await self.save()
        await self.publish()
        await self.assign()
        before = await svc.load()
        results = await asyncio.gather(*[self.client.get(f"/spaces/rooms/{self.r}/plan/pdf") for _ in range(2)])
        self.assertEqual([r.status_code for r in results], [200, 200])
        self.assertEqual(await svc.load(), before)
