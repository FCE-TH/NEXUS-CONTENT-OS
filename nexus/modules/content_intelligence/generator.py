"""
NEXUS — Módulo A: Content Intelligence
Motor de generación textual con enrutamiento multi-LLM (Groq, Claude, OpenAI).
"""
import os
from anthropic import Anthropic
from groq import Groq
from nexus.core.orchestrator.router import detect_task_type, route_task, get_available_providers, TaskType

anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")) if os.getenv("ANTHROPIC_API_KEY") else None
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None

SYSTEM_PROMPT_BASE = """Eres el motor de contenido de NEXUS Content OS.
Tu función es generar contenido de alta calidad adaptado al perfil de marca del operador.
Sé directo, concreto y orientado a resultado. Sin relleno."""


def _call_groq(system: str, briefing: str, model: str = "llama-3.1-70b-versatile") -> dict:
    """Llama a Groq Llama."""
    response = groq_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": briefing},
        ],
        max_tokens=2048,
        temperature=0.7,
    )
    return {
        "content": response.choices[0].message.content,
        "input_tokens": getattr(response.usage, "prompt_tokens", 0),
        "output_tokens": getattr(response.usage, "completion_tokens", 0),
    }


def _call_anthropic(system: str, briefing: str, model: str = "claude-haiku-4-5") -> dict:
    """Llama a Claude."""
    response = anthropic_client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": briefing}],
    )
    return {
        "content": response.content[0].text,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }


def generate_content(
    briefing: str,
    profile_context: str = "",
    rag_context: str = "",
    system_prompt_override: str = "",
    profile_id: str = "",
    prefer_provider: str = None,
) -> dict:
    """
    Genera contenido usando el modelo óptimo según la tarea y disponibilidad.
    
    prefer_provider: "groq" o "anthropic" para forzar proveedor (si está disponible)
    
    Returns:
        dict con 'content', 'model_used', 'task_type', 'provider'
    """
    # Detectar tipo de tarea
    context_length = len(profile_context) + len(rag_context)
    task_type = detect_task_type(briefing, context_length)
    
    # Obtener disponibilidad de APIs
    available = get_available_providers()
    
    # Seleccionar modelo y proveedor
    model = route_task(task_type, available)
    provider = model.split("/")[0]
    
    # Inyectar feedback
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

    # Llamada al LLM según proveedor
    try:
        if provider == "groq" and groq_client:
            result = _call_groq(system, briefing)
            result["provider"] = "groq"
            result["model_used"] = "llama-3.1-70b"
        else:
            # Claude por defecto
            model_name = "claude-sonnet-4-5" if task_type == TaskType.COMPLEX_INSTRUCTIONS else "claude-haiku-4-5"
            result = _call_anthropic(system, briefing, model_name)
            result["provider"] = "anthropic"
            result["model_used"] = model_name
    except Exception as e:
        print(f"Error con {provider}: {e}. Intentando fallback...")
        if provider == "groq" and anthropic_client:
            result = _call_anthropic(system, briefing, "claude-haiku-4-5")
            result["provider"] = "anthropic (fallback de Groq)"
            result["model_used"] = "claude-haiku-4-5"
        else:
            raise

    result["task_type"] = task_type.value
    return result
