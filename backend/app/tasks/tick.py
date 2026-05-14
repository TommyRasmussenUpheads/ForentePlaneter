import asyncio
from app.worker import app


@app.task(name="app.tasks.tick.process_tick")
def process_tick():
    from app.services.tick import process_tick_async
    asyncio.run(process_tick_async())


@app.task(name="app.tasks.tick.respawn_npc_defenses")
def respawn_npc_defenses():
    from app.services.tick import respawn_npc_defenses_async
    asyncio.run(respawn_npc_defenses_async())


@app.task(name="app.tasks.tick.check_round_end")
def check_round_end():
    from app.services.tick import check_round_end_async
    asyncio.run(check_round_end_async())
