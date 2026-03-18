#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

SERVICE_NAME="${SERVICE_NAME:-api}"
TAIL_LINES="${TAIL_LINES:-200}"
FOLLOW="${FOLLOW_LOGS:-0}"

usage() {
	cat <<'EOF'
Usage: logs.sh [options]

Options:
  --service <name>           Service name (default: api)
  --lines <count>            Number of lines to show (default: 200)
  --follow                   Stream logs continuously
  --help                     Show this message
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--service)
			SERVICE_NAME="$2"
			shift 2
			;;
		--lines)
			TAIL_LINES="$2"
			shift 2
			;;
		--follow)
			FOLLOW="1"
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

if ! [[ "${TAIL_LINES}" =~ ^[0-9]+$ ]]; then
	fail "--lines must be an integer: ${TAIL_LINES}"
fi

COMPOSE_FILE_PATH="$(resolve_compose_file)"
ensure_compose_available

if is_truthy "${FOLLOW}"; then
	compose logs --tail "${TAIL_LINES}" --follow "${SERVICE_NAME}"
	log "Log streaming ended for service=${SERVICE_NAME}"
	exit 0
fi

compose logs --tail "${TAIL_LINES}" "${SERVICE_NAME}"
log "Log snapshot printed for service=${SERVICE_NAME}"
