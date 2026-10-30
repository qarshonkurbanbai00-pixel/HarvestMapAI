from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from ..database import get_db
from ..models import Business, Product, Location, PriceHistory, User
from ..schemas import BusinessIn, ProductIn, LocationIn
from ..security import current_user, owner_user, admin_user, check_owner
from ..services import business_dict, product_dict, in_season, public_products, public_businesses, statistics, distance_km, price_trends

router = APIRouter(prefix="/api", tags=["Каталог және карта"])


def get_business(db, id):
    b = db.get(Business, id)
    if not b:
        raise HTTPException(404, "Кәсіп табылмады")
    return b


def get_product(db, id):
    p = db.get(Product, id)
    if not p:
        raise HTTPException(404, "Өнім табылмады")
    return p


def page(items, page, size):
    return {
        "items": items[(page - 1) * size : page * size],
        "total": len(items),
        "page": page,
        "size": size,
        "pages": (len(items) + size - 1) // size,
    }


@router.get("/locations")
def locations(db: Session = Depends(get_db)):
    return [
        {"id": l.id, "name": l.name, "region": l.region, "latitude": l.latitude, "longitude": l.longitude, "is_demo": l.is_demo}
        for l in db.scalars(select(Location).order_by(Location.name))
    ]


@router.post("/locations", status_code=201)
def create_location(body: LocationIn, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    l = Location(**body.model_dump())
    db.add(l)
    db.commit()
    db.refresh(l)
    return {"id": l.id, **body.model_dump()}


@router.put("/locations/{id}")
def update_location(id: int, body: LocationIn, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    l = db.get(Location, id)
    if not l:
        raise HTTPException(404, "Елді мекен табылмады")
    for k, v in body.model_dump().items():
        setattr(l, k, v)
    db.commit()
    return {"id": id, **body.model_dump()}


@router.delete("/locations/{id}")
def delete_location(id: int, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    l = db.get(Location, id)
    if not l:
        raise HTTPException(404, "Елді мекен табылмады")
    if db.scalar(select(func.count()).select_from(Business).where(Business.location_id == id)):
        raise HTTPException(409, "Бұл елді мекенде кәсіптер бар")
    db.delete(l)
    db.commit()
    return {"message": "Елді мекен жойылды"}


@router.get("/businesses")
def businesses(
    q: str = Query("", max_length=150),
    category: str = "",
    location_id: int | None = None,
    sort: str = Query("name", pattern="^(name|newest)$"),
    page_number: int = Query(1, ge=1, alias="page"),
    size: int = Query(12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Business).where(Business.status == "approved").options(selectinload(Business.location))
    if q:
        stmt = stmt.where(func.lower(Business.name + " " + Business.description).contains(q.lower(), autoescape=True))
    if category:
        stmt = stmt.where(Business.category == category)
    if location_id:
        stmt = stmt.where(Business.location_id == location_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = (
        stmt.order_by(Business.name if sort == "name" else Business.created_at.desc(), Business.id)
        .offset((page_number - 1) * size)
        .limit(size)
    )
    return {
        "items": [business_dict(b) for b in db.scalars(stmt)],
        "total": total,
        "page": page_number,
        "size": size,
        "pages": (total + size - 1) // size,
    }


@router.get("/businesses/{id}")
def business(id: int, db: Session = Depends(get_db)):
    b = get_business(db, id)
    if b.status != "approved":
        raise HTTPException(404, "Кәсіп табылмады")
    return {**business_dict(b), "products": [product_dict(p) for p in b.products if p.status == "approved"]}


@router.post("/businesses", status_code=201)
def create_business(body: BusinessIn, user: User = Depends(owner_user), db: Session = Depends(get_db)):
    if not db.get(Location, body.location_id):
        raise HTTPException(422, "Елді мекенді таңдаңыз")
    b = Business(**body.model_dump(), owner_id=user.id, status="pending")
    db.add(b)
    db.commit()
    return business_dict(b)


@router.put("/businesses/{id}")
def update_business(id: int, body: BusinessIn, user: User = Depends(owner_user), db: Session = Depends(get_db)):
    b = get_business(db, id)
    check_owner(b, user)
    if not db.get(Location, body.location_id):
        raise HTTPException(422, "Елді мекенді таңдаңыз")
    for k, v in body.model_dump().items():
        setattr(b, k, v)
    # Content changes always go through moderation again, including admin edits.
    b.status = "pending"
    db.commit()
    db.refresh(b)
    return business_dict(b)


@router.delete("/businesses/{id}")
def delete_business(id: int, user: User = Depends(owner_user), db: Session = Depends(get_db)):
    b = get_business(db, id)
    check_owner(b, user)
    db.delete(b)
    db.commit()
    return {"message": "Кәсіп және оған тиесілі өнімдер жойылды"}


@router.get("/products")
def products(
    q: str = Query("", max_length=150),
    category: str = "",
    location_id: int | None = None,
    business_id: int | None = None,
    seasonal: bool = False,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    unit: str = "",
    sort: str = Query("name", pattern="^(name|price_asc|price_desc|newest)$"),
    page_number: int = Query(1, ge=1, alias="page"),
    size: int = Query(12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Product)
        .join(Business)
        .where(Product.status == "approved", Business.status == "approved")
        .options(selectinload(Product.business).selectinload(Business.location))
    )
    if q:
        stmt = stmt.where(func.lower(Product.name + " " + Product.description).contains(q.lower(), autoescape=True))
    if category:
        stmt = stmt.where(Product.category == category)
    if location_id:
        stmt = stmt.where(Business.location_id == location_id)
    if business_id:
        stmt = stmt.where(Product.business_id == business_id)
    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)
    if unit:
        stmt = stmt.where(Product.unit == unit)
    order = {"name": Product.name, "price_asc": Product.price, "price_desc": Product.price.desc(), "newest": Product.created_at.desc()}[
        sort
    ]
    if seasonal:
        # Seasonal predicate handles seasons crossing December/January.
        from datetime import datetime, timezone
        from sqlalchemy import and_, or_

        m = datetime.now(timezone.utc).month
        stmt = stmt.where(
            or_(
                and_(Product.season_start <= Product.season_end, Product.season_start <= m, Product.season_end >= m),
                and_(Product.season_start > Product.season_end, or_(Product.season_start <= m, Product.season_end >= m)),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(order, Product.id).offset((page_number - 1) * size).limit(size))
    return {
        "items": [product_dict(p) for p in rows],
        "total": total,
        "page": page_number,
        "size": size,
        "pages": (total + size - 1) // size,
    }


@router.get("/products/{id}")
def product(id: int, db: Session = Depends(get_db)):
    p = get_product(db, id)
    if p.status != "approved" or p.business.status != "approved":
        raise HTTPException(404, "Өнім табылмады")
    return {**product_dict(p), "history": [{"price": float(h.price), "recorded_at": h.recorded_at.isoformat()} for h in p.history]}


@router.post("/products", status_code=201)
def create_product(body: ProductIn, user: User = Depends(owner_user), db: Session = Depends(get_db)):
    b = get_business(db, body.business_id)
    check_owner(b, user)
    p = Product(**body.model_dump(), status="pending")
    db.add(p)
    db.flush()
    db.add(PriceHistory(product_id=p.id, price=p.price))
    db.commit()
    return product_dict(p)


@router.put("/products/{id}")
def update_product(id: int, body: ProductIn, user: User = Depends(owner_user), db: Session = Depends(get_db)):
    p = get_product(db, id)
    check_owner(p.business, user)
    b = get_business(db, body.business_id)
    check_owner(b, user)
    from decimal import Decimal

    if p.price != Decimal(str(body.price)).quantize(Decimal("0.01")):
        db.add(PriceHistory(product_id=p.id, price=body.price))
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    p.status = "pending"
    db.commit()
    db.refresh(p)
    return product_dict(p)


@router.delete("/products/{id}")
def delete_product(id: int, user: User = Depends(owner_user), db: Session = Depends(get_db)):
    p = get_product(db, id)
    check_owner(p.business, user)
    db.delete(p)
    db.commit()
    return {"message": "Өнім жойылды"}


@router.get("/owner/catalog")
def own_catalog(user: User = Depends(owner_user), db: Session = Depends(get_db)):
    stmt = select(Business).options(selectinload(Business.location), selectinload(Business.products).selectinload(Product.business))
    if user.role != "admin":
        stmt = stmt.where(Business.owner_id == user.id)
    bs = db.scalars(stmt.order_by(Business.id)).all()
    return {"businesses": [business_dict(b) for b in bs], "products": [product_dict(p) for b in bs for p in b.products]}


@router.get("/statistics")
def stats(db: Session = Depends(get_db)):
    return statistics(db)


@router.get("/statistics/trends")
def trends(product_id: int | None = None, db: Session = Depends(get_db)):
    return {
        "items": price_trends(db, [product_id] if product_id is not None else None),
        "notice": "Өнімнің алғашқы және соңғы тіркелген бағалары салыстырылды; бұл нарық болжамы емес.",
    }


@router.get("/map")
def map_data(
    q: str = Query("", max_length=150),
    kind: str = Query("all", pattern="^(all|business|product)$"),
    category: str = "",
    location_id: int | None = None,
    lat: float | None = Query(None, ge=-90, le=90),
    lon: float | None = Query(None, ge=-180, le=180),
    radius_km: float = Query(50, gt=0, le=20000),
    bbox: str | None = None,
    db: Session = Depends(get_db),
):
    if (lat is None) != (lon is None):
        raise HTTPException(422, "Ендік пен бойлықты бірге көрсетіңіз")
    bounds = None
    if bbox:
        try:
            bounds = [float(x) for x in bbox.split(",")]
            w, s, e, n = bounds
            if not (-180 <= w <= 180 and -180 <= e <= 180 and -90 <= s <= n <= 90):
                raise ValueError()
        except (ValueError, TypeError):
            raise HTTPException(422, "bbox пішімі: батыс,оңтүстік,шығыс,солтүстік") from None
    features = []
    rows = []
    if kind in ("all", "business"):
        rows.extend(("business", business_dict(b)) for b in public_businesses(db, lat=lat, lon=lon, radius_km=radius_km, bounds=bounds))
    if kind in ("all", "product"):
        rows.extend(("product", product_dict(p)) for p in public_products(db, lat=lat, lon=lon, radius_km=radius_km, bounds=bounds))
    for typ, item in rows:
        if (
            q
            and q.casefold()
            not in (
                item["name"] + " " + item.get("location_name", item.get("location", {}).get("name", "")) + " " + item["description"]
            ).casefold()
        ):
            continue
        if category and item["category"] != category:
            continue
        if location_id and item["location_id"] != location_id:
            continue
        y, x = item["latitude"], item["longitude"]
        if bounds:
            w, s, e, n = bounds
            if not s <= y <= n or not ((w <= x <= e) if w <= e else (x >= w or x <= e)):
                continue
        distance = distance_km(lat, lon, y, x) if lat is not None else None
        if distance is not None and distance > radius_km:
            continue
        features.append(
            {
                "type": "Feature",
                "id": f"{typ}-{item['id']}",
                "geometry": {"type": "Point", "coordinates": [x, y]},
                "properties": {**item, "kind": typ, "distance_km": round(distance, 2) if distance is not None else None},
            }
        )
    if lat is not None:
        features.sort(key=lambda f: f["properties"]["distance_km"])
    return {
        "type": "FeatureCollection",
        "features": features[:1000],
        "total": len(features),
        "truncated": len(features) > 1000,
        "notice": "Демо нүктелер — оқу үлгілері; расталған кәсіптер емес.",
    }
