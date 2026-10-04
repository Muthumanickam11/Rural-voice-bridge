from typing import Optional
from fastapi import Request
from fastapi.responses import JSONResponse

ERROR_CATALOG = {
    "E_MIC_DENIED": {
        "en": "Microphone permission needed to use voice.",
        "ta": "குரல் வழி சேவைக்கு மைக்ரோஃபோன் அனுமதி தேவை.",
        "retryable": False
    },
    "E_NO_SPEECH": {
        "en": "Could not detect clear speech. Please try speaking closer to the mic or type.",
        "ta": "எதுவும் தெளிவாகக் கேட்கவில்லை. மைக்கை வாய்க்கு அருகில் வைத்து பேசவும் அல்லது தட்டச்சு செய்யவும்.",
        "retryable": True
    },
    "E_NO_NET": {
        "en": "Internet unavailable. Emergency helplines are still functional.",
        "ta": "இணைய இணைப்பு இல்லை. அவசர உதவி எண்கள் வழக்கம் போல் செயல்படும்.",
        "retryable": True
    },
    "E_SLOW": {
        "en": "Server is preparing services, please wait a moment.",
        "ta": "சேவையகம் தயாராகிறது, ஒரு நிமிடம் காத்திருக்கவும்.",
        "retryable": True
    },
    "E_LIMIT": {
        "en": "Too many requests. Please try again after a few moments.",
        "ta": "அதிக கோரிக்கைகள். சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்.",
        "retryable": True
    },
    "E_INVALID": {
        "en": "Some of the details provided were not valid. Please check and try again.",
        "ta": "வழங்கப்பட்ட சில விவரங்கள் சரியல்ல. மீண்டும் உறுதிப்படுத்தி முயற்சிக்கவும்.",
        "retryable": False
    },
    "E_UNKNOWN_Q": {
        "en": "No verified government source found for this query. Call 15100 for free legal help.",
        "ta": "இதைப் பற்றி நம்பகமான அதிகாரப்பூர்வ தகவல் இல்லை. இலவச சட்ட உதவிக்கு 15100 அழைக்கவும்.",
        "retryable": False
    },
    "E_FILE_TOO_LARGE": {
        "en": "Uploaded file is too large (max 5 MB).",
        "ta": "பதிவேற்றிய கோப்பு 5MB அளவுக்கு மேல் உள்ளது.",
        "retryable": False
    },
    "E_INTERNAL": {
        "en": "An internal processing error occurred. Please try again.",
        "ta": "தொழில்நுட்ப கோளாறு ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.",
        "retryable": True
    }
}

class AppError(Exception):
    def __init__(self, code: str, status_code: int = 400, custom_message_ta: Optional[str] = None):
        self.code = code
        self.status_code = status_code
        self.custom_message_ta = custom_message_ta
        super().__init__(code)

def format_error_response(
    code: str,
    request_id: str = "",
    status_code: int = 400,
    extra: Optional[dict] = None,
) -> JSONResponse:
    info = ERROR_CATALOG.get(code, ERROR_CATALOG["E_INTERNAL"])
    body = {
        "code": code,
        "message_en": info["en"],
        "message_ta": info["ta"],
        "retryable": info["retryable"],
        "request_id": request_id
    }
    if extra:
        body.update(extra)
    return JSONResponse(status_code=status_code, content={"error": body})
