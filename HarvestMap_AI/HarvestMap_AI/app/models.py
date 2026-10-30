from datetime import datetime, timezone
from sqlalchemy import String, Text, ForeignKey, Numeric, Float, Boolean, DateTime, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint("role IN ('user','owner','admin')"),)


class Location(Base):
    __tablename__ = "locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    region: Mapped[str] = mapped_column(String(120), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("latitude >= -90 AND latitude <= 90"), CheckConstraint("longitude >= -180 AND longitude <= 180"))


class Business(Base):
    __tablename__ = "businesses"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    description: Mapped[str] = mapped_column(Text)
    address: Mapped[str] = mapped_column(String(250))
    phone: Mapped[str] = mapped_column(String(40), default="")
    website: Mapped[str] = mapped_column(String(300), default="")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    location: Mapped[Location] = relationship()
    products: Mapped[list["Product"]] = relationship(back_populates="business", cascade="all, delete-orphan")
    __table_args__ = (
        CheckConstraint("status IN ('pending','approved','rejected')"),
        CheckConstraint("latitude >= -90 AND latitude <= 90"),
        CheckConstraint("longitude >= -180 AND longitude <= 180"),
        Index("ix_business_coordinates", "latitude", "longitude"),
    )


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    unit: Mapped[str] = mapped_column(String(20), default="кг")
    stock: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    season_start: Mapped[int] = mapped_column(default=1)
    season_end: Mapped[int] = mapped_column(default=12)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    business: Mapped[Business] = relationship(back_populates="products")
    history: Mapped[list["PriceHistory"]] = relationship(cascade="all, delete-orphan", order_by="PriceHistory.recorded_at")
    __table_args__ = (
        CheckConstraint("price > 0"),
        CheckConstraint("stock >= 0"),
        CheckConstraint("season_start BETWEEN 1 AND 12"),
        CheckConstraint("season_end BETWEEN 1 AND 12"),
        CheckConstraint("status IN ('pending','approved','rejected')"),
    )


class PriceHistory(Base):
    __tablename__ = "price_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
