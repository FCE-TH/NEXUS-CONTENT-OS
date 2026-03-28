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

    # Programación de publicaciones
    st.divider()
    with st.expander("🗓️ Programar publicación"):
        from nexus.core.scheduler.scheduler import schedule_post, next_optimal_slot, OPTIMAL_WINDOWS
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("Europe/Madrid")
        sched_platform = st.selectbox("Plataforma", list(adapted.keys()) if adapted else ["linkedin"], key="sched_platform")
        
        next_slot = next_optimal_slot(sched_platform)
        st.caption(f"⏰ Próximo slot óptimo: **{next_slot.strftime('%d/%m/%Y a las %H:%M')}**")

        use_optimal = st.checkbox("Usar slot óptimo automático", value=True)
        if not use_optimal:
            custom_date = st.date_input("Fecha", value=next_slot.date())
            custom_time = st.time_input("Hora", value=next_slot.time())

        if st.button("📅 Programar", type="secondary"):
            import uuid
            content_to_schedule = adapted.get(sched_platform, r.get("generated_content", ""))
            publish_at = next_slot if use_optimal else datetime(
                custom_date.year, custom_date.month, custom_date.day,
                custom_time.hour, custom_time.minute, tzinfo=tz
            )
            result_sched = schedule_post(
                content=content_to_schedule,
                platform=sched_platform,
                profile_id=r.get("profile_id", ""),
                output_id=str(uuid.uuid4())[:8],
                publish_at=publish_at,
            )
            st.success(f"✓ Programado para {result_sched['publish_at_human']} — {result_sched['window_label']}")

    # Feedback de métricas
    st.divider()
    with st.expander("📊 Registrar métricas de rendimiento (cierra el bucle)"):
        st.caption("Introduce los resultados reales de una publicación para que NEXUS aprenda")
        fb_platform = st.selectbox("Plataforma", ["linkedin", "x", "instagram"])
        col_v, col_l, col_s, col_c = st.columns(4)
        fb_views = col_v.number_input("Views", min_value=0, value=0)
        fb_likes = col_l.number_input("Likes", min_value=0, value=0)
        fb_shares = col_s.number_input("Shares", min_value=0, value=0)
        fb_clicks = col_c.number_input("Clicks", min_value=0, value=0)
        fb_engagement = st.slider("Engagement rate", 0.0, 1.0, 0.05, 0.01)

        if st.button("💾 Guardar métricas", type="secondary"):
            from nexus.core.feedback.tracker import record_performance
            import uuid
            record_performance(
                output_id=str(uuid.uuid4())[:8],
                profile_id=r.get("profile_id", ""),
                platform=fb_platform,
                content=r.get("generated_content", ""),
                briefing=r.get("briefing", ""),
                content_type=clf.get("content_type", ""),
                metrics={
                    "views": fb_views, "likes": fb_likes,
                    "shares": fb_shares, "clicks": fb_clicks,
                    "engagement_rate": fb_engagement,
                },
            )
            st.success("✓ Métricas guardadas — NEXUS aprenderá de este contenido")

    if st.button("🗑️ Limpiar y nueva producción"):
        del st.session_state["last_result"]
        st.rerun()

# ── COLA DE PUBLICACIONES ────────────────────────────────
from nexus.core.scheduler.scheduler import get_pending_posts
pending = get_pending_posts(10)
if pending:
    st.subheader(f"🗓️ Cola de publicaciones ({len(pending)} pendientes)")
    for p in pending:
        col_t, col_p, col_pr, col_c = st.columns([2, 2, 2, 1])
        col_t.write(f"⏰ {p['publish_at_human']}")
        col_p.write(f"📢 {p['platform'].upper()}")
        col_pr.write(f"👤 {p['profile_id']}")
        col_c.button("❌", key=f"cancel_{p['output_id']}_{p['platform']}")
    st.divider()

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
