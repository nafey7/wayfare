# Terraform Infrastructure Guide

Complete guide to managing Voya infrastructure with Terraform.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Deploying Staging Environment](#deploying-staging-environment)
- [Managing Infrastructure](#managing-infrastructure)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

The Voya platform uses Terraform to manage AWS infrastructure as code. This provides:
- **Version control** for infrastructure changes
- **Reproducible** environments (staging, production)
- **Automated** deployments via CI/CD
- **State management** with S3 and DynamoDB locking

**Infrastructure Components**:
- VPC with public/private subnets across 2 AZs
- Application Load Balancer with HTTPS support
- ECS Fargate cluster for containerized application
- ECR repository for Docker images
- Secrets Manager for sensitive configuration
- CloudWatch Logs for observability
- VPC Endpoints for cost optimization

## Prerequisites

### Required Tools

```bash
# Terraform
terraform --version  # Should be >= 1.6.0

# AWS CLI
aws --version  # Should be >= 2.0

# Docker (for building images)
docker --version
```

### AWS Credentials

Configure AWS profile with appropriate permissions:

```bash
# ~/.aws/credentials
[voya-poweruser]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
region = us-east-1
```

**Required IAM permissions**:
- VPC, EC2, ECS, ECR management
- IAM role creation
- Secrets Manager access
- CloudWatch Logs access
- Application Load Balancer management

## Initial Setup

### Step 1: Create Terraform Backend

The backend stores Terraform state remotely in S3 with DynamoDB locking.

```bash
cd terraform/backend-setup

# Initialize Terraform
terraform init

# Review planned changes
terraform plan

# Create S3 bucket and DynamoDB table
terraform apply

# Note the outputs (bucket name and table name)
terraform output
```

**This creates**:
- S3 bucket: `voya-terraform-state-155304839180`
- DynamoDB table: `voya-terraform-locks`

**⚠️ IMPORTANT**: Run this only once. These resources are shared across all environments.

### Step 2: Populate Secrets Manager

After deploying infrastructure, you must set secret values manually:

```bash
# Set each secret value
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/MONGODB_URI \
  --secret-string "mongodb+srv://user:pass@cluster.mongodb.net/voya_staging" \
  --profile voya-poweruser

aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/JWT_SECRET \
  --secret-string "your-super-secret-jwt-key-min-32-chars" \
  --profile voya-poweruser

# Repeat for: GEMINI_API_KEY, GOOGLE_API_KEY, SENDGRID_API_KEY, FLIGHTLOGIC_API_KEY
```

**Secrets to set**:
1. `MONGODB_URI` - MongoDB connection string
2. `JWT_SECRET` - JWT signing key (≥32 characters)
3. `GEMINI_API_KEY` - Google Gemini API key
4. `GOOGLE_API_KEY` - Google API key
5. `SENDGRID_API_KEY` - SendGrid email API key
6. `FLIGHTLOGIC_API_KEY` - FlightLogic travel API key

## Deploying Staging Environment

### Step 1: Review Configuration

```bash
cd terraform/environments/staging

# Review variables
cat terraform.tfvars

# Edit if needed (VPC CIDR, task size, etc.)
vim terraform.tfvars
```

### Step 2: Initialize Terraform

```bash
# Download providers and configure backend
terraform init

# You should see:
# "Successfully configured the backend "s3"!"
# "Terraform has been successfully initialized!"
```

### Step 3: Plan Changes

```bash
# Generate execution plan
terraform plan

# Review output carefully:
# - Resources to create (should be ~40+ resources)
# - No resources to destroy (on first run)
# - No unexpected changes
```

**Expected resources**:
- 1 VPC
- 6 subnets (2 public, 4 private across 2 AZs)
- 1 NAT Gateway + Elastic IP
- 1 Internet Gateway
- 5 VPC Endpoints
- 5 Security Groups
- 2 IAM Roles
- 1 ECR Repository
- 6 CloudWatch Log Groups
- 6 Secrets Manager Secrets
- 1 Application Load Balancer
- 1 Target Group
- 2 ALB Listeners
- 1 ECS Cluster
- 1 ECS Task Definition
- 1 ECS Service

### Step 4: Apply Changes

```bash
# Create infrastructure
terraform apply

# Review plan one more time
# Type "yes" to confirm

# Wait 5-10 minutes for completion
```

### Step 5: Note Outputs

```bash
# View all outputs
terraform output

# Key outputs:
terraform output alb_dns_name          # Load balancer URL
terraform output ecr_repository_url     # Docker image repository
terraform output nat_gateway_public_ip  # For whitelisting
```

### Step 6: Build and Deploy Application

```bash
# Get ECR repository URL
ECR_REPO=$(terraform output -raw ecr_repository_url)

# Build Docker image (from project root)
cd ../../..
docker build -t $ECR_REPO:latest \
  --build-arg REACT_APP_API_URL=https://staging.myvoya.ai/api .

# Login to ECR
aws ecr get-login-password --region us-east-1 --profile voya-poweruser | \
  docker login --username AWS --password-stdin $ECR_REPO

# Push image
docker push $ECR_REPO:latest

# Trigger ECS deployment
aws ecs update-service \
  --cluster staging-cluster \
  --service staging-fastapi-react-service \
  --force-new-deployment \
  --profile voya-poweruser

# Monitor deployment
aws ecs describe-services \
  --cluster staging-cluster \
  --services staging-fastapi-react-service \
  --profile voya-poweruser
```

### Step 7: Test Application

```bash
# Get ALB DNS name
ALB_DNS=$(terraform output -raw alb_dns_name)

# Test health endpoint
curl http://$ALB_DNS/health

# Expected: {"status":"healthy"}
```

## Managing Infrastructure

### Making Changes

```bash
cd terraform/environments/staging

# Edit variables or module configuration
vim terraform.tfvars

# Preview changes
terraform plan

# Apply changes
terraform apply
```

### Updating ECS Task (after code changes)

```bash
# Build new image with tag
docker build -t $ECR_REPO:v1.2.3 .
docker push $ECR_REPO:v1.2.3

# Update terraform.tfvars
# container_image_tag = "v1.2.3"

# Apply changes
terraform plan
terraform apply
```

### Scaling ECS Service

```bash
# Edit terraform.tfvars
# ecs_desired_count = 2

terraform apply
```

### Viewing Current State

```bash
# List all resources
terraform state list

# Show specific resource
terraform state show module.ecs.aws_ecs_service.app

# Refresh state from AWS
terraform refresh

# View outputs
terraform output
```

### Destroying Infrastructure

```bash
# ⚠️ DANGEROUS - Destroys all resources
terraform destroy

# Review destruction plan carefully
# Type "yes" to confirm

# Note: This does NOT delete:
# - S3 state bucket
# - DynamoDB lock table
# - Docker images in ECR (delete manually)
```

## Troubleshooting

### Issue: Backend initialization fails

```bash
# Error: Failed to get existing workspaces

# Solution: Verify S3 bucket exists
aws s3 ls s3://voya-terraform-state-155304839180 --profile voya-poweruser

# If missing, run backend-setup first
cd terraform/backend-setup && terraform apply
```

### Issue: State lock timeout

```bash
# Error: Error acquiring the state lock

# Check for stuck locks
aws dynamodb scan \
  --table-name voya-terraform-locks \
  --profile voya-poweruser

# Force unlock (ONLY if no other terraform is running)
terraform force-unlock LOCK_ID
```

### Issue: ECS tasks not starting

```bash
# Check ECS service events
aws ecs describe-services \
  --cluster staging-cluster \
  --services staging-fastapi-react-service \
  --profile voya-poweruser \
  --query 'services[0].events[:5]'

# Check CloudWatch logs
aws logs tail /ecs/staging-voya-backend --follow --profile voya-poweruser

# Common causes:
# 1. Secrets not populated
# 2. Invalid Docker image
# 3. Insufficient task CPU/memory
# 4. Security group blocking traffic
```

### Issue: Cannot access application via ALB

```bash
# Check ALB target health
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw target_group_arn) \
  --profile voya-poweruser

# Check security group rules
aws ec2 describe-security-groups \
  --group-ids $(terraform output -raw alb_security_group_id) \
  --profile voya-poweruser
```

### Issue: Secrets not accessible by ECS

```bash
# Verify secret exists and has value
aws secretsmanager get-secret-value \
  --secret-id staging/Voya-fastAPI/MONGODB_URI \
  --profile voya-poweruser

# Check IAM role permissions
aws iam get-role-policy \
  --role-name staging-ecs-task-execution-role \
  --policy-name staging-ecs-secrets-access \
  --profile voya-poweruser
```

## Best Practices

### 1. Always Run Plan Before Apply

```bash
# GOOD
terraform plan
# Review output
terraform apply

# BAD
terraform apply -auto-approve
```

### 2. Use Version Control

```bash
# Commit terraform.tfvars changes
git add terraform/environments/staging/terraform.tfvars
git commit -m "chore: update staging ECS task size"
git push
```

### 3. Tag Resources Appropriately

All resources are automatically tagged with:
- `Environment=staging`
- `ManagedBy=Terraform`
- `Project=Voya`

### 4. Protect Critical Resources

```hcl
# In module configuration
lifecycle {
  prevent_destroy = true  # Prevents accidental deletion
}
```

### 5. Use Workspaces (Optional)

```bash
# Create workspace for feature testing
terraform workspace new feature-xyz

# Switch workspaces
terraform workspace select staging

# List workspaces
terraform workspace list
```

### 6. Regular State Backups

```bash
# Pull current state
terraform state pull > staging-state-$(date +%Y%m%d).json

# Store securely (encrypted, access-controlled)
```

### 7. Review Security

```bash
# Scan Terraform code for security issues
terraform init
terraform validate

# Use checkov or tfsec
checkov -d terraform/environments/staging
```

## CI/CD Integration

Terraform apply is NOT run in CI/CD automatically. Infrastructure changes require manual review.

**Workflow**:
1. Developer creates Terraform changes
2. CI runs `terraform fmt` and `terraform validate`
3. PR shows `terraform plan` output as comment
4. After approval, DevOps runs `terraform apply` locally
5. State stored in S3, tracked in git

**GitHub Actions workflow** (`.github/workflows/terraform-plan.yml`):
```yaml
# TODO: Create workflow for automated planning
```

## Additional Resources

- **AWS Documentation**: https://docs.aws.amazon.com/ecs/
- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **Project Architecture**: See `docs/ARCHITECTURE.md`
- **Deployment Runbook**: See `docs/DEPLOYMENT.md`

---

**Last Updated**: October 2025
**Maintainer**: DevOps Team
