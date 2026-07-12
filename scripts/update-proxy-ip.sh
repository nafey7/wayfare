#!/bin/bash
# Update FlightLogic proxy IP in local .env file
# Usage: ./scripts/update-proxy-ip.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

echo "🔍 Fetching current FlightLogic Inspector IP..."

# Get current task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster staging-cluster \
  --service-name staging-flightlogic-inspector \
  --desired-status RUNNING \
  --query 'taskArns[0]' \
  --output text \
  --profile voya-admin)

if [ -z "$TASK_ARN" ] || [ "$TASK_ARN" == "None" ]; then
  echo "❌ No running inspector task found"
  exit 1
fi

echo "✅ Found task: ${TASK_ARN##*/}"

# Get ENI ID
ENI_ID=$(aws ecs describe-tasks \
  --cluster staging-cluster \
  --tasks "$TASK_ARN" \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value | [0]' \
  --output text \
  --profile voya-admin)

# Get public IP
PUBLIC_IP=$(aws ec2 describe-network-interfaces \
  --network-interface-ids "$ENI_ID" \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --output text \
  --profile voya-admin)

if [ -z "$PUBLIC_IP" ] || [ "$PUBLIC_IP" == "None" ]; then
  echo "❌ No public IP found (task may be in private subnet)"
  exit 1
fi

echo "✅ Current proxy IP: $PUBLIC_IP"

# Update .env file
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env file not found at: $ENV_FILE"
  exit 1
fi

# Backup .env
cp "$ENV_FILE" "$ENV_FILE.backup"

# Update or add FLIGHTLOGIC_API_URL
if grep -q "^FLIGHTLOGIC_API_URL=" "$ENV_FILE"; then
  # Update existing line (works on both macOS and Linux)
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|^FLIGHTLOGIC_API_URL=.*|FLIGHTLOGIC_API_URL=http://$PUBLIC_IP:8080/api/aeroVE5|" "$ENV_FILE"
  else
    sed -i "s|^FLIGHTLOGIC_API_URL=.*|FLIGHTLOGIC_API_URL=http://$PUBLIC_IP:8080/api/aeroVE5|" "$ENV_FILE"
  fi
  echo "✅ Updated FLIGHTLOGIC_API_URL in $ENV_FILE"
else
  echo "FLIGHTLOGIC_API_URL=http://$PUBLIC_IP:8080/api/aeroVE5" >> "$ENV_FILE"
  echo "✅ Added FLIGHTLOGIC_API_URL to $ENV_FILE"
fi

echo ""
echo "🎉 Done! Proxy URL updated to: http://$PUBLIC_IP:8080/api/aeroVE5"
echo ""
echo "💡 Tip: Add this to your shell alias:"
echo "   alias update-proxy='$SCRIPT_DIR/update-proxy-ip.sh'"
