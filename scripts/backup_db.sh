#!/usr/bin/env bash
# scripts/backup_db.sh
#
# PostgreSQL backup → gzip → S3 (30-day retention).
#
# USAGE (standalone):
#   bash scripts/backup_db.sh
#
# REQUIRED ENV VARS:
#   DATABASE_URL   — postgresql://user:pass@host:5432/dbname
#   BACKUP_S3_BUCKET — e.g. my-vatbot-backups
#
# OPTIONAL ENV VARS:
#   BACKUP_S3_PREFIX  — prefix inside bucket (default: vatbot)
#   BACKUP_RETAIN_DAYS — how long to keep old backups (default: 30)
#   PG_DUMP_OPTS      — extra flags for pg_dump (default: empty)
#
# DEPENDENCIES:
#   pg_dump (postgresql-client), gzip, awscli
#
# RENDER.COM CRON SETUP:
#   1. Add a "Cron Job" service in Render dashboard
#   2. Build command: pip install awscli
#   3. Start command: bash scripts/backup_db.sh
#   4. Schedule: 0 3 * * *  (daily at 03:00 UTC)
#   5. Add the env vars listed above in Render environment settings
# ------------------------------------------------------------------
set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────
TIMESTAMP=$(date -u +"%Y-%m-%dT%H%M%SZ")
S3_PREFIX="${BACKUP_S3_PREFIX:-vatbot}"
RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-30}"
DUMP_FILE="/tmp/vatbot_${TIMESTAMP}.sql.gz"

# ── Validate required env vars ──────────────────────────────────────
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL is not set." >&2
  exit 1
fi

if [[ -z "${BACKUP_S3_BUCKET:-}" ]]; then
  echo "ERROR: BACKUP_S3_BUCKET is not set." >&2
  exit 1
fi

# ── Dump ────────────────────────────────────────────────────────────
echo "[backup] Starting dump at ${TIMESTAMP}"
pg_dump "${DATABASE_URL}" \
  --no-owner \
  --no-acl \
  --format=plain \
  ${PG_DUMP_OPTS:-} \
  | gzip -9 > "${DUMP_FILE}"

DUMP_SIZE=$(du -sh "${DUMP_FILE}" | cut -f1)
echo "[backup] Dump created: ${DUMP_FILE} (${DUMP_SIZE})"

# ── Upload to S3 ─────────────────────────────────────────────────────
S3_KEY="${S3_PREFIX}/${TIMESTAMP}.sql.gz"
aws s3 cp "${DUMP_FILE}" "s3://${BACKUP_S3_BUCKET}/${S3_KEY}" \
  --storage-class STANDARD_IA

echo "[backup] Uploaded to s3://${BACKUP_S3_BUCKET}/${S3_KEY}"

# ── Cleanup local temp file ──────────────────────────────────────────
rm -f "${DUMP_FILE}"

# ── Rotate old backups (delete objects older than RETAIN_DAYS) ───────
CUTOFF=$(date -u -d "${RETAIN_DAYS} days ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
  || date -u -v-"${RETAIN_DAYS}"d +"%Y-%m-%dT%H:%M:%SZ")  # macOS fallback

echo "[backup] Deleting backups older than ${RETAIN_DAYS} days (before ${CUTOFF})"
aws s3 ls "s3://${BACKUP_S3_BUCKET}/${S3_PREFIX}/" \
  | awk '{print $4}' \
  | while read -r KEY; do
      OBJ_DATE=$(echo "${KEY}" | grep -oP '\d{4}-\d{2}-\d{2}T\d{6}Z' | head -1 || true)
      if [[ -n "${OBJ_DATE}" && "${OBJ_DATE}" < "${CUTOFF}" ]]; then
        aws s3 rm "s3://${BACKUP_S3_BUCKET}/${S3_PREFIX}/${KEY}"
        echo "[backup] Deleted old backup: ${KEY}"
      fi
    done

echo "[backup] Done."
