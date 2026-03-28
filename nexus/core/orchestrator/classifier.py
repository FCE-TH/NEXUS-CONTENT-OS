"""
NEXUS — Clasificador de contenido
Analiza el output generado y decide: tipo, formato, canales óptimos, adaptaciones.
Usa Claude Haiku (tarea de extracción/clasificación — rápido y barato).
"""
import os
import json
from anthropic import Anthropic

anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CLASSIFIER_PROMPT = """Analiza el siguiente contenido generado y devuelve un JSON con esta estructura exacta:

{
  "content_type": "tweet|thread|post_linkedin|article|caption_ig|cronoca_deportiva|script_video|otro",
  "tone": "informativo|promocional|emocional|humoristico|urgente|educativo",
  "length_category": "micro|corto|medio|largo",
  "topics": ["lista", "de", "temas", "detectados"],
  "optimal_platforms": ["linkedin", "instagram", "x", "youtube", "facebook"],
  "needs_media": true|false,
  "urgency": "alta|media|baja",
  "adaptations_needed": {
    "linkedin": "descripción breve de qué adaptar o null si no necesita cambios",
    "instagram": "descripción breve o null",
    "x": "descripción breve o null"
  },
  "quality_score": 1-10,
  "quality_notes": "observación breve sobre calidad y mejoras"
}

Solo devuelve el JSON, sin texto adicional."""


def classify_content(content: str, profile_id: str = "", briefing: str = "") -> dict:
    """
    Clasifica contenido generado y determina su distribución óptima.
    
    Returns:
        dict con clasificación completa
    """
    context = f"Perfil: {profile_id}\nBriefing original: {briefing}\n\n" if profile_id else ""
    
    response = anthropic.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        system=CLASSIFIER_PROMPT,
        messages=[{
            "role": "user",
            "content": f"{context}CONTENIDO A CLASIFICAR:\n\n{content}"
        }],
    )

    raw = response.content[0].text.strip()
    
    # Limpiar posibles backticks si el modelo los añade
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    
    try:
        classification = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback si el JSON falla
        classification = {
            "content_type": "otro",
            "optimal_platforms": ["linkedin"],
            "urgency": "media",
            "quality_score": 5,
            "quality_notes": "Clasificación automática fallida",
            "raw_response": raw,
        }
    
    classification["tokens_used"] = response.usage.output_tokens
    return classification


def route_to_platforms(classification: dict) -> list[str]:
    """Devuelve los canales donde debe publicarse según la clasificación."""
    return classification.get("optimal_platforms", [])


def format_classification_summary(classification: dict) -> str:
    """Resumen legible de la clasificación para logs y UI."""
    return (
        f"Tipo: {classification.get('content_type')} | "
        f"Tono: {classification.get('tone')} | "
        f"Canales: {', '.join(classification.get('optimal_platforms', []))} | "
        f"Calidad: {classification.get('quality_score')}/10 | "
        f"Urgencia: {classification.get('urgency')}"
    )
