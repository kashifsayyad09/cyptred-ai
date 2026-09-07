# AI Exam Guardian — Terraform Infrastructure

> **Purpose:** Provisions the full AWS infrastructure for AI Exam Guardian on EC2 + RDS MySQL.
>
> **NOT for EKS.** Architecture is designed to be EKS-migration-ready but the initial deployment uses EC2 + Docker Compose.

## Prerequisites

- Terraform >= 1.6
- AWS CLI configured (`aws configure`)
- An existing Route 53 hosted zone (optional — for DNS)
- An ACM certificate ARN (optional — for HTTPS)

## Usage

```bash
# 1. Create S3 backend bucket (once, manually or via bootstrap script)
aws s3 mb s3://your-terraform-state-bucket --region us-east-1

# 2. Copy and fill variables
cp terraform.tfvars.example terraform.tfvars

# 3. Initialise
terraform init

# 4. Plan
terraform plan -out=tfplan

# 5. Apply
terraform apply tfplan
```

## Variables

See `variables.tf` and `terraform.tfvars.example`.

## Outputs

After `terraform apply`:

- `ec2_public_ip` — EC2 instance public IP
- `rds_endpoint` — RDS MySQL endpoint (private)
- `ecr_backend_url` — ECR repository URL for backend image
- `ecr_mcp_url` — ECR repository URL for MCP image
- `ecr_rag_url` — ECR repository URL for RAG image
- `ecr_frontend_url` — ECR repository URL for frontend image
- `oidc_role_arn` — IAM role ARN for GitHub Actions OIDC

## Security

- RDS is in a private subnet — not publicly accessible
- EC2 security group allows only 80/443 from internet
- EC2 security group allows 22 (SSH) from your IP only
- RDS security group allows 3306 from EC2 security group only
- All secrets via EC2 instance user data or AWS Secrets Manager (not hardcoded)
