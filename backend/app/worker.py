from celery import Celery
from celery.schedules import crontab
import os

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "forente_planeter",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks.tick", "app.tasks.notifications"],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

app.conf.beat_schedule = {
    # Main game tick — every hour on the hour
    "game-tick": {
        "task": "app.tasks.tick.process_tick",
        "schedule": crontab(minute=0, hour="*"),
    },
    # NPC defense respawn check — every 6 hours
    "npc-respawn": {
        "task": "app.tasks.tick.respawn_npc_defenses",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    # Check for expired game rounds — every hour
    "check-round-end": {
        "task": "app.tasks.tick.check_round_end",
        "schedule": crontab(minute=5, hour="*"),
    },
}
