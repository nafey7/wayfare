# Terraform Staging Environment

This directory contains Terraform configuration for the Voya staging environment.

## 📚 Documentation

- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Complete deployment guide with secrets configuration
- **[README.md](./README.md)** (this file) - Terraform usage and best practices

## Quick Start

```bash
# Navigate to staging environment
cd terraform/environments/staging

# Initialize Terraform
terraform init

# Create local terraform.tfvars (optional, for personal AWS profile preference)
echo 'aws_profile = "your-profile-name"' > terraform.tfvars

# Plan deployment
terraform plan -var-file="staging.tfvars"

# Apply changes
terraform apply -var-file="staging.tfvars"
```

## File Structure

```
terraform/environments/staging/
├── main.tf              # Main infrastructure resources
├── variables.tf         # Variable definitions (with defaults)
├── outputs.tf           # Output values
├── staging.tfvars       # Environment-specific config (COMMITTED)
├── terraform.tfvars     # Local overrides (GITIGNORED)
└── README.md            # This file
```

## Configuration Files

### `staging.tfvars` (Committed)
Contains **environment-specific** configuration shared across the team:
- VPC CIDR, subnets, availability zones
- ECS task sizing (CPU, memory, desired count)
- ACM certificate ARN for staging.myvoya.ai
- Auto-scaling configuration
- Environment-specific tags

**This file IS committed to git** - everyone uses the same staging configuration.

### `terraform.tfvars` (Gitignored)
Contains **personal preferences** for local development:
- `aws_profile` - Your local AWS profile name
- Any other variable overrides for testing

**This file is NOT committed to git** - each developer has their own.

### `variables.tf`
Defines all variables with:
- Type constraints
- Descriptions
- Default values (where applicable)

## Usage Patterns

### Standard Workflow
```bash
# Use team configuration
terraform plan -var-file="staging.tfvars"
terraform apply -var-file="staging.tfvars"
```

### With Local Overrides
```bash
# Create terraform.tfvars with your preferences
echo 'aws_profile = "voya-admin"' > terraform.tfvars

# Terraform automatically loads terraform.tfvars + staging.tfvars
terraform plan -var-file="staging.tfvars"
terraform apply -var-file="staging.tfvars"
```

### Command-Line Overrides
```bash
# Override specific variables
terraform apply \
  -var-file="staging.tfvars" \
  -var="ecs_desired_count=2" \
  -var="enable_autoscaling=true"
```

## Variable Priority (Highest to Lowest)

1. Command-line `-var` flags
2. Command-line `-var-file` (last one wins)
3. `terraform.tfvars` (auto-loaded, gitignored)
4. `*.auto.tfvars` (auto-loaded alphabetically, gitignored)
5. Environment variables (`TF_VAR_name`)
6. Default values in `variables.tf`

## AWS Profile Configuration

The `aws_profile` variable determines which AWS credentials to use:

### Default Behavior (`aws_profile = null`)
Uses AWS SDK default credential chain:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. Default profile from `~/.aws/credentials`
3. IAM instance profile (for EC2/ECS)
4. OIDC federation (for GitHub Actions)

### Explicit Profile
```hcl
# terraform.tfvars
aws_profile = "voya-admin"
```

### For Different Operations
```bash
# Normal operations (PowerUser permissions)
terraform apply -var-file="staging.tfvars" -var="aws_profile=voya-poweruser"

# IAM changes (Admin permissions required)
terraform apply -var-file="staging.tfvars" -var="aws_profile=voya-admin"
```

## Multi-Environment Setup

### Directory Structure
```
terraform/
├── modules/                    # Shared modules
│   ├── networking/
│   ├── security/
│   ├── ecs/
│   ├── alb/
│   └── github-oidc/
├── environments/
│   ├── staging/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── staging.tfvars     # Committed
│   │   └── terraform.tfvars   # Gitignored
│   ├── production/            # Future
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── production.tfvars  # Committed
│   │   └── terraform.tfvars   # Gitignored
│   └── testing/               # Future
│       ├── main.tf
│       ├── variables.tf
│       ├── testing.tfvars     # Committed
│       └── terraform.tfvars   # Gitignored
```

### Creating New Environments

1. **Copy staging directory:**
   ```bash
   cp -r environments/staging environments/production
   ```

2. **Update backend configuration in `main.tf`:**
   ```hcl
   backend "s3" {
     key = "production/terraform.tfstate"  # Change from "staging"
   }
   ```

3. **Create `production.tfvars`:**
   ```hcl
   aws_region = "us-east-1"

   # Production-specific values
   vpc_cidr           = "10.1.0.0/16"  # Different CIDR
   ecs_desired_count  = 3              # More instances
   enable_autoscaling = true           # Enable for production

   acm_certificate_arn = "arn:aws:acm:..."  # Production cert

   common_tags = {
     Environment = "production"
     # ...
   }
   ```

4. **Deploy:**
   ```bash
   cd environments/production
   terraform init
   terraform plan -var-file="production.tfvars"
   terraform apply -var-file="production.tfvars"
   ```

## State Management

### Backend Configuration
Terraform state is stored in:
- **S3 Bucket**: `voya-terraform-state-155304839180`
- **State Key**: `staging/terraform.tfstate`
- **Lock Table**: `voya-terraform-locks` (DynamoDB)
- **Encryption**: Enabled

### State Locking
State is automatically locked during operations. If a lock persists:
```bash
# View lock info
terraform force-unlock <LOCK_ID>
```

### State Commands
```bash
# View current state
terraform show

# List resources
terraform state list

# Show specific resource
terraform state show module.ecs.aws_ecs_cluster.main

# Remove resource from state (advanced)
terraform state rm module.example.resource
```

## Common Operations

### View Current Infrastructure
```bash
terraform show
terraform state list
```

### Plan Without Apply
```bash
terraform plan -var-file="staging.tfvars" -out=tfplan
# Review plan
terraform show tfplan
```

### Targeted Apply
```bash
# Apply only specific resources
terraform apply -var-file="staging.tfvars" -target=module.ecs
```

### Destroy Resources
```bash
# Destroy everything (DANGEROUS)
terraform destroy -var-file="staging.tfvars"

# Destroy specific resource
terraform destroy -var-file="staging.tfvars" -target=module.ecs.aws_ecs_service.app
```

### Import Existing Resources
```bash
# Import manually-created resource
terraform import -var-file="staging.tfvars" \
  module.ecs.aws_ecs_cluster.main \
  arn:aws:ecs:us-east-1:155304839180:cluster/staging-cluster
```

## Outputs

After successful apply, Terraform displays:
- VPC ID and NAT Gateway public IP
- ALB DNS name
- ECR repository URL
- ECS cluster and service names
- GitHub Actions role ARN
- CloudWatch log group names

View outputs anytime:
```bash
terraform output
terraform output nat_gateway_public_ip
```

## Secrets Management

**NEVER put secrets in Terraform files!**

Secrets are managed via AWS Secrets Manager. See **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** for complete setup instructions.

Quick reference:
```bash
# List secrets that need values
terraform output secrets_to_populate

# Set secret value
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/SECRET_NAME \
  --secret-string 'your-secret-value' \
  --profile voya \
  --region us-east-1
```

**Required Secrets** (10 total):
- `MONGODB_URI` - MongoDB Atlas connection string
- `JWT_SECRET` - Random 32+ character string
- `GEMINI_API_KEY` - Google Gemini API key
- `GOOGLE_API_KEY` - Google Cloud API key
- `SENDGRID_API_KEY` - SendGrid email API key
- `FLIGHTLOGIC_API_KEY` - FlightLogic API key
- `FLIGHTLOGIC_PASSWORD` - FlightLogic password
- `STRIPE_SECRET_KEY` - Stripe secret key (test mode)
- `STRIPE_PUBLISHABLE_KEY` - Stripe publishable key (test mode)
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook signing secret

## CI/CD Integration

GitHub Actions uses OIDC (no AWS profiles):
- IAM Role: `GitHubActionsDeployRole`
- Repository: `myvoya/voya`
- Workflow: `.github/workflows/deploy-staging.yml`

The workflow runs:
```bash
# In GitHub Actions (OIDC authentication, no profile needed)
terraform apply -var-file="staging.tfvars"
```

## Troubleshooting

### "Error acquiring state lock"
```bash
terraform force-unlock <LOCK_ID>
```

### "Provider authentication failed"
```bash
# Check your AWS credentials
aws sts get-caller-identity --profile voya-poweruser

# Verify profile in terraform.tfvars
cat terraform.tfvars
```

### "Resource already exists"
```bash
# Import existing resource
terraform import -var-file="staging.tfvars" <RESOURCE_ADDRESS> <RESOURCE_ID>
```

### Permission Denied for IAM Operations
```bash
# Use admin profile for IAM changes
terraform apply -var-file="staging.tfvars" -var="aws_profile=voya-admin"
```

## Best Practices

1. **Always use `-var-file="staging.tfvars"`** to ensure team configuration
2. **Never commit terraform.tfvars** - it's for personal preferences only
3. **Test with `terraform plan`** before applying
4. **Use targeted applies** for risky changes: `-target=module.name`
5. **Keep state in S3** - never use local state in a team environment
6. **Document variable changes** in staging.tfvars with comments
7. **Use consistent naming** - prefix resources with `${environment}-`
8. **Tag everything** - use `common_tags` for resource tracking

## Support

- **Terraform Docs**: https://developer.hashicorp.com/terraform/docs
- **AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **Project Documentation**: `../../docs/`
- **Questions**: Create GitHub issue or ask in team chat
