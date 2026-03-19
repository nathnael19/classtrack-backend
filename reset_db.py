import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in .env file.")
    exit(1)

# Handle SQLite correctly
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def reset_db_data():
    db = SessionLocal()
    try:
        print("Starting database data reset...")
        
        # List of tables to truncate in order or with CASCADE
        # We use a single TRUNCATE command with CASCADE to handle all foreign key constraints
        tables = [
            "attendances",
            "leave_requests",
            "notifications",
            "device_fingerprints",
            "enrollments",
            "course_lecturers",
            "class_sessions",
            "courses",
            "users",
            "departments",
            "rooms",
            "terms",
            "organizations"
        ]
        
        # Join table names
        tables_str = ", ".join(tables)
        
        # Execute truncate
        # RESTART IDENTITY resets any auto-incrementing IDs
        # CASCADE handles foreign key dependencies
        print(f"Truncating tables: {tables_str}")
        db.execute(text(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE;"))
        db.commit()
        
        print("Database data reset successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error resetting database: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_db_data()
