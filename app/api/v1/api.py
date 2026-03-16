from fastapi import APIRouter
from .endpoints import auth, users, attendance, courses, sessions, analytics

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
