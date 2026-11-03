"""Identity and clinic memberships.

Revision ID: 0001_identity
Revises:
"""
from alembic import op
import sqlalchemy as sa
revision = '0001_identity'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('email',sa.String(254),nullable=False),
        sa.Column('password_hash',sa.String(255),nullable=False),
        sa.Column('full_name',sa.String(120),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('email'))
    op.create_index('ix_users_email','users',['email'])
    op.create_table('clinics',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('name',sa.String(120),nullable=False),
        sa.Column('slug',sa.String(80),nullable=False,unique=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_table('clinic_memberships',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('clinic_id',sa.String(36),sa.ForeignKey('clinics.id',ondelete='CASCADE'),nullable=False),
        sa.Column('role',sa.String(20),nullable=False),
        sa.UniqueConstraint('user_id','clinic_id'),
        sa.CheckConstraint("role IN ('admin','clinician','receptionist')",name='valid_role'))
    op.create_index('ix_clinic_memberships_user_id','clinic_memberships',['user_id'])
    op.create_index('ix_clinic_memberships_clinic_id','clinic_memberships',['clinic_id'])
    op.create_table('sessions',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('token_hash',sa.String(64),nullable=False,unique=True),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_sessions_user_id','sessions',['user_id'])
    op.create_index('ix_sessions_token_hash','sessions',['token_hash'])

def downgrade():
    op.drop_table('sessions')
    op.drop_table('clinic_memberships')
    op.drop_table('clinics')
    op.drop_table('users')
