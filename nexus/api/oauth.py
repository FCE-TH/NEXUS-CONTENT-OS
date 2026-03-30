"""
NEXUS — OAuth2 para LinkedIn
Flujo: Usuario → "Autorizar LinkedIn" → LinkedIn approval → token guardado
"""
import os
import httpx
from fastapi import APIRouter, HTTPException, Query
from urllib.parse import urlencode

router = APIRouter()

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI = "http://161.35.157.215:8000/api/oauth/callback"  # Callback a FastAPI


@router.get("/oauth/linkedin/authorize")
def authorize_linkedin():
    """Redirige al usuario a LinkedIn para autorizar."""
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(status_code=400, detail="LinkedIn credentials not configured")

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "w_member_social",  # Permisos para publicar
        "state": "nexus_oauth_state",
    }
    auth_url = f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"
    return {"redirect_url": auth_url}


@router.get("/oauth/callback")
async def oauth_callback(code: str = Query(None), error: str = Query(None)):
    """Callback después de que usuario aprueba en LinkedIn."""
    if error:
        return {"error": f"LinkedIn OAuth error: {error}"}

    if not code:
        return {"error": "No authorization code received"}

    # Intercambiar code por access token
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                LINKEDIN_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                },
            )

        if token_response.status_code != 200:
            return {"error": f"Failed to get token: {token_response.text}"}

        token_data = token_response.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 5184000)  # 60 days default

        # Guardar solo el access token por ahora
        # El person_id se obtiene cuando publiquemos (lazy loading)
        _save_linkedin_token(access_token, "", expires_in)
        
        return {
            "success": True,
            "message": f"✓ LinkedIn autorizado! Token guardado.",
            "note": "Token guardado. Se usará al publicar.",
        }

    except Exception as e:
        return {"error": f"OAuth error: {str(e)}"}


def _save_linkedin_token(token: str, person_id: str, expires_in: int):
    """Guarda token en .env (MVP - en prod usar database)."""
    env_path = "/root/.openclaw/workspace/projects/nexus/.env"
    
    # Leer .env actual
    with open(env_path, "r") as f:
        lines = f.readlines()
    
    # Remover líneas antiguas de LinkedIn token
    lines = [l for l in lines if not l.startswith("LINKEDIN_ACCESS_TOKEN=") and not l.startswith("LINKEDIN_PERSON_ID=")]
    
    # Añadir nuevas credenciales
    lines.append(f"LINKEDIN_ACCESS_TOKEN={token}\n")
    lines.append(f"LINKEDIN_PERSON_ID={person_id}\n")
    
    # Escribir .env actualizado
    with open(env_path, "w") as f:
        f.writelines(lines)
    
    print(f"✓ LinkedIn token guardado en .env (expira en {expires_in}s)")
