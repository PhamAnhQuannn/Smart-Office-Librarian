#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

ENVIRONMENT="${ENVIRONMENT:-staging}"
TARGET_RELEASE="${TARGET_RELEASE:-}"
SKIP_HEALTH_CHECK="${SKIP_HEALTH_CHECK:-0}"

usage() {
	cat <<'EOF'
Usage: rollback.sh [options]

Options:
  --environment <name>       Target environment (default: staging)
  --target-release <name>    Explicit release id to roll back to
  --skip-health-check        Skip post-rollback health verification
  --dry-run                  Print actions without executing
  --help                     Show this message
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--environment)
			ENVIRONMENT="$2"
			shift 2
			;;
		--target-release)
			TARGET_RELEASE="$2"
			shift 2
			;;
		--skip-health-check)
			SKIP_HEALTH_CHECK="1"
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

release_dir="$(ensure_release_dir)"
release_state_file="${release_dir}/current_release_${ENVIRONMENT}.txt"
deploy_history_file="${release_dir}/deploy_history.log"
rollback_history_file="${release_dir}/rollback_history.log"

if [[ -z "${TARGET_RELEASE}" ]]; then
	if [[ ! -f "${deploy_history_file}" ]]; then
		fail "No deploy history found at ${deploy_history_file}. Use --target-release."
	fi

	TARGET_RELEASE="$(awk -F',' -v env="${ENVIRONMENT}" '$2 == env { print $3 }' "${deploy_history_file}" | tail -n 2 | head -n 1)"
	if [[ -z "${TARGET_RELEASE}" ]]; then
		fail "Could not infer a previous release for environment=${ENVIRONMENT}."
	fi
fi

metadata_file="${release_dir}/${TARGET_RELEASE}.env"
if [[ ! -f "${metadata_file}" ]]; then
	fail "Release metadata not found: ${metadata_file}"
fi

# shellcheck disable=SC1090
source "${metadata_file}"

COMPOSE_FILE_PATH="${compose_file:-$(resolve_compose_file)}"
if [[ ! -s "${COMPOSE_FILE_PATH}" ]]; then
	fail "Compose file is missing or empty for release ${TARGET_RELEASE}: ${COMPOSE_FILE_PATH}"
fi

ensure_compose_available
log "Rolling back environment=${ENVIRONMENT} to release=${TARGET_RELEASE}"

compose config >/dev/null
compose up -d --remove-orphans

if ! is_truthy "${SKIP_HEALTH_CHECK}"; then
	DRY_RUN="${DRY_RUN:-0}" "${SCRIPT_DIR}/health_check.sh"
else
	log "Skipping health checks (--skip-health-check)."
fi

if ! is_truthy "${DRY_RUN:-0}"; then
	echo "${TARGET_RELEASE}" > "${release_state_file}"
	printf '%s,%s,%s\n' "$(date -u +"%Y%m%dT%H%M%SZ")" "${ENVIRONMENT}" "${TARGET_RELEASE}" >> "${rollback_history_file}"
fi

log "Rollback complete. release=${TARGET_RELEASE}"
