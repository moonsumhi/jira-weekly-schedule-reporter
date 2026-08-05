from __future__ import annotations
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import pytz
from dateutil import parser as dtparser

KST = pytz.timezone("Asia/Seoul")


def next_9am_kst(now_utc: datetime) -> datetime:
    """now_utc(UTC, tz-aware) 이후 가장 가까운 09:00 KST를 UTC로 반환한다."""
    now_kst = now_utc.astimezone(KST)
    candidate = now_kst.replace(hour=9, minute=0, second=0, microsecond=0)
    if candidate <= now_kst:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc)


@dataclass(frozen=True)
class TimeProvider:
    tz: str = "Asia/Seoul"

    def parse(self, s: str) -> datetime:
        dt = dtparser.parse(s)
        if dt.tzinfo is None:
            return KST.localize(dt)
        return dt

    def to_utc(self, dt: datetime) -> datetime:
        return dt.astimezone(timezone.utc)

    def to_kst(self, dt: datetime) -> datetime:
        return dt.astimezone(KST)


class TimeUtil:
    provider = TimeProvider()

    @staticmethod
    def ensure_utc(s: str) -> datetime:
        return TimeUtil.provider.to_utc(TimeUtil.provider.parse(s))

    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)
