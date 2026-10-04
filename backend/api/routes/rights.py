from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from rag.retriever import retriever

router = APIRouter()

# Each topic declares the knowledge-base file_ids and search terms that back it.
# Previously topics were matched only by `file_id == topic_id`, which worked for
# exactly one of seven topics; the rest silently returned empty content.
TOPICS: List[Dict[str, Any]] = [
    {
        "id": "land",
        "title_ta": "நில உரிமைகள் (பட்டா / சிட்டா)",
        "title_en": "Land Rights & Patta",
        "icon": "\U0001F33E",
        "description_ta": "பட்டா, சிட்டா, எல்லை தகராறு, ஆக்கிரமிப்பு மற்றும் நில அளவீடு உரிமைகள்.",
        "category": "land",
        "file_ids": ["patta_chitta"],
        "search_terms": "பட்டா சிட்டா அடங்கல் நில உரிமை patta land"
    },
    {
        "id": "bns",
        "title_ta": "புதிய குற்றவியல் சட்டம் (BNS)",
        "title_en": "New Criminal Law (BNS)",
        "icon": "⚖️",
        "description_ta": "பழைய IPC 498A, மோசடி 420 போன்றவற்றுக்கு மாற்றாக வந்த புதிய BNS சட்டங்கள் மற்றும் FIR உரிமைகள்.",
        "category": "legal",
        "file_ids": ["bns_overview"],
        "search_terms": "bns bnss bsa புதிய குற்றவியல் சட்டம் fir"
    },
    {
        "id": "arrest",
        "title_ta": "காவல்துறை & கைது உரிமைகள்",
        "title_en": "Police & Arrest Rights",
        "icon": "\U0001F46E",
        "description_ta": "கைது செய்யப்படும் போது தகவல் உரிமை, பிணை உரிமை மற்றும் பெண்கள் பாதுகாப்பு விதிகள்.",
        "category": "legal",
        "file_ids": ["arrest_rights"],
        "search_terms": "கைது காவல்துறை உரிமை பிணை arrest rights போலீஸ்"
    },
    {
        "id": "legal_aid",
        "title_ta": "இலவச சட்ட உதவி (NALSA)",
        "title_en": "Free Legal Aid & Lok Adalat",
        "icon": "\U0001F3DB️",
        "description_ta": "வழக்கு நடத்த அரசு செலவில் இலவச வழக்கறிஞர் உதவி மற்றும் லோக் அதாலத் சமரசம்.",
        "category": "legal",
        "file_ids": ["legal_aid"],
        "search_terms": "இலவச சட்ட உதவி nalsa lok adalat legal aid dlsa வழக்கறிஞர்"
    },
    {
        "id": "labor",
        "title_ta": "தொழிலாளர் & ஊதிய உரிமைகள்",
        "title_en": "Labor & Minimum Wage Rights",
        "icon": "\U0001F477",
        "description_ta": "100 நாள் வேலை, குறைந்தபட்ச கூலி, சம்பள பாக்கி மற்றும் தொழிலாளர் நல வாரியம்.",
        "category": "scheme",
        "file_ids": ["labor"],
        "search_terms": "தொழிலாளர் ஊதிய கூலி mgnrega labour wage minninum wage"
    },
    {
        "id": "rti",
        "title_ta": "தகவல் அறியும் உரிமை (RTI)",
        "title_en": "Right to Information",
        "icon": "\U0001F4DD",
        "description_ta": "அரசு அலுவலக கோப்புகள் மற்றும் முடிவுகளை ₹10 கட்டணத்தில் பெறும் வழிமுறைகள்.",
        "category": "rti_grievance",
        "file_ids": ["rti_basics"],
        "search_terms": "rti தகவல் அறியும் உரிமை information act பதில்"
    },
    {
        "id": "certificates",
        "title_ta": "அரசு சான்றிதழ்கள் (இ-சேவை)",
        "title_en": "Certificates via e-Sevai",
        "icon": "\U0001F4DC",
        "description_ta": "சாதி, வருமானம், இருப்பிடம், முதல் பட்டதாரி மற்றும் வாரிசு சான்றிதழ் வழிமுறைகள்.",
        "category": "processes",
        "file_ids": ["certificates"],
        "search_terms": "சான்றிதழ் இ-சேவை certificate esevai சாதி வருமானம்"
    },
]


@router.get("/topics")
def get_rights_topics():
    # Strip internal wiring fields from the public listing.
    public = [{k: v for k, v in t.items() if k not in ("file_ids", "search_terms")} for t in TOPICS]
    return {"topics": public}


@router.get("/{topic_id}")
def get_topic_detail(topic_id: str):
    topic_meta = next((t for t in TOPICS if t["id"] == topic_id), None)

    if topic_meta is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    chunks: List[Dict[str, Any]] = []

    # 1. Direct file_id match (the reliable path).
    for file_id in topic_meta.get("file_ids", []):
        chunks.extend(retriever.chunks_for_file(file_id))

    # 2. Fall back to retrieval if the expected file is missing from the KB.
    if not chunks:
        for term in topic_meta.get("search_terms", topic_id).split():
            for c in retriever.retrieve(term, top_k=3, category_filter=topic_meta.get("category")):
                if c not in chunks:
                    chunks.append(c)
        chunks = chunks[:6]

    if not chunks:
        raise HTTPException(status_code=404, detail="No verified guidance is available for this topic yet")

    return {
        "topic": {k: v for k, v in topic_meta.items() if k not in ("file_ids", "search_terms")},
        "chunks": chunks
    }
