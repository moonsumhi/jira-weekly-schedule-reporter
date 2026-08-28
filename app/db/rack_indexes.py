"""랙 배치(rack_placements) 인덱스.

핵심은 U 중복 점유를 DB 수준에서 최종 차단하는 unique multikey index다.
`occupied_slots`(예: ["F:18","R:18","F:19","R:19"])의 각 원소가 별도 인덱스 항목이
되고, `(rack_ref_id, slot)` 복합 unique 라서 서로 다른 배치가 같은 슬롯을 가지면
E11000 duplicate key 로 거부된다. partial(is_deleted=false)이라 반출된 배치가
차지하던 U 는 즉시 재사용 가능하다.
"""
from __future__ import annotations

import logging

from app.db.mongo import MongoClientManager

logger = logging.getLogger(__name__)


async def create_rack_indexes() -> None:
    col = MongoClientManager.get_rack_placements_collection()

    # 자산 1개당 배치 문서 1건(활성/반출 포함). 재배치 시 기존 문서를 재활성화한다.
    await col.create_index(
        [("asset_category", 1), ("asset_ref_id", 1)],
        unique=True,
        name="uq_rack_placement_asset",
    )

    # 활성 배치의 점유 슬롯 유일성 → U 중복 점유 DB 차단(동시 요청 포함).
    await col.create_index(
        [("rack_ref_id", 1), ("occupied_slots", 1)],
        unique=True,
        partialFilterExpression={"is_deleted": False},
        name="uq_rack_occupied_slot_active",
    )

    # 랙 배치도 조회용.
    await col.create_index(
        [("rack_ref_id", 1), ("is_deleted", 1), ("start_u", -1)],
        name="ix_rack_layout",
    )

    hist = MongoClientManager.get_rack_placements_history_collection()
    await hist.create_index("asset_ref_id")
    await hist.create_index("rack_ref_id")
    await hist.create_index("changed_at")

    logger.info("랙 배치 인덱스 생성 완료")
