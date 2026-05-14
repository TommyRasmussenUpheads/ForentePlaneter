# Forente Planeter

Space strategy game — tick-based, browser-based.

## Stack

| Service | Technology | Port |
|---|---|---|
| API | FastAPI (Python) | 3200 |
| Frontend | React + Vite | 5173 |
| Database | PostgreSQL 16 | 5432 |
| Cache / Queue | Redis 7 | 6379 |
| Tick motor | Celery + Beat | — |

## Quick start

```bash
# 1. Clone and enter project
cd ForentePlaneter

# 2. Create environment file
cp .env.example .env
# Edit .env and set all passwords and SECRET_KEY

# 3. Start all services
docker compose up --build

# 4. API is available at
http://localhost:3200

# 5. API docs (Swagger)
http://localhost:3200/docs

# 6. Frontend
http://localhost:5173
```

## Services

### API — FastAPI
- Port 3200
- Auto-reload in development
- Swagger UI at /docs

### Tick motor — Celery Beat
- Fires every hour on the hour
- Processes: resource production, fleet movement,
  combat resolution, blockade updates, NPC respawn,
  score calculation, round-end check

### Database
- Schema auto-applied from db/init.sql on first run
- Persistent volume: db_data

### Redis
- Celery broker and result backend
- Persistent volume: redis_data

## Game rules summary

- Tick = 1 hour
- 1 galaxy, hex grid layout
- P1 at center, rings expand outward
- 1–2 NPC systems between players
- Frontier NPC buffer on outer edge
- Elder Race at galaxy edge (admin-controlled)
- "Unknown Regions - Do not pass beyond" guards Elder Race

## Roles
- superadmin — break the glass, 2FA required
- admin — full admin access + controls Elder Race
- elder_race — special observing player account
- player — normal player
