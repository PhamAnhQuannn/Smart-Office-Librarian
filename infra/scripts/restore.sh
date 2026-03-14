#!/usr/bin/env bash
set -euo pipefail

# PostgreSQL restore script for Embedlyzer recovery.
# RPO target: <= 24h. RTO target: <= 1h for API/metadata layer.

if [[ $# -lt 1 ]]; then
	echo "Usage: $0 <backup_file.sql.gz> [--drop-public]"
	exit 1
fi

BACKUP_FILE="$1"
DROP_PUBLIC="${2:-}"

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-embedlyzer}"
DB_USER="${DB_USER:-postgres}"

: "${DB_PASSWORD:?DB_PASSWORD must be set}"

if [[ ! -f "${BACKUP_FILE}" ]]; then
	echo "Backup file not found: ${BACKUP_FILE}"
	exit 1
fi

export PGPASSWORD="${DB_PASSWORD}"

if [[ "${DROP_PUBLIC}" == "--drop-public" ]]; then
	psql --host "${DB_HOST}" --port "${DB_PORT}" --username "${DB_USER}" --dbname "${DB_NAME}" \
		-c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
fi

gunzip -c "${BACKUP_FILE}" | psql \
	--host "${DB_HOST}" \
	--port "${DB_PORT}" \
	--username "${DB_USER}" \
	--dbname "${DB_NAME}"

unset PGPASSWORD

echo "Restore complete: ${BACKUP_FILE}"
echo "Recovery objective reference: RPO<=24h, RTO<=1h (API/metadata), RTO<=4h (full vector restore target)."

