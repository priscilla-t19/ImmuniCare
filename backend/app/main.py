from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import os

app = FastAPI(title="ImmuniCare API", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok", "service": "immunicare-api"}

@app.get("/ready")
def ready():
    url = os.environ.get("DATABASE_URL")
    if not url:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database not configured")
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
    except SQLAlchemyError:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ready"}
