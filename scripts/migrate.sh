#!/usr/bin/env bash
# =============================================================================
# AI Exam Guardian — Database Migration Script
#
# Runs schema.sql against the target MySQL database.
# Execute after RDS is provisioned and before first application start.
#
# Usage:
#   export DB_HOST=your-rds-endpoint.rds.amazonaws.com
#   export DB_USER=exam_guardian_admin
#   export DB_PASSWORD=your-password
#   export DB_NAME=exam_guardian
#   ./scripts/migrate.sh
# =============================================================================

set -euo pipefail

DB_HOST="${DB_HOST:?DB_HOST is required}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:?DB_USER is required}"
DB_PASSWORD="${DB_PASSWORD:?DB_PASSWORD is required}"
DB_NAME="${DB_NAME:-exam_guardian}"

SCHEMA_FILE="$(dirname "$0")/../backend/schema.sql"

if [[ ! -f "$SCHEMA_FILE" ]]; then
    echo "ERROR: schema.sql not found at $SCHEMA_FILE"
    exit 1
fi

echo "Running database migration..."
echo "  Host:     $DB_HOST:$DB_PORT"
echo "  Database: $DB_NAME"
echo "  User:     $DB_USER"
echo "  Schema:   $SCHEMA_FILE"

mysql \
    -h "$DB_HOST" \
    -P "$DB_PORT" \
    -u "$DB_USER" \
    --password="$DB_PASSWORD" \
    < "$SCHEMA_FILE"

echo "✓ Migration complete."
