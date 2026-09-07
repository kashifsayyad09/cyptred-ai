terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state backend — replace bucket name before use
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "exam-guardian/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ai-exam-guardian"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
