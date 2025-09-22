"""add email_confirmed and email_confirmations table

Revision ID: 002
Revises: 001
Create Date: 2025-09-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade():
    # Add column email_confirmado to usuarios (SQLite supports ALTER ADD COLUMN)
    with op.get_context().autocommit_block():
        try:
            op.add_column('usuarios', sa.Column('email_confirmado', sa.Boolean(), nullable=True, server_default=sa.text('0')))
        except Exception:
            # best-effort; if the column already exists, ignore
            pass

    # Create email_confirmations table
    op.create_table(
        'email_confirmations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.Column('expira_em', sa.DateTime(), nullable=True),
        sa.Column('confirmado', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
    )

def downgrade():
    op.drop_table('email_confirmations')
    # dropping a column in SQLite is not straightforward; skip in downgrade
    try:
        op.drop_column('usuarios', 'email_confirmado')
    except Exception:
        pass
