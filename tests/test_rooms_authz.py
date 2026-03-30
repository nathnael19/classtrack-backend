import os
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


# Ensure authz tests run against an isolated DB.
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

TEST_DB_PATH = REPO_ROOT / "test_classtrack_rooms.db"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ALGORITHM"] = "HS256"

sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models.room import Room, RoomStatus, RoomType  # noqa: E402
from app.models.user import User, UserRole, UserState  # noqa: E402
from app.core.security import create_access_token  # noqa: E402


class RoomsAuthzTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        cls.client = TestClient(app)

        cls.db = SessionLocal()

        cls.admin_user = User(
            name="Admin",
            email="admin@example.com",
            hashed_password="!",
            role=UserRole.admin,
            account_status=UserState.active.value,
            is_verified=True,
        )
        cls.student_user = User(
            name="Student",
            email="student@example.com",
            hashed_password="!",
            role=UserRole.student,
            account_status=UserState.active.value,
            is_verified=True,
        )
        cls.db.add_all([cls.admin_user, cls.student_user])
        cls.db.commit()
        cls.db.refresh(cls.admin_user)
        cls.db.refresh(cls.student_user)

        cls.room = Room(
            name="Room A",
            building="Building 1",
            capacity=50,
            latitude=12.34,
            longitude=56.78,
            geofence_radius=100.0,
            type=RoomType.lecture_hall,
            status=RoomStatus.active,
        )
        cls.db.add(cls.room)
        cls.db.commit()
        cls.db.refresh(cls.room)

        cls.admin_token = create_access_token({"sub": cls.admin_user.email})
        cls.student_token = create_access_token({"sub": cls.student_user.email})

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db.close()

    def test_student_cannot_update_room(self):
        payload = {
            "name": "Room A - updated",
            "building": "Building 1",
            "capacity": 60,
            "latitude": 12.34,
            "longitude": 56.78,
            "geofence_radius": 120.0,
            "type": "lecture_hall",
            "status": "active",
        }
        res = self.client.put(
            f"/api/v1/rooms/{self.room.id}",
            json=payload,
            headers={"Authorization": f"Bearer {self.student_token}"},
        )
        self.assertEqual(res.status_code, 403)

    def test_student_cannot_delete_room(self):
        res = self.client.delete(
            f"/api/v1/rooms/{self.room.id}",
            headers={"Authorization": f"Bearer {self.student_token}"},
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_can_update_room(self):
        payload = {
            "name": "Room A - updated by admin",
            "building": "Building 1",
            "capacity": 60,
            "latitude": 12.34,
            "longitude": 56.78,
            "geofence_radius": 120.0,
            "type": "lecture_hall",
            "status": "active",
        }
        res = self.client.put(
            f"/api/v1/rooms/{self.room.id}",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(res.status_code, 200)

    def test_admin_can_delete_room(self):
        res = self.client.delete(
            f"/api/v1/rooms/{self.room.id}",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()

