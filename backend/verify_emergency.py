import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")


def post(path, payload, timeout=120):
    req = urllib.request.Request(
        f"http://127.0.0.1:8000{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


CASES = [
    ("english immediate danger", "I am in danger, a woman is being beaten right now please help immediately", "immediate_danger"),
    ("english domestic violence", "my husband is beating me, i need a helpline now", "domestic_violence"),
    ("english trapped", "I am trapped in my house please send help", "immediate_danger"),
    ("english suicide risk", "I want to die, I have been thinking of killing myself", "suicide_self_harm"),
    ("english medical", "my father has severe chest pain, call an ambulance", "medical_emergency"),
    ("tamil domestic violence", "கணவர் அடிக்கிறான், உதவி வேணும்", "domestic_violence"),
    ("tamil immediate danger", "என்னை ஒருவர் தாக்குகிறார், உதவி வேணும்", "immediate_danger"),
    ("tamil suicide risk", "நான் சாகணும், உதவி வேணும்", "suicide_self_harm"),
    ("tamil medical", "பாம்பு கடி, ஆம்புலன்ஸ் வேணும்", "medical_emergency"),
]

NORMAL = [
    "how do I apply for a patta transfer",
    "what documents are needed for caste certificate",
    "how much is the free legal aid",
    "who is my MLA",
    "tell me about PM-KISAN scheme",
    "I need help filling this form",
    "what is the RTI process",
    "where is the taluk office",
    "where can I get a caste certificate",
    "I want to apply for a scholarship",
]

fails = []

print("--- live emergency pipeline (/api/v1/text/query) ---")
for label, text, expect_cat in CASES:
    r = post("/api/v1/text/query", {"text": text, "language": "ta"})
    safety = r.get("safety") or {}
    resp = safety.get("response") or {}
    numbers = [str(n) for n in (resp.get("helpline_numbers") or [])]
    short = (r.get("answer") or {}).get("short", "")
    is_emerg = safety.get("is_emergency") is True
    cat_ok = safety.get("category") == expect_cat
    # The helpline number must appear in BOTH the payload and the spoken text,
    # otherwise a voice-only user never hears it.
    spoken = any(n in short for n in numbers) if numbers else False
    ok = is_emerg and cat_ok and bool(numbers) and bool(short) and spoken
    if not ok:
        fails.append((label, is_emerg, safety.get("category"), numbers, spoken, short[:60]))
    print(
        f"{'ok  ' if ok else 'FAIL'} emerg={is_emerg!s:5s} cat={str(safety.get('category')):18s} "
        f"spoken={spoken!s:5s} numbers={numbers}  [{label}]"
    )

print("\n--- live normal questions must not trip SOS ---")
for text in NORMAL:
    r = post("/api/v1/text/query", {"text": text, "language": "ta"})
    safety = r.get("safety") or {}
    is_emerg = safety.get("is_emergency") is True
    if is_emerg:
        fails.append(("FALSE-POSITIVE", text, safety.get("category")))
    print(f"{'FAIL' if is_emerg else 'ok  '} emerg={is_emerg!s:5s} <- {text[:48]}")

print()
if fails:
    print(f"{len(fails)} FAILURES:")
    for f in fails:
        print("  ", f)
    raise SystemExit(1)
print("LIVE EMERGENCY PIPELINE: all cases pass")
