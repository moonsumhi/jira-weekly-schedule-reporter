"""세션(Access Token) 만료 시간 — app.settings(DB) 값을 우선 사용, 없으면 .env 기본값."""
import time

from app.core.config import settings

KEY_INTERNAL = "access_token_expire_minutes"
KEY_EXTERNAL = "access_token_expire_minutes_external"

# DB 조회 캐시 (60초 TTL) — app/utils/ip.py의 internal_ips 캐시와 동일한 패턴
_cache: dict = {"internal": None, "external": None, "at": 0.0}
_TTL = 60.0


def _parse_minutes(value) -> int | None:
    try:
        minutes = int(value)
        return minutes if minutes > 0 else None
    except (TypeError, ValueError):
        return None


async def _load() -> None:
    now = time.monotonic()
    if now - _cache["at"] < _TTL:
        return

    from app.db.mongo import MongoClientManager
    col = MongoClientManager.get_db()[MongoClientManager.APP_SETTINGS]
    internal_doc = await col.find_one({"key": KEY_INTERNAL})
    external_doc = await col.find_one({"key": KEY_EXTERNAL})

    _cache["internal"] = _parse_minutes(internal_doc.get("value") if internal_doc else None)
    _cache["external"] = _parse_minutes(external_doc.get("value") if external_doc else None)
    _cache["at"] = now


async def get_expire_minutes(is_external: bool) -> int:
    """DB 설정값이 있으면 그 값을, 없으면 .env(Settings) 기본값을 반환."""
    await _load()
    if is_external:
        return _cache["external"] or settings.ACCESS_TOKEN_EXPIRE_MINUTES_EXTERNAL
    return _cache["internal"] or settings.ACCESS_TOKEN_EXPIRE_MINUTES


def invalidate_cache():
    """설정 변경 시 캐시 무효화"""
    _cache["at"] = 0.0
