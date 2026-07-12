# Deployment Runbook

Operational guide for deploying and managing the Voya travel platform.

## Table of Contents
- [Deployment Overview](#deployment-overview)
- [Staging Deployment](#staging-deployment)
- [Production Deployment](#production-deployment-future)
- [Rollback Procedures](#rollback-procedures)
- [Monitoring](#monitoring)
- [Emergency Procedures](#emergency-procedures)

## Deployment Overview

**Environments**:
- **Staging**: Deployed from `develop` branch, automatic via GitHub Actions
- **Production**: (Future) Deployed from `main` branch, manual approval required

**Deployment Methods**:
1. **Automated (CI/CD)**: Push to `develop` → GitHub Actions → Staging
2. **Manual**: Build locally → Push to ECR → Update ECS service

## Staging Deployment

### Automated Deployment (Recommended)

**Trigger**: Push to `develop` branch

```bash
# Make changes
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/your-feature

# Make changes, commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/your-feature
gh pr create --base develop --title "Add new feature"

# After PR approval and merge to develop
# → GitHub Actions automatically deploys to staging
```

**GitHub Actions Workflow**:
1. **Quality Checks** (5-10 min)
   - Ruff linting + formatting
   - MyPy type checking (non-blocking)
   - Bandit security scan
   - Backend unit tests
   - Frontend tests

2. **Build & Push** (5-10 min)
   - Build Docker image
   - Tag with git SHA
   - Push to ECR

3. **Deploy** (5-10 min)
   - Update ECS task definition
   - Deploy to ECS Fargate
   - Wait for service stability

4. **E2E Tests** (10-15 min, optional)
   - Run Playwright tests against staging
   - Report results

**Total time**: ~30-40 minutes

### Manual Deployment

```bash
# 1. Build Docker image
docker build -t 155304839180.dkr.ecr.us-east-1.amazonaws.com/myvoya-staging-fastapi-react:$(git rev-parse --short HEAD) .

# 2. Login to ECR
aws ecr get-login-password --region us-east-1 --profile voya-poweruser | \
  docker login --username AWS --password-stdin 155304839180.dkr.ecr.us-east-1.amazonaws.com

# 3. Push image
docker push 155304839180.dkr.ecr.us-east-1.amazonaws.com/myvoya-staging-fastapi-react:$(git rev-parse --short HEAD)

# 4. Update ECS service
aws ecs update-service \
  --cluster staging-cluster \
  --service staging-fastapi-react-service \
  --force-new-deployment \
  --profile voya-poweruser

# 5. Monitor deployment
aws ecs describe-services \
  --cluster staging-cluster \
  --services staging-fastapi-react-service \
  --profile voya-poweruser \
  --query 'services[0].{Status:status,RunningCount:runningCount,DesiredCount:desiredCount,Deployments:deployments[]}'
```

### Deployment Verification

```bash
# 1. Check service status
aws ecs describe-services \
  --cluster staging-cluster \
  --services staging-fastapi-react-service \
  --profile voya-poweruser

# 2. Check task health
aws ecs list-tasks \
  --cluster staging-cluster \
  --service-name staging-fastapi-react-service \
  --profile voya-poweruser

# 3. Test health endpoint
curl https://staging.myvoya.ai/health

# Expected: {"status":"healthy"}

# 4. Check logs
aws logs tail /ecs/staging-voya-backend --follow --profile voya-poweruser
```

## Production Deployment (Future)

**⚠️ Production deployment not yet configured. Follow this process when ready:**

### Pre-Deployment Checklist

- [ ] All staging tests passing
- [ ] Security scan completed (no critical issues)
- [ ] Database migrations tested
- [ ] Secrets populated in production Secrets Manager
- [ ] ACM certificate configured for `app.myvoya.ai`
- [ ] MongoDB Atlas production cluster ready
- [ ] Backup of current production state taken
- [ ] Rollback plan documented
- [ ] Stakeholders notified

### Production Deployment Process

```bash
# 1. Create production release tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# 2. Build production image
docker build -t 155304839180.dkr.ecr.us-east-1.amazonaws.com/myvoya-prod-fastapi-react:v1.0.0 .

# 3. Push to production ECR
docker push 155304839180.dkr.ecr.us-east-1.amazonaws.com/myvoya-prod-fastapi-react:v1.0.0

# 4. Update production ECS (with approval)
aws ecs update-service \
  --cluster myvoya_prod_cluster \
  --service fastapi-react-service-f3hmdaii \
  --force-new-deployment \
  --profile voya-admin

# 5. Monitor closely
watch -n 5 'aws ecs describe-services --cluster myvoya_prod_cluster --services fastapi-react-service-f3hmdaii --profile voya-admin'
```

## Rollback Procedures

### Rollback Scenarios

**When to rollback**:
- Application not responding after deployment
- Critical bugs discovered
- Database migration failure
- Dependency issues

### Quick Rollback (ECS)

```bash
# Option 1: Revert to previous task definition
aws ecs describe-task-definition \
  --task-definition staging-fastapi-react \
  --profile voya-poweruser \
  --query 'taskDefinition.{Family:family,Revision:revision}'

# Use previous revision (e.g., revision - 1)
aws ecs update-service \
  --cluster staging-cluster \
  --service staging-fastapi-react-service \
  --task-definition staging-fastapi-react:17 \
  --force-new-deployment \
  --profile voya-poweruser

# Option 2: Rollback via GitHub Actions
# Re-run previous successful deployment workflow
gh run list --workflow deploy-staging.yml
gh run rerun RUN_ID
```

### Full Terraform Rollback

```bash
# If infrastructure changes caused issues
cd terraform/environments/staging

# Revert to previous commit
git log --oneline terraform.tfvars
git checkout <previous-commit> -- terraform.tfvars

# Apply previous state
terraform plan
terraform apply
```

### Database Rollback

```bash
# If database migrations were applied

# 1. Check migration status
docker exec -it backend python -m alembic current

# 2. Downgrade to previous version
docker exec -it backend python -m alembic downgrade -1

# 3. Verify data integrity
```

## Monitoring

### Real-Time Monitoring

```bash
# ECS Service Status
aws ecs describe-services \
  --cluster staging-cluster \
  --services staging-fastapi-react-service \
  --profile voya-poweruser

# CloudWatch Logs (live)
aws logs tail /ecs/staging-voya-backend --follow --profile voya-poweruser

# ALB Target Health
aws elbv2 describe-target-health \
  --target-group-arn $(cd terraform/environments/staging && terraform output -raw target_group_arn) \
  --profile voya-poweruser
```

### Key Metrics

**Application Metrics**:
- CPU Utilization (target: <70%)
- Memory Utilization (target: <80%)
- Request count
- Error rate (target: <1%)
- Response time (target: <500ms p95)

**Infrastructure Metrics**:
- ECS running tasks (should match desired count)
- ALB healthy targets (should be > 0)
- NAT Gateway data transfer
- VPC endpoint usage

### CloudWatch Dashboards

```bash
# Create dashboard (one-time setup)
aws cloudwatch put-dashboard \
  --dashboard-name StagingVoyaMetrics \
  --dashboard-body file://cloudwatch-dashboard.json \
  --profile voya-poweruser
```

### Alerts

**Critical Alerts** (immediate action required):
- No healthy targets in ALB target group
- ECS service unable to start tasks
- Container crash loop
- 500 error rate > 5%

**Warning Alerts** (investigate soon):
- CPU > 70% for 10 minutes
- Memory > 80% for 10 minutes
- Slow response times (p95 > 1s)
- Failed health checks

## Emergency Procedures

### Application Down

```bash
# 1. Check ECS service
aws ecs describe-services \
  --cluster staging-cluster \
  --services staging-fastapi-react-service \
  --profile voya-poweruser

# 2. Check task status
aws ecs list-tasks \
  --cluster staging-cluster \
  --service-name staging-fastapi-react-service \
  --desired-status RUNNING \
  --profile voya-poweruser

# 3. Check logs for errors
aws logs tail /ecs/staging-voya-backend --since 10m --profile voya-poweruser

# 4. If tasks failing to start, check:
# - Secrets populated correctly
# - ECR image exists and is valid
# - Security groups allow traffic
# - Sufficient CPU/memory

# 5. Quick fix: Restart service
aws ecs update-service \
  --cluster staging-cluster \
  --service staging-fastapi-react-service \
  --force-new-deployment \
  --profile voya-poweruser
```

### Database Connection Issues

```bash
# 1. Verify MongoDB Atlas connectivity
# Check VPC peering status in Atlas dashboard

# 2. Check security group rules
aws ec2 describe-security-groups \
  --group-ids $(cd terraform/environments/staging && terraform output -raw ecs_security_group_id) \
  --profile voya-poweruser

# 3. Verify MONGODB_URI secret
aws secretsmanager get-secret-value \
  --secret-id staging/Voya-fastAPI/MONGODB_URI \
  --profile voya-poweruser

# 4. Test connection from ECS task
aws ecs execute-command \
  --cluster staging-cluster \
  --task TASK_ID \
  --container fastapi-react-container \
  --command "/bin/sh" \
  --interactive \
  --profile voya-poweruser
```

### High CPU/Memory Usage

```bash
# 1. Check current metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=staging-cluster Name=ServiceName,Value=staging-fastapi-react-service \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --profile voya-poweruser

# 2. Scale up immediately
cd terraform/environments/staging
# Edit terraform.tfvars: ecs_desired_count = 2
terraform apply

# 3. Or increase task size
# Edit terraform.tfvars:
# ecs_task_cpu = 2048
# ecs_task_memory = 4096
terraform apply
```

### Security Incident

```bash
# 1. Immediately restrict access
# Update ALB security group to block all traffic
aws ec2 authorize-security-group-ingress \
  --group-id $(cd terraform/environments/staging && terraform output -raw alb_security_group_id) \
  --ip-permissions IpProtocol=-1,FromPort=-1,ToPort=-1,IpRanges=[{CidrIp=0.0.0.0/32}] \
  --profile voya-poweruser

# 2. Take snapshot of logs
aws logs create-export-task \
  --log-group-name /ecs/staging-voya-backend \
  --from $(date -d '1 hour ago' +%s)000 \
  --to $(date +%s)000 \
  --destination voya-security-logs \
  --profile voya-poweruser

# 3. Rotate all secrets
# ... (detailed procedure)

# 4. Audit access
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::ECS::Service \
  --start-time $(date -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --profile voya-poweruser
```

## Contact Information

**On-Call Rotation**: (Configure in PagerDuty/Opsgenie)

**Escalation**:
1. DevOps Engineer (5 min response)
2. Lead Developer (15 min response)
3. CTO (30 min response)

**External Dependencies**:
- MongoDB Atlas Support: https://support.mongodb.com
- AWS Support: Enterprise plan
- SendGrid Support: https://support.sendgrid.com

---

**Last Updated**: October 2025
**Review Frequency**: Monthly
