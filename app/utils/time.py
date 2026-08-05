from __future__ import annotations
from datetime import datetime, timezone
from dataclasses import dataclass
import pytz
from dateutil import parser as dtparser

KST = pytz.timezone("Asia/Seoul")


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
