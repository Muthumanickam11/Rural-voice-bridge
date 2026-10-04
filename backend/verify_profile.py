"""Regression tests for the POST /api/v1/schemes/check profile contract.

The eligibility engine compares raw values with `in` / `eq`, so an unrecognised
value silently fails every rule and reports "not eligible" for a scheme the person
may well qualify for. These cases pin the normalisation and rejection behaviour.
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from api.schemas import SchemeCheckRequest

fails = []


def expect_accept(label, sent, want):
    try:
        got = SchemeCheckRequest(profile=sent).profile
    except Exception as exc:
        fails.append((label, f"unexpectedly rejected: {exc}"))
        print(f"FAIL {label}: rejected -> {exc}")
        return
    if got != want:
        fails.append((label, f"got {got}"))
        print(f"FAIL {label}: got {got}")
        print(f"                 want {want}")
    else:
        print(f"ok   {label}: {got}")


def expect_reject(label, sent, must_mention=None):
    try:
        got = SchemeCheckRequest(profile=sent).profile
    except Exception as exc:
        if must_mention and must_mention not in str(exc):
            fails.append((label, f"wrong reason: {exc}"))
            print(f"FAIL {label}: raised but missing {must_mention!r}")
            return
        reason = next(
            (ln.strip() for ln in str(exc).splitlines()
             if "not recognised" in ln or "must be true or false" in ln),
            str(exc).splitlines()[0],
        )
        print(f"ok   {label}: rejected -> {reason[:76]}")
        return
    fails.append((label, f"accepted as {got}"))
    print(f"FAIL {label}: accepted as {got}")


print("=== canonical values from SchemesPage pass through untouched ===")
expect_accept(
    "form submit",
    {
        "occupation": "farmer", "gender": "F", "age_group": "18_to_59",
        "family_income_bucket": "below_1.2L", "ration_card": "AAY",
        "owns_land": "yes", "family_taxpayer_or_govt": False,
    },
    {
        "occupation": "farmer", "gender": "F", "age_group": "18_to_59",
        "family_income_bucket": "below_1.2L", "ration_card": "AAY",
        "owns_land": "yes", "family_taxpayer_or_govt": False,
    },
)

print()
print("=== free-form / voice-style input is normalised ===")
expect_accept(
    "tamil + loose case",
    {
        "occupation": "விவசாயி", "gender": "female", "age_group": "60+",
        "family_income_bucket": "below_1.2l", "ration_card": "aay",
        "owns_land": "Yes",
    },
    {
        "occupation": "farmer", "gender": "F", "age_group": "60_plus",
        "family_income_bucket": "below_1.2L", "ration_card": "AAY",
        "owns_land": "yes",
    },
)
expect_accept(
    "boolean strings coerced",
    {"is_bpl": "true", "is_widow": "no", "family_taxpayer_or_govt": "1"},
    {"is_bpl": True, "is_widow": False, "family_taxpayer_or_govt": True},
)

print()
print("=== unanswered controls are dropped, not passed through ===")
expect_accept(
    "empty and null",
    {"gender": "", "occupation": None, "age_group": "18_to_59", "is_bpl": "  "},
    {"age_group": "18_to_59"},
)
expect_accept("empty profile", {}, {})

print()
print("=== genuinely unknown values are rejected loudly ===")
expect_reject("bad gender", {"gender": "zzz"}, "not recognised")
expect_reject("bad occupation", {"occupation": "astronaut"}, "not recognised")
expect_reject("bad boolean", {"is_bpl": "perhaps"}, "must be true or false")

print()
print("=== normalisation must not change eligibility outcomes ===")
from engine.scheme_engine import scheme_engine

canonical = {"occupation": "farmer", "gender": "F", "age_group": "60_plus",
             "family_income_bucket": "below_1.2L", "ration_card": "AAY",
             "owns_land": "yes", "family_taxpayer_or_govt": False}
loose = {"occupation": "விவசாயி", "gender": "female", "age_group": "60+",
         "family_income_bucket": "below_1.2l", "ration_card": "aay",
         "owns_land": "Yes", "family_taxpayer_or_govt": "no"}
a = {s["scheme_id"] for s in scheme_engine.evaluate_profile(canonical)["likely_eligible"]}
b = {s["scheme_id"] for s in scheme_engine.evaluate_profile(
    SchemeCheckRequest(profile=loose).profile)["likely_eligible"]}
if a != b:
    fails.append(("equivalence", f"{sorted(a)} != {sorted(b)}"))
    print(f"FAIL equivalence: canonical={sorted(a)} loose={sorted(b)}")
else:
    print(f"ok   canonical and loose profiles agree: {sorted(a)}")

print()
if fails:
    print(f"{len(fails)} FAILURES:")
    for label, detail in fails:
        print(f"  {label}: {detail}")
    raise SystemExit(1)
print("SCHEME PROFILE CONTRACT: all cases pass")