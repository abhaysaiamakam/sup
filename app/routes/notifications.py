from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from bson import ObjectId
from ..database import notifications_col
from ..models import NotificationResponse
from ..auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.get("", response_model=List[NotificationResponse])
def get_user_notifications(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id_str = str(current_user["id"])
    cursor = notifications_col.find({"user_id": user_id_str}).sort("created_at", -1).limit(50)
    return [{
        "id": str(r["_id"]),
        "user_id": str(r["user_id"]),
        "request_id": str(r.get("request_id")) if r.get("request_id") else None,
        "title": r["title"],
        "message": r["message"],
        "is_read": bool(r.get("is_read", False)),
        "created_at": r["created_at"]
    } for r in cursor]

@router.patch("/{notification_id}/read")
def mark_notification_read(notification_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id_str = str(current_user["id"])
    if ObjectId.is_valid(notification_id):
        notifications_col.update_one(
            {"_id": ObjectId(notification_id), "user_id": user_id_str},
            {"$set": {"is_read": True}}
        )
    return {"success": True}

@router.patch("/read-all")
def mark_all_notifications_read(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id_str = str(current_user["id"])
    notifications_col.update_many(
        {"user_id": user_id_str},
        {"$set": {"is_read": True}}
    )
    return {"success": True}
