"""End-of-Support 날짜 맵 빌드 및 24시간 캐시 관리."""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)

_CACHE_TTL = 86400  # 24h

# Rocky Linux / RHEL / CentOS 는 endoflife.date 가 마이너 버전 단위 사이클만 제공하며
# 현재 지원 중인 최신 마이너의 eol 이 false 이므로 메이저 버전 키를 직접 정의한다.
STATIC_FALLBACK: Dict[str, str] = {
    "Rocky Linux|8": "2029-05",
    "Rocky Linux|9": "2032-05",
    "RHEL|7":        "2024-06",
    "RHEL|8":        "2029-05",
    "RHEL|9":        "2032-05",
    "CentOS|6":      "2020-11",
    "CentOS|7":      "2024-06",
    "CentOS|8":      "2021-12",
    "Oracle|12c R1": "2022-07",
    "Oracle|12c R2": "2022-03",
    "Oracle|19c":    "2027-04",
    "Oracle|21c":    "2024-04",
    "Oracle|23c":    "2030-04",
    "SAP HANA|1.0":  "2023-12",
    "SAP HANA|2.0":  "2030-12",
}

# endoflife.date 슬러그 → 표시명
_PRODUCT_DISPLAY: Dict[str, str] = {
    "rocky-linux":    "Rocky Linux",
    "centos":         "CentOS",
    "rhel":           "RHEL",
    "ubuntu":         "Ubuntu",
    "debian":         "Debian",
    "amazon-linux":   "Amazon Linux",
    "windowsserver":  "Windows Server",
    "mariadb":        "MariaDB",
    "postgresql":     "PostgreSQL",
    "mysql":          "MySQL",
    "mssqlserver":    "MS SQL Server",
    "esxi":           "ESXi",
    "vcenter":        "vCenter",
}

_WINDOWS_SLUG = "windows"


def _parse_eol(eol: Any) -> str | None:
    """eol 필드를 'YYYY-MM' 문자열로 변환. false/None 이면 None 반환."""
    if not eol or eol is False:
        return None
    s = str(eol)
    parts = s.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    return None


async def _fetch_product(client: httpx.AsyncClient, slug: str) -> list:
    try:
        r = await client.get(
            f"https://endoflife.date/api/{slug}.json",
            timeout=10,
            follow_redirects=True,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("endoflife.date fetch failed for %s: %s", slug, e)
        return []


async def build_eos_map() -> Dict[str, str]:
    """endoflife.date API를 호출해 EoS 날짜 맵을 빌드한다."""
    result: Dict[str, str] = dict(STATIC_FALLBACK)

    async with httpx.AsyncClient() as client:
        for slug, display in _PRODUCT_DISPLAY.items():
            cycles = await _fetch_product(client, slug)
            for entry in cycles:
                cycle = str(entry.get("cycle", ""))
                eol = _parse_eol(entry.get("eol"))
                if cycle and eol:
                    result[f"{display}|{cycle}"] = eol

        win_cycles = await _fetch_product(client, _WINDOWS_SLUG)
        for entry in win_cycles:
            cycle = str(entry.get("cycle", ""))
            eol = _parse_eol(entry.get("eol"))
            if not cycle or not eol:
                continue
            if cycle.startswith("10-"):
                result[f"Windows 10|{cycle[3:]}"] = eol
            elif cycle.startswith("11-"):
                result[f"Windows 11|{cycle[3:]}"] = eol
            elif cycle == "10":
                result["Windows 10|10"] = eol
            elif cycle == "11":
                result["Windows 11|11"] = eol

    # Windows 10/11: 버전 없이 OS명만 있을 때를 위한 최신 EoS 폴백 키
    for win_name in ("Windows 10", "Windows 11"):
        prefix = f"{win_name}|"
        dates = [v for k, v in result.items() if k.startswith(prefix)]
        if dates:
            result[f"{win_name}|{win_name}"] = max(dates)

    # Windows Server R2 alias: "2012-R2" → "2012 R2" 형식도 조회 가능하도록
    ws_aliases: Dict[str, str] = {}
    for key, val in result.items():
        if key.startswith("Windows Server|"):
            cycle = key[len("Windows Server|"):]
            normalized = re.sub(r"-r2$", " R2", cycle, flags=re.IGNORECASE)
            if normalized != cycle:
                ws_aliases[f"Windows Server|{normalized}"] = val
    result.update(ws_aliases)

    return result


class EosService:
    """EoS 맵 빌드 결과를 24시간 캐시하는 서비스."""

    _cache_data: Dict[str, str] | None = None
    _cache_ts: float = 0.0

    @classmethod
    async def get_eos_map(cls) -> Dict[str, str]:
        now = time.time()
        if cls._cache_data is None or now - cls._cache_ts > _CACHE_TTL:
            logger.info("EoS map 캐시 갱신 중...")
            cls._cache_data = await build_eos_map()
            cls._cache_ts = now
            logger.info("EoS map %d개 항목 로드 완료", len(cls._cache_data))
        return cls._cache_data
