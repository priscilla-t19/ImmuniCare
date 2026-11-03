import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

def get_engine():
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL not configured')
    return create_engine(url, pool_pre_ping=True)

def get_db():
    engine = get_engine()
    try:
        with sessionmaker(bind=engine)() as db:
            yield db
    finally:
        engine.dispose()
