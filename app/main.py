from fastapi import FastAPI
from .api.v1.api import api_router
from .db.session import engine
from .db import base

# Create database tables
base.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ClassTrack API", version="1.0.0")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Welcome to ClassTrack API"}
