from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from ..database import categories_col
from ..models import CategoryResponse
from ..auth import get_current_user

router = APIRouter(prefix="/api/categories", tags=["Categories"])

@router.get("", response_model=List[CategoryResponse])
def get_categories(current_user: Dict[str, Any] = Depends(get_current_user)):
    cursor = categories_col.find({})
    result = []
    for r in cursor:
        result.append({
            "id": r["id"],
            "name": r["name"],
            "description": r["description"],
            "icon": r["icon"],
            "default_handler_role": r["default_handler_role"],
            "sla_hours": r.get("sla_hours", 48),
            "fields_schema": r.get("fields_schema", [])
        })
    return result
