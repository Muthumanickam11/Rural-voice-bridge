import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from safety.classifier import safety_classifier as c

MUST = [
    ("I am in danger, a woman is being beaten right now please help immediately", "immediate_danger"),
    ("my husband is beating me, i need a helpline now", "domestic_violence"),
    ("husband beats me", "domestic_violence"),
    ("he hits me every day", "domestic_violence"),
    ("I am trapped, please help", "immediate_danger"),
    ("he is threatening me with a knife, help now", "immediate_danger"),
    ("someone is attacking me, send help immediately", "immediate_danger"),
    ("I want to die", "suicide_self_harm"),
    ("I am thinking of killing myself", "suicide_self_harm"),
    ("my child is being abused", "child_abuse"),
    ("he raped my daughter", "child_abuse"),
    ("money was debited from my account, fraud", "cyber_fraud"),
    ("snake bite, need ambulance", "medical_emergency"),
    ("my father has severe chest pain, call ambulance", "medical_emergency"),
    ("she cannot breathe", "medical_emergency"),
    ("he is holding me against my will, help", "immediate_danger"),
    # Tamil (kept in a real UTF-8 file, not written through PowerShell)
    ("நான் சாகணும்", "suicide_self_harm"),
    ("கணவர் அடிக்கிறான்", "domestic_violence"),
    ("பாம்பு கடி, ஆம்புலன்ஸ் வேணும்", "medical_emergency"),
    ("வங்கி பணம் திருடு போனது", "cyber_fraud"),
    ("என்னை ஒருவர் தாக்குகிறார், உதவி வேணும்", "immediate_danger"),
]

# Spacing/punctuation/typography robustness: these MUST still detect.
ROBUST = [
    "  I am   in   danger  ",
    "I\u2019m in danger",          # curly apostrophe
    "HELP!!! I AM IN DANGER NOW",  # shouting
    "i need HELP immediately, being threatened",
]

# These are ordinary civic questions and must NOT be treated as emergencies.
MUST_NOT = [
    "how do I apply for a patta",
    "what documents are needed for caste certificate",
    "how much is the free legal aid",
    "who is my MLA",
    "tell me about PM-KISAN scheme",
    "I need help filling this form",
    "my chest is fine but how do I renew it",
    "what is the RTI process",
    "where is the taluk office",
    "how to apply for a job",
    "what is the cost of a patta transfer",
    "explain the farmer welfare scheme",
    "where can I get a caste certificate",
    "I want to apply for a scholarship",
]

fails = []

print("--- must detect ---")
for text, expected in MUST:
    r = c.evaluate(text)
    ok = r["level"] == "emergency" and r["category"] == expected
    if not ok:
        fails.append(("MISS/WRONG-CAT", text, expected, r["level"], r["category"]))
    print(f"{'ok  ' if ok else 'FAIL'} {str(r['category']):18s} <- {text[:50]}")

print("\n--- robustness (any emergency) ---")
for text in ROBUST:
    r = c.evaluate(text)
    ok = r["level"] == "emergency"
    if not ok:
        fails.append(("ROBUSTNESS", text, "emergency", r["level"], r["category"]))
    print(f"{'ok  ' if ok else 'FAIL'} {str(r['category']):18s} <- {text[:50]!r}")

print("\n--- must NOT be emergency ---")
for text in MUST_NOT:
    r = c.evaluate(text)
    bad = r["level"] == "emergency"
    if bad:
        fails.append(("FALSE-POSITIVE", text, "none", r["level"], r["category"]))
    print(f"{'FAIL' if bad else 'ok  '} {str(r['category']):18s} <- {text[:50]}")

print()
if fails:
    print(f"{len(fails)} FAILURES:")
    for f in fails:
        print("  ", f)
    raise SystemExit(1)
print("SAFETY CLASSIFIER: all cases pass")
