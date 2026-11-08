"""Patient and guardian records.

Revision ID: 0002_patients_guardians
Revises: 0001_identity
"""
from alembic import op
import sqlalchemy as sa
revision = '0002_patients_guardians'
down_revision = '0001_identity'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('guardians',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('clinic_id',sa.String(36),sa.ForeignKey('clinics.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('full_name',sa.String(120),nullable=False),
        sa.Column('identity_number',sa.String(40)),
        sa.Column('phone',sa.String(32)),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('clinic_id','identity_number',name='uq_guardian_clinic_identity'))
    op.create_index('ix_guardians_clinic_id','guardians',['clinic_id'])
    op.create_table('patients',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('clinic_id',sa.String(36),sa.ForeignKey('clinics.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('full_name',sa.String(120),nullable=False),
        sa.Column('birth_certificate_number',sa.String(60),nullable=False),
        sa.Column('date_of_birth',sa.Date(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('clinic_id','birth_certificate_number',name='uq_patient_clinic_birth_certificate'))
    op.create_index('ix_patients_clinic_id','patients',['clinic_id'])
    op.create_table('patient_guardians',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('clinic_id',sa.String(36),sa.ForeignKey('clinics.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('patient_id',sa.String(36),sa.ForeignKey('patients.id',ondelete='CASCADE'),nullable=False),
        sa.Column('guardian_id',sa.String(36),sa.ForeignKey('guardians.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('relationship_type',sa.String(40),nullable=False),
        sa.UniqueConstraint('patient_id','guardian_id',name='uq_patient_guardian'))
    for col in ('clinic_id','patient_id','guardian_id'):
        op.create_index(f'ix_patient_guardians_{col}','patient_guardians',[col])

def downgrade():
    op.drop_table('patient_guardians')
    op.drop_table('patients')
    op.drop_table('guardians')
