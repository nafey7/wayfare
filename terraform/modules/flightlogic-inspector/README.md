# FlightLogic Inspector Module

Deploys nginx as a reverse proxy to inspect FlightLogic API requests and responses.

## Purpose

This module allows developers to:
1. Send FlightLogic API requests from their local machine to the ECS-hosted inspector
2. Inspector forwards requests to the real FlightLogic API (using ECS's whitelisted IP)
3. View all request/response details in CloudWatch Logs

## Architecture

```
Local Dev → inspector.staging.myvoya.ai (ALB) → ECS Inspector (nginx) → FlightLogic API
                                                          ↓
                                                   CloudWatch Logs
```

## Usage

### 1. Deploy to ECS

Add the module to your staging environment:

```hcl
module "flightlogic_inspector" {
  source = "../../modules/flightlogic-inspector"

  environment                  = local.environment
  vpc_id                       = module.networking.vpc_id
  private_subnet_ids           = module.networking.private_subnet_ids
  inspector_security_group_id  = module.security.ecs_security_group_id
  ecs_cluster_id               = module.ecs.cluster_id
  task_execution_role_arn      = module.iam.ecs_task_execution_role_arn
  task_role_arn                = module.iam.ecs_task_role_arn
  target_group_arn             = module.alb.target_group_arn
  alb_listener_arn             = module.alb.http_listener_arn
  alb_https_listener_arn       = module.alb.https_listener_arn
  domain_name                  = "staging.myvoya.ai"
  aws_region                   = var.aws_region

  tags = var.common_tags
}
```

### 2. Configure DNS

Add DNS record for inspector subdomain:
```
inspector.staging.myvoya.ai → ALB DNS
```

### 3. Use from Local Development

Point your local backend to use the inspector:

```bash
# In backend_python/.env
FLIGHTLOGIC_API_URL=https://inspector.staging.myvoya.ai/api/aeroVE5
```

### 4. View Requests

Access the nginx logs via CloudWatch:
```bash
aws logs tail /ecs/staging-flightlogic-inspector --follow --profile voya-admin
```

## Security Considerations

- The inspector uses the same ECS security group as the backend
- ALB HTTPS listener requires certificate for `inspector.staging.myvoya.ai`
- Consider adding authentication if needed (can be done via ALB)

## Resource Requirements

- **CPU**: 256 units (configurable via `task_cpu`)
- **Memory**: 512 MB (configurable via `task_memory`)
- **Desired Count**: 1 task (sufficient for development)

## Limitations

- Local docker compose service won't work (IP not whitelisted)
- Must deploy to ECS for actual functionality
- ECS deployment uses whitelisted IP to access FlightLogic

## Troubleshooting

### View logs
```bash
AWS_PROFILE=voya-admin aws logs tail /ecs/staging-flightlogic-inspector --follow
```

### Check service status
```bash
AWS_PROFILE=voya-admin aws ecs describe-services \
  --cluster staging-voya \
  --services staging-flightlogic-inspector
```
