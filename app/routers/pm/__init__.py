from fastapi import APIRouter
from app.routers.pm import (
    organizations, projects, issues, sprints, board,
    dashboard, users, uploads, work_status,
    weekly_reports, monthly_reports,
)

router = APIRouter()

router.include_router(organizations.router,   prefix="/organizations",     tags=["pm-organizations"])
router.include_router(projects.router,        prefix="/projects",          tags=["pm-projects"])
router.include_router(issues.router,          prefix="/projects",          tags=["pm-issues"])
router.include_router(sprints.router,         prefix="/projects",          tags=["pm-sprints"])
router.include_router(board.router,           prefix="/projects",          tags=["pm-board"])
router.include_router(dashboard.router,       prefix="/dashboard",         tags=["pm-dashboard"])
router.include_router(users.router,           prefix="/users",             tags=["pm-users"])
router.include_router(uploads.router,                                      tags=["pm-uploads"])
router.include_router(work_status.router,                                  tags=["pm-work-status"])
router.include_router(weekly_reports.router,  prefix="/weekly-reports",    tags=["pm-weekly-reports"])
router.include_router(monthly_reports.router, prefix="/monthly-reports",   tags=["pm-monthly-reports"])
