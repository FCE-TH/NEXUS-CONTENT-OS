"""
NEXUS — Conector LiveScore (RapidAPI)
Partidos reales de LaLiga y ligas europeas.
"""
import os
import httpx

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
HOST = "livescore6.p.rapidapi.com"
BASE = f"https://{HOST}"

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": HOST,
    "Content-Type": "application/json",
}


def _parse_event(e: dict, stage: dict) -> dict:
    """Extrae datos relevantes de un evento."""
    t1 = e.get("T1", [{}])[0]
    t2 = e.get("T2", [{}])[0]
    return {
        "id": e.get("Eid"),
        "home": t1.get("Nm", ""),
        "away": t2.get("Nm", ""),
        "score_home": e.get("Tr1", "-"),
        "score_away": e.get("Tr2", "-"),
        "status": e.get("Eps", ""),
        "league": stage.get("Snm", ""),
        "country": stage.get("Cnm", ""),
        "date": e.get("Esd", ""),
    }


def get_laliga_matches() -> list[dict]:
    """Últimos partidos de LaLiga."""
    resp = httpx.get(
        f"{BASE}/matches/v2/list-by-league",
        params={"Category": "soccer", "Ccd": "spain", "Scd": "laliga"},
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    matches = []
    for stage in data.get("Stages", []):
        for event in stage.get("Events", []):
            matches.append(_parse_event(event, stage))

    return matches


def get_live_matches(category: str = "soccer") -> list[dict]:
    """Partidos en vivo ahora mismo."""
    resp = httpx.get(
        f"{BASE}/matches/v2/list-live",
        params={"Category": category},
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    matches = []
    for stage in data.get("Stages", []):
        for event in stage.get("Events", []):
            matches.append(_parse_event(event, stage))

    return matches
