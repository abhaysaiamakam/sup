from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class UserRole(str, Enum):
    employee = "employee"
    hr = "hr"
    payroll = "payroll"
    it = "it"
    admin = "admin"

class RequestPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"

class RequestStatus(str, Enum):
    submitted = "submitted"
    under_review = "under_review"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"
    rejected = "rejected"
    on_hold = "on_hold"

# Auth Models
class UserRegister(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6)
    role: Optional[UserRole] = UserRole.employee
    department: Optional[str] = "General"
    designation: Optional[str] = "Employee"
    employee_id: Optional[str] = None
    phone: Optional[str] = None

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    role: str
    department: Optional[str] = None
    designation: Optional[str] = None
    employee_id: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Category Models
class CategoryResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    default_handler_role: str
    sla_hours: int
    fields_schema: List[Dict[str, Any]]

# Comment Models
class CommentCreate(BaseModel):
    message: str = Field(..., min_length=1)
    is_internal: bool = False

class CommentResponse(BaseModel):
    id: str
    request_id: str
    user_id: str
    user_name: str
    user_role: str
    message: str
    is_internal: bool
    created_at: str

# Attachment Models
class AttachmentResponse(BaseModel):
    id: str
    request_id: str
    user_id: str
    uploader_name: str
    filename: str
    file_size: int
    content_type: str
    attachment_type: str
    created_at: str

# Audit Log Models
class AuditLogResponse(BaseModel):
    id: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    action: str
    details: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: str

# Notification Models
class NotificationResponse(BaseModel):
    id: str
    user_id: str
    request_id: Optional[str] = None
    title: str
    message: str
    is_read: bool
    created_at: str

# Service Request Models
class RequestCreate(BaseModel):
    category_id: str
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    priority: RequestPriority = RequestPriority.medium
    custom_data: Optional[Dict[str, Any]] = None
    is_confidential: Optional[bool] = False

class RequestStatusUpdate(BaseModel):
    status: RequestStatus
    reason_or_notes: Optional[str] = None

class RequestAssignUpdate(BaseModel):
    assigned_to: Optional[str] = None
    assignment_note: Optional[str] = None

class RequestResponse(BaseModel):
    id: str
    request_number: str
    category_id: str
    category_name: str
    category_icon: str
    user_id: str
    requester_name: str
    requester_email: str
    requester_department: Optional[str] = None
    requester_employee_id: Optional[str] = None
    title: str
    description: str
    priority: str
    status: str
    assigned_to: Optional[str] = None
    assignee_name: Optional[str] = None
    rejection_reason: Optional[str] = None
    resolution_notes: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = None
    is_confidential: bool = False
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None
    comment_count: int = 0
    attachment_count: int = 0
    is_overdue: bool = False

class RequestDetailResponse(RequestResponse):
    comments: List[CommentResponse] = []
    attachments: List[AttachmentResponse] = []
    audit_logs: List[AuditLogResponse] = []

# Analytics Model
class DashboardAnalytics(BaseModel):
    total_requests: int
    pending_requests: int
    in_progress_requests: int
    resolved_requests: int
    closed_requests: int
    rejected_requests: int
    overdue_requests: int
    avg_resolution_hours: float
    requests_by_category: Dict[str, int]
    requests_by_priority: Dict[str, int]
    recent_activity: List[AuditLogResponse]
