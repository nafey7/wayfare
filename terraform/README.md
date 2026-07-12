# Voya Terraform Infrastructure

Infrastructure as Code for the Voya travel platform using Terraform.

## Quick Start

**First-time setup:**
```bash
# 1. Create backend (one-time, shared across all environments)
cd terraform/backend-setup
terraform init && terraform apply

# 2. Deploy staging environment
cd ../environments/staging
terraform init
terraform plan
terraform apply

# 3. Set secrets (see docs/TERRAFORM.md for complete list)
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/MONGODB_URI \
  --secret-string "your-mongodb-uri" \
  --profile voya-poweruser
```

**Subsequent deployments:**
```bash
cd terraform/environments/staging
terraform plan
terraform apply
```

## Structure

```
terraform/
├── modules/              # Reusable infrastructure modules
│   ├── networking/       # VPC, subnets, NAT, IGW, VPC endpoints
│   ├── security/         # Security groups
│   ├── iam/              # IAM roles and policies
│   ├── ecr/              # ECR container registry
│   ├── logs/             # CloudWatch log groups
│   ├── secrets/          # AWS Secrets Manager
│   ├── alb/              # Application Load Balancer
│   └── ecs/              # ECS cluster, service, task definition
├── environments/
│   ├── staging/          # Staging environment configuration
│   └── production/       # Production environment (future)
└── backend-setup/        # Initial backend setup (S3 + DynamoDB)
```

## Common Commands

```bash
# View infrastructure
terraform show
terraform state list
terraform output

# Update infrastructure
terraform plan
terraform apply

# Deploy new application version
aws ecs update-service \
  --cluster staging-cluster \
  --service staging-fastapi-react-service \
  --force-new-deployment \
  --profile voya-poweruser

# View logs
aws logs tail /ecs/staging-voya-backend --follow --profile voya-poweruser

# Check service status
aws ecs describe-services \
  --cluster staging-cluster \
  --services staging-fastapi-react-service \
  --profile voya-poweruser
```

## Documentation

**Complete guides:**
- **[Terraform Setup & Management](../docs/TERRAFORM.md)** - Comprehensive infrastructure guide
- **[Deployment Runbook](../docs/DEPLOYMENT.md)** - Operational procedures, rollback, monitoring
- **[Staging Environment Guide](environments/staging/README.md)** - Terraform variables and configuration

**Quick reference:**
- Prerequisites: Terraform ≥1.6.0, AWS CLI, Docker
- AWS Profile: `voya-poweruser` or `voya-admin`
- State Backend: S3 (`voya-terraform-state-155304839180`)
- Staging Infrastructure: ~45 AWS resources (~$50-80/month)

## Environment-Specific Configuration

Each environment has its own directory with:
- `main.tf` - Infrastructure orchestration
- `variables.tf` - Variable definitions
- `terraform.tfvars` - Environment-specific values (committed)
- `outputs.tf` - Deployment information

See [environments/staging/README.md](environments/staging/README.md) for detailed configuration guide.

## CI/CD Integration

GitHub Actions workflow: `.github/workflows/deploy-staging.yml`

**Automated on push to `develop`:**
1. Quality checks (Ruff, MyPy, Bandit, pytest)
2. Build Docker image
3. Push to ECR
4. Deploy to ECS
5. Run E2E tests

**Manual workflow dispatch:** Trigger from GitHub Actions UI

## Troubleshooting

**ECS tasks not starting?**
```bash
# Check logs
aws logs tail /ecs/staging-voya-backend --follow --profile voya-poweruser

# Verify secrets populated
aws secretsmanager get-secret-value \
  --secret-id staging/Voya-fastAPI/MONGODB_URI \
  --profile voya-poweruser
```

**State lock timeout?**
```bash
# Check for stuck locks
aws dynamodb scan --table-name voya-terraform-locks --profile voya-poweruser

# Force unlock (only if no other terraform running)
terraform force-unlock LOCK_ID
```

**More troubleshooting:** See [docs/TERRAFORM.md](../docs/TERRAFORM.md) and [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)

## Support

- **Comprehensive Guide**: [docs/TERRAFORM.md](../docs/TERRAFORM.md)
- **Deployment Runbook**: [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)
- **Module Documentation**: Each module has a README.md
- **Questions**: Create GitHub issue with `terraform` label

---

**Last Updated**: October 2025
**Status**: Staging environment deployed and operational
