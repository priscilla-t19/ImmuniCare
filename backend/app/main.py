import os
import re
from datetime import datetime, timezone, date
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session as DbSession
from .db import get_db
from .models import User, Clinic, Membership, Guardian, Patient, PatientGuardian, Session as AuthSession
from .security import hash_password, verify_password, new_token, token_digest, expiration

app = FastAPI(title='ImmuniCare API', version='0.3.0')

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


# Milestone 3: clinic-scoped patient and guardian records.
# API responses intentionally do not include government identity numbers by default.
class GuardianInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    identity_number: str | None = Field(default=None, max_length=40)
    phone: str | None = Field(default=None, max_length=32)

class GuardianPatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)

class PatientInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    birth_certificate_number: str = Field(min_length=2, max_length=60)
    date_of_birth: date

class PatientPatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    date_of_birth: date | None = None

class GuardianLink(BaseModel):
    guardian_id: str
    relationship_type: str = Field(min_length=2, max_length=40)

def can_edit(membership):
    if membership.role not in ('admin', 'clinician', 'receptionist'):
        raise HTTPException(status_code=403, detail='Insufficient permission')

def guardian_public(g):
    return {'id':g.id,'clinic_id':g.clinic_id,'full_name':g.full_name,'phone':g.phone}

def patient_public(p):
    return {'id':p.id,'clinic_id':p.clinic_id,'full_name':p.full_name,
            'birth_certificate_number':p.birth_certificate_number,'date_of_birth':p.date_of_birth.isoformat()}

def check_birth_date(value):
    if value > date.today():
        raise HTTPException(status_code=422, detail='Date of birth cannot be in the future')

def scoped(db, model, clinic_id, item_id):
    item = db.scalar(select(model).where(model.id==item_id,model.clinic_id==clinic_id))
    if item is None:
        raise HTTPException(status_code=404, detail='Record not found')
    return item

@app.get('/clinics/{clinic_id}/guardians')
def list_guardians(clinic_id: str, search: str = '', membership=Depends(clinic_access), db: DbSession=Depends(get_db)):
    stmt = select(Guardian).where(Guardian.clinic_id==clinic_id)
    if search.strip():
        stmt = stmt.where(Guardian.full_name.ilike('%'+search.strip()[:120]+'%'))
    return [guardian_public(g) for g in db.scalars(stmt.order_by(Guardian.full_name).limit(100))]

@app.post('/clinics/{clinic_id}/guardians', status_code=201)
def create_guardian(clinic_id: str, payload: GuardianInput, membership=Depends(clinic_access), db: DbSession=Depends(get_db)):
    can_edit(membership)
    g=Guardian(clinic_id=clinic_id,full_name=payload.full_name.strip(),
              identity_number=payload.identity_number.strip() if payload.identity_number else None,
              phone=payload.phone.strip() if payload.phone else None)
    db.add(g)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409,detail='Guardian identity already exists in this clinic')
    db.refresh(g)
    return guardian_public(g)

@app.get('/clinics/{clinic_id}/guardians/{guardian_id}')
def get_guardian(clinic_id: str, guardian_id: str, membership=Depends(clinic_access), db: DbSession=Depends(get_db)):
    return guardian_public(scoped(db,Guardian,clinic_id,guardian_id))

@app.patch('/clinics/{clinic_id}/guardians/{guardian_id}')
def update_guardian(clinic_id: str, guardian_id: str, payload: GuardianPatch, membership=Depends(clinic_access), db: DbSession=Depends(get_db)):
    can_edit(membership)
    g=scoped(db,Guardian,clinic_id,guardian_id)
    for key,value in payload.model_dump(exclude_unset=True).items():
        if value is None and key=='full_name':
            raise HTTPException(status_code=422,detail='Full name cannot be null')
        setattr(g,key,value.strip() if isinstance(value,str) else value)
    db.commit()
    return guardian_public(g)

@app.get('/clinics/{clinic_id}/patients')
def list_patients(clinic_id: str, search: str = '', membership=Depends(clinic_access), db: DbSession=Depends(get_db)):
    stmt=select(Patient).where(Patient.clinic_id==clinic_id)
    if search.strip():
        stmt=stmt.where(Patient.full_name.ilike('%'+search.strip()[:120]+'%'))
    return [patient_public(p) for p in db.scalars(stmt.order_by(Patient.full_name).limit(100))]

@app.post('/clinics/{clinic_id}/patients', status_code=201)
def create_patient(clinic_id: str, payload: PatientInput, membership=Depends(clinic_access), db: DbSession=Depends(get_db)):
    can_edit(membership)
    check_birth_date(payload.date_of_birth)
    p=Patient(clinic_id=clinic_id,full_name=payload.full_name.strip(),
              birth_certificate_number=payload.birth_certificate_number.strip(),date_of_birth=payload.date_of_birth)
    db.add(p)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409,detail='Birth certificate number already exists in this clinic')
    db.refresh(p)
    return patient_public(p)

@app.get('/clinics/{clinic_id}/patients/{patient_id}')
def get_patient(clinic_id: str, patient_id: str, membership=Depends(clinic_access), db: DbSession=Depends(get_db)):
    p=scoped(db,Patient,clinic_id,patient_id)
    links=db.execute(select(PatientGuardian,Guardian).join(Guardian,PatientGuardian.guardian_id==Guardian.id).where(PatientGuardian.patient_id==p.id,PatientGuardian.clinic_id==clinic_id,Guardian.clinic_id==clinic_id)).all()
    return {**patient_public(p),'guardians':[{**guardian_public(g),'relationship_type':link.relationship_type} for link,g in links]}

@app.patch('/clinics/{clinic_id}/patients/{patient_id}')
def update_patient(clinic_id: str, patient_id: str, payload: PatientPatch, membership=Depends(clinic_access), db: DbSession=Depends(get_db)):
    can_edit(membership)
    p=scoped(db,Patient,clinic_id,patient_id)
    for key,value in payload.model_dump(exclude_unset=True).items():
        if value is None:
            raise HTTPException(status_code=422,detail='Patient fields cannot be null')
        if key=='date_of_birth': check_birth_date(value)
        setattr(p,key,value.strip() if isinstance(value,str) else value)
    db.commit()
    return patient_public(p)

@app.post('/clinics/{clinic_id}/patients/{patient_id}/guardians',status_code=201)
def link_guardian(clinic_id: str, patient_id: str, payload: GuardianLink, membership=Depends(clinic_access), db: DbSession=Depends(get_db)):
    can_edit(membership)
    scoped(db,Patient,clinic_id,patient_id)
    scoped(db,Guardian,clinic_id,payload.guardian_id)
    link=PatientGuardian(clinic_id=clinic_id,patient_id=patient_id,guardian_id=payload.guardian_id,relationship_type=payload.relationship_type.strip())
    db.add(link)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409,detail='Guardian already linked to this patient')
    return {'id':link.id,'patient_id':patient_id,'guardian_id':payload.guardian_id,'relationship_type':link.relationship_type}

@app.delete('/clinics/{clinic_id}/patients/{patient_id}/guardians/{guardian_id}',status_code=204)
def unlink_guardian(clinic_id: str,patient_id: str,guardian_id: str,membership=Depends(clinic_access),db: DbSession=Depends(get_db)):
    can_edit(membership)
    link=db.scalar(select(PatientGuardian).where(PatientGuardian.clinic_id==clinic_id,PatientGuardian.patient_id==patient_id,PatientGuardian.guardian_id==guardian_id))
    if not link: raise HTTPException(status_code=404,detail='Relationship not found')
    db.delete(link)
    db.commit()
