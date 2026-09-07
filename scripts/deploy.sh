#!/usr/bin/env bash
# =============================================================================
# AI Exam Guardian — EC2 Deploy Script
#
# Run this on the EC2 instance (or invoke remotely via GitHub Actions).
#
# Usage:
#   ./scripts/deploy.sh [IMAGE_TAG]
#
# Environment variables (from .env or set before running):
#   ECR_REGISTRY   — <account>.dkr.ecr.<region>.amazonaws.com
#   AWS_REGION     — AWS region
#   IMAGE_TAG      — Docker image tag to deploy (default: latest)
# =============================================================================

set -euo pipefail

DEPLOY_DIR="/opt/exam-guardian"
COMPOSE_FILE="docker-compose.prod.yml"
LOG_FILE="/var/log/exam-guardian-deploy.log"

IMAGE_TAG="${1:-${IMAGE_TAG:-latest}}"

log() {
    echo "[$(date '+%Y-%m-%dT%H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# ── Validate environment ───────────────────────────────────────────────────────
log "=== AI Exam Guardian Deploy ==="
log "Image tag: $IMAGE_TAG"
log "Deploy dir: $DEPLOY_DIR"

if [[ ! -f "$DEPLOY_DIR/.env" ]]; then
    log "ERROR: $DEPLOY_DIR/.env not found. Cannot deploy without environment configuration."
    exit 1
fi

if [[ ! -f "$DEPLOY_DIR/$COMPOSE_FILE" ]]; then
    log "ERROR: $DEPLOY_DIR/$COMPOSE_FILE not found."
    exit 1
fi

# ── ECR Login ─────────────────────────────────────────────────────────────────
log "Authenticating with ECR..."
AWS_REGION="${AWS_REGION:-$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo us-east-1)}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${ECR_REGISTRY:-${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com}"

aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$ECR_REGISTRY"

export ECR_REGISTRY IMAGE_TAG

# ── Pull latest images ─────────────────────────────────────────────────────────
log "Pulling images (tag: $IMAGE_TAG)..."
cd "$DEPLOY_DIR"
docker compose -f "$COMPOSE_FILE" pull

# ── Zero-downtime rolling update ──────────────────────────────────────────────
log "Deploying services..."

# Bring up infrastructure services first (they have no external dependencies)
docker compose -f "$COMPOSE_FILE" up -d --no-recreate mcp rag prometheus grafana

# Wait for MCP and RAG to be healthy before restarting backend
log "Waiting for MCP and RAG health..."
timeout 60 bash -c 'until docker compose -f docker-compose.prod.yml ps mcp | grep -q healthy; do sleep 3; done' || true
timeout 60 bash -c 'until docker compose -f docker-compose.prod.yml ps rag | grep -q healthy; do sleep 3; done' || true

# Restart backend with new image
docker compose -f "$COMPOSE_FILE" up -d --force-recreate backend

# Wait for backend to be healthy
log "Waiting for backend health..."
timeout 90 bash -c 'until docker compose -f docker-compose.prod.yml ps backend | grep -q healthy; do sleep 5; done' || {
    log "WARNING: Backend did not reach healthy state within 90s — check logs"
}

# Restart frontend and nginx
docker compose -f "$COMPOSE_FILE" up -d --force-recreate frontend
sleep 5
docker compose -f "$COMPOSE_FILE" up -d --force-recreate nginx

# ── Verify deployment ─────────────────────────────────────────────────────────
log "Verifying deployment..."
sleep 10

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health 2>/dev/null || echo "000")
if [[ "$HTTP_STATUS" == "200" ]]; then
    log "✓ Health check passed (HTTP $HTTP_STATUS)"
else
    log "✗ Health check FAILED (HTTP $HTTP_STATUS) — deployment may have issues"
    log "  Check: docker compose -f $COMPOSE_FILE logs backend"
    exit 1
fi

# ── Clean up old images ───────────────────────────────────────────────────────
log "Pruning old Docker images..."
docker image prune -f --filter "until=72h" || true

log "=== Deploy complete. Tag: $IMAGE_TAG ==="
