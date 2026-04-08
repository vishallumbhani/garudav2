-- Migration: Add users and alerts tables
-- Run this against your PostgreSQL garuda database

-- Users table for JWT authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    tenant_id VARCHAR(100) DEFAULT 'default',
    enabled BOOLEAN DEFAULT TRUE,
    must_change_password BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);
CREATE INDEX IF NOT EXISTS ix_users_tenant_role ON users(tenant_id, role);

-- Alerts table for alert management
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(2000),
    context JSONB,
    tenant_id VARCHAR(100),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_alerts_tenant_severity ON alerts(tenant_id, severity);
CREATE INDEX IF NOT EXISTS ix_alerts_created_at ON alerts(created_at);

-- Create default admin user (password: Admin@Garuda1)
-- Change this immediately after first login!
INSERT INTO users (username, email, password_hash, role, tenant_id, enabled)
VALUES (
    'admin',
    'admin@garuda.local',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- password: secret
    'admin',
    'default',
    TRUE
) ON CONFLICT (username) DO NOTHING;

-- Note: Update the password hash above with a real bcrypt hash
-- Generate with: python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('YourPassword'))"
