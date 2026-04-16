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


def get_committees() -> list:
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{BASE_URL}/CommiteesList", headers=HEADERS)
        r.raise_for_status()
        return r.json()


def get_appraisers() -> list:
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{BASE_URL}/DecisiveAppraisersList", headers=HEADERS)
        r.raise_for_status()
        return r.json()


def get_versions() -> list:
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{BASE_URL}/AppraisalVersions", headers=HEADERS)
        r.raise_for_status()
        return r.json()


def pdf_url(token: str) -> str:
    return f"{PDF_BASE_URL}/{token}"
