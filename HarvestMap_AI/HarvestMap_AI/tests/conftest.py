import os
import secrets

os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["AI_API_KEY"] = ""
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models import User, Location, Business, Product, PriceHistory
from app.security import password_hash, token_for, _buckets


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def pragmas(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")
        conn.create_function("lower", 1, lambda v: v.casefold() if isinstance(v, str) else v, deterministic=True)

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db):
    def override():
        yield db

    app.dependency_overrides[get_db] = override
    _buckets.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample(db):
    password = secrets.token_urlsafe(18)
    hashed = password_hash.hash(password)
    users = {}
    for role in ["admin", "owner", "user"]:
        u = User(email=f"{role}@example.com", name="Сынақ " + role, role=role, password_hash=hashed)
        db.add(u)
        users[role] = u
    second = User(email="other@example.com", name="Басқа иесі", role="owner", password_hash=hashed)
    db.add(second)
    loc = Location(name="Алматы", region="Алматы қаласы", latitude=43.2389, longitude=76.8897, is_demo=True)
    db.add(loc)
    db.flush()
    b = Business(
        owner_id=users["owner"].id,
        location_id=loc.id,
        name="Демо · Сынақ бағы",
        category="farm",
        description="Оқу мақсатындағы сынақ кәсіп сипаттамасы",
        address="Демо мекенжай",
        latitude=43.24,
        longitude=76.89,
        status="approved",
        is_demo=True,
    )
    db.add(b)
    db.flush()
    p = Product(
        business_id=b.id,
        name="Қызанақ",
        category="vegetables",
        description="Оқу мақсатындағы өнім сипаттамасы",
        price=650,
        unit="кг",
        stock=100,
        season_start=1,
        season_end=12,
        status="approved",
        is_demo=True,
    )
    db.add(p)
    db.flush()
    db.add(PriceHistory(product_id=p.id, price=650, recorded_at=datetime.now(timezone.utc)))
    db.commit()
    return {
        "users": users,
        "second": second,
        "location": loc,
        "business": b,
        "product": p,
        "password": password,
        "headers": {r: {"Authorization": "Bearer " + token_for(u)} for r, u in users.items()},
        "other_headers": {"Authorization": "Bearer " + token_for(second)},
    }


@pytest.fixture
def business_body(sample):
    return {
        "name": "Жаңа кәсіп",
        "category": "shop",
        "description": "Жаңа кәсіптің толық сипаттамасы",
        "location_id": sample["location"].id,
        "address": "Сынақ көшесі, 12",
        "phone": "",
        "website": "",
        "latitude": 43.25,
        "longitude": 76.9,
    }


@pytest.fixture
def product_body(sample):
    return {
        "business_id": sample["business"].id,
        "name": "Алма",
        "category": "fruit",
        "description": "Жергілікті өнімнің толық сипаттамасы",
        "price": 420,
        "unit": "кг",
        "stock": 100,
        "season_start": 1,
        "season_end": 12,
    }
