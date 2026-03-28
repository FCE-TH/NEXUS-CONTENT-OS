"""
NEXUS Content OS — UI de producción y revisión
Ejecutar: streamlit run ui.py
"""
import sys, os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from nexus.shared.storage import list_outputs, save_output
from nexus.core.orchestrator.graph import nexus_graph

st.set_page_config(page_title="NEXUS Content OS", page_icon="⚡", layout="wide")

st.title("⚡ NEXUS Content OS")
st.caption("Plataforma de producción de contenido multiformato asistida por IA")

# ── SIDEBAR ──────────────────────────────────────────────
with st.sidebar:
    st.header("Nueva producción")
    profile_id = st.text_input("Perfil", value="squirrel_os")
    operator = st.text_input("Operador", value="Felipe")
    briefing = st.text_area("Briefing", height=150,
        placeholder="Describe qué quieres generar, para quién y en qué tono...")
    generate_btn = st.button("🚀 Generar", type="primary", use_container_width=True)

# ── GENERACIÓN ────────────────────────────────────────────
if generate_btn and briefing:
    with st.spinner("Generando contenido con Claude..."):
        result = nexus_graph.invoke({
            "briefing": briefing,
            "profile_id": profile_id,
            "operator": operator,
            "generated_content": None,
            "human_approved": None,
            "published": False,
            "error": None,
        }, config={"configurable": {"thread_id": f"ui_{profile_id}_{len(briefing)}"}})

    st.success("✓ Contenido generado")
    st.session_state["last_result"] = result

# ── REVISIÓN DEL ÚLTIMO OUTPUT ────────────────────────────
if "last_result" in st.session_state:
    r = st.session_state["last_result"]
    st.subheader("Revisión — aprobación humana (HITL)")
    col1, col2 = st.columns([3, 1])
    with col1:
        content = st.text_area("Contenido generado", value=r["generated_content"], height=300)
    with col2:
        st.metric("Perfil", r["profile_id"])
        st.metric("Publicado", "✓" if r["published"] else "Pendiente")
        if st.button("✅ Aprobar y publicar", type="primary"):
            st.success("Publicado ✓")
            del st.session_state["last_result"]
        if st.button("❌ Rechazar"):
            st.warning("Rechazado")
            del st.session_state["last_result"]

# ── HISTORIAL ─────────────────────────────────────────────
st.divider()
st.subheader("Historial de producciones")

outputs = list_outputs(20)
if not outputs:
    st.info("No hay producciones todavía. Crea la primera desde el panel izquierdo.")
else:
    for o in outputs:
        with st.expander(f"**{o['id']}** · {o['timestamp'][:19]} · {o['profile_id']}"):
            st.caption(f"Operador: {o['operator']} · Publicado: {'✓' if o['published'] else '✗'}")
            st.markdown("**Briefing:**")
            st.text(o["briefing"])
            st.markdown("**Contenido:**")
            st.markdown(o["content"])
