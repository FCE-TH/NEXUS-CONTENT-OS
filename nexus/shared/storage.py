"""
NEXUS — Almacenamiento de outputs
Guarda cada producción en JSON para trazabilidad.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path

OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)


def save_output(state: dict, metadata: dict = {}) -> str:
    """Guarda el output de una producción y devuelve el ID."""
    production_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()

    record = {
        "id": production_id,
        "timestamp": timestamp,
        "profile_id": state.get("profile_id"),
        "operator": state.get("operator"),
        "briefing": state.get("briefing"),
        "content": state.get("generated_content"),
        "approved": state.get("human_approved"),
        "published": state.get("published"),
        **metadata,
    }

    output_file = OUTPUTS_DIR / f"{timestamp[:10]}_{production_id}.json"
    output_file.write_text(json.dumps(record, ensure_ascii=False, indent=2))

    return production_id


def list_outputs(limit: int = 20) -> list[dict]:
    """Lista los últimos outputs."""
    files = sorted(OUTPUTS_DIR.glob("*.json"), reverse=True)[:limit]
    return [json.loads(f.read_text()) for f in files]
