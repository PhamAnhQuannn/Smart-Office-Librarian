# Deployment Guide

## Backup And Restore Policy (NFR-3.5 Foundation)

This baseline defines the production-facing backup and restore controls for PostgreSQL metadata.

### Backup Schedule

- Daily backup command: `infra/scripts/backup.sh`
- Default retention: 7 days
- Output location default: `./backups/postgres`

### Required Environment Variables

- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `BACKUP_DIR` (optional override)
- `RETENTION_DAYS` (optional override; default 7)

### Example Daily Schedule

Run daily via scheduler/cron equivalent:

```bash
DB_PASSWORD="<secret>" BACKUP_DIR="/var/backups/embedlyzer" infra/scripts/backup.sh
```

### Restore Procedure

- Restore command: `infra/scripts/restore.sh <backup_file.sql.gz>`
- Optional reset before restore: `infra/scripts/restore.sh <backup_file.sql.gz> --drop-public`

### Recovery Objectives

- RPO: <= 24 hours
- RTO: <= 1 hour for API and PostgreSQL metadata layer
- RTO (full vector restoration): <= 4 hours target

### Verification Cadence

- Weekly non-production restore drill is required.
- Record latest drill date and outcome in incident operations notes.

