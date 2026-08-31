"""외부망에서 endoflife.date 데이터를 받아 소스 반입용 EoS snapshot을 갱신한다.

별도 패키지 설치 없이 자동화할 수 있도록 Python 표준 라이브러리만 사용한다.
외부 API가 전부 실패하면 기존 파일을 건드리지 않고 실패 코드로 종료한다.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

logger = logging.getLogger("update_eos_snapshot")

PRODUCT_DISPLAY = {
    "rocky-linux": "Rocky Linux",
    "centos": "CentOS",
    "rhel": "RHEL",
    "ubuntu": "Ubuntu",
    "debian": "Debian",
    "amazon-linux": "Amazon Linux",
    "windowsserver": "Windows Server",
    "mariadb": "MariaDB",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mssqlserver": "MS SQL Server",
    "esxi": "ESXi",
    "vcenter": "vCenter",
}
WINDOWS_SLUG = "windows"


def ssl_context() -> ssl.SSLContext:
    configured = os.getenv("SSL_CERT_FILE")
    candidates = [
        configured,
        ssl.get_default_verify_paths().cafile,
        "/etc/ssl/cert.pem",
        "/etc/ssl/certs/ca-certificates.crt",
    ]
    cafile = next((path for path in candidates if path and Path(path).is_file()), None)
    return ssl.create_default_context(cafile=cafile)


SSL_CONTEXT = ssl_context()


def parse_eol(value: Any) -> str | None:
    if not value or value is False:
        return None
    parts = str(value).split("-")
    return f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else None


def fetch_product(slug: str) -> list[dict[str, Any]]:
    request = Request(
        f"https://endoflife.date/api/{slug}.json",
        headers={"User-Agent": "jira-reporter-eos-snapshot/1.0"},
    )
    with urlopen(request, timeout=15, context=SSL_CONTEXT) as response:  # noqa: S310 - 고정된 신뢰 URL만 사용
        data = json.load(response)
    if not isinstance(data, list):
        raise ValueError(f"unexpected response for {slug}")
    return [entry for entry in data if isinstance(entry, dict)]


def read_existing(path: Path) -> dict[str, str]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        data = raw.get("data", raw) if isinstance(raw, dict) else {}
        return {
            str(key): str(value)
            for key, value in data.items()
            if isinstance(key, str) and isinstance(value, str)
        }
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning("기존 snapshot을 읽지 못했습니다: %s", exc)
        return {}


def build_snapshot(path: Path) -> tuple[int, int]:
    slugs = [*PRODUCT_DISPLAY, WINDOWS_SLUG]
    fetched: dict[str, list[dict[str, Any]]] = {}
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=len(slugs)) as executor:
        futures = {executor.submit(fetch_product, slug): slug for slug in slugs}
        for future in as_completed(futures):
            slug = futures[future]
            try:
                fetched[slug] = future.result()
            except Exception as exc:
                failures.append(slug)
                logger.warning("%s 조회 실패: %s", slug, exc)

    if not fetched:
        raise RuntimeError("외부 EoS API가 모두 실패했습니다. 기존 snapshot을 유지합니다.")

    existing = read_existing(path)
    result = dict(existing)
    for slug, display in PRODUCT_DISPLAY.items():
        for entry in fetched.get(slug, []):
            cycle = str(entry.get("cycle", ""))
            eol = parse_eol(entry.get("eol"))
            if cycle and eol:
                result[f"{display}|{cycle}"] = eol

    for entry in fetched.get(WINDOWS_SLUG, []):
        cycle = str(entry.get("cycle", ""))
        eol = parse_eol(entry.get("eol"))
        if not cycle or not eol:
            continue
        if cycle.startswith("10-"):
            result[f"Windows 10|{cycle[3:]}"] = eol
        elif cycle.startswith("11-"):
            result[f"Windows 11|{cycle[3:]}"] = eol
        elif cycle in {"10", "11"}:
            result[f"Windows {cycle}|{cycle}"] = eol

    for win_name in ("Windows 10", "Windows 11"):
        prefix = f"{win_name}|"
        dates = [value for key, value in result.items() if key.startswith(prefix)]
        if dates:
            result[f"{win_name}|{win_name}"] = max(dates)

    aliases: dict[str, str] = {}
    for key, value in result.items():
        if key.startswith("Windows Server|"):
            cycle = key[len("Windows Server|"):]
            normalized = re.sub(r"-r2$", " R2", cycle, flags=re.IGNORECASE)
            if normalized != cycle:
                aliases[f"Windows Server|{normalized}"] = value
    result.update(aliases)

    if result == existing:
        logger.info("EoS 데이터 변경 없음: 기존 snapshot을 유지합니다.")
        return len(result), len(fetched)

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "endoflife.date",
        "successful_products": len(fetched),
        "failed_products": sorted(failures),
        "data": dict(sorted(result.items())),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)
    return len(result), len(fetched)


def main() -> int:
    default_output = Path(__file__).resolve().parents[1] / "data" / "eos_map_snapshot.json"
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=default_output)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        item_count, success_count = build_snapshot(args.output)
    except Exception as exc:
        logger.error("EoS snapshot 갱신 실패: %s", exc)
        return 1
    logger.info("EoS snapshot 갱신 완료: %d개 항목 (%d개 API 성공)", item_count, success_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
