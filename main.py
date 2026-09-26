import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId

# ----------------- MONGODB SETUP -----------------
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "hr_service_portal")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

users_col = db["users"]
categories_col = db["categories"]
requests_col = db["service_requests"]
comments_col = db["comments"]

# Helper to serialize Mongo docs safely
def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return {}
    res = dict(doc)
    
    # Preserve existing custom 'id' (e.g. category slugs) if present; otherwise use '_id'
    if "_id" in res:
        if "id" not in res or not res["id"]:
            res["id"] = str(res["_id"])
        res["_id"] = str(res["_id"])
    return res

def seed_mongo_if_empty():
    # 1. Categories
    if categories_col.count_documents({}) == 0:
        categories = [
            {
                "id": "leave_clarification",
                "name": "Leave Clarification",
                "description": "Queries regarding leave balances, eligibility, and policies.",
                "icon": "calendar",
                "fields_schema": [
                    {"name": "leave_type", "label": "Leave Type", "type": "select", "options": ["Annual Leave", "Sick Leave", "Casual Leave", "Maternity/Paternity", "Unpaid Leave"]},
                    {"name": "query_type", "label": "Topic", "type": "select", "options": ["Balance Discrepancy", "Leave Carry-Forward", "Policy Query", "Rejected Leave"]},
                    {"name": "date_range", "label": "Affected Dates", "type": "text"}
                ]
            },
            {
                "id": "payroll_query",
                "name": "Payroll Query",
                "description": "Confidential queries regarding salary, taxes, bonuses, or payslips.",
                "icon": "dollar-sign",
                "fields_schema": [
                    {"name": "payroll_topic", "label": "Topic", "type": "select", "options": ["Salary Credit", "TDS Tax Deductions", "Missing Payslip", "Bonus Payout"]},
                    {"name": "pay_period", "label": "Pay Period (Month/Year)", "type": "text"},
                    {"name": "disputed_amount", "label": "Disputed Amount (Optional)", "type": "text"}
                ]
            },
            {
                "id": "experience_letter",
                "name": "Experience Letter",
                "description": "Request official company service & experience certificate.",
                "icon": "award",
                "fields_schema": [
                    {"name": "joining_date", "label": "Date of Joining", "type": "date"},
                    {"name": "purpose", "label": "Intended Purpose", "type": "select", "options": ["Visa / Immigration", "Higher Studies", "Bank Loan", "New Job Transition"]},
                    {"name": "addressed_to", "label": "Addressed To (Optional)", "type": "text"}
                ]
            },
            {
                "id": "asset_request",
                "name": "Asset Request",
                "description": "Hardware equipment, laptops, 4K monitors, and access badges.",
                "icon": "laptop",
                "fields_schema": [
                    {"name": "asset_type", "label": "Asset Type", "type": "select", "options": ["MacBook Pro / Laptop", "Secondary 4K Monitor", "Keyboard & Mouse", "Building Access Card"]},
                    {"name": "request_reason", "label": "Reason", "type": "select", "options": ["New Joiner Equipment", "Hardware Upgrade", "Remote Work / WFH Kit"]},
                    {"name": "delivery_location", "label": "Delivery Location", "type": "select", "options": ["Main Office IT Desk", "Ship to Home Address"]}
                ]
            },
            {
                "id": "onboarding_request",
                "name": "Onboarding Request",
                "description": "New hire credentials, company RFID badge, and starter packages.",
                "icon": "user-plus",
                "fields_schema": [
                    {"name": "joiner_full_name", "label": "New Employee Full Name", "type": "text"},
                    {"name": "department_assigned", "label": "Department", "type": "select", "options": ["Engineering", "Product Design", "Human Resources", "Marketing", "Finance & Accounts"]},
                    {"name": "joining_date", "label": "Joining Date", "type": "date"}
                ]
            }
        ]
        categories_col.insert_many(categories)

    # 2. Users
    if users_col.count_documents({}) == 0:
        users = [
            {"username": "john.doe", "email": "john.doe@company.com", "password": "emp123", "full_name": "John Doe", "role": "employee", "department": "Engineering"},
            {"username": "sarah.smith", "email": "sarah.smith@company.com", "password": "emp123", "full_name": "Sarah Smith", "role": "employee", "department": "Marketing"},
            {"username": "elena.hr", "email": "elena.hr@company.com", "password": "hr123", "full_name": "Elena Rostova", "role": "hr", "department": "Human Resources"},
            {"username": "david.payroll", "email": "david.payroll@company.com", "password": "payroll123", "full_name": "David Miller", "role": "payroll", "department": "Finance & Payroll"},
            {"username": "alex.it", "email": "alex.it@company.com", "password": "it123", "full_name": "Alex Rivera", "role": "it", "department": "IT Operations"},
            {"username": "admin", "email": "admin@company.com", "password": "admin123", "full_name": "Marcus Vance", "role": "admin", "department": "Executive Ops"}
        ]
        users_col.insert_many(users)

# ----------------- FASTAPI APP -----------------
app = FastAPI(title="NexusHR — FastAPI MongoDB Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
def startup_db():
    seed_mongo_if_empty()

# ----------------- SCHEMAS -----------------
class LoginInput(BaseModel):
    username: str
    password: str

class RequestCreateInput(BaseModel):
    user_id: str
    category_id: str
    title: str
    description: str
    priority: str = "medium"
    custom_data: Optional[Dict[str, Any]] = {}

class StatusUpdateInput(BaseModel):
    status: str
    notes: Optional[str] = None

class AssignInput(BaseModel):
    assigned_to: Optional[str] = None

class CommentCreateInput(BaseModel):
    user_id: str
    user_name: str
    user_role: str
    message: str
    is_internal: bool = False

# ----------------- ROUTES -----------------
@app.post("/api/auth/login")
def login(data: LoginInput):
    user = users_col.find_one({"$or": [{"username": data.username}, {"email": data.username}], "password": data.password})
    if not user:
        user = users_col.find_one({"$or": [{"username": data.username}, {"email": data.username}]})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    user_data = serialize_doc(user)
    user_data.pop("password", None)
    user_data.pop("password_hash", None)
    return {"user": user_data, "token": f"jwt-token-{user_data['id']}"}

@app.get("/api/users")
def get_users():
    docs = users_col.find({})
    users = []
    for d in docs:
        u = serialize_doc(d)
        u.pop("password", None)
        u.pop("password_hash", None)
        users.append(u)
    return users

@app.get("/api/categories")
def get_categories():
    docs = categories_col.find({})
    res = []
    for d in docs:
        cat = serialize_doc(d)
        # Populate fields from fields_schema or fields
        cat["fields"] = cat.get("fields_schema") or cat.get("fields") or []
        res.append(cat)
    return res

@app.get("/api/requests")
def get_requests(user_id: Optional[str] = None, role: Optional[str] = None):
    query = {}
    if role == "employee" and user_id:
        query["user_id"] = user_id
    elif role == "payroll":
        query["$or"] = [{"category_id": "payroll_query"}, {"category_id": "payroll"}, {"user_id": user_id}]
    
    docs = requests_col.find(query).sort("created_at", DESCENDING)
    results = []

    user_map = {str(u["_id"]): u for u in users_col.find({})}
    for u in users_col.find({}):
        if "id" in u:
            user_map[str(u["id"])] = u
            
    cat_map = {c["id"]: c.get("name", c["id"]) for c in categories_col.find({})}
    for c in categories_col.find({}):
        cat_map[str(c["_id"])] = c.get("name", c["id"])

    for d in docs:
        item = serialize_doc(d)
        u = user_map.get(str(item.get("user_id")))
        item["requester_name"] = u.get("full_name", "Employee") if u else "Employee"
        item["requester_email"] = u.get("email", "") if u else ""
        item["requester_dept"] = u.get("department", "Corporate") if u else "Corporate"
        item["category_name"] = cat_map.get(item.get("category_id"), item.get("category_id"))
        results.append(item)
    return results

@app.get("/api/requests/{request_id}")
def get_request_detail(request_id: str, role: str = "employee"):
    query = {}
    if ObjectId.is_valid(request_id):
        query = {"$or": [{"_id": ObjectId(request_id)}, {"id": request_id}]}
    else:
        query = {"id": request_id}

    doc = requests_col.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Request not found")
    
    req_data = serialize_doc(doc)
    
    # Requester info
    requester = None
    if ObjectId.is_valid(str(req_data.get("user_id"))):
        requester = users_col.find_one({"_id": ObjectId(req_data["user_id"])})
    if not requester:
        requester = users_col.find_one({"id": req_data.get("user_id")})

    req_data["requester_name"] = requester.get("full_name", "Employee") if requester else "Employee"
    req_data["requester_email"] = requester.get("email", "") if requester else ""
    req_data["requester_dept"] = requester.get("department", "Corporate") if requester else "Corporate"

    cat = categories_col.find_one({"$or": [{"id": req_data.get("category_id")}, {"_id": ObjectId(req_data.get("category_id")) if ObjectId.is_valid(req_data.get("category_id", "")) else None}]})
    req_data["category_name"] = cat.get("name", req_data.get("category_id")) if cat else req_data.get("category_id")

    # Comments
    c_query = {"request_id": req_data["id"]}
    if role == "employee":
        c_query["is_internal"] = False
    
    comments = list(comments_col.find(c_query).sort("created_at", ASCENDING))
    req_data["comments"] = [serialize_doc(c) for c in comments]
    return req_data

@app.post("/api/requests")
def create_request(data: RequestCreateInput):
    now = datetime.now(timezone.utc).isoformat()
    req_num = f"HR-{datetime.now().year}-{ObjectId().binary.hex()[:4].upper()}"
    
    doc = {
        "request_number": req_num,
        "user_id": data.user_id,
        "category_id": data.category_id,
        "title": data.title,
        "description": data.description,
        "priority": data.priority,
        "status": "submitted",
        "assigned_to": None,
        "custom_data": data.custom_data or {},
        "created_at": now,
        "updated_at": now
    }
    
    ins = requests_col.insert_one(doc)
    return {"id": str(ins.inserted_id), "request_number": req_num, "status": "submitted"}

@app.patch("/api/requests/{request_id}/status")
def update_status(request_id: str, data: StatusUpdateInput):
    query = {"_id": ObjectId(request_id)} if ObjectId.is_valid(request_id) else {"id": request_id}
    requests_col.update_one(query, {"$set": {"status": data.status, "resolution_notes": data.notes, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Status updated successfully", "status": data.status}

@app.patch("/api/requests/{request_id}/assign")
def assign_request(request_id: str, payload: AssignInput):
    query = {"_id": ObjectId(request_id)} if ObjectId.is_valid(request_id) else {"id": request_id}
    requests_col.update_one(query, {"$set": {"assigned_to": payload.assigned_to, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Assigned successfully"}

@app.post("/api/requests/{request_id}/comments")
def add_comment(request_id: str, data: CommentCreateInput):
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "request_id": request_id,
        "user_id": data.user_id,
        "user_name": data.user_name,
        "user_role": data.user_role,
        "message": data.message,
        "is_internal": data.is_internal,
        "created_at": now
    }
    ins = comments_col.insert_one(doc)
    return {"id": str(ins.inserted_id), "created_at": now}

@app.get("/api/analytics")
def get_analytics():
    all_reqs = list(requests_col.find({}))
    total = len(all_reqs)
    
    status_counts = {}
    priority_counts = {}
    category_counts = {}

    for c in categories_col.find({}):
        category_counts[c["name"]] = 0

    cat_map = {c["id"]: c.get("name", c["id"]) for c in categories_col.find({})}

    for r in all_reqs:
        st = r.get("status", "submitted")
        status_counts[st] = status_counts.get(st, 0) + 1

        pr = r.get("priority", "medium")
        priority_counts[pr] = priority_counts.get(pr, 0) + 1

        cname = cat_map.get(r.get("category_id"), r.get("category_id"))
        category_counts[cname] = category_counts.get(cname, 0) + 1

    return {
        "total": total,
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "category_counts": category_counts
    }
