import re

AADHAAR_REGEX = re.compile(r'\b[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}\b')
PHONE_REGEX = re.compile(r'(?:\+91[\s-]?)?[6-9]\d{9}\b')
PAN_REGEX = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', re.IGNORECASE)
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b')
# 9-18 digit account numbers. Runs AFTER phone redaction so that a 10-digit
# mobile number is labelled [PHONE] rather than [BANK_ACCOUNT].
BANK_ACCOUNT_REGEX = re.compile(r'\b\d{9,18}\b')
BANK_IFSC_REGEX = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b')
NAME_TA_REGEX = re.compile(r'(?:என்\s+பெயர்|பெயர்\s+)(?:[:\s]+)([^\s,.\n]+)', re.UNICODE)
NAME_EN_REGEX = re.compile(r'(?:my\s+name\s+is|name\s+is\s+)(?:[:\s]+)([A-Za-z]+)', re.IGNORECASE)


def redact_pii(text: str) -> str:
    """
    Redacts personal identifiers before storage or sending to external models:
    Aadhaar -> [AADHAAR]
    Phone -> [PHONE]
    PAN -> [PAN]
    Email -> [EMAIL]
    Bank account / IFSC -> [BANK_ACCOUNT]
    Explicit names -> [NAME]
    """
    if not text:
        return text

    # Redact Aadhaar first (12 digits)
    text = AADHAAR_REGEX.sub("[AADHAAR]", text)
    # Redact PAN
    text = PAN_REGEX.sub("[PAN]", text)
    # Redact Email
    text = EMAIL_REGEX.sub("[EMAIL]", text)
    # Redact Phone before bank accounts so mobile numbers keep their label
    text = PHONE_REGEX.sub("[PHONE]", text)
    # Redact IFSC, then any remaining long digit run
    text = BANK_IFSC_REGEX.sub("[BANK_ACCOUNT]", text)
    text = BANK_ACCOUNT_REGEX.sub("[BANK_ACCOUNT]", text)

    # Redact explicitly declared names
    text = NAME_TA_REGEX.sub('என் பெயர் [NAME]', text)
    text = NAME_EN_REGEX.sub('my name is [NAME]', text)

    return text
