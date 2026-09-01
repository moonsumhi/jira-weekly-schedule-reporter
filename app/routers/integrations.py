"""외부 서비스가 사용하는 최소 범위의 연동 API."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from app.core.config import settings
from app.db.mongo import MongoClientManager


router = APIRouter()

_INCIDENT_NOTIFY_CATEGORY_KEY = "incident_notify_emails"
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class IncidentNotificationRecipient(BaseModel):
    name: str
    email: str


class IncidentNotificationRecipientsResponse(BaseModel):
    recipients: list[IncidentNotificationRecipient]
    count: int


async def require_incident_notify_api_key(
    api_key: str | None = Depends(_api_key_header),
) -> None:
    configured_key = settings.INCIDENT_NOTIFY_API_KEY
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="장애 알림 연동 API가 설정되지 않았습니다.",
        )
    if not api_key or not secrets.compare_digest(api_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 API 키입니다.",
        )


@router.get(
    "/incident-notification/recipients",
    response_model=IncidentNotificationRecipientsResponse,
    dependencies=[Depends(require_incident_notify_api_key)],
)
async def list_incident_notification_recipients(
    response: Response,
) -> IncidentNotificationRecipientsResponse:
    """관리자 환경설정에 등록된 활성 장애 알림 메일 대상자를 반환한다."""
    response.headers["Cache-Control"] = "no-store"

    collection = MongoClientManager.get_env_categories_collection()
    category = await collection.find_one({"key": _INCIDENT_NOTIFY_CATEGORY_KEY})
    items = sorted(
        category.get("items", []) if category else [],
        key=lambda item: item.get("sort_order", 0),
    )

    recipients: list[IncidentNotificationRecipient] = []
    seen_emails: set[str] = set()
    for item in items:
        if not item.get("is_active", True):
            continue

        email = str(item.get("value") or "").strip()
        normalized_email = email.casefold()
        if not email or normalized_email in seen_emails:
            continue

        name = str(item.get("label") or "").strip() or email
        recipients.append(IncidentNotificationRecipient(name=name, email=email))
        seen_emails.add(normalized_email)

    return IncidentNotificationRecipientsResponse(
        recipients=recipients,
        count=len(recipients),
    )
