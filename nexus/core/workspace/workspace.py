"""
NEXUS — Gestión de workspaces (multi-tenant)
Un workspace = un cliente/empresa del SaaS. Aislamiento total de datos.
El arquetipo define la configuración automática del workspace.
"""
import os
import json
import hashlib
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from nexus.core.workspace.archetypes import ArchetypeID, get_archetype

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
WORKSPACES_COLLECTION = "workspaces"
VECTOR_SIZE = 1024

_qdrant = None


def _get_qdrant():
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(url=QDRANT_URL)
        collections = [c.name for c in _qdrant.get_collections().collections]
        if WORKSPACES_COLLECTION not in collections:
            _qdrant.create_collection(
                collection_name=WORKSPACES_COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
    return _qdrant


def _id_from_slug(slug: str) -> int:
    return int(hashlib.md5(slug.encode()).hexdigest()[:8], 16)


def create_workspace(
    workspace_id: str,
    name: str,
    archetype_id: str,
    company_context: dict = None,
) -> dict:
    """
    Crea un workspace nuevo con configuración basada en el arquetipo.
    
    company_context: {
        tone, beliefs, main_channels, brand_colors, target_audience, ...
    }
    """
    archetype = get_archetype(archetype_id)

    workspace = {
        "workspace_id": workspace_id,
        "name": name,
        "archetype": archetype_id,
        "archetype_label": archetype.label,
        "can_manage_clients": archetype.can_manage_clients,
        "active_modules": archetype.modules,
        "default_channels": archetype.default_channels,
        "max_brand_profiles": archetype.max_brand_profiles,
        "primary_workflow": archetype.primary_workflow,
        "company_context": company_context or {},
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }

    qdrant = _get_qdrant()
    qdrant.upsert(
        collection_name=WORKSPACES_COLLECTION,
        points=[PointStruct(
            id=_id_from_slug(workspace_id),
            vector=[0.1] * VECTOR_SIZE,
            payload=workspace,
        )],
    )
    return workspace


def get_workspace(workspace_id: str) -> dict | None:
    qdrant = _get_qdrant()
    results, _ = qdrant.scroll(
        collection_name=WORKSPACES_COLLECTION,
        scroll_filter=Filter(must=[
            FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
        ]),
        with_payload=True,
        limit=1,
    )
    return results[0].payload if results else None


def list_workspaces() -> list[dict]:
    qdrant = _get_qdrant()
    results, _ = qdrant.scroll(
        collection_name=WORKSPACES_COLLECTION,
        with_payload=True,
        limit=100,
    )
    return [r.payload for r in results]


def workspace_has_module(workspace_id: str, module: str) -> bool:
    ws = get_workspace(workspace_id)
    if not ws:
        return False
    return module in ws.get("active_modules", [])


def workspace_to_context(workspace: dict) -> str:
    """Convierte el workspace en contexto legible para el LLM."""
    ctx = workspace.get("company_context", {})
    archetype = workspace.get("archetype_label", "")
    parts = [
        f"Empresa: {workspace.get('name')} ({archetype})",
    ]
    if ctx.get("tone"):
        parts.append(f"Tono: {ctx['tone']}")
    if ctx.get("target_audience"):
        parts.append(f"Audiencia: {ctx['target_audience']}")
    if ctx.get("beliefs"):
        beliefs = ctx["beliefs"] if isinstance(ctx["beliefs"], list) else [ctx["beliefs"]]
        parts.append(f"Valores: {', '.join(beliefs)}")
    return "\n".join(parts)
