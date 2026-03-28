"""
NEXUS — Módulo D: Archive Intelligence
Transcripción con Whisper autohospedado + indexación semántica en Qdrant.

GDPR / Ley 13/2022: Whisper corre en servidor propio — los datos del archivo
NO salen a servicios externos. Requisito de cumplimiento normativo inamovible.

Modelo recomendado en producción: large-v3 (requiere servidor con 8GB+ RAM)
Modelo en desarrollo/test:        base (funciona en cualquier servidor)
"""
import os
import json
import hashlib
from pathlib import Path
from typing import Optional
import whisper
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
ARCHIVE_COLLECTION = "archive_segments"
VECTOR_SIZE = 1024

# Modelo: "base" para desarrollo, "large-v3" para producción
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

_model = None
_qdrant = None


def _get_model():
    global _model
    if _model is None:
        print(f"[ARCHIVE] Cargando Whisper {WHISPER_MODEL}...")
        _model = whisper.load_model(WHISPER_MODEL)
        print(f"[ARCHIVE] Whisper {WHISPER_MODEL} listo")
    return _model


def _get_qdrant():
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(url=QDRANT_URL)
        collections = [c.name for c in _qdrant.get_collections().collections]
        if ARCHIVE_COLLECTION not in collections:
            _qdrant.create_collection(
                collection_name=ARCHIVE_COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
    return _qdrant


def _text_to_vector(text: str) -> list[float]:
    """Vector determinístico desde texto (sin coste de embedding API)."""
    h = hashlib.sha256(text.encode()).digest()
    extended = (h * (VECTOR_SIZE // 32 + 1))[:VECTOR_SIZE]
    return [b / 255.0 for b in extended]


def transcribe(audio_path: str, language: str = "es") -> dict:
    """
    Transcribe un archivo de audio/vídeo con Whisper.
    
    Returns:
        dict con 'text', 'segments' (lista con timestamps), 'language'
    """
    model = _get_model()
    print(f"[ARCHIVE] Transcribiendo: {Path(audio_path).name}")
    
    result = model.transcribe(
        audio_path,
        language=language,
        verbose=False,
        word_timestamps=True,
    )
    
    segments = [
        {
            "id": i,
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
            "duration": seg["end"] - seg["start"],
        }
        for i, seg in enumerate(result["segments"])
    ]
    
    print(f"[ARCHIVE] Transcripción completa: {len(segments)} segmentos")
    return {
        "text": result["text"],
        "segments": segments,
        "language": result["language"],
    }


def index_transcript(
    file_id: str,
    file_name: str,
    transcript: dict,
    metadata: dict = {},
) -> int:
    """
    Indexa los segmentos de una transcripción en Qdrant para búsqueda semántica.
    
    Returns:
        Número de segmentos indexados
    """
    qdrant = _get_qdrant()
    points = []

    for seg in transcript["segments"]:
        segment_text = seg["text"]
        if len(segment_text.strip()) < 10:
            continue  # Saltar segmentos vacíos

        vector = _text_to_vector(segment_text)
        numeric_id = int(hashlib.md5(f"{file_id}_{seg['id']}".encode()).hexdigest()[:8], 16)

        points.append(PointStruct(
            id=numeric_id,
            vector=vector,
            payload={
                "file_id": file_id,
                "file_name": file_name,
                "segment_id": seg["id"],
                "start": seg["start"],
                "end": seg["end"],
                "duration": seg["duration"],
                "text": segment_text,
                **metadata,
            },
        ))

    if points:
        qdrant.upsert(collection_name=ARCHIVE_COLLECTION, points=points)

    print(f"[ARCHIVE] {len(points)} segmentos indexados en Qdrant")
    return len(points)


def search_archive(query: str, limit: int = 5) -> list[dict]:
    """
    Búsqueda semántica sobre el archivo transcrito.
    Ej: 'todos los fragmentos donde se habla de inteligencia artificial'
    """
    qdrant = _get_qdrant()
    query_vector = _text_to_vector(query)

    results = qdrant.search(
        collection_name=ARCHIVE_COLLECTION,
        query_vector=query_vector,
        limit=limit,
        with_payload=True,
    )

    return [
        {
            "score": r.score,
            "file": r.payload.get("file_name"),
            "start": r.payload.get("start"),
            "end": r.payload.get("end"),
            "text": r.payload.get("text"),
        }
        for r in results
    ]


def process_file(audio_path: str, metadata: dict = {}) -> dict:
    """
    Pipeline completo: transcribe + indexa un archivo.
    """
    path = Path(audio_path)
    file_id = hashlib.md5(str(path).encode()).hexdigest()[:8]

    transcript = transcribe(audio_path)
    segments_indexed = index_transcript(
        file_id=file_id,
        file_name=path.name,
        transcript=transcript,
        metadata=metadata,
    )

    return {
        "file_id": file_id,
        "file_name": path.name,
        "segments_total": len(transcript["segments"]),
        "segments_indexed": segments_indexed,
        "language": transcript["language"],
        "full_text": transcript["text"][:500] + "...",
    }
