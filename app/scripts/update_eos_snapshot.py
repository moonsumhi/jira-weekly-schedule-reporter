"""Collect unreviewed feed candidates, or render vendor-reviewed offline snapshots.

Scheduled automation uses --candidate-report and never changes runtime data.
--render-reviewed requires no network; only lifecycle_audit.json supplies dates.
The legacy invocation still collects feeds but cannot override reviewed facts.
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

# 직접 실행과 모듈 실행에서 동일한 순수 매핑 함수를 사용한다.
if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.lifecycle_mapping import update_vmware_dates
from app.lifecycle_audit import reviewed_eos_map

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


def build_snapshot(path: Path, frontend_output: Path | None = None, candidate_report: Path | None = None) -> tuple[int, int]:
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
    result = {} if candidate_report is not None else dict(existing)
    for slug, display in PRODUCT_DISPLAY.items():
        for entry in fetched.get(slug, []):
            update_vmware_dates(result, display, entry)
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


    aliases: dict[str, str] = {}
    for key, value in result.items():
        if key.startswith("Windows Server|"):
            cycle = key[len("Windows Server|"):]
            normalized = re.sub(r"-r2$", " R2", cycle, flags=re.IGNORECASE)
            if normalized != cycle:
                aliases[f"Windows Server|{normalized}"] = value
    result.update(aliases)

    if candidate_report is not None:
        reviewed = reviewed_eos_map({})
        payload = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "status": "unreviewed_candidates_only",
            "failed_products": sorted(failures),
            "changes": {key: {"reviewed": reviewed.get(key), "candidate": value}
                        for key, value in sorted(result.items()) if reviewed.get(key) != value},
        }
        candidate_report.parent.mkdir(parents=True, exist_ok=True)
        candidate_report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return len(payload["changes"]), len(fetched)

    return write_reviewed_snapshot(path, frontend_output, len(fetched), failures)


def write_reviewed_snapshot(path: Path, frontend_output: Path | None = None,
                            success_count: int = 0, failures: list[str] | None = None) -> tuple[int, int]:
    """Render reviewed facts offline. Candidate API responses are never inputs."""
    existing = read_existing(path)
    result = reviewed_eos_map({})
    if frontend_output is not None:
        vmware = {key: value for key, value in sorted(result.items())
                  if key.startswith(("ESXi|", "vCenter|"))}
        frontend_output.parent.mkdir(parents=True, exist_ok=True)
        frontend_tmp = frontend_output.with_suffix(".json.tmp")
        frontend_tmp.write_text(json.dumps(vmware, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        frontend_tmp.replace(frontend_output)

    if result == existing:
        logger.info("EoS 데이터 변경 없음: 기존 snapshot을 유지합니다.")
        return len(result), success_count

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "vendor-reviewed lifecycle_audit.json",
        "successful_products": success_count,
        "failed_products": sorted(failures or []),
        "data": dict(sorted(result.items())),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)
    return len(result), success_count


def main() -> int:
    default_output = Path(__file__).resolve().parents[1] / "data" / "eos_map_snapshot.json"
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--frontend-output", type=Path,
                        help="VMware 프런트엔드 오프라인 맵도 함께 생성")
    parser.add_argument("--candidate-report", type=Path, help="검토 후보 보고서만 생성; 배포 데이터 변경 없음")
    parser.add_argument("--render-reviewed", action="store_true", help="외부 조회 없이 검증 원본으로 스냅샷 생성")
    args = parser.parse_args()
    if args.render_reviewed and args.candidate_report:
        parser.error("--render-reviewed and --candidate-report are mutually exclusive")
    if args.frontend_output is None and args.output == default_output:
        args.frontend_output = Path(__file__).resolve().parents[2] / "frontend/optool/src/data/vmware_lifecycle_snapshot.json"
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        if args.render_reviewed:
            item_count, success_count = write_reviewed_snapshot(args.output, args.frontend_output)
        else:
            item_count, success_count = build_snapshot(args.output, args.frontend_output, args.candidate_report)
    except Exception as exc:
        logger.error("EoS snapshot 갱신 실패: %s", exc)
        return 1
    logger.info("EoS snapshot 갱신 완료: %d개 항목 (%d개 API 성공)", item_count, success_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
