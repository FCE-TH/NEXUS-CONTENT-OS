# NEXUS Content OS

Plataforma de producción de contenido multiformato asistida por IA.
7 capas · 5 perfiles · Multi-LLM · ~436€/mes

## Arquitectura

```
Capa 0 — Entradas & Triggers
Capa 1 — Núcleo compartido (Hub)
Capa 2 — Motor LLM multi-proveedor
Capa 3 — Motor Visual (imagen · vídeo · audio)
Capa 4 — Procesamiento A/V & adaptación multiformato
Capa 5 — Bus de distribución multicanal
```

## Stack

- **Orquestación:** LangGraph + LangChain
- **Vector DB:** Qdrant (autohospedado)
- **Base de datos:** PostgreSQL via Supabase (RLS)
- **Eventos:** Redis pub/sub
- **LLMs:** Claude 3.5 Sonnet · GPT-4o · GPT-4o mini · Claude 3 Haiku
- **Visual:** FLUX.1 · LoRA · IP-Adapter · Runway · Kling · ElevenLabs
- **A/V:** Whisper Large-v3 · FFmpeg · PySceneDetect · MoviePy
- **API:** FastAPI

## Setup

```bash
# 1. Copiar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 2. Levantar infraestructura
docker compose up -d

# 3. Instalar dependencias Python
pip install -e ".[dev]"

# 4. Verificar
python -c "from nexus.core.orchestrator.graph import nexus_graph; print('OK')"
```

## Estructura

```
nexus/
├── core/
│   ├── orchestrator/   # LangGraph - flujos de producción
│   ├── knowledge/      # Qdrant - base vectorial
│   ├── profiles/       # PromptLayer - voces de marca
│   └── events/         # Redis - bus de eventos
├── modules/
│   ├── content_intelligence/  # Motor LLM (Módulo A)
│   ├── visual_engine/         # Imagen/vídeo (Módulo B)
│   ├── sports/                # Tiempo real deportivo (Módulo C)
│   ├── archive/               # Archivo audiovisual (Módulo D)
│   └── distribution/          # Publicación multicanal (Módulo E)
└── api/                       # FastAPI endpoints
```

## Perfiles

1. **Canal Deporte** — contenido deportivo en tiempo real
2. **EXTV** — explotación de archivo audiovisual
3. **Abstracto Producciones** — control artístico visual
4. **RANNA** — biblioteca de estilos de marca
5. **Susana Freelance** — gestión multi-cliente

## Roadmap (6 meses · 120K€ · 1.080h)

- **F1 (S1-S4):** Infraestructura + setup → Hito H1
- **F2 (S3-S10):** Orquestación + perfiles → Hito H2, H3
- **F3 (S7-S16):** Motor visual + deportivo + archivo → Hito H4, H5, H6
- **F4 (S13-S20):** Distribución + analítica + loop → Hito H7, H8
- **F5 (S19-S24):** QA + formación + producción → Hito H9, H10
