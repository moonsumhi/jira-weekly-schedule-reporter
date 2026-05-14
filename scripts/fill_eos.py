"""
기존 자산 데이터에 EoS 여부/날짜 자동 채우기
- 운영체제 + version → endoflife.date 조회
- 네트워크/정보보호시스템 → fields.eos_date가 있으면 상태만 계산
"""
import asyncio
import re
from datetime import date
from typing import Optional
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb://jira_user:nccrekr1%21@172.18.0.2:27017/backoffice?authSource=backoffice"
EOS_STATUS_KEY = "eos_action_status"
EOS_DATE_KEY = "eos_date"
TODAY = date.today().strftime("%Y-%m")

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

COLLECTIONS = {
    "서버":      ("assets_servers",  "assets_server_history"),
    "네트워크":  ("assets_network",  "assets_network_history"),
    "정보보호시스템": ("assets_security", "assets_security_history"),
    "DBMS":     ("assets_dbms",     "assets_dbms_history"),
    "VMware":   ("assets_vmware",   "assets_vmware_history"),
}


STATIC_FALLBACK = {
    # Rocky Linux / RHEL / CentOS: endoflife.date 는 마이너 버전 단위 사이클만 제공하며
    # 현재 지원 중인 최신 마이너의 eol 이 false 이므로 메이저 버전 키를 직접 추가한다.
    "Rocky Linux|8": "2029-05",
    "Rocky Linux|9": "2032-05",
    "RHEL|7": "2024-06",
    "RHEL|8": "2029-05",
    "RHEL|9": "2032-05",
    "CentOS|6": "2020-11",
    "CentOS|7": "2024-06",
    "CentOS|8": "2021-12",
    # Oracle DB
    "Oracle|12c R1": "2022-07",
    "Oracle|12c R2": "2022-03",
    "Oracle|19c":    "2027-04",
    "Oracle|21c":    "2024-04",
    "Oracle|23c":    "2030-04",
    # SAP HANA
    "SAP HANA|1.0":  "2023-12",
    "SAP HANA|2.0":  "2030-12",
}


async def build_eos_map() -> dict:
    result = dict(STATIC_FALLBACK)
    async with httpx.AsyncClient(timeout=15) as client:
        for slug, display in PRODUCT_DISPLAY.items():
            try:
                r = await client.get(f"https://endoflife.date/api/{slug}.json", follow_redirects=True)
                r.raise_for_status()
                for entry in r.json():
                    cycle = str(entry.get("cycle", ""))
                    eol = entry.get("eol")
                    if not eol or eol is False:
                        continue
                    eol_str = str(eol)[:7]  # YYYY-MM
                    if len(eol_str) >= 7:
                        result[f"{display}|{cycle}"] = eol_str
            except Exception as e:
                print(f"  skip {slug}: {e}")

        # Windows 10/11
        try:
            r = await client.get("https://endoflife.date/api/windows.json", follow_redirects=True)
            r.raise_for_status()
            for entry in r.json():
                cycle = str(entry.get("cycle", ""))
                eol = entry.get("eol")
                if not eol or eol is False:
                    continue
                eol_str = str(eol)[:7]
                if cycle.startswith("10-"):
                    result[f"Windows 10|{cycle[3:]}"] = eol_str
                elif cycle.startswith("11-"):
                    result[f"Windows 11|{cycle[3:]}"] = eol_str
                elif cycle == "10":
                    result["Windows 10|10"] = eol_str
                elif cycle == "11":
                    result["Windows 11|11"] = eol_str
        except Exception as e:
            print(f"  skip windows: {e}")

    print(f"EoS 맵 로드 완료: {len(result)}개 항목")
    return result


OS_NORMALIZE = {
    "rockylinux":               "Rocky Linux",
    "rocky linux":              "Rocky Linux",
    "centos linux":             "CentOS",
    "centos":                   "CentOS",
    "red hat enterprise linux": "RHEL",
    "rhel":                     "RHEL",
    "ubuntu":                   "Ubuntu",
    "debian":                   "Debian",
    "amazon linux":             "Amazon Linux",
    "windows server":           "Windows Server",
    "windowsserver":            "Windows Server",
    "windows 10":               "Windows 10",
    "windows 10pro":            "Windows 10",
    "windows 11":               "Windows 11",
    "mariadb":                  "MariaDB",
    "postgresql":               "PostgreSQL",
    "mysql":                    "MySQL",
    "ms sql server":            "MS SQL Server",
    "mssql":                    "MS SQL Server",
    "suse":                     None,  # 지원 안 함
    "windows":                  "Windows",  # version으로 10/11 판별
    "vmware esxi":              "ESXi",
    "vmware vcenter":           "vCenter",
    "esxi":                     "ESXi",
    "vcenter":                  "vCenter",
    "vmware vcenter server":    "vCenter",
}


def normalize_os(dist: str) -> Optional[str]:
    key = dist.strip().lower()
    for pattern, mapped in OS_NORMALIZE.items():
        if key == pattern or key.startswith(pattern + " ") or key.startswith(pattern + "-"):
            return mapped
    return dist.strip() if dist.strip() else None


def lookup_eos(eos_map: dict, dist: str, version: str) -> Optional[tuple]:
    """OS + 버전으로 EoS 날짜 조회. (status, date) 반환 또는 None."""
    if not dist:
        return None

    normalized = normalize_os(dist)
    if not normalized:
        return None

    # "Windows" + version "10"/"10pro" → "Windows 10"
    # "Windows" + version "11" → "Windows 11"
    if normalized == "Windows":
        ver_lower = version.strip().lower()
        if ver_lower.startswith("10"):
            normalized = "Windows 10"
            version = "10"
        elif ver_lower.startswith("11"):
            normalized = "Windows 11"
            version = "11"

    # Windows Server 2012R2 → try "2012-r2" and "2012"
    extra_candidates = []
    if normalized == "Windows Server" and version:
        ver_clean = version.lower().replace(" ", "")
        if "r2" in ver_clean:
            year = ver_clean.replace("r2", "").strip("-")
            extra_candidates.append(f"Windows Server|{year}-r2")
            extra_candidates.append(f"Windows Server|{year}")

    candidates = []
    if version:
        candidates.append(f"{normalized}|{version}")
        parts = version.split(".")
        if len(parts) >= 2:
            candidates.append(f"{normalized}|{parts[0]}.{parts[1]}")
        candidates.append(f"{normalized}|{parts[0]}")
    # 버전 없이 OS만
    candidates.append(f"{normalized}|{normalized}")
    candidates.extend(extra_candidates)

    for key in candidates:
        if key in eos_map:
            eol_date = eos_map[key]
            status = "EOS" if eol_date <= TODAY else "ACTIVE"
            return status, eol_date

    # Windows 10/11 폴백: 버전 매칭 실패 시 해당 제품의 최신 EoS 날짜 사용
    if normalized in ("Windows 10", "Windows 11"):
        prefix = f"{normalized}|"
        dates = [v for k, v in eos_map.items() if k.startswith(prefix)]
        if dates:
            latest = max(dates)
            status = "EOS" if latest <= TODAY else "ACTIVE"
            return status, latest

    return None


# 네트워크/정보보호시스템 기종 패턴 매핑 (프론트엔드 NETWORK_EOS_LIST 동일)
NETWORK_EOS_LIST = [
    # Nexus 2000
    ("2148t",       "2017-06"), ("2224tp",     "2017-06"), ("2232pp",     "2017-06"), ("2248tp",     "2017-06"),
    # Nexus 3000
    ("3016",        "2019-10"), ("3048",       "2021-01"), ("3064t",      "2022-01"), ("3064x",      "2022-01"),
    ("3064pq",      "2021-01"), ("3064",       "2021-01"),
    # Nexus 5000
    ("5010",        "2017-01"), ("5020",       "2017-01"), ("5548p",      "2022-01"), ("5548up",     "2022-01"),
    ("5596t",       "2022-01"), ("5596up",     "2022-01"), ("5672up16g",  "2023-08"), ("5672up",     "2023-08"),
    # Nexus 6000
    ("6001p",       "2022-10"), ("6001t",      "2022-10"), ("6004ef",     "2023-10"), ("6004",       "2023-10"),
    # Nexus 7000
    ("7004",        "2024-10"), ("7009",       "2024-10"), ("7010",       "2024-10"), ("7018",       "2024-10"),
    # Nexus 9000
    ("9372px",      "2024-04"), ("9372tx",     "2024-04"), ("9396px",     "2024-04"), ("9396tx",     "2024-04"),
    ("93120tx",     "2024-04"), ("93128tx",    "2024-04"),
    ("c93180ycex",  "2027-11"), ("93180ycex",  "2027-11"),
    ("c93180ycfx2", "2029-12"), ("93180ycfx2", "2029-12"),
    ("c9336cfx2",   "2030-12"), ("9336cfx2",   "2030-12"),
    ("c93240ycfx2", "2030-12"), ("93240ycfx2", "2030-12"),
    # Nexus 9500 chassis
    ("c9504",       "2030-12"), ("9504",       "2030-12"),
    ("c9508",       "2030-12"), ("9508",       "2030-12"),
    ("nexus9500",   "2030-12"), ("n9k9500",    "2030-12"),
    # Nexus 9332
    ("c9332c",      "2030-12"), ("9332c",      "2030-12"),
    # Cisco MDS (파이버채널)
    ("mds9148s",    "2024-10"), ("mds9148",    "2024-10"),
    # Cisco ASR
    ("asr1001x",    "2026-12"), ("asr1001",    "2026-12"),
    # Cisco Catalyst 9000
    ("c9200",       "2030-12"), ("c9300",      "2030-12"), ("c9400",      "2030-12"),
    # Cisco Catalyst 2960X
    ("2960x",       "2026-01"), ("ws-c2960x",  "2026-01"),
    # Cisco HyperFlex FI
    ("hxfi6454",    "2029-12"), ("fi6454",     "2029-12"),
    # Piolink
    ("pask3200x",   "2024-12"), ("pask3200",   "2024-12"),
    # Fujitsu PRIMERGY
    ("rx1330m4",    "2028-06"),
]


# 날짜 없이 상태만 알려진 제품 (pattern → (status, date))
NETWORK_MANUAL_STATUS = [
    # EOS
    ("secuimfd21000",     "EOS",    ""),
    ("mfd21000",          "EOS",    ""),
    ("securegate",        "EOS",    ""),
    ("chakramax",         "EOS",    ""),
    ("dguard",            "EOS",    ""),
    ("pc30",              "EOS",    ""),  # 내PC지키미 3.0 (한글 제거 후 정규화)
    # ACTIVE
    ("paloalto",          "ACTIVE", ""),
    ("secuingf",          "ACTIVE", ""),
    ("junipermag",        "ACTIVE", ""),
    ("juniper",           "ACTIVE", ""),
    ("deepsecurity",      "ACTIVE", ""),
    ("deepdiscovery",     "ACTIVE", ""),
    ("sparrow",           "ACTIVE", ""),
    ("superserver",       "ACTIVE", ""),
    ("wsus",              "ACTIVE", ""),
    ("bluemax",           "ACTIVE", ""),
    ("pcfilter",          "ACTIVE", ""),
    ("genian",            "ACTIVE", ""),
    ("dbsafer",           "ACTIVE", ""),
    ("secuve",            "ACTIVE", ""),
    ("medialand",         "ACTIVE", ""),
    ("wshield",           "ACTIVE", ""),
    ("secuway",           "ACTIVE", ""),
    ("vada",              "ACTIVE", ""),
    ("coolfilter",        "ACTIVE", ""),
    ("dellpoweredge",     "ACTIVE", ""),
    ("spamsniper",        "ACTIVE", ""),
    ("sslu3000",          "ACTIVE", ""),
    ("wapple",            "ACTIVE", ""),
    ("serveri",           "ACTIVE", ""),
    ("ntp",               "ACTIVE", ""),
    ("v3",                "ACTIVE", ""),
]


def _normalize_model(s: str) -> str:
    import re as _re
    return _re.sub(r"[^a-z0-9]", "", s.lower())


def get_network_eos(model: str) -> Optional[tuple]:
    """네트워크/정보보호시스템 기종명으로 EoS 날짜 조회."""
    if not model.strip():
        return None
    normalized = _normalize_model(model)
    # 긴 패턴 우선 — 날짜 기반 목록
    sorted_list = sorted(NETWORK_EOS_LIST, key=lambda x: -len(x[0]))
    for pattern, date in sorted_list:
        if pattern in normalized:
            status = "EOS" if date <= TODAY else "ACTIVE"
            return status, date
    # 수동 상태 목록 (날짜 없음)
    manual_sorted = sorted(NETWORK_MANUAL_STATUS, key=lambda x: -len(x[0]))
    for pattern, status, date in manual_sorted:
        if pattern in normalized:
            return status, date
    return None


def calc_status_from_date(eos_date: str) -> str:
    """YYYY-MM 형식 날짜로 상태 계산."""
    m = re.match(r"(\d{4}-\d{2})", eos_date)
    if m:
        return "EOS" if m.group(1) <= TODAY else "ACTIVE"
    return "ACTIVE"


async def fill_eos():
    print("EoS 맵 로딩 중...")
    eos_map = await build_eos_map()

    client = AsyncIOMotorClient(MONGO_URI)
    db = client["backoffice"]

    total_updated = 0
    total_skipped = 0

    for cat, (col_name, _) in COLLECTIONS.items():
        col = db[col_name]
        assets = await col.find({"is_deleted": {"$ne": True}}).to_list(None)
        updated = 0

        for asset in assets:
            fields = asset.get("fields", {})
            asset_type = fields.get("자산유형", cat)

            # 이미 EoS 여부가 있으면 스킵
            if fields.get(EOS_STATUS_KEY):
                total_skipped += 1
                continue

            new_status = None
            new_date = None

            # ① eos_date가 이미 있으면 상태만 계산
            existing_date = fields.get(EOS_DATE_KEY, "")
            if existing_date:
                new_status = calc_status_from_date(str(existing_date))
                new_date = str(existing_date)[:7]

            # ② 서버/DBMS/VMware: OS + 버전으로 자동 조회
            elif asset_type not in ("네트워크", "정보보호시스템"):
                dist = str(fields.get("운영체제", ""))
                version = str(fields.get("version", ""))
                result = lookup_eos(eos_map, dist, version)
                if result:
                    new_status, new_date = result

            # ③ 네트워크/정보보호시스템: 기종명 패턴 매칭
            else:
                model = str(fields.get("운영체제", ""))
                result = get_network_eos(model)
                if result:
                    new_status, new_date = result

            if new_status:
                await col.update_one(
                    {"_id": asset["_id"]},
                    {"$set": {
                        f"fields.{EOS_STATUS_KEY}": new_status,
                        f"fields.{EOS_DATE_KEY}": new_date or existing_date,
                    }}
                )
                updated += 1

        print(f"  [{col_name}] 업데이트 {updated}건 / 전체 {len(assets)}건")
        total_updated += updated
        total_skipped += (len(assets) - updated)

    client.close()
    print(f"\n완료: 업데이트 {total_updated}건, 기존값 유지 {total_skipped}건")


asyncio.run(fill_eos())
