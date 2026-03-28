"""
NEXUS — Módulo A: Content Intelligence
Motor de generación textual con enrutamiento multi-LLM.
"""
import os
from anthropic import Anthropic
from nexus.core.orchestrator.router import detect_task_type, route_task, TaskType

anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


SYSTEM_PROMPT_BASE = """Eres el motor de contenido de NEXUS Content OS.
Tu función es generar contenido de alta calidad adaptado al perfil de marca del operador.
Sé directo, concreto y orientado a resultado. Sin relleno."""


def generate_content(
    briefing: str,
    profile_context: str = "",
    rag_context: str = "",
    system_prompt_override: str = "",
    profile_id: str = "",
) -> dict:
    """
    Genera contenido usando el modelo óptimo según la tarea.
    
    Returns:
        dict con 'content', 'model_used', 'task_type'
    """
    # Detectar tipo de tarea
    context_length = len(profile_context) + len(rag_context)
    task_type = detect_task_type(briefing, context_length)
    
    # Seleccionar modelo (solo Anthropic disponible por ahora)
    available_providers = ["anthropic"]
    model = route_task(task_type, available_providers)
    
    # Inyectar feedback de mejores contenidos anteriores
    feedback_context = ""
    if profile_id:
        try:
            from nexus.core.feedback.tracker import get_top_performers, format_feedback_context
            top = get_top_performers(profile_id=profile_id, limit=3)
            feedback_context = format_feedback_context(top)
        except Exception:
            pass

    # Construir system prompt
    system = system_prompt_override or SYSTEM_PROMPT_BASE
    if profile_context:
        system += f"\n\n## Perfil de marca:\n{profile_context}"
    if feedback_context:
        system += f"\n\n## {feedback_context}"
    if rag_context:
        system += f"\n\n## Contexto relevante (producciones anteriores):\n{rag_context}"

    # Llamada al modelo
    response = anthropic_client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": briefing}],
    )
    
    return {
        "content": response.content[0].text,
        "model_used": model,
        "task_type": task_type.value,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
