# ── General ────────────────────────────────────────────────────────────────────

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (production | staging)"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["production", "staging"], var.environment)
    error_message = "environment must be 'production' or 'staging'."
  }
}

variable "project_name" {
  description = "Project name used in resource naming and tagging"
  type        = string
  default     = "exam-guardian"
}

# ── Networking ─────────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (one per AZ, used by RDS)"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "availability_zones" {
  description = "AZs to use (must match subnet counts)"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "ssh_allowed_cidr" {
  description = "CIDR allowed to SSH into EC2 (your IP). Use /32 for a single IP."
  type        = string
  default     = "0.0.0.0/0"  # CHANGE THIS to your IP before production deploy
}

# ── EC2 ────────────────────────────────────────────────────────────────────────

variable "ec2_instance_type" {
  description = "EC2 instance type for the application server"
  type        = string
  default     = "t3.medium"
}

variable "ec2_key_pair_name" {
  description = "Name of an existing EC2 key pair for SSH access"
  type        = string
  default     = ""
}

variable "ec2_ami_id" {
  description = "AMI ID (Ubuntu 22.04 LTS in the target region). Leave empty to use data source lookup."
  type        = string
  default     = ""
}

variable "ec2_root_volume_size_gb" {
  description = "EC2 root EBS volume size in GB"
  type        = number
  default     = 30
}

# ── RDS ────────────────────────────────────────────────────────────────────────

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage_gb" {
  description = "RDS initial allocated storage in GB"
  type        = number
  default     = 20
}

variable "rds_max_allocated_storage_gb" {
  description = "RDS maximum allocated storage for autoscaling in GB"
  type        = number
  default     = 100
}

variable "rds_db_name" {
  description = "MySQL database name"
  type        = string
  default     = "exam_guardian"
}

variable "rds_username" {
  description = "MySQL master username"
  type        = string
  default     = "exam_guardian_admin"
  sensitive   = true
}

variable "rds_password" {
  description = "MySQL master password (min 16 chars, use a strong random value)"
  type        = string
  sensitive   = true
}

variable "rds_backup_retention_days" {
  description = "Number of days to retain automated RDS backups"
  type        = number
  default     = 7
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ for RDS (recommended for production)"
  type        = bool
  default     = false
}

# ── GitHub Actions OIDC ────────────────────────────────────────────────────────

variable "github_org" {
  description = "GitHub organisation or user name (e.g. 'my-org')"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name (e.g. 'ai-exam-guardian')"
  type        = string
  default     = "ai-exam-guardian"
}

# ── Application ────────────────────────────────────────────────────────────────

variable "domain_name" {
  description = "Domain name for the application (e.g. examguardian.example.com). Leave empty to use EC2 IP."
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS. Required if domain_name is set."
  type        = string
  default     = ""
}
