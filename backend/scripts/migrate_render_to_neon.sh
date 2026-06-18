#!/usr/bin/env bash
#
# migrate_render_to_neon.sh
#
# Automates migrating a PostgreSQL database from Render to Neon.
# Steps:
#  1) Export from Render with pg_dump (to ./render_backup.sql)
#  2) Import into Neon with psql
#  3) (Optional) Update Render service env var DATABASE_URL to SQLAlchemy format via Render API
#
# Idempotence: Uses pg_dump --clean/--if-exists so re-import drops/recreates objects.
# Safe defaults: Does NOT print credentials; reads them from env vars below.
#
# Usage:
#   # minimally set these (export in your shell or a .env loaded before running):
#   export RENDER_DATABASE_URL="postgresql://<user>:<password>@<host>:5432/<dbname>?sslmode=require"
#   export NEON_PSQL_URL="postgresql://<user>:<password>@<host>.neon.tech/<dbname>?sslmode=require&channel_binding=require"
#   # optional: provide explicit SQLAlchemy-style URL instead of deriving it
#   # export SQLALCHEMY_DATABASE_URL_OVERRIDE="postgresql+psycopg2://<user>:<password>@<host>.neon.tech/<dbname>?sslmode=require"
#   # optional (for step 4):
#   # export RENDER_API_KEY="<render_api_key>"
#   # export RENDER_SERVICE_ID="<render_service_id>"
#   # export RENDER_API_BASE="https://api.render.com/v1"   # default
#   #
#   bash ./migrate_render_to_neon.sh
#
set -Eeuo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CWD="$(pwd)"

# -------------------- Configurable variables (override via env or env-file) --------------------
# You can provide these via exported environment variables OR via an env file (see MIGRATE_ENV_FILE below).
# For security, DO NOT hardcode secrets in this script.
RENDER_DATABASE_URL="${RENDER_DATABASE_URL:-}"
NEON_PSQL_URL="${NEON_PSQL_URL:-}"
SQLALCHEMY_DATABASE_URL_OVERRIDE="${SQLALCHEMY_DATABASE_URL_OVERRIDE:-}"

RENDER_API_KEY="${RENDER_API_KEY:-}"
RENDER_SERVICE_ID="${RENDER_SERVICE_ID:-}"
RENDER_API_BASE="${RENDER_API_BASE:-https://api.render.com/v1}"

BACKUP_FILE="${BACKUP_FILE:-render_backup.sql}"

# Optional env file loader: set MIGRATE_ENV_FILE to a path, or place a .env.migration next to this script or in CWD.
MIGRATE_ENV_FILE="${MIGRATE_ENV_FILE:-}"

# Preferred Postgres client major version (used for docker fallback)
PG_CLIENT_VERSION="${PG_CLIENT_VERSION:-17}"

# -------------------- Helpers --------------------
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
abort() { echo; echo "ERROR: $*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || abort "Missing required command: $1"
}

# Determine major version number from a command like pg_dump --version
pg_major_version() {
  local cmd="$1"
  local ver
  ver="$($cmd --version 2>/dev/null | awk 'NR==1{print $NF}')" || return 1
  printf '%s' "$ver" | awk -F. '{print $1}'
}

# Build docker run wrapper for postgres client commands if needed
docker_pg() {
  local tool="$1"; shift
  local img="postgres:${PG_CLIENT_VERSION}-alpine"
  docker run --rm \
    -e PGPASSFILE=/tmp/.pgpass \
    -e PGSSLMODE=require \
    -v "$PWD":/work -w /work \
    "$img" "$tool" "$@"
}

# Best-effort extraction of sslmode from a query string
extract_sslmode() {
  # input: query string (e.g., "sslmode=require&channel_binding=require")
  # output: value of sslmode or empty
  local qs="$1"
  printf '%%s' "$qs" | tr '&' '\n' | awk -F'=' '$1=="sslmode" {print $2; exit}'
}

# Safely build JSON payload using jq if available.
build_render_env_json() {
  local key="$1"; shift
  local value="$1"; shift
  if command -v jq >/dev/null 2>&1; then
    jq -n --arg KEY "$key" --arg VAL "$value" '{envVars:[{key:$KEY, value:$VAL}]}'
  else
    # Fallback: print a template (avoid unsafe manual JSON escaping)
    cat <<TEMPLATE
{"envVars":[{"key":"${key}","value":"__REPLACE_WITH_URL__"}]}
TEMPLATE
  fi
}

# Derive an SQLAlchemy-compatible URL from a standard PostgreSQL URI.
#  Converts scheme and keeps only sslmode in the query string.
derive_sqlalchemy_url() {
  local uri="$1"
  # Require postgresql:// scheme
  if [[ "$uri" != postgresql://* ]]; then
    echo ""; return 0
  fi
  local without_scheme="${uri#postgresql://}"
  local before_qs="${without_scheme%%\?*}"
  local qs=""
  if [[ "$without_scheme" == *\?* ]]; then
    qs="${without_scheme#*\?}"
  fi
  local sslm
  sslm="$(extract_sslmode "$qs")"
  if [[ -z "$sslm" ]]; then sslm="require"; fi
  printf 'postgresql+psycopg2://%s?sslmode=%s' "$before_qs" "$sslm"
}

cleanup_on_error() {
  log "A failure occurred. You can re-run the script safely; it is idempotent."
}
trap cleanup_on_error ERR

# -------------------- Preconditions --------------------
# Load env file if provided or discovered
load_env_if_present() {
  local candidate=""
  if [[ -n "$MIGRATE_ENV_FILE" && -f "$MIGRATE_ENV_FILE" ]]; then
    candidate="$MIGRATE_ENV_FILE"
  elif [[ -f "$SCRIPT_DIR/.env.migration" ]]; then
    candidate="$SCRIPT_DIR/.env.migration"
  elif [[ -f "$CWD/.env.migration" ]]; then
    candidate="$CWD/.env.migration"
  fi
  if [[ -n "$candidate" ]]; then
    log "Loading env vars from: $candidate"
    set -a
    # shellcheck disable=SC1090
    source "$candidate"
    set +a
    # Refresh variables after sourcing
    RENDER_DATABASE_URL="${RENDER_DATABASE_URL:-}"
    NEON_PSQL_URL="${NEON_PSQL_URL:-}"
    SQLALCHEMY_DATABASE_URL_OVERRIDE="${SQLALCHEMY_DATABASE_URL_OVERRIDE:-}"
    RENDER_API_KEY="${RENDER_API_KEY:-}"
    RENDER_SERVICE_ID="${RENDER_SERVICE_ID:-}"
    RENDER_API_BASE="${RENDER_API_BASE:-https://api.render.com/v1}"
  fi
}

load_env_if_present

log "Checking prerequisites..."
need_cmd curl

# Decide which pg_dump/psql to use: prefer local if major >= required, else docker fallback
USE_DOCKER_PG=0
if command -v pg_dump >/dev/null 2>&1 && command -v psql >/dev/null 2>&1; then
  local_major="$(pg_major_version pg_dump || echo 0)"
  if [[ "$local_major" -lt "$PG_CLIENT_VERSION" ]]; then
    if command -v docker >/dev/null 2>&1; then
      log "Using dockerized Postgres client (postgres:${PG_CLIENT_VERSION}) due to local version $local_major."
      USE_DOCKER_PG=1
    else
      abort "Local pg_dump major=$local_major < required ${PG_CLIENT_VERSION}, and Docker not found. Install postgresql-client-${PG_CLIENT_VERSION} or Docker."
    fi
  fi
else
  if command -v docker >/dev/null 2>&1; then
    log "Using dockerized Postgres client (postgres:${PG_CLIENT_VERSION}) as pg_dump/psql not found locally."
    USE_DOCKER_PG=1
  else
    abort "pg_dump/psql not found and Docker not available. Please install Postgres client or Docker."
  fi
fi

# Wrapper functions to execute chosen clients without eval pitfalls
pg_dump_cmd() {
  if [[ "$USE_DOCKER_PG" -eq 1 ]]; then
    docker_pg pg_dump "$@"
  else
    command pg_dump "$@"
  fi
}

psql_cmd() {
  if [[ "$USE_DOCKER_PG" -eq 1 ]]; then
    docker_pg psql "$@"
  else
    command psql "$@"
  fi
}

[[ -n "$RENDER_DATABASE_URL" ]] || abort "RENDER_DATABASE_URL is not set. See header for required format."
[[ -n "$NEON_PSQL_URL" ]] || abort "NEON_PSQL_URL is not set. See header for required format."

# -------------------- Step 1: Dump from Render --------------------
log "Starting pg_dump from Render to ./$BACKUP_FILE ..."
# --clean/--if-exists make the import idempotent by dropping objects first.
# --no-owner/--no-acl avoid ownership/privilege issues on restore.
pg_dump_cmd \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --format=plain \
  --file="$BACKUP_FILE" \
  "$RENDER_DATABASE_URL"

if [[ ! -s "$BACKUP_FILE" ]]; then
  abort "Dump file $BACKUP_FILE is empty or missing."
fi
log "Dump completed: $(du -h "$BACKUP_FILE" | awk '{print $1}')"

# -------------------- Step 2 & 3: Import into Neon --------------------
log "Importing dump into Neon (this may take a while)..."
# -v ON_ERROR_STOP=1 ensures we stop on first SQL error
psql_cmd -v ON_ERROR_STOP=1 -d "$NEON_PSQL_URL" -f "$BACKUP_FILE"
log "Import completed successfully."

# -------------------- Step 4: Prepare/Update DATABASE_URL on Render --------------------
# Derive SQLAlchemy-style URL unless an explicit override is provided.
SQLALCHEMY_URL="${SQLALCHEMY_DATABASE_URL_OVERRIDE:-}"
if [[ -z "$SQLALCHEMY_URL" ]]; then
  SQLALCHEMY_URL="$(derive_sqlalchemy_url "$NEON_PSQL_URL")"
fi

if [[ -z "$SQLALCHEMY_URL" ]]; then
  log "Could not derive SQLAlchemy URL automatically. Please set SQLALCHEMY_DATABASE_URL_OVERRIDE and re-run step 4.";
else
  log "Derived SQLAlchemy DATABASE_URL for the app."
fi

# Try to update via Render API if credentials are present; otherwise print instructions.
if [[ -n "$RENDER_API_KEY" && -n "$RENDER_SERVICE_ID" && -n "$SQLALCHEMY_URL" ]]; then
  log "Attempting to update Render env var DATABASE_URL via API..."
  if command -v jq >/dev/null 2>&1; then
    payload="$(build_render_env_json "DATABASE_URL" "$SQLALCHEMY_URL")"
    set +e
    resp_code=$(curl -sS -o /tmp/render_env_resp.json -w '%{http_code}' \
      -X PUT "${RENDER_API_BASE}/services/${RENDER_SERVICE_ID}/env-vars" \
      -H "Authorization: Bearer ${RENDER_API_KEY}" \
      -H "Content-Type: application/json" \
      --data "$payload")
    set -e
    if [[ "$resp_code" != "200" && "$resp_code" != "201" && "$resp_code" != "204" ]]; then
      log "PUT failed with HTTP $resp_code. Will try POST as a fallback..."
      set +e
      resp_code=$(curl -sS -o /tmp/render_env_resp.json -w '%{http_code}' \
        -X POST "${RENDER_API_BASE}/services/${RENDER_SERVICE_ID}/env-vars" \
        -H "Authorization: Bearer ${RENDER_API_KEY}" \
        -H "Content-Type: application/json" \
        --data "$payload")
      set -e
    fi
    if [[ "$resp_code" == "200" || "$resp_code" == "201" || "$resp_code" == "204" ]]; then
      log "Render env var DATABASE_URL updated successfully (HTTP $resp_code)."
    else
      log "Render API update did not succeed (HTTP $resp_code). Inspect /tmp/render_env_resp.json and update manually."
    fi
  else
    cat <<'NOTE'
-------------------------------------------------------------------------------
jq not found. Skipping automatic Render API update.
To update DATABASE_URL on Render manually, run (replace the placeholder value):

curl -sS -X PUT "${RENDER_API_BASE}/services/${RENDER_SERVICE_ID}/env-vars" \
  -H "Authorization: Bearer ${RENDER_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"envVars":[{"key":"DATABASE_URL","value":"__REPLACE_WITH_SQLALCHEMY_URL__"}]}'

If PUT fails, try POST:

curl -sS -X POST "${RENDER_API_BASE}/services/${RENDER_SERVICE_ID}/env-vars" \
  -H "Authorization: Bearer ${RENDER_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"envVars":[{"key":"DATABASE_URL","value":"__REPLACE_WITH_SQLALCHEMY_URL__"}]}'
-------------------------------------------------------------------------------
NOTE
  fi
else
  log "RENDER_API_KEY/RENDER_SERVICE_ID not provided or SQLAlchemy URL not derived. Skipping API update."
fi

# -------------------- Step 5: Final messages --------------------
cat <<EOF

✅ Migration finished.

Next steps / reminders:
- [ ] Update DATABASE_URL in Render Dashboard if not updated automatically.
      Expected SQLAlchemy format: postgresql+psycopg2://<user>:<password>@<host>.neon.tech/<dbname>?sslmode=require
      Derived value (if available):
      ${SQLALCHEMY_URL:-<not derived>}
- [ ] Trigger a manual deploy in Render so your app picks up the new env var.
- [ ] Test your app: login, create users, and verify critical flows.
- [ ] Check Render logs for any database-related errors.

Artifacts:
- Dump file: ./${BACKUP_FILE}

Re-running this script is safe. It will re-dump from Render and re-import into Neon, dropping/recreating objects.
EOF
