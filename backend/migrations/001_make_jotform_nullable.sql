-- Migration: Make jotform_submission_id nullable
-- Date: 2025-11-17
-- Purpose: Allow manual client creation without JotForm submission ID

-- For SQLite
-- SQLite requires recreating the table since ALTER COLUMN is limited

BEGIN TRANSACTION;

-- Create new clients table with nullable jotform_submission_id
CREATE TABLE clients_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    jotform_submission_id VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Copy existing data
INSERT INTO clients_new (id, name, jotform_submission_id, created_at, updated_at)
SELECT id, name, jotform_submission_id, created_at, updated_at
FROM clients;

-- Drop old table
DROP TABLE clients;

-- Rename new table
ALTER TABLE clients_new RENAME TO clients;

-- Recreate index if it exists
CREATE INDEX IF NOT EXISTS ix_clients_id ON clients(id);

COMMIT;
