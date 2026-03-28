"""
NEXUS — Marcas cliente
Para workspaces de AGENCIA y PRODUCTORA: gestión de marcas de clientes anunciantes.
Cada marca cliente tiene su propia voz, canales y contexto — aislado por workspace.
"""
import os
import hashlib
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
BRANDS_COLLECTION = "client_brands"
VECTOR_SIZE = 1024

_qdrant = None


def _get_qdrant():
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(url=QDRANT_URL)
        collections = [c.name for c in _qdrant.get_collections().collections]
        if BRANDS_COLLECTION not in collections:
            _qdrant.create_collection(
                collection_name=BRANDS_COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
    return _qdrant


def _id(workspace_id: str, brand_id: str) -> int:
    return int(hashlib.md5(f"{workspace_id}:{brand_id}".encode()).hexdigest()[:8], 16)


def add_client_brand(
    workspace_id: str,
    brand_id: str,
    name: str,
    sector: str,
    tone: str,
    target_audience: str,
    channels: list[str],
    beliefs: list[str] = None,
    never_say: list[str] = None,
    examples: list[str] = None,
) -> dict:
    """Añade una marca cliente al workspace de una agencia o productora."""
    brand = {
        "workspace_id": workspace_id,
        "brand_id": brand_id,
        "name": name,
        "sector": sector,
        "tone": tone,
        "target_audience": target_audience,
        "channels": channels,
        "beliefs": beliefs or [],
        "never_say": never_say or [],
        "examples": examples or [],
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }
    _get_qdrant().upsert(
        collection_name=BRANDS_COLLECTION,
        points=[PointStruct(
            id=_id(workspace_id, brand_id),
            vector=[0.1] * VECTOR_SIZE,
            payload=brand,
        )],
    )
    return brand


def list_client_brands(workspace_id: str) -> list[dict]:
    """Lista todas las marcas cliente de un workspace."""
    results, _ = _get_qdrant().scroll(
        collection_name=BRANDS_COLLECTION,
        scroll_filter=Filter(must=[
            FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
        ]),
        with_payload=True,
        limit=100,
    )
    return [r.payload for r in results]


def get_client_brand(workspace_id: str, brand_id: str) -> dict | None:
    results, _ = _get_qdrant().scroll(
        collection_name=BRANDS_COLLECTION,
        scroll_filter=Filter(must=[
            FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id)),
            FieldCondition(key="brand_id", match=MatchValue(value=brand_id)),
        ]),
        with_payload=True,
        limit=1,
    )
    return results[0].payload if results else None


def brand_to_context(brand: dict) -> str:
    """Convierte una marca cliente en contexto para el LLM."""
    parts = [
        f"Marca: {brand['name']} ({brand.get('sector', '')})",
        f"Tono: {brand['tone']}",
        f"Audiencia: {brand['target_audience']}",
    ]
    if brand.get("beliefs"):
        parts.append(f"Valores: {', '.join(brand['beliefs'])}")
    if brand.get("never_say"):
        parts.append(f"Nunca decir: {', '.join(brand['never_say'])}")
    if brand.get("examples"):
        parts.append("Ejemplos de voz:")
        for ex in brand["examples"][:2]:
            parts.append(f'  "{ex}"')
    return "\n".join(parts)
