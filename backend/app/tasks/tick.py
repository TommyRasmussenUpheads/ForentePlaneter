import asyncio
import logging
from app.worker import app

log = logging.getLogger(__name__)


def _run(coro):
    """Kjør en coroutine i en fersk event loop — trygt fra Celery sync worker."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            # Avbryt alle gjenværende tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        finally:
            loop.close()
            asyncio.set_event_loop(None)


@app.task(name="app.tasks.tick.process_tick")
def process_tick():
    from app.services.tick import process_tick_async
    _run(process_tick_async())


@app.task(name="app.tasks.tick.respawn_npc_defenses")
def respawn_npc_defenses():
    from app.services.tick import respawn_npc_defenses_async
    _run(respawn_npc_defenses_async())


@app.task(name="app.tasks.tick.check_round_end")
def check_round_end():
    from app.services.tick import check_round_end_async
    _run(check_round_end_async())
