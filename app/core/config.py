import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "ClassTrack API"
    PROJECT_VERSION: str = "1.0.0"
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-for-development")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./classtrack.db")
    
    # Static files and uploads
    STATIC_DIR: str = os.path.join(os.getcwd(), "static")
    UPLOADS_DIR: str = os.path.join(STATIC_DIR, "uploads")
    STATIC_URL_PREFIX: str = "/static"

settings = Settings()
