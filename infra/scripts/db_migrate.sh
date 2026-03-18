#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

TARGET_REVISION="${TARGET_REVISION:-head}"
API_SERVICE_NAME="${API_SERVICE_NAME:-api}"
RUN_MIGRATIONS_LOCALLY="${RUN_MIGRATIONS_LOCALLY:-0}"
MIGRATION_COMMAND="${MIGRATION_COMMAND:-}"

LOCAL_ALEMBIC_INI="${LOCAL_ALEMBIC_INI:-${REPO_ROOT}/backend/app/db/migrations/alembic.ini}"
CONTAINER_ALEMBIC_INI="${CONTAINER_ALEMBIC_INI:-/app/app/db/migrations/alembic.ini}"

usage() {
	cat <<'EOF'
Usage: db_migrate.sh [options]

Options:
  --revision <rev>           Alembic target revision (default: head)
  --service <name>           Compose API service name (default: api)
  --local                    Run migration from local environment instead of container
  --command <command>        Override migration command fully
  --dry-run                  Print actions without executing
  --help                     Show this message
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--revision)
			TARGET_REVISION="$2"
			shift 2
			;;
		--service)
			API_SERVICE_NAME="$2"
			shift 2
			;;
		--local)
			RUN_MIGRATIONS_LOCALLY="1"
			shift
			;;
		--command)
			MIGRATION_COMMAND="$2"
			shift 2
			;;
		--dry-run)
			DRY_RUN="1"
			shift
			;;
		--help)
			usage
			exit 0
			;;
		*)
			fail "Unknown argument: $1"
			;;
	esac
done

if [[ -n "${MIGRATION_COMMAND}" ]]; then
	log "Running explicit migration command override."
	run_shell_command "${MIGRATION_COMMAND}"
	log "Migration command override completed."
	exit 0
fi

if is_truthy "${RUN_MIGRATIONS_LOCALLY}"; then
	require_command alembic
	if [[ ! -f "${LOCAL_ALEMBIC_INI}" ]]; then
		fail "Local alembic config not found: ${LOCAL_ALEMBIC_INI}"
	fi

	run_cmd alembic -c "${LOCAL_ALEMBIC_INI}" upgrade "${TARGET_REVISION}"
	log "Local migration completed to revision=${TARGET_REVISION}"
	exit 0
fi

COMPOSE_FILE_PATH="$(resolve_compose_file)"
ensure_compose_available

log "Running container migration for service=${API_SERVICE_NAME} revision=${TARGET_REVISION}"
compose exec -T "${API_SERVICE_NAME}" alembic -c "${CONTAINER_ALEMBIC_INI}" upgrade "${TARGET_REVISION}"

log "Container migration completed to revision=${TARGET_REVISION}"
