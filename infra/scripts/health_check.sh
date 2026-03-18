#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

RETRIES="${HEALTH_RETRIES:-10}"
INTERVAL_SECONDS="${HEALTH_INTERVAL_SECONDS:-3}"
TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-5}"

usage() {
	cat <<'EOF'
Usage: health_check.sh [options]

Options:
  --url <endpoint>           Add endpoint URL to verify (may be repeated)
  --retries <count>          Retry count per endpoint (default: 10)
  --interval <seconds>       Delay between retries (default: 3)
  --timeout <seconds>        Curl timeout in seconds (default: 5)
  --dry-run                  Print actions without executing
  --help                     Show this message

Environment:
  CHECK_URLS                 Comma-separated endpoint URLs
EOF
}

declare -a CHECK_URL_LIST=()

if [[ -n "${CHECK_URLS:-}" ]]; then
	IFS=',' read -r -a CHECK_URL_LIST <<< "${CHECK_URLS}"
fi

while [[ $# -gt 0 ]]; do
	case "$1" in
		--url)
			CHECK_URL_LIST+=("$2")
			shift 2
			;;
		--retries)
			RETRIES="$2"
			shift 2
			;;
		--interval)
			INTERVAL_SECONDS="$2"
			shift 2
			;;
		--timeout)
			TIMEOUT_SECONDS="$2"
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

if [[ ${#CHECK_URL_LIST[@]} -eq 0 ]]; then
	CHECK_URL_LIST=(
		"${API_HEALTH_URL:-http://localhost:8000/health}"
		"${API_READY_URL:-http://localhost:8000/ready}"
		"${METRICS_URL:-http://localhost:8000/metrics}"
		"${FRONTEND_URL:-http://localhost:3101}"
	)
fi

require_command curl

for endpoint in "${CHECK_URL_LIST[@]}"; do
	if [[ -z "${endpoint}" ]]; then
		continue
	fi

	log "Checking endpoint: ${endpoint}"
	passed="0"

	for attempt in $(seq 1 "${RETRIES}"); do
		if run_cmd curl --fail --silent --show-error --max-time "${TIMEOUT_SECONDS}" "${endpoint}" >/dev/null; then
			log "Endpoint healthy: ${endpoint} (attempt ${attempt}/${RETRIES})"
			passed="1"
			break
		fi

		log "Endpoint not ready: ${endpoint} (attempt ${attempt}/${RETRIES})"
		sleep "${INTERVAL_SECONDS}"
	done

	if [[ "${passed}" != "1" ]]; then
		fail "Health verification failed for endpoint: ${endpoint}"
	fi
done

log "Health checks passed for all endpoints."
