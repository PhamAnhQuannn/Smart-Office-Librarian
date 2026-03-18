#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

RUN_HEALTH_CHECK="${RUN_HEALTH_CHECK_AFTER_RESTART:-1}"
SERVICES_INPUT="${RESTART_SERVICES:-api frontend worker}"

usage() {
	cat <<'EOF'
Usage: restart_services.sh [options]

Options:
  --service <name>           Service to restart (may be repeated)
  --skip-health-check        Skip health verification after restart
  --dry-run                  Print actions without executing
  --help                     Show this message
EOF
}

declare -a SERVICES=()

while [[ $# -gt 0 ]]; do
	case "$1" in
		--service)
			SERVICES+=("$2")
			shift 2
			;;
		--skip-health-check)
			RUN_HEALTH_CHECK="0"
			shift
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

if [[ ${#SERVICES[@]} -eq 0 ]]; then
	read -r -a SERVICES <<< "${SERVICES_INPUT}"
fi

if [[ ${#SERVICES[@]} -eq 0 ]]; then
	fail "No services were provided for restart."
fi

COMPOSE_FILE_PATH="$(resolve_compose_file)"
ensure_compose_available

log "Restarting services: ${SERVICES[*]}"
compose restart "${SERVICES[@]}"

if is_truthy "${RUN_HEALTH_CHECK}"; then
	DRY_RUN="${DRY_RUN:-0}" "${SCRIPT_DIR}/health_check.sh"
else
	log "Skipping health checks (--skip-health-check)."
fi

log "Service restart flow completed."
