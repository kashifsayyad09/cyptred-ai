"""
Phase 11 — AWS Deployment tests.

Covers:
  - Terraform file structure (all required .tf files exist)
  - Terraform variables completeness
  - Terraform outputs contain required keys
  - docker-compose.prod.yml structure
  - deploy.sh script exists and contains required steps
  - migrate.sh exists
  - GitHub Actions deploy workflow exists and is correctly structured
  - .env.example contains deployment variables
  - .gitignore protects terraform.tfvars and credentials

All tests are pure file-inspection tests — no AWS credentials required.
"""

from __future__ import annotations

import os
import sys

import pytest

# ── path setup ────────────────────────────────────────────────────────────────

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BACKEND_ROOT)
INFRA_ROOT = os.path.join(REPO_ROOT, "infra")
TERRAFORM_ROOT = os.path.join(INFRA_ROOT, "terraform")
SCRIPTS_ROOT = os.path.join(REPO_ROOT, "scripts")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── 1. Terraform structure ────────────────────────────────────────────────────

class TestTerraformStructure:
    """Verify all required Terraform files exist."""

    def test_terraform_dir_exists(self):
        assert os.path.isdir(TERRAFORM_ROOT), "infra/terraform/ directory not found"

    def test_main_tf_exists(self):
        assert os.path.isfile(os.path.join(TERRAFORM_ROOT, "main.tf"))

    def test_variables_tf_exists(self):
        assert os.path.isfile(os.path.join(TERRAFORM_ROOT, "variables.tf"))

    def test_vpc_tf_exists(self):
        assert os.path.isfile(os.path.join(TERRAFORM_ROOT, "vpc.tf"))

    def test_security_groups_tf_exists(self):
        assert os.path.isfile(os.path.join(TERRAFORM_ROOT, "security_groups.tf"))

    def test_ec2_tf_exists(self):
        assert os.path.isfile(os.path.join(TERRAFORM_ROOT, "ec2.tf"))

    def test_rds_tf_exists(self):
        assert os.path.isfile(os.path.join(TERRAFORM_ROOT, "rds.tf"))

    def test_ecr_tf_exists(self):
        assert os.path.isfile(os.path.join(TERRAFORM_ROOT, "ecr.tf"))

    def test_outputs_tf_exists(self):
        assert os.path.isfile(os.path.join(TERRAFORM_ROOT, "outputs.tf"))

    def test_tfvars_example_exists(self):
        assert os.path.isfile(os.path.join(TERRAFORM_ROOT, "terraform.tfvars.example"))

    def test_user_data_template_exists(self):
        assert os.path.isfile(os.path.join(TERRAFORM_ROOT, "user_data.sh.tpl"))

    def test_readme_exists(self):
        assert os.path.isfile(os.path.join(TERRAFORM_ROOT, "README.md"))


# ── 2. Terraform content ──────────────────────────────────────────────────────

class TestTerraformContent:
    """Verify Terraform files contain required declarations."""

    def test_main_has_s3_backend(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "main.tf"))
        assert 'backend "s3"' in content

    def test_main_has_aws_provider(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "main.tf"))
        assert 'provider "aws"' in content

    def test_main_has_required_version(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "main.tf"))
        assert "required_version" in content

    def test_main_has_default_tags(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "main.tf"))
        assert "default_tags" in content

    def test_variables_has_aws_region(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "variables.tf"))
        assert 'variable "aws_region"' in content

    def test_variables_has_rds_password(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "variables.tf"))
        assert 'variable "rds_password"' in content

    def test_variables_rds_password_is_sensitive(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "variables.tf"))
        assert "sensitive   = true" in content

    def test_variables_has_github_org(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "variables.tf"))
        assert 'variable "github_org"' in content

    def test_vpc_has_vpc_resource(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "vpc.tf"))
        assert 'resource "aws_vpc"' in content

    def test_vpc_has_internet_gateway(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "vpc.tf"))
        assert 'resource "aws_internet_gateway"' in content

    def test_vpc_has_public_subnets(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "vpc.tf"))
        assert 'resource "aws_subnet" "public"' in content

    def test_vpc_has_private_subnets(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "vpc.tf"))
        assert 'resource "aws_subnet" "private"' in content

    def test_sg_rds_not_publicly_accessible(self):
        """RDS SG must only allow access from EC2 SG — not 0.0.0.0/0."""
        content = _read(os.path.join(TERRAFORM_ROOT, "security_groups.tf"))
        # Must reference EC2 security group, not internet
        assert "security_groups" in content
        # Must NOT allow MySQL from 0.0.0.0/0
        rds_section = content[content.find('resource "aws_security_group" "rds"'):]
        assert '0.0.0.0/0' not in rds_section.split('egress')[0]  # Before egress block

    def test_ec2_has_iam_instance_profile(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "ec2.tf"))
        assert "iam_instance_profile" in content

    def test_ec2_has_elastic_ip(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "ec2.tf"))
        assert 'resource "aws_eip"' in content

    def test_ec2_root_volume_encrypted(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "ec2.tf"))
        assert "encrypted             = true" in content

    def test_rds_not_publicly_accessible(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "rds.tf"))
        assert "publicly_accessible    = false" in content

    def test_rds_storage_encrypted(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "rds.tf"))
        assert "storage_encrypted     = true" in content

    def test_rds_has_deletion_protection(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "rds.tf"))
        assert "deletion_protection" in content

    def test_rds_is_mysql_8(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "rds.tf"))
        assert '"mysql"' in content
        assert '"8.0"' in content

    def test_ecr_has_four_repos(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "ecr.tf"))
        assert '"backend"' in content
        assert '"mcp"' in content
        assert '"rag"' in content
        assert '"frontend"' in content

    def test_ecr_scan_on_push_enabled(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "ecr.tf"))
        assert "scan_on_push = true" in content

    def test_ecr_has_lifecycle_policy(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "ecr.tf"))
        assert 'resource "aws_ecr_lifecycle_policy"' in content

    def test_ecr_has_github_oidc(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "ecr.tf"))
        assert "token.actions.githubusercontent.com" in content

    def test_ecr_oidc_not_wildcard(self):
        """OIDC condition must scope to specific repo, not *."""
        content = _read(os.path.join(TERRAFORM_ROOT, "ecr.tf"))
        assert "StringLike" in content
        assert "github_org" in content or "var.github_org" in content

    def test_outputs_has_ec2_public_ip(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "outputs.tf"))
        assert 'output "ec2_public_ip"' in content

    def test_outputs_has_rds_endpoint(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "outputs.tf"))
        assert 'output "rds_endpoint"' in content

    def test_outputs_rds_endpoint_sensitive(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "outputs.tf"))
        assert "sensitive   = true" in content

    def test_outputs_has_ecr_urls(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "outputs.tf"))
        assert "ecr_backend_url" in content
        assert "ecr_mcp_url" in content
        assert "ecr_rag_url" in content
        assert "ecr_frontend_url" in content

    def test_outputs_has_oidc_role_arn(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "outputs.tf"))
        assert "oidc_role_arn" in content

    def test_user_data_installs_docker(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "user_data.sh.tpl"))
        assert "docker" in content.lower()

    def test_user_data_has_systemd_service(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "user_data.sh.tpl"))
        assert "systemd" in content or "systemctl" in content

    def test_tfvars_example_has_rds_password_placeholder(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "terraform.tfvars.example"))
        assert "CHANGE_ME" in content

    def test_tfvars_example_has_ssh_cidr_placeholder(self):
        content = _read(os.path.join(TERRAFORM_ROOT, "terraform.tfvars.example"))
        assert "YOUR_IP_ADDRESS" in content


# ── 3. Production Docker Compose ───────────────────────────────────────────────

class TestDockerComposeProd:
    """Verify docker-compose.prod.yml is correctly structured for production."""

    COMPOSE = os.path.join(INFRA_ROOT, "docker-compose.prod.yml")

    def test_prod_compose_exists(self):
        assert os.path.isfile(self.COMPOSE)

    def test_uses_ecr_registry_variable(self):
        content = _read(self.COMPOSE)
        assert "ECR_REGISTRY" in content

    def test_uses_image_tag_variable(self):
        content = _read(self.COMPOSE)
        assert "IMAGE_TAG" in content

    def test_backend_depends_on_mcp_and_rag(self):
        content = _read(self.COMPOSE)
        # Find the actual "  backend:" service block (indented, not "exam-guardian-backend")
        idx = content.find("\n  backend:\n")
        assert idx >= 0, "backend service block not found"
        backend_section = content[idx:idx + 800]
        assert "mcp" in backend_section
        assert "rag" in backend_section

    def test_prometheus_not_on_public_port(self):
        """Prometheus must use expose (internal) not ports (public) in production."""
        content = _read(self.COMPOSE)
        # Find prometheus section
        prom_start = content.find("  prometheus:")
        prom_section = content[prom_start:prom_start + 400]
        # Should use expose, not ports
        assert "expose:" in prom_section
        # Should NOT have a public port binding
        assert '"9090:9090"' not in prom_section

    def test_grafana_not_on_public_port(self):
        """Grafana must use expose (internal) not ports (public) in production."""
        content = _read(self.COMPOSE)
        grafana_start = content.find("  grafana:")
        grafana_section = content[grafana_start:grafana_start + 500]
        assert "expose:" in grafana_section
        assert '"3001:3000"' not in grafana_section

    def test_all_services_have_healthcheck(self):
        content = _read(self.COMPOSE)
        services = ["nginx:", "frontend:", "backend:", "mcp:", "rag:"]
        for svc in services:
            idx = content.find(f"  {svc}")
            if idx >= 0:
                section = content[idx:idx + 600]
                assert "healthcheck:" in section, f"Service {svc} missing healthcheck"

    def test_all_services_have_restart_policy(self):
        content = _read(self.COMPOSE)
        assert content.count("restart: unless-stopped") >= 6

    def test_logging_configured(self):
        content = _read(self.COMPOSE)
        assert "json-file" in content
        assert "max-size" in content

    def test_grafana_sign_up_disabled(self):
        content = _read(self.COMPOSE)
        assert "GF_USERS_ALLOW_SIGN_UP=false" in content

    def test_rag_vectorstore_volume_defined(self):
        content = _read(self.COMPOSE)
        assert "rag-vectorstore:" in content


# ── 4. Deploy scripts ─────────────────────────────────────────────────────────

class TestDeployScripts:
    """Verify deploy and migrate scripts exist and have correct content."""

    def test_deploy_sh_exists(self):
        assert os.path.isfile(os.path.join(SCRIPTS_ROOT, "deploy.sh"))

    def test_migrate_sh_exists(self):
        assert os.path.isfile(os.path.join(SCRIPTS_ROOT, "migrate.sh"))

    def test_deploy_sh_has_ecr_login(self):
        content = _read(os.path.join(SCRIPTS_ROOT, "deploy.sh"))
        assert "ecr get-login-password" in content or "ecr-login" in content

    def test_deploy_sh_has_docker_compose_pull(self):
        content = _read(os.path.join(SCRIPTS_ROOT, "deploy.sh"))
        assert "docker compose" in content
        assert "pull" in content

    def test_deploy_sh_has_health_check(self):
        content = _read(os.path.join(SCRIPTS_ROOT, "deploy.sh"))
        assert "/health" in content

    def test_deploy_sh_has_set_e(self):
        """Script must use set -e to fail fast."""
        content = _read(os.path.join(SCRIPTS_ROOT, "deploy.sh"))
        assert "set -e" in content

    def test_deploy_sh_validates_env_file(self):
        content = _read(os.path.join(SCRIPTS_ROOT, "deploy.sh"))
        assert ".env" in content

    def test_migrate_sh_uses_required_env_vars(self):
        content = _read(os.path.join(SCRIPTS_ROOT, "migrate.sh"))
        assert "DB_HOST" in content
        assert "DB_PASSWORD" in content

    def test_migrate_sh_uses_schema_sql(self):
        content = _read(os.path.join(SCRIPTS_ROOT, "migrate.sh"))
        assert "schema.sql" in content


# ── 5. GitHub Actions Deploy Workflow ─────────────────────────────────────────

class TestGitHubActionsDeployWorkflow:
    """Verify the deploy workflow is correctly structured."""

    DEPLOY_WORKFLOW = os.path.join(REPO_ROOT, ".github", "workflows", "deploy.yml")

    def test_deploy_workflow_exists(self):
        assert os.path.isfile(self.DEPLOY_WORKFLOW)

    def test_triggers_on_ci_completion(self):
        content = _read(self.DEPLOY_WORKFLOW)
        assert "workflow_run" in content

    def test_allows_manual_dispatch(self):
        content = _read(self.DEPLOY_WORKFLOW)
        assert "workflow_dispatch" in content

    def test_gates_on_ci_success(self):
        content = _read(self.DEPLOY_WORKFLOW)
        assert "conclusion == 'success'" in content

    def test_uses_oidc_for_aws(self):
        content = _read(self.DEPLOY_WORKFLOW)
        assert "id-token: write" in content

    def test_deploys_via_ssh(self):
        content = _read(self.DEPLOY_WORKFLOW)
        assert "ssh" in content.lower()

    def test_runs_deploy_script(self):
        content = _read(self.DEPLOY_WORKFLOW)
        assert "deploy.sh" in content

    def test_verifies_health_after_deploy(self):
        content = _read(self.DEPLOY_WORKFLOW)
        assert "/health" in content

    def test_production_environment_set(self):
        content = _read(self.DEPLOY_WORKFLOW)
        assert "environment:" in content
        assert "production" in content

    def test_uses_ec2_host_secret(self):
        content = _read(self.DEPLOY_WORKFLOW)
        assert "EC2_HOST" in content

    def test_uses_ssh_key_secret(self):
        content = _read(self.DEPLOY_WORKFLOW)
        assert "EC2_SSH_PRIVATE_KEY" in content


# ── 6. Security: sensitive files protected ────────────────────────────────────

class TestSensitiveFilesProtected:
    """Verify .gitignore protects secrets and state files."""

    GITIGNORE = os.path.join(REPO_ROOT, ".gitignore")

    def test_gitignore_exists(self):
        assert os.path.isfile(self.GITIGNORE)

    def test_env_files_ignored(self):
        content = _read(self.GITIGNORE)
        assert ".env" in content

    def test_tfvars_ignored(self):
        content = _read(self.GITIGNORE)
        assert "*.tfvars" in content

    def test_tfstate_ignored(self):
        content = _read(self.GITIGNORE)
        assert "*.tfstate" in content

    def test_pem_keys_ignored(self):
        content = _read(self.GITIGNORE)
        assert "*.pem" in content

    def test_tfvars_example_NOT_ignored(self):
        """*.tfvars.example should be tracked (it's a template)."""
        content = _read(self.GITIGNORE)
        assert "!*.tfvars.example" in content

    def test_terraform_dot_dir_ignored(self):
        content = _read(self.GITIGNORE)
        assert ".terraform/" in content

    def test_no_actual_tfvars_committed(self):
        """terraform.tfvars (with real secrets) must not be in repo."""
        tfvars = os.path.join(TERRAFORM_ROOT, "terraform.tfvars")
        assert not os.path.isfile(tfvars), \
            "terraform.tfvars found in repo — this file may contain secrets and should be gitignored!"

    def test_no_actual_env_committed(self):
        """.env must not be committed to the repo root."""
        env_file = os.path.join(REPO_ROOT, ".env")
        assert not os.path.isfile(env_file), \
            ".env found in repo root — this file may contain secrets and must not be committed!"


# ── 7. .env.example completeness ──────────────────────────────────────────────

class TestEnvExampleDeploymentVars:
    """Verify .env.example contains deployment-related placeholders."""

    ENV_EXAMPLE = os.path.join(REPO_ROOT, ".env.example")

    def test_env_example_exists(self):
        assert os.path.isfile(self.ENV_EXAMPLE)

    def test_has_aws_region(self):
        content = _read(self.ENV_EXAMPLE)
        assert "AWS_REGION" in content

    def test_has_ecr_registry(self):
        content = _read(self.ENV_EXAMPLE)
        assert "ECR_REGISTRY" in content

    def test_has_image_tag(self):
        content = _read(self.ENV_EXAMPLE)
        assert "IMAGE_TAG" in content

    def test_has_rds_host_placeholder(self):
        content = _read(self.ENV_EXAMPLE)
        assert "rds.amazonaws.com" in content or "DB_HOST" in content

    def test_never_contains_real_secrets(self):
        """Verify the file only contains placeholder values."""
        content = _read(self.ENV_EXAMPLE)
        # These patterns would indicate real credentials
        forbidden = [
            "sk-",          # OpenAI-style key
            "gsk_",         # Groq key prefix
            "nvapi-",       # NVIDIA key prefix
            "AKIA",         # AWS access key
        ]
        for pattern in forbidden:
            assert pattern not in content, \
                f"Possible real credential found in .env.example: {pattern}"

    def test_groq_key_is_placeholder(self):
        content = _read(self.ENV_EXAMPLE)
        assert "CHANGE_ME_GROQ_API_KEY" in content or "CHANGE_ME" in content
