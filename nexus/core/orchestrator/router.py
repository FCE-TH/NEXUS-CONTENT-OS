"""
NEXUS — Enrutador inteligente de modelos LLM
Selecciona el modelo óptimo según la naturaleza de la tarea y disponibilidad de APIs.

Preferencia: Groq Llama 3.1 70B (gratis) → Claude Haiku (barato) → Claude Sonnet (mejor)
"""
from enum import Enum
from typing import Literal


class TaskType(str, Enum):
    COPY_STANDARD = "copy_standard"        # Tarea estándar: Groq o Haiku
    COMPLEX_INSTRUCTIONS = "complex"       # Instrucciones complejas: Sonnet
    VOLUME = "volume"                      # Alto volumen: Groq o Haiku-mini
    EXTRACTION = "extraction"              # Clasificación: Groq o Haiku
    SPANISH_FIRST = "spanish_first"        # Español crítico: Haiku o Sonnet


# Tabla de enrutamiento (optimizada para coste + calidad)
# groq/llama-3.1-70b:  gratis (hasta límite) — muy rápido, buen español
# claude-haiku-4-5:    ~$0.25/M input       — fallback si Groq falla
# claude-sonnet-4-5:   ~$3/M input          — solo tareas muy complejas
ROUTING_TABLE: dict[TaskType, list[str]] = {
    TaskType.COPY_STANDARD:        ["groq/llama-3.1-70b", "claude-haiku-4-5"],
    TaskType.COMPLEX_INSTRUCTIONS: ["claude-sonnet-4-5", "groq/llama-3.1-70b"],
    TaskType.VOLUME:               ["groq/llama-3.1-70b", "claude-haiku-4-5"],
    TaskType.EXTRACTION:           ["groq/llama-3.1-70b", "claude-haiku-4-5"],
    TaskType.SPANISH_FIRST:        ["claude-haiku-4-5", "groq/llama-3.1-70b"],
}


def route_task(task_type: TaskType, available_providers: dict[str, bool]) -> str:
    """
    Devuelve el modelo correcto según la tarea y disponibilidad de APIs.
    
    available_providers: {
        "groq": True/False,
        "anthropic": True/False,
        "openai": True/False,
    }
    """
    candidates = ROUTING_TABLE[task_type]
    
    for model in candidates:
        if model.startswith("groq") and available_providers.get("groq", False):
            return model
        elif model.startswith("claude") and available_providers.get("anthropic", False):
            return model
        elif model.startswith("gpt") and available_providers.get("openai", False):
            return model
    
    # Fallback: devuelve el primero disponible
    for model in candidates:
        provider = model.split("/")[0]
        if available_providers.get(provider, False):
            return model
    
    # Si nada está disponible, devuelve Claude Haiku (esperamos que esté siempre disponible)
    return "claude-haiku-4-5"


def detect_task_type(briefing: str, context_length: int = 0) -> TaskType:
    """Infiere el tipo de tarea a partir del briefing."""
    briefing_lower = briefing.lower()
    
    # Tareas complejas
    if context_length > 50000:
        return TaskType.COMPLEX_INSTRUCTIONS
    
    complex_keywords = [
        "campaña completa", "restricciones de marca", "analiza el documento", 
        "revisa todo", "instrucciones muy estrictas", "múltiples restricciones"
    ]
    if any(k in briefing_lower for k in complex_keywords):
        return TaskType.COMPLEX_INSTRUCTIONS
    
    # Tareas de extracción
    extraction_keywords = ["extrae", "clasifica", "identifica", "lista", "metadata", "tags", "estructura"]
    if any(k in briefing_lower for k in extraction_keywords):
        return TaskType.EXTRACTION
    
    # Tareas de volumen
    volume_keywords = ["resume", "adapta", "variaciones", "versiones", "reformula", "múltiples versiones"]
    if any(k in briefing_lower for k in volume_keywords):
        return TaskType.VOLUME
    
    # Spanish-first: cuando la precisión en español es crítica
    spanish_keywords = ["castellano", "español muy preciso", "sutileza del español", "traducción"]
    if any(k in briefing_lower for k in spanish_keywords):
        return TaskType.SPANISH_FIRST
    
    # Default: copy estándar
    return TaskType.COPY_STANDARD


def get_available_providers() -> dict[str, bool]:
    """Verifica qué APIs están configuradas."""
    import os
    return {
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
    }
