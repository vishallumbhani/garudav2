#!/usr/bin/env bash
# Backup script for Garuda Phase 3 working state

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="../garuda_backup_phase3_${TIMESTAMP}"
PROJECT_ROOT="$(pwd)"

echo "Creating backup of Garuda Phase 3 to: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Copy project files excluding unnecessary directories
rsync -av --progress \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.ruff_cache' \
    --exclude='.coverage' \
    --exclude='logs/*.log' \
    --exclude='logs/*.jsonl' \
    --exclude='data/uploads/*' \
    --exclude='data/processed/*' \
    --exclude='data/quarantine/*' \
    --exclude='data/backups/*' \
    --exclude='data/ml/arjuna_review_queue.json' \
    --exclude='models/*.pkl' \
    --exclude='src/engines/arjuna/*.pkl' \
    --exclude='.env' \
    --exclude='*.pyc' \
    --exclude='.git' \
    ./ "$BACKUP_DIR/"

# Create a manifest of installed pip packages
source venv/bin/activate
pip freeze > "$BACKUP_DIR/requirements_backup.txt"
deactivate

# Create a README with instructions using echo (avoid heredoc issues)
README_FILE="$BACKUP_DIR/README_RESTORE.md"
echo "# Garuda Phase 3 Backup" > "$README_FILE"
echo "" >> "$README_FILE"
echo "## Restore Instructions" >> "$README_FILE"
echo "" >> "$README_FILE"
echo "1. Create a new directory and extract the backup:" >> "$README_FILE"
echo "   \`\`\`bash" >> "$README_FILE"
echo "   mkdir garuda_restore" >> "$README_FILE"
echo "   cp -r * garuda_restore/" >> "$README_FILE"
echo "   cd garuda_restore" >> "$README_FILE"
echo "   \`\`\`" >> "$README_FILE"
echo "" >> "$README_FILE"
echo "2. Set up virtual environment:" >> "$README_FILE"
echo "   \`\`\`bash" >> "$README_FILE"
echo "   python3 -m venv venv" >> "$README_FILE"
echo "   source venv/bin/activate" >> "$README_FILE"
echo "   pip install -r requirements_backup.txt" >> "$README_FILE"
echo "   \`\`\`" >> "$README_FILE"
echo "" >> "$README_FILE"
echo "3. Set up PostgreSQL and Redis as per original setup (see docs/phase1-local-setup.md)." >> "$README_FILE"
echo "" >> "$README_FILE"
echo "4. Restore the database if you have a separate backup:" >> "$README_FILE"
echo "   \`\`\`bash" >> "$README_FILE"
echo "   psql -U garuda -h localhost -d garuda < garuda_db_backup.sql" >> "$README_FILE"
echo "   \`\`\`" >> "$README_FILE"
echo "" >> "$README_FILE"
echo "5. Restart the server:" >> "$README_FILE"
echo "   \`\`\`bash" >> "$README_FILE"
echo "   ./scripts/run_dev.sh" >> "$README_FILE"
echo "   \`\`\`" >> "$README_FILE"
echo "" >> "$README_FILE"
echo "## Backup contents" >> "$README_FILE"
echo "- Full source code (src/, scripts/, configs/, etc.)" >> "$README_FILE"
echo "- Requirements file" >> "$README_FILE"
echo "- Basic configuration templates (.env.example)" >> "$README_FILE"
echo "- No sensitive data (logs, uploads, models, .env) are included." >> "$README_FILE"
echo "" >> "$README_FILE"
echo "## Date of backup: $(date)" >> "$README_FILE"

# Optionally back up the database (ask user)
read -p "Do you want to back up the PostgreSQL database? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    DB_BACKUP="$BACKUP_DIR/garuda_db_backup.sql"
    echo "Creating database backup to $DB_BACKUP"
    PGPASSWORD=change_this_local_password pg_dump -U garuda -h localhost garuda > "$DB_BACKUP"
    echo "Database backup completed."
else
    echo "Skipping database backup."
fi

echo "Backup completed successfully at: $BACKUP_DIR"
echo "To restore, copy the directory to a new location and follow README_RESTORE.md"
