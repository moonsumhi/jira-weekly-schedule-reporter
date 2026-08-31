"""End-of-Support 날짜 맵 빌드 및 메모리/파일 캐시 관리."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)

_SNAPSHOT_ENV = "EOS_SNAPSHOT_PATH"
_BUNDLED_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "eos_map_snapshot.json"

# Rocky Linux / RHEL / CentOS 는 endoflife.date 가 마이너 버전 단위 사이클만 제공하며
# 현재 지원 중인 최신 마이너의 eol 이 false 이므로 메이저 버전 키를 직접 정의한다.
STATIC_FALLBACK: Dict[str, str] = {
    # Rocky Linux (https://wiki.rockylinux.org/rocky/version/)
    "Rocky Linux|8":    "2029-05",
    "Rocky Linux|8.3":  "2021-06",
    "Rocky Linux|8.4":  "2021-11",
    "Rocky Linux|8.5":  "2022-05",
    "Rocky Linux|8.6":  "2022-11",
    "Rocky Linux|8.7":  "2023-05",
    "Rocky Linux|8.8":  "2023-11",
    "Rocky Linux|8.9":  "2024-05",
    "Rocky Linux|8.10": "2029-05",
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
    # Windows Server (endoflife.date 외부 API 호출 실패 시 폴백 — 내부망 등 인터넷 접근이
    # 막힌 환경에서도 EoS 표시가 "확인 불가"로 비지 않도록 함)
    "Windows Server|2000":       "2010-07",
    "Windows Server|2003":       "2007-04",
    "Windows Server|2003-sp1":   "2009-04",
    "Windows Server|2003-sp2":   "2015-07",
    "Windows Server|2008-sp2":   "2020-01",
    "Windows Server|2008-r2-sp1": "2020-01",
    "Windows Server|2012":       "2023-10",
    "Windows Server|2012 R2":    "2023-10",
    "Windows Server|1709-sac":   "2019-04",
    "Windows Server|1803-sac":   "2019-11",
    "Windows Server|1809-sac":   "2020-11",
    "Windows Server|1903-sac":   "2020-12",
    "Windows Server|1909-sac":   "2021-05",
    "Windows Server|2004-sac":   "2021-12",
    "Windows Server|20h2-sac":   "2022-08",
    "Windows Server|2016":       "2027-01",
    "Windows Server|2019":       "2029-01",
    "Windows Server|2022":       "2031-10",
    "Windows Server|23h2-ac":    "2026-05",
    "Windows Server|2025":       "2034-11",
    # Windows Server: OS_TREE 드롭다운은 "-sac" 접미사 없이 저장되므로 그 형식으로도 조회 가능하게 별칭 추가
    "Windows Server|1909": "2021-05",
    "Windows Server|2004": "2021-12",
    "Windows Server|20H2": "2022-08",
    # Windows 10 / 11 (endoflife.date 폴백)
    "Windows 10|22H2": "2025-10",
    "Windows 11|21H2": "2024-10",
    "Windows 11|22H2": "2025-10",
    "Windows 11|23H2": "2026-11",
    # Ubuntu (Standard Support 종료 기준)
    "Ubuntu|18.04": "2023-04",
    "Ubuntu|20.04": "2025-04",
    "Ubuntu|22.04": "2027-04",
    "Ubuntu|24.04": "2029-04",
    # Debian (LTS 종료 기준)
    "Debian|10": "2024-06",
    "Debian|11": "2026-06",
    "Debian|12": "2028-06",
    # Amazon Linux
    "Amazon Linux|2":    "2025-06",
    "Amazon Linux|2023": "2028-03",
    # MariaDB
    "MariaDB|10.2":  "2022-05",
    "MariaDB|10.3":  "2023-05",
    "MariaDB|10.4":  "2024-06",
    "MariaDB|10.5":  "2025-06",
    "MariaDB|10.6":  "2026-07",
    "MariaDB|10.11": "2028-02",
    "MariaDB|11.0":  "2024-06",
    "MariaDB|11.1":  "2024-08",
    "MariaDB|11.2":  "2024-11",
    "MariaDB|11.3":  "2025-02",
    "MariaDB|11.4":  "2029-05",
    # PostgreSQL
    "PostgreSQL|12": "2024-11",
    "PostgreSQL|13": "2025-11",
    "PostgreSQL|14": "2026-11",
    "PostgreSQL|15": "2027-11",
    "PostgreSQL|16": "2028-11",
    "PostgreSQL|17": "2029-11",
    # MySQL (Extended Support 종료 기준)
    "MySQL|5.7": "2023-10",
    "MySQL|8.0": "2026-04",
    "MySQL|8.4": "2032-04",
    # MS SQL Server (Extended Support 종료 기준)
    "MS SQL Server|2017": "2027-10",
    "MS SQL Server|2019": "2030-01",
    "MS SQL Server|2022": "2033-01",
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


async def _fetch_product(client: httpx.AsyncClient, slug: str) -> tuple[list, bool]:
    try:
        r = await client.get(
            f"https://endoflife.date/api/{slug}.json",
            timeout=10,
            follow_redirects=True,
        )
        r.raise_for_status()
        data = r.json()
        return (data if isinstance(data, list) else []), True
    except Exception as e:
        logger.warning("endoflife.date fetch failed for %s: %s", slug, e)
        return [], False


async def _build_eos_map_with_status(base: Dict[str, str] | None = None) -> tuple[Dict[str, str], int]:
    """외부 API를 병렬 호출해 EoS 맵과 성공한 API 수를 반환한다."""
    result: Dict[str, str] = dict(STATIC_FALLBACK)
    if base:
        result.update(base)

    async with httpx.AsyncClient() as client:
        slugs = [*_PRODUCT_DISPLAY, _WINDOWS_SLUG]
        responses = await asyncio.gather(*(_fetch_product(client, slug) for slug in slugs))
        fetched = dict(zip(slugs, responses))

        for slug, display in _PRODUCT_DISPLAY.items():
            cycles, _ = fetched[slug]
            for entry in cycles:
                cycle = str(entry.get("cycle", ""))
                eol = _parse_eol(entry.get("eol"))
                if cycle and eol:
                    result[f"{display}|{cycle}"] = eol

        win_cycles, _ = fetched[_WINDOWS_SLUG]
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

    success_count = sum(1 for _, succeeded in responses if succeeded)
    return result, success_count


async def build_eos_map() -> Dict[str, str]:
    """endoflife.date API를 호출해 EoS 날짜 맵을 빌드한다."""
    result, _ = await _build_eos_map_with_status()
    return result


def _snapshot_path() -> Path:
    return Path(os.getenv(_SNAPSHOT_ENV, str(_BUNDLED_SNAPSHOT_PATH))).expanduser()


def _read_snapshot() -> Dict[str, str] | None:
    path = _snapshot_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        data = raw.get("data", raw) if isinstance(raw, dict) else None
        if not isinstance(data, dict):
            raise ValueError("snapshot data must be an object")
        normalized = {
            str(key): str(value)
            for key, value in data.items()
            if isinstance(key, str) and isinstance(value, str) and key and value
        }
        if not normalized:
            raise ValueError("snapshot is empty")
        logger.info("EoS snapshot %d개 항목 로드: %s", len(normalized), path)
        return normalized
    except FileNotFoundError:
        logger.warning("EoS snapshot 파일 없음: %s", path)
    except Exception as e:
        logger.warning("EoS snapshot 로드 실패 (%s): %s", path, e)
        return None


class EosService:
    """저장소에 포함된 EoS snapshot을 메모리에 캐시하는 서비스."""

    _cache_data: Dict[str, str] | None = None

    @classmethod
    async def get_eos_map(cls) -> Dict[str, str]:
        if cls._cache_data is None:
            snapshot = _read_snapshot()
            cls._cache_data = dict(STATIC_FALLBACK)
            if snapshot:
                cls._cache_data.update(snapshot)

        return cls._cache_data
