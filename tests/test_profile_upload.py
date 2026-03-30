import os
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"

# Use the same isolated DB file as other authz/upload tests to avoid destructive ops on dev DB.
TEST_DB_PATH = REPO_ROOT / "test_classtrack_rooms.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ALGORITHM"] = "HS256"

sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models.user import User, UserRole, UserState  # noqa: E402
from app.core.security import create_access_token  # noqa: E402


class ProfileUploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.user = User(
            name="Student",
            email="student_upload@example.com",
            hashed_password="!",
            role=UserRole.student,
            account_status=UserState.active.value,
            is_verified=True,
        )
        cls.db.add(cls.user)
        cls.db.commit()
        cls.db.refresh(cls.user)

        cls.user_token = create_access_token({"sub": cls.user.email})

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db.close()

    def test_svg_profile_picture_rejected(self):
        svg_payload = b"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <script>alert('xss')</script>
</svg>"""

        res = self.client.post(
            "/api/v1/users/me/profile-picture",
            headers={"Authorization": f"Bearer {self.user_token}"},
            files={"file": ("avatar.svg", svg_payload, "image/svg+xml")},
        )

        self.assertEqual(res.status_code, 400)
        self.assertIn("Unsupported image type", res.text)


if __name__ == "__main__":
    unittest.main()

