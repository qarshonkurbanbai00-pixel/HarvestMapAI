from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from .config import get_settings
from .database import get_db
from .models import User

password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
# Single-process limit, deliberately bounded; use an edge limiter for multiple workers.
_buckets = defaultdict(deque)
_lock = Lock()


def rate_limit(request: Request, scope: str, count: int, seconds: int = 60):
    now = datetime.now(timezone.utc).timestamp()
    key = (request.client.host if request.client else "unknown", scope)
    with _lock:
        if len(_buckets) > 10000:
            for old in list(_buckets):
                if not _buckets[old] or now - _buckets[old][-1] > seconds:
                    del _buckets[old]
            if len(_buckets) > 10000:
                raise HTTPException(429, "Сұрау тым көп. Кейінірек қайталаңыз.")
        bucket = _buckets[key]
        while bucket and now - bucket[0] >= seconds:
            bucket.popleft()
        if len(bucket) >= count:
            raise HTTPException(429, "Сұрау тым көп. Біраз уақыттан кейін қайталаңыз.", headers={"Retry-After": str(seconds)})
        bucket.append(now)


def token_for(user: User):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user.id), "ver": user.token_version, "iat": now, "exp": now + timedelta(minutes=get_settings().access_token_minutes)},
        get_settings().secret_key,
        algorithm="HS256",
    )


def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    token = credentials.credentials if credentials else request.cookies.get("harvest_session")
    if not token:
        raise HTTPException(401, "Жүйеге кіріңіз")
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"], options={"require": ["exp", "sub", "ver"]})
        user = db.get(User, int(payload["sub"]))
        if not user or not user.is_active or user.token_version != payload["ver"]:
            raise ValueError()
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(401, "Сессия аяқталды. Қайта кіріңіз.") from None
    return user


def owner_user(user: User = Depends(current_user)):
    if user.role not in ("owner", "admin"):
        raise HTTPException(403, "Кәсіп иесінің рұқсаты қажет")
    return user


def admin_user(user: User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Әкімші рұқсаты қажет")
    return user


def check_owner(business, user):
    if business.owner_id != user.id and user.role != "admin":
        raise HTTPException(403, "Бұл кәсіпті өзгертуге рұқсат жоқ")


def user_dict(user):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "is_active": user.is_active}
