# Garuda Phase 3 Backup

## Restore Instructions

1. Create a new directory and extract the backup:
   ```bash
   mkdir garuda_restore
   cp -r * garuda_restore/
   cd garuda_restore
   ```

2. Set up virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements_backup.txt
   ```

3. Set up PostgreSQL and Redis as per original setup (see docs/phase1-local-setup.md).

4. Restore the database if you have a separate backup:
   ```bash
   psql -U garuda -h localhost -d garuda < garuda_db_backup.sql
   ```

5. Restart the server:
   ```bash
   ./scripts/run_dev.sh
   ```

## Backup contents
- Full source code (src/, scripts/, configs/, etc.)
- Requirements file
- Basic configuration templates (.env.example)
- No sensitive data (logs, uploads, models, .env) are included.

## Date of backup: Fri Apr  3 12:50:04 AM UTC 2026
