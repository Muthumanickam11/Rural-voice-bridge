import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from engine.scheme_engine import scheme_engine

# Use the exact vocabulary SchemesPage's form collects, since that is what the
# rules in schemes_master.json are written against.
PROFILES = {
    "farmer woman, land, low income, AAY": {
        "occupation": "farmer", "gender": "F", "age_group": "18_to_59",
        "family_income_bucket": "below_1.2L", "ration_card": "AAY",
        "owns_land": "yes", "family_taxpayer_or_govt": False,
    },
    "senior citizen, widow, no income": {
        "occupation": "senior", "gender": "F", "age_group": "60_plus",
        "family_income_bucket": "below_1.2L", "ration_card": "PHH",
        "owns_land": "no", "family_taxpayer_or_govt": False,
    },
    "girl student": {
        "occupation": "student", "gender": "F", "age_group": "18_to_59",
        "family_income_bucket": "below_1.2L", "ration_card": "PHH",
        "owns_land": "no", "family_taxpayer_or_govt": False,
    },
    "boy student": {
        "occupation": "student", "gender": "M", "age_group": "18_to_59",
        "family_income_bucket": "below_1.2L", "ration_card": "PHH",
        "owns_land": "no", "family_taxpayer_or_govt": False,
    },
    "tenant farmer, no own land": {
        "occupation": "tenant_farmer", "gender": "M", "age_group": "18_to_59",
        "family_income_bucket": "1.2L_to_2.5L", "ration_card": "NPHH",
        "owns_land": "no", "family_taxpayer_or_govt": False,
    },
    "general worker, no land, no card": {
        "occupation": "worker", "gender": "M", "age_group": "18_to_59",
        "family_income_bucket": "above_2.5L", "ration_card": "none",
        "owns_land": "no", "family_taxpayer_or_govt": True,
    },
}

fails = []
EXPECTED = {
    "farmer woman, land, low income, AAY": {"pm_kisan", "cmchis", "free_legal_aid", "free_electricity"},
    "senior citizen, widow, no income": {"old_age_pension"},
    "girl student": {"pudhumai_penn"},
    "boy student": {"tamil_pudhalvan"},
    "tenant farmer, no own land": {"uzhavar_padhukappu"},
    "general worker, no land, no card": set(),
}

for label, profile in PROFILES.items():
    r = scheme_engine.evaluate_profile(profile)
    likely = {s["scheme_id"] for s in r["likely_eligible"]}
    maybe = {s["scheme_id"] for s in r["maybe_eligible"]}
    notel = {s["scheme_id"] for s in r["not_eligible"]}
    print(f"=== {label} ===")
    print(f"  likely({len(likely)}): {sorted(likely)}")
    print(f"  maybe ({len(maybe)}): {sorted(maybe)}")
    print(f"  not   ({len(notel)}): {sorted(notel)}")
    print(f"  fix_list: {r['fix_list']}")
    want = EXPECTED[label]
    missing = want - likely
    if missing:
        fails.append((label, "missing from likely_eligible", sorted(missing)))
        print(f"  !! expected in likely: {sorted(missing)}")
    # Nothing may be in two buckets at once.
    overlap = (likely & maybe) | (likely & notel) | (maybe & notel)
    if overlap:
        fails.append((label, "bucket overlap", sorted(overlap)))
        print(f"  !! bucket overlap: {sorted(overlap)}")
    print()

print()
if fails:
    print(f"{len(fails)} FAILURES:")
    for f in fails:
        print("  ", f)
    raise SystemExit(1)
print("SCHEME ENGINE: all expected eligibility outcomes correct")
