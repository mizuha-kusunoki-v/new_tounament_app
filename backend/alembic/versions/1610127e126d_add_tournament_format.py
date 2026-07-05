"""add tournament format

Revision ID: 1610127e126d
Revises: 31398394a636
Create Date: 2026-07-05 19:53:32.537323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1610127e126d'
down_revision: Union[str, None] = '31398394a636'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Unlike op.create_table (which auto-emits CREATE TYPE for enum columns as
# part of the table DDL), op.add_column on Postgres does NOT create a new
# enum type on its own -- it just assumes it already exists. SQLite has no
# native enum type (columns are plain VARCHAR + CHECK), so this gap only
# surfaces once you run the migration against real Postgres. The type must
# be created explicitly first; .create()/.drop() no-op on dialects (like
# SQLite) that don't have a separate enum type to manage.
tournament_format_enum = sa.Enum('SINGLE_ELIMINATION', 'DOUBLE_ELIMINATION', name='tournamentformat')


def upgrade() -> None:
    tournament_format_enum.create(op.get_bind(), checkfirst=True)
    # server_default backfills existing rows (predating this column) as
    # double-elimination, matching the prior hardcoded behavior.
    op.add_column(
        'tournaments',
        sa.Column(
            'format',
            tournament_format_enum,
            nullable=False,
            server_default='DOUBLE_ELIMINATION',
        ),
    )


def downgrade() -> None:
    op.drop_column('tournaments', 'format')
    tournament_format_enum.drop(op.get_bind(), checkfirst=True)
