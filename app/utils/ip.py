"""IP 기반 내부/외부 접속 판별"""
import ipaddress
import time

from fastapi import Request

# 내부 IP 목록 캐시 (60초 TTL)
_cache: dict = {"ips": [], "at": 0.0}
_TTL = 60.0

# RFC 1918 / 사설 IPv4 대역
_PRIVATE_V4 = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]
# 사설 IPv6 대역 (로컬, ULA, 링크로컬, IPv4-mapped 포함)
_PRIVATE_V6 = [
    ipaddress.ip_network("::1/128"),          # loopback
    ipaddress.ip_network("fc00::/7"),          # Unique Local
    ipaddress.ip_network("fe80::/10"),         # Link-local
    ipaddress.ip_network("::ffff:0:0/96"),     # IPv4-mapped
    ipaddress.ip_network("64:ff9b::/96"),      # IPv4/IPv6 translator
]


def _normalize_ip(raw: str) -> str:
    """포트 제거 및 IPv4-mapped IPv6(::ffff:a.b.c.d) → IPv4 변환"""
    ip = raw.strip()
    # [::1]:8080 형식
    if ip.startswith("["):
        ip = ip[1:ip.find("]")]
    # IPv4:port 형식 (콜론 1개이면 포트 포함)
    elif ":" not in ip:
        pass  # pure IPv4
    elif ip.count(":") == 1:
        ip = ip.split(":")[0]
    # IPv4-mapped: ::ffff:192.168.1.1
    if ip.lower().startswith("::ffff:") and "." in ip:
        ip = ip[7:]
    return ip


def _is_private_ip(raw: str) -> bool:
    ip = _normalize_ip(raw)
    try:
        addr = ipaddress.ip_address(ip)
        if isinstance(addr, ipaddress.IPv4Address):
            return any(addr in net for net in _PRIVATE_V4)
        else:
            return any(addr in net for net in _PRIVATE_V6)
    except ValueError:
        return False


async def _load_internal_ips() -> list[str]:
    now = time.monotonic()
    if now - _cache["at"] < _TTL:
        return _cache["ips"]

    try:
        from app.db.mongo import MongoClientManager
        col = MongoClientManager.get_db()[MongoClientManager.APP_SETTINGS]
        doc = await col.find_one({"key": "internal_ips"})
        raw = doc.get("value", "") if doc else ""
        ips = [s.strip() for s in raw.replace("\n", ",").split(",") if s.strip()]
    except Exception:
        ips = []

    _cache["ips"] = ips
    _cache["at"] = now
    return ips


def _get_client_ip(request: Request) -> str:
    """nginx 프록시 환경에서 실제 클라이언트 IP 추출 (포트/IPv6 정규화 포함)"""
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return _normalize_ip(real_ip)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return _normalize_ip(forwarded.split(",")[0])
    host = request.client.host if request.client else "127.0.0.1"
    return _normalize_ip(host)


def _matches(client_ip: str, pattern: str) -> bool:
    """CIDR, IP 프리픽스, 정확한 IP 매칭"""
    try:
        if "/" in pattern:
            return ipaddress.ip_address(client_ip) in ipaddress.ip_network(pattern, strict=False)
        return client_ip == pattern or client_ip.startswith(pattern)
    except ValueError:
        return False


async def is_internal_ip(request: Request) -> bool:
    """현재 요청 IP가 내부 접속인지 확인.

    판별 순서:
    1. 사설 IP 대역(RFC 1918)이면 항상 내부 — LAN/Docker 환경 대응
    2. 내부 IP 목록이 설정된 경우 해당 목록으로 추가 매칭
    3. 목록 미설정 + 공인 IP → 외부 접속
    """
    client_ip = _get_client_ip(request)

    # 사설 IP는 항상 내부 (Docker 게이트웨이, 사내망 모두 포함)
    if _is_private_ip(client_ip):
        return True

    # 공인 IP인 경우 추가 허용 목록 확인
    internal_ips = await _load_internal_ips()
    return any(_matches(client_ip, pattern) for pattern in internal_ips)


def invalidate_cache():
    """설정 변경 시 캐시 무효화"""
    _cache["at"] = 0.0
