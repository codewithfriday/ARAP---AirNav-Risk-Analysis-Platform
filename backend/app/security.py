from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except ValueError:
        return False


def create_token(username: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.token_minutes)
    return jwt.encode({"sub": username, "exp": exp}, settings.secret_key, algorithm="HS256")


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    try:
        sub = jwt.decode(token, settings.secret_key, algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    u = db.query(User).filter_by(username=sub, active=True).first()
    if not u:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return u


def require(*roles: str):
    def dep(u: User = Depends(current_user)) -> User:
        if u.role not in roles and u.role != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {', '.join(roles)}")
        return u
    return dep


EDITORS = ("assessor", "reviewer")
