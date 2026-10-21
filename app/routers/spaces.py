"""Space APIs use the existing JWT and the organization/space menu permission."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.models.spaces import (
    AssignmentInput,
    BuildingInput,
    CloneInput,
    FloorInput,
    PersonInput,
    PlanInput,
    RoomInput,
    TeamInput,
    VersionInput,
)
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.services import spaces as service

router = APIRouter()


async def require_space_access(user: UserPublic = Depends(get_current_user)):
    service.require_access(user)
    return user


@router.get("")
async def snapshot(user=Depends(require_space_access)):
    return await service.snapshot(user)


def entity_routes(kind, model):
    async def create(
        payload: model,
        revision: int = Query(..., ge=0),
        user=Depends(require_space_access),
    ):
        return await service.save_entity(
            kind, None, payload.model_dump(), revision, user
        )

    async def update(
        ident: str,
        payload: model,
        revision: int = Query(..., ge=0),
        user=Depends(require_space_access),
    ):
        return await service.save_entity(
            kind, ident, payload.model_dump(), revision, user
        )

    async def delete(
        ident: str, revision: int = Query(..., ge=0), user=Depends(require_space_access)
    ):
        return await service.delete_entity(kind, ident, revision, user)

    router.add_api_route(
        f"/{kind}",
        create,
        methods=["POST"],
        status_code=201,
        name=f"create_space_{kind}",
    )
    router.add_api_route(
        f"/{kind}/{{ident}}", update, methods=["PUT"], name=f"update_space_{kind}"
    )
    router.add_api_route(
        f"/{kind}/{{ident}}",
        delete,
        methods=["DELETE"],
        name=f"delete_space_{kind}",
    )


for kind, model in [
    ("teams", TeamInput),
    ("buildings", BuildingInput),
    ("floors", FloorInput),
    ("rooms", RoomInput),
    ("people", PersonInput),
]:
    entity_routes(kind, model)


@router.get("/rooms/{room_id}/plan")
async def get_plan(
    room_id: str, draft: bool = False, user=Depends(require_space_access)
):
    return await service.get_plan(room_id, user, draft)


@router.get("/rooms/{room_id}/plan/pdf")
async def export_plan_pdf(room_id: str, user=Depends(require_space_access)):
    content, filename = await service.export_plan_pdf(room_id, user)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"seat-plan.pdf\"; filename*=UTF-8''{quote(filename, safe='')}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.put("/rooms/{room_id}/plan")
async def save_plan(
    room_id: str, payload: PlanInput, user=Depends(require_space_access)
):
    return await service.save_plan(room_id, payload, user)


@router.delete("/rooms/{room_id}/plan")
async def delete_plan(
    room_id: str,
    version: int = Query(..., ge=0),
    release_assignments: bool = False,
    revision: int | None = Query(None, ge=0),
    user=Depends(require_space_access),
):
    return await service.delete_plan(room_id, version, user, release_assignments, revision)


@router.post("/rooms/{room_id}/plan/publish")
async def publish(
    room_id: str, payload: VersionInput, user=Depends(require_space_access)
):
    return await service.publish_plan(room_id, payload.version, user)


@router.post("/rooms/{room_id}/plan/clone", status_code=201)
async def clone(room_id: str, payload: CloneInput, user=Depends(require_space_access)):
    return await service.clone_plan(room_id, payload, user)


@router.put("/seats/{seat_id}/assignment")
async def assign(
    seat_id: str, payload: AssignmentInput, user=Depends(require_space_access)
):
    return await service.assign(
        seat_id, payload.person_id, payload.revision, user, payload.team_id
    )


@router.delete("/seats/{seat_id}/assignment")
async def unassign(
    seat_id: str, revision: int = Query(..., ge=0), user=Depends(require_space_access)
):
    return await service.unassign(seat_id, revision, user)
