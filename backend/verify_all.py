import json
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
OUT = []


def show(label, value):
    OUT.append(f"{label}: {value}")


def post(path, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, headers={"Content-Type": "application/json; charset=utf-8"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path, headers=None):
    req = urllib.request.Request(f"{BASE}{path}", headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def post_multipart(path, fields):
    boundary = "----rvbtest"
    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8")
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{BASE}{path}", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


# --- 1. Encoding + answer quality (Tamil round-trip) ---
r = post("/text/query", {"text": "பட்டா என்றால் என்ன?"})
show("1 INTENTS", r["intent"])
show("1 SHORT", r["answer"]["short"][:220])
show("1 STEP1", r["answer"]["steps"][0][:220])
show("1 VERIFIED", r["verification"]["passed"])
show("1 CHECKS", r["verification"]["checks"])
show("1 AUDIO", "present" if r["audio_b64"] else "null")
show("1 TOTAL_MS", r["timings_ms"]["total"])

# --- 2. Markdown must not leak ---
leak = any("**" in s or "##" in s for s in r["answer"]["steps"])
show("2 MARKDOWN_LEAK", leak)

# --- 3. short must not be a heading/question ---
show("3 SHORT_IS_QUESTION", r["answer"]["short"].strip().endswith("?"))

# --- 4. Emergency path with empty helplines (previously IndexError) ---
from safety.classifier import safety_classifier
original = dict(safety_classifier.emergency_responses)
for cat in list(original.keys()):
    original[cat]["helpline_numbers"] = []
try:
    e = post("/text/query", {"text": "எனக்கு உடனடி உதவி வேண்டும்"})
    show("4 EMERGENCY", e["intent"])
    show("4 EMERGENCY_PHONE", e["answer"]["where"][0]["phone"])
except Exception as exc:
    show("4 EMERGENCY", f"CRASH: {type(exc).__name__}")
finally:
    safety_classifier.emergency_responses = original

# --- 5. LLM returning non-dict JSON must not crash ---
from providers.llm_provider import llm_provider, _coerce_answer
show("5 COERCE_LIST", _coerce_answer([1, 2, 3]))
show("5 COERCE_SCALAR", _coerce_answer("hello"))
show("5 COERCE_EMPTY", _coerce_answer({}))
show("5 COERCE_OK", bool(_coerce_answer({"short": "x", "steps": ["**a**"], "sources": [{"name": "n", "url": "u"}]})))
show("5 COERCE_STRIP", _coerce_answer({"short": "**bold** `code`", "steps": ["1. **step**"], "sources": [{"name": "n", "url": "u"}]})["short"])

# --- 6. Scheme engine tri-state ---
from engine.scheme_engine import scheme_engine
partial = scheme_engine.evaluate_profile({"gender": "F", "occupation": "student"})
names = [s["scheme_id"] for s in partial["likely_eligible"]]
maybe = [s["scheme_id"] for s in partial["maybe_eligible"]]
notel = [s["scheme_id"] for s in partial["not_eligible"]]
show("6 LIKELY", names)
show("6 MAYBE", maybe)
show("6 NOT", notel)
show("6 NALA", "free_legal_aid" in names or "free_legal_aid" in maybe)
show("6 FIXLIST_LEN", len(partial["fix_list"]))

# --- 7. RTI with blank applicant_name ---
rti = post("/rti/generate", {
    "problem": "என் விண்ணப்பம் நிராகரிக்கப்பட்டது", "department": "revenue",
    "district": "madurai", "applicant_name": "", "applicant_address": ""
})
show("7 BLANK_NAME_LINE", [ln for ln in rti["letter_en"].splitlines() if ln.strip().startswith("Name:")])
show("7 BLANK_I_LINE", [ln for ln in rti["letter_en"].splitlines() if ln.strip().startswith("I,")])

# --- 8. PII redaction on RTI ---
rti2 = post("/rti/generate", {
    "problem": "என் ஆதார் 3456 7890 1234 பற்றி விசாரணை", "department": "revenue",
    "district": "madurai"
})
show("8 AADHAAR_REDACTED", "[AADHAAR]" in rti2["letter_en"])
show("8 RAW_AADHAAR_GONE", "3456 7890 1234" not in rti2["letter_en"])

# --- 9. Feedback request_id correlation ---
f = post("/feedback", {"request_id": "abc-123", "rating": 4, "reason": "wrong", "comment": "call me 9876543210"})
show("9 FEEDBACK", f["ok"])
import json as _json
with open("logs/audit.jsonl", "r", encoding="utf-8") as _f:
    _lines = [l for l in _f if l.strip()]
last = _json.loads(_lines[-1])
show("9 LAST_EVENT", last["event_type"])
show("9 LAST_REQ_ID", last["request_id"])
show("9 LAST_INTENT", last["intent"])
show("9 RATING", last["extra"].get("rating"))

# --- 10. Voice/text response shape parity ---
v = post_multipart("/voice/process", {"transcript": "எனது ஆதார் அட்டை எப்படி இழக்கினேன்?"})
show("10 VOICE_INTENT", v["intent"])
show("10 VOICE_KEYS_SAME_AS_TEXT", set(v.keys()) == set(r.keys()))
show("10 VOICE_FOLLOWUPS_INTENT_SPECIFIC", v["follow_ups"][:1])
show("10 VOICE_VERIFIED", v["verification"]["passed"])

# --- 11. Error envelope uniformity ---
import urllib.error
def err_status(path, payload=None):
    try:
        if payload is None:
            get(path)
        else:
            post(path, payload)
        return "no-error"
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8"))
        return f"{e.code} has_error_key={'error' in body} ta={'message_ta' in json.dumps(body)}"

show("11 404_RIGHTS", err_status("/rights/nonexistent"))
show("11 404_SCHEMES", err_status("/schemes/nonexistent"))
show("11 404_HELPCENTER", err_status("/helpcenters?district=atlantis"))
show("11 422_VALIDATION", err_status("/text/query", {"text": ""}))
show("11 401_ADMIN", err_status("/admin/metrics"))

# --- 12. Security headers on error paths ---
req = urllib.request.Request(f"{BASE}/rights/nonexistent")
try:
    urllib.request.urlopen(req, timeout=30)
except urllib.error.HTTPError as e:
    h = e.headers
    show("12 ERR_HDRS", {k: h.get(k) for k in ["X-Request-Id", "X-Content-Type-Options", "X-Frame-Options"]})

# --- 13. Schemes endpoint must not leak rules ---
sc = get("/schemes")
show("13 LEAKS_RULES", any("rules" in s for s in sc["schemes"]))
show("13 COUNT", sc["count"])

# --- 14. Helpcenters districts shape ---
hc = get("/helpcenters/districts")
show("14 DISTRICTS_KEYS", list(hc.keys()))

# --- 15. TTS speed honoured ---
t = post("/tts", {"text": "வணக்கம்", "speed": 1.3})
show("15 TTS_OK", t["ok"])
show("15 TTS_SPEED", t["speed"])
show("15 TTS_FORMAT", t["format"])

# --- 16. Empty/garbage queries must not 500 ---
for q in ["", "   ", "?", "!!!@@@###", "asdfghjkl", "123456"]:
    try:
        rr = post("/text/query", {"text": q})
        show(f"16 Q={q!r}", f"{rr['intent']} verified={rr['verification']['passed']}")
    except urllib.error.HTTPError as e:
        show(f"16 Q={q!r}", f"HTTP {e.code}")

# --- 17. Unknown KB file must not brick startup ---
show("17 CHUNKER_BADFILE", __import__("rag.chunker", fromlist=["x"]).chunk_markdown_file("nonexistent.md"))

# --- 18. BM25 zero-token guard ---
show("18 AVG_DL", __import__("rag.retriever", fromlist=["x"]).retriever.avg_dl)

# --- 19. Redactor covers bank account ---
from privacy.redactor import redact_pii
show("19 REDACT_ACC", redact_pii("account 123456789012"))
show("19 REDACT_PHONE", redact_pii("call 9876543210"))
show("19 REDACT_IFSC", redact_pii("ifsc SBIN0001234"))

# --- 20. Intent precedence: RTI + money keyword ---
from agents.graph import detect_intent
show("20 RTI_PRECEDENCE", detect_intent("RTI மனு பணம் கட்டணம்")[0])
show("20 ALL_INTENTS", {i: detect_intent(f"{i.lower()}")[0] for i in ["LABOR_RIGHTS", "WOMEN_RIGHTS", "CERTIFICATE_PROCESS"]})

with open("verify_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(OUT))
print("WROTE", len(OUT), "lines")
