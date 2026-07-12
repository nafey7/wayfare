# Staging Environment Deployment Guide

Complete guide for deploying and configuring the Voya staging environment.

## Prerequisites

- AWS CLI configured with `voya` profile (PowerUser permissions)
- Terraform >= 1.6.0
- Access to Stripe Dashboard (test mode)
- MongoDB Atlas access (for IP whitelisting)

## Initial Infrastructure Deployment

### 1. Deploy Terraform Infrastructure

```bash
cd terraform/environments/staging

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var="aws_profile=voya" -out=tfplan

# Apply infrastructure
terraform apply -var="aws_profile=voya" tfplan
```

This creates:
- VPC with NAT Gateway (public IP: `98.89.125.207`)
- ECS cluster and service
- ALB with HTTPS (staging.myvoya.ai)
- ECR repository
- Secrets Manager placeholders (empty values)
- IAM roles for ECS and GitHub Actions

### 2. Configure Secrets

Terraform creates secret **placeholders** - you must populate them manually:

```bash
# MongoDB connection string
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/MONGODB_URI \
  --secret-string 'mongodb+srv://voya:PASSWORD@voya.whurbgz.mongodb.net/voya_staging?retryWrites=true&w=majority&appName=Voya' \
  --profile voya \
  --region us-east-1

# JWT secret (generate random 32+ char string)
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/JWT_SECRET \
  --secret-string '$(openssl rand -base64 32)' \
  --profile voya \
  --region us-east-1

# Google Gemini API key
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/GEMINI_API_KEY \
  --secret-string 'YOUR_GEMINI_KEY' \
  --profile voya \
  --region us-east-1

# Google API key (Maps, Geocoding, Places)
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/GOOGLE_API_KEY \
  --secret-string 'YOUR_GOOGLE_KEY' \
  --profile voya \
  --region us-east-1

# SendGrid API key
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/SENDGRID_API_KEY \
  --secret-string 'YOUR_SENDGRID_KEY' \
  --profile voya \
  --region us-east-1

# FlightLogic credentials
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/FLIGHTLOGIC_API_KEY \
  --secret-string 'YOUR_FLIGHTLOGIC_KEY' \
  --profile voya \
  --region us-east-1

aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/FLIGHTLOGIC_PASSWORD \
  --secret-string 'YOUR_FLIGHTLOGIC_PASSWORD' \
  --profile voya \
  --region us-east-1
```

### 3. Configure Stripe

#### 3a. Get Stripe Keys from Dashboard

1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy "Publishable key" (starts with `pk_test_`)
3. Reveal and copy "Secret key" (starts with `sk_test_`)

#### 3b. Store Stripe Keys in Secrets Manager

```bash
# Stripe secret key
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/STRIPE_SECRET_KEY \
  --secret-string 'sk_test_YOUR_KEY_HERE' \
  --profile voya \
  --region us-east-1

# Stripe publishable key
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/STRIPE_PUBLISHABLE_KEY \
  --secret-string 'pk_test_YOUR_KEY_HERE' \
  --profile voya \
  --region us-east-1
```

#### 3c. Create Stripe Webhook

```bash
# Create webhook using Stripe CLI or API
curl -X POST https://api.stripe.com/v1/webhook_endpoints \
  -u "sk_test_YOUR_KEY_HERE:" \
  -d "url=https://staging.myvoya.ai/api/webhooks/stripe" \
  -d "enabled_events[]=payment_intent.succeeded" \
  -d "enabled_events[]=payment_intent.payment_failed" \
  -d "enabled_events[]=payment_intent.canceled" \
  -d "description=Staging environment webhook for Voya"
```

Save the webhook secret (starts with `whsec_`):

```bash
# Store webhook secret
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/STRIPE_WEBHOOK_SECRET \
  --secret-string 'whsec_YOUR_SECRET_HERE' \
  --profile voya \
  --region us-east-1
```

### 4. Configure MongoDB Atlas IP Whitelist

1. Go to MongoDB Atlas → Network Access
2. Add IP Whitelist: `10.0.0.0/16` (entire staging VPC)
3. Description: "Voya Staging VPC"

**Why full VPC CIDR?** ECS tasks get random private IPs within the VPC, so we whitelist the entire range.

### 5. Verify Security Group Configuration

The staging security group should already have the necessary egress rules:

```bash
# Get security group ID
SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=staging-ecs-sg" \
  --query 'SecurityGroups[0].GroupId' \
  --output text \
  --profile voya \
  --region us-east-1)

# Check egress rules
aws ec2 describe-security-groups \
  --group-ids $SG_ID \
  --query 'SecurityGroups[0].IpPermissionsEgress' \
  --profile voya \
  --region us-east-1
```

**Expected rules**:
- Port 443 (HTTPS) → `0.0.0.0/0` - Used for MongoDB Atlas connection via internet
- Port 27017 (MongoDB) → `192.168.248.0/21` - VPC peering route (optional, not required)

**Note**: MongoDB Atlas connections work via HTTPS (port 443) through the NAT Gateway, NOT via VPC peering. The port 27017 rule to the peered VPC is optional and not used in practice.

### 6. Configure API IP Whitelisting

Whitelist staging NAT IP (`98.89.125.207`) in:

1. **Google Cloud Console** → APIs & Services → Credentials → API Key Restrictions
2. **FlightLogic** → Contact support to whitelist IP for test account `myvoya_testAPI`

### 7. Build and Deploy Docker Image

```bash
# Navigate to project root
cd /path/to/voya

# Build Docker image
docker build -t 155304839180.dkr.ecr.us-east-1.amazonaws.com/myvoya-staging-fastapi-react:latest .

# Login to ECR
aws ecr get-login-password --region us-east-1 --profile voya | \
  docker login --username AWS --password-stdin 155304839180.dkr.ecr.us-east-1.amazonaws.com

# Push image
docker push 155304839180.dkr.ecr.us-east-1.amazonaws.com/myvoya-staging-fastapi-react:latest

# Force new ECS deployment
aws ecs update-service \
  --cluster staging-cluster \
  --service staging-fastapi-react-service \
  --force-new-deployment \
  --profile voya \
  --region us-east-1
```

### 8. Verify Deployment

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster staging-cluster \
  --services staging-fastapi-react-service \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount}' \
  --profile voya \
  --region us-east-1

# Monitor CloudWatch logs
aws logs tail /ecs/staging-voya-backend \
  --follow \
  --profile voya \
  --region us-east-1

# Check health endpoint
curl https://staging.myvoya.ai/health

# Test API
curl https://staging.myvoya.ai/api/docs
```

## Post-Deployment Configuration

### DNS Configuration

Create CNAME record in Route 53 (or your DNS provider):
```
staging.myvoya.ai → staging-alb-553012629.us-east-1.elb.amazonaws.com
```

### SSL Certificate

The ACM certificate ARN is configured in `variables.tf`:
```hcl
acm_certificate_arn = "arn:aws:acm:us-east-1:155304839180:certificate/c663d9d0-9a0f-4403-b338-aedd8c473298"
```

Ensure certificate covers `staging.myvoya.ai`.

## Secrets Management Checklist

Use this checklist to verify all secrets are configured:

```bash
# Check which secrets need values
aws secretsmanager list-secrets \
  --filters "Key=name,Values=staging/Voya-fastAPI" \
  --query 'SecretList[].Name' \
  --profile voya \
  --region us-east-1

# Test each secret (don't print sensitive values)
for secret in $(aws secretsmanager list-secrets --filters "Key=name,Values=staging/Voya-fastAPI" --query 'SecretList[].Name' --output text --profile voya --region us-east-1); do
  value=$(aws secretsmanager get-secret-value --secret-id "$secret" --query SecretString --output text --profile voya --region us-east-1 2>&1)
  if [[ $value == PLACEHOLDER* ]]; then
    echo "❌ $secret: Not set (placeholder)"
  elif [[ $value == *"ResourceNotFoundException"* ]]; then
    echo "❌ $secret: Does not exist"
  elif [[ -z $value ]]; then
    echo "❌ $secret: Empty"
  else
    echo "✅ $secret: Set"
  fi
done
```

Expected output:
```
✅ staging/Voya-fastAPI/FLIGHTLOGIC_API_KEY: Set
✅ staging/Voya-fastAPI/FLIGHTLOGIC_PASSWORD: Set
✅ staging/Voya-fastAPI/GEMINI_API_KEY: Set
✅ staging/Voya-fastAPI/GOOGLE_API_KEY: Set
✅ staging/Voya-fastAPI/JWT_SECRET: Set
✅ staging/Voya-fastAPI/MONGODB_URI: Set
✅ staging/Voya-fastAPI/SENDGRID_API_KEY: Set
✅ staging/Voya-fastAPI/STRIPE_PUBLISHABLE_KEY: Set
✅ staging/Voya-fastAPI/STRIPE_SECRET_KEY: Set
✅ staging/Voya-fastAPI/STRIPE_WEBHOOK_SECRET: Set
```

## Updating Configuration

### Update Environment Variables

Edit `terraform/environments/staging/main.tf`:
```hcl
additional_environment_vars = [
  {
    name  = "NEW_VAR"
    value = "new_value"
  }
]
```

Then apply:
```bash
terraform plan -var="aws_profile=voya"
terraform apply -var="aws_profile=voya"

# Force new deployment to pick up changes
aws ecs update-service \
  --cluster staging-cluster \
  --service staging-fastapi-react-service \
  --force-new-deployment \
  --profile voya \
  --region us-east-1
```

### Update Secret Values

```bash
# Update secret
aws secretsmanager put-secret-value \
  --secret-id staging/Voya-fastAPI/SECRET_NAME \
  --secret-string 'new-value' \
  --profile voya \
  --region us-east-1

# Force deployment to reload secrets
aws ecs update-service \
  --cluster staging-cluster \
  --service staging-fastapi-react-service \
  --force-new-deployment \
  --profile voya \
  --region us-east-1
```

## Troubleshooting

### Container Fails to Start

```bash
# Check logs
aws logs tail /ecs/staging-voya-backend --since 10m --profile voya --region us-east-1

# Common issues:
# - Missing secrets (check all 10 are set)
# - MongoDB connection timeout (check IP whitelist)
# - Invalid Stripe keys (verify in dashboard)
```

### MongoDB Connection Timeout

1. **Check MongoDB Atlas whitelist**: Should have `10.0.0.0/16`
2. **Check security group**: Egress rule for port 27017 should allow `0.0.0.0/0`
3. **Verify connection string**: Should use `mongodb+srv://` and correct database name

### Stripe Webhook Failures

```bash
# Verify webhook is registered
curl https://api.stripe.com/v1/webhook_endpoints \
  -u "sk_test_YOUR_KEY:"

# Check webhook secret matches
aws secretsmanager get-secret-value \
  --secret-id staging/Voya-fastAPI/STRIPE_WEBHOOK_SECRET \
  --query SecretString \
  --output text \
  --profile voya \
  --region us-east-1
```

### API IP Restriction Errors

**Error**: `403 The provided API key has an IP address restriction`

**Solution**: Whitelist `98.89.125.207` in:
- Google Cloud Console (for Gemini/Google APIs)
- FlightLogic support portal (for flight APIs)

## Disaster Recovery

### Full Infrastructure Rebuild

If infrastructure is destroyed, follow these steps:

1. **Deploy Terraform** (creates empty secrets)
2. **Populate all 10 secrets** (see step 2 above)
3. **Configure MongoDB whitelist** (see step 4)
4. **Configure security groups** (see step 5)
5. **Recreate Stripe webhook** (see step 3c)
6. **Whitelist NAT IP** in Google/FlightLogic (see step 6)
7. **Deploy Docker image** (see step 7)

**Backup secret values** before destroying infrastructure!

```bash
# Backup all secrets to file
for secret in $(aws secretsmanager list-secrets --filters "Key=name,Values=staging/Voya-fastAPI" --query 'SecretList[].Name' --output text --profile voya --region us-east-1); do
  value=$(aws secretsmanager get-secret-value --secret-id "$secret" --query SecretString --output text --profile voya --region us-east-1 2>&1)
  echo "$secret=$value" >> staging-secrets-backup.txt
done

# IMPORTANT: Store staging-secrets-backup.txt securely (not in git!)
```

## Monitoring

### CloudWatch Logs
```bash
# Backend logs
aws logs tail /ecs/staging-voya-backend --follow --profile voya --region us-east-1

# Filter for errors
aws logs tail /ecs/staging-voya-backend --follow --filter-pattern "ERROR" --profile voya --region us-east-1
```

### ECS Service Health
```bash
# Service status
aws ecs describe-services \
  --cluster staging-cluster \
  --services staging-fastapi-react-service \
  --profile voya \
  --region us-east-1

# Task details
aws ecs list-tasks \
  --cluster staging-cluster \
  --service-name staging-fastapi-react-service \
  --profile voya \
  --region us-east-1
```

### Application Health
```bash
# Health check
curl https://staging.myvoya.ai/health

# API docs
curl https://staging.myvoya.ai/api/docs
```

## Support

- **Terraform Issues**: See `README.md` in this directory
- **Application Issues**: See main project documentation in `/docs`
- **AWS Issues**: Check CloudWatch logs and ECS service events
