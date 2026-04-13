# Changelog

All notable changes to VAT Bot are documented here.  
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [SemVer](https://semver.org/).

---

## [Unreleased] — Sprint 2 Stabilization (2026-01-xx)

Branch: `sprint-2-stabilization`  
Auditor: external security review  
Total commits on branch: 9 (P1–P11; P3/P6 were pre-done)

### Fixed
- **All models**: `SCHEMA = os.environ.get('DB_SCHEMA') or None` — empty `DB_SCHEMA` now means  
  *no schema prefix* instead of `"None.tablename"`. Fixes SQLite test compatibility and a latent  
  production bug when `DB_SCHEMA` is unset. (P9, commit `168207d`)
- **`auth/models.py`, `crm/models.py`, `app/mailguard/models.py`, `app/teamguard/models.py`,  
  `app/pentesting/models.py`, `crm/osint_models.py`**: all ForeignKey f-strings use `_sp` helper  
  so they remain correct when SCHEMA is None. (P9)
- **`tests/conftest.py`**: `DB_SCHEMA=''` (was `'public'`) so SQLite tests never see schema-prefixed  
  table names. (P9)
- **CI `pip-audit`**: removed silent fallback; now `pip-audit --strict` — fails on any CVE. (P7, `f7082fc`)

### Added
- **`services/security_helpers.py`**: `require_same_origin` decorator — rejects cross-origin POSTs  
  on CSRF-exempt JSON endpoints. Applied to `/api/chat/message` and `/api/sales-chat`. (P2, `76b3b2a`)
- **`config.py`** (`ALLOWED_ORIGINS`): whitelist for same-origin check, set via env var. (P2)
- **`app/mailguard/scheduler.py`**: `setup_mailguard_scheduler()` — APScheduler background  
  IMAP poller, runs every `MAILGUARD_POLL_INTERVAL_MINUTES` (default 5 min). (P4, `5e7b3ec`)
- **`crm/monitoring_scheduler.py`**: `init_monitoring_scheduler()` — daily CRM re-check  
  at 03:00 (configurable via `CRM_MONITORING_HOUR`). (P4)
- **`application.py`** (`create_app`): defense-in-depth check — raises `RuntimeError` if  
  `SECRET_KEY` is empty/insecure in production. (P1, `b23ad83`)
- **`application.py`** (`promote-admin` CLI): `flask promote-admin <email>` grants admin rights  
  to an existing user. (P9)
- **`GET /auth/export-data`**: GDPR Art. 20 data portability endpoint — returns  
  `vatbot_userdata_<id>.json` with profile, subscriptions and verification history. (P10, `d717cce`)
- **`POST /auth/delete-account`**: was already implemented (full cascade delete). Confirmed  
  GDPR-compliant. (P10)
- **`requirements.in`**: source-of-truth for direct dependencies (48 packages). (P8, `e305675`)
- **CI quality job**: installs pip-tools, compiles `requirements.in`, diffs against  
  `requirements.txt` and emits a warning if out of sync. (P8)
- **`scripts/backup_db.sh`**: `pg_dump | gzip | aws s3 cp` with 30-day retention rotation. (P11, `30a6cab`)
- **`docs/BACKUP.md`**: setup guide, restore procedure, S3 least-privilege IAM policy. (P11)
- **`pyproject.toml`**: complete `[tool.ruff]` and `[tool.bandit]` sections —  
  ruff rules: `E,F,W,I,B,C4,UP,S`; bandit skips `B101,B311`. (P7)
- **`tests/test_smoke.py`**: `TestProductionConfigGuards` (SECRET_KEY guard) +  
  `TestChatbotOriginProtection` (origin check). 21 total tests, 25% coverage. (P1/P2/P9)

### Changed
- **`application.py`**: config object now instantiated at `create_app()` call time  
  (`_conf_cls()` not `from_object(_conf_cls)`) so `ProductionConfig.__init__` validation  
  runs immediately. (P1)
- **`config.py`** `TestingConfig`: `SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}`  
  (removed `pool_size`/`max_overflow` which are invalid for SQLite). (P1)
- **`app/mailguard/rules.py`, `app/services/phoneintel.py`, `programmatic/routes.py`**:  
  `print()` replaced with `logger`/`logging.warning`. (P5, `ac13fac`)
- **`admin/routes.py`** `/scheduler/status`: now reports all three schedulers  
  (`monitoring`, `mailguard`, `crm_monitoring`). (P4)
- **`requirements.txt`**: pinned `pip-tools==7.4.1` as dev dependency. (P8)

### Already Completed Before This Sprint
- P3: MailGuard password encryption (Fernet in `app/mailguard/oauth.py`) — was production-ready.
- P6: SMTP config deduplication (`MAIL_*` canonical, `SMTP_*` aliases) — completed in Sprint 1.

---

## [0.2.0] — Sprint 1 Refactor (2025-12-xx)

- Refactored `application.py` 958 → 490 lines
- Added CI/CD pipeline (`.github/workflows/ci.yml`)
- Pre-commit hooks: ruff + bandit
- Logging infrastructure (`python-json-logger`)
- Dependency updates (Flask 3.0.3, SQLAlchemy 2.0.35)

## [0.1.0] — Sprint 0 Security Baseline

- Fixed `/make-admin` unauthenticated privilege escalation
- Removed `debug=True` from production boot
- Added `ProductionConfig` env-var validation
- Added `/healthz` and `/readyz` probe endpoints
- Rate limiting (Flask-Limiter)
- Fixed encoding issues (UTF-8 everywhere)
