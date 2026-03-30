from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from .api.v1.api import api_router
from .db.session import engine, get_db
from .db import base
from .core.config import settings
from .core.limiter import limiter
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from .core.security_headers import SecurityHeadersMiddleware

# Do not log connection strings or secrets.

# Create database tables
base.Base.metadata.create_all(bind=engine)

# Ensure static/uploads directory exists
if not os.path.exists(settings.UPLOADS_DIR):
    os.makedirs(settings.UPLOADS_DIR)

# Ensure private profile picture directory exists
if not os.path.exists(settings.PROFILE_PICTURES_DIR):
    os.makedirs(settings.PROFILE_PICTURES_DIR)

app = FastAPI(title="ClassTrack API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Baseline security hardening headers.
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api_router, prefix="/api/v1")

# Mount static files
app.mount(settings.STATIC_URL_PREFIX, StaticFiles(directory=settings.STATIC_DIR), name="static")

@app.get("/")
def root():
    return {"message": "Welcome to ClassTrack API"}
