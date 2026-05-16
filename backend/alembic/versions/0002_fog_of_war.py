"""fog of war — explored_systems

Revision ID: 0002_fog_of_war
Revises: 0001_baseline
Create Date: 2026-05-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0002_fog_of_war"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── explored_systems ─────────────────────────────────────
    # Tracker hvilke solsystemer en spiller har utforsket.
    # Et system blir synlig når:
    #   1. Det er spillerens eget system (settes ved game start)
    #   2. Spilleren bygger sitt første ekspedisjonsskip (naboer til eget system)
    #   3. Et ekspedisjonsskip ankommer et system (det systemet + dets naboer)
    op.execute("""
        CREATE TABLE IF NOT EXISTS explored_systems (
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            system_id   UUID NOT NULL REFERENCES solar_systems(id) ON DELETE CASCADE,
            explored_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (user_id, system_id)
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_explored_user
        ON explored_systems(user_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_explored_system
        ON explored_systems(system_id)
    """)

    # ── has_built_expedition på users ────────────────────────
    # Flagg som settes første gang en spiller fullfører bygging
    # av et ekspedisjonsskip. Brukes for å avgjøre om naboer
    # til eget system skal være synlige.
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS has_built_expedition BOOLEAN NOT NULL DEFAULT FALSE
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS explored_systems CASCADE")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS has_built_expedition")
