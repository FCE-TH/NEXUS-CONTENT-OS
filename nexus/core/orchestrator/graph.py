"""
NEXUS — Orquestador central (LangGraph)
Flujo básico end-to-end: Briefing → LLM → Revisión humana → Distribución
"""
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


class NexusState(TypedDict):
    """Estado compartido del flujo de producción."""
    briefing: str
    profile_id: str
    operator: str
    generated_content: str | None
    human_approved: bool | None
    published: bool
    error: str | None


def intake_node(state: NexusState) -> NexusState:
    """Capa 0: Recibe el briefing y valida el perfil."""
    print(f"[INTAKE] Perfil: {state['profile_id']} | Operador: {state['operator']}")
    return state


def generate_node(state: NexusState) -> NexusState:
    """Capa 2: Genera contenido vía LLM (enrutamiento inteligente)."""
    # TODO: Conectar con motor LLM multi-proveedor
    print(f"[GENERATE] Generando contenido para: {state['briefing'][:50]}...")
    state["generated_content"] = f"[PLACEHOLDER] Contenido generado para: {state['briefing']}"
    return state


def human_review_node(state: NexusState) -> NexusState:
    """HITL: Checkpoint de aprobación humana antes de publicar."""
    print(f"[REVIEW] Esperando aprobación humana...")
    # En producción: notificación a Streamlit UI
    # En desarrollo: auto-aprueba
    state["human_approved"] = True
    return state


def route_after_review(state: NexusState) -> Literal["distribute", "end"]:
    """Router: decide si publicar o terminar según aprobación."""
    if state.get("human_approved"):
        return "distribute"
    return "end"


def distribute_node(state: NexusState) -> NexusState:
    """Capa 5: Publica en los canales configurados para el perfil."""
    print(f"[DISTRIBUTE] Publicando contenido aprobado...")
    state["published"] = True
    return state


def build_graph() -> StateGraph:
    """Construye y compila el grafo principal de NEXUS."""
    graph = StateGraph(NexusState)

    graph.add_node("intake", intake_node)
    graph.add_node("generate", generate_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("distribute", distribute_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "generate")
    graph.add_edge("generate", "human_review")
    graph.add_conditional_edges(
        "human_review",
        route_after_review,
        {"distribute": "distribute", "end": END}
    )
    graph.add_edge("distribute", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# Instancia global del grafo
nexus_graph = build_graph()
