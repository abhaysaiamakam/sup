from fastapi import APIRouter, HTTPException, status, Depends, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from pathlib import Path
from bson import ObjectId
import shutil
import uuid

from ..database import (
    requests_col, categories_col, users_col, comments_col,
    attachments_col, audit_logs_col, notifications_col, UPLOAD_DIR
)
from ..models import (
    RequestCreate, RequestStatusUpdate, RequestAssignUpdate,
    RequestResponse, RequestDetailResponse, CommentCreate, CommentResponse,
    AttachmentResponse, AuditLogResponse
)
from ..auth import get_current_user, require_roles, can_access_request

router = APIRouter(prefix="/api/requests", tags=["Service Requests"])

def format_request_doc(doc: Dict[str, Any], current_user_role: str) -> Dict[str, Any]:
    req_id = str(doc["_id"])
    
    # Requester info
    requester = None
    if ObjectId.is_valid(doc.get("user_id", "")):
        requester = users_col.find_one({"_id": ObjectId(doc["user_id"])})
    if not requester:
        requester = users_col.find_one({"id": doc.get("user_id")})

    # Category info
    category = categories_col.find_one({"id": doc.get("category_id")})

    # Assignee info
    assignee = None
    if doc.get("assigned_to"):
        if ObjectId.is_valid(doc["assigned_to"]):
            assignee = users_col.find_one({"_id": ObjectId(doc["assigned_to"])})
        if not assignee:
            assignee = users_col.find_one({"id": doc["assigned_to"]})

    # Counts
    comment_filter = {"request_id": req_id}
    if current_user_role == "employee":
        comment_filter["is_internal"] = False
    comment_count = comments_col.count_documents(comment_filter)
    attachment_count = attachments_col.count_documents({"request_id": req_id})

    # Overdue SLA check
    sla_hours = category.get("sla_hours", 48) if category else 48
    created_dt = datetime.fromisoformat(doc["created_at"].replace("Z", "+00:00"))
    sla_deadline = created_dt + timedelta(hours=sla_hours)
    is_overdue = False
    if doc.get("status") not in ("resolved", "closed", "rejected"):
        if datetime.now(timezone.utc) > sla_deadline:
            is_overdue = True

    return {
        "id": req_id,
        "request_number": doc["request_number"],
        "category_id": doc["category_id"],
        "category_name": category.get("name", doc["category_id"]) if category else doc["category_id"],
        "category_icon": category.get("icon", "file") if category else "file",
        "user_id": str(doc["user_id"]),
        "requester_name": requester.get("full_name", "Unknown") if requester else "Unknown",
        "requester_email": requester.get("email", "") if requester else "",
        "requester_department": requester.get("department", "General") if requester else "General",
        "requester_employee_id": requester.get("employee_id", "") if requester else "",
        "title": doc["title"],
        "description": doc["description"],
        "priority": doc["priority"],
        "status": doc["status"],
        "assigned_to": str(doc["assigned_to"]) if doc.get("assigned_to") else None,
        "assignee_name": assignee.get("full_name") if assignee else None,
        "rejection_reason": doc.get("rejection_reason"),
        "resolution_notes": doc.get("resolution_notes"),
        "custom_data": doc.get("custom_data", {}),
        "is_confidential": bool(doc.get("is_confidential", False)),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
        "resolved_at": doc.get("resolved_at"),
        "closed_at": doc.get("closed_at"),
        "comment_count": comment_count,
        "attachment_count": attachment_count,
        "is_overdue": is_overdue
    }

@router.post("", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
def create_service_request(req_in: RequestCreate, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    cat_doc = categories_col.find_one({"id": req_in.category_id})
    if not cat_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Category '{req_in.category_id}' does not exist")

    now = datetime.now(timezone.utc).isoformat()
    req_number = f"HR-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
    is_confidential = True if req_in.category_id == "payroll_query" or req_in.is_confidential else False

    req_doc = {
        "request_number": req_number,
        "category_id": req_in.category_id,
        "user_id": str(current_user["id"]),
        "title": req_in.title,
        "description": req_in.description,
        "priority": req_in.priority.value if hasattr(req_in.priority, 'value') else req_in.priority,
        "status": "submitted",
        "assigned_to": None,
        "rejection_reason": None,
        "resolution_notes": None,
        "custom_data": req_in.custom_data or {},
        "is_confidential": is_confidential,
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
        "closed_at": None
    }

    res = requests_col.insert_one(req_doc)
    req_id = str(res.inserted_id)

    # Audit log
    audit_logs_col.insert_one({
        "request_id": req_id,
        "user_id": str(current_user["id"]),
        "action": "REQUEST_CREATED",
        "details": f"{current_user['full_name']} created {cat_doc['name']} request: {req_in.title}",
        "old_value": None,
        "new_value": "submitted",
        "ip_address": request.client.host if request.client else "127.0.0.1",
        "created_at": now
    })

    # Notification to requester
    notifications_col.insert_one({
        "user_id": str(current_user["id"]),
        "request_id": req_id,
        "title": "Request Submitted",
        "message": f"Your service request {req_number} ({cat_doc['name']}) has been successfully submitted.",
        "is_read": False,
        "created_at": now
    })

    # Notify staff
    staff_cursor = users_col.find({"$or": [{"role": cat_doc["default_handler_role"]}, {"role": "admin"}]})
    for staff in staff_cursor:
        if str(staff["_id"]) != str(current_user["id"]):
            notifications_col.insert_one({
                "user_id": str(staff["_id"]),
                "request_id": req_id,
                "title": "New Service Request",
                "message": f"New request {req_number} raised by {current_user['full_name']} in {cat_doc['name']}.",
                "is_read": False,
                "created_at": now
            })

    created_doc = requests_col.find_one({"_id": res.inserted_id})
    return format_request_doc(created_doc, current_user["role"])

@router.get("", response_model=List[RequestResponse])
def get_service_requests(
    category_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    assigned_to: Optional[str] = None,
    my_assigned_only: Optional[bool] = False,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    query = {}

    # Role enforcement
    if current_user["role"] == "employee":
        query["user_id"] = str(current_user["id"])
    else:
        # Non-admin / non-payroll staff cannot see confidential payroll queries unless they own it or are assigned
        if current_user["role"] not in ("admin", "payroll"):
            query["$or"] = [
                {"is_confidential": False},
                {"user_id": str(current_user["id"])},
                {"assigned_to": str(current_user["id"])}
            ]

    # Filters
    if category_id:
        query["category_id"] = category_id
    if status:
        query["status"] = status
    if priority:
        query["priority"] = priority
    if assigned_to:
        query["assigned_to"] = assigned_to
    if my_assigned_only:
        query["assigned_to"] = str(current_user["id"])
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"request_number": {"$regex": search, "$options": "i"}}
        ]

    cursor = requests_col.find(query).sort("created_at", -1)
    return [format_request_doc(doc, current_user["role"]) for doc in cursor]

@router.get("/{request_id}", response_model=RequestDetailResponse)
def get_service_request_detail(request_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    doc = None
    if ObjectId.is_valid(request_id):
        doc = requests_col.find_one({"_id": ObjectId(request_id)})
    if not doc:
        doc = requests_col.find_one({"id": request_id})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")

    if not can_access_request(current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to view this request")

    base_formatted = format_request_doc(doc, current_user["role"])
    req_id_str = str(doc["_id"])

    # Fetch comments
    comment_filter = {"request_id": req_id_str}
    if current_user["role"] == "employee":
        comment_filter["is_internal"] = False

    comments_cursor = comments_col.find(comment_filter).sort("created_at", 1)
    comments = []
    for c in comments_cursor:
        u = None
        if ObjectId.is_valid(c.get("user_id", "")):
            u = users_col.find_one({"_id": ObjectId(c["user_id"])})
        if not u:
            u = users_col.find_one({"id": c.get("user_id")})
        comments.append({
            "id": str(c["_id"]),
            "request_id": str(c["request_id"]),
            "user_id": str(c["user_id"]),
            "user_name": u.get("full_name", "Staff") if u else "Staff",
            "user_role": u.get("role", "employee") if u else "employee",
            "message": c["message"],
            "is_internal": bool(c.get("is_internal", False)),
            "created_at": c["created_at"]
        })

    # Fetch attachments
    att_cursor = attachments_col.find({"request_id": req_id_str}).sort("created_at", 1)
    attachments = []
    for a in att_cursor:
        u = None
        if ObjectId.is_valid(a.get("user_id", "")):
            u = users_col.find_one({"_id": ObjectId(a["user_id"])})
        if not u:
            u = users_col.find_one({"id": a.get("user_id")})
        attachments.append({
            "id": str(a["_id"]),
            "request_id": str(a["request_id"]),
            "user_id": str(a["user_id"]),
            "uploader_name": u.get("full_name", "User") if u else "User",
            "filename": a["filename"],
            "file_size": a["file_size"],
            "content_type": a["content_type"],
            "attachment_type": a.get("attachment_type", "supporting"),
            "created_at": a["created_at"]
        })

    # Fetch audit logs
    audit_cursor = audit_logs_col.find({"request_id": req_id_str}).sort("created_at", -1)
    audit_logs = []
    for al in audit_cursor:
        u = None
        if al.get("user_id") and ObjectId.is_valid(al["user_id"]):
            u = users_col.find_one({"_id": ObjectId(al["user_id"])})
        if not u and al.get("user_id"):
            u = users_col.find_one({"id": al["user_id"]})
        audit_logs.append({
            "id": str(al["_id"]),
            "request_id": str(al.get("request_id")) if al.get("request_id") else None,
            "user_id": str(al.get("user_id")) if al.get("user_id") else None,
            "user_name": u.get("full_name", "System") if u else "System",
            "action": al["action"],
            "details": al["details"],
            "old_value": al.get("old_value"),
            "new_value": al.get("new_value"),
            "created_at": al["created_at"]
        })

    return {
        **base_formatted,
        "comments": comments,
        "attachments": attachments,
        "audit_logs": audit_logs
    }

@router.patch("/{request_id}/status", response_model=RequestResponse)
def update_request_status(
    request_id: str,
    status_update: RequestStatusUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    doc = None
    if ObjectId.is_valid(request_id):
        doc = requests_col.find_one({"_id": ObjectId(request_id)})
    if not doc:
        doc = requests_col.find_one({"id": request_id})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")

    current_status = doc["status"]
    new_status = status_update.status.value if hasattr(status_update.status, 'value') else status_update.status

    # Employee can only close a resolved request
    if current_user["role"] == "employee":
        if str(doc["user_id"]) != str(current_user["id"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage your own requests")
        if new_status != "closed" or current_status != "resolved":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employees can only close a request once it has been resolved by HR")

    now = datetime.now(timezone.utc).isoformat()
    resolved_at = now if new_status == "resolved" else doc.get("resolved_at")
    closed_at = now if new_status == "closed" else doc.get("closed_at")
    rejection_reason = status_update.reason_or_notes if new_status == "rejected" else doc.get("rejection_reason")
    resolution_notes = status_update.reason_or_notes if new_status in ("resolved", "closed") else doc.get("resolution_notes")

    requests_col.update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "status": new_status,
            "rejection_reason": rejection_reason,
            "resolution_notes": resolution_notes,
            "updated_at": now,
            "resolved_at": resolved_at,
            "closed_at": closed_at
        }}
    )

    # Audit log
    details_msg = f"{current_user['full_name']} changed status from '{current_status}' to '{new_status}'"
    if status_update.reason_or_notes:
        details_msg += f". Remarks: {status_update.reason_or_notes}"

    audit_logs_col.insert_one({
        "request_id": str(doc["_id"]),
        "user_id": str(current_user["id"]),
        "action": "STATUS_CHANGE",
        "details": details_msg,
        "old_value": current_status,
        "new_value": new_status,
        "ip_address": request.client.host if request.client else "127.0.0.1",
        "created_at": now
    })

    # Notification to requester
    if str(current_user["id"]) != str(doc["user_id"]):
        notif_msg = f"Status of your request {doc['request_number']} changed to {new_status.upper().replace('_', ' ')}."
        if status_update.reason_or_notes:
            notif_msg += f" Note: {status_update.reason_or_notes}"
        notifications_col.insert_one({
            "user_id": str(doc["user_id"]),
            "request_id": str(doc["_id"]),
            "title": "Request Status Updated",
            "message": notif_msg,
            "is_read": False,
            "created_at": now
        })

    updated_doc = requests_col.find_one({"_id": doc["_id"]})
    return format_request_doc(updated_doc, current_user["role"])

@router.patch("/{request_id}/assign", response_model=RequestResponse)
def assign_service_request(
    request_id: str,
    assign_in: RequestAssignUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles("hr", "payroll", "it", "admin"))
):
    doc = None
    if ObjectId.is_valid(request_id):
        doc = requests_col.find_one({"_id": ObjectId(request_id)})
    if not doc:
        doc = requests_col.find_one({"id": request_id})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")

    assignee_name = "Unassigned"
    assigned_to_id = None
    if assign_in.assigned_to:
        staff_doc = None
        if ObjectId.is_valid(assign_in.assigned_to):
            staff_doc = users_col.find_one({"_id": ObjectId(assign_in.assigned_to)})
        if not staff_doc:
            staff_doc = users_col.find_one({"id": assign_in.assigned_to})
        
        if not staff_doc or staff_doc.get("role") not in ('hr', 'payroll', 'it', 'admin'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected staff member does not exist or lacks staff privileges")
        
        assignee_name = staff_doc["full_name"]
        assigned_to_id = str(staff_doc["_id"])

    now = datetime.now(timezone.utc).isoformat()
    old_assigned_to = doc.get("assigned_to")
    new_status = doc["status"]
    if doc["status"] == "submitted" and assigned_to_id:
        new_status = "under_review"

    requests_col.update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "assigned_to": assigned_to_id,
            "status": new_status,
            "updated_at": now
        }}
    )

    # Audit log
    audit_logs_col.insert_one({
        "request_id": str(doc["_id"]),
        "user_id": str(current_user["id"]),
        "action": "ASSIGNMENT_CHANGE",
        "details": f"{current_user['full_name']} assigned request {doc['request_number']} to {assignee_name}. Note: {assign_in.assignment_note or 'None'}",
        "old_value": str(old_assigned_to),
        "new_value": str(assigned_to_id),
        "ip_address": request.client.host if request.client else "127.0.0.1",
        "created_at": now
    })

    # Notification to newly assigned staff
    if assigned_to_id and assigned_to_id != str(current_user["id"]):
        notifications_col.insert_one({
            "user_id": assigned_to_id,
            "request_id": str(doc["_id"]),
            "title": "Request Assigned to You",
            "message": f"You have been assigned to service request {doc['request_number']} ({doc['title']}).",
            "is_read": False,
            "created_at": now
        })

    updated_doc = requests_col.find_one({"_id": doc["_id"]})
    return format_request_doc(updated_doc, current_user["role"])

@router.post("/{request_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    request_id: str,
    comment_in: CommentCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    doc = None
    if ObjectId.is_valid(request_id):
        doc = requests_col.find_one({"_id": ObjectId(request_id)})
    if not doc:
        doc = requests_col.find_one({"id": request_id})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")

    if not can_access_request(current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to comment on this request")

    is_internal = bool(comment_in.is_internal and current_user["role"] != "employee")
    now = datetime.now(timezone.utc).isoformat()
    req_id_str = str(doc["_id"])

    res = comments_col.insert_one({
        "request_id": req_id_str,
        "user_id": str(current_user["id"]),
        "message": comment_in.message,
        "is_internal": is_internal,
        "created_at": now
    })

    requests_col.update_one({"_id": doc["_id"]}, {"$set": {"updated_at": now}})

    # Notifications
    if not is_internal:
        if str(current_user["id"]) == str(doc["user_id"]):
            target_user = doc.get("assigned_to")
            if target_user:
                notifications_col.insert_one({
                    "user_id": str(target_user),
                    "request_id": req_id_str,
                    "title": "New Employee Comment",
                    "message": f"{current_user['full_name']} posted a message on {doc['request_number']}.",
                    "is_read": False,
                    "created_at": now
                })
        else:
            notifications_col.insert_one({
                "user_id": str(doc["user_id"]),
                "request_id": req_id_str,
                "title": "New HR Message",
                "message": f"{current_user['full_name']} replied on your request {doc['request_number']}.",
                "is_read": False,
                "created_at": now
            })

    return {
        "id": str(res.inserted_id),
        "request_id": req_id_str,
        "user_id": str(current_user["id"]),
        "user_name": current_user["full_name"],
        "user_role": current_user["role"],
        "message": comment_in.message,
        "is_internal": is_internal,
        "created_at": now
    }

@router.post("/{request_id}/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    request_id: str,
    file: UploadFile = File(...),
    attachment_type: str = Form("supporting"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    doc = None
    if ObjectId.is_valid(request_id):
        doc = requests_col.find_one({"_id": ObjectId(request_id)})
    if not doc:
        doc = requests_col.find_one({"id": request_id})

    if not doc or not can_access_request(current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    safe_filename = f"{uuid.uuid4().hex[:8]}_{Path(file.filename).name}"
    target_path = UPLOAD_DIR / safe_filename

    contents = await file.read()
    file_size = len(contents)
    with open(target_path, "wb") as f:
        f.write(contents)

    now = datetime.now(timezone.utc).isoformat()
    req_id_str = str(doc["_id"])

    res = attachments_col.insert_one({
        "request_id": req_id_str,
        "user_id": str(current_user["id"]),
        "filename": file.filename,
        "file_path": str(target_path),
        "file_size": file_size,
        "content_type": file.content_type or "application/octet-stream",
        "attachment_type": attachment_type,
        "created_at": now
    })

    audit_logs_col.insert_one({
        "request_id": req_id_str,
        "user_id": str(current_user["id"]),
        "action": "ATTACHMENT_UPLOADED",
        "details": f"{current_user['full_name']} uploaded file '{file.filename}' ({attachment_type})",
        "ip_address": "127.0.0.1",
        "created_at": now
    })

    return {
        "id": str(res.inserted_id),
        "request_id": req_id_str,
        "user_id": str(current_user["id"]),
        "uploader_name": current_user["full_name"],
        "filename": file.filename,
        "file_size": file_size,
        "content_type": file.content_type or "application/octet-stream",
        "attachment_type": attachment_type,
        "created_at": now
    }

@router.get("/{request_id}/attachments/{attachment_id}/download")
def download_attachment(
    request_id: str,
    attachment_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    doc = None
    if ObjectId.is_valid(request_id):
        doc = requests_col.find_one({"_id": ObjectId(request_id)})
    if not doc:
        doc = requests_col.find_one({"id": request_id})

    if not doc or not can_access_request(current_user, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    att_doc = None
    if ObjectId.is_valid(attachment_id):
        att_doc = attachments_col.find_one({"_id": ObjectId(attachment_id), "request_id": str(doc["_id"])})
    if not att_doc:
        att_doc = attachments_col.find_one({"id": attachment_id, "request_id": str(doc["_id"])})

    if not att_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    file_path = Path(att_doc["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Physical file not found on server")

    return FileResponse(
        path=file_path,
        filename=att_doc["filename"],
        media_type=att_doc["content_type"]
    )

@router.post("/{request_id}/generate-experience-letter")
def generate_experience_letter(
    request_id: str,
    current_user: Dict[str, Any] = Depends(require_roles("hr", "admin"))
):
    doc = None
    if ObjectId.is_valid(request_id):
        doc = requests_col.find_one({"_id": ObjectId(request_id)})
    if not doc:
        doc = requests_col.find_one({"id": request_id})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    if doc.get("category_id") != "experience_letter":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only generate experience certificate for Experience Letter category")

    requester = None
    if ObjectId.is_valid(doc.get("user_id", "")):
        requester = users_col.find_one({"_id": ObjectId(doc["user_id"])})
    if not requester:
        requester = users_col.find_one({"id": doc.get("user_id")})

    custom_data = doc.get("custom_data", {})
    joining_date = custom_data.get("joining_date", "March 15, 2023")
    purpose = custom_data.get("purpose", "Employment Verification & Professional Records")
    addressed_to = custom_data.get("addressed_to", "TO WHOM IT MAY CONCERN")
    today_str = datetime.now().strftime("%B %d, %Y")
    emp_name = requester.get("full_name", "Employee") if requester else "Employee"
    emp_code = requester.get("employee_id", "EMP-XXXX") if requester else "EMP-XXXX"
    emp_dept = requester.get("department", "Engineering") if requester else "Engineering"
    emp_desig = requester.get("designation", "Software Engineer") if requester else "Software Engineer"

    letter_content = f"""================================================================================
                           GLOBAL ENTERPRISE CORP
                        HUMAN RESOURCES OPERATIONS
                     100 Enterprise Blvd, Tech Park, CA
================================================================================

Date: {today_str}
Ref: EXP/HR/{doc['request_number']}

{addressed_to.upper()}

SUBJECT: CERTIFICATE OF EMPLOYMENT & SERVICE EXPERIENCE

This is to certify that {emp_name} (Employee ID: {emp_code}) 
has been a valued employee with Global Enterprise Corp since {joining_date}.

Employment Details:
- Full Name: {emp_name}
- Employee ID: {emp_code}
- Department: {emp_dept}
- Current Designation: {emp_desig}
- Status: Active & in Good Standing
- Purpose of Issuance: {purpose}

During their tenure with us, {emp_name} has consistently exhibited 
high standards of professionalism, technical proficiency, and dedication to our core organizational goals.

This certificate is issued upon the employee's request for official records.

Sincerely,

Elena Rostova
Senior HR Business Partner
People & Culture Operations
Global Enterprise Corp
[CORPORATE SEAL VERIFIED - SECURE AUDIT ID: {doc['request_number']}]
================================================================================
"""
    filename = f"Experience_Letter_{emp_code}_{doc['request_number']}.txt"
    file_path = UPLOAD_DIR / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(letter_content)

    now = datetime.now(timezone.utc).isoformat()
    req_id_str = str(doc["_id"])

    res = attachments_col.insert_one({
        "request_id": req_id_str,
        "user_id": str(current_user["id"]),
        "filename": filename,
        "file_path": str(file_path),
        "file_size": len(letter_content.encode("utf-8")),
        "content_type": "text/plain",
        "attachment_type": "generated_letter",
        "created_at": now
    })

    # Auto transition to resolved
    requests_col.update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "status": "resolved",
            "resolution_notes": "Official Experience Letter generated and attached.",
            "resolved_at": now,
            "updated_at": now
        }}
    )

    # Audit log
    audit_logs_col.insert_one({
        "request_id": req_id_str,
        "user_id": str(current_user["id"]),
        "action": "LETTER_GENERATED",
        "details": f"{current_user['full_name']} generated official Experience Letter and resolved {doc['request_number']}",
        "old_value": "in_progress",
        "new_value": "resolved",
        "ip_address": "127.0.0.1",
        "created_at": now
    })

    # Notify employee
    notifications_col.insert_one({
        "user_id": str(doc["user_id"]),
        "request_id": req_id_str,
        "title": "Experience Letter Ready!",
        "message": f"Your official Experience Letter for {doc['request_number']} is ready to download.",
        "is_read": False,
        "created_at": now
    })

    return {
        "success": True,
        "message": "Experience Letter generated successfully",
        "attachment_id": str(res.inserted_id),
        "filename": filename
    }
