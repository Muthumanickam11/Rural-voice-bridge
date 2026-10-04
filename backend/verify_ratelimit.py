"""Confirms health/docs are exempt from the per-IP rate limit, while the API is not."""
import json
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8000"


def get(path):
    req = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers)


fails = []
LIMIT = 60

print(f"--- {LIMIT + 5} calls to /api/v1/health (must all be 200) ---")
codes = [get("/api/v1/health")[0] for _ in range(LIMIT + 5)]
ok = all(c == 200 for c in codes)
if not ok:
    fails.append(("health got throttled", sorted(set(codes))))
print(f"{'ok  ' if ok else 'FAIL'} health codes={sorted(set(codes))} n={len(codes)}")

print(f"--- {LIMIT + 5} calls to /api/v1/ready (must all be 200) ---")
codes = [get("/api/v1/ready")[0] for _ in range(LIMIT + 5)]
ok = all(c == 200 for c in codes)
if not ok:
    fails.append(("ready got throttled", sorted(set(codes))))
print(f"{'ok  ' if ok else 'FAIL'} ready codes={sorted(set(codes))} n={len(codes)}")

print("--- /api/v1/health/ready compatibility alias ---")
s, _ = get("/api/v1/health/ready")
ok = s == 200
if not ok:
    fails.append(("alias missing", s))
print(f"{'ok  ' if ok else 'FAIL'} /api/v1/health/ready -> {s}")

print("--- /docs still served ---")
s, _ = get("/docs")
ok = s == 200
if not ok:
    fails.append(("/docs not served", s))
print(f"{'ok  ' if ok else 'FAIL'} /docs -> {s}")

print("--- a real API route IS still limited ---")
codes = [get("/api/v1/rights/topics")[0] for _ in range(LIMIT + 15)]
throttled = 429 in codes
ok = throttled and codes[-1] == 429
if not ok:
    fails.append(("api not rate limited", sorted(set(codes))))
print(f"{'ok  ' if ok else 'FAIL'} api codes={sorted(set(codes))} (429 seen: {throttled})")

print()
if fails:
    print(f"{len(fails)} FAILURES:")
    for f in fails:
        print("  ", f)
    raise SystemExit(1)
print("RATE LIMIT EXEMPTION: correct")
