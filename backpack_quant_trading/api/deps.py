"""Dependency injection: auth, DB, steward token."""
import os
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyCookie
import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from backpack_quant_trading.database.models import db_manager

SECRET_KEY = os.environ.get("JWT_SECRET", "backpack-quant-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer(auto_error=False)
cookie_scheme = APIKeyCookie(name="access_token", auto_error=False)


def verify_password(plain: str, hashed: str) -> bool:
    return check_password_hash(hashed, plain)


def get_password_hash(password: str) -> str:
    return generate_password_hash(password)


def create_access_token(data: dict) -> str:
    import datetime
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    cookie: Optional[str] = Depends(cookie_scheme),
) -> Optional[dict]:
    """Resolve user from Bearer token or cookie."""
    token = None
    if credentials:
        token = credentials.credentials
    elif cookie:
        token = cookie
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = db_manager.get_user_by_id(int(user_id))
    if not user:
        return None
    return {"id": user.id, "username": user.username, "role": user.role}


async def require_user(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Require logged-in user; 401 otherwise."""
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def steward_token_ok(token: str) -> bool:
    t = (token or "").strip()
    if not t:
        return False
    expected = (
        os.environ.get("AGENT_STEWARD_TOKEN", "").strip()
        or os.environ.get("WEBHOOK_SECRET", "").strip()
    )
    return bool(expected) and t == expected


async def require_steward(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Steward internal call: Bearer AGENT_STEWARD_TOKEN or WEBHOOK_SECRET."""
    token = credentials.credentials if credentials else ""
    if not steward_token_ok(token):
        raise HTTPException(status_code=401, detail="小管家鉴权失败")
    return {"id": 0, "username": "小管家", "role": "steward"}
