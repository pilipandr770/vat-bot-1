# Database Backup — VAT Bot

## Overview

Backups are created via `scripts/backup_db.sh`:
- **Format**: `pg_dump` (plain SQL) → gzip  
- **Storage**: AWS S3 (STANDARD_IA storage class)  
- **Retention**: 30 days (configurable via `BACKUP_RETAIN_DAYS`)  
- **Schedule**: Daily at 03:00 UTC

---

## Required Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | Full PostgreSQL connection string | `postgresql://u:p@host/db` |
| `BACKUP_S3_BUCKET` | S3 bucket name | `my-vatbot-backups` |

## Optional Environment Variables

| Variable | Default | Description |
|---|---|---|
| `BACKUP_S3_PREFIX` | `vatbot` | Key prefix inside the bucket |
| `BACKUP_RETAIN_DAYS` | `30` | Days to keep old backups |
| `PG_DUMP_OPTS` | _(empty)_ | Extra flags for `pg_dump` (e.g. `--schema vat_verification`) |

---

## Setup on Render.com

1. Go to **Render dashboard → New → Cron Job**
2. **Name**: `vatbot-db-backup`
3. **Build command**: `pip install awscli`
4. **Start command**: `bash scripts/backup_db.sh`
5. **Schedule**: `0 3 * * *` (daily 03:00 UTC)
6. Add the env vars above under **Environment**
7. (Optional) Add `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_DEFAULT_REGION` if not using an IAM instance role

> **Tip**: Use an S3 bucket with server-side encryption (AES-256 or KMS) and an IAM role with write-only (`s3:PutObject`) access for the backup job and read-only access for the restore role.

---

## Manual Backup

```bash
# From your local machine or Render shell:
export DATABASE_URL="postgresql://..."
export BACKUP_S3_BUCKET="my-vatbot-backups"
bash scripts/backup_db.sh
```

---

## Restore Procedure

```bash
# 1. Download the backup from S3
aws s3 cp "s3://${BACKUP_S3_BUCKET}/vatbot/2026-01-15T030000Z.sql.gz" /tmp/backup.sql.gz

# 2. Decompress
gunzip /tmp/backup.sql.gz

# 3. Restore (into a fresh / empty database)
psql "${DATABASE_URL}" < /tmp/backup.sql

# 4. Recreate the schema search path if needed
psql "${DATABASE_URL}" -c "SET search_path TO vat_verification;"
```

> **Warning**: Restoring into an existing database will overwrite data. Always test in a staging environment first.

---

## S3 Bucket Policy (Least Privilege)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BackupWrite",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::ACCOUNT_ID:role/render-backup-role" },
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::my-vatbot-backups/vatbot/*"
    },
    {
      "Sid": "RestoreRead",
      "Effect": "Allow",
      "Principal": { "AWS": "arn:aws:iam::ACCOUNT_ID:role/render-restore-role" },
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::my-vatbot-backups",
        "arn:aws:s3:::my-vatbot-backups/*"
      ]
    }
  ]
}
```

---

## Monitoring

Render Cron Job logs are available in the Render dashboard under the **Cron Job → Logs** tab.  
Each backup run prints:
```
[backup] Starting dump at 2026-01-15T030000Z
[backup] Dump created: /tmp/vatbot_2026-01-15T030000Z.sql.gz (4.2M)
[backup] Uploaded to s3://my-vatbot-backups/vatbot/2026-01-15T030000Z.sql.gz
[backup] Deleting backups older than 30 days ...
[backup] Done.
```
