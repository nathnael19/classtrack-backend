import os
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
TEST_DB_PATH = REPO_ROOT / "test_classtrack_rooms.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ALGORITHM"] = "HS256"

sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.user import User, UserRole, UserState  # noqa: E402
from app.core.security import create_access_token  # noqa: E402


class OrgDeptAuthzTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.org1 = Organization(name="Org 1", domain="org1.example")
        cls.org2 = Organization(name="Org 2", domain="org2.example")
        cls.db.add_all([cls.org1, cls.org2])
        cls.db.commit()
        cls.db.refresh(cls.org1)
        cls.db.refresh(cls.org2)

        cls.dept1 = Department(name="Dept 1", head="Head", location="L1", description="D1", organization_id=cls.org1.id)
        cls.dept2 = Department(name="Dept 2", head="Head", location="L2", description="D2", organization_id=cls.org2.id)
        cls.db.add_all([cls.dept1, cls.dept2])
        cls.db.commit()
        cls.db.refresh(cls.dept1)
        cls.db.refresh(cls.dept2)

        cls.admin = User(
            name="Admin",
            email="admin_org@example.com",
            hashed_password="!",
            role=UserRole.admin,
            account_status=UserState.active.value,
            is_verified=True,
            organization_id=cls.org1.id,
        )
        cls.lecturer = User(
            name="Lecturer",
            email="lect_org@example.com",
            hashed_password="!",
            role=UserRole.lecturer,
            account_status=UserState.active.value,
            is_verified=True,
            organization_id=cls.org1.id,
        )
        cls.db.add_all([cls.admin, cls.lecturer])
        cls.db.commit()
        cls.db.refresh(cls.admin)
        cls.db.refresh(cls.lecturer)

        cls.admin_token = create_access_token({"sub": cls.admin.email})
        cls.lecturer_token = create_access_token({"sub": cls.lecturer.email})

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db.close()

    def test_organizations_require_auth(self):
        res = self.client.get("/api/v1/organizations")
        self.assertEqual(res.status_code, 401)

    def test_organizations_filtered_for_non_admin(self):
        res = self.client.get(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {self.lecturer_token}"},
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["id"], self.org1.id)

    def test_departments_filtered_for_non_admin(self):
        res = self.client.get(
            "/api/v1/departments",
            headers={"Authorization": f"Bearer {self.lecturer_token}"},
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["id"], self.dept1.id)


if __name__ == "__main__":
    unittest.main()

