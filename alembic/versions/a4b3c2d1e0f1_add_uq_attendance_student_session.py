"""Add unique constraint to prevent duplicate attendance rows.

Revision ID: a4b3c2d1e0f1
Revises: 69ffd3cc2c7d
Create Date: 2026-03-30
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a4b3c2d1e0f1"
down_revision: Union[str, None] = "69ffd3cc2c7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_attendances_student_session",
        "attendances",
        ["student_id", "session_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_attendances_student_session",
        "attendances",
        type_="unique",
    )

