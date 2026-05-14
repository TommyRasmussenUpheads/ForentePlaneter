# Alembic migration helper for Windows
# Usage:
#   .\migrate.ps1 upgrade        — apply all pending migrations
#   .\migrate.ps1 downgrade -1   — roll back one migration
#   .\migrate.ps1 current        — show current revision
#   .\migrate.ps1 history        — show migration history
#   .\migrate.ps1 revision "msg" — create new auto-migration

param(
    [string]$Command = "upgrade",
    [string]$Args = "head"
)

switch ($Command) {
    "upgrade"   { docker exec forente_planeter_api alembic -c alembic.ini upgrade $Args }
    "downgrade" { docker exec forente_planeter_api alembic -c alembic.ini downgrade $Args }
    "current"   { docker exec forente_planeter_api alembic -c alembic.ini current }
    "history"   { docker exec forente_planeter_api alembic -c alembic.ini history --verbose }
    "revision"  { docker exec forente_planeter_api alembic -c alembic.ini revision --autogenerate -m $Args }
    default     { Write-Host "Usage: .\migrate.ps1 [upgrade|downgrade|current|history|revision] [args]" }
}
