import math
from datetime import datetime, timezone
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from .models import Business, Product


def in_season(start, end, month=None):
    month = month or datetime.now(timezone.utc).month
    return start <= month <= end if start <= end else month >= start or month <= end


def distance_km(lat1, lon1, lat2, lon2):
    a, b = math.radians(lat1), math.radians(lat2)
    dlat, dlon = b - a, math.radians(lon2 - lon1)
    x = math.sin(dlat / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.atan2(math.sqrt(x), math.sqrt(max(0, 1 - x)))


def business_dict(b):
    return {
        "id": b.id,
        "owner_id": b.owner_id,
        "location_id": b.location_id,
        "name": b.name,
        "category": b.category,
        "description": b.description,
        "address": b.address,
        "phone": b.phone,
        "website": b.website,
        "latitude": b.latitude,
        "longitude": b.longitude,
        "status": b.status,
        "is_demo": b.is_demo,
        "location": {"id": b.location.id, "name": b.location.name, "region": b.location.region},
        "created_at": b.created_at.isoformat(),
    }


def product_dict(p):
    return {
        "id": p.id,
        "business_id": p.business_id,
        "name": p.name,
        "category": p.category,
        "description": p.description,
        "price": float(p.price),
        "unit": p.unit,
        "stock": float(p.stock),
        "season_start": p.season_start,
        "season_end": p.season_end,
        "in_season": in_season(p.season_start, p.season_end),
        "status": p.status,
        "is_demo": p.is_demo,
        "business_name": p.business.name,
        "location_id": p.business.location_id,
        "location_name": p.business.location.name,
        "latitude": p.business.latitude,
        "longitude": p.business.longitude,
    }


def spatial_filter(stmt, db, lat=None, lon=None, radius_km=50, bounds=None):
    # Bound parameters only; PostGIS geography radius is in meters.
    if bounds:
        from sqlalchemy import or_

        w, s, e, n = bounds
        stmt = stmt.where(Business.latitude.between(s, n))
        stmt = stmt.where(Business.longitude.between(w, e) if w <= e else or_(Business.longitude >= w, Business.longitude <= e))
    if lat is not None and db.bind.dialect.name == "postgresql":
        stmt = stmt.where(
            text("ST_DWithin(businesses.geom, CAST(ST_SetSRID(ST_MakePoint(:near_lon,:near_lat),4326) AS geography), :near_meters)")
        ).params(near_lon=lon, near_lat=lat, near_meters=radius_km * 1000)
    return stmt


def public_products(db, **spatial):
    stmt = (
        select(Product)
        .join(Business)
        .where(Product.status == "approved", Business.status == "approved")
        .options(selectinload(Product.business).selectinload(Business.location))
    )
    return db.scalars(spatial_filter(stmt, db, **spatial)).all()


def public_businesses(db, **spatial):
    stmt = select(Business).where(Business.status == "approved").options(selectinload(Business.location))
    return db.scalars(spatial_filter(stmt, db, **spatial)).all()


def price_trends(db, product_ids=None):
    stmt = (
        select(Product)
        .join(Business)
        .where(Product.status == "approved", Business.status == "approved")
        .options(selectinload(Product.history), selectinload(Product.business))
    )
    if product_ids is not None:
        stmt = stmt.where(Product.id.in_(product_ids))
    result = []
    for p in db.scalars(stmt):
        history = sorted(p.history, key=lambda h: (h.recorded_at, h.id))
        if len(history) < 2:
            continue
        first, last = history[0], history[-1]
        result.append(
            {
                "product_id": p.id,
                "name": p.name,
                "unit": p.unit,
                "business_name": p.business.name,
                "first_price": float(first.price),
                "latest_price": float(last.price),
                "change_percent": round((float(last.price) / float(first.price) - 1) * 100, 2),
                "from": first.recorded_at.isoformat(),
                "to": last.recorded_at.isoformat(),
                "observations": len(history),
                "is_demo": p.is_demo,
            }
        )
    return result


def statistics(db):
    businesses = public_businesses(db)
    products = public_products(db)
    categories = {}
    regions = {}
    for b in businesses:
        categories[b.category] = categories.get(b.category, 0) + 1
        regions[b.location.region] = regions.get(b.location.region, 0) + 1
    prices = {}
    # Never combine incompatible currencies/units or different product names.
    for p in products:
        key = (p.name, p.unit)
        prices.setdefault(key, []).append(float(p.price))
    return {
        "businesses": len(businesses),
        "products": len(products),
        "seasonal_products": sum(in_season(p.season_start, p.season_end) for p in products),
        "regions": len(regions),
        "business_categories": categories,
        "businesses_by_region": regions,
        "price_comparison": [
            {
                "name": name,
                "unit": unit,
                "min": min(vals),
                "max": max(vals),
                "average": round(sum(vals) / len(vals), 2),
                "offers": len(vals),
            }
            for (name, unit), vals in prices.items()
        ],
        "demo_businesses": sum(b.is_demo for b in businesses),
        "demo_products": sum(p.is_demo for p in products),
        "notice": "Бұл — тек платформаға енгізілген деректер. Демо жазбалар нақты нарық статистикасы емес.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
