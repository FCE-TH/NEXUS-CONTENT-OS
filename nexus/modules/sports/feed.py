"""
NEXUS — Módulo C: Sports Intelligence
Contenido deportivo en tiempo real desde TheSportsDB (free, sin API key).
Trigger via Redis pub/sub. Pipeline: evento → Claude → distribución en <5 min.

APIs soportadas:
  - TheSportsDB (free, sin key): arranque inmediato
  - API-Football (RapidAPI): cuando se configure RAPIDAPI_KEY
"""
import os
import asyncio
import httpx
from datetime import datetime

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"


# ── THESPORTSDB (FREE) ────────────────────────────────────
async def get_last_events(league_id: str = "4335", limit: int = 5) -> list[dict]:
    """
    Últimos eventos de una liga desde TheSportsDB.
    Liga 4335 = La Liga española (free, sin key)
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{SPORTSDB_BASE}/eventspastleague.php?id={league_id}")
        resp.raise_for_status()
        data = resp.json()

    events = data.get("events") or []
    return [
        {
            "id": e.get("idEvent"),
            "home": e.get("strHomeTeam"),
            "away": e.get("strAwayTeam"),
            "score_home": e.get("intHomeScore"),
            "score_away": e.get("intAwayScore"),
            "date": e.get("dateEvent"),
            "league": e.get("strLeague"),
            "venue": e.get("strVenue"),
            "status": e.get("strStatus"),
        }
        for e in events[:limit]
    ]


async def get_event_details(event_id: str) -> dict:
    """Detalles de un partido específico."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{SPORTSDB_BASE}/lookupevent.php?id={event_id}")
        resp.raise_for_status()
        data = resp.json()

    events = data.get("events") or []
    if not events:
        return {}

    e = events[0]
    return {
        "id": e.get("idEvent"),
        "home": e.get("strHomeTeam"),
        "away": e.get("strAwayTeam"),
        "score_home": e.get("intHomeScore"),
        "score_away": e.get("intAwayScore"),
        "date": e.get("dateEvent"),
        "league": e.get("strLeague"),
        "description": e.get("strDescriptionEN") or e.get("strDescriptionES") or "",
        "venue": e.get("strVenue"),
        "city": e.get("strCity"),
    }


async def get_league_standings(league_id: str = "4335") -> list[dict]:
    """Clasificación actual de una liga."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{SPORTSDB_BASE}/lookuptable.php?l={league_id}&s=2024-2025")
        resp.raise_for_status()
        data = resp.json()

    table = data.get("table") or []
    return [
        {
            "pos": t.get("intRank"),
            "team": t.get("strTeam"),
            "played": t.get("intPlayed"),
            "won": t.get("intWin"),
            "drawn": t.get("intDraw"),
            "lost": t.get("intLoss"),
            "gf": t.get("intGoalsFor"),
            "ga": t.get("intGoalsAgainst"),
            "points": t.get("intPoints"),
        }
        for t in table[:10]  # Top 10
    ]


def format_event_for_briefing(event: dict) -> str:
    """Convierte datos de partido en briefing para el LLM."""
    return (
        f"Partido: {event['home']} {event['score_home']} - {event['score_away']} {event['away']}\n"
        f"Liga: {event['league']}\n"
        f"Fecha: {event['date']}\n"
        f"Estado: {event.get('status', 'Finalizado')}\n"
        f"Estadio: {event.get('venue', '')}"
    )


# ── REDIS TRIGGER (pub/sub) ───────────────────────────────
async def publish_sports_event(event: dict, redis_url: str = "redis://localhost:6379"):
    """Publica un evento deportivo en Redis para que el orquestador lo procese."""
    import redis.asyncio as aioredis
    import json

    r = await aioredis.from_url(redis_url)
    await r.publish("nexus:sports:events", json.dumps(event))
    await r.aclose()
    print(f"[SPORTS] Evento publicado en Redis: {event.get('home')} vs {event.get('away')}")
