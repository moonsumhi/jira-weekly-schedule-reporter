from fastapi import APIRouter
from app.routers.sr import requests as sr_requests
from app.routers.sr import admin_requests as sr_admin

router = APIRouter()

router.include_router(sr_requests.router, prefix="/schedule/service-requests", tags=["sr-requests"])
router.include_router(sr_admin.router, prefix="/admin/schedule/service-requests", tags=["sr-admin"])
