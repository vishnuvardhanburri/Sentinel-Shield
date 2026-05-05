variable "project_name" {
  description = "Name prefix for Sovereign Shield resources."
  type        = string
  default     = "sovereign-shield"
}

variable "aws_region" {
  description = "AWS region for buyer-owned private deployment."
  type        = string
  default     = "ap-south-1"
}

variable "vpc_id" {
  description = "Buyer VPC where the golden image is deployed."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for API, Redis, Postgres, and local AI workers."
  type        = list(string)
}

variable "container_image" {
  description = "Buyer-built Sovereign Shield container image."
  type        = string
}

variable "db_instance_class" {
  description = "RDS instance class for metadata and policy state."
  type        = string
  default     = "db.t4g.medium"
}

variable "redis_node_type" {
  description = "ElastiCache node type for session, risk, and quarantine state."
  type        = string
  default     = "cache.t4g.small"
}
