from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Business, Product, User
from ..schemas import Moderation, RoleChange
from ..security import admin_user, user_dict
from ..services import business_dict, product_dict

router = APIRouter(prefix="/api/admin", tags=["Модерация"])


@router.get("/queue")
def queue(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return {
        "businesses": [business_dict(b) for b in db.scalars(select(Business).where(Business.status != "approved"))],
        "products": [product_dict(p) for p in db.scalars(select(Product).where(Product.status != "approved"))],
    }


@router.patch("/{kind}/{id}/status")
def moderate(kind: str, id: int, body: Moderation, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    model = {"businesses": Business, "products": Product}.get(kind)
    if not model:
        raise HTTPException(404, "Бөлім табылмады")
    obj = db.get(model, id)
    if not obj:
        raise HTTPException(404, "Жазба табылмады")
    obj.status = body.status
    db.commit()
    return {"id": id, "status": obj.status}


@router.get("/users")
def users(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [user_dict(u) for u in db.scalars(select(User).order_by(User.id))]


@router.patch("/users/{id}")
def change_role(id: int, body: RoleChange, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    target = db.get(User, id)
    if not target:
        raise HTTPException(404, "Пайдаланушы табылмады")
    if id == user.id:
        raise HTTPException(409, "Өзіңіздің рөліңізді немесе белсенділігіңізді мұнда өзгерте алмайсыз")
    target.role = body.role
    target.is_active = body.is_active
    target.token_version += 1
    db.commit()
    return user_dict(target)
