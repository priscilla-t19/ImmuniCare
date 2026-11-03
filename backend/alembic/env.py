from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.db import Base
from app import models
import os

config = context.config
config.set_main_option('sqlalchemy.url', os.environ['DATABASE_URL'].replace('%', '%%'))
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=os.environ['DATABASE_URL'], target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    from sqlalchemy import create_engine
    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
