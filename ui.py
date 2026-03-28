"""
NEXUS Content OS — UI de producción y revisión
Ejecutar: streamlit run ui.py
"""
import sys, os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from nexus.shared.storage import list_outputs
from nexus.core.orchestrator.graph import nexus_graph

st.set_page_config(page_title="NEXUS Content OS", page_icon="⚡", layout="wide")

st.title("⚡ NEXUS Content OS")
st.caption("Intake → Generate → Classify → Adapt → HITL → Distribute")

# ── SIDEBAR ──────────────────────────────────────────────
with st.sidebar:
    st.header("Nueva producción")
    
    from nexus.core.profiles.manager import list_profiles
    available_profiles = list_profiles()
    if not available_profiles:
        available_profiles = ["squirrel_os"]
    
    profile_id = st.selectbox("Perfil de marca", options=available_profiles, index=0)
    operator = st.text_input("Operador", value="Felipe")
    briefing = st.text_area("Briefing", height=150,
        placeholder="Describe qué quieres generar, para quién y en qué tono...")
    generate_btn = st.button("🚀 Generar", type="primary", use_container_width=True)

# ── GENERACIÓN ────────────────────────────────────────────
if generate_btn and briefing:
    with st.spinner("Generando, clasificando y adaptando..."):
        result = nexus_graph.invoke({
            "briefing": briefing,
            "profile_id": profile_id,
            "operator": operator,
            "generated_content": None,
            "classification": None,
            "target_platforms": None,
            "adapted_content": None,
            "human_approved": None,
            "published": False,
            "error": None,
        }, config={"configurable": {"thread_id": f"ui_{profile_id}_{len(briefing)}"}})

    st.session_state["last_result"] = result

# ── RESULTADO ─────────────────────────────────────────────
if "last_result" in st.session_state:
    r = st.session_state["last_result"]
    clf = r.get("classification") or {}

    # Métricas de clasificación
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tipo", clf.get("content_type", "-"))
    col2.metric("Calidad", f"{clf.get('quality_score', '-')}/10")
    col3.metric("Urgencia", clf.get("urgency", "-"))
    col4.metric("Canales", len(r.get("target_platforms") or []))

    if clf.get("quality_notes"):
        st.info(f"💡 {clf['quality_notes']}")

    st.divider()

    # Contenido original
    with st.expander("📝 Contenido original", expanded=False):
        st.markdown(r.get("generated_content", ""))

    # Adaptaciones por canal
    adapted = r.get("adapted_content") or {}
    if adapted:
        st.subheader("Versiones por canal — Aprobación HITL")
        platform_icons = {"linkedin": "💼", "x": "🐦", "instagram": "📸", "facebook": "📘", "youtube": "▶️"}

        tabs = st.tabs([f"{platform_icons.get(p, '📢')} {p.upper()}" for p in adapted.keys()])
        for tab, (platform, content) in zip(tabs, adapted.items()):
            with tab:
                edited = st.text_area(f"Contenido {platform}", value=content, height=250, key=f"edit_{platform}")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button(f"✅ Aprobar {platform}", key=f"approve_{platform}", type="primary"):
                        st.success(f"✓ {platform} aprobado para publicación")
                with col_b:
                    st.caption(f"{len(content)} caracteres")

    st.divider()
    if st.button("🗑️ Limpiar y nueva producción"):
        del st.session_state["last_result"]
        st.rerun()

# ── HISTORIAL ─────────────────────────────────────────────
st.subheader("Historial de producciones")
outputs = list_outputs(10)
if not outputs:
    st.info("No hay producciones todavía.")
else:
    for o in outputs:
        with st.expander(f"**{o['id']}** · {o['timestamp'][:19]} · {o['profile_id']}"):
            st.caption(f"Operador: {o['operator']} · Publicado: {'✓' if o['published'] else '✗'}")
            st.text(f"Briefing: {o['briefing'][:100]}")
            st.markdown(o["content"])
