import os
import re
import json
import yaml
import unicodedata
from typing import Dict, Any, Optional

from config.settings import settings
from utils.logger import logger

KEYWORDS_FILE = os.path.join(settings.KB_PATH, "safety", "keywords_ta_en.yaml")
EMERGENCY_FILE = os.path.join(settings.KB_PATH, "safety", "emergency.json")

# Danger words and urgency words are matched together. Either one alone is far
# too broad ("help" or "pain" appear in ordinary civic questions), but a
# statement that carries both is a distress signal and must reach helplines.
DANGER_TERMS = (
    "in danger", "danger", "unsafe", "trapped", "attacked", "attacking", "beaten", "beating",
    "hit me", "hits me", "stabbed", "stabbing", "kidnapped", "abducted", "hostage",
    "struggling", "scared", "frightened", "terrified", "afraid", "threatening", "threatens",
    "threatened", "hurt", "bleeding", "assaulted", "chased", "followed", "abusing", "abused",
    "அபாயம்", "ஆபாய", "தாக்கப்பட்ட", "தாக்குகிறார்", "தாக்குகின்றார்", "தாக்குதல்",
    "வெளியேற முடியவில்லை", "சிக்கியுள்ள", "வன்முறை", "அடிக்கிறார்", "அடிக்கிறான்",
    "அடித்து", "நொறுக்குகிறார்", "பயம்", "அச்சம்", "நட்புயாத்தல்", "வெறுட்கப்படுகிறேன்",
    "கொல்லவேண்டும்",
)
URGENCY_TERMS = (
    "help", "urgent", "immediately", "now", "right now", "emergency", "sos", "rescue",
    "quickly", "fast",
    "உதவி", "உடனடி", "உடனே", "அவசர", "மீண்டும்", "விரைவு", "இப்போது", "இதரம்",
)

# A user in danger does not reliably also say "now"/"help" - a plea can be as
# simple as "I am in danger". These phrases are dangerous on their own, so they
# trigger a helpline without needing a co-occurring urgency word. They are
# deliberately unambiguous: "help me" is NOT here, because that also appears in
# ordinary requests such as "help me fill this form".
STRONG_DANGER_TERMS = (
    "in danger", "im in danger", "i am in danger", "life is in danger",
    "trapped", "held hostage", "hostage", "kidnapped", "kidnap", "abducted",
    "against my will", "not free to leave", "detained", "held against",
    "being beaten", "beaten up", "attacked me", "he is beating", "she is beating",
    "stabbed", "stabs", "choking me", "strangling",
    "suicidal", "want to die", "want to die", "kill myself", "killing myself",
    "end my life", "commit suicide",
    "raped", "rape me", "molested", "sexual harassment", "stalking me", "blackmailed",
    "cannot breathe", "cant breathe", "chest pain", "heart attack", "snake bite",
    "unconscious", "not breathing", "severe bleeding", "unconscious person",
    "money debited", "unauthorized transaction", "account hacked", "otp scam", "phishing",
    "domestic violence", "child abuse", "child marriage", "pocso", "dowry harassment",
    "அபாயத்தில்", "ஆபாயத்தில்", "சிக்கியுள்ள", "வெறுட்கப்படுகிறேன்", "கொல்லவேண்டும்",
    "சாகணும்", "தற்கொலை", "விஷம் குடிக்க", "பூச்சி மருந்து",
)

# Literal keyword lists cannot express word forms: "attacking" does not contain
# "attacked", and "killing myself" does not contain "kill myself". These
# patterns are suffix-tolerant so the same phrase is caught in any tense.
DANGER_PATTERNS = (
    r"\b(attack|attacking|beat|beating|beats|hit|hits|hitting|stab|stabs|stabbing|"
    r"abduct|abducts|abducting|kidnap|kidnaps|kidnapping|threaten|threatens|"
    r"threatening|hurt|hurts|hurting|assault|assaults|assaulting)\b",
    r"\b(danger|dangerous|trapped|hostage|scared|terrified|afraid|fear)\b",
    r"\b(kill|kills|killing)\s+(me|myself|my\s?self)\b",
    r"\bhurt(ing)?\s+me\b",
    r"\b(raped|rape|rapping)\b",
    r"\b(beaten|beating|beaten up)\b",
)


def _normalize(text: str) -> str:
    """Collapse whitespace/punctuation so 'help  me, now!' still matches."""
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"[\u2018\u2019\u201c\u201d]", "'", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _contains(haystack: str, needle: str) -> bool:
    """Word-boundary aware containment for Latin text, plain substring otherwise."""
    if not needle:
        return False
    # Tamil has no reliable \b semantics, so substring matching is correct there.
    if re.search(r"[a-z]", needle):
        return re.search(rf"(?<![a-z]){re.escape(needle)}(?![a-z])", haystack) is not None
    return needle in haystack


class SafetyClassifier:
    def __init__(self):
        self.categories: Dict[str, Any] = {}
        self.emergency_responses: Dict[str, Any] = {}
        self._load_configs()

    def _load_configs(self):
        if os.path.exists(KEYWORDS_FILE):
            try:
                with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
                    self.categories = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Error loading safety keywords: {e}")
                self.categories = {}
        else:
            logger.error(f"Safety keyword file missing: {KEYWORDS_FILE}")

        if os.path.exists(EMERGENCY_FILE):
            try:
                with open(EMERGENCY_FILE, "r", encoding="utf-8") as f:
                    self.emergency_responses = json.load(f) or {}
            except Exception as e:
                logger.error(f"Error loading emergency responses: {e}")
                self.emergency_responses = {}
        else:
            logger.error(f"Emergency response file missing: {EMERGENCY_FILE}")

    def evaluate(self, text: str) -> Dict[str, Any]:
        """
        Evaluates input text against safety categories.
        Returns safety assessment dictionary.
        """
        if not text:
            return {
                "level": "none",
                "is_emergency": False,
                "category": None,
                "response": None
            }

        text_lower = _normalize(text)

        for cat_name, cat_data in (self.categories or {}).items():
            if not isinstance(cat_data, dict):
                continue

            for kw in cat_data.get("keywords_ta", []) or []:
                if kw and _normalize(str(kw)) in text_lower:
                    return self._build_emergency_result(cat_name)

            for kw in cat_data.get("keywords_en", []) or []:
                if kw and _contains(text_lower, _normalize(str(kw))):
                    return self._build_emergency_result(cat_name)

            for pat in cat_data.get("patterns", []) or []:
                try:
                    if re.search(pat, text, re.IGNORECASE):
                        return self._build_emergency_result(cat_name)
                except re.error as exc:
                    logger.warning(f"Invalid safety regex for '{cat_name}': {exc}")

        # Fallback: a distress statement that no literal phrase matched still
        # has to reach a helpline rather than fall through to a scheme answer.
        # Two routes trigger it: an unambiguous danger phrase on its own, or a
        # danger word combined with an urgency word.
        if any(_contains(text_lower, _normalize(d)) for d in STRONG_DANGER_TERMS):
            return self._build_emergency_result("immediate_danger")

        has_danger = any(_contains(text_lower, _normalize(d)) for d in DANGER_TERMS)
        if not has_danger:
            has_danger = any(re.search(p, text_lower) for p in DANGER_PATTERNS)
        has_urgency = any(_contains(text_lower, _normalize(u)) for u in URGENCY_TERMS)
        if has_danger and has_urgency:
            return self._build_emergency_result("immediate_danger")

        return {
            "level": "none",
            "is_emergency": False,
            "category": None,
            "response": None
        }

    def _build_emergency_result(self, cat_name: str) -> Dict[str, Any]:
        resp_data = self.emergency_responses.get(cat_name) or {
            "title_ta": "அவசர உதவி",
            "message_ta": "அவசர தேவைக்கு உடனடியாக 112 அல்லது 181 எண்ணை அழைக்கவும்.",
            "helpline_numbers": ["112", "181"],
            "action": "call_immediately",
            "show_sos": True
        }
        if not isinstance(resp_data, dict):
            resp_data = {}

        # Guarantee a non-empty helpline list. An empty one used to raise
        # IndexError on the highest-stakes request type in the app.
        helplines = resp_data.get("helpline_numbers")
        if isinstance(helplines, str):
            helplines = [helplines]
        if not isinstance(helplines, list) or not helplines:
            helplines = ["112"]

        resp_data = dict(resp_data)
        resp_data["helpline_numbers"] = [str(n).strip() for n in helplines if str(n).strip()] or ["112"]

        return {
            "level": "emergency",
            "is_emergency": True,
            "category": cat_name,
            "response": resp_data
        }


safety_classifier = SafetyClassifier()
