#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

WORKER_SERVICE_NAME="${WORKER_SERVICE_NAME:-worker}"
WORKER_REPLICAS="${WORKER_REPLICAS:-}"
RUN_HEALTH_CHECK="${RUN_HEALTH_CHECK_AFTER_SCALE:-1}"

usage() {
	cat <<'EOF'
Usage: scale_workers.sh [options]

Options:
  --service <name>           Worker service name (default: worker)
  --replicas <count>         Desired replica count (required)
  --skip-health-check        Skip health verification after scaling
  --dry-run                  Print actions without executing
  --help                     Show this message
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--service)
			WORKER_SERVICE_NAME="$2"
			shift 2
			;;
		--replicas)
			WORKER_REPLICAS="$2"
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

if [[ -z "${WORKER_REPLICAS}" ]]; then
	fail "--replicas is required"
fi

if ! [[ "${WORKER_REPLICAS}" =~ ^[0-9]+$ ]]; then
	fail "Replica count must be an integer: ${WORKER_REPLICAS}"
fi

COMPOSE_FILE_PATH="$(resolve_compose_file)"
ensure_compose_available

log "Scaling service ${WORKER_SERVICE_NAME} to replicas=${WORKER_REPLICAS}"
compose up -d --scale "${WORKER_SERVICE_NAME}=${WORKER_REPLICAS}" "${WORKER_SERVICE_NAME}"

if is_truthy "${RUN_HEALTH_CHECK}"; then
	DRY_RUN="${DRY_RUN:-0}" "${SCRIPT_DIR}/health_check.sh"
else
	log "Skipping health checks (--skip-health-check)."
fi

log "Worker scaling flow completed."
