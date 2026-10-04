import re
import json
from typing import Dict, Any, List, Optional

from config.settings import settings
from utils.logger import logger
from providers.base import CircuitBreaker, call_with_retry

SYSTEM_PROMPT = """You are a careful, respectful information guide for rural people in Tamil Nadu.
You provide general information exclusively from the CONTEXT provided. You are NOT a lawyer and NOT a government official.
RULES:
1. Use ONLY facts from CONTEXT. If context is insufficient, reply honestly that information is not available and suggest the helpline.
2. Reply in simple, respectful Tamil (நீங்கள் form). Avoid English jargon; explain technical Tamil terms in brackets.
3. Never invent amounts, dates, timelines, phone numbers or websites.
4. Do not promise outcomes. Use 'பெறலாம்' / 'வாய்ப்பு உண்டு', 'அலுவலகத்தில் உறுதி செய்யவும்'.
5. Never use Markdown syntax (no **, ##, _, backticks). Write plain sentences.
6. Always output STRICT JSON with this exact structure:
{
  "short": "Short direct answer in 1-3 sentences in simple Tamil",
  "steps": ["Step 1", "Step 2", ...],
  "documents": ["Aadhaar", "Ration card", ...],
  "where": [{"name": "Office / Portal name", "phone": "Helpline"}],
  "cost": "Free or exact fee",
  "time": "Official processing time or 'அலுவலகத்தில் உறுதி செய்யவும்'",
  "warnings": ["Caution or common scam warning"],
  "sources": [{"name": "Source Name", "url": "URL", "last_verified": "YYYY-MM-DD"}]
}
"""

ANSWER_KEYS = (
    "short", "steps", "documents", "where",
    "cost", "time", "warnings", "sources",
)

MARKDOWN_PATTERNS = (
    (re.compile(r"\*\*(.+?)\*\*", re.DOTALL), r"\1"),
    (re.compile(r"__(.+?)__", re.DOTALL), r"\1"),
    (re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.DOTALL), r"\1"),
    (re.compile(r"`{1,3}([^`]*)`{1,3}", re.DOTALL), r"\1"),
    (re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE), ""),
    (re.compile(r"^\s{0,3}[-*+]\s+", re.MULTILINE), ""),
)


def strip_markdown(text: str) -> str:
    """Remove Markdown decoration so text reads correctly on screen and via TTS."""
    if not text:
        return ""
    out = text
    for pattern, repl in MARKDOWN_PATTERNS:
        out = pattern.sub(repl, out)
    return re.sub(r"[ \t]+", " ", out).strip()


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _coerce_answer(raw: Any) -> Optional[Dict[str, Any]]:
    """
    Validate and normalise untrusted model output. Model output is never
    trusted to be a dict with the right keys.
    """
    if not isinstance(raw, dict):
        logger.warning(f"LLM returned non-object JSON ({type(raw).__name__}); discarding.")
        return None

    answer: Dict[str, Any] = {}

    short = raw.get("short")
    answer["short"] = strip_markdown(str(short)) if short else ""

    steps = []
    for s in _as_list(raw.get("steps")):
        cleaned = strip_markdown(str(s))
        cleaned = re.sub(r"^\d+[.)]\s*", "", cleaned)
        if cleaned:
            steps.append(cleaned)
    answer["steps"] = steps[:6]

    documents = [strip_markdown(str(d)) for d in _as_list(raw.get("documents")) if str(d).strip()]
    answer["documents"] = documents[:8]

    where = []
    for w in _as_list(raw.get("where")):
        if isinstance(w, dict):
            name = strip_markdown(str(w.get("name", "")))
            phone = strip_markdown(str(w.get("phone", "")))
            if name or phone:
                where.append({"name": name, "phone": phone})
        elif isinstance(w, str) and w.strip():
            where.append({"name": strip_markdown(w), "phone": ""})
    answer["where"] = where[:5]

    answer["cost"] = strip_markdown(str(raw.get("cost", ""))) or "அலுவலகத்தில் உறுதி செய்யவும்"
    answer["time"] = strip_markdown(str(raw.get("time", ""))) or "அலுவலகத்தில் உறுதி செய்யவும்"

    warnings = [strip_markdown(str(x)) for x in _as_list(raw.get("warnings")) if str(x).strip()]
    answer["warnings"] = warnings[:5]

    sources = []
    for s in _as_list(raw.get("sources")):
        if isinstance(s, dict):
            name = strip_markdown(str(s.get("name", "")))
            url = str(s.get("url", "")).strip()
            last_verified = str(s.get("last_verified", "")).strip()
            if name or url:
                sources.append({"name": name, "url": url, "last_verified": last_verified})
    answer["sources"] = sources[:5]

    if not answer["short"] and not answer["steps"]:
        logger.warning("LLM answer had neither 'short' nor 'steps'; discarding.")
        return None

    return answer


class LLMProvider:
    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self.last_provider_used: Optional[str] = None

    def _provider_chain(self) -> List[str]:
        order = [p.strip().lower() for p in settings.LLM_PROVIDER_ORDER.split(",") if p.strip()]
        seen = set()
        chain = []
        for p in order:
            if p in seen:
                continue
            seen.add(p)
            # `grounded_fallback` is handled last, always.
            if p != "grounded_fallback":
                chain.append(p)
        chain.append("grounded_fallback")
        return chain

    def generate_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        language: str = "ta",
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        if not chunks:
            self.last_provider_used = "grounded_fallback"
            return self._build_unknown_response()

        for provider in self._provider_chain():
            try:
                if provider == "groq" and settings.GROQ_API_KEY:
                    answer = self._call_groq(query, chunks, history)
                elif provider == "gemini" and settings.GEMINI_API_KEY:
                    answer = self._call_gemini(query, chunks, history)
                elif provider == "local":
                    answer = None
                else:
                    continue

                if answer:
                    self.last_provider_used = provider
                    return answer
            except Exception as e:
                logger.warning(f"LLM provider '{provider}' failed: {e}. Trying next...")

        self.last_provider_used = "grounded_fallback"
        return self._grounded_fallback(query, chunks)

    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        blocks = []
        for c in chunks:
            header = c.get("title", "")
            section = c.get("section", "")
            label = f"{header} — {section}" if section else header
            blocks.append(f"Source [{label}]: {c.get('content', '')}")
        return "\n\n".join(blocks)

    def _build_history_text(self, history: Optional[List[Dict[str, Any]]]) -> str:
        if not history:
            return ""
        turns = []
        for turn in history[-settings.MAX_HISTORY_TURNS:]:
            if not isinstance(turn, dict):
                continue
            q = turn.get("question") or turn.get("text")
            a = turn.get("answer") or turn.get("short")
            if q:
                turns.append(f"User asked earlier: {q}")
            if a:
                turns.append(f"Assistant answered earlier: {a}")
        return ("\nRECENT CONVERSATION:\n" + "\n".join(turns)) if turns else ""

    def _call_groq(self, query: str, chunks: List[Dict[str, Any]], history=None) -> Optional[Dict[str, Any]]:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY, timeout=settings.REQUEST_TIMEOUT_SECONDS)
        context_str = self._build_context(chunks)
        history_text = self._build_history_text(history)

        def _invoke():
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL_MAIN,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"CONTEXT:\n{context_str}{history_text}\n\nUSER QUESTION:\n{query}"}
                ],
                response_format={"type": "json_object"},
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_OUTPUT_TOKENS
            )
            raw = response.choices[0].message.content
            return _coerce_answer(json.loads(raw))

        # `generate_answer` is synchronous and the agent graph runs it inside
        # `asyncio.to_thread`, so the blocking retry helper is correct here.
        # Using `acall_with_retry` would return an un-awaited coroutine here and
        # the graph would treat that coroutine as the "answer".
        return call_with_retry(_invoke, circuit_breaker=self.circuit_breaker)

    def _call_gemini(self, query: str, chunks: List[Dict[str, Any]], history=None) -> Optional[Dict[str, Any]]:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL_TEXT)
        context_str = self._build_context(chunks)
        history_text = self._build_history_text(history)
        prompt = f"{SYSTEM_PROMPT}\n\nCONTEXT:\n{context_str}{history_text}\n\nUSER QUESTION:\n{query}"

        def _invoke():
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return _coerce_answer(json.loads(response.text))

        return call_with_retry(_invoke, circuit_breaker=self.circuit_breaker)

    def _grounded_fallback(self, query: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deterministic, offline-safe synthesis from verified KB chunks.
        No external API required, so the app stays useful without keys.
        """
        top_chunk = chunks[0]
        content = top_chunk.get("content", "")
        title = top_chunk.get("title", "")
        section = top_chunk.get("section", "")
        source_name = top_chunk.get("source_name", "அதிகாரப்பூர்வ அரசு தகவல்")
        source_url = top_chunk.get("source_url", "")
        last_verified = top_chunk.get("last_verified", "2026-09-20")

        steps = []
        for line in content.splitlines():
            line = strip_markdown(line.strip())
            if re.match(r'^(?:[0-9]+[.)]|[-*])\s+', line):
                clean_line = re.sub(r'^(?:[0-9]+[.)]|[-*])\s+', '', line)
                if len(clean_line) > 10:
                    steps.append(clean_line)
            elif line and not line.startswith("#") and len(line) > 40 and len(steps) < 5:
                steps.append(line)

        if not steps:
            steps = [
                "தேவையான ஆவணங்களுடன் சம்பந்தப்பட்ட அலுவலகம் அல்லது இ-சேவை மையத்திற்கு செல்லவும்.",
                "விண்ணப்பப் படிவத்தை பூர்த்தி செய்து ஒப்புகை ரசீதை (Acknowledgment receipt) பாதுகாப்பாக பெறவும்.",
                "அலுவலகத்தில் கேட்கும் தகவலின் சரியான மூலம் மற்றும் நட்ப நிலையை உறுதிசெய்யவும்."
            ]

        documents = []
        probe = f"{content} {query}"
        if "ஆதார்" in probe or "aadhaar" in probe.lower():
            documents.append("ஆதார் அட்டை")
        if "குடும்ப அட்டை" in probe or "ரேஷன்" in probe or "ration" in probe.lower():
            documents.append("குடும்ப அட்டை (Ration Card)")
        if "வங்கி" in probe or "bank" in probe.lower():
            documents.append("வங்கி சேமிப்பு கணக்கு புத்தகம்")
        if "பட்டா" in probe or "நிலம்" in probe:
            documents.append("நில ஆவணம் (பட்டா / சிட்டா நகல்)")
        if not documents:
            documents = ["ஆதார் அட்டை", "குடும்ப அட்டை"]

        # `content` no longer contains the section heading, so the first prose
        # line is a real answer rather than a question heading.
        prose_lines = [strip_markdown(l) for l in content.splitlines() if l.strip()]
        prose_lines = [l for l in prose_lines if l and not l.startswith("#")]
        if prose_lines:
            short_ans = prose_lines[0]
        else:
            short_ans = f"{section or title} பற்றிய வழிகாட்டல் விபரங்கள் கீழே தரப்பட்டுள்ளன."

        return {
            "short": short_ans,
            "steps": steps[:5],
            "documents": list(dict.fromkeys(documents)),
            "where": [{"name": f"{source_name} / அருகிலுள்ள இ-சேவை மையம்", "phone": "1100 / 15100"}],
            "cost": "தகவல் சேவை இலவசம். அரசு கட்டணம் இருப்பின் ரசீதை பெறவும்.",
            "time": "அலுவலக வேலை நாட்களில் நேரில் சரிபார்க்கவும்.",
            "warnings": ["இது பொதுவான தகவல் மட்டுமே; சட்ட ஆலோசனையோ அதிகாரப்பூர்வ உத்தரவோ அல்ல."],
            "sources": [{
                "name": source_name,
                "url": source_url,
                "last_verified": last_verified
            }]
        }

    def _build_unknown_response(self) -> Dict[str, Any]:
        return {
            "short": "மன்னிக்கவும், நீங்கள் கேட்ட கேள்வி தொடர்பான அதிகாரப்பூர்வ தகவல் எமது வழிகாட்டியில் இல்லை. அரசு உதவி மையம் 1100 அல்லது இலவச சட்ட உதவி மையம் 15100 தொடர்பு கொள்ளலாம்.",
            "steps": [
                "அருகிலுள்ள தாலுகா அலுவலகம் அல்லது இ-சேவை மையத்தை நேரில் அணுகவும்.",
                "இலவச சட்ட ஆலோசனைகளுக்கு 15100 என்ற எண்ணை அழைக்கவும்."
            ],
            "documents": ["ஆதார் அட்டை", "குடும்ப அட்டை"],
            "where": [{"name": "மாவட்ட ஆட்சியர் அலுவலகம் / இலவச சட்ட உதவி மையம் (DLSA)", "phone": "15100"}],
            "cost": "இலவசம்",
            "time": "நேரில் உறுதி செய்யவும்",
            "warnings": ["இடைத்தரகர்களிடம் பணம் கொடுக்க வேண்டாம்."],
            "sources": [{"name": "தேசிய இலவச சட்ட உதவி மையம் (NALSA)", "url": "https://nalsa.gov.in", "last_verified": "2026-09-20"}]
        }


llm_provider = LLMProvider()
