import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas import Register, Login, AccountUpdate, PasswordChange
from ..security import current_user, password_hash, token_for, user_dict, rate_limit
from ..config import get_settings

router = APIRouter(prefix="/api/auth", tags=["Тіркелу және есептік жазба"])


def session_response(response, user):
    token = token_for(user)
    settings = get_settings()
    response.set_cookie(
        "harvest_session",
        token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    response.set_cookie(
        "harvest_csrf",
        secrets.token_urlsafe(32),
        httponly=False,
        secure=settings.secure_cookies,
        samesite="strict",
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    return {"access_token": token, "token_type": "bearer", "user": user_dict(user)}


@router.post("/register", status_code=201)
def register(body: Register, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request, "register", 8, 300)
    user = User(email=str(body.email).lower(), name=body.name, password_hash=password_hash.hash(body.password), role=body.role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Бұл электрондық пошта бұрын тіркелген") from None
    return session_response(response, user)


@router.post("/login")
def login(body: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request, "login", 15, 300)
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    # Verify a dummy Argon2 hash too, to reduce email enumeration timing differences.
    valid = password_hash.verify(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.is_active:
        raise HTTPException(401, "Электрондық пошта немесе құпиясөз қате")
    return session_response(response, user)


DUMMY_HASH = password_hash.hash(secrets.token_urlsafe(24))


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_dict(user)


@router.patch("/me")
def update_me(body: AccountUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.name = body.name
    db.commit()
    return user_dict(user)


@router.post("/password")
def change_password(body: PasswordChange, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not password_hash.verify(body.current_password, user.password_hash):
        raise HTTPException(400, "Қазіргі құпиясөз қате")
    user.password_hash = password_hash.hash(body.new_password)
    user.token_version += 1
    db.commit()
    return session_response(response, user)


@router.post("/logout")
def logout(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.token_version += 1
    db.commit()
    response.delete_cookie("harvest_session", path="/")
    response.delete_cookie("harvest_csrf", path="/")
    return {"message": "Жүйеден шықтыңыз"}
