#!/usr/bin/env bash
# Backend convenience wrapper – delegates to the canonical infra backup script.
# Usage: backup_db.sh
#   All config via environment variables (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INFRA_SCRIPT="${SCRIPT_DIR}/../../infra/scripts/backup.sh"

if [[ ! -f "${INFRA_SCRIPT}" ]]; then
  echo "ERROR: Infra backup script not found at ${INFRA_SCRIPT}" >&2
  exit 1
fi

exec bash "${INFRA_SCRIPT}" "$@"
