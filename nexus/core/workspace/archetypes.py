"""
NEXUS — Arquetipos de negocio
Define qué es cada tipo de workspace, qué módulos activa y cómo se configura.

4 arquetipos:
  PUBLISHER   — medios, broadcasters, producción propia a escala
  PRODUCTORA  — casas de producción creativa, ejecutan para anunciantes
  AGENCIA     — gestionan contenido/estrategia de múltiples clientes anunciantes
  ANUNCIANTE  — la marca gestionando su propio contenido, sin intermediario
"""

from enum import Enum
from dataclasses import dataclass, field


class ArchetypeID(str, Enum):
    PUBLISHER   = "publisher"
    PRODUCTORA  = "productora"
    AGENCIA     = "agencia"
    ANUNCIANTE  = "anunciante"


@dataclass
class Archetype:
    id: ArchetypeID
    label: str
    description: str
    can_manage_clients: bool        # Puede gestionar proyectos de anunciantes externos
    modules: list[str]              # Módulos activos por defecto
    default_channels: list[str]     # Canales de distribución principales
    max_brand_profiles: int         # Perfiles de marca simultáneos
    primary_workflow: str           # Flujo principal de trabajo
    typical_volume: str             # Volumen de producción típico
    examples: list[str]             # Casos de uso de referencia


ARCHETYPES: dict[ArchetypeID, Archetype] = {

    ArchetypeID.PUBLISHER: Archetype(
        id=ArchetypeID.PUBLISHER,
        label="Publisher / Medio",
        description="Canal de contenido, medio digital o broadcaster. Produce a escala "
                    "con identidad editorial propia. El tiempo real es clave.",
        can_manage_clients=False,
        modules=[
            "content_intelligence",
            "visual_engine",
            "sports_realtime",
            "archive_intelligence",
            "distribution",
            "analytics",
        ],
        default_channels=["x", "instagram", "youtube", "facebook", "web"],
        max_brand_profiles=3,
        primary_workflow="realtime_sports",
        typical_volume="alto",
        examples=["Canal Deporte", "EXTV", "medios digitales", "broadcasters"],
    ),

    ArchetypeID.PRODUCTORA: Archetype(
        id=ArchetypeID.PRODUCTORA,
        label="Productora",
        description="Casa de producción creativa. Ejecuta proyectos de producción "
                    "(vídeo, foto, piezas creativas) para clientes anunciantes. "
                    "El control artístico y la coherencia visual entre piezas es clave.",
        can_manage_clients=True,
        modules=[
            "content_intelligence",
            "visual_engine",
            "archive_intelligence",
            "distribution",
            "analytics",
        ],
        default_channels=["instagram", "linkedin", "youtube", "web"],
        max_brand_profiles=10,
        primary_workflow="visual_production",
        typical_volume="medio",
        examples=["Abstracto Producciones", "productoras audiovisuales", "estudios creativos"],
    ),

    ArchetypeID.AGENCIA: Archetype(
        id=ArchetypeID.AGENCIA,
        label="Agencia",
        description="Agencia de contenidos o marketing que gestiona la estrategia "
                    "y producción de múltiples clientes anunciantes. "
                    "La escala multicliente y la separación de voces de marca es clave.",
        can_manage_clients=True,
        modules=[
            "content_intelligence",
            "visual_engine",
            "distribution",
            "analytics",
        ],
        default_channels=["linkedin", "instagram", "x", "facebook"],
        max_brand_profiles=25,
        primary_workflow="multi_client_standard",
        typical_volume="alto",
        examples=["RANNA", "Susana Freelance", "agencias de contenidos", "consultoras de marketing"],
    ),

    ArchetypeID.ANUNCIANTE: Archetype(
        id=ArchetypeID.ANUNCIANTE,
        label="Anunciante / Marca",
        description="Marca o empresa gestionando su propio contenido sin intermediario. "
                    "Una sola identidad de marca, varios canales. "
                    "La consistencia y el calendario son clave.",
        can_manage_clients=False,
        modules=[
            "content_intelligence",
            "visual_engine",
            "distribution",
            "analytics",
        ],
        default_channels=["linkedin", "instagram", "x"],
        max_brand_profiles=2,
        primary_workflow="standard",
        typical_volume="medio",
        examples=["marca D2C", "empresa B2B con equipo de contenidos propio", "personal brand"],
    ),
}


def get_archetype(archetype_id: str) -> Archetype:
    return ARCHETYPES[ArchetypeID(archetype_id)]


def all_archetypes() -> list[Archetype]:
    return list(ARCHETYPES.values())


def archetype_options_for_ui() -> list[tuple[str, str]]:
    """Para selectbox en UI: lista de (id, label)."""
    return [(a.id.value, a.label) for a in ARCHETYPES.values()]
