import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import app
from app import models

@pytest.fixture
def client():
    engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def fk_on(dbapi_connection, connection_record):
        dbapi_connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    def override():
        with factory() as session:
            yield session
    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

def register(client, slug, email):
    return client.post('/auth/register-clinic', json={'clinic_name':slug.title(), 'clinic_slug':slug, 'full_name':'Test Admin', 'email':email, 'password':'long-password-123'})

def token(client, email, password='long-password-123'):
    r=client.post('/auth/login',json={'email':email,'password':password})
    assert r.status_code==200, r.text
    return {'Authorization':'Bearer '+r.json()['access_token']}

def test_registration_login_logout(client):
    r=register(client,'clinic-one','admin1@example.com')
    assert r.status_code==201, r.text
    assert 'password_hash' not in r.text
    assert register(client,'clinic-one','admin2@example.com').status_code==409
    assert client.post('/auth/login',json={'email':'admin1@example.com','password':'wrong'}).status_code==401
    headers=token(client,'admin1@example.com')
    assert client.get('/auth/me',headers=headers).json()['clinics'][0]['role']=='admin'
    assert client.post('/auth/logout',headers=headers).status_code==204
    assert client.get('/auth/me',headers=headers).status_code==401

def test_tenant_isolation_and_roles(client):
    a=register(client,'clinic-one','admin1@example.com').json()['clinic']['id']
    b=register(client,'clinic-two','admin2@example.com').json()['clinic']['id']
    ah=token(client,'admin1@example.com')
    bh=token(client,'admin2@example.com')
    assert client.get(f'/clinics/{a}',headers=ah).status_code==200
    assert client.get(f'/clinics/{b}',headers=ah).status_code==404
    assert client.get(f'/clinics/{a}/staff',headers=bh).status_code==404
    assert client.post(f'/clinics/{b}/staff',headers=ah,json={'full_name':'X User','email':'x@example.com','password':'long-password-123','role':'clinician'}).status_code==404
    staff=client.post(f'/clinics/{a}/staff',headers=ah,json={'full_name':'Staff Member','email':'staff@example.com','password':'long-password-123','role':'clinician'})
    assert staff.status_code==201, staff.text
    sh=token(client,'staff@example.com')
    assert client.get(f'/clinics/{a}',headers=sh).status_code==200
    assert client.get(f'/clinics/{a}/staff',headers=sh).status_code==403
    assert client.post(f'/clinics/{a}/staff',headers=sh,json={'full_name':'Y User','email':'y@example.com','password':'long-password-123','role':'admin'}).status_code==403
    assert client.get(f'/clinics/{b}',headers=sh).status_code==404
    assert client.post(f'/clinics/{a}/staff',headers=ah,json={'full_name':'Existing','email':'admin2@example.com','password':'long-password-123','role':'admin'}).status_code==409

def test_validation_and_auth_required(client):
    assert client.get('/auth/me').status_code==401
    assert client.post('/auth/register-clinic',json={'clinic_name':'A','clinic_slug':'INVALID SLUG','full_name':'X','email':'not-email','password':'short'}).status_code==422
