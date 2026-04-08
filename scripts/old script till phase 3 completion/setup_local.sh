#!/usr/bin/env bash
set -euo pipefail

# ==================================================================
# Garuda Phase 1 - Local Ubuntu Setup Script
# ==================================================================

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Logging functions ---
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

# --- Check if running with sudo ---
if [ "$EUID" -eq 0 ]; then
    error "Please do not run this script as root. Run as a normal user with sudo privileges."
fi

# --- Detect Ubuntu version ---
if ! command -v lsb_release &> /dev/null; then
    error "lsb_release not found. This script is intended for Ubuntu."
fi
ubuntu_version=$(lsb_release -rs)
info "Detected Ubuntu $ubuntu_version"

# --- Check for required commands ---
for cmd in curl git python3; do
    if ! command -v $cmd &> /dev/null; then
        error "$cmd not found. Please install it first."
    fi
done

# --- Configuration (modify if needed) ---
DB_NAME="garuda"
DB_USER="garuda"
DB_PASS="change_this_local_password"
PROJECT_ROOT="$(pwd)"
VENV_DIR="$PROJECT_ROOT/venv"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

# --- 1. Install system packages ---
info "Updating package list and installing system dependencies..."
sudo apt update
sudo apt install -y \
    python3-pip python3-venv \
    postgresql postgresql-contrib \
    redis-server \
    build-essential libpq-dev \
    nginx \
    curl wget git

# --- 2. Start and enable services ---
info "Starting PostgreSQL and Redis..."
sudo systemctl enable postgresql redis-server nginx
sudo systemctl start postgresql redis-server nginx

# --- 3. Create PostgreSQL database and user ---
info "Creating PostgreSQL database and user..."
# Check if user already exists
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    warn "User $DB_USER already exists. Skipping creation."
else
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
fi

if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    warn "Database $DB_NAME already exists. Skipping creation."
else
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
fi
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# --- 4. Create directory structure ---
info "Creating project directories..."
mkdir -p data/uploads data/processed data/quarantine data/backups logs
touch logs/app.log logs/audit.jsonl logs/error.log

# --- 5. Python virtual environment ---
if [ -d "$VENV_DIR" ]; then
    warn "Virtual environment already exists at $VENV_DIR. Reusing."
else
    info "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

info "Activating virtual environment and installing Python packages..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip

if [ -f "$REQUIREMENTS_FILE" ]; then
    pip install -r "$REQUIREMENTS_FILE"
else
    error "requirements.txt not found in $PROJECT_ROOT"
fi

# --- 6. Environment configuration ---
if [ -f "$ENV_FILE" ]; then
    warn ".env already exists. Skipping creation."
else
    if [ -f "$ENV_EXAMPLE" ]; then
        info "Creating .env from .env.example..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        # Replace placeholders with actual values
        sed -i "s|postgresql+asyncpg://garuda:change_this_local_password@localhost:5432/garuda|postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME|g" "$ENV_FILE"
        sed -i "s|GARUDA_SECRET_KEY=replace_with_local_secret|GARUDA_SECRET_KEY=$(openssl rand -hex 32)|g" "$ENV_FILE"
        info "Updated .env with database credentials and generated secret key."
    else
        error ".env.example not found. Cannot create .env."
    fi
fi

# --- 7. Database initialization ---
info "Initializing database tables..."
if [ -f "$PROJECT_ROOT/src/db/init_db.py" ]; then
    python -m src.db.init_db
else
    error "init_db.py not found. Cannot initialize database."
fi

# --- 8. Optional: Systemd service ---
read -p "Do you want to install Garuda as a systemd service? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SERVICE_FILE="/etc/systemd/system/garuda.service"
    if [ -f "$SERVICE_FILE" ]; then
        warn "Service file already exists. Skipping."
    else
        info "Creating systemd service..."
        sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Garuda Local API
After=network.target postgresql.service redis-server.service

[Service]
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_DIR/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
        sudo systemctl daemon-reload
        sudo systemctl enable garuda
        sudo systemctl start garuda
        info "Garuda service installed and started."
    fi
fi

# --- 9. Optional: Nginx reverse proxy ---
read -p "Do you want to configure Nginx as a reverse proxy for Garuda? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    NGINX_CONF="/etc/nginx/sites-available/garuda"
    if [ -f "$NGINX_CONF" ]; then
        warn "Nginx config already exists. Skipping."
    else
        info "Creating Nginx configuration..."
        sudo tee "$NGINX_CONF" > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 60;
        proxy_send_timeout 300;
    }
}
EOF
        sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
        sudo nginx -t && sudo systemctl reload nginx
        info "Nginx configured and reloaded."
    fi
fi

# --- 10. Final instructions ---
info "Setup completed successfully!"
echo
echo "To run the development server manually:"
echo "  source venv/bin/activate"
echo "  uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000"
echo
echo "To test the API:"
echo "  curl http://localhost:8000/v1/health"
echo
if [ -f "/etc/systemd/system/garuda.service" ]; then
    echo "Garuda is running as a systemd service. Use:"
    echo "  sudo systemctl status garuda"
    echo "  sudo systemctl restart garuda"
fi
echo
echo "Remember to review and adjust .env if needed."