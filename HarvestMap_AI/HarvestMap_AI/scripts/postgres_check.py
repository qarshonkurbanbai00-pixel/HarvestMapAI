"""Non-destructive integration checks against a migrated, demo-seeded PostgreSQL/PostGIS DB.
DATABASE_URL must explicitly point at PostgreSQL. All temporary writes are rolled back.
Run: python -m scripts.postgres_check
"""

from sqlalchemy import text, select
from fastapi.testclient import TestClient
from app.config import get_settings
from app.database import engine, SessionLocal
from app.main import app
from app.models import Business


def main():
    if engine.dialect.name != "postgresql":
        raise SystemExit("Set DATABASE_URL to a migrated, demo-seeded PostgreSQL/PostGIS database first.")
    with engine.connect() as connection:
        version = connection.scalar(text("SELECT PostGIS_Lib_Version()"))
        assert version
        assert (
            connection.scalar(text("SELECT COUNT(*) FROM pg_indexes WHERE indexname IN ('ix_business_geography','ix_location_geography')"))
            == 2
        )
        assert connection.scalar(text("SELECT COUNT(*) FROM businesses WHERE ST_SRID(geom::geometry) != 4326")) == 0
    print("PASS PostGIS extension, geography indexes, SRID 4326")
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/businesses?q=демо").json()["total"] >= 8
        assert client.get("/api/products?q=қызанақ").json()["total"] >= 3
        assert client.get("/api/map?lat=43.2389&lon=76.8897&radius_km=60").json()["total"] > 0
        assert client.get("/api/map?lat=0&lon=0&radius_km=1").json()["total"] == 0
        assert client.get("/api/map?bbox=76,43,78,44").json()["total"] > 0
        assert client.get("/api/statistics").json()["demo_products"] >= 16
        assert client.get("/api/statistics/trends").json()["items"]
    print("PASS PostgreSQL Unicode search, native ST_DWithin radius, bbox, GeoJSON, analytics, health")
    with SessionLocal() as db:
        business = db.scalar(select(Business).where(Business.is_demo.is_(True)))
        assert business is not None
        old_lat = business.latitude
        business.latitude = 40.12345
        db.flush()
        new_lat = db.scalar(text("SELECT ST_Y(geom::geometry) FROM businesses WHERE id=:id"), {"id": business.id})
        assert abs(new_lat - 40.12345) < 1e-8
        db.rollback()
        db.refresh(business)
        assert business.latitude == old_lat
    print("PASS generated geography column follows coordinate edits; temporary write rolled back")


if __name__ == "__main__":
    main()
