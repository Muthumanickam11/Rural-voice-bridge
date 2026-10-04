from datetime import datetime, timezone, timedelta
from fastapi import APIRouter

from api.schemas import RtiGenerateRequest
from config.settings import settings
from privacy.redactor import redact_pii

router = APIRouter()
IST = timezone(timedelta(hours=5, minutes=30))


@router.post("/generate")
def generate_rti_application(req: RtiGenerateRequest):
    today = datetime.now(IST).strftime("%d/%m/%Y")

    # Same PII policy as the Q&A path. The letter still needs the real name and
    # address on the copy the user prints, but any identifier that is not
    # needed for addressing (reference numbers, problem text) is redacted
    # before it is echoed back or logged.
    problem = redact_pii(req.problem) if settings.PII_REDACTION else req.problem
    ref_numbers = redact_pii(req.ref_numbers) if settings.PII_REDACTION else req.ref_numbers
    name = (req.applicant_name or "").strip() or "குடிமகன் / குடிமகள்"
    address = (req.applicant_address or "").strip()

    # Smart question restructuring
    # Convert "why was my application rejected" into legal record-based inquiries
    q1 = f"Please provide a certified copy of the order / decision recorded regarding my application / grievance relating to: {problem}."
    q2 = f"Please provide certified copies of all file notings, inspection reports, and official correspondence processed in connection with this matter."
    q3 = f"Please provide the names, designations, and office contact details of the officials responsible for taking action on this matter."
    q4 = f"Please provide the daily progress report and date-wise details of action taken on application / ref no: {ref_numbers or 'N/A'}."

    fee_clause = "I belong to a Below Poverty Line (BPL) family (valid BPL / AAY ration card copy enclosed) and am exempt from payment of fee." if req.is_bpl else "I have affixed / enclosed the prescribed application fee of Rs. 10/- by way of Court Fee Stamp / IPO / Demand Draft."

    letter_en = f"""Date: {today}
Place: {req.district.capitalize()}

To:
The Public Information Officer (PIO),
Office of the {req.department.title()},
{req.district.capitalize()} District, Tamil Nadu.

Subject: Request for Information under Section 6(1) of the Right to Information Act, 2005.

Sir / Madam,
I, {name}, resident of {address or req.district.capitalize()}, hereby request the following information under Section 6(1) of the RTI Act, 2005:

1. {q1}
2. {q2}
3. {q3}
4. {q4}

Fee Details:
{fee_clause}

Statutory Time Limit:
Kindly furnish the requested information within the statutory period of 30 days as mandated under Section 7(1) of the RTI Act, 2005 (or within 48 hours if concerning life and liberty).

Declaration:
To the best of my knowledge, the information sought above does not fall under any of the exempted categories under Section 8 or 9 of the RTI Act, 2005.

Yours faithfully,

(Signature / Left Thumb Impression)
Name: {name}
Address: {address or req.district.capitalize()}
Enclosures:
1. Proof of fee payment (Court fee stamp / IPO / DD / BPL card copy)
2. Copies of previous applications / receipts (if any)
"""

    explanation_ta = f"""தேதி: {today} | இடம்: {req.district}
பெறுநர்: பொதுத் தகவல் அலுவலர் (PIO), {req.department} துறை, {req.district} மாவட்டம்.
பொருள்: தகவல் அறியும் உரிமைச் சட்டம் 2005 பிரிவு 6(1)-ன் கீழ் தகவல் கோருதல்.

நீங்கள் கோரிய தகவல்கள்:
1. எனது விண்ணப்பம் / புகார் ({problem}) மீது எடுக்கப்பட்ட அதிகாரப்பூர்வ முடிவு மற்றும் உத்தரவின் சான்றொப்பமிட்ட நகல்.
2. இந்த மனு மீது அரசு அலுவலர்கள் எழுதிய கோப்புக் குறிப்புகள் (File Notings) மற்றும் அறிக்கைகளின் நகல்கள்.
3. இதில் நடவடிக்கை எடுக்க வேண்டிய அலுவலர்களின் பெயர் மற்றும் பதவி விபரம்.
4. நாள் வாரியாக எடுக்கப்பட்ட நடவடிக்கைகள் விபரம்.

கட்டண விபரம்:
{"வறுமைக் கோட்டிற்கு கீழ் உள்ள குடும்ப அட்டை நகல் இணைக்கப்பட்டுள்ளது (கட்டணம் இலவசம்)." if req.is_bpl else "மனு கட்டணம் ₹10 நீதிமன்ற கட்டண வில்லை அல்லது அஞ்சல் ஆணை மூலம் செலுத்தப்பட்டுள்ளது."}
"""

    checklist = [
        "மனுவில் ₹10 நீதிமன்ற கட்டண வில்லை (Court Fee Stamp) ஒட்டவும் அல்லது அஞ்சலகத்தில் ₹10 Indian Postal Order வாங்கவும் (BPL அட்டை இருப்பின் கட்டணம் இலவசம்).",
        "மனுவை தாலுகா / மாவட்ட அலுவலக பொதுத் தகவல் அலுவலருக்கு (PIO) பதிவுத் தபால் (Registered Post with Ack Due) மூலம் அனுப்பவும்.",
        "தபால் அனுப்பிய ரசீது மற்றும் ஒப்புகை அட்டையை பத்திரமாக வைத்திருக்கவும்.",
        "மனு சேர்ந்த நாளிலிருந்து 30 நாட்களுக்குள் தகவல் கிடைக்க வேண்டும்.",
        "30 நாட்களில் தகவல் வராவிட்டால், அதே அலுவலக முதல் மேல்முறையீட்டு அலுவலருக்கு (First Appellate Authority) இலவசமாக மேல்முறையீடு செய்யலாம்."
    ]

    route_advice = "இது பொதுவான சேவை குறைபாடு எனில், முதலமைச்சரின் உதவி மையம் (1100) அல்லது மாவட்ட ஆட்சியரின் திங்கட்கிழமை மக்கள் குறைதீர்ப்பு முகாமிலும் உடனடியாக மனு அளிக்கலாம்."

    return {
        "letter_en": letter_en,
        "letter_ta": explanation_ta,
        "checklist": checklist,
        "route_advice": route_advice,
        "deadline_days": 30
    }
