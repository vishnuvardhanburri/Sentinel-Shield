output "redis_primary_endpoint" {
  value       = aws_elasticache_replication_group.risk_state.primary_endpoint_address
  description = "Use as REDIS_URL host for shared risk/quarantine/session state."
}

output "postgres_endpoint" {
  value       = aws_db_instance.metadata.address
  description = "Use as DATABASE_URL host for shared metadata and policy state."
}

output "shield_security_group_id" {
  value       = aws_security_group.shield.id
  description = "Attach this security group to Sovereign Shield API and worker nodes."
}
