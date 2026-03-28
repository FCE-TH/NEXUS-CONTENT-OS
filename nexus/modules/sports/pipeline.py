"""
NEXUS — Pipeline deportivo end-to-end
Evento → Briefing → Claude (Haiku) → Contenido listo para publicar
Objetivo: <5 minutos desde el pitido final
"""
import asyncio
from nexus.modules.sports.feed import get_last_events, format_event_for_briefing
from nexus.modules.content_intelligence.generator import generate_content
from nexus.shared.storage import save_output


SPORTS_SYSTEM_PROMPT = """Eres el redactor deportivo de Canal Deporte.
Escribes crónicas y posts deportivos en español. Estilo: directo, vibrante, datos primero.
Sin florituras. El lector quiere el resultado y los datos clave en los primeros 2 segundos.
Adapta el formato según lo que se pida: tweet, crónica, hilo, post."""


async def generate_match_content(event: dict, format: str = "tweet") -> dict:
    """
    Genera contenido de un partido en el formato indicado.
    
    Formats: tweet | cronica | hilo | post_ig
    """
    format_instructions = {
        "tweet": "Escribe un tweet con el resultado. Máximo 280 caracteres. Incluye el marcador y dato más relevante.",
        "cronica": "Escribe una crónica del partido de 150-200 palabras. Resultado, momentos clave, destacado.",
        "hilo": "Escribe un hilo de 4 tweets sobre el partido. Numera cada tweet (1/4, 2/4...).",
        "post_ig": "Escribe un caption de Instagram sobre el partido. Máximo 150 palabras. Con emojis relevantes.",
    }

    event_data = format_event_for_briefing(event)
    briefing = f"{format_instructions.get(format, format_instructions['tweet'])}\n\nDatos del partido:\n{event_data}"

    result = generate_content(
        briefing=briefing,
        system_prompt_override=SPORTS_SYSTEM_PROMPT,
    )

    return {
        "event": event,
        "format": format,
        "content": result["content"],
        "model": result["model_used"],
        "tokens": result["output_tokens"],
    }


async def run_pipeline(league_id: str = "4335", formats: list[str] = ["tweet", "cronica"]) -> list[dict]:
    """
    Pipeline completo: obtiene últimos partidos y genera contenido.
    """
    print(f"[SPORTS] Obteniendo últimos eventos de liga {league_id}...")
    events = await get_last_events(league_id, limit=1)  # Último partido

    if not events:
        print("[SPORTS] No hay eventos recientes")
        return []

    event = events[0]
    print(f"[SPORTS] Procesando: {event['home']} {event['score_home']}-{event['score_away']} {event['away']}")

    results = []
    for fmt in formats:
        output = await generate_match_content(event, fmt)
        print(f"[SPORTS] {fmt} generado ({output['tokens']} tokens, {output['model']})")
        results.append(output)

        # Guardar en historial
        save_output({
            "briefing": f"[SPORTS] {fmt}: {event['home']} vs {event['away']}",
            "profile_id": "canal_deporte",
            "operator": "sports_pipeline",
            "generated_content": output["content"],
            "human_approved": True,
            "published": False,
            "error": None,
        })

    return results
