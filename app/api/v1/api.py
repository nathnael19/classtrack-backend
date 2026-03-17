from fastapi import APIRouter
from .endpoints import auth, users, attendance, courses, sessions, analytics, rooms, organizations, departments, terms, device_fingerprints, leave_requests, notifications

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(departments.router, prefix="/departments", tags=["departments"])
api_router.include_router(terms.router, prefix="/terms", tags=["terms"])
api_router.include_router(device_fingerprints.router, prefix="/device_fingerprints", tags=["device_fingerprints"])
api_router.include_router(leave_requests.router, prefix="/leave_requests", tags=["leave_requests"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
