"""End-of-Service 날짜 맵 빌드 및 메모리/파일 캐시 관리."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict

import httpx

from app.lifecycle_mapping import update_vmware_dates
from app.lifecycle_audit import reviewed_eos_map

logger = logging.getLogger(__name__)

_SNAPSHOT_ENV = "EOS_SNAPSHOT_PATH"
_BUNDLED_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "eos_map_snapshot.json"

# Rocky Linux / RHEL / CentOS 는 endoflife.date 가 마이너 버전 단위 사이클만 제공하며
# 현재 지원 중인 최신 마이너의 eol 이 false 이므로 메이저 버전 키를 직접 정의한다.
STATIC_FALLBACK: Dict[str, str] = reviewed_eos_map({})

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
                update_vmware_dates(result, display, entry)
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
    return reviewed_eos_map(result), success_count


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
        return reviewed_eos_map(normalized)
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
