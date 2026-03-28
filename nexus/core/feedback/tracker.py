"""
NEXUS — Sistema de retroalimentación (Hito H8)
Las métricas de rendimiento de lo publicado alimentan la siguiente generación.
Principio: el sistema aprende qué funciona para cada perfil y canal.
"""
import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
FEEDBACK_COLLECTION = "content_performance"
VECTOR_SIZE = 1024

_qdrant = None


def _get_qdrant():
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(url=QDRANT_URL)
        collections = [c.name for c in _qdrant.get_collections().collections]
        if FEEDBACK_COLLECTION not in collections:
            _qdrant.create_collection(
                collection_name=FEEDBACK_COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
    return _qdrant


def _text_to_vector(text: str) -> list[float]:
    h = hashlib.sha256(text.encode()).digest()
    extended = (h * (VECTOR_SIZE // 32 + 1))[:VECTOR_SIZE]
    return [b / 255.0 for b in extended]


def record_performance(
    output_id: str,
    profile_id: str,
    platform: str,
    content: str,
    briefing: str,
    content_type: str,
    metrics: dict,
) -> bool:
    """
    Registra las métricas de rendimiento de un contenido publicado.
    
    metrics dict esperado:
    {
        "views": int,
        "likes": int,
        "shares": int,
        "comments": int,
        "clicks": int,
        "engagement_rate": float,  # 0.0 - 1.0
    }
    """
    qdrant = _get_qdrant()

    # Score compuesto (ponderado)
    engagement = metrics.get("engagement_rate", 0)
    shares = metrics.get("shares", 0)
    clicks = metrics.get("clicks", 0)
    views = max(metrics.get("views", 1), 1)

    performance_score = (
        engagement * 40 +           # engagement rate: el más importante
        (shares / views) * 30 +     # viralidad
        (clicks / views) * 20 +     # conversión
        min(views / 1000, 1) * 10   # alcance (normalizado, cap 1000 views = max)
    )

    numeric_id = int(hashlib.md5(f"{output_id}_{platform}".encode()).hexdigest()[:8], 16)

    qdrant.upsert(
        collection_name=FEEDBACK_COLLECTION,
        points=[PointStruct(
            id=numeric_id,
            vector=_text_to_vector(content),
            payload={
                "output_id": output_id,
                "profile_id": profile_id,
                "platform": platform,
                "content_type": content_type,
                "briefing": briefing,
                "content_preview": content[:300],
                "metrics": metrics,
                "performance_score": round(performance_score, 2),
                "recorded_at": datetime.now().isoformat(),
            },
        )],
    )
    return True


def get_top_performers(
    profile_id: str,
    platform: str = "",
    limit: int = 3,
) -> list[dict]:
    """
    Recupera los contenidos con mejor rendimiento para un perfil.
    Estos se usan como contexto en la siguiente generación.
    """
    qdrant = _get_qdrant()

    # Scroll con filtro por perfil
    results, _ = qdrant.scroll(
        collection_name=FEEDBACK_COLLECTION,
        scroll_filter=Filter(
            must=[FieldCondition(key="profile_id", match=MatchValue(value=profile_id))]
        ),
        with_payload=True,
        limit=100,
    )

    if not results:
        return []

    # Filtrar por plataforma si se especifica
    if platform:
        results = [r for r in results if r.payload.get("platform") == platform]

    # Ordenar por performance_score descendente
    sorted_results = sorted(
        results,
        key=lambda r: r.payload.get("performance_score", 0),
        reverse=True,
    )

    return [r.payload for r in sorted_results[:limit]]


def format_feedback_context(top_performers: list[dict]) -> str:
    """
    Convierte los mejores contenidos en contexto legible para el LLM.
    """
    if not top_performers:
        return ""

    lines = ["CONTENIDOS CON MEJOR RENDIMIENTO (úsalos como referencia de estilo y enfoque):"]
    for i, p in enumerate(top_performers, 1):
        score = p.get("performance_score", 0)
        metrics = p.get("metrics", {})
        lines.append(
            f"\n[#{i} — Score {score:.1f} | "
            f"{metrics.get('views', 0)} views | "
            f"{metrics.get('engagement_rate', 0)*100:.1f}% engagement | "
            f"{p.get('platform', '')}]"
        )
        lines.append(f"Briefing: {p.get('briefing', '')[:80]}")
        lines.append(f"Contenido: {p.get('content_preview', '')[:200]}")

    return "\n".join(lines)
