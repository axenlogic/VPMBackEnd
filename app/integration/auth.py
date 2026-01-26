from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import HTTPException

from app.core.config import settings


def create_intake_token(client_id: str) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.INTEGRATION_TOKEN_EXPIRY_MINUTES)
    payload = {
        "client_id": client_id,
        "scope": "intake",
        "exp": expiry,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_intake_token(authorization: str) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("scope") != "intake":
        raise HTTPException(status_code=403, detail="Token not authorized for intake endpoints")
    return payload

