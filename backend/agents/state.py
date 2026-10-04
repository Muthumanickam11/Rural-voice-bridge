from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict, total=False):
    session_id: str
    request_id: str
    channel: str  # voice, text, scheme, rti
    user_text_raw: str
    user_text_clean: str
    language: str
    history: List[Dict[str, Any]]
    safety: Dict[str, Any]
    intent: str
    intent_confidence: float
    retrieved: List[Dict[str, Any]]
    answer: Optional[Dict[str, Any]]
    provider_used: Optional[str]
    verification: Dict[str, Any]
    audio_base64: Optional[str]
    timings_ms: Dict[str, float]
    errors: List[str]
