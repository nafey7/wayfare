# FlightLogic Inspector Proxy - Developer Guide

## Overview

The FlightLogic Inspector is an nginx reverse proxy deployed on ECS that allows developers to:
1. **Debug FlightLogic API requests/responses** - View request/response logs in CloudWatch
2. **Test locally with non-whitelisted IPs** - Route local requests through AWS NAT gateway (98.89.125.207)

## Architecture

```
Local Development → Proxy (34.232.44.167:8080) → FlightLogic API
                          ↓
                    CloudWatch Logs (/ecs/staging-flightlogic-inspector)
```

The proxy uses AWS NAT gateway IP (98.89.125.207) which is whitelisted by FlightLogic, allowing developers with non-whitelisted IPs to test locally.

## Quick Start - Local Development

### 1. Auto-Update Proxy IP (Recommended)

⚠️ **Note**: The proxy IP changes when the ECS task restarts. Use this script to auto-update your `.env`:

```bash
# Run from project root
./scripts/update-proxy-ip.sh

# Or add to your shell alias
alias update-proxy='./scripts/update-proxy-ip.sh'
```

The script automatically:
- Fetches the current proxy IP from AWS
- Updates `FLIGHTLOGIC_API_URL` in `backend_python/.env`
- Creates a backup of your `.env` file

### 2. Manual Configuration (Alternative)

Edit `backend_python/.env`:

```bash
FLIGHTLOGIC_API_URL=http://34.232.44.167:8080/api/aeroVE5  # ⚠️ IP changes on restart!
FLIGHTLOGIC_USER_ID=myvoya_testAPI
FLIGHTLOGIC_PASSWORD=<get from AWS Secrets Manager>
FLIGHTLOGIC_ACCESS_TYPE=Test
FLIGHTLOGIC_IP_ADDRESS=98.89.125.207
```

**Get password from AWS:**
```bash
aws secretsmanager get-secret-value \
  --secret-id staging/Voya-fastAPI/FLIGHTLOGIC_PASSWORD \
  --query SecretString \
  --output text \
  --profile voya-poweruser
```

### 2. Test FlightLogic API

**Example: Flight Search**
```bash
curl -X POST http://34.232.44.167:8080/api/aeroVE5/availability \
  -H "Content-Type: application/json" \
  -H "Accept-Encoding: gzip" \
  -d '{
    "userID": "myvoya_testAPI",
    "userPassword": "<password>",
    "accessType": "Test",
    "ipAddress": "98.89.125.207",
    "journeyType": "OneWay",
    "originDestinationInfo": [{
      "departureDate": "2025-12-01",
      "airportOriginCode": "JFK",
      "airportDestinationCode": "LAX"
    }],
    "cabinClass": "Economy",
    "adults": 1,
    "children": 0,
    "infants": 0
  }'
```

All requests are logged to CloudWatch. View logs with:
```bash
aws logs tail /ecs/staging-flightlogic-inspector --follow --profile voya-admin
```

## Proxy Public IP

**Current Public IP**: `34.232.44.167`

⚠️ **Note**: This IP changes when the ECS task restarts. Check current IP:
```bash
aws ecs list-tasks \
  --cluster staging-cluster \
  --service-name staging-flightlogic-inspector \
  --desired-status RUNNING \
  --query 'taskArns[0]' \
  --output text \
  --profile voya-admin | \
  xargs -I {} aws ecs describe-tasks \
    --cluster staging-cluster \
    --tasks {} \
    --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value | [0]' \
    --output text \
    --profile voya-admin | \
  xargs -I {} aws ec2 describe-network-interfaces \
    --network-interface-ids {} \
    --query 'NetworkInterfaces[0].Association.PublicIp' \
    --output text \
    --profile voya-admin
```

## FlightLogic API Credentials (Staging)

- **User ID**: `myvoya_testAPI`
- **Password**: Stored in AWS Secrets Manager (`staging/Voya-fastAPI/FLIGHTLOGIC_PASSWORD`)
- **Access Type**: `Test`
- **IP Address**: `98.89.125.207` (NAT gateway, whitelisted)
- **Base URL** (direct): `https://travelnext.works/api/aeroVE5`
- **Base URL** (via proxy): `http://34.232.44.167:8080/api/aeroVE5`

## API Endpoints

All FlightLogic endpoints are available through the proxy:

| Endpoint | Description |
|----------|-------------|
| `/availability` | Flight search |
| `/fareRules` | Get fare rules |
| `/revalidate` | Revalidate fare |
| `/booking` | Create booking |
| `/issueTicket` | Issue ticket |
| `/cancelBooking` | Cancel booking |
| `/extraServices` | Get extra services |
| `/tripDetails` | Get trip details |

## CloudWatch Logs

View nginx access and error logs for debugging:
```bash
aws logs tail /ecs/staging-flightlogic-inspector \
  --follow \
  --format short \
  --profile voya-admin
```

## Troubleshooting

### "Connection refused" or "Empty reply from server"
- Check if proxy task is running: `aws ecs describe-services --cluster staging-cluster --services staging-flightlogic-inspector --profile voya-admin`
- Verify public IP hasn't changed (ECS tasks get new IPs on restart)
- Check security group allows port 8080 from 0.0.0.0/0

### "Authentication failed" from FlightLogic
- Verify password from Secrets Manager is correct
- Ensure `ipAddress` field is `98.89.125.207` (NAT gateway IP)
- Check `accessType` is `Test` (not `LIVE`)

### Requests not appearing in CloudWatch logs
- Verify you're sending requests to the **proxy port 8080** (not directly to FlightLogic)
- Check CloudWatch logs for nginx error messages
- Verify nginx is running: check ECS service status

## Terraform Configuration

**Location**: `terraform/modules/flightlogic-inspector/`

**Key files**:
- `main.tf` - ECS task definition, service, target groups
- `variables.tf` - Module inputs (debug flags, subnets, etc.)
- `security.tf` - Public access rules for debugging
- `outputs.tf` - Proxy URLs and service details

**Debug features** (enabled in staging):
- `enable_ecs_exec = true` - SSH-like access via ECS Exec
- `assign_public_ip = true` - Direct public access to port 8080
- `enable_health_checks = false` - Disabled for debugging (prevents restarts)

## Security Notes

⚠️ **Debug Mode Warning**: Public access to port 8080 is **only enabled in staging** for debugging. This allows anyone to:
- Send requests through the proxy
- Access CloudWatch logs (with AWS credentials)

**Production deployment should**:
- Disable public IP assignment (`assign_public_ip = false`)
- Remove public access security group rules
- Use ALB-only access or VPN

## Future Improvements

### Static IP Solution (Recommended)

The current setup requires updating `.env` when the ECS task restarts. For a more permanent solution:

**Option A: Network Load Balancer with Static IPs**
- Deploy NLB with Elastic IPs for the inspector
- Provides stable IPs that never change
- Cost: ~$20/month for NLB

**Option B: Route53 DNS with Auto-Update**
- Create DNS record: `proxy.staging.myvoya.ai`
- Use EventBridge + Lambda to auto-update DNS when task IP changes
- Cost: Minimal (Lambda + Route53)

**Option C: nginx Path Rewriting**
- Configure nginx location directive to strip `/flightlogic` prefix
- Enables using ALB stable DNS: `https://staging.myvoya.ai/flightlogic/api/aeroVE5`
- Requires updating nginx configuration

### Why Not ALB?

The Application Load Balancer has stable DNS (`staging.myvoya.ai`) but path-based routing adds a `/flightlogic` prefix that nginx would forward to FlightLogic, breaking the API path. This requires:
- nginx rewrite rules to strip prefixes, OR
- Using NLB instead (passes traffic through without modification)

## Additional Resources

- **nginx docs**: https://nginx.org/en/docs/
- **FlightLogic API docs**: `dev-tools/extern/flightlogic_apis/`
- **Field definitions**: `dev-tools/docs/flightlogic-field-definitions.md`
- **Auto-update script**: `scripts/update-proxy-ip.sh`

---

**Last Updated**: November 2025
**Maintainer**: DevOps Team
