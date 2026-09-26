import os
from datetime import datetime, timezone
from pathlib import Path
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
from typing import Dict, Any, Optional

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "hr_service_portal")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Collections
users_col = db["users"]
categories_col = db["categories"]
requests_col = db["service_requests"]
comments_col = db["comments"]
attachments_col = db["attachments"]
audit_logs_col = db["audit_logs"]
notifications_col = db["notifications"]

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def init_db():
    # Setup Indexes
    users_col.create_index([("email", ASCENDING)], unique=True)
    users_col.create_index([("username", ASCENDING)], unique=True)
    users_col.create_index([("employee_id", ASCENDING)], unique=True)
    
    categories_col.create_index([("id", ASCENDING)], unique=True)
    
    requests_col.create_index([("user_id", ASCENDING)])
    requests_col.create_index([("request_number", ASCENDING)], unique=True)
    requests_col.create_index([("status", ASCENDING)])
    requests_col.create_index([("category_id", ASCENDING)])
    requests_col.create_index([("assigned_to", ASCENDING)])
    requests_col.create_index([("created_at", DESCENDING)])
    
    comments_col.create_index([("request_id", ASCENDING)])
    attachments_col.create_index([("request_id", ASCENDING)])
    audit_logs_col.create_index([("request_id", ASCENDING)])
    audit_logs_col.create_index([("created_at", DESCENDING)])
    notifications_col.create_index([("user_id", ASCENDING), ("is_read", ASCENDING)])

def seed_default_data_if_needed():
    from .auth import hash_password

    if users_col.count_documents({}) > 0:
        return

    now = datetime.now(timezone.utc).isoformat()

    # 1. Seed Categories with dynamic custom field definitions
    categories = [
        {
            "id": "leave_clarification",
            "name": "Leave Clarification",
            "description": "Queries regarding leave balances, eligibility, leave policies, or rejected leave requests.",
            "icon": "calendar-days",
            "default_handler_role": "hr",
            "sla_hours": 24,
            "fields_schema": [
                {"name": "leave_type", "label": "Leave Type", "type": "select", "options": ["Annual/Paid Leave", "Sick/Medical Leave", "Casual Leave", "Maternity/Paternity", "Bereavement", "Compensatory Off", "Unpaid Leave"], "required": True},
                {"name": "query_type", "label": "Clarification Topic", "type": "select", "options": ["Balance Discrepancy", "Leave Carry-Forward", "Eligibility Policy", "Previously Rejected Leave", "Leave Encashment", "Other"], "required": True},
                {"name": "date_range", "label": "Affected Date / Period", "type": "text", "placeholder": "e.g. Oct 12 - Oct 16, 2026", "required": False}
            ]
        },
        {
            "id": "payroll_query",
            "name": "Payroll Query",
            "description": "Confidential queries regarding salary, tax deductions, payslips, bonuses, or reimbursements.",
            "icon": "banknotes",
            "default_handler_role": "payroll",
            "sla_hours": 24,
            "fields_schema": [
                {"name": "payroll_topic", "label": "Payroll Topic", "type": "select", "options": ["Salary Credit Discrepancy", "Tax/TDS Deductions", "Bonus/Incentive Payout", "Missing Payslip", "Expense Reimbursement", "Bank Account Update"], "required": True},
                {"name": "pay_period", "label": "Pay Period (Month/Year)", "type": "text", "placeholder": "e.g. September 2026", "required": True},
                {"name": "disputed_amount", "label": "Disputed Amount (if applicable)", "type": "text", "placeholder": "e.g. $450 or ₹35,000", "required": False}
            ]
        },
        {
            "id": "experience_letter",
            "name": "Experience Letter",
            "description": "Request official company service & experience certificate, relieving documents, or employment verification.",
            "icon": "award",
            "default_handler_role": "hr",
            "sla_hours": 48,
            "fields_schema": [
                {"name": "joining_date", "label": "Date of Joining", "type": "date", "required": True},
                {"name": "relieving_or_current", "label": "Current Employment Status", "type": "select", "options": ["Currently Working (Service Certificate)", "Resigned / Relieving in Notice Period", "Ex-Employee"], "required": True},
                {"name": "purpose", "label": "Intended Purpose", "type": "select", "options": ["Visa / Immigration Application", "Higher Studies / University Admission", "Bank Loan / Financial Verification", "New Job Transition", "Personal Record"], "required": True},
                {"name": "addressed_to", "label": "Addressed To (Optional)", "type": "text", "placeholder": "e.g. To Whom It May Concern / Embassy of Canada", "required": False}
            ]
        },
        {
            "id": "asset_request",
            "name": "Asset Request",
            "description": "Request hardware equipment, monitors, peripherals, access cards, or office setup supplies.",
            "icon": "laptop",
            "default_handler_role": "it",
            "sla_hours": 48,
            "fields_schema": [
                {"name": "asset_type", "label": "Asset Type", "type": "select", "options": ["MacBook Pro / High-Performance Laptop", "Secondary 4K Monitor", "Ergonomic Keyboard & Mouse", "Building Access Keycard", "Noise-Cancelling Headset", "Docking Station / Adapters"], "required": True},
                {"name": "request_reason", "label": "Reason / Justification", "type": "select", "options": ["New Joiner Equipment", "Hardware Upgrade / Malfunction Replacement", "Remote Work / WFH Kit", "Lost Access Card"], "required": True},
                {"name": "delivery_location", "label": "Delivery / Handover Location", "type": "select", "options": ["Main HQ Office - IT Desk", "Branch Office", "Ship to Home Address"], "required": True}
            ]
        },
        {
            "id": "onboarding_request",
            "name": "Onboarding Request",
            "description": "New hire assistance including enterprise system credentials, company ID card, department access, and documentation.",
            "icon": "user-plus",
            "default_handler_role": "hr",
            "sla_hours": 24,
            "fields_schema": [
                {"name": "joiner_full_name", "label": "New Employee Full Name", "type": "text", "required": True},
                {"name": "joiner_employee_id", "label": "Assigned Employee ID", "type": "text", "placeholder": "e.g. EMP-2026-089", "required": True},
                {"name": "joining_date", "label": "Joining Date", "type": "date", "required": True},
                {"name": "department_assigned", "label": "Department", "type": "select", "options": ["Engineering", "Product Design", "Human Resources", "Marketing", "Finance & Accounts", "Sales & Ops"], "required": True},
                {"name": "required_items", "label": "Requirements Needed", "type": "select", "options": ["Complete New Hire Bundle (All)", "System & Email Credentials", "Company RFID Badge", "Health Insurance Enrollment", "HR Policy Briefing"], "required": True}
            ]
        }
    ]

    categories_col.insert_many(categories)

    # 2. Seed Users
    users_data = [
        {"email": "john.doe@company.com", "username": "john.doe", "full_name": "John Doe", "password_hash": hash_password("emp123"), "role": "employee", "department": "Engineering", "designation": "Senior Full-Stack Engineer", "employee_id": "EMP-1001", "phone": "+1 (555) 234-5678", "created_at": now},
        {"email": "sarah.smith@company.com", "username": "sarah.smith", "full_name": "Sarah Smith", "password_hash": hash_password("emp123"), "role": "employee", "department": "Marketing", "designation": "Product Marketing Lead", "employee_id": "EMP-1002", "phone": "+1 (555) 345-6789", "created_at": now},
        {"email": "kevin.chen@company.com", "username": "kevin.chen", "full_name": "Kevin Chen", "password_hash": hash_password("emp123"), "role": "employee", "department": "Product Design", "designation": "UI/UX Designer", "employee_id": "EMP-1003", "phone": "+1 (555) 456-7890", "created_at": now},
        {"email": "elena.hr@company.com", "username": "elena.hr", "full_name": "Elena Rostova", "password_hash": hash_password("hr123"), "role": "hr", "department": "Human Resources", "designation": "Senior HR Business Partner", "employee_id": "HR-2001", "phone": "+1 (555) 901-2345", "created_at": now},
        {"email": "david.payroll@company.com", "username": "david.payroll", "full_name": "David Miller", "password_hash": hash_password("payroll123"), "role": "payroll", "department": "Finance & Payroll", "designation": "Payroll & Benefits Lead", "employee_id": "FIN-3001", "phone": "+1 (555) 912-3456", "created_at": now},
        {"email": "alex.it@company.com", "username": "alex.it", "full_name": "Alex Rivera", "password_hash": hash_password("it123"), "role": "it", "department": "IT Operations", "designation": "Lead Systems Administrator", "employee_id": "IT-4001", "phone": "+1 (555) 923-4567", "created_at": now},
        {"email": "admin@company.com", "username": "admin", "full_name": "Marcus Vance", "password_hash": hash_password("admin123"), "role": "admin", "department": "Executive / People Ops", "designation": "VP of People & Operations", "employee_id": "ADM-0001", "phone": "+1 (555) 999-0000", "created_at": now}
    ]

    inserted_users = users_col.insert_many(users_data)
    user_ids = inserted_users.inserted_ids

    u_john = user_ids[0]
    u_sarah = user_ids[1]
    u_kevin = user_ids[2]
    u_elena = user_ids[3]
    u_david = user_ids[4]
    u_alex = user_ids[5]
    u_admin = user_ids[6]

    # 3. Seed Requests
    sample_requests = [
        {
            "request_number": "HR-2026-0001",
            "category_id": "experience_letter",
            "user_id": str(u_john),
            "title": "Official Experience & Relieving Certificate for Visa Application",
            "description": "Requesting an official experience letter mentioning my designation, tenure, and department for my upcoming Canadian PR application.",
            "priority": "high",
            "status": "in_progress",
            "assigned_to": str(u_elena),
            "rejection_reason": None,
            "resolution_notes": None,
            "custom_data": {"joining_date": "2023-03-15", "relieving_or_current": "Currently Working (Service Certificate)", "purpose": "Visa / Immigration Application", "addressed_to": "High Commission of Canada"},
            "is_confidential": False,
            "created_at": "2026-09-20T10:15:00Z",
            "updated_at": "2026-09-22T14:30:00Z",
            "resolved_at": None,
            "closed_at": None
        },
        {
            "request_number": "HR-2026-0002",
            "category_id": "payroll_query",
            "user_id": str(u_john),
            "title": "TDS Tax Deduction Discrepancy for August Payroll",
            "description": "I noticed an unexpected higher TDS deduction of $320 in my August paystub compared to previous months. Please provide breakdown calculation.",
            "priority": "medium",
            "status": "in_progress",
            "assigned_to": str(u_david),
            "rejection_reason": None,
            "resolution_notes": None,
            "custom_data": {"payroll_topic": "Tax/TDS Deductions", "pay_period": "August 2026", "disputed_amount": "$320.00"},
            "is_confidential": True,
            "created_at": "2026-09-21T11:00:00Z",
            "updated_at": "2026-09-22T16:00:00Z",
            "resolved_at": None,
            "closed_at": None
        },
        {
            "request_number": "HR-2026-0003",
            "category_id": "asset_request",
            "user_id": str(u_sarah),
            "title": "Secondary 4K Monitor for Remote Work Setup",
            "description": "Requesting an external 27-inch 4K monitor and USB-C display adapter for multi-window campaign data analysis.",
            "priority": "medium",
            "status": "resolved",
            "assigned_to": str(u_alex),
            "rejection_reason": None,
            "resolution_notes": "Approved by IT Operations. Dell UltraSharp 27-inch 4K monitor dispatched via DHL tracking #982341.",
            "custom_data": {"asset_type": "Secondary 4K Monitor", "request_reason": "Remote Work / WFH Kit", "delivery_location": "Ship to Home Address"},
            "is_confidential": False,
            "created_at": "2026-09-18T09:30:00Z",
            "updated_at": "2026-09-21T17:00:00Z",
            "resolved_at": "2026-09-21T17:00:00Z",
            "closed_at": None
        },
        {
            "request_number": "HR-2026-0004",
            "category_id": "leave_clarification",
            "user_id": str(u_sarah),
            "title": "Maternity & Parental Leave Policy Clarification",
            "description": "Would like to understand the eligibility criteria and flexible phase-in options for parental leave starting early Q1 next year.",
            "priority": "low",
            "status": "under_review",
            "assigned_to": str(u_elena),
            "rejection_reason": None,
            "resolution_notes": None,
            "custom_data": {"leave_type": "Maternity/Paternity", "query_type": "Eligibility Policy", "date_range": "Jan 2027 onwards"},
            "is_confidential": False,
            "created_at": "2026-09-24T14:20:00Z",
            "updated_at": "2026-09-24T14:20:00Z",
            "resolved_at": None,
            "closed_at": None
        },
        {
            "request_number": "HR-2026-0005",
            "category_id": "onboarding_request",
            "user_id": str(u_kevin),
            "title": "System Credentials & Office RFID Badge Setup",
            "description": "New Joiner onboarding package setup. Need GitHub Enterprise access, Figma organization seat, and main office building access badge.",
            "priority": "urgent",
            "status": "submitted",
            "assigned_to": None,
            "rejection_reason": None,
            "resolution_notes": None,
            "custom_data": {"joiner_full_name": "Kevin Chen", "joiner_employee_id": "EMP-1003", "joining_date": "2026-09-25", "department_assigned": "Product Design", "required_items": "Complete New Hire Bundle (All)"},
            "is_confidential": False,
            "created_at": "2026-09-25T08:00:00Z",
            "updated_at": "2026-09-25T08:00:00Z",
            "resolved_at": None,
            "closed_at": None
        }
    ]

    inserted_reqs = requests_col.insert_many(sample_requests)
    req_ids = inserted_reqs.inserted_ids

    r1_id = str(req_ids[0])
    r2_id = str(req_ids[1])
    r3_id = str(req_ids[2])

    # 4. Seed Comments
    sample_comments = [
        {"request_id": r1_id, "user_id": str(u_elena), "message": "Hello John, I have verified your employee profile. I am drafting your official experience letter on company letterhead now.", "is_internal": False, "created_at": "2026-09-22T10:00:00Z"},
        {"request_id": r1_id, "user_id": str(u_elena), "message": "INTERNAL NOTE: Verified all employment dates against HRIS record. No pending disciplinary items. Approved for standard template.", "is_internal": True, "created_at": "2026-09-22T10:05:00Z"},
        {"request_id": r1_id, "user_id": str(u_john), "message": "Thank you Elena! Please make sure the letter is signed with company seal.", "is_internal": False, "created_at": "2026-09-22T14:30:00Z"},
        {"request_id": r2_id, "user_id": str(u_david), "message": "Hi John, reviewing the tax calculation with our finance auditor. We adjusted the quarterly slab bracket. I will upload a revised tax computation sheet.", "is_internal": False, "created_at": "2026-09-22T15:00:00Z"},
        {"request_id": r2_id, "user_id": str(u_david), "message": "INTERNAL NOTE: John's investment declaration was received after the August cut-off date. September payroll will reflect the tax offset credit.", "is_internal": True, "created_at": "2026-09-22T15:05:00Z"},
        {"request_id": r3_id, "user_id": str(u_alex), "message": "Sarah, your request has been approved by IT Ops. The monitor was shipped today with tracking #982341.", "is_internal": False, "created_at": "2026-09-21T16:45:00Z"},
        {"request_id": r3_id, "user_id": str(u_sarah), "message": "Received the monitor in great condition. Thank you so much Alex!", "is_internal": False, "created_at": "2026-09-22T09:00:00Z"}
    ]

    comments_col.insert_many(sample_comments)

    # 5. Seed Audit Logs
    sample_audits = [
        {"request_id": r1_id, "user_id": str(u_john), "action": "REQUEST_CREATED", "details": "John Doe submitted Experience Letter request HR-2026-0001", "old_value": None, "new_value": "submitted", "ip_address": "127.0.0.1", "created_at": "2026-09-20T10:15:00Z"},
        {"request_id": r1_id, "user_id": str(u_elena), "action": "STATUS_CHANGE", "details": "Elena Rostova changed status to In Progress and assigned to self", "old_value": "submitted", "new_value": "in_progress", "ip_address": "127.0.0.1", "created_at": "2026-09-22T09:30:00Z"},
        {"request_id": r2_id, "user_id": str(u_john), "action": "REQUEST_CREATED", "details": "John Doe submitted Confidential Payroll Query HR-2026-0002", "old_value": None, "new_value": "submitted", "ip_address": "127.0.0.1", "created_at": "2026-09-21T11:00:00Z"},
        {"request_id": r2_id, "user_id": str(u_david), "action": "ASSIGNED", "details": "David Miller assigned request to self", "old_value": None, "new_value": "david.payroll", "ip_address": "127.0.0.1", "created_at": "2026-09-22T14:00:00Z"},
        {"request_id": r3_id, "user_id": str(u_sarah), "action": "REQUEST_CREATED", "details": "Sarah Smith submitted Asset Request HR-2026-0003", "old_value": None, "new_value": "submitted", "ip_address": "127.0.0.1", "created_at": "2026-09-18T09:30:00Z"},
        {"request_id": r3_id, "user_id": str(u_alex), "action": "STATUS_CHANGE", "details": "Alex Rivera marked request as Resolved with courier info", "old_value": "in_progress", "new_value": "resolved", "ip_address": "127.0.0.1", "created_at": "2026-09-21T17:00:00Z"}
    ]

    audit_logs_col.insert_many(sample_audits)

    # 6. Seed Notifications
    sample_notifications = [
        {"user_id": str(u_john), "request_id": r1_id, "title": "Request In Progress", "message": "Your Experience Letter request HR-2026-0001 is now being processed by Elena Rostova.", "is_read": False, "created_at": "2026-09-22T09:30:00Z"},
        {"user_id": str(u_john), "request_id": r2_id, "title": "Payroll Query Update", "message": "David Miller left a response on your payroll inquiry HR-2026-0002.", "is_read": False, "created_at": "2026-09-22T15:00:00Z"},
        {"user_id": str(u_sarah), "request_id": r3_id, "title": "Asset Delivered", "message": "Your Dell 4K Monitor request HR-2026-0003 has been resolved.", "is_read": True, "created_at": "2026-09-21T17:00:00Z"},
        {"user_id": str(u_elena), "request_id": str(req_ids[4]), "title": "New Onboarding Request", "message": "A new onboarding request HR-2026-0005 requires HR processing.", "is_read": False, "created_at": "2026-09-25T08:00:00Z"}
    ]

    notifications_col.insert_many(sample_notifications)
