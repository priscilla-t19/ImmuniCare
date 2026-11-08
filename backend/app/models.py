import uuid
from datetime import date
from datetime import datetime, timezone
from sqlalchemy import Index
from sqlalchemy import String, Date, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def uid():
    return str(uuid.uuid4())

def now():
    return datetime.now(timezone.utc)

class User(Base):
    __table_args__ = (Index("ix_users_email", "email"),)
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)

class Clinic(Base):
    __tablename__ = 'clinics'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)

class Membership(Base):
    __tablename__ = 'clinic_memberships'
    __table_args__ = (UniqueConstraint('user_id', 'clinic_id'), CheckConstraint("role IN ('admin','clinician','receptionist')", name='valid_role'))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    clinic_id: Mapped[str] = mapped_column(ForeignKey('clinics.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)

class Session(Base):
    __table_args__ = (Index("ix_sessions_token_hash", "token_hash"),)
    __tablename__ = 'sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Guardian(Base):
    __tablename__ = 'guardians'
    __table_args__ = (UniqueConstraint('clinic_id', 'identity_number', name='uq_guardian_clinic_identity'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    clinic_id: Mapped[str] = mapped_column(ForeignKey('clinics.id', ondelete='RESTRICT'), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    identity_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)

class Patient(Base):
    __tablename__ = 'patients'
    __table_args__ = (UniqueConstraint('clinic_id', 'birth_certificate_number', name='uq_patient_clinic_birth_certificate'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    clinic_id: Mapped[str] = mapped_column(ForeignKey('clinics.id', ondelete='RESTRICT'), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    birth_certificate_number: Mapped[str] = mapped_column(String(60), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)

class PatientGuardian(Base):
    __tablename__ = 'patient_guardians'
    __table_args__ = (UniqueConstraint('patient_id', 'guardian_id', name='uq_patient_guardian'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    clinic_id: Mapped[str] = mapped_column(ForeignKey('clinics.id', ondelete='RESTRICT'), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    guardian_id: Mapped[str] = mapped_column(ForeignKey('guardians.id', ondelete='RESTRICT'), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(40), nullable=False)
