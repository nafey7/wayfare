# Strapi RDS Module
# Creates PostgreSQL RDS instance for Strapi CMS

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.19"
    }
  }
}

# DB Subnet Group (uses existing private subnets)
resource "aws_db_subnet_group" "strapi" {
  name        = "${var.environment}-strapi-db-subnet-group"
  description = "Subnet group for Strapi RDS in ${var.environment}"
  subnet_ids  = var.private_subnet_ids

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-strapi-db-subnet-group"
    }
  )
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "strapi" {
  identifier = "${var.environment}-strapi-postgres"

  # Engine
  engine               = "postgres"
  engine_version       = "16"
  instance_class       = var.instance_class
  parameter_group_name = aws_db_parameter_group.strapi.name

  # Storage
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database
  db_name  = var.db_name
  username = var.db_username

  # RDS-managed password (stored in Secrets Manager automatically)
  manage_master_user_password = true

  # Networking
  db_subnet_group_name   = aws_db_subnet_group.strapi.name
  vpc_security_group_ids = [var.rds_security_group_id]
  publicly_accessible    = false
  port                   = 5432

  # Availability
  multi_az = var.multi_az

  # Backups
  backup_retention_period = var.backup_retention_period
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  # Protection
  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.environment}-strapi-final-snapshot"
  copy_tags_to_snapshot     = true

  # Monitoring
  performance_insights_enabled = true

  # Apply
  apply_immediately = var.apply_immediately

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-strapi-postgres"
    }
  )
}

# Parameter Group
resource "aws_db_parameter_group" "strapi" {
  name        = "${var.environment}-strapi-postgres16"
  family      = "postgres16"
  description = "Parameter group for Strapi PostgreSQL 16 in ${var.environment}"

  parameter {
    name  = "log_connections"
    value = "1"
  }

  # Disable forced SSL for within-VPC connections
  parameter {
    name  = "rds.force_ssl"
    value = "0"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-strapi-postgres16-params"
    }
  )
}
