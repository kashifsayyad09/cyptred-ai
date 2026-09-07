#!/bin/bash
# AI Exam Guardian — EC2 Bootstrap Script
# This script runs once on first boot to install Docker and pull the application.
# Rendered by Terraform with project variables substituted.

set -euo pipefail
exec > >(tee /var/log/exam-guardian-bootstrap.log | logger -t exam-guardian-bootstrap) 2>&1

echo "=== AI Exam Guardian bootstrap starting ==="
echo "Region: ${aws_region} | Project: ${project_name} | Env: ${environment}"

# ── System update ──────────────────────────────────────────────────────────────
apt-get update -y
apt-get upgrade -y
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    awscli \
    jq \
    unzip

# ── Docker install ─────────────────────────────────────────────────────────────
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

# Add ubuntu user to docker group (for manual deploys via SSH)
usermod -aG docker ubuntu

# ── Application directory ──────────────────────────────────────────────────────
mkdir -p /opt/exam-guardian
chown ubuntu:ubuntu /opt/exam-guardian

# ── ECR login helper (runs before each docker compose pull) ───────────────────
cat > /usr/local/bin/ecr-login.sh << 'ECRSCRIPT'
#!/bin/bash
AWS_REGION=$(ec2-metadata --availability-zone 2>/dev/null | sed 's/[a-z]$//' || echo "${aws_region}")
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
ECRSCRIPT
chmod +x /usr/local/bin/ecr-login.sh

# ── Systemd service for the application ──────────────────────────────────────
cat > /etc/systemd/system/exam-guardian.service << 'SYSTEMD'
[Unit]
Description=AI Exam Guardian Application
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/exam-guardian
EnvironmentFile=/opt/exam-guardian/.env
ExecStartPre=/usr/local/bin/ecr-login.sh
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d --pull always
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
StandardOutput=journal
StandardError=journal
SyslogIdentifier=exam-guardian

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload
systemctl enable exam-guardian

echo "=== Bootstrap complete. Deploy application via: ==="
echo "  1. Copy .env and docker-compose.prod.yml to /opt/exam-guardian/"
echo "  2. sudo systemctl start exam-guardian"
