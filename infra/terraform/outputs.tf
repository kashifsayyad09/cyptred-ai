# ── Terraform outputs ──────────────────────────────────────────────────────────

output "ec2_public_ip" {
  description = "EC2 Elastic IP — set this in your DNS A record"
  value       = aws_eip.app.public_ip
}

output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "rds_endpoint" {
  description = "RDS MySQL endpoint (private — only accessible from EC2)"
  value       = aws_db_instance.mysql.endpoint
  sensitive   = true
}

output "rds_port" {
  description = "RDS MySQL port"
  value       = aws_db_instance.mysql.port
}

output "ecr_backend_url" {
  description = "ECR URL for the backend image"
  value       = aws_ecr_repository.app["backend"].repository_url
}

output "ecr_mcp_url" {
  description = "ECR URL for the MCP image"
  value       = aws_ecr_repository.app["mcp"].repository_url
}

output "ecr_rag_url" {
  description = "ECR URL for the RAG image"
  value       = aws_ecr_repository.app["rag"].repository_url
}

output "ecr_frontend_url" {
  description = "ECR URL for the frontend image"
  value       = aws_ecr_repository.app["frontend"].repository_url
}

output "oidc_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC — set as AWS_OIDC_ROLE_ARN in GitHub secrets"
  value       = aws_iam_role.github_actions.arn
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "deployment_instructions" {
  description = "Next steps after terraform apply"
  value = <<-EOT
    ═══════════════════════════════════════════════════════════════
    AI Exam Guardian — Infrastructure deployed!
    ═══════════════════════════════════════════════════════════════

    1. Add the following to GitHub repository secrets:
       AWS_OIDC_ROLE_ARN = ${aws_iam_role.github_actions.arn}
       AWS_REGION        = ${var.aws_region}

    2. SSH to EC2:
       ssh ubuntu@${aws_eip.app.public_ip}

    3. Copy your .env file to /opt/exam-guardian/.env on EC2

    4. Run the deploy script:
       ./scripts/deploy.sh

    5. Application will be available at:
       http://${aws_eip.app.public_ip}

    RDS endpoint (internal): ${aws_db_instance.mysql.endpoint}
    ═══════════════════════════════════════════════════════════════
  EOT
}
