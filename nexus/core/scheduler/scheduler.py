"""
NEXUS — Scheduler de publicaciones
Programa contenido para publicarse en las horas óptimas por plataforma.
Usa Redis como cola de trabajos pendientes.
"""
import os
import json
import redis
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
QUEUE_KEY = "nexus:scheduler:queue"
TIMEZONE = ZoneInfo("Europe/Madrid")

# Ventanas óptimas de publicación por plataforma (hora local Madrid)
OPTIMAL_WINDOWS = {
    "linkedin": [
        {"hour": 8, "minute": 30, "label": "Mañana profesional"},
        {"hour": 12, "minute": 0,  "label": "Pausa del mediodía"},
        {"hour": 17, "minute": 30, "label": "Cierre de jornada"},
    ],
    "x": [
        {"hour": 9,  "minute": 0,  "label": "Inicio del día"},
        {"hour": 13, "minute": 0,  "label": "Mediodía"},
        {"hour": 20, "minute": 0,  "label": "Noche"},
        {"hour": 22, "minute": 0,  "label": "Prime time"},
    ],
    "instagram": [
        {"hour": 9,  "minute": 0,  "label": "Mañana"},
        {"hour": 12, "minute": 30, "label": "Mediodía"},
        {"hour": 19, "minute": 0,  "label": "Tarde"},
        {"hour": 21, "minute": 0,  "label": "Noche"},
    ],
    "facebook": [
        {"hour": 9,  "minute": 0,  "label": "Mañana"},
        {"hour": 13, "minute": 0,  "label": "Mediodía"},
        {"hour": 19, "minute": 0,  "label": "Tarde"},
    ],
}

# Días óptimos por plataforma (0=lunes, 6=domingo)
OPTIMAL_DAYS = {
    "linkedin": [0, 1, 2, 3, 4],   # Lunes a viernes
    "x":        [0, 1, 2, 3, 4, 5, 6],  # Todos los días
    "instagram": [0, 2, 3, 4, 6],  # Lunes, miércoles, jueves, viernes, domingo
    "facebook":  [0, 2, 4],        # Lunes, miércoles, viernes
}


def _get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


def next_optimal_slot(platform: str, from_dt: datetime = None) -> datetime:
    """
    Calcula el próximo slot óptimo de publicación para una plataforma.
    """
    now = from_dt or datetime.now(TIMEZONE)
    windows = OPTIMAL_WINDOWS.get(platform, OPTIMAL_WINDOWS["x"])
    optimal_days = OPTIMAL_DAYS.get(platform, list(range(7)))

    # Buscar en los próximos 7 días
    for day_offset in range(8):
        candidate_date = now + timedelta(days=day_offset)
        
        if candidate_date.weekday() not in optimal_days:
            continue

        for window in windows:
            candidate = candidate_date.replace(
                hour=window["hour"],
                minute=window["minute"],
                second=0,
                microsecond=0,
            )
            # Debe ser al menos 5 minutos en el futuro
            if candidate > now + timedelta(minutes=5):
                return candidate

    # Fallback: 1 hora desde ahora
    return now + timedelta(hours=1)


def schedule_post(
    content: str,
    platform: str,
    profile_id: str,
    output_id: str,
    publish_at: datetime = None,
) -> dict:
    """
    Añade un post a la cola de publicación programada.
    Si no se especifica publish_at, usa el próximo slot óptimo.
    """
    r = _get_redis()
    
    slot = publish_at or next_optimal_slot(platform)
    
    job = {
        "output_id": output_id,
        "profile_id": profile_id,
        "platform": platform,
        "content": content,
        "publish_at": slot.isoformat(),
        "status": "pending",
        "created_at": datetime.now(TIMEZONE).isoformat(),
    }
    
    # Guardar en Redis sorted set (score = timestamp para ordenar por fecha)
    r.zadd(QUEUE_KEY, {json.dumps(job): slot.timestamp()})
    
    return {
        "scheduled": True,
        "platform": platform,
        "publish_at": slot.isoformat(),
        "publish_at_human": slot.strftime("%d/%m/%Y a las %H:%M"),
        "window_label": _get_window_label(platform, slot),
    }


def get_pending_posts(limit: int = 20) -> list[dict]:
    """Lista los posts pendientes ordenados por fecha de publicación."""
    r = _get_redis()
    now_ts = datetime.now(TIMEZONE).timestamp()
    
    # Obtener todos los pendientes (score >= ahora)
    items = r.zrangebyscore(QUEUE_KEY, now_ts, "+inf", start=0, num=limit, withscores=True)
    
    posts = []
    for item, score in items:
        job = json.loads(item)
        job["publish_at_human"] = datetime.fromtimestamp(score, TIMEZONE).strftime("%d/%m %H:%M")
        posts.append(job)
    
    return posts


def get_overdue_posts() -> list[dict]:
    """Posts que deberían haberse publicado ya."""
    r = _get_redis()
    now_ts = datetime.now(TIMEZONE).timestamp()
    
    items = r.zrangebyscore(QUEUE_KEY, "-inf", now_ts, withscores=True)
    return [json.loads(item) for item, _ in items]


def cancel_post(output_id: str, platform: str) -> bool:
    """Cancela un post programado."""
    r = _get_redis()
    pending = get_pending_posts(100)
    
    for post in pending:
        if post.get("output_id") == output_id and post.get("platform") == platform:
            r.zrem(QUEUE_KEY, json.dumps({k: v for k, v in post.items() 
                                          if k != "publish_at_human"}))
            return True
    return False


def _get_window_label(platform: str, dt: datetime) -> str:
    windows = OPTIMAL_WINDOWS.get(platform, [])
    for w in windows:
        if w["hour"] == dt.hour:
            return w["label"]
    return "Horario personalizado"
