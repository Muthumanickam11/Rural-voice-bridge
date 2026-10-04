import os
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException

from config.settings import settings
from utils.logger import logger

router = APIRouter()

PUBLIC_OFFICE_FIELDS = ("type", "name_en", "name_ta", "address", "phone", "timing", "services")


def load_json_file(rel_path: str) -> List[Dict[str, Any]]:
    full_path = os.path.join(settings.KB_PATH, rel_path)
    if not os.path.exists(full_path):
        logger.warning(f"Knowledge base file not found: {full_path}")
        return []
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError) as exc:
        logger.error(f"Failed to load {full_path}: {exc}")
        return []


def _districts() -> List[Dict[str, Any]]:
    return load_json_file(os.path.join("helpcenters", "districts.json"))


def _public_office(office: Dict[str, Any]) -> Dict[str, Any]:
    return {k: office.get(k) for k in PUBLIC_OFFICE_FIELDS if k in office}


def _public_district(d: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": d.get("id"),
        "name_en": d.get("name_en"),
        "name_ta": d.get("name_ta")
    }


@router.get("/districts")
def list_districts():
    # Object envelope, consistent with every other endpoint in the API.
    return {"districts": [_public_district(d) for d in _districts()]}


@router.get("")
def get_help_centers(district: Optional[str] = None, office_type: Optional[str] = None):
    districts = _districts()
    if not districts:
        raise HTTPException(status_code=503, detail="Help center data is unavailable")

    if district:
        dist_data = next((d for d in districts if str(d.get("id", "")).lower() == district.lower()), None)
        if not dist_data:
            raise HTTPException(status_code=404, detail="District not found")
    else:
        dist_data = districts[0]

    offices = [_public_office(o) for o in dist_data.get("offices", []) if isinstance(o, dict)]
    if office_type and office_type != "all":
        offices = [o for o in offices if o.get("type") == office_type]

    return {
        "district": _public_district(dist_data),
        "offices": offices,
        "count": len(offices)
    }


@router.get("/helplines")
def get_emergency_helplines():
    return {"helplines": load_json_file(os.path.join("helpcenters", "helplines.json"))}
