from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from api.schemas import SchemeCheckRequest
from engine.scheme_engine import scheme_engine

router = APIRouter()

# Rule internals are not part of the public contract and must not be exposed.
INTERNAL_KEYS = {"rules", "not_eligible_reasons"}


def _public(scheme: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in scheme.items() if k not in INTERNAL_KEYS}


def _public_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    evaluate_profile() returns full scheme dicts (including the raw rule
    definitions) in each eligibility bucket. Only the user-facing `reasons`
    strings are wanted over the wire, so the same internal-key filter used by
    the list endpoints is applied here too.
    """
    out = dict(result)
    for bucket in ("likely_eligible", "maybe_eligible", "not_eligible"):
        items = out.get(bucket)
        if isinstance(items, list):
            out[bucket] = [_public(i) for i in items]
    return out


@router.post("/check")
def check_scheme_eligibility(req: SchemeCheckRequest):
    return _public_result(scheme_engine.evaluate_profile(req.profile))


@router.get("")
def list_all_schemes():
    return {
        "count": len(scheme_engine.schemes),
        "schemes": [_public(s) for s in scheme_engine.schemes]
    }


@router.get("/{scheme_id}")
def get_scheme_detail(scheme_id: str):
    for s in scheme_engine.schemes:
        if s.get("scheme_id") == scheme_id:
            return _public(s)
    raise HTTPException(status_code=404, detail="Scheme not found")
