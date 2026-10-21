"""Space directory and immutable plan versions.

The deployed MongoDB is standalone (no multi-document transactions). References,
permissions, live seats and assignments therefore share a compact atomic registry,
with separate normalized entity arrays. Geometry is stored in immutable documents;
only a successfully CAS-swapped registry pointer makes a version visible. This also
keeps publish, cross-room moves and deactivation atomic across multiple workers.
"""
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from bson import BSON, ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from starlette.concurrency import run_in_threadpool

from app.db.mongo import MongoClientManager as M
from app.models.spaces import PlanInput
from app.models.user import TEAM_OPTIONS

REGISTRY = "space_registry"
VERSIONS = "space_plan_versions"
ENTITY_KINDS = ("teams", "buildings", "floors", "rooms", "people")


def uid():
    return uuid4().hex


def now():
    return datetime.now(timezone.utc).isoformat()


def fail(message, status=409):
    raise HTTPException(status_code=status, detail=message)


def find(state, kind, ident):
    item = next((i for i in state[kind] if i["id"] == ident), None)
    if item is None:
        fail("요청한 정보를 찾을 수 없습니다.", 404)
    return item


def has_space_access(user):
    return bool(user.is_admin or "spaces" in (user.permissions or []))


def require_access(user):
    if not has_space_access(user):
        fail("인적자원 관리 메뉴 권한이 필요합니다.", 403)


def room_access(state, user, room_id):
    require_access(user)
    return find(state, "rooms", room_id)


async def initialize():
    db = M.get_db()
    await db[VERSIONS].create_index([("room_id", 1), ("created_at", -1)])
    if await db[REGISTRY].find_one({"_id": "directory"}, {"_id": 1}):
        return
    # Reuse the existing team vocabulary, without changing any login account.
    team_names = set(TEAM_OPTIONS)
    team_names.update(t for t in await M.get_users_collection().distinct("team") if t)
    colors = ["#1976d2", "#00897b", "#8e24aa", "#ef6c00", "#546e7a"]
    state = {
        "_id": "directory",
        "revision": 0,
        **{k: [] for k in ENTITY_KINDS},
        "seats": [],
        "assignments": [],
        "plans": [],
    }
    state["teams"] = [
        {"id": uid(), "name": name, "color": colors[i % len(colors)], "manager_ids": []}
        for i, name in enumerate(sorted(team_names))
    ]
    try:
        await db[REGISTRY].insert_one(state)
    except DuplicateKeyError:
        pass  # Another worker initialized the same registry.


async def load():
    state = await M.get_db()[REGISTRY].find_one({"_id": "directory"})
    if state is None:
        await initialize()
        state = await M.get_db()[REGISTRY].find_one({"_id": "directory"})
    return state


async def commit(state, user):
    revision = state["revision"]
    state.update(revision=revision + 1, updated_at=now(), updated_by=user.email)
    # Leave headroom below Mongo's 16 MiB document limit; reject without any partial update.
    if len(BSON.encode(state)) > 12 * 1024 * 1024:
        fail("공간 데이터 용량 한도에 도달했습니다. 관리자에게 문의해 주세요.", 413)
    result = await M.get_db()[REGISTRY].replace_one(
        {"_id": "directory", "revision": revision}, state
    )
    if not result.matched_count:
        fail("다른 사용자가 정보를 변경했습니다. 새로고침 후 다시 시도해 주세요.")


def check_revision(state, revision):
    if revision != state["revision"]:
        fail("다른 사용자가 정보를 변경했습니다. 새로고침 후 다시 시도해 주세요.")


async def accounts():
    docs = (
        await M.get_users_collection()
        .find({"is_blocked": {"$ne": True}}, {"full_name": 1, "email": 1, "team": 1})
        .to_list(None)
    )
    return [
        {
            "id": str(d["_id"]),
            "name": d.get("full_name") or d["email"],
            "email": d["email"],
            "team": d.get("team"),
        }
        for d in docs
    ]


async def snapshot(user):
    require_access(user)
    state = await load()
    return {
        "revision": state["revision"],
        **{kind: state[kind] for kind in ENTITY_KINDS},
        "seats": state["seats"],
        "assignments": state["assignments"],
        "plans": [
            {
                "room_id": p["room_id"],
                "version": p["version"],
                "published": bool(p.get("published_id")),
                "has_draft": bool(p.get("draft_id")),
            }
            for p in state["plans"]
            if p.get("draft_id") or p.get("published_id")
        ],
        "accounts": await accounts(),
        "can_manage": True,
        # Keep existing capability fields for clients using the previous API.
        "editable_room_ids": [r["id"] for r in state["rooms"]],
        "managed_team_ids": [t["id"] for t in state["teams"]],
        "is_admin": user.is_admin,
    }


async def validate_users(ids):
    unique = set(ids)
    if any(not ObjectId.is_valid(i) for i in unique):
        fail("올바른 로그인 계정을 선택해 주세요.", 422)
    count = await M.get_users_collection().count_documents(
        {"_id": {"$in": [ObjectId(i) for i in unique]}, "is_blocked": {"$ne": True}}
    )
    if count != len(unique):
        fail("존재하지 않거나 차단된 로그인 계정입니다.", 422)


async def save_entity(kind, ident, data, revision, user):
    require_access(user)
    state = await load()
    check_revision(state, revision)
    old = find(state, kind, ident) if ident else None
    ident = ident or uid()
    parent_keys = {
        "teams": None,
        "buildings": None,
        "floors": "building_id",
        "rooms": "floor_id",
    }
    if kind in parent_keys:
        parent = parent_keys[kind]
        if any(
            i["id"] != ident
            and i["name"].casefold() == data["name"].casefold()
            and (not parent or i[parent] == data[parent])
            for i in state[kind]
        ):
            fail("같은 위치에 동일한 이름이 이미 있습니다.")
    if kind == "teams":
        await validate_users(data["manager_ids"])
        # Team names link to the established user.team vocabulary.
        if old and old["name"] != data["name"]:
            fail("기존 계정과의 연결을 유지하기 위해 팀명은 변경할 수 없습니다.", 422)
    elif kind == "floors":
        find(state, "buildings", data["building_id"])
    elif kind == "rooms":
        find(state, "floors", data["floor_id"])
        for team_id in data["team_ids"]:
            find(state, "teams", team_id)
        await validate_users(data["manager_ids"] + data["viewer_ids"])
        if any(
            s["room_id"] == ident
            and s["team_id"]
            and s["team_id"] not in data["team_ids"]
            for s in state["seats"]
        ):
            fail("좌석을 사용하는 팀은 사무실에서 제거할 수 없습니다.")
        if any(
            p["room_id"] == ident
            and p["active"]
            and p["team_id"] not in data["team_ids"]
            for p in state["people"]
        ):
            fail("근무 인원이 있는 팀은 사무실에서 제거할 수 없습니다.")
    elif kind == "people":
        find(state, "teams", data["team_id"])
        if data["room_id"]:
            room = room_access(state, user, data["room_id"])
            if data["team_id"] not in room["team_ids"]:
                fail("소속 팀이 사용하는 사무실을 선택해 주세요.", 422)
        if data["user_id"]:
            await validate_users([data["user_id"]])
            if any(
                p["id"] != ident and p["user_id"] == data["user_id"]
                for p in state["people"]
            ):
                fail("이미 다른 인원에 연결된 로그인 계정입니다.")
        assignment = next(
            (a for a in state["assignments"] if a["person_id"] == ident), None
        )
        if assignment:
            seat = find(state, "seats", assignment["seat_id"])
            if not data["active"]:
                state["assignments"].remove(assignment)
            elif data["team_id"] != seat["team_id"]:
                fail("팀 변경 전에 기존 좌석 배정을 해제해 주세요.")
            elif data["room_id"] != seat["room_id"]:
                fail("배정된 인원의 근무 공간은 좌석 배정 메뉴에서 변경해 주세요.")
    item = {"id": ident, **data, "updated_at": now(), "updated_by": user.email}
    state[kind] = [i for i in state[kind] if i["id"] != ident] + [item]
    await commit(state, user)
    return {"id": ident, "revision": state["revision"]}


async def delete_entity(kind, ident, revision, user):
    require_access(user)
    state = await load()
    check_revision(state, revision)
    find(state, kind, ident)
    if kind == "people":
        state["assignments"] = [a for a in state["assignments"] if a["person_id"] != ident]
        state["people"] = [p for p in state["people"] if p["id"] != ident]
        await commit(state, user)
        return {"revision": state["revision"]}
    checks = {
        "buildings": [("floors", "building_id")],
        "floors": [("rooms", "floor_id")],
        "rooms": [("people", "room_id"), ("seats", "room_id")],
        "teams": [("people", "team_id"), ("seats", "team_id")],
    }
    if kind not in checks:
        fail("삭제할 수 없는 항목입니다.", 422)
    if any(any(i.get(key) == ident for i in state[k]) for k, key in checks[kind]):
        fail("하위 공간, 인원 또는 배치도가 있어 삭제할 수 없습니다.")
    if kind == "rooms":
        meta = plan_meta(state, ident)
        if meta.get("published_id") or meta.get("draft_id"):
            fail("배치도가 있어 삭제할 수 없습니다. 배치도를 먼저 삭제해 주세요.")
        state["plans"] = [p for p in state["plans"] if p["room_id"] != ident]
    if kind == "teams" and any(ident in r["team_ids"] for r in state["rooms"]):
        fail("사무실에서 사용 중인 팀입니다.")
    state[kind] = [i for i in state[kind] if i["id"] != ident]
    await commit(state, user)
    return {"revision": state["revision"]}


def plan_meta(state, room_id):
    return next(
        (p for p in state["plans"] if p["room_id"] == room_id),
        {"room_id": room_id, "version": 0, "draft_id": None, "published_id": None},
    )


async def get_plan(room_id, user, draft=False):
    state = await load()
    room_access(state, user, room_id)
    meta = plan_meta(state, room_id)
    ident = (
        (meta.get("draft_id") or meta.get("published_id"))
        if draft
        else meta.get("published_id")
    )
    document = await M.get_db()[VERSIONS].find_one({"_id": ident}) if ident else None
    data = (
        {k: v for k, v in document.items() if k != "_id"}
        if document
        else {"width": 1600, "height": 1000, "objects": [], "seats": []}
    )
    return {
        **data,
        "version": meta["version"],
        "published": bool(meta.get("published_id")),
        "has_draft": bool(meta.get("draft_id")) if draft else False,
    }


async def export_plan_pdf(room_id, user):
    require_access(user)
    # Read geometry and current assignments from the same registry generation.
    state = await load()
    room = room_access(state, user, room_id)
    meta = plan_meta(state, room_id)
    if not meta.get("published_id"):
        fail("게시된 배치도가 없습니다. 배치도를 게시한 뒤 PDF로 저장해 주세요.")
    document = await M.get_db()[VERSIONS].find_one({"_id": meta["published_id"]})
    if document is None:
        fail("게시된 배치도를 찾을 수 없습니다. 새로고침 후 다시 시도해 주세요.", 404)
    from .pdf import render_plan_pdf

    content = await run_in_threadpool(
        render_plan_pdf, state, room, document, meta.get("published_at")
    )
    name = "".join(c for c in room["name"] if c not in '\r\n/\\<>:"|?*').strip()
    return content, f"{name or '사무실'}_좌석배치도.pdf"


def validate_plan(state, room, data):
    for seat in data["seats"]:
        if seat["team_id"] and seat["team_id"] not in room["team_ids"]:
            fail("좌석의 사용 팀은 해당 사무실의 사용 팀이어야 합니다.", 422)
        if any(
            s["id"] == seat["id"] and s["room_id"] != room["id"] for s in state["seats"]
        ):
            fail("다른 사무실의 좌석 식별자는 사용할 수 없습니다.", 422)
    for obj in data["objects"]:
        if obj["team_id"] and obj["team_id"] not in room["team_ids"]:
            fail("구역의 팀은 해당 사무실의 사용 팀이어야 합니다.", 422)


async def save_plan(room_id, payload, user):
    state = await load()
    room = room_access(state, user, room_id)
    meta = deepcopy(plan_meta(state, room_id))
    if meta["version"] != payload.version:
        fail("다른 사용자가 배치도를 수정했습니다. 변경사항을 확인한 뒤 다시 저장해 주세요.")
    data = payload.model_dump(exclude={"version"})
    validate_plan(state, room, data)
    doc = {
        "_id": uid(),
        "room_id": room_id,
        **data,
        "created_at": now(),
        "created_by": user.email,
    }
    # An orphan on a CAS failure is harmless and never returned through public APIs.
    await M.get_db()[VERSIONS].insert_one(doc)
    meta.update(draft_id=doc["_id"], version=meta["version"] + 1)
    state["plans"] = [p for p in state["plans"] if p["room_id"] != room_id] + [meta]
    await commit(state, user)
    return {"version": meta["version"]}


async def publish_plan(room_id, version, user):
    state = await load()
    room = room_access(state, user, room_id)
    meta = plan_meta(state, room_id)
    if version != meta["version"]:
        fail("다른 사용자가 배치도를 수정했습니다. 새로고침 후 게시해 주세요.")
    if not meta.get("draft_id"):
        fail("먼저 배치도를 임시저장해 주세요.")
    doc = await M.get_db()[VERSIONS].find_one({"_id": meta["draft_id"]})
    validate_plan(state, room, doc)
    next_seats = {s["id"]: s for s in doc["seats"]}
    occupied = {a["seat_id"] for a in state["assignments"]}
    for seat in state["seats"]:
        if seat["room_id"] != room_id or seat["id"] not in occupied:
            continue
        new = next_seats.get(seat["id"])
        if not new or new["team_id"] != seat["team_id"]:
            fail("배정된 좌석은 삭제하거나 사용 팀을 바꿀 수 없습니다. 먼저 배정을 해제해 주세요.")
    state["seats"] = [s for s in state["seats"] if s["room_id"] != room_id] + [
        {**s, "room_id": room_id} for s in doc["seats"]
    ]
    meta.update(
        published_id=meta["draft_id"],
        draft_id=None,
        version=version + 1,
        published_at=now(),
        published_by=user.email,
    )
    await commit(state, user)
    return {"version": meta["version"]}


async def clone_plan(room_id, payload, user):
    source = await get_plan(room_id, user, draft=payload.source == "draft")
    if source["version"] != payload.version:
        fail("원본 배치도가 변경되었습니다. 새로고침 후 복제해 주세요.")
    state = await load()
    room_access(state, user, payload.target_room_id)
    target = plan_meta(state, payload.target_room_id)
    if target.get("draft_id") or target.get("published_id"):
        fail("아직 배치도가 없는 사무실에만 복제할 수 있습니다.")
    if not source.get("created_at"):
        fail("저장된 원본 배치도가 없습니다.")
    room = find(state, "rooms", payload.target_room_id)
    mapping = {s["id"]: uid() for s in source["seats"]}
    for seat in source["seats"]:
        seat["id"] = mapping[seat["id"]]
        if seat["team_id"] not in room["team_ids"]:
            seat["team_id"] = None
    for obj in source["objects"]:
        obj["id"] = uid()
        if obj["seat_id"]:
            obj["seat_id"] = mapping[obj["seat_id"]]
        if obj["team_id"] not in room["team_ids"]:
            obj["team_id"] = None
    return await save_plan(
        payload.target_room_id,
        PlanInput(
            version=target["version"], **{k: source[k] for k in ("width", "height", "objects", "seats")}
        ),
        user,
    )


async def delete_plan(room_id, version, user, release_assignments=False, revision=None):
    state = await load()
    room_access(state, user, room_id)
    if revision is not None:
        check_revision(state, revision)
    elif release_assignments:
        fail("배정 해제와 삭제를 확인한 최신 정보가 필요합니다. 새로고침 후 다시 삭제해 주세요.", 422)
    meta = plan_meta(state, room_id)
    if meta["version"] != version:
        fail("다른 사용자가 배치도를 변경했습니다. 새로고침 후 다시 삭제해 주세요.")
    if not (meta.get("published_id") or meta.get("draft_id")):
        fail("삭제할 배치도가 없습니다.", 404)
    seat_ids = {s["id"] for s in state["seats"] if s["room_id"] == room_id}
    assigned = sum(a["seat_id"] in seat_ids for a in state["assignments"])
    if assigned and not release_assignments:
        fail(f"{assigned}개 좌석에 인원이 배정되어 있습니다. 좌석 배정을 먼저 해제한 뒤 배치도를 삭제해 주세요.")
    # Release this room's assignments and remove its plan in the same CAS commit.
    # A failure or concurrent change must never leave just the assignments removed.
    state["assignments"] = [a for a in state["assignments"] if a["seat_id"] not in seat_ids]
    state["seats"] = [s for s in state["seats"] if s["room_id"] != room_id]
    # Keep a monotonically increasing generation so stale editors cannot recreate
    # a deleted plan. Immutable version documents remain available for audit.
    meta.update(
        published_id=None, draft_id=None, version=version + 1,
        deleted_at=now(), deleted_by=user.email,
    )
    await commit(state, user)
    return {"version": meta["version"], "revision": state["revision"], "released_assignments": assigned}


async def configure_unowned_seat(state, seat, team_id, user):
    """Change only the seat's team, preserving published and draft geometry.

    The caller commits the new version pointers with the assignment in one CAS.
    Never publish the rest of an administrator's in-progress draft here.
    """
    meta = plan_meta(state, seat["room_id"])
    documents = []
    for key in ("published_id", "draft_id"):
        if not meta.get(key):
            continue
        source = await M.get_db()[VERSIONS].find_one({"_id": meta[key]})
        target = next((s for s in source["seats"] if s["id"] == seat["id"]), None)
        if not target or target["team_id"] not in (None, team_id):
            fail("편집본에서 이 좌석을 삭제하거나 다른 팀으로 변경했습니다. 배치도를 먼저 확인하고 게시해 주세요.")
        source.update(_id=uid(), created_at=now(), created_by=user.email)
        target["team_id"] = team_id
        documents.append((key, source))
    if not any(key == "published_id" for key, _ in documents):
        fail("게시된 좌석을 찾을 수 없습니다. 배치도를 다시 불러와 주세요.")
    for key, document in documents:
        await M.get_db()[VERSIONS].insert_one(document)
        meta[key] = document["_id"]
    meta.update(
        version=meta["version"] + 1, published_at=now(), published_by=user.email
    )
    seat["team_id"] = team_id


async def assign(seat_id, person_id, revision, user, team_id=None):
    require_access(user)
    state = await load()
    check_revision(state, revision)
    seat = find(state, "seats", seat_id)
    room = room_access(state, user, seat["room_id"])
    configure_team = not seat["team_id"] and team_id is not None
    if team_id is not None:
        if team_id not in room["team_ids"]:
            fail("좌석의 담당 팀은 사무실 사용 팀 중에서 선택해 주세요.", 422)
        if seat["team_id"] and seat["team_id"] != team_id:
            fail("이미 담당 팀이 지정된 좌석입니다. 최신 정보를 불러와 주세요.")
    target_team = team_id if configure_team else seat["team_id"]
    person = find(state, "people", person_id)
    if not person["active"]:
        fail("비활성 인원에게 좌석을 배정할 수 없습니다.", 422)
    if not target_team or target_team != person["team_id"]:
        fail("좌석과 인원의 소속 팀이 일치해야 합니다.", 422)
    occupied = next((a for a in state["assignments"] if a["seat_id"] == seat_id), None)
    if occupied and occupied["person_id"] != person_id:
        fail("이미 다른 인원이 배정된 좌석입니다.")
    previous = next(
        (a for a in state["assignments"] if a["person_id"] == person_id), None
    )
    if previous:
        previous_seat = find(state, "seats", previous["seat_id"])
        room_access(state, user, previous_seat["room_id"])
    if configure_team:
        await configure_unowned_seat(state, seat, target_team, user)
    state["assignments"] = [
        a for a in state["assignments"] if a["person_id"] != person_id
    ]
    state["assignments"].append(
        {
            "id": uid(),
            "seat_id": seat_id,
            "person_id": person_id,
            "assigned_at": now(),
            "assigned_by": user.email,
        }
    )
    person["room_id"] = seat["room_id"]
    await commit(state, user)
    return {"revision": state["revision"]}


async def unassign(seat_id, revision, user):
    require_access(user)
    state = await load()
    check_revision(state, revision)
    seat = find(state, "seats", seat_id)
    room_access(state, user, seat["room_id"])
    state["assignments"] = [a for a in state["assignments"] if a["seat_id"] != seat_id]
    await commit(state, user)
    return {"revision": state["revision"]}
