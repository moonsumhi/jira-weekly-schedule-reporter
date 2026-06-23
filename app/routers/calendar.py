"""Google Calendar ICS 피드 → JSON 이벤트"""
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from icalendar import Calendar

from app.models.user import UserPublic
from app.routers.auth import get_current_user

router = APIRouter()

# ICS 피드 URL (서버 사이드 전용, 클라이언트에 노출되지 않음)
_ICS_URL = (
    "https://calendar.google.com/calendar/ical/"
    "ncdcteam22%40gmail.com/"
    "private-5cad84bbf84f02f133121c6ae2c14539/basic.ics"
)


def _to_dt(v: Any) -> tuple[datetime, bool]:
    """(datetime, allDay) 반환"""
    if isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc), False
        return v, False
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day, tzinfo=timezone.utc), True
    return datetime.now(timezone.utc), False


@router.get("/events")
async def get_events(current_user: UserPublic = Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(_ICS_URL)
            resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"캘린더 조회 실패: {exc}")

    try:
        cal = Calendar.from_ical(resp.content)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"캘린더 파싱 실패: {exc}")

    now = datetime.now(timezone.utc)
    cutoff_past = now - timedelta(days=60)
    cutoff_future = now + timedelta(days=180)

    events = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        dtstart = component.get("DTSTART")
        dtend = component.get("DTEND")
        if dtstart is None:
            continue

        start, all_day = _to_dt(dtstart.dt)
        end, _ = _to_dt(dtend.dt) if dtend else (start, all_day)

        if end < cutoff_past or start > cutoff_future:
            continue

        events.append({
            "title": str(component.get("SUMMARY", "")),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "description": str(component.get("DESCRIPTION", "") or ""),
            "location": str(component.get("LOCATION", "") or ""),
            "allDay": all_day,
        })

    events.sort(key=lambda x: x["start"])
    return events
