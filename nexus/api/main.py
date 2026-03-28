"""
NEXUS Content OS — API REST
Permite a Cursor, Alex y sistemas externos interactuar con NEXUS programáticamente.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from nexus.core.orchestrator.graph import nexus_graph, NexusState
from nexus.core.profiles.manager import save_profile, get_profile, profile_to_context
from nexus.shared.storage import list_outputs, save_output

app = FastAPI(
    title="NEXUS Content OS API",
    description="Plataforma de producción de contenido multiformato asistida por IA",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── MODELOS ───────────────────────────────────────────────
class GenerateRequest(BaseModel):
    briefing: str
    profile_id: str = "default"
    operator: str = "system"


class GenerateResponse(BaseModel):
    content: str
    profile_id: str
    published: bool


class ProfileRequest(BaseModel):
    profile_id: str
    data: dict


# ── ENDPOINTS ─────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "service": "NEXUS Content OS", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    """Genera contenido con el perfil de marca indicado."""
    result = nexus_graph.invoke(
        {
            "briefing": req.briefing,
            "profile_id": req.profile_id,
            "operator": req.operator,
            "generated_content": None,
            "human_approved": None,
            "published": False,
            "error": None,
        },
        config={"configurable": {"thread_id": f"api_{req.profile_id}_{len(req.briefing)}"}},
    )
    return GenerateResponse(
        content=result["generated_content"],
        profile_id=req.profile_id,
        published=result["published"],
    )


@app.get("/outputs")
def get_outputs(limit: int = 20):
    """Lista las últimas producciones."""
    return list_outputs(limit)


@app.post("/profiles")
def create_profile(req: ProfileRequest):
    """Crea o actualiza un perfil de marca."""
    save_profile(req.profile_id, req.data)
    return {"status": "saved", "profile_id": req.profile_id}


@app.get("/profiles/{profile_id}")
def get_profile_endpoint(profile_id: str):
    """Recupera un perfil de marca."""
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Perfil '{profile_id}' no encontrado")
    return profile
