# ── RDS Subnet Group (private subnets) ────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name        = "${var.project_name}-db-subnet-group"
  description = "Subnet group for AI Exam Guardian RDS MySQL"
  subnet_ids  = aws_subnet.private[*].id

  tags = { Name = "${var.project_name}-db-subnet-group" }
}

# ── RDS Parameter Group ────────────────────────────────────────────────────────

resource "aws_db_parameter_group" "mysql8" {
  name        = "${var.project_name}-mysql8"
  family      = "mysql8.0"
  description = "AI Exam Guardian MySQL 8.0 parameter group"

  # Enforce TLS for all connections
  parameter {
    name  = "require_secure_transport"
    value = "ON"
  }

  # Slow query log for observability
  parameter {
    name  = "slow_query_log"
    value = "1"
  }

  parameter {
    name  = "long_query_time"
    value = "2"
  }

  tags = { Name = "${var.project_name}-mysql8-params" }
}

# ── RDS MySQL Instance ─────────────────────────────────────────────────────────

resource "aws_db_instance" "mysql" {
  identifier = "${var.project_name}-mysql"

  # Engine
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = var.rds_instance_class
  parameter_group_name = aws_db_parameter_group.mysql8.name

  # Storage
  allocated_storage     = var.rds_allocated_storage_gb
  max_allocated_storage = var.rds_max_allocated_storage_gb
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database
  db_name  = var.rds_db_name
  username = var.rds_username
  password = var.rds_password

  # Network — PRIVATE, not publicly accessible
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = var.rds_multi_az

  # Backups
  backup_retention_period = var.rds_backup_retention_days
  backup_window           = "03:00-04:00"
  maintenance_window      = "Sun:04:00-Sun:05:00"

  # Deletion protection — set to true in production
  deletion_protection     = var.environment == "production"
  skip_final_snapshot     = var.environment != "production"
  final_snapshot_identifier = var.environment == "production" ? "${var.project_name}-final-snapshot" : null

  # Monitoring
  monitoring_interval          = 60
  monitoring_role_arn          = aws_iam_role.rds_monitoring.arn
  performance_insights_enabled = true

  # Auto minor version upgrades
  auto_minor_version_upgrade = true

  tags = { Name = "${var.project_name}-mysql" }
}

# ── RDS Enhanced Monitoring IAM Role ──────────────────────────────────────────

resource "aws_iam_role" "rds_monitoring" {
  name = "${var.project_name}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}
