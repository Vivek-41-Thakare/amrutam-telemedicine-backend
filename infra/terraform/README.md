# Terraform scaffold

This directory reserves the Infrastructure as Code deliverable. Choose the target cloud and region before defining production resources. A real deployment should provision network boundaries, private database access, managed secrets, managed PostgreSQL/Redis, application runtime, TLS ingress, monitoring, and encrypted remote Terraform state.

Do not commit state files, cloud credentials, or real secrets. Validate with `terraform fmt -check`, `terraform init -backend=false`, and `terraform validate` after provider and resource configuration is added. This scaffold does not yet provision cloud infrastructure.
