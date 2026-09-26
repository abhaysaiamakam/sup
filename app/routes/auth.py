from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId

from ..database import users_col, audit_logs_col, notifications_col
from ..models import UserRegister, UserLogin, UserResponse, TokenResponse
from ..auth import hash_password, verify_password, create_access_token, get_current_user, require_roles

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

def format_user_doc(u: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(u["_id"]),
        "email": u["email"],
        "username": u["username"],
        "full_name": u["full_name"],
        "role": u["role"],
        "department": u.get("department"),
        "designation": u.get("designation"),
        "employee_id": u.get("employee_id"),
        "phone": u.get("phone"),
        "created_at": u.get("created_at")
    }

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, request: Request):
    # Check if email or username already exists
    existing = users_col.find_one({
        "$or": [
            {"email": user_in.email.lower()},
            {"username": user_in.username.lower()}
        ]
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or username already exists"
        )

    now = datetime.now(timezone.utc).isoformat()
    emp_id = user_in.employee_id or f"EMP-{int(datetime.now().timestamp()) % 10000:04d}"

    user_doc = {
        "email": user_in.email.lower(),
        "username": user_in.username.lower(),
        "full_name": user_in.full_name,
        "password_hash": hash_password(user_in.password),
        "role": user_in.role.value if hasattr(user_in.role, 'value') else user_in.role,
        "department": user_in.department,
        "designation": user_in.designation,
        "employee_id": emp_id,
        "phone": user_in.phone,
        "created_at": now
    }

    res = users_col.insert_one(user_doc)
    user_id = str(res.inserted_id)

    # Log audit
    audit_logs_col.insert_one({
        "request_id": None,
        "user_id": user_id,
        "action": "USER_REGISTERED",
        "details": f"User {user_in.full_name} registered as {user_in.role}",
        "ip_address": request.client.host if request.client else "127.0.0.1",
        "created_at": now
    })

    # Send welcome notification
    notifications_col.insert_one({
        "user_id": user_id,
        "request_id": None,
        "title": "Welcome to HR Service Desk",
        "message": "Your account has been created. You can now raise service requests and track their status in real-time.",
        "is_read": False,
        "created_at": now
    })

    created_user = format_user_doc(users_col.find_one({"_id": res.inserted_id}))

    token = create_access_token(
        user_id=created_user["id"],
        username=created_user["username"],
        email=created_user["email"],
        role=created_user["role"],
        full_name=created_user["full_name"]
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": created_user
    }

@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, request: Request):
    identifier = login_data.username_or_email.lower().strip()
    user_row = users_col.find_one({
        "$or": [
            {"email": identifier},
            {"username": identifier}
        ]
    })

    if not user_row or not verify_password(login_data.password, user_row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password"
        )

    user_id = str(user_row["_id"])
    now = datetime.now(timezone.utc).isoformat()

    # Log login audit
    audit_logs_col.insert_one({
        "request_id": None,
        "user_id": user_id,
        "action": "USER_LOGIN",
        "details": f"User {user_row['full_name']} ({user_row['role']}) logged in",
        "ip_address": request.client.host if request.client else "127.0.0.1",
        "created_at": now
    })

    formatted_user = format_user_doc(user_row)

    token = create_access_token(
        user_id=formatted_user["id"],
        username=formatted_user["username"],
        email=formatted_user["email"],
        role=formatted_user["role"],
        full_name=formatted_user["full_name"]
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": formatted_user
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return format_user_doc(current_user)

@router.get("/staff", response_model=List[UserResponse])
def get_staff_members(current_user: Dict[str, Any] = Depends(require_roles("hr", "payroll", "it", "admin"))):
    cursor = users_col.find({"role": {"$in": ["hr", "payroll", "it", "admin"]}}).sort("full_name", 1)
    return [format_user_doc(u) for u in cursor]

@router.get("/users", response_model=List[UserResponse])
def get_all_users(current_user: Dict[str, Any] = Depends(require_roles("admin"))):
    cursor = users_col.find({}).sort("created_at", -1)
    return [format_user_doc(u) for u in cursor]
