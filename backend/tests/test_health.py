from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "immunicare-api"}

def test_ready_without_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    response = client.get("/ready")
    assert response.status_code == 503
