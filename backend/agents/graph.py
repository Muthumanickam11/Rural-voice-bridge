import time
import re
import asyncio
from typing import Dict, Any, List, Optional

from agents.state import AgentState
from config.settings import settings
from safety.classifier import safety_classifier
from privacy.redactor import redact_pii
from rag.retriever import retriever
from providers.llm_provider import llm_provider
from providers.tts_provider import tts_provider
from utils.logger import logger, log_audit_event

# Order matters: more specific intents are checked first so a query that
# matches several buckets is classified as the more specific one.
# (Previously SCHEME_INFO's "பணம்" shadowed RTI_HELP queries.)
INTENT_KEYWORDS: Dict[str, List[str]] = {
    "RTI_HELP": ["rti", "தகவல் அறியும்", "பதில் வரவில்லை", "கோப்பு", "appeal", "மேல்முறையீடு", "அரசு பதில்", "information act"],
    "WOMEN_RIGHTS": ["பெண்கள்", "மனைவி", "கணவர்", "வரதட்சணை", "வழக்கு", "women", "dowry", "மகளிர்", "maiden"],
    "LABOR_RIGHTS": ["கூலி", "வேலை", "சம்பளம்", "100 நாள்", "125 நாள்", "தொழிலாளர்", "wage", "labour", "labor", "mgnrega", "ஊதியம்", "இழப்பு", "worker", "employee"],
    "CERTIFICATE_PROCESS": ["சான்றிதழ்", "சாதி", "வருமானம்", "வாரிசு", "இருப்பிடம்", "இ-சேவை", "certificate", "esevai", "ஆதார்", "aadhaar", "இழக்க", "புதிய அட்டை", "replacement", "இருப்பு சான்று"],
    "LAND_RIGHTS": ["பட்டா", "சிட்டா", "அடங்கல்", "fmb", "நிலம்", "சர்வே", "வில்லங்கம்", "ஆக்கிரமிப்பு", "கிரையம்", "land", "patta", "ec", "அடங்கல் பத்து"],
    "SCHEME_INFO": ["திட்டம்", "பணம்", "6000", "உதவித்தொகை", "pm kisan", "மகளிர் உரிமை", "காப்பீடு", "வீடு", "மின்சாரம்", "scheme", "subsidy", "அரசு உதவி", "திட்டங்கள்"],
}

# ASCII keywords must match on word boundaries. Without this, "rti" matches
# inside "certificate" and every certificate query is misrouted to RTI_HELP.
ASCII_TOKEN_REGEX = re.compile(r"^[a-z0-9 ]+$")

FOLLOW_UPS: Dict[str, List[str]] = {
    "LAND_RIGHTS": ["பட்டா மாறுதல் எப்படி?", "சிட்டா ஆன்லைனில் பார்ப்பது எப்படி?", "நில அளவீடு செய்வது எப்படி?"],
    "SCHEME_INFO": ["விண்ணப்பிக்க என்ன ஆவணங்கள் தேவை?", "எங்கு சென்று விண்ணப்பிப்பது?", "தகுதி வரம்புகள் என்ன?"],
    "RTI_HELP": ["RTI கட்டணம் எவ்வளவு?", "பதில் வரவில்லை என்றால் என்ன செய்வது?", "மாதிரி மனு பார்க்க"],
    "WOMEN_RIGHTS": ["வரதட்சணம் தடுக்க என்ன செய்வது?", "இலவச சட்ட உதவி எப்படி பெறுவது?", "அரசு பாதுகாப்பு நிறுவனம் எப்படி செயல்படுகிறது?"],
    "LABOR_RIGHTS": ["குறைந்தபட்ச கூலி எவ்வளவு?", "100 நாள் வேலைத் திட்டம் எப்படி வேண்டுகொள்வது?", "சம்பள பாக்கி பெற என்ன செய்வது?"],
    "CERTIFICATE_PROCESS": ["சாதி சான்றிதழ் எப்படி பெறுவது?", "இருப்பிடச் சான்றிதழ் எவ்வளவு நேரம்?", "இ-சேவை தளத்தை எப்படி பயன்படுத்துவது?"],
    "EMERGENCY": ["அவசர உதவி எண்கள் எவை?", "என்ன என்றால் யாரை அழைக்க வேண்டும்?", "என் பகுதியில் என்ன உதவி மையம் உள்ளது?"],
}
DEFAULT_FOLLOW_UPS = ["முக்கிய அரசு திட்டங்கள்", "இலவச சட்ட உதவி பெறுவது எப்படி?", "அருகிலுள்ள உதவி மையங்கள்"]

BANNED_PROMISE_PATTERNS = [
    r"you will definitely win",
    r"உறுதியாக வெல்வீர்கள்",
    r"உறுதி அளிக்கிறேன்",
    r"guaranteed to win",
    r"நிச்சயம் பெறலாம்",
]
DISCLAIMER_MARKERS = ("சட்ட ஆலோசனையோ", "பொதுவான தகவல்")
DISCLAIMER = "இது பொதுவான தகவல் மட்டுமே; சட்ட ஆலோசனை அல்ல. முடிவெடுக்கும் முன் அரசு அலுவலகத்தில் உறுதி செய்யவும்."


def _keyword_matches(kw: str, text_lower: str) -> bool:
    """Tamil matches on substring; Latin keywords must match on word boundaries."""
    if not kw:
        return False
    if ASCII_TOKEN_REGEX.match(kw):
        return re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text_lower) is not None
    return kw in text_lower


def detect_intent(text: str) -> tuple[str, float]:
    t_lower = text.lower() if text else ""
    for intent, kws in INTENT_KEYWORDS.items():
        for kw in kws:
            if _keyword_matches(kw, t_lower):
                return intent, 0.85
    return "GENERAL_QUERY", 0.50


def follow_ups_for(intent: str) -> List[str]:
    return FOLLOW_UPS.get(intent, DEFAULT_FOLLOW_UPS)


def _normalize_helplines(resp: Dict[str, Any]) -> List[str]:
    """Never index into a possibly-empty helpline list."""
    raw = resp.get("helpline_numbers")
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        raw = []
    numbers = [str(n).strip() for n in raw if str(n).strip()]
    return numbers or ["112"]


def verify_answer(answer: Dict[str, Any], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    checks: List[str] = []
    passed = True

    if not isinstance(answer, dict):
        return {"passed": False, "checks": ["invalid_answer_shape"]}

    # 1. Has source
    if answer.get("sources"):
        checks.append("has_source")
    else:
        checks.append("missing_source")
        passed = False

    # 2. Grounding: at least one retrieved chunk must back the answer.
    if chunks:
        checks.append("grounded_in_kb")
    else:
        checks.append("not_grounded")
        passed = False

    # 3. No banned deceptive / outcome-promising patterns
    text_repr = str(answer)
    for p in BANNED_PROMISE_PATTERNS:
        if re.search(p, text_repr, re.IGNORECASE):
            checks.append("banned_pattern")
            passed = False
            break

    # 4. Mandatory disclaimer always present
    warnings = answer.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
    if not any(any(marker in str(w) for marker in DISCLAIMER_MARKERS) for w in warnings):
        warnings.append(DISCLAIMER)
    answer["warnings"] = warnings
    checks.append("disclaimer_added")

    return {"passed": passed, "checks": checks}


class RuralVoiceBridgeGraph:
    async def execute(self, state: AgentState) -> AgentState:
        t_start = time.time()

        # Step 1: PII Redaction & Safety Gate
        t0 = time.time()
        state["user_text_clean"] = (
            redact_pii(state["user_text_raw"]) if settings.PII_REDACTION else state["user_text_raw"]
        )
        safety_eval = safety_classifier.evaluate(state["user_text_raw"])
        state["safety"] = safety_eval
        state["timings_ms"]["safety"] = round((time.time() - t0) * 1000, 2)

        # Immediate Emergency Bypass
        if safety_eval.get("is_emergency"):
            return self._handle_emergency(state, safety_eval, t_start)

        # Step 2: Intent Classification & Retrieval
        t1 = time.time()
        # Intent is detected on the RAW text: PII redaction replaces digit runs
        # with placeholders and destroys intent signal (e.g. "ஆதார் 1234 5678 9012").
        intent, conf = detect_intent(state["user_text_raw"])
        state["intent"] = intent
        state["intent_confidence"] = conf

        # BM25 is CPU-bound; keep it off the event loop.
        retrieved_chunks = await asyncio.to_thread(
            retriever.retrieve,
            state["user_text_clean"],
            settings.RERANK_TO
        )
        state["retrieved"] = retrieved_chunks
        state["timings_ms"]["retrieve"] = round((time.time() - t1) * 1000, 2)

        # Step 3: Generation (blocking provider I/O offloaded to a worker thread)
        t2 = time.time()
        try:
            answer = await asyncio.wait_for(
                asyncio.to_thread(
                    llm_provider.generate_answer,
                    state["user_text_clean"],
                    retrieved_chunks,
                    state.get("language", "ta"),
                    state.get("history")
                ),
                timeout=settings.REQUEST_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            logger.error(f"LLM generation timed out after {settings.REQUEST_TIMEOUT_SECONDS}s")
            state["errors"].append("llm_timeout")
            answer = llm_provider._grounded_fallback(state["user_text_clean"], retrieved_chunks) if retrieved_chunks \
                else llm_provider._build_unknown_response()
        except Exception as exc:
            logger.error(f"LLM generation failed: {exc}")
            state["errors"].append("llm_failed")
            answer = llm_provider._grounded_fallback(state["user_text_clean"], retrieved_chunks) if retrieved_chunks \
                else llm_provider._build_unknown_response()

        # Guarantee a usable answer shape even if every provider misbehaved.
        if not isinstance(answer, dict) or not answer:
            state["errors"].append("invalid_answer")
            answer = llm_provider._grounded_fallback(state["user_text_clean"], retrieved_chunks) if retrieved_chunks \
                else llm_provider._build_unknown_response()

        state["answer"] = answer
        # The provider tracks this on itself for the audit log; mirror it into
        # state so the shared response builder can report it to the client.
        state["provider_used"] = llm_provider.last_provider_used
        state["timings_ms"]["llm"] = round((time.time() - t2) * 1000, 2)

        # Step 4: Verification (result IS surfaced to the client)
        t3 = time.time()
        verif = verify_answer(state["answer"], retrieved_chunks)
        state["verification"] = verif
        state["timings_ms"]["verify"] = round((time.time() - t3) * 1000, 2)

        # Step 5: TTS for the spoken short answer
        t4 = time.time()
        short_text = state["answer"].get("short", "")
        audio_b64 = await tts_provider.generate_speech_base64(short_text, speed=settings.TTS_SPEED_DEFAULT)
        state["audio_base64"] = audio_b64
        state["timings_ms"]["tts"] = round((time.time() - t4) * 1000, 2)

        state["timings_ms"]["total"] = round((time.time() - t_start) * 1000, 2)

        log_audit_event(
            event_type="query_completed",
            request_id=state["request_id"],
            session_id=state["session_id"],
            intent=state["intent"],
            safety_level=state["safety"].get("level", "none"),
            provider_used=llm_provider.last_provider_used,
            latency_ms=state["timings_ms"]["total"],
            status="success" if verif["passed"] else "unverified",
            extra={"chunks_retrieved": len(retrieved_chunks), "verified": verif["passed"]}
        )

        return state

    def _handle_emergency(self, state: AgentState, safety_eval: Dict[str, Any], t_start: float) -> AgentState:
        state["intent"] = "EMERGENCY"
        state["intent_confidence"] = 1.0
        resp = safety_eval.get("response") or {}
        if not isinstance(resp, dict):
            resp = {}

        helplines = _normalize_helplines(resp)
        helpline_str = ", ".join(helplines)

        state["answer"] = {
            "short": resp.get("message_ta") or "உடனடி உதவி தேவை எனில் 112 அழையுங்கள்.",
            "steps": [
                f"அவசர உதவி எண்: {helpline_str} உடனடியாக அழையுங்கள்.",
                "உங்கள் இருப்பிடத்தை கூறி உதவி கோரவும்.",
                "தேவைப்பட்டால் அருகில் உள்ள காவல் நிலையம் அல்லது மருத்துவமனைக்கு செல்லவும்."
            ],
            "documents": [],
            "where": [{"name": resp.get("title_ta") or "அவசர உதவி மையம்", "phone": helplines[0]}],
            "cost": "முற்றிலும் இலவசம்",
            "time": "24 மணி நேர உடனடி சேவை",
            "warnings": ["உடனடி ஆபத்து அல்லது வன்முறையில் தாமதிக்காமல் அவசர எண்ணை அழைக்கவும்."],
            "sources": [{"name": "அரசு அவசர உதவி சேவை", "url": "https://112.gov.in", "last_verified": "2026-09-20"}]
        }
        state["verification"] = {"passed": True, "checks": ["emergency_bypass"]}
        state["timings_ms"]["total"] = round((time.time() - t_start) * 1000, 2)

        log_audit_event(
            event_type="emergency_triggered",
            request_id=state["request_id"],
            session_id=state["session_id"],
            intent="EMERGENCY",
            safety_level="emergency",
            latency_ms=state["timings_ms"]["total"],
            status="emergency_handled",
            extra={"helplines": helplines}
        )
        return state


agent_graph = RuralVoiceBridgeGraph()
