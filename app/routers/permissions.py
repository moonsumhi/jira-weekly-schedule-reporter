"""메뉴 단위 API 접근 권한 dependency."""
from fastapi import Depends, HTTPException

from app.models.user import UserPublic
from app.routers.auth import get_current_user


async def require_asset_access(
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    """관리자 또는 자산 메뉴 권한을 가진 사용자만 허용한다."""
    if not current_user.is_admin and "asset" not in (current_user.permissions or []):
        raise HTTPException(status_code=403, detail="자산 메뉴 권한이 필요합니다.")
    return current_user
