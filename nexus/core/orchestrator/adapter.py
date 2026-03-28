"""
NEXUS — Adaptador de contenido por canal
Toma el contenido original y genera versiones optimizadas para cada plataforma.
Usa las instrucciones del clasificador para adaptar, no reescribir desde cero.
"""
import os
from anthropic import Anthropic

anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

PLATFORM_SPECS = {
    "linkedin": {
        "max_chars": 3000,
        "style": "Profesional, párrafos cortos, emojis moderados, hashtags al final (3-5 máx).",
        "format": "Texto estructurado con saltos de línea. Primer párrafo como gancho.",
    },
    "x": {
        "max_chars": 280,
        "style": "Directo, sin relleno. Datos concretos. Máximo impacto en mínimo espacio.",
        "format": "Si es largo, hilo numerado (1/N). Sin hashtags en exceso.",
    },
    "instagram": {
        "max_chars": 2200,
        "style": "Visual, más cercano, emojis naturales. Storytelling breve.",
        "format": "Caption con gancho en primera línea. Hashtags en comentario o al final separados.",
    },
    "facebook": {
        "max_chars": 63206,
        "style": "Conversacional, más contextual que LinkedIn.",
        "format": "Párrafos cortos, pregunta al final para fomentar comentarios.",
    },
}


def adapt_for_platform(
    original_content: str,
    platform: str,
    adaptation_instructions: str = "",
    profile_context: str = "",
) -> str:
    """
    Adapta contenido para una plataforma específica.
    Si no hay instrucciones de adaptación, devuelve el original.
    """
    if not adaptation_instructions or adaptation_instructions.lower() == "null":
        # Sin cambios necesarios — devolver original (posiblemente truncado)
        spec = PLATFORM_SPECS.get(platform, {})
        max_chars = spec.get("max_chars", 99999)
        return original_content[:max_chars] if len(original_content) > max_chars else original_content

    spec = PLATFORM_SPECS.get(platform, {})
    
    system = f"""Adapta el siguiente contenido para {platform.upper()}.

Especificaciones de {platform}:
- Máximo: {spec.get('max_chars', 'sin límite')} caracteres
- Estilo: {spec.get('style', '')}
- Formato: {spec.get('format', '')}

Instrucciones específicas de adaptación: {adaptation_instructions}

{f'Contexto de marca: {profile_context}' if profile_context else ''}

IMPORTANTE: Mantén la voz y mensajes clave del original. Adapta el formato y longitud, no el mensaje.
Devuelve SOLO el contenido adaptado, sin explicaciones."""

    response = anthropic.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": f"CONTENIDO ORIGINAL:\n\n{original_content}"}],
    )

    return response.content[0].text.strip()


def adapt_all_platforms(
    original_content: str,
    classification: dict,
    profile_context: str = "",
) -> dict[str, str]:
    """
    Genera versiones adaptadas para todos los canales óptimos.
    
    Returns:
        dict {platform: adapted_content}
    """
    adaptations = classification.get("adaptations_needed", {})
    target_platforms = classification.get("optimal_platforms", [])
    
    results = {}
    for platform in target_platforms:
        instructions = adaptations.get(platform, "")
        adapted = adapt_for_platform(
            original_content=original_content,
            platform=platform,
            adaptation_instructions=instructions or "",
            profile_context=profile_context,
        )
        results[platform] = adapted
        print(f"[ADAPT] {platform}: {len(adapted)} chars")
    
    return results
