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
from nexus.core.workspace.archetypes import all_archetypes, get_archetype
from nexus.core.workspace.workspace import create_workspace, get_workspace, list_workspaces

st.set_page_config(page_title="NEXUS Content OS", page_icon="⚡", layout="wide")

# ── GESTIÓN DE WORKSPACE ACTIVO ───────────────────────────
if "active_workspace" not in st.session_state:
    st.session_state["active_workspace"] = None

workspaces = list_workspaces()

# ── SIDEBAR ──────────────────────────────────────────────
with st.sidebar:
    st.title("⚡ NEXUS")

    # Selector de workspace
    ws_options = {ws["workspace_id"]: ws["name"] for ws in workspaces}
    ws_options["__new__"] = "＋ Nuevo workspace"
    selected_ws_id = st.selectbox(
        "Workspace",
        options=list(ws_options.keys()),
        format_func=lambda x: ws_options[x],
        key="ws_selector",
    )

    if selected_ws_id != "__new__":
        ws = get_workspace(selected_ws_id)
        st.session_state["active_workspace"] = ws
        archetype = get_archetype(ws["archetype"])
        st.caption(f"**{archetype.label}**")
        st.caption(f"Módulos: {len(ws['active_modules'])} activos")
        st.divider()

    # Formulario de producción
    if st.session_state["active_workspace"]:
        ws = st.session_state["active_workspace"]

        st.header("Nueva producción")

        # Selector de marca cliente (solo Agencia y Productora)
        selected_brand = None
        if ws["archetype"] in ("agencia", "productora"):
            from nexus.core.workspace.client_brands import list_client_brands
            brands = list_client_brands(ws["workspace_id"])
            if brands:
                brand_options = {"__ws__": f"— {ws['name']} (propio) —"}
                brand_options.update({b["brand_id"]: b["name"] for b in brands})
                selected_brand_id = st.selectbox(
                    "Marca cliente",
                    options=list(brand_options.keys()),
                    format_func=lambda x: brand_options[x],
                )
                if selected_brand_id != "__ws__":
                    selected_brand = next((b for b in brands if b["brand_id"] == selected_brand_id), None)
            else:
                st.caption("Sin marcas cliente — añade una en ⚙️ Marcas")

        operator = st.text_input("Operador", value="Felipe")
        briefing = st.text_area("Briefing", height=150,
            placeholder="Describe qué quieres generar, para quién y en qué tono...")
        generate_btn = st.button("🚀 Generar", type="primary", use_container_width=True)
    else:
        generate_btn = False
        briefing = ""

# ── NUEVO WORKSPACE (onboarding) ─────────────────────────
if selected_ws_id == "__new__":
    st.title("⚡ Nuevo Workspace")
    st.caption("El arquetipo configura automáticamente los módulos, canales y flujos de trabajo.")

    archetypes = all_archetypes()
    cols = st.columns(2)
    selected_archetype_id = None

    for i, arch in enumerate(archetypes):
        with cols[i % 2]:
            icon = {"publisher": "📡", "productora": "🎬", "agencia": "🏢", "anunciante": "🏷️"}
            with st.container(border=True):
                st.subheader(f"{icon.get(arch.id.value, '⚡')} {arch.label}")
                st.caption(arch.description)
                st.caption(f"Clientes externos: {'✓' if arch.can_manage_clients else '✗'} · Perfiles: hasta {arch.max_brand_profiles}")
                st.caption(f"Módulos: {', '.join(arch.modules[:3])}{'...' if len(arch.modules) > 3 else ''}")
                if st.button(f"Elegir {arch.label}", key=f"arch_{arch.id.value}"):
                    st.session_state["onboarding_archetype"] = arch.id.value

    if "onboarding_archetype" in st.session_state:
        arch = get_archetype(st.session_state["onboarding_archetype"])
        st.divider()
        st.subheader(f"Configurar workspace — {arch.label}")

        with st.form("new_workspace_form"):
            ws_name = st.text_input("Nombre de la empresa / workspace")
            ws_slug = st.text_input("ID único (sin espacios, solo letras y guiones)", 
                                     placeholder="ej: canal-deporte, ranna-agency")
            tone = st.text_area("Tono de comunicación",
                placeholder="Ej: Directo, con datos, sin florituras. Habla de igual a igual.")
            target_audience = st.text_input("Audiencia principal",
                placeholder="Ej: Profesionales del marketing digital 25-45 años")
            beliefs = st.text_area("Valores / pilares de marca (uno por línea)")

            st.caption(f"**Canales por defecto:** {', '.join(arch.default_channels)}")
            st.caption(f"**Módulos activos:** {', '.join(arch.modules)}")

            submitted = st.form_submit_button("✅ Crear workspace", type="primary")
            if submitted and ws_name and ws_slug:
                create_workspace(
                    workspace_id=ws_slug,
                    name=ws_name,
                    archetype_id=st.session_state["onboarding_archetype"],
                    company_context={
                        "tone": tone,
                        "target_audience": target_audience,
                        "beliefs": [b.strip() for b in beliefs.split("\n") if b.strip()],
                    },
                )
                del st.session_state["onboarding_archetype"]
                st.success(f"✓ Workspace '{ws_name}' creado. Selecciónalo en el panel izquierdo.")
                st.rerun()
    st.stop()

# ── CABECERA ─────────────────────────────────────────────
ws = st.session_state["active_workspace"]
archetype = get_archetype(ws["archetype"])
icon = {"publisher": "📡", "productora": "🎬", "agencia": "🏢", "anunciante": "🏷️"}
st.title(f"{icon.get(ws['archetype'], '⚡')} {ws['name']}")
st.caption(f"{archetype.label}  ·  {', '.join(ws['default_channels'])}")

# ── GENERACIÓN ────────────────────────────────────────────
if generate_btn and briefing:
    # Si hay marca cliente seleccionada, usar su ID como perfil
    active_profile = selected_brand["brand_id"] if selected_brand else ws["workspace_id"]
    with st.spinner("Generando, clasificando y adaptando..."):
        result = nexus_graph.invoke({
            "briefing": briefing,
            "profile_id": active_profile,
            "operator": operator,
            "generated_content": None,
            "classification": None,
            "target_platforms": None,
            "adapted_content": None,
            "human_approved": None,
            "published": False,
            "error": None,
        }, config={"configurable": {"thread_id": f"ui_{ws['workspace_id']}_{len(briefing)}"}})

    st.session_state["last_result"] = result

# ── RESULTADO ─────────────────────────────────────────────
if "last_result" in st.session_state:
    r = st.session_state["last_result"]
    clf = r.get("classification") or {}

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tipo", clf.get("content_type", "-"))
    col2.metric("Calidad", f"{clf.get('quality_score', '-')}/10")
    col3.metric("Urgencia", clf.get("urgency", "-"))
    col4.metric("Canales", len(r.get("target_platforms") or []))

    if clf.get("quality_notes"):
        st.info(f"💡 {clf['quality_notes']}")

    st.divider()

    with st.expander("📝 Contenido original", expanded=False):
        st.markdown(r.get("generated_content", ""))

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

    # Programar publicación
    st.divider()
    with st.expander("🗓️ Programar publicación"):
        from nexus.core.scheduler.scheduler import schedule_post, next_optimal_slot
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("Europe/Madrid")
        sched_platform = st.selectbox("Plataforma", list(adapted.keys()) if adapted else ws["default_channels"], key="sched_platform")
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
                profile_id=ws["workspace_id"],
                output_id=str(uuid.uuid4())[:8],
                publish_at=publish_at,
            )
            st.success(f"✓ Programado para {result_sched['publish_at_human']} — {result_sched['window_label']}")

    # Feedback de métricas
    with st.expander("📊 Registrar métricas de rendimiento"):
        from nexus.core.feedback.tracker import record_performance
        fb_platform = st.selectbox("Plataforma", ["linkedin", "x", "instagram"], key="fb_platform")
        col_v, col_l, col_s, col_c = st.columns(4)
        fb_views = col_v.number_input("Views", min_value=0, value=0)
        fb_likes = col_l.number_input("Likes", min_value=0, value=0)
        fb_shares = col_s.number_input("Shares", min_value=0, value=0)
        fb_clicks = col_c.number_input("Clicks", min_value=0, value=0)
        fb_engagement = st.slider("Engagement rate", 0.0, 1.0, 0.05, 0.01)

        if st.button("💾 Guardar métricas", type="secondary"):
            import uuid
            record_performance(
                output_id=str(uuid.uuid4())[:8],
                profile_id=ws["workspace_id"],
                platform=fb_platform,
                content=r.get("generated_content", ""),
                briefing=r.get("briefing", ""),
                content_type=clf.get("content_type", ""),
                metrics={"views": fb_views, "likes": fb_likes, "shares": fb_shares,
                         "clicks": fb_clicks, "engagement_rate": fb_engagement},
            )
            st.success("✓ Métricas guardadas")

    st.divider()
    if st.button("🗑️ Limpiar y nueva producción"):
        del st.session_state["last_result"]
        st.rerun()

# ── MARCAS CLIENTE (Agencia / Productora) ────────────────
if ws["archetype"] in ("agencia", "productora"):
    from nexus.core.workspace.client_brands import list_client_brands, add_client_brand
    with st.expander("⚙️ Marcas cliente"):
        brands = list_client_brands(ws["workspace_id"])
        if brands:
            for b in brands:
                st.write(f"**{b['name']}** · {b.get('sector','')} · {', '.join(b.get('channels',[]))}")
        else:
            st.info("No hay marcas cliente todavía.")

        st.subheader("Añadir marca cliente")
        with st.form("add_brand_form"):
            b_name = st.text_input("Nombre de la marca")
            b_id = st.text_input("ID único (slug)", placeholder="ej: marca-x")
            b_sector = st.text_input("Sector", placeholder="Ej: Moda, Tech, Alimentación")
            b_tone = st.text_area("Tono de comunicación")
            b_audience = st.text_input("Audiencia objetivo")
            b_channels = st.multiselect("Canales principales", ["linkedin","x","instagram","facebook","youtube","tiktok"], default=["instagram","linkedin"])
            b_never = st.text_input("Nunca decir (separado por comas)")
            if st.form_submit_button("➕ Añadir marca", type="primary"):
                if b_name and b_id:
                    add_client_brand(
                        workspace_id=ws["workspace_id"],
                        brand_id=b_id,
                        name=b_name,
                        sector=b_sector,
                        tone=b_tone,
                        target_audience=b_audience,
                        channels=b_channels,
                        never_say=[x.strip() for x in b_never.split(",") if x.strip()],
                    )
                    st.success(f"✓ Marca '{b_name}' añadida")
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
