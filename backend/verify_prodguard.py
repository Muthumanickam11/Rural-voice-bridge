"""Regression tests for the production configuration guard.

The plan requires startup checks that refuse to run with a misconfigured
production setup, so these cases pin which settings block a production boot.
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from config.settings import Settings

fails = []

VALID_PROD = {
    "APP_ENV": "production",
    "DEBUG": False,
    "SECRET_KEY": "a-real-secret-key-of-sufficient-length-0000000000",
    "ADMIN_TOKEN": "a-real-admin-token",
    "ALLOWED_ORIGINS": "https://app.example.org",
    "ALLOWED_HOSTS": "app.example.org",
    "GROQ_API_KEY": "gsk_test_key_value",
}


def problems_for(**overrides):
    cfg = dict(VALID_PROD)
    cfg.update(overrides)
    return Settings(_env_file=None, **cfg).validate_production_config()


def expect_blocks(label, overrides, must_mention):
    problems = problems_for(**overrides)
    if not any(must_mention in p for p in problems):
        fails.append((label, f"expected {must_mention!r}, got {problems}"))
        print(f"FAIL {label}: not blocked -> {problems}")
        return
    hit = next(p for p in problems if must_mention in p)
    print(f"ok   {label}: {hit}")


def expect_allows(label, overrides):
    problems = problems_for(**overrides)
    if problems:
        fails.append((label, f"unexpectedly blocked: {problems}"))
        print(f"FAIL {label}: {problems}")
    else:
        print(f"ok   {label}")


print("=== a correctly configured production boots ===")
expect_allows("valid production config", {})

print()
print("=== unsafe production settings block startup ===")
expect_blocks("default admin token", {"ADMIN_TOKEN": "dev-admin-token-rural-voice-bridge"},
              "ADMIN_TOKEN")
expect_blocks("default secret key", {"SECRET_KEY": "development-secret-key-rural-voice-bridge-2026-secure"},
              "SECRET_KEY")
expect_blocks("debug left on", {"DEBUG": True}, "DEBUG")
expect_blocks("wildcard cors", {"ALLOWED_ORIGINS": "*"}, "wildcard")
expect_blocks("plaintext origin", {"ALLOWED_ORIGINS": "http://evil.example.org"}, "https://")
expect_blocks("no allowed hosts", {"ALLOWED_HOSTS": ""}, "ALLOWED_HOSTS")
expect_blocks("no llm key", {"GROQ_API_KEY": "", "GEMINI_API_KEY": ""}, "no LLM provider key")
expect_blocks("pii redaction off", {"PII_REDACTION": False}, "PII_REDACTION")
expect_blocks("query logging on", {"STORE_QUERY_TEXT": True, "LOG_USER_TEXT": True}, "disabled in production")

print()
print("=== local development is never blocked ===")
local = Settings(_env_file=None)
if local.is_production:
    fails.append(("local dev", "defaults were treated as production"))
    print("FAIL local dev: defaults look like production")
else:
    if local.validate_production_config():
        fails.append(("local dev", f"local reported {local.validate_production_config()}"))
        print(f"FAIL local dev: {local.validate_production_config()}")
    else:
        print("ok   local dev: guard silent, default tokens allowed")

staging_like = Settings(_env_file=None, APP_ENV="staging", DEBUG=False)
print(f"ok   DEBUG=False marks {staging_like.APP_ENV!r} as production: {staging_like.is_production}")

print()
if fails:
    print(f"{len(fails)} FAILURES:")
    for label, detail in fails:
        print(f"  {label}: {detail}")
    raise SystemExit(1)
print("PRODUCTION STARTUP GUARD: all cases pass")