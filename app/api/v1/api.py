from fastapi import APIRouter
from .endpoints import auth, users, attendance

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
