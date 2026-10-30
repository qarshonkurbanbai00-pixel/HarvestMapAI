"""Optional PostgreSQL geography indexes; SQLite retains portable coordinates."""

from alembic import op

revision = "0002_postgis"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        op.execute(
            "ALTER TABLE businesses ADD COLUMN geom geography(Point,4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude,latitude),4326)::geography) STORED"
        )
        op.execute("CREATE INDEX ix_business_geography ON businesses USING GIST (geom)")
        op.execute(
            "ALTER TABLE locations ADD COLUMN geom geography(Point,4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude,latitude),4326)::geography) STORED"
        )
        op.execute("CREATE INDEX ix_location_geography ON locations USING GIST (geom)")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE businesses DROP COLUMN geom")
        op.execute("ALTER TABLE locations DROP COLUMN geom")
