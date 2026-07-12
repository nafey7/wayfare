# Production Environment Terraform Configuration

This directory contains Terraform configuration for the **new** production environment, deployed to `prod.myvoya.ai` initially, then switched to `app.myvoya.ai` after validation.

## Background

This configuration was created after investigating unexplained ~20 second response times in the existing production environment (manually created, default VPC). The staging environment (Terraform-managed, dedicated VPC) works perfectly (~0.4s response times).

**Approach**: Create a fresh production environment using Terraform to eliminate hidden infrastructure issues.

## Prerequisites

1. **AWS CLI** configured with `voya-poweruser` profile
2. **Terraform** >= 1.6.0
3. **terraform.tfvars** file with sensitive values (see below)

## Configuration Files

| File | Purpose |
|------|---------|
| `main.tf` | Module orchestration (networking, security, IAM, ECS, ALB, etc.) |
| `variables.tf` | Variable definitions with production defaults |
| `outputs.tf` | Outputs including NAT Gateway IP and deployment instructions |
| `terraform.tfvars` | **NOT COMMITTED** - Contains sensitive values |

## Required terraform.tfvars

Create a `terraform.tfvars` file (not committed to git):

```hcl
# imgproxy signing keys (must match backend secrets)
imgproxy_key  = "YOUR_IMGPROXY_KEY_HEX"
imgproxy_salt = "YOUR_IMGPROXY_SALT_HEX"

# Optional: Override defaults
# aws_profile = "voya-poweruser"
# container_image_tag = "2026.1.6"
```

## Deployment Steps

### 1. Initialize Terraform

```bash
cd terraform/environments/prod
terraform init
```

### 2. Plan and Review

```bash
terraform plan -out=tfplan
```

### 3. Apply Infrastructure

```bash
terraform apply tfplan
```

### 4. Note the NAT Gateway IP

```bash
terraform output nat_gateway_public_ip
```

**This IP must be whitelisted in:**
- MongoDB Atlas IP Access List
- FlightLogic (or use `FLIGHTLOGIC_SPOOF_IP` workaround temporarily)

### 5. Copy Secrets from Existing Prod

Copy secret values from existing prod to the new Terraform-created secrets:

```bash
# List secrets to populate
terraform output secrets_to_populate

# Example: Copy MONGODB_URI
aws secretsmanager get-secret-value \
  --secret-id arn:aws:secretsmanager:us-east-1:155304839180:secret:Voya-fastAPI/MONGODB_URI-5itOzl \
  --profile voya-poweruser \
  --query SecretString --output text

# Set in new secret
aws secretsmanager put-secret-value \
  --secret-id prod/Voya-fastAPI/MONGODB_URI \
  --secret-string 'COPIED_VALUE' \
  --profile voya-poweruser
```

### 6. Deploy Application

```bash
# Force new deployment
aws ecs update-service \
  --cluster prod-voya-cluster \
  --service prod-fastapi-react-service \
  --force-new-deployment \
  --profile voya-poweruser
```

### 7. Configure DNS (CloudFlare)

Point `prod.myvoya.ai` to the new ALB:

```bash
terraform output alb_dns_name
```

### 8. Test

```bash
# Health check
curl https://prod.myvoya.ai/health

# Run multiple times to verify consistency
for i in {1..10}; do
  curl -s -o /dev/null -w "%{time_starttransfer}\n" https://prod.myvoya.ai/health
done
```

### 9. Switch app.myvoya.ai (After Validation)

Once `prod.myvoya.ai` is verified working:
1. Update CloudFlare CNAME: `app.myvoya.ai` -> new ALB DNS
2. Monitor for issues
3. Keep old infrastructure as rollback option

## FlightLogic IP Workaround

Until the new NAT Gateway IP is whitelisted by FlightLogic, use the `FLIGHTLOGIC_SPOOF_IP` environment variable:

```hcl
# In variables.tf (already configured)
variable "flightlogic_spoof_ip" {
  default = "44.208.39.138"  # Existing prod NAT Gateway IP
}
```

This adds an `X-Forwarded-For` header to FlightLogic API requests, bypassing their IP whitelist.

## Rollback

If issues are discovered:

1. **DNS Rollback**: Point `app.myvoya.ai` back to old ALB
2. **Keep New Infra**: Don't destroy until investigation complete
3. **Destroy New Infra** (only if abandoned):
   ```bash
   terraform destroy
   ```

## Key Differences from Staging

| Setting | Staging | Production |
|---------|---------|------------|
| VPC CIDR | 10.0.0.0/16 | 10.1.0.0/16 |
| CPU | 1024 (1 vCPU) | 2048 (2 vCPU) |
| Memory | 2048 MB | 4096 MB |
| Autoscaling Max | 4 | 8 |
| Sentry Sampling | 100% | 10% |
| Debug Mode | true | true |
| Dev Tools | true | true |
| Log Level | DEBUG | DEBUG |
| FlightLogic Mode | Test | Production |
| FlightLogic API | aeroVE5 | aeroVE5-prod |
| FlightLogic User | myvoya_testAPI | myvoya_prodAPI |
| ECR Retention | 5 images | 10 images |
| Log Retention | 30 days | 90 days |

## Related Issues

- [#83](https://github.com/myvoya/voya/issues/83) - Set up Terraform for production environment
- [#103](https://github.com/myvoya/voya/issues/103) - Production Deployment Pipeline & Infrastructure Improvements
