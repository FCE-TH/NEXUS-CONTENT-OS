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
    classification: dict | None
    target_platforms: list | None
    adapted_content: dict | None
    human_approved: bool | None
    published: bool
    error: str | None


def intake_node(state: NexusState) -> NexusState:
    """Capa 0: Recibe el briefing y valida el perfil."""
    print(f"[INTAKE] Perfil: {state['profile_id']} | Operador: {state['operator']}")
    return state


def generate_node(state: NexusState) -> NexusState:
    """Capa 2: Genera contenido vía LLM (enrutamiento inteligente)."""
    from dotenv import load_dotenv
    load_dotenv()
    from nexus.modules.content_intelligence.generator import generate_content
    from nexus.core.profiles.manager import get_profile, profile_to_context
    from nexus.core.workspace.workspace import get_workspace, workspace_has_module
    
    # Obtener contexto del workspace
    ws = get_workspace(state.get("profile_id", ""))
    profile = get_profile(state.get("profile_id", ""))
    profile_context = profile_to_context(profile) if profile else ""
    
    if profile_context:
        print(f"[GENERATE] Perfil cargado: {profile.get('name')}")

    print(f"[GENERATE] Briefing: {state['briefing'][:60]}...")
    
    # Si el workspace tiene módulo sports y el briefing es sobre deportes, usar LiveScore
    rag_context = ""
    if ws and workspace_has_module(ws['workspace_id'], "sports_realtime"):
        briefing_lower = state['briefing'].lower()
        sports_keywords = ['partido', 'gol', 'madrid', 'barcelona', 'laliga', 'champions', 'resultado', 'baloncesto', 'tenis']
        if any(k in briefing_lower for k in sports_keywords):
            try:
                from nexus.modules.sports.livescore import get_live_matches, get_laliga_matches
                # Intentar partidos en vivo primero, fallback a LaLiga reciente
                matches = get_live_matches() or get_laliga_matches()
                if matches:
                    # Convertir lista de dicts a texto legible para el LLM
                    matches_text = "\n".join([
                        f"• {m['home']} {m['score_home']}-{m['score_away']} {m['away']} ({m['league']})"
                        for m in matches[:5]
                    ])
                    rag_context = f"## Últimos resultados/partidos en directo:\n{matches_text}"
                    print(f"[GENERATE] ✓ Datos deportivos cargados via LiveScore ({len(matches)} partidos)")
            except Exception as e:
                print(f"[GENERATE] ⚠️ LiveScore no disponible: {e}")
    
    result = generate_content(
        briefing=state["briefing"],
        profile_context=profile_context,
        rag_context=rag_context,
        profile_id=state.get("profile_id", ""),
    )
    print(f"[GENERATE] Modelo: {result['model_used']} | Tarea: {result['task_type']} | Tokens: {result['output_tokens']}")
    state["generated_content"] = result["content"]
    return state


def classify_node(state: NexusState) -> NexusState:
    """Clasifica el contenido y determina canales de distribución."""
    from nexus.core.orchestrator.classifier import classify_content, route_to_platforms, format_classification_summary
    
    classification = classify_content(
        content=state["generated_content"],
        profile_id=state.get("profile_id", ""),
        briefing=state.get("briefing", ""),
    )
    platforms = route_to_platforms(classification)
    
    print(f"[CLASSIFY] {format_classification_summary(classification)}")
    
    state["classification"] = classification
    state["target_platforms"] = platforms
    return state


def adapt_node(state: NexusState) -> NexusState:
    """Adapta el contenido para cada canal según el clasificador."""
    from nexus.core.orchestrator.adapter import adapt_all_platforms
    from nexus.core.profiles.manager import get_profile, profile_to_context

    profile = get_profile(state.get("profile_id", ""))
    profile_context = profile_to_context(profile) if profile else ""

    adapted = adapt_all_platforms(
        original_content=state["generated_content"],
        classification=state["classification"],
        profile_context=profile_context,
    )
    state["adapted_content"] = adapted
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
    from nexus.shared.storage import save_output
    print(f"[DISTRIBUTE] Publicando contenido aprobado...")
    state["published"] = True
    pid = save_output(state)
    print(f"[DISTRIBUTE] Output guardado → ID: {pid}")
    return state


def build_graph() -> StateGraph:
    """Construye y compila el grafo principal de NEXUS."""
    graph = StateGraph(NexusState)

    graph.add_node("intake", intake_node)
    graph.add_node("generate", generate_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("distribute", distribute_node)

    graph.set_entry_point("intake")
    graph.add_node("classify", classify_node)
    graph.add_node("adapt", adapt_node)

    graph.add_edge("intake", "generate")
    graph.add_edge("generate", "classify")
    graph.add_edge("classify", "adapt")
    graph.add_edge("adapt", "human_review")
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
