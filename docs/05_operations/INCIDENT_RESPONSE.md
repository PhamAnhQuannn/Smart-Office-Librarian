# Incident Response Guide

## Reliability Incidents (NFR-3.5 Foundation)

### Incident Type: Backup Failure

1. Confirm failure from scheduler logs.
2. Re-run backup manually:

```bash
DB_PASSWORD="<secret>" infra/scripts/backup.sh
```

3. Confirm a new backup artifact exists in the configured backup directory.
4. If repeated failure occurs, escalate as reliability incident and open RCA.

### Incident Type: Restore Required

1. Select latest valid backup (`backup_<db>_<timestamp>.sql.gz`).
2. Execute restore in approved window:

```bash
DB_PASSWORD="<secret>" infra/scripts/restore.sh <backup_file.sql.gz>
```

3. Use `--drop-public` only for full schema replacement.
4. Validate API and DB health after restore.

### Recovery Targets

- RPO <= 24h
- RTO <= 1h for API and metadata layer
- RTO <= 4h target for full vector restoration scope

### Post-Incident Actions

1. Record timeline, blast radius, and customer impact.
2. Record whether RPO/RTO targets were met.
3. Create follow-up task for prevention hardening if targets were missed.

