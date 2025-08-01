"""free_call_token_info

Revision ID: f8fca3ab5b39
Revises:
Create Date: 2025-06-09 13:08:06.197414

"""

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision = "f8fca3ab5b39"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "free_call_token_info",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", mysql.VARCHAR(length=128), nullable=False),
        sa.Column("organization_id", mysql.VARCHAR(length=128), nullable=False),
        sa.Column("service_id", mysql.VARCHAR(length=128), nullable=False),
        sa.Column("group_id", mysql.VARCHAR(length=128), nullable=False),
        sa.Column("token", sa.VARBINARY(length=512), nullable=False),
        sa.Column("expiration_block_number", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            mysql.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            mysql.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        "ix_token_body",
        "free_call_token_info",
        ["username", "organization_id", "service_id", "group_id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_token_body", table_name="free_call_token_info")
    op.drop_table("free_call_token_info")
    # ### end Alembic commands ###
