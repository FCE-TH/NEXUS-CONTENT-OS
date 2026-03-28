#!/usr/bin/env python3
"""
NEXUS — Visor de outputs por terminal
Uso: python view_outputs.py [--limit N]
"""
import sys
sys.path.insert(0, '.')

from nexus.shared.storage import list_outputs

limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == '--limit' else 5

outputs = list_outputs(limit)

if not outputs:
    print("No hay outputs todavía.")
    sys.exit(0)

for o in outputs:
    print(f"\n{'='*60}")
    print(f"ID: {o['id']}  |  {o['timestamp'][:19]}  |  Perfil: {o['profile_id']}")
    print(f"Operador: {o['operator']}")
    print(f"Briefing: {o['briefing'][:80]}...")
    print(f"Publicado: {'✓' if o['published'] else '✗'}  |  Aprobado: {'✓' if o['approved'] else '✗'}")
    print(f"\n--- CONTENIDO ---")
    print(o['content'])
