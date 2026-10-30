from logging.config import fileConfig
from alembic import context
from app.database import engine, Base
from app import models

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    # These objects belong to explicit PostGIS migration 0002, not portable ORM metadata.
    if type_ == "table" and name == "spatial_ref_sys":
        return False
    if type_ == "column" and name == "geom":
        return False
    if type_ == "index" and name in ("ix_business_geography", "ix_location_geography"):
        return False
    return True


if context.is_offline_mode():
    context.configure(url=str(engine.url), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=engine.dialect.name == "sqlite",
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()
