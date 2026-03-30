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

    # Profile pictures (store outside public static to prevent active-content injection).
    PROFILE_PICTURES_DIR: str = os.path.join(os.getcwd(), "private_uploads", "profile_pictures")
    PROFILE_PICTURES_MAX_BYTES: int = int(os.getenv("PROFILE_PICTURES_MAX_BYTES", "1048576"))  # 1MB
    
    # Resend Email Service
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    # Comma-separated list of allowed CORS origins.
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", FRONTEND_URL).split(",")
        if o.strip()
    ]
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

settings = Settings()
