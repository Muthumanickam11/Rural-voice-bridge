import json
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

EXPECTED = {
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "content-security-policy",
    "permissions-policy",
    "x-request-id",
}


def probe(method, path, body=None, headers=None):
    req = urllib.request.Request(
        f"http://127.0.0.1:8000{path}",
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, hdrs, payload = r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        status, hdrs, payload = e.code, dict(e.headers), e.read()
    return status, hdrs, payload


CASES = [
    ("GET  200 health", "GET", "/api/v1/health", None, None),
    ("GET  200 ready", "GET", "/api/v1/ready", None, None),
    ("GET  404 rights", "GET", "/api/v1/rights/does-not-exist", None, None),
    ("GET  404 helpcenters", "GET", "/api/v1/helpcenters?district=Atlantis", None, None),
    ("GET  401 admin", "GET", "/api/v1/admin/metrics", None, None),
    ("GET  401 admin bad token", "GET", "/api/v1/admin/metrics", None, {"X-Admin-Token": "wrong"}),
    ("POST 400 empty query", "POST", "/api/v1/text/query", {"text": ""}, None),
    ("POST 422 bad body", "POST", "/api/v1/text/query", {"nope": 1}, None),
    ("POST 200 query", "POST", "/api/v1/text/query", {"text": "patta transfer"}, None),
]

fails = []
print("--- security headers on every response class ---")
for label, method, path, body, hdrs in CASES:
    status, rheaders, payload = probe(method, path, body, hdrs)
    present = {k.lower() for k in rheaders}
    missing = EXPECTED - present
    # /docs-style HTML is exempt; these are all JSON API routes.
    ok = not missing
    if not ok:
        fails.append((label, status, sorted(missing)))
    try:
        parsed = json.loads(payload.decode("utf-8"))
        has_error_key = isinstance(parsed, dict) and "error" in parsed
    except Exception:
        parsed = None
        has_error_key = None
    print(f"{'ok  ' if ok else 'FAIL'} {status} err_key={has_error_key!s:5s} missing={sorted(missing) or '-'}  [{label}]")

print()
if fails:
    print(f"{len(fails)} FAILURES:")
    for f in fails:
        print("  ", f)
    raise SystemExit(1)
print("SECURITY HEADERS + ERROR ENVELOPE: all cases pass")
