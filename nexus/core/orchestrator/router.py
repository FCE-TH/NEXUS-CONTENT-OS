"""
NEXUS — Enrutador inteligente de modelos LLM
Selecciona el modelo óptimo según la naturaleza de la tarea.
"""
from enum import Enum
from typing import Literal


class TaskType(str, Enum):
    COPY_STANDARD = "copy_standard"        # GPT-4o: copy en castellano
    COMPLEX_INSTRUCTIONS = "complex"       # Claude Sonnet: instrucciones complejas / docs largos
    VOLUME = "volume"                      # GPT-4o mini: resúmenes, variaciones, adaptaciones
    EXTRACTION = "extraction"              # Claude Haiku: extracción de metadatos, clasificación


# Tabla de enrutamiento
ROUTING_TABLE: dict[TaskType, str] = {
    TaskType.COPY_STANDARD:       "gpt-4o",
    TaskType.COMPLEX_INSTRUCTIONS: "claude-sonnet-4-5",
    TaskType.VOLUME:              "gpt-4o-mini",
    TaskType.EXTRACTION:          "claude-haiku-3-5",
}

# Fallback si solo hay API key de Anthropic
ANTHROPIC_FALLBACK: dict[str, str] = {
    "gpt-4o":      "claude-sonnet-4-5",
    "gpt-4o-mini": "claude-haiku-3-5",
}


def route_task(task_type: TaskType, available_providers: list[str]) -> str:
    """Devuelve el modelo correcto según la tarea y los proveedores disponibles."""
    model = ROUTING_TABLE[task_type]
    
    # Si el modelo es de OpenAI y no hay clave, usar fallback Anthropic
    if model.startswith("gpt") and "openai" not in available_providers:
        model = ANTHROPIC_FALLBACK.get(model, "claude-sonnet-4-5")
    
    return model


def detect_task_type(briefing: str, context_length: int = 0) -> TaskType:
    """Infiere el tipo de tarea a partir del briefing."""
    briefing_lower = briefing.lower()
    
    if context_length > 50000:
        return TaskType.COMPLEX_INSTRUCTIONS
    
    extraction_keywords = ["extrae", "clasifica", "identifica", "lista", "metadata", "tags"]
    if any(k in briefing_lower for k in extraction_keywords):
        return TaskType.EXTRACTION
    
    volume_keywords = ["resume", "adapta", "variaciones", "versiones", "reformula"]
    if any(k in briefing_lower for k in volume_keywords):
        return TaskType.VOLUME
    
    complex_keywords = ["campaña completa", "restricciones de marca", "analiza el documento", "revisa todo"]
    if any(k in briefing_lower for k in complex_keywords):
        return TaskType.COMPLEX_INSTRUCTIONS
    
    return TaskType.COPY_STANDARD
