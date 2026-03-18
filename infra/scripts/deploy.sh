#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=infra/scripts/common.sh
source "${SCRIPT_DIR}/common.sh"

ENVIRONMENT="${ENVIRONMENT:-staging}"
RELEASE_VERSION="${RELEASE_VERSION:-}"
SKIP_MIGRATIONS="${SKIP_MIGRATIONS:-0}"
SKIP_HEALTH_CHECK="${SKIP_HEALTH_CHECK:-0}"

usage() {
	cat <<'EOF'
Usage: deploy.sh [options]

Options:
  --environment <name>       Target environment (default: staging)
  --version <release>        Explicit release version label
  --skip-migrations          Skip database migrations
  --skip-health-check        Skip post-deploy health verification
  --dry-run                  Print actions without executing
  --help                     Show this message

Environment:
  COMPOSE_FILE               Compose file path (default: infra/docker/docker-compose.yml)
  RELEASES_DIR               Release metadata directory (default: infra/releases)
EOF
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		--environment)
			ENVIRONMENT="$2"
			shift 2
			;;
		--version)
			RELEASE_VERSION="$2"
			shift 2
			;;
		--skip-migrations)
			SKIP_MIGRATIONS="1"
			shift
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

COMPOSE_FILE_PATH="$(resolve_compose_file)"
ensure_compose_available

release_dir="$(ensure_release_dir)"
release_state_file="${release_dir}/current_release_${ENVIRONMENT}.txt"
deploy_history_file="${release_dir}/deploy_history.log"

timestamp="$(date -u +"%Y%m%dT%H%M%SZ")"
commit_sha="$(get_git_commit)"

if [[ -z "${RELEASE_VERSION}" ]]; then
	RELEASE_VERSION="${ENVIRONMENT}-${timestamp}-${commit_sha}"
fi

previous_release="none"
if [[ -f "${release_state_file}" ]]; then
	previous_release="$(<"${release_state_file}")"
fi

metadata_file="${release_dir}/${RELEASE_VERSION}.env"
cat > "${metadata_file}" <<EOF
release_version=${RELEASE_VERSION}
environment=${ENVIRONMENT}
timestamp_utc=${timestamp}
commit_sha=${commit_sha}
compose_file=${COMPOSE_FILE_PATH}
previous_release=${previous_release}
EOF

log "Deploy preflight passed for environment=${ENVIRONMENT}, release=${RELEASE_VERSION}"
compose config >/dev/null

compose pull --ignore-pull-failures
compose up -d --remove-orphans

if ! is_truthy "${SKIP_MIGRATIONS}"; then
	DRY_RUN="${DRY_RUN:-0}" COMPOSE_FILE="${COMPOSE_FILE_PATH}" ENVIRONMENT="${ENVIRONMENT}" \
		"${SCRIPT_DIR}/db_migrate.sh"
else
	log "Skipping migrations (--skip-migrations)."
fi

if ! is_truthy "${SKIP_HEALTH_CHECK}"; then
	DRY_RUN="${DRY_RUN:-0}" "${SCRIPT_DIR}/health_check.sh"
else
	log "Skipping health checks (--skip-health-check)."
fi

if ! is_truthy "${DRY_RUN:-0}"; then
	echo "${RELEASE_VERSION}" > "${release_state_file}"
	printf '%s,%s,%s,%s\n' "${timestamp}" "${ENVIRONMENT}" "${RELEASE_VERSION}" "${commit_sha}" >> "${deploy_history_file}"
fi

log "Deployment complete. release=${RELEASE_VERSION} previous=${previous_release}"
