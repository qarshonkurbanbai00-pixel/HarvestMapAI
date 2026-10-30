"""Idempotent, explicitly fictional demonstration data; no hard-coded login credentials."""

import argparse
from datetime import datetime, timedelta, timezone
import secrets
from sqlalchemy import select
from app.database import SessionLocal
from app.models import User, Location, Business, Product, PriceHistory
from app.security import password_hash

LOCATIONS = [
    ("Алматы", "Алматы қаласы", 43.2389, 76.8897),
    ("Талғар", "Алматы облысы", 43.3045, 77.2328),
    ("Қаскелең", "Алматы облысы", 43.2000, 76.6200),
    ("Шымкент", "Шымкент қаласы", 42.3155, 69.5869),
    ("Түркістан", "Түркістан облысы", 43.3010, 68.2690),
    ("Астана", "Астана қаласы", 51.1694, 71.4491),
]
BUSINESSES = [
    ("Демо · Жасыл алқап", "farm", 1, "Көкөніс өсіретін оқу үлгісіндегі шаруашылық."),
    ("Демо · Алма бағы", "farm", 1, "Жеміс-жидек ұсынатын ойдан шығарылған бақ."),
    ("Демо · Береке дүкені", "shop", 0, "Жергілікті өнімдер сататын оқу дүкені."),
    ("Демо · Таңғы базар", "market", 0, "Маусымдық өнімдерге арналған үлгілік базар."),
    ("Демо · Дала дәмі", "farm", 2, "Сүт өнімдерін ұсынатын үлгілік шаруашылық."),
    ("Демо · Оңтүстік өнім", "farm", 3, "Оңтүстік өңірдің көкөністеріне арналған үлгі."),
    ("Демо · Түркістан астығы", "farm", 4, "Дәнді дақылдарға арналған ойдан шығарылған кәсіп."),
    ("Демо · Астана жеткізу", "service", 5, "Жергілікті өнімдерді жеткізу қызметінің үлгісі."),
]
PRODUCTS = [
    ("Қызанақ", "vegetables", 650, "кг", 5, 10, 0),
    ("Қияр", "vegetables", 480, "кг", 4, 10, 0),
    ("Алма", "fruit", 420, "кг", 8, 11, 1),
    ("Алмұрт", "fruit", 780, "кг", 8, 10, 1),
    ("Қызанақ", "vegetables", 720, "кг", 5, 10, 2),
    ("Алма", "fruit", 510, "кг", 8, 11, 2),
    ("Сәбіз", "vegetables", 240, "кг", 7, 11, 3),
    ("Картоп", "vegetables", 210, "кг", 8, 12, 3),
    ("Сүт", "dairy", 450, "л", 1, 12, 4),
    ("Ірімшік", "dairy", 2400, "кг", 1, 12, 4),
    ("Бал", "honey", 3500, "кг", 5, 9, 4),
    ("Қызанақ", "vegetables", 580, "кг", 4, 11, 5),
    ("Қарбыз", "fruit", 180, "кг", 6, 9, 5),
    ("Бидай", "grain", 130, "кг", 7, 10, 6),
    ("Ұн", "grain", 320, "кг", 1, 12, 6),
    ("Сүт", "dairy", 520, "л", 1, 12, 7),
]


def seed():
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == "demo-owner@example.invalid"))
        if existing:
            print("Demo seed already exists. No rows changed.")
            return
        owner = User(
            email="demo-owner@example.invalid",
            name="Демо деректер иесі",
            role="owner",
            password_hash=password_hash.hash(secrets.token_urlsafe(48)),
            is_active=False,
        )
        db.add(owner)
        db.flush()
        locs = []
        for name, region, lat, lon in LOCATIONS:
            l = Location(name=name, region=region, latitude=lat, longitude=lon, is_demo=True)
            db.add(l)
            locs.append(l)
        db.flush()
        bs = []
        for i, (name, cat, li, desc) in enumerate(BUSINESSES):
            l = locs[li]
            b = Business(
                owner_id=owner.id,
                location_id=l.id,
                name=name,
                category=cat,
                description=desc + " Бұл жазба нақты кәсіп туралы мәлімет емес.",
                address="Демо мекенжай, " + str(i + 1),
                latitude=l.latitude + (i % 3) * 0.012,
                longitude=l.longitude + (i % 3) * 0.017,
                status="approved",
                is_demo=True,
            )
            db.add(b)
            bs.append(b)
        db.flush()
        for i, (name, cat, price, unit, start, end, bi) in enumerate(PRODUCTS):
            p = Product(
                business_id=bs[bi].id,
                name=name,
                category=cat,
                description="Оқу мақсатындағы үлгілік өнім. Бағасы мен қоры ойдан алынған; нақты сатылым ұсынысы емес.",
                price=price,
                unit=unit,
                stock=80 + i * 10,
                season_start=start,
                season_end=end,
                status="approved",
                is_demo=True,
            )
            db.add(p)
            db.flush()
            for j in range(6):
                db.add(
                    PriceHistory(
                        product_id=p.id,
                        price=round(price * (1 + (5 - j) * 0.025), 2),
                        recorded_at=datetime.now(timezone.utc) - timedelta(days=(5 - j) * 7),
                    )
                )
        db.commit()
        print("Created 6 demo locations, 8 demo businesses, 16 demo products and 96 price-history points. No login accounts created.")


if __name__ == "__main__":
    seed()
