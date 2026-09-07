# ── Ubuntu 22.04 LTS AMI (latest in region) ───────────────────────────────────

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  ami_id = var.ec2_ami_id != "" ? var.ec2_ami_id : data.aws_ami.ubuntu.id
}

# ── IAM instance profile for ECR pull ─────────────────────────────────────────

resource "aws_iam_role" "ec2_instance_role" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_instance_role.name
}

# ── User data bootstrap script ────────────────────────────────────────────────

locals {
  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    aws_region   = var.aws_region
    project_name = var.project_name
    environment  = var.environment
  })
}

# ── EC2 instance ──────────────────────────────────────────────────────────────

resource "aws_instance" "app" {
  ami                    = local.ami_id
  instance_type          = var.ec2_instance_type
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name
  key_name               = var.ec2_key_pair_name != "" ? var.ec2_key_pair_name : null

  user_data = local.user_data

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.ec2_root_volume_size_gb
    delete_on_termination = true
    encrypted             = true
  }

  # Prevent accidental replacement — change instance type via lifecycle
  lifecycle {
    ignore_changes = [ami, user_data]
  }

  tags = { Name = "${var.project_name}-app-server" }
}

# ── Elastic IP ────────────────────────────────────────────────────────────────

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"

  tags = { Name = "${var.project_name}-eip" }
}
