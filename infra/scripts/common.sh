#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
DEFAULT_RELEASES_DIR="${RELEASES_DIR:-${REPO_ROOT}/infra/releases}"

log() {
	printf '[%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$*"
}

fail() {
	log "ERROR: $*"
	exit 1
}

require_command() {
	local command_name="$1"
	if ! command -v "${command_name}" >/dev/null 2>&1; then
		fail "Required command not found: ${command_name}"
	fi
}

is_truthy() {
	case "${1:-}" in
		1|true|TRUE|yes|YES|on|ON)
			return 0
			;;
		*)
			return 1
			;;
	esac
}

run_cmd() {
	if is_truthy "${DRY_RUN:-0}"; then
		log "[dry-run] $*"
		return 0
	fi

	"$@"
}

run_shell_command() {
	local command_text="$1"
	if is_truthy "${DRY_RUN:-0}"; then
		log "[dry-run] ${command_text}"
		return 0
	fi

	bash -lc "${command_text}"
}

resolve_compose_file() {
	local compose_file_candidate
	compose_file_candidate="${COMPOSE_FILE:-${REPO_ROOT}/infra/docker/docker-compose.yml}"

	if [[ ! -f "${compose_file_candidate}" ]]; then
		fail "Compose file does not exist: ${compose_file_candidate}"
	fi

	if [[ ! -s "${compose_file_candidate}" ]]; then
		fail "Compose file is empty: ${compose_file_candidate}"
	fi

	printf '%s' "${compose_file_candidate}"
}

ensure_compose_available() {
	require_command docker
	if docker compose version >/dev/null 2>&1; then
		return 0
	fi
	if command -v docker-compose >/dev/null 2>&1; then
		return 0
	fi

	fail "Neither 'docker compose' nor 'docker-compose' is available."
}

compose() {
	if docker compose version >/dev/null 2>&1; then
		run_cmd docker compose -f "${COMPOSE_FILE_PATH}" "$@"
		return
	fi

	run_cmd docker-compose -f "${COMPOSE_FILE_PATH}" "$@"
}

ensure_release_dir() {
	mkdir -p "${DEFAULT_RELEASES_DIR}"
	printf '%s' "${DEFAULT_RELEASES_DIR}"
}

get_git_commit() {
	if command -v git >/dev/null 2>&1 && git -C "${REPO_ROOT}" rev-parse --short HEAD >/dev/null 2>&1; then
		git -C "${REPO_ROOT}" rev-parse --short HEAD
		return
	fi

	printf '%s' "unknown"
}
