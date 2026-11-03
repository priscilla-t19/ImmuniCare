import os
import re
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session as DbSession
from .db import get_db
from .models import User, Clinic, Membership, Session as AuthSession
from .security import hash_password, verify_password, new_token, token_digest, expiration

app = FastAPI(title='ImmuniCare API', version='0.2.0')

class RegisterClinic(BaseModel):
    clinic_name: str = Field(min_length=2, max_length=120)
    clinic_slug: str = Field(pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$', min_length=3, max_length=80)
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

class Login(BaseModel):
    email: EmailStr
    password: str

class StaffCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: str

def normalized_email(value):
    return str(value).strip().lower()

def serialize_clinic(clinic, role):
    return {'id': clinic.id, 'name': clinic.name, 'slug': clinic.slug, 'role': role}

def issue_session(db, user):
    token = new_token()
    db.add(AuthSession(user_id=user.id, token_hash=token_digest(token), expires_at=expiration()))
    db.commit()
    return {'access_token': token, 'token_type': 'bearer', 'expires_in': 8 * 3600}

def current_auth(authorization: str | None = Header(default=None), db: DbSession = Depends(get_db)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Authentication required', headers={'WWW-Authenticate':'Bearer'})
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail='Invalid session')
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_digest(token)))
    if not session or session.expires_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail='Invalid or expired session')
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid session')
    return user, session

def clinic_access(clinic_id: str, auth=Depends(current_auth), db: DbSession=Depends(get_db)):
    user, _ = auth
    membership = db.scalar(select(Membership).where(Membership.user_id==user.id, Membership.clinic_id==clinic_id))
    if not membership:
        raise HTTPException(status_code=404, detail='Clinic not found')
    return membership

@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'immunicare-api'}

@app.get('/ready')
def ready(db: DbSession=Depends(get_db)):
    try:
        db.execute(text('SELECT 1'))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail='Database unavailable')
    return {'status': 'ready'}

@app.post('/auth/register-clinic', status_code=201)
def register_clinic(payload: RegisterClinic, db: DbSession=Depends(get_db)):
    email = normalized_email(payload.email)
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail='Email already registered')
    clinic = Clinic(name=payload.clinic_name.strip(), slug=payload.clinic_slug)
    user = User(email=email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password))
    db.add_all([clinic, user])
    try:
        db.flush()
        db.add(Membership(user_id=user.id, clinic_id=clinic.id, role='admin'))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Email or clinic slug already in use')
    return {'clinic': serialize_clinic(clinic, 'admin'), 'user': {'id':user.id,'email':user.email,'full_name':user.full_name}}

@app.post('/auth/login')
def login(payload: Login, db: DbSession=Depends(get_db)):
    user = db.scalar(select(User).where(User.email == normalized_email(payload.email)))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    return issue_session(db, user)

@app.post('/auth/logout', status_code=204)
def logout(auth=Depends(current_auth), db: DbSession=Depends(get_db)):
    _, session = auth
    db.delete(session)
    db.commit()

@app.get('/auth/me')
def me(auth=Depends(current_auth), db: DbSession=Depends(get_db)):
    user, _ = auth
    rows = db.execute(select(Clinic, Membership.role).join(Membership, Clinic.id == Membership.clinic_id).where(Membership.user_id == user.id)).all()
    return {'id':user.id, 'email':user.email, 'full_name':user.full_name, 'clinics':[serialize_clinic(c,r) for c,r in rows]}

@app.get('/clinics/{clinic_id}')
def get_clinic(clinic_id: str, membership=Depends(clinic_access), db: DbSession=Depends(get_db)):
    clinic = db.get(Clinic, clinic_id)
    return serialize_clinic(clinic, membership.role)

@app.get('/clinics/{clinic_id}/staff')
def staff_list(clinic_id: str, membership=Depends(clinic_access), db: DbSession=Depends(get_db)):
    if membership.role != 'admin':
        raise HTTPException(status_code=403, detail='Admin permission required')
    rows = db.execute(select(User, Membership.role).join(Membership, Membership.user_id == User.id).where(Membership.clinic_id == clinic_id)).all()
    return [{'id':u.id,'full_name':u.full_name,'email':u.email,'role':role} for u,role in rows]

@app.post('/clinics/{clinic_id}/staff', status_code=201)
def add_staff(clinic_id: str, payload: StaffCreate, membership=Depends(clinic_access), db: DbSession=Depends(get_db)):
    if membership.role != 'admin':
        raise HTTPException(status_code=403, detail='Admin permission required')
    if payload.role not in ('admin', 'clinician', 'receptionist'):
        raise HTTPException(status_code=422, detail='Invalid role')
    email = normalized_email(payload.email)
    user = db.scalar(select(User).where(User.email == email))
    if user:
        # Do not let clinic administrators claim an existing account in another clinic.
        raise HTTPException(status_code=409, detail='Email already registered')
    user = User(email=email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.flush()
        db.add(Membership(user_id=user.id, clinic_id=clinic_id, role=payload.role))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Email already registered')
    return {'id':user.id,'email':user.email,'full_name':user.full_name,'role':payload.role}
