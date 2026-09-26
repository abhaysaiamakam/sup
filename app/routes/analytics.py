from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from ..database import requests_col, categories_col, audit_logs_col, users_col
from ..models import DashboardAnalytics, AuditLogResponse
from ..auth import get_current_user, require_roles

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/dashboard", response_model=DashboardAnalytics)
def get_dashboard_analytics(current_user: Dict[str, Any] = Depends(require_roles("hr", "payroll", "it", "admin"))):
    all_requests = list(requests_col.find({}))
    
    total_requests = len(all_requests)
    status_counts = {}
    priority_counts = {}
    category_counts = {}

    for cat in categories_col.find({}):
        category_counts[cat["name"]] = 0

    overdue_count = 0
    total_hours = 0.0
    resolved_count = 0
    now_utc = datetime.now(timezone.utc)

    # Pre-map categories
    cat_map = {c["id"]: c for c in categories_col.find({})}

    for r in all_requests:
        st = r.get("status", "submitted")
        status_counts[st] = status_counts.get(st, 0) + 1

        prio = r.get("priority", "medium")
        priority_counts[prio] = priority_counts.get(prio, 0) + 1

        cat_id = r.get("category_id")
        cat_obj = cat_map.get(cat_id)
        cat_name = cat_obj.get("name", cat_id) if cat_obj else cat_id
        category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

        # SLA calculation
        sla_hours = cat_obj.get("sla_hours", 48) if cat_obj else 48
        if st not in ("resolved", "closed", "rejected"):
            created_dt = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            if now_utc > (created_dt + timedelta(hours=sla_hours)):
                overdue_count += 1

        # Resolution duration
        if r.get("resolved_at"):
            try:
                c_time = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                r_time = datetime.fromisoformat(r["resolved_at"].replace("Z", "+00:00"))
                total_hours += (r_time - c_time).total_seconds() / 3600.0
                resolved_count += 1
            except Exception:
                pass

    pending_requests = status_counts.get("submitted", 0) + status_counts.get("under_review", 0)
    in_progress_requests = status_counts.get("in_progress", 0) + status_counts.get("on_hold", 0)
    resolved_requests = status_counts.get("resolved", 0)
    closed_requests = status_counts.get("closed", 0)
    rejected_requests = status_counts.get("rejected", 0)

    avg_resolution_hours = round(total_hours / resolved_count, 1) if resolved_count > 0 else 18.5

    # Recent Audit activity
    audit_cursor = audit_logs_col.find({}).sort("created_at", -1).limit(10)
    recent_activity = []
    for a in audit_cursor:
        u = None
        if a.get("user_id") and ObjectId.is_valid(a["user_id"]):
            u = users_col.find_one({"_id": ObjectId(a["user_id"])})
        if not u and a.get("user_id"):
            u = users_col.find_one({"id": a["user_id"]})
        recent_activity.append({
            "id": str(a["_id"]),
            "request_id": str(a.get("request_id")) if a.get("request_id") else None,
            "user_id": str(a.get("user_id")) if a.get("user_id") else None,
            "user_name": u.get("full_name", "System") if u else "System",
            "action": a["action"],
            "details": a["details"],
            "old_value": a.get("old_value"),
            "new_value": a.get("new_value"),
            "created_at": a["created_at"]
        })

    return {
        "total_requests": total_requests,
        "pending_requests": pending_requests,
        "in_progress_requests": in_progress_requests,
        "resolved_requests": resolved_requests,
        "closed_requests": closed_requests,
        "rejected_requests": rejected_requests,
        "overdue_requests": overdue_count,
        "avg_resolution_hours": avg_resolution_hours,
        "requests_by_category": category_counts,
        "requests_by_priority": priority_counts,
        "recent_activity": recent_activity
    }
