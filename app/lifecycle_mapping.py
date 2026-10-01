"""스냅샷 생성기와 런타임 수집기가 공유하는 VMware 날짜 매핑."""
from datetime import date
from typing import Any


def update_vmware_dates(result: dict[str, str], display: str, entry: dict[str, Any]) -> None:
    """기존 월 단위 키를 유지하면서 지원 단계별 정확한 날짜를 추가한다.

    원본 필드 누락/잘못된 날짜는 기존 값을 보존하고, 명시적인 false는 제거한다.
    technicalGuidance는 계약 조건부 참고일이며 일반 지원 판정에 사용하지 않는다.
    """
    if display not in {"ESXi", "vCenter"} or not entry.get("cycle"):
        return
    prefix = f"{display}|{entry['cycle']}"
    for source, suffix in (("eol", "generalSupport"), ("technicalGuidance", "technicalGuidance")):
        key = f"{prefix}|{suffix}"
        value = entry.get(source)
        if value is False:
            result.pop(key, None)
            continue
        if not isinstance(value, str):
            continue
        try:
            parsed = date.fromisoformat(value).isoformat()
        except ValueError:
            continue
        result[key] = parsed
