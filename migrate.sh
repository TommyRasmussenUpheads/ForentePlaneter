#!/bin/bash
# Run Alembic migrations inside the API container
# Usage:
#   ./migrate.sh upgrade        — apply all pending migrations
#   ./migrate.sh downgrade -1   — roll back one migration
#   ./migrate.sh current        — show current revision
#   ./migrate.sh history        — show migration history
#   ./migrate.sh revision "msg" — create new migration

CMD=${1:-upgrade}
ARGS=${2:-head}

case "$CMD" in
  upgrade)
    docker exec forente_planeter_api alembic -c alembic.ini upgrade $ARGS
    ;;
  downgrade)
    docker exec forente_planeter_api alembic -c alembic.ini downgrade $ARGS
    ;;
  current)
    docker exec forente_planeter_api alembic -c alembic.ini current
    ;;
  history)
    docker exec forente_planeter_api alembic -c alembic.ini history --verbose
    ;;
  revision)
    docker exec forente_planeter_api alembic -c alembic.ini revision --autogenerate -m "$ARGS"
    ;;
  *)
    echo "Usage: ./migrate.sh [upgrade|downgrade|current|history|revision] [args]"
    ;;
esac
