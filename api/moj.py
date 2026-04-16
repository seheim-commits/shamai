import httpx

BASE_URL = (
    "https://pub-justice.openapi.gov.il/pub/moj/portal/rest"
    "/searchpredefinedapi/v1/SearchPredefinedApi/DecisiveAppraiser"
)
PDF_BASE_URL = (
    "https://free-justice.openapi.gov.il/free/moj/portal/rest"
    "/searchpredefinedapi/v1/SearchPredefinedApi/Documents/DecisiveAppraiser"
)

HEADERS = {
    "accept": "application/json",
    "content-type": "application/json;charset=UTF-8",
    "x-client-id": "149a5bad-edde-49a6-9fb9-188bd17d4788",
    "referer": "https://www.gov.il/he/departments/dynamiccollectors/decisive_appraisal_decisions?skip=0",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "origin": "https://www.gov.il",
}


def search_decisions(skip: int = 0, **filters) -> dict:
    body = {"skip": skip, **{k: v for k, v in filters.items() if v}}
    with httpx.Client(timeout=30) as client:
        r = client.post(f"{BASE_URL}/SearchDecisions", json=body, headers=HEADERS)
        r.raise_for_status()
        return r.json()


_COMMITTEES_FALLBACK = ['אור יהודה', 'אזור', 'אילת', 'אלעד', 'אשקלון', 'באר טוביה', 'בית שמש', 'בני ברק', 'בת ים', 'גבעות אלונים', 'גבעת שמואל', 'גבעתיים', 'גדרה', 'גן יבנה', 'דרום השרון', 'הגליל המזרחי', 'הגליל המרכזי', 'הגליל תחתון', 'הדרים הוד השרון', 'הראל', 'הרצליה', 'ועדה מחוזית חיפה', 'זמורה', 'חבל אשר', 'חדרה', 'חולון', 'חוף השרון', 'חיפה', 'טבריה', 'יבנה', 'יהוד-נווה אפריים', 'יישובי הברון', 'ירושלים', 'כפר סבא', 'כפר שמריהו', 'לב הגליל', 'לב השרון', 'לוד', 'מבוא העמקים', 'מודיעין - מכבים - רעות', 'מורדות הכרמל', 'מטה יהודה', 'מעלה נפתלי', 'מעלות תרשיחא', 'מצפה אפק', 'משגב', 'נהריה', 'נתיבות', 'נתניה', 'עמק חפר', 'פרדס חנה כרכור', 'פתח תקוה', 'צפת', 'קצרין', 'קרית אתא', 'קרית גת', 'ראשון לציון', 'רחובות', 'רמלה', 'רמת גן', 'רמת השרון', 'רעננה', 'שוהם', 'שרונים', 'תל אביב-יפו']

_APPRAISERS_FALLBACK = ['אשור מישל', 'בן פורת לילך', 'ברזילי בועז', 'בריל דוד', 'גולדברג ארנון', 'גלן אורית', 'דדון דוד', 'דדון מרדכי', 'דודזון שמאמה אוולין', 'הוכטייל נתלי', 'הלוי יעקב', 'הרון יעל', 'הרצברג גיל', 'וייס רביב רינת', 'חיים מסילתי', 'חימי אלדד', 'יוסף יגאל', 'יפה שלומי', 'ירקוני ערן', 'כהן אלי', 'כהן אליהו', 'כהן ארז', 'מאור רמה', 'סרחאן עומר', "פז יעקב –ג'קי", 'פלד יהודה', 'צדיק גיא', 'קוט בועז', 'רבינסון חגית', 'שוורצברד ברק', 'שחור דנה']


def get_committees() -> list:
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{BASE_URL}/CommiteesList", headers=HEADERS)
            r.raise_for_status()
            return r.json()
    except Exception:
        return _COMMITTEES_FALLBACK


def get_appraisers() -> list:
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{BASE_URL}/DecisiveAppraisersList", headers=HEADERS)
            r.raise_for_status()
            return r.json()
    except Exception:
        return _APPRAISERS_FALLBACK


_VERSIONS_FALLBACK = ['שומה מקורית', 'שומה מתוקנת אחרי ערר']


def get_versions() -> list:
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{BASE_URL}/AppraisalVersions", headers=HEADERS)
            r.raise_for_status()
            items = r.json()
            # API returns objects; extract string values, skip numeric placeholders
            return [v["Value"] for v in items if isinstance(v, dict) and not v["Value"].isdigit()]
    except Exception:
        return _VERSIONS_FALLBACK


def pdf_url(token: str) -> str:
    return f"{PDF_BASE_URL}/{token}"
