"""
NEXUS — Gestión de perfiles de marca
Almacena y recupera contexto de marca desde Qdrant.
"""
import os
import json
import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from anthropic import Anthropic

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "brand_profiles"
VECTOR_SIZE = 1024  # claude embeddings via voyage / usamos hash simple por ahora

client = QdrantClient(url=QDRANT_URL)
anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _ensure_collection():
    """Crea la colección si no existe."""
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


def _text_to_vector(text: str) -> list[float]:
    """
    Genera un vector desde texto.
    Por ahora usa un hash determinístico simple (sin coste de embedding).
    TODO: Reemplazar con voyage-3 o text-embedding-3-small para semántica real.
    """
    import hashlib
    h = hashlib.sha256(text.encode()).digest()
    # Expande el hash de 32 bytes a VECTOR_SIZE floats normalizados
    extended = (h * (VECTOR_SIZE // 32 + 1))[:VECTOR_SIZE]
    vector = [b / 255.0 for b in extended]
    return vector


def save_profile(profile_id: str, profile_data: dict) -> bool:
    """Guarda o actualiza un perfil de marca en Qdrant."""
    _ensure_collection()

    profile_text = json.dumps(profile_data, ensure_ascii=False)
    vector = _text_to_vector(profile_id + profile_text)

    # ID numérico desde hash del profile_id
    numeric_id = int(hashlib.md5(profile_id.encode()).hexdigest()[:8], 16)

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[PointStruct(
            id=numeric_id,
            vector=vector,
            payload={"profile_id": profile_id, **profile_data},
        )],
    )
    return True


def get_profile(profile_id: str) -> dict | None:
    """Recupera un perfil de marca por ID."""
    _ensure_collection()

    import hashlib
    numeric_id = int(hashlib.md5(profile_id.encode()).hexdigest()[:8], 16)

    results = client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=[numeric_id],
        with_payload=True,
    )

    if results:
        return results[0].payload
    return None


def profile_to_context(profile: dict) -> str:
    """Convierte un perfil en texto de contexto para el LLM."""
    lines = [
        f"MARCA: {profile.get('name', '')}",
        f"DESCRIPCIÓN: {profile.get('description', '')}",
        f"TONO: {profile.get('tone', '')}",
        f"CONVICCIONES: {', '.join(profile.get('beliefs', []))}",
        f"NUNCA DIRÍA: {', '.join(profile.get('never_say', []))}",
    ]
    if profile.get("examples"):
        lines.append("EJEMPLOS DE VOZ:")
        for ex in profile.get("examples", []):
            lines.append(f"  - {ex}")
    return "\n".join(lines)
