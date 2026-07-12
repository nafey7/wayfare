#!/bin/bash
# Update Stripe webhook URL with new ngrok URL
#
# This script automatically updates the Stripe webhook endpoint when ngrok restarts
# and the public URL changes (free tier ngrok URLs change on every restart).
#
# Prerequisites:
# - ngrok running (docker compose up -d)
# - Stripe CLI installed and authenticated (stripe login)
# - jq installed for JSON parsing
#
# Usage:
#   ./backend_python/scripts/update-webhook-url.sh

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Webhook endpoint ID for local development
WEBHOOK_ID="we_1SJfsKPD9V3ngpza4LdY8VLF"

echo -e "${BLUE}🔄 Updating Stripe webhook URL...${NC}\n"

# Check if ngrok is running
if ! curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1; then
  echo -e "${RED}❌ Error: ngrok is not running${NC}"
  echo -e "   Start ngrok: ${YELLOW}docker compose up -d ngrok${NC}"
  exit 1
fi

# Get new ngrok URL
NEW_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')

if [ -z "$NEW_URL" ] || [ "$NEW_URL" == "null" ]; then
  echo -e "${RED}❌ Could not get ngrok URL. Is ngrok running?${NC}"
  echo -e "   Check ngrok status: ${YELLOW}docker compose ps ngrok${NC}"
  echo -e "   View ngrok logs: ${YELLOW}docker compose logs ngrok${NC}"
  exit 1
fi

echo -e "${GREEN}🔗 New ngrok URL: ${BLUE}$NEW_URL${NC}"

# Check if Stripe CLI is available
if ! command -v stripe &> /dev/null; then
  echo -e "${RED}❌ Error: Stripe CLI not found${NC}"
  echo -e "   Install: ${YELLOW}https://stripe.com/docs/stripe-cli${NC}"
  exit 1
fi

# Update local webhook endpoint
echo -e "\n${BLUE}📝 Updating webhook endpoint ${WEBHOOK_ID}...${NC}"
if stripe webhook_endpoints update "$WEBHOOK_ID" --url "$NEW_URL/webhooks/stripe" > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Webhook URL updated successfully${NC}"
  echo -e "   Endpoint: ${BLUE}$NEW_URL/webhooks/stripe${NC}"
else
  echo -e "${RED}❌ Failed to update webhook endpoint${NC}"
  echo -e "   Check if you're logged in: ${YELLOW}stripe login${NC}"
  echo -e "   Verify webhook ID: ${YELLOW}stripe webhook_endpoints list${NC}"
  exit 1
fi

# Reminder to restart backend
echo -e "\n${YELLOW}⚠️  Don't forget to restart the backend to apply changes:${NC}"
echo -e "   ${GREEN}docker compose restart backend${NC}"
echo -e "\n${BLUE}📊 Verify webhook is working:${NC}"
echo -e "   1. View ngrok dashboard: ${BLUE}http://localhost:4040${NC}"
echo -e "   2. Check backend logs: ${YELLOW}docker compose logs -f backend${NC}"
echo -e "   3. Test with Stripe: ${YELLOW}stripe trigger payment_intent.succeeded${NC}"
