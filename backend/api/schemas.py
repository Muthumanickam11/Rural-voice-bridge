from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

from config.settings import settings

DEFAULT_APPLICANT_NAME = "குடிமகன் / குடிமகள்"


class TextQueryRequest(BaseModel):
    text: str = Field(..., max_length=settings.MAX_TEXT_CHARS)
    language: str = settings.STT_LANGUAGE_DEFAULT
    history: Optional[List[Dict[str, Any]]] = None


# Canonical profile vocabulary. This is the wire contract for
# POST /api/v1/schemes/check and matches SchemesPage.jsx exactly.
# The eligibility engine compares with plain `in` / `eq`, so an unrecognised value
# silently fails every rule and would report "not eligible" for a scheme the person
# may well qualify for. Better to normalise what we can and reject the rest loudly.
SCHEME_PROFILE_VOCAB: Dict[str, set] = {
    "occupation": {
        "farmer", "tenant_farmer", "labourer", "worker",
        "student", "women_head", "senior",
    },
    "gender": {"M", "F", "Other"},
    "age_group": {"under_18", "18_to_59", "60_plus"},
    "family_income_bucket": {"below_1.2L", "1.2L_to_2.5L", "above_2.5L"},
    "ration_card": {"AAY", "PHH", "NPHH", "none"},
    "owns_land": {"yes", "no", "family_not_in_my_name"},
    "community": {"SC", "ST", "Other", "none"},
    "special_status": {"all_eligible_categories", "none"},
}

SCHEME_PROFILE_BOOL_FIELDS = {
    "family_taxpayer_or_govt",
    "is_bpl",
    "is_widow",
    "is_disabled",
    "is_senior_citizen",
    "has_ration_card",
}

# Values a voice pipeline or third-party client may plausibly send.
PROFILE_ALIASES = {
    "occupation": {
        "farmer": "farmer", "விவசாயி": "farmer",
        "tenant_farmer": "tenant_farmer", "tenant": "tenant_farmer",
        "குத்தகை": "tenant_farmer", "குத்தகை விவசாயி": "tenant_farmer",
        "labourer": "labourer", "laborer": "labourer", "labour": "labourer",
        "கூலி": "labourer", "agricultural_labourer": "labourer",
        "worker": "worker", "தொழிலாளி": "worker",
        "student": "student", "மாணவர்": "student",
        "women_head": "women_head", "head_of_family": "women_head",
        "senior": "senior", "senior_citizen": "senior", "முதியோர்": "senior",
    },
    "gender": {
        "m": "M", "male": "M", "ஆண்": "M", "புரன்": "M",
        "f": "F", "female": "F", "woman": "F", "பெண்": "F", "மகள்": "F",
        "other": "Other", "transgender": "Other", "tg": "Other",
        "திருநங்கை": "Other", "மற்றவர்": "Other",
    },
    "age_group": {
        "under_18": "under_18", "below_18": "under_18", "minor": "under_18",
        "18_to_59": "18_to_59", "18-59": "18_to_59", "adult": "18_to_59",
        "60_plus": "60_plus", "60+": "60_plus", "senior_citizen": "60_plus",
        "60_and_above": "60_plus",
    },
    "family_income_bucket": {
        "below_1.2l": "below_1.2L", "below_1_2l": "below_1.2L",
        "1.2l_to_2.5l": "1.2L_to_2.5L", "1_2l_to_2_5l": "1.2L_to_2.5L",
        "above_2.5l": "above_2.5L", "above_2_5l": "above_2.5L",
        "2.5l_plus": "above_2.5L",
    },
    "ration_card": {
        "aay": "AAY", "ஆரஞ்சு": "AAY", "அந்தியோதய": "AAY",
        "phh": "PHH", "முன்னுரிமை": "PHH",
        "nphh": "NPHH", "not_phh": "NPHH", "non_phh": "NPHH",
        "none": "none", "no": "none", "nil": "none",
    },
    "owns_land": {
        "yes": "yes", "true": "yes", "ஆம்": "yes",
        "no": "no", "false": "no", "இல்லை": "no", "nil": "no",
        "family_not_in_my_name": "family_not_in_my_name",
        "family": "family_not_in_my_name",
    },
    "community": {
        "sc": "SC", "st": "ST", "other": "Other", "none": "none",
        "oc": "Other", "bc": "Other", "மற்றவர்": "Other",
    },
    "special_status": {
        "all_eligible_categories": "all_eligible_categories",
        "any": "all_eligible_categories",
        "none": "none",
    },
}

_TRUE_STRINGS = {"true", "yes", "1", "y", "ஆம்"}
_FALSE_STRINGS = {"false", "no", "0", "n", "இல்லை"}


def _coerce_bool(value: Any) -> Any:
    """Convert a boolean-ish string to a real bool; leave everything else alone."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in _TRUE_STRINGS:
            return True
        if v in _FALSE_STRINGS:
            return False
    return value


class SchemeCheckRequest(BaseModel):
    profile: Dict[str, Any]

    @field_validator("profile", mode="before")
    @classmethod
    def _normalise_profile(cls, v: Any) -> Any:
        if not isinstance(v, dict):
            raise ValueError("profile must be an object")

        clean: Dict[str, Any] = {}
        problems: List[str] = []

        for raw_key, raw_val in v.items():
            key = str(raw_key).strip()

            # Drop unanswered controls outright: the engine already treats "" as
            # unknown for tri-state fields, and an empty enum value can never match.
            if raw_val is None or (isinstance(raw_val, str) and not raw_val.strip()):
                continue

            if key in SCHEME_PROFILE_BOOL_FIELDS:
                coerced = _coerce_bool(raw_val)
                if not isinstance(coerced, bool):
                    problems.append(f"{key} must be true or false")
                else:
                    clean[key] = coerced
                continue

            vocab = SCHEME_PROFILE_VOCAB.get(key)
            if vocab is None:
                # Unknown field: keep it, the engine ignores unknown fields anyway.
                clean[key] = raw_val
                continue

            if not isinstance(raw_val, str):
                clean[key] = raw_val
                continue

            token = raw_val.strip()
            lowered = token.lower()
            canonical = PROFILE_ALIASES.get(key, {}).get(lowered)
            if canonical is None and token in vocab:
                canonical = token
            if canonical is None:
                problems.append(
                    f"{key} '{token}' is not recognised; expected one of {sorted(vocab)}"
                )
                continue
            clean[key] = canonical

        if problems:
            raise ValueError("; ".join(problems))
        return clean


class RtiGenerateRequest(BaseModel):
    problem: str = Field(..., min_length=1, max_length=2000)
    department: str = Field(..., min_length=1, max_length=200)
    district: str = Field(..., min_length=1, max_length=100)
    applicant_name: Optional[str] = DEFAULT_APPLICANT_NAME
    applicant_address: Optional[str] = ""
    is_bpl: bool = False
    ref_numbers: Optional[str] = ""

    @field_validator("applicant_name", mode="before")
    @classmethod
    def _blank_name_to_default(cls, v):
        # An empty string from a form control is not "not provided": it would
        # bypass the field default and render a blank name in the letter.
        if v is None or (isinstance(v, str) and not v.strip()):
            return DEFAULT_APPLICANT_NAME
        return v

    @field_validator("applicant_address", "ref_numbers", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v


class FeedbackRequest(BaseModel):
    request_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    reason: Optional[str] = None  # wrong, outdated, confusing, too_long, audio_bad, other
    comment: Optional[str] = Field(default=None, max_length=1000)

class HealthResponse(BaseModel):
    status: str
    version: str
    kb_version: str
    time: str

class ReadyResponse(BaseModel):
    ok: bool
    providers: Dict[str, Any]
