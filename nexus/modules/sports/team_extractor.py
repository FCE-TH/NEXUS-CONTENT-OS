"""
NEXUS — Extractor de equipo/liga del briefing deportivo
Detecta automáticamente qué equipo/liga mencionas para buscar datos específicos.
"""
import re

# Mapeo de nombres a IDs de liga/competición
TEAM_TO_LEAGUE = {
    # LaLiga
    "real madrid": "laliga",
    "barcelona": "laliga",
    "atletico": "laliga",
    "sevilla": "laliga",
    "real sociedad": "laliga",
    "betis": "laliga",
    "athletic": "laliga",
    "bilbao": "laliga",
    "girona": "laliga",
    "osasuna": "laliga",
    "rayo": "laliga",
    "vallecano": "laliga",
    "villarreal": "laliga",
    "laliga": "laliga",
    
    # Champions League
    "champions": "champions",
    "champions league": "champions",
    
    # Other leagues
    "premier": "premier",
    "liga": "laliga",
    "serie a": "seria",
    "bundesliga": "bundesliga",
    "ligue 1": "ligue1",
    
    # Clubs generales
    "madrid": "laliga",
    "barca": "laliga",
    "messi": "laliga",
    "ronaldo": "laliga",
    "vinicius": "laliga",
}

LEAGUE_IDS = {
    "laliga": "laliga",
    "champions": "champions",
    "premier": "premier",
    "serie": "seria",
    "bundesliga": "bundesliga",
    "ligue1": "ligue1",
}


def extract_team_and_league(briefing: str) -> dict:
    """
    Analiza el briefing y extrae equipo/liga mencionados.
    
    Returns:
        {
            "team": "nombre del equipo" or None,
            "league": "id_liga" or None,
            "confidence": float (0-1),
        }
    """
    briefing_lower = briefing.lower()
    
    # Buscar coincidencias de equipo
    matched_team = None
    matched_league = None
    confidence = 0.0
    
    # Primer intento: buscar nombre de equipo exacto
    for team_name, league_id in TEAM_TO_LEAGUE.items():
        if team_name in briefing_lower:
            matched_team = team_name
            matched_league = league_id
            confidence = 0.9
            break
    
    # Segundo intento: buscar liga
    if not matched_league:
        for league_name, league_id in LEAGUE_IDS.items():
            if league_name in briefing_lower:
                matched_league = league_id
                confidence = 0.7
                break
    
    # Tercer intento: palabras clave genéricas que indican LaLiga (default)
    if not matched_league:
        if any(kw in briefing_lower for kw in ["partido", "gol", "resultado"]):
            matched_league = "laliga"  # Default: LaLiga
            confidence = 0.3
    
    return {
        "team": matched_team,
        "league": matched_league,
        "confidence": confidence,
        "briefing_snippet": briefing[:100],
    }


def format_extraction_for_livescore(extraction: dict) -> dict:
    """
    Convierte la extracción en parámetros para LiveScore.
    
    Returns:
        {"league": "laliga", "country": "spain", ...}
    """
    league = extraction.get("league", "laliga")
    
    league_params = {
        "laliga": {"Scd": "laliga", "Ccd": "spain"},
        "champions": {"Scd": "champions", "Ccd": None},
        "premier": {"Scd": "premier", "Ccd": "england"},
        "seria": {"Scd": "seria", "Ccd": "italy"},
        "bundesliga": {"Scd": "bundesliga", "Ccd": "germany"},
        "ligue1": {"Scd": "ligue1", "Ccd": "france"},
    }
    
    return league_params.get(league, league_params["laliga"])
