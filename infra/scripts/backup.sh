#!/usr/bin/env bash
set -euo pipefail

# Daily PostgreSQL backup script for Embedlyzer.
# Default retention keeps the latest 7 days of compressed backups.

BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-embedlyzer}"
DB_USER="${DB_USER:-postgres}"

: "${DB_PASSWORD:?DB_PASSWORD must be set}"

timestamp="$(date -u +"%Y%m%dT%H%M%SZ")"
mkdir -p "${BACKUP_DIR}"
backup_file="${BACKUP_DIR}/backup_${DB_NAME}_${timestamp}.sql.gz"

export PGPASSWORD="${DB_PASSWORD}"
pg_dump \
	--host "${DB_HOST}" \
	--port "${DB_PORT}" \
	--username "${DB_USER}" \
	--dbname "${DB_NAME}" \
	--no-owner \
	--no-privileges | gzip > "${backup_file}"
unset PGPASSWORD

# Prune backups older than the retention window.
find "${BACKUP_DIR}" -type f -name "backup_${DB_NAME}_*.sql.gz" -mtime +"${RETENTION_DAYS}" -print -delete

echo "Backup complete: ${backup_file}"
echo "Retention policy: ${RETENTION_DAYS} days"

