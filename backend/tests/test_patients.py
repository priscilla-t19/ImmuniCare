import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base, get_db
from app.main import app

@pytest.fixture
def client():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    @event.listens_for(engine,'connect')
    def fk_on(connection, record):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine)
    def override():
        with factory() as session: yield session
    app.dependency_overrides[get_db]=override
    try:
        with TestClient(app) as c: yield c
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

def setup(client,slug,email):
    r=client.post('/auth/register-clinic',json={'clinic_name':slug,'clinic_slug':slug,'full_name':'Test Admin','email':email,'password':'long-password-123'})
    assert r.status_code==201,r.text
    t=client.post('/auth/login',json={'email':email,'password':'long-password-123'}).json()['access_token']
    return r.json()['clinic']['id'],{'Authorization':'Bearer '+t}

def test_patient_guardian_crud_and_validation(client):
    a,auth=setup(client,'clinic-one','one@example.com')
    root=f'/clinics/{a}'
    g=client.post(root+'/guardians',headers=auth,json={'full_name':'Demo Guardian','identity_number':'DEMO-1','phone':'000-000'})
    assert g.status_code==201,g.text
    assert 'identity_number' not in g.json()
    assert client.post(root+'/guardians',headers=auth,json={'full_name':'Duplicate','identity_number':'DEMO-1'}).status_code==409
    p=client.post(root+'/patients',headers=auth,json={'full_name':'Demo Infant','birth_certificate_number':'DEMO-B1','date_of_birth':'2024-01-01'})
    assert p.status_code==201,p.text
    assert client.post(root+'/patients',headers=auth,json={'full_name':'Another','birth_certificate_number':'DEMO-B1','date_of_birth':'2024-01-01'}).status_code==409
    assert client.post(root+'/patients',headers=auth,json={'full_name':'Future','birth_certificate_number':'DEMO-B2','date_of_birth':'2999-01-01'}).status_code==422
    pid=p.json()['id']; gid=g.json()['id']
    assert client.post(f'{root}/patients/{pid}/guardians',headers=auth,json={'guardian_id':gid,'relationship_type':'parent'}).status_code==201
    assert client.post(f'{root}/patients/{pid}/guardians',headers=auth,json={'guardian_id':gid,'relationship_type':'parent'}).status_code==409
    detail=client.get(f'{root}/patients/{pid}',headers=auth).json()
    assert detail['guardians'][0]['id']==gid
    assert len(client.get(root+'/patients?search=Infant',headers=auth).json())==1
    assert client.patch(f'{root}/patients/{pid}',headers=auth,json={'full_name':'Updated Infant'}).json()['full_name']=='Updated Infant'
    assert client.patch(f'{root}/guardians/{gid}',headers=auth,json={'phone':'111'}).json()['phone']=='111'
    assert client.delete(f'{root}/patients/{pid}/guardians/{gid}',headers=auth).status_code==204
    assert client.get(f'{root}/patients/{pid}',headers=auth).json()['guardians']==[]

def test_cross_clinic_records_are_inaccessible(client):
    a,ah=setup(client,'clinic-one','one@example.com')
    b,bh=setup(client,'clinic-two','two@example.com')
    p=client.post(f'/clinics/{a}/patients',headers=ah,json={'full_name':'Clinic One Infant','birth_certificate_number':'B1','date_of_birth':'2024-01-01'}).json()
    g=client.post(f'/clinics/{a}/guardians',headers=ah,json={'full_name':'Clinic One Guardian'}).json()
    assert client.get(f'/clinics/{a}/patients',headers=bh).status_code==404
    assert client.get(f'/clinics/{a}/patients/{p["id"]}',headers=bh).status_code==404
    assert client.patch(f'/clinics/{a}/patients/{p["id"]}',headers=bh,json={'full_name':'Attack'}).status_code==404
    assert client.get(f'/clinics/{b}/patients/{p["id"]}',headers=bh).status_code==404
    assert client.patch(f'/clinics/{b}/patients/{p["id"]}',headers=bh,json={'full_name':'Attack'}).status_code==404
    assert client.post(f'/clinics/{b}/patients/{p["id"]}/guardians',headers=bh,json={'guardian_id':g['id'],'relationship_type':'parent'}).status_code==404
    bp=client.post(f'/clinics/{b}/patients',headers=bh,json={'full_name':'Clinic Two Infant','birth_certificate_number':'B1','date_of_birth':'2024-01-01'}).json()
    assert client.post(f'/clinics/{b}/patients/{bp["id"]}/guardians',headers=bh,json={'guardian_id':g['id'],'relationship_type':'parent'}).status_code==404
    assert client.get(f'/clinics/{b}/patients',headers=bh).json()[0]['id']==bp['id']
    assert client.get(f'/clinics/{b}/guardians',headers=bh).json()==[]
    assert client.get(f'/clinics/{b}/patients',headers={}).status_code==401

def test_clinician_and_receptionist_access(client):
    a,ah=setup(client,'clinic-one','one@example.com')
    for role in ('clinician','receptionist'):
        email=f'{role}@example.com'
        r=client.post(f'/clinics/{a}/staff',headers=ah,json={'full_name':role.title(),'email':email,'password':'long-password-123','role':role})
        assert r.status_code==201
        token=client.post('/auth/login',json={'email':email,'password':'long-password-123'}).json()['access_token']
        auth={'Authorization':'Bearer '+token}
        assert client.post(f'/clinics/{a}/guardians',headers=auth,json={'full_name':'Demo Guardian'}).status_code==201
        assert client.post(f'/clinics/{a}/patients',headers=auth,json={'full_name':'Demo Infant','birth_certificate_number':role,'date_of_birth':'2024-01-01'}).status_code==201
