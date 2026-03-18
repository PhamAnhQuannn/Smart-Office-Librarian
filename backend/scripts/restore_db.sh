#!/usr/bin/env bash
# Backend convenience wrapper – delegates to the canonical infra restore script.
# Usage: restore_db.sh <backup_file.sql.gz> [--drop-public]
#   All config via environment variables (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD).
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup_file.sql.gz> [--drop-public]" >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INFRA_SCRIPT="${SCRIPT_DIR}/../../infra/scripts/restore.sh"

if [[ ! -f "${INFRA_SCRIPT}" ]]; then
  echo "ERROR: Infra restore script not found at ${INFRA_SCRIPT}" >&2
  exit 1
fi

exec bash "${INFRA_SCRIPT}" "$@"
