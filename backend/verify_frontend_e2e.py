"""End-to-end check through the Vite dev proxy, i.e. the same origin the browser uses."""
import json
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://localhost:3000"


def call(method, path, body=None, headers=None, raw=None, ctype=None):
    h = dict(headers or {})
    data = raw
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        h["Content-Type"] = "application/json"
    if ctype:
        h["Content-Type"] = ctype
    req = urllib.request.Request(BASE + path, method=method, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


fails = []


def check(label, cond, detail=""):
    print(f"{'ok  ' if cond else 'FAIL'} {label}" + (f"  <- {detail}" if detail else ""))
    if not cond:
        fails.append((label, detail))


print("=== health / ready ===")
s, _, b = call("GET", "/api/v1/health")
h = json.loads(b)
check("health 200", s == 200 and h["status"] == "healthy", h.get("version"))
s, _, b = call("GET", "/api/v1/ready")
rd = json.loads(b)
providers = rd.get("providers", {})
check("ready 200", s == 200 and rd.get("ok") is True, f"chunks={providers.get('rag_chunks_loaded')}")
check("ready reports chunk count", (providers.get("rag_chunks_loaded") or 0) > 0, str(providers.get("rag_chunks_loaded")))
check("ready reports fallback", providers.get("grounded_fallback") is True)

print("\n=== text query (frontend client sends X-Request-Id, X-Session-Id) ===")
s, hdrs, b = call(
    "POST", "/api/v1/text/query",
    {"text": "நில உரிமை பட்டா எப்படி பெறுகிறேன்", "language": "ta"},
    headers={"X-Request-Id": "req-e2e-1", "X-Session-Id": "sess-e2e-1"},
)
r = json.loads(b)
check("query 200", s == 200, r.get("answer", {}).get("short", "")[:60])
check("answer has short text", bool((r.get("answer") or {}).get("short")))
check("verification present", isinstance(r.get("verification"), dict) and "passed" in r["verification"], str(r.get("verification")))
check("provider_used exposed", r.get("provider_used") is not None, str(r.get("provider_used")))
check("follow_ups is list", isinstance(r.get("follow_ups"), list), f"n={len(r.get('follow_ups') or [])}")
check("session echoed", r.get("session_id") == "sess-e2e-1", str(r.get("session_id")))
check("sources_used is list", isinstance(r.get("sources_used"), list), f"n={len(r.get('sources_used') or [])}")
check("CORS vary present", "Vary" in hdrs or "vary" in {k.lower() for k in hdrs})

print("\n=== emergency via proxy ===")
s, _, b = call("POST", "/api/v1/text/query", {"text": "I am in danger please help now", "language": "en"})
r = json.loads(b)
saf = r.get("safety") or {}
check("emergency detected", saf.get("is_emergency") is True, str(saf.get("category")))
check("helplines present", bool((saf.get("response") or {}).get("helpline_numbers")))

print("\n=== feedback correlates to the answer (client echoes request_id) ===")
s, _, b = call(
    "POST", "/api/v1/feedback",
    {"request_id": "req-e2e-1", "rating": 5, "reason": "other", "comment": "useful"},
)
check("feedback 200", s == 200 and json.loads(b).get("ok") is True)

print("\n=== rights (all 7 topics) ===")
s, _, b = call("GET", "/api/v1/rights/topics")
t = json.loads(b)
topics = t.get("topics", [])
check("7 topics", len(topics) == 7, f"n={len(topics)}")
check("topics have icon/title", all(x.get("icon") and x.get("title_ta") for x in topics))
for x in topics:
    s2, _, b2 = call("GET", f"/api/v1/rights/{x['id']}")
    d = json.loads(b2)
    n = len(d.get("chunks") or [])
    check(f"topic {x['id']}", s2 == 200 and n > 0, f"chunks={n}")

print("\n=== help centers ===")
s, _, b = call("GET", "/api/v1/helpcenters/districts")
d = json.loads(b)
check("districts has key", isinstance(d.get("districts"), list), f"n={len(d.get('districts') or [])}")
if d.get("districts"):
    first = d["districts"][0]
    sid = first.get("id") if isinstance(first, dict) else first
    s2, _, b2 = call("GET", f"/api/v1/helpcenters?district={sid}")
    o = json.loads(b2)
    check("district offices", s2 == 200 and isinstance(o.get("offices"), list), f"offices={len(o.get('offices') or [])}")
    check("offices have no internal fields", all("rules" not in x for x in o.get("offices", [])))
s3, _, b3 = call("GET", "/api/v1/helpcenters?district=Atlantis")
check("unknown district 404", s3 == 404, str(s3))

print("\n=== schemes ===")
s, _, b = call("POST", "/api/v1/schemes/check", {"profile": {
    "age": 45, "gender": "female", "annual_income": 60000, "occupation": "farmer",
    "state": "Tamil Nadu", "district": "Thanjavur", "family_size": 4,
    "land_owning": True, "land_area_acres": 1.5, "bpl_card": True, "widow": False,
}})
sc = json.loads(b)
check("schemes 200", s == 200, f"eligible={len(sc.get('eligible', []))} maybe={len(sc.get('maybe_eligible', []))}")
check("no internal rules leaked", "rules" not in json.dumps(sc))

print("\n=== RTI ===")
s, _, b = call("POST", "/api/v1/rti/generate", {
    "problem": "என் பட்டா பtransfer பிரச்சனை", "department": "Revenue Department",
    "district": "Chennai", "is_bpl": True, "applicant_name": "  ",
    "ref_numbers": "REF/2024/001, aadhaar 9876 5432 1098", "applicant_address": "1, Gandhi St",
})
rti = json.loads(b)
check("rti 200", s == 200 and bool(rti.get("letter_en")), rti.get("letter_en", "")[:50])
check("rti checklist present", isinstance(rti.get("checklist"), list) and len(rti["checklist"]) > 0)
check("aadhaar redacted", "9876 5432 1098" not in json.dumps(rti), "ref scrubbed")
check("blank name defaulted", "குடிமகன்" in rti.get("letter_en", "") or "குடிமகள்" in rti.get("letter_en", ""))

print("\n=== tts ===")
s, _, b = call("POST", "/api/v1/tts", {"text": "உங்கள் உரிமை", "speed": 1.3})
t2 = json.loads(b)
check("tts 200", s == 200 and bool(t2.get("audio_b64")), f"bytes={len(t2.get('audio_b64') or '')}")
check("tts speed echoed", t2.get("speed") == 1.3, str(t2.get("speed")))

print("\n=== admin auth ===")
s, _, _ = call("GET", "/api/v1/admin/metrics")
check("no token 401", s == 401, str(s))
s, _, b = call("GET", "/api/v1/admin/metrics", headers={"X-Admin-Token": "wrong"})
check("bad token 401", s == 401, str(s))
s, _, b = call("GET", "/api/v1/admin/metrics", headers={"X-Admin-Token": "dev-admin-token-rural-voice-bridge"})
m = json.loads(b)
check("good token 200", s == 200 and "total_events" in m, list(m)[:4])
s, _, b = call("GET", "/api/v1/admin/logs?limit=5", headers={"X-Admin-Token": "dev-admin-token-rural-voice-bridge"})
lg = json.loads(b)
check("logs 200", s == 200 and isinstance(lg.get("logs"), list), f"n={len(lg.get('logs') or [])}")

print("\n=== rate limiting headers ===")
s, h3, _ = call("GET", "/api/v1/health")
lower = {k.lower() for k in h3}
check("x-ratelimit-limit", "x-ratelimit-limit" in lower, str(sorted(lower)))
check("x-ratelimit-remaining", "x-ratelimit-remaining" in lower)

print()
if fails:
    print(f"{len(fails)} FAILURES:")
    for f in fails:
        print("  ", f)
    raise SystemExit(1)
print("FRONTEND-PROXY E2E: all checks pass")
