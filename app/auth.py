import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import jwt
from bson import ObjectId
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from .database import users_col

SECRET_KEY = os.getenv("JWT_SECRET", "hr-enterprise-secret-key-prod-2026-secure-token")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}:{key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        if not hashed_password or ":" not in hashed_password:
            return False
        salt, key = hashed_password.split(":")
        computed = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(computed.hex(), key)
    except Exception:
        return False

def create_access_token(user_id: str, username: str, email: str, role: str, full_name: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "email": email,
        "role": role,
        "full_name": full_name,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: Optional[str] = Depends(oauth2_scheme), authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    auth_token = token
    if not auth_token and authorization and authorization.startswith("Bearer "):
        auth_token = authorization.split(" ")[1]

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token claims",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    user = None
    if user_id and ObjectId.is_valid(user_id):
        user = users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        username = payload.get("username")
        if username:
            user = users_col.find_one({"username": username})
    if not user:
        email = payload.get("email")
        if email:
            user = users_col.find_one({"email": email})
    if not user:
        user = users_col.find_one({"id": user_id})

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists",
        )

    user["id"] = str(user["_id"])
    return user

def require_roles(*allowed_roles: str):
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_role = current_user.get("role")
        if user_role not in allowed_roles and "admin" not in allowed_roles and user_role != "admin":
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Requires one of roles: {', '.join(allowed_roles)} (Your role: {user_role})",
                )
        return current_user
    return role_checker

def can_access_request(user: Dict[str, Any], request_doc: Dict[str, Any]) -> bool:
    user_role = user.get("role")
    user_id = str(user.get("id"))

    # Owner can always see their own request
    if str(request_doc.get("user_id")) == user_id:
        return True

    # Admin has master access
    if user_role == "admin":
        return True

    # Confidential Payroll Query check
    if request_doc.get("is_confidential") or request_doc.get("category_id") == "payroll_query":
        if user_role in ("payroll", "admin"):
            return True
        if str(request_doc.get("assigned_to")) == user_id:
            return True
        return False

    # HR and IT can see general operational requests
    if user_role in ("hr", "payroll", "it"):
        return True

    return False
