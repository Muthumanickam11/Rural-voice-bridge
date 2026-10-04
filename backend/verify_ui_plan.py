"""Checks the built frontend against the UI numbers the plan states explicitly.

The plan names concrete values (112px mic button, 48px minimum tap target, 18px
body text, turmeric for fills only, taller Tamil line spacing). These are easy to
regress silently during a redesign, so they are pinned here.
"""

import re
import sys
import pathlib

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

FRONTEND = pathlib.Path("..") / "frontend" / "src"

fails = []


def check(label, ok, detail=""):
    if ok:
        print(f"ok   {label}")
    else:
        fails.append((label, detail))
        print(f"FAIL {label}: {detail}")


def read(name):
    return (FRONTEND / name).read_text(encoding="utf-8")


index_css = read("index.css")
app_css = read("App.css")
all_css = index_css + "\n" + app_css


def rule_body(css, selector):
    """Return the declaration block for an exact selector."""
    pat = re.compile(
        re.escape(selector) + r"\s*\{([^}]*)\}", re.M
    )
    m = pat.search(css)
    return m.group(1) if m else None


def rule_property(body, prop):
    m = re.search(rf"(?<![\w-]){re.escape(prop)}\s*:\s*([^;]+)", body or "")
    return m.group(1).strip() if m else None


print("=== plan UI numbers ===")

html_font = rule_property(rule_body(index_css, "html"), "font-size")
check(
    "body text is 18px",
    html_font == "18px",
    f"html font-size = {html_font!r}, expected '18px' (plan: 18px body text)",
)

mic = rule_body(app_css, ".mic-btn")
mic_w = rule_property(mic, "width")
mic_h = rule_property(mic, "height")
check(
    "mic button is 112px",
    mic_w == "112px" and mic_h == "112px",
    f".mic-btn {mic_w} x {mic_h}, expected 112px x 112px",
)

required_states = ["idle", "requesting", "recording", "processing", "playing", "error"]
missing = [s for s in required_states if f".mic-btn.{s}" not in app_css]
check(
    "mic button has all six states",
    not missing,
    f"missing {missing} (plan lists idle, listening, processing, playing, error, disabled)",
)
check(
    "mic button has a disabled state",
    ".mic-btn:disabled" in app_css,
    "no .mic-btn:disabled rule",
)

print()
print("=== 48px minimum tap targets ===")
INTERACTIVE = [
    (index_css, ".btn"),
    (app_css, ".sos-btn"),
    (app_css, ".nav-tab"),
    (app_css, ".quick-chip"),
    (app_css, ".followup-chip"),
    (app_css, ".icon-btn"),
    (app_css, ".where-item"),
    (app_css, ".topic-card"),
]
for css, sel in INTERACTIVE:
    body = rule_body(css, sel)
    if body is None:
        check(f"{sel} exists", False, "selector not found")
        continue
    declared = rule_property(body, "min-height")
    measured = rule_property(body, "height")
    px = None
    if declared:
        px = float(declared.rstrip("px")) if declared.endswith("px") else float(declared.rstrip("rem")) * 18
    elif measured:
        px = float(measured.rstrip("px")) if measured.endswith("px") else float(measured.rstrip("rem")) * 18
    check(
        f"{sel} tap target >= 48px",
        px is not None and px >= 48,
        f"no explicit min-height/height (declared {declared!r}, {measured!r})",
    )

print()
print("=== text legibility ===")
sizes = [
    float(v) * 18
    for css in (index_css, app_css)
    for v in re.findall(r"font-size:\s*(0\.[0-9]+)rem", css)
]
tiny = [s for s in sizes if s < 14]
check(
    "no text below 14px",
    not tiny,
    f"{len(tiny)} rules below 14px (smallest {min(tiny):.1f}px)" if tiny else "",
)

print()
print("=== colour contrast ===")


def luminance(hex_colour):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(fg, bg):
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


tokens = dict(
    re.findall(r"(--clr-[a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", index_css)
)
surfaces = [tokens.get("--clr-bg"), tokens.get("--clr-surface"),
            tokens.get("--clr-surface-2"), tokens.get("--clr-surface-3")]
text_tokens = ["--clr-text", "--clr-text-muted", "--clr-text-subtle",
               "--clr-primary", "--clr-secondary", "--clr-warning", "--clr-danger"]
for t in text_tokens:
    fg = tokens.get(t)
    if not fg:
        check(f"{t} defined", False, "token missing")
        continue
    worst = min(contrast(fg, bg) for bg in surfaces if bg)
    check(
        f"{t} {fg} >= 4.5:1 on every surface",
        worst >= 4.5,
        f"worst contrast {worst:.2f}:1",
    )

print()
print("=== turmeric rule ===")
turmeric = tokens.get("--clr-accent")
check("turmeric token defined", turmeric is not None, "--clr-accent missing")
if turmeric:
    on_white = contrast(turmeric, "#ffffff")
    check(
        "turmeric is not used as a text colour",
        not re.search(rf"color:\s*{re.escape(turmeric)}\b", all_css)
        and not re.search(r"color:\s*var\(--clr-accent\)", all_css),
        "turmeric used for text; the plan says fills only (~2:1 on white)",
    )
    print(f"     turmeric on white = {on_white:.2f}:1 (fills only, as the plan specifies)")

print()
print("=== Tamil typography ===")
headings = rule_body(index_css, "h1, h2, h3, h4")
check(
    "Tamil glyphs have a font fallback in headings",
    headings is not None and "--font-ta" in headings,
    f"heading font-family = {rule_property(headings, 'font-family')!r}; "
    "Tamil text in <h1>-<h4> would fall back to an unpredictable system font",
)
lh = rule_property(headings, "line-height")
if lh:
    val = float(lh)
    check("heading line-height suits Tamil", val >= 1.35, f"line-height {lh}")
body_lh = rule_property(rule_body(index_css, "p, li, label, span"), "line-height")
if body_lh:
    check("body line-height suits Tamil", float(body_lh) >= 1.5, f"line-height {body_lh}")

print()
if fails:
    print(f"{len(fails)} FAILURES:")
    for label, detail in fails:
        print(f"  {label}: {detail}")
    raise SystemExit(1)
print("UI PLAN CONFORMANCE: all checks pass")