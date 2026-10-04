import os
import json
from typing import Dict, Any, List, Optional

from config.settings import settings
from utils.logger import logger

# Fields where "not answered" and "explicitly no" must not be conflated.
# If the user has not answered, we cannot claim the rule failed.
TRISTATE_FIELDS = {
    "family_taxpayer_or_govt",
    "special_status",
    "has_ration_card",
    "is_bpl",
    "is_widow",
    "is_disabled",
    "is_senior_citizen",
}


class SchemeEngine:
    def __init__(self, master_rules_path: Optional[str] = None):
        if not master_rules_path:
            master_rules_path = os.path.join(settings.KB_PATH, "schemes", "schemes_master.json")
        self.rules_path = master_rules_path
        self.schemes: List[Dict[str, Any]] = []
        self.load_schemes()

    def load_schemes(self):
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    self.schemes = json.load(f)
            except Exception as e:
                logger.error(f"Error loading schemes_master.json: {e}")
                self.schemes = []
        else:
            logger.warning(f"Schemas master file not found: {self.rules_path}")

    def evaluate_field(self, condition: Dict[str, Any], profile: Dict[str, Any]) -> bool:
        field = condition.get("field")
        if not field:
            return False

        present = field in profile
        val = profile.get(field)
        # Empty string / None from an unanswered form control.
        unanswered = (val is None or val == "")

        if "in" in condition:
            allowed = condition["in"]
            if unanswered and field in TRISTATE_FIELDS:
                # Unanswered. Pass only if there is a wildcard "any" that the
                # rule itself declares as unconditional.
                return "any" in allowed
            return val in allowed

        if "eq" in condition:
            target = condition["eq"]
            if unanswered and field in TRISTATE_FIELDS:
                return target is True
            return val == target

        if "neq" in condition:
            target = condition["neq"]
            if unanswered and field in TRISTATE_FIELDS:
                return False
            return val != target

        return False

    def evaluate_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        likely_eligible: List[Dict[str, Any]] = []
        maybe_eligible: List[Dict[str, Any]] = []
        not_eligible: List[Dict[str, Any]] = []
        fix_list: set = set()

        for scheme in self.schemes:
            rules = scheme.get("rules", {}) or {}
            all_conditions = rules.get("all", []) or []
            maybe_conditions = rules.get("maybe_if", []) or []
            reasons_map = scheme.get("not_eligible_reasons", {}) or {}
            prerequisites = scheme.get("prerequisites", []) or []

            failed_reasons: List[str] = []
            unknown_fields: List[str] = []
            for cond in all_conditions:
                if self.evaluate_field(cond, profile):
                    continue
                field_name = cond.get("field", "")
                val = profile.get(field_name)
                if (val is None or val == "") and field_name in TRISTATE_FIELDS:
                    # Rule not failed; the user simply has not answered yet.
                    unknown_fields.append(field_name)
                    continue
                reason = reasons_map.get(
                    field_name,
                    f"{field_name} நிபந்தனை பூர்த்தியாகவில்லை."
                )
                failed_reasons.append(reason)

            scheme_copy = dict(scheme)
            unmatched_notes = [
                c.get("note", "மேலதிக விபரம் தேவை")
                for c in maybe_conditions
                if self.evaluate_field(c, profile)
            ]

            def attach_unknown_notes(target: Dict[str, Any]) -> None:
                notes = list(unmatched_notes)
                notes.append(
                    "இந்த விவரங்களை மேலும் வழங்கினால் தகுதியை உறுதிப்படுத்த முடியும்: "
                    + ", ".join(unknown_fields)
                )
                target["maybe_notes"] = notes
                target["needs_more_info"] = list(unknown_fields)

            if not failed_reasons and not unknown_fields:
                # Every condition definitively satisfied.
                likely_eligible.append(scheme_copy)
                fix_list.update(prerequisites)
            elif not failed_reasons and unknown_fields:
                # Nothing failed, but eligibility depends on unanswered questions.
                attach_unknown_notes(scheme_copy)
                maybe_eligible.append(scheme_copy)
                fix_list.update(prerequisites)
            elif unmatched_notes or unknown_fields:
                attach_unknown_notes(scheme_copy)
                scheme_copy["reasons"] = failed_reasons
                maybe_eligible.append(scheme_copy)
                fix_list.update(prerequisites)
            else:
                scheme_copy["reasons"] = failed_reasons
                not_eligible.append(scheme_copy)

        return {
            "likely_eligible": likely_eligible,
            "maybe_eligible": maybe_eligible,
            "not_eligible": not_eligible,
            "fix_list": sorted(list(fix_list)),
            "total_evaluated": len(self.schemes)
        }


scheme_engine = SchemeEngine()
