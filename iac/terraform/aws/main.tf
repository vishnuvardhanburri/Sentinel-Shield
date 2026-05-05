terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name = var.project_name
}

resource "aws_security_group" "shield" {
  name        = "${local.name}-private-sg"
  description = "Private network boundary for Sovereign Shield active-passive nodes"
  vpc_id      = var.vpc_id

  ingress {
    description = "mTLS ingress from buyer load balancer only"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    description = "Private egress for database, Redis, and local model network"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["10.0.0.0/8"]
  }
}

resource "aws_elasticache_subnet_group" "risk_state" {
  name       = "${local.name}-redis-subnets"
  subnet_ids = var.private_subnet_ids
}

resource "aws_elasticache_replication_group" "risk_state" {
  replication_group_id       = "${local.name}-risk"
  description                = "JWT revocation, Oracle risk, and quarantine state"
  engine                     = "redis"
  node_type                  = var.redis_node_type
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  subnet_group_name          = aws_elasticache_subnet_group.risk_state.name
  security_group_ids         = [aws_security_group.shield.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
}

resource "aws_db_subnet_group" "metadata" {
  name       = "${local.name}-postgres-subnets"
  subnet_ids = var.private_subnet_ids
}

resource "aws_db_instance" "metadata" {
  identifier              = "${local.name}-metadata"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = var.db_instance_class
  allocated_storage       = 50
  storage_encrypted       = true
  db_subnet_group_name    = aws_db_subnet_group.metadata.name
  vpc_security_group_ids  = [aws_security_group.shield.id]
  backup_retention_period = 7
  skip_final_snapshot     = false
  username                = "sovereign_admin"
  manage_master_user_password = true
}

# Buyer-owned ECS/EKS/VM deployment should run two shield nodes:
# - active node serves production traffic
# - passive node tails ledger state and is promoted by load-balancer health checks
# The container image is supplied by var.container_image after buyer build/signing.
