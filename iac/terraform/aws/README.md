# Sovereign Shield Golden Image - AWS Terraform

This pack is a buyer-owned private cloud starting point for active-passive Sovereign Shield deployment.

It provisions:
- private security boundary for API nodes
- Redis replication group for JWT revocation, Oracle risk state, and quarantine state
- encrypted Postgres for metadata, policy, tenant, and admin state
- deployment notes for two Shield nodes behind a buyer load balancer

It does not claim a managed SaaS deployment. The buyer owns cloud account, DNS, TLS, secrets, container signing, and operational runbooks.

Example:

```bash
terraform -chdir=iac/terraform/aws init
terraform -chdir=iac/terraform/aws apply \
  -var 'vpc_id=vpc-xxxx' \
  -var 'private_subnet_ids=["subnet-a","subnet-b"]' \
  -var 'container_image=123456789012.dkr.ecr.ap-south-1.amazonaws.com/sovereign-shield:buyer'
```
