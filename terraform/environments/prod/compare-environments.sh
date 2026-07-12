#!/usr/bin/env bash
#
# compare-environments.sh
# Compares old (manually created) and new (Terraform-managed) production environments
#
# Usage:
#   ./compare-environments.sh              # Export old-prod and new-prod, then compare
#   ./compare-environments.sh --old-only   # Export only old-prod environment
#   ./compare-environments.sh --new-only   # Export only new-prod environment (after terraform apply)
#   ./compare-environments.sh --staging    # Export staging environment
#   ./compare-environments.sh --compare    # Compare old-prod vs new-prod
#   ./compare-environments.sh --compare-staging  # Compare staging vs old-prod
#   ./compare-environments.sh --all        # Export all three environments and generate all comparisons
#

set -euo pipefail

# Configuration
AWS_PROFILE="${AWS_PROFILE:-voya-admin}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/env-comparison"
OLD_DIR="${OUTPUT_DIR}/old-prod"
NEW_DIR="${OUTPUT_DIR}/new-prod"
DIFF_DIR="${OUTPUT_DIR}/diffs"

# Old prod identifiers (manually created)
OLD_VPC_ID="vpc-0dd1e1751ad3fbb64"
OLD_ECS_CLUSTER="myvoya_prod_cluster"
OLD_ECS_SERVICE="myvoya_prod_service"
OLD_TASK_FAMILY="fastapi-react"
OLD_ALB_NAME="myvoya-prod-alb"

# New prod identifiers (Terraform-managed) - update after terraform apply
NEW_VPC_ID="${NEW_VPC_ID:-}"  # Set after terraform apply
NEW_ECS_CLUSTER="${NEW_ECS_CLUSTER:-prod-voya-cluster}"
NEW_ECS_SERVICE="${NEW_ECS_SERVICE:-prod-fastapi-react-service}"
NEW_TASK_FAMILY="${NEW_TASK_FAMILY:-prod-fastapi-react}"
NEW_ALB_NAME="${NEW_ALB_NAME:-prod-voya-alb}"

# Staging identifiers (Terraform-managed, working correctly)
STAGING_VPC_ID="${STAGING_VPC_ID:-}"  # Will be fetched from terraform output
STAGING_ECS_CLUSTER="staging-cluster"
STAGING_ECS_SERVICE="staging-fastapi-react-service"
STAGING_TASK_FAMILY="staging-fastapi-react"
STAGING_ALB_NAME="staging-alb"
STAGING_ECR_REPO="myvoya-staging-fastapi-react"
STAGING_DIR="${OUTPUT_DIR}/staging"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create output directories
setup_dirs() {
    mkdir -p "$OLD_DIR" "$NEW_DIR" "$DIFF_DIR"
    log_info "Output directory: $OUTPUT_DIR"
}

# AWS CLI wrapper
aws_cmd() {
    aws --profile "$AWS_PROFILE" --region "$AWS_REGION" "$@"
}

# Export ECS Task Definition
export_task_definition() {
    local env=$1
    local family=$2
    local output_dir=$3

    log_info "Exporting ECS task definition: $family"

    aws_cmd ecs describe-task-definition \
        --task-definition "$family" \
        --query 'taskDefinition' \
        --output json > "${output_dir}/ecs-task-definition.json" 2>/dev/null || {
        log_warn "Task definition $family not found"
        echo '{}' > "${output_dir}/ecs-task-definition.json"
    }

    # Extract environment variables separately for easier comparison
    jq -r '.containerDefinitions[0].environment // [] | sort_by(.name)' \
        "${output_dir}/ecs-task-definition.json" > "${output_dir}/ecs-env-vars.json"

    # Extract secrets separately
    jq -r '.containerDefinitions[0].secrets // [] | sort_by(.name)' \
        "${output_dir}/ecs-task-definition.json" > "${output_dir}/ecs-secrets.json"

    # Extract container command
    jq -r '.containerDefinitions[0].command // []' \
        "${output_dir}/ecs-task-definition.json" > "${output_dir}/ecs-command.json"
}

# Export ECS Service
export_ecs_service() {
    local cluster=$1
    local service=$2
    local output_dir=$3

    log_info "Exporting ECS service: $cluster/$service"

    aws_cmd ecs describe-services \
        --cluster "$cluster" \
        --services "$service" \
        --query 'services[0]' \
        --output json > "${output_dir}/ecs-service.json" 2>/dev/null || {
        log_warn "ECS service $service not found in cluster $cluster"
        echo '{}' > "${output_dir}/ecs-service.json"
    }
}

# Export ECS Cluster
export_ecs_cluster() {
    local cluster=$1
    local output_dir=$2

    log_info "Exporting ECS cluster: $cluster"

    aws_cmd ecs describe-clusters \
        --clusters "$cluster" \
        --include SETTINGS CONFIGURATIONS \
        --query 'clusters[0]' \
        --output json > "${output_dir}/ecs-cluster.json" 2>/dev/null || {
        log_warn "ECS cluster $cluster not found"
        echo '{}' > "${output_dir}/ecs-cluster.json"
    }
}

# Export VPC Configuration
export_vpc() {
    local vpc_id=$1
    local output_dir=$2

    if [[ -z "$vpc_id" ]]; then
        log_warn "VPC ID not provided, skipping VPC export"
        return
    fi

    log_info "Exporting VPC: $vpc_id"

    # VPC details
    aws_cmd ec2 describe-vpcs \
        --vpc-ids "$vpc_id" \
        --output json > "${output_dir}/vpc.json" 2>/dev/null || echo '{"Vpcs":[]}' > "${output_dir}/vpc.json"

    # Subnets
    aws_cmd ec2 describe-subnets \
        --filters "Name=vpc-id,Values=$vpc_id" \
        --query 'Subnets | sort_by(@, &AvailabilityZone)' \
        --output json > "${output_dir}/vpc-subnets.json" 2>/dev/null || echo '[]' > "${output_dir}/vpc-subnets.json"

    # Route tables
    aws_cmd ec2 describe-route-tables \
        --filters "Name=vpc-id,Values=$vpc_id" \
        --output json > "${output_dir}/vpc-route-tables.json" 2>/dev/null || echo '{"RouteTables":[]}' > "${output_dir}/vpc-route-tables.json"

    # Internet Gateways
    aws_cmd ec2 describe-internet-gateways \
        --filters "Name=attachment.vpc-id,Values=$vpc_id" \
        --output json > "${output_dir}/vpc-igw.json" 2>/dev/null || echo '{"InternetGateways":[]}' > "${output_dir}/vpc-igw.json"

    # NAT Gateways
    aws_cmd ec2 describe-nat-gateways \
        --filter "Name=vpc-id,Values=$vpc_id" \
        --output json > "${output_dir}/vpc-nat-gateways.json" 2>/dev/null || echo '{"NatGateways":[]}' > "${output_dir}/vpc-nat-gateways.json"

    # Extract NAT Gateway public IPs
    jq -r '.NatGateways[] | select(.State=="available") | .NatGatewayAddresses[].PublicIp // empty' \
        "${output_dir}/vpc-nat-gateways.json" > "${output_dir}/vpc-nat-ips.txt" 2>/dev/null || true

    # VPC Endpoints
    aws_cmd ec2 describe-vpc-endpoints \
        --filters "Name=vpc-id,Values=$vpc_id" \
        --output json > "${output_dir}/vpc-endpoints.json" 2>/dev/null || echo '{"VpcEndpoints":[]}' > "${output_dir}/vpc-endpoints.json"

    # VPC Peering Connections
    aws_cmd ec2 describe-vpc-peering-connections \
        --filters "Name=requester-vpc-info.vpc-id,Values=$vpc_id" \
        --output json > "${output_dir}/vpc-peering.json" 2>/dev/null || echo '{"VpcPeeringConnections":[]}' > "${output_dir}/vpc-peering.json"
}

# Export Security Groups
export_security_groups() {
    local vpc_id=$1
    local output_dir=$2

    if [[ -z "$vpc_id" ]]; then
        log_warn "VPC ID not provided, skipping security groups export"
        return
    fi

    log_info "Exporting security groups for VPC: $vpc_id"

    aws_cmd ec2 describe-security-groups \
        --filters "Name=vpc-id,Values=$vpc_id" \
        --query 'SecurityGroups | sort_by(@, &GroupName)' \
        --output json > "${output_dir}/security-groups.json" 2>/dev/null || echo '[]' > "${output_dir}/security-groups.json"

    # Create a summary view
    jq '[.[] | {
        GroupId: .GroupId,
        GroupName: .GroupName,
        Description: .Description,
        InboundRules: [.IpPermissions[] | {
            Protocol: .IpProtocol,
            FromPort: .FromPort,
            ToPort: .ToPort,
            Sources: ([.IpRanges[].CidrIp] + [.UserIdGroupPairs[].GroupId] + [.PrefixListIds[].PrefixListId])
        }],
        OutboundRules: [.IpPermissionsEgress[] | {
            Protocol: .IpProtocol,
            FromPort: .FromPort,
            ToPort: .ToPort,
            Destinations: ([.IpRanges[].CidrIp] + [.UserIdGroupPairs[].GroupId] + [.PrefixListIds[].PrefixListId])
        }]
    }]' "${output_dir}/security-groups.json" > "${output_dir}/security-groups-summary.json" 2>/dev/null || true
}

# Export ALB Configuration
export_alb() {
    local alb_name=$1
    local output_dir=$2

    log_info "Exporting ALB: $alb_name"

    # Get ALB ARN first
    local alb_arn
    alb_arn=$(aws_cmd elbv2 describe-load-balancers \
        --names "$alb_name" \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text 2>/dev/null) || {
        log_warn "ALB $alb_name not found"
        echo '{}' > "${output_dir}/alb.json"
        return
    }

    # ALB details
    aws_cmd elbv2 describe-load-balancers \
        --names "$alb_name" \
        --query 'LoadBalancers[0]' \
        --output json > "${output_dir}/alb.json" 2>/dev/null || echo '{}' > "${output_dir}/alb.json"

    # ALB attributes
    aws_cmd elbv2 describe-load-balancer-attributes \
        --load-balancer-arn "$alb_arn" \
        --query 'Attributes' \
        --output json > "${output_dir}/alb-attributes.json" 2>/dev/null || echo '[]' > "${output_dir}/alb-attributes.json"

    # Listeners
    aws_cmd elbv2 describe-listeners \
        --load-balancer-arn "$alb_arn" \
        --query 'Listeners' \
        --output json > "${output_dir}/alb-listeners.json" 2>/dev/null || echo '[]' > "${output_dir}/alb-listeners.json"

    # Target Groups
    local tg_arns
    tg_arns=$(aws_cmd elbv2 describe-listeners \
        --load-balancer-arn "$alb_arn" \
        --query 'Listeners[].DefaultActions[].TargetGroupArn' \
        --output text 2>/dev/null | tr '\t' '\n' | grep -v '^$' | sort -u) || true

    if [[ -n "$tg_arns" ]]; then
        aws_cmd elbv2 describe-target-groups \
            --target-group-arns $tg_arns \
            --output json > "${output_dir}/alb-target-groups.json" 2>/dev/null || echo '{"TargetGroups":[]}' > "${output_dir}/alb-target-groups.json"

        # Target health for each target group
        for tg_arn in $tg_arns; do
            local tg_name
            tg_name=$(echo "$tg_arn" | grep -oP 'targetgroup/\K[^/]+')
            aws_cmd elbv2 describe-target-health \
                --target-group-arn "$tg_arn" \
                --output json > "${output_dir}/alb-target-health-${tg_name}.json" 2>/dev/null || true
        done
    else
        echo '{"TargetGroups":[]}' > "${output_dir}/alb-target-groups.json"
    fi
}

# Export ECR Repository
export_ecr() {
    local repo_name=$1
    local output_dir=$2

    log_info "Exporting ECR repository: $repo_name"

    aws_cmd ecr describe-repositories \
        --repository-names "$repo_name" \
        --output json > "${output_dir}/ecr-repository.json" 2>/dev/null || {
        log_warn "ECR repository $repo_name not found"
        echo '{"repositories":[]}' > "${output_dir}/ecr-repository.json"
    }

    # Repository policy
    aws_cmd ecr get-repository-policy \
        --repository-name "$repo_name" \
        --output json > "${output_dir}/ecr-policy.json" 2>/dev/null || echo '{}' > "${output_dir}/ecr-policy.json"

    # Lifecycle policy
    aws_cmd ecr get-lifecycle-policy \
        --repository-name "$repo_name" \
        --output json > "${output_dir}/ecr-lifecycle.json" 2>/dev/null || echo '{}' > "${output_dir}/ecr-lifecycle.json"

    # Recent images
    aws_cmd ecr describe-images \
        --repository-name "$repo_name" \
        --query 'imageDetails | sort_by(@, &imagePushedAt) | [-5:]' \
        --output json > "${output_dir}/ecr-images.json" 2>/dev/null || echo '[]' > "${output_dir}/ecr-images.json"
}

# Export CloudWatch Log Group
export_cloudwatch_logs() {
    local log_group=$1
    local output_dir=$2

    log_info "Exporting CloudWatch log group: $log_group"

    aws_cmd logs describe-log-groups \
        --log-group-name-prefix "$log_group" \
        --query 'logGroups[0]' \
        --output json > "${output_dir}/cloudwatch-log-group.json" 2>/dev/null || echo '{}' > "${output_dir}/cloudwatch-log-group.json"
}

# Export SSM Parameters (for old prod)
export_ssm_parameters() {
    local output_dir=$1

    log_info "Exporting SSM parameters"

    local params=(
        FLIGHTLOGIC_ACCESS_TYPE
        FLIGHTLOGIC_API_URL
        FLIGHTLOGIC_IP_ADDRESS
        FLIGHTLOGIC_USER_ID
        BACKEND_URL
        FLIGHTLOGIC_FLIGHTS_API_BASE_URL
        FLIGHTLOGIC_HOTELS_API_BASE_URL
        REACT_APP_API_URL
        CORS_ORIGINS
        N8N_ITINERARY_WEBHOOK_URL
        FLIGHTLOGIC_SPOOF_IP
        FLIGHTLOGIC_STRIPE_ACCOUNT_ID
    )

    echo "{" > "${output_dir}/ssm-parameters.json"
    local first=true
    for param in "${params[@]}"; do
        local value
        value=$(aws_cmd ssm get-parameter --name "$param" --query 'Parameter.Value' --output text 2>/dev/null) || value="NOT_FOUND"
        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo "," >> "${output_dir}/ssm-parameters.json"
        fi
        echo "  \"$param\": \"$value\"" >> "${output_dir}/ssm-parameters.json"
    done
    echo "}" >> "${output_dir}/ssm-parameters.json"
}

# Export IAM Roles
export_iam_roles() {
    local env=$1
    local output_dir=$2

    log_info "Exporting IAM roles for $env"

    local roles=()
    if [[ "$env" == "old" ]]; then
        roles=("MyEcsTaskRole" "ecsTaskExecutionRole")
    elif [[ "$env" == "staging" ]]; then
        roles=("staging-ecs-task-role" "staging-ecs-task-execution-role")
    else
        roles=("prod-ecs-task-role" "prod-ecs-task-execution-role")
    fi

    for role in "${roles[@]}"; do
        aws_cmd iam get-role \
            --role-name "$role" \
            --output json > "${output_dir}/iam-role-${role}.json" 2>/dev/null || {
            log_warn "IAM role $role not found"
            echo '{}' > "${output_dir}/iam-role-${role}.json"
        }

        # Attached policies
        aws_cmd iam list-attached-role-policies \
            --role-name "$role" \
            --output json > "${output_dir}/iam-role-${role}-policies.json" 2>/dev/null || echo '{"AttachedPolicies":[]}' > "${output_dir}/iam-role-${role}-policies.json"

        # Inline policies
        aws_cmd iam list-role-policies \
            --role-name "$role" \
            --output json > "${output_dir}/iam-role-${role}-inline.json" 2>/dev/null || echo '{"PolicyNames":[]}' > "${output_dir}/iam-role-${role}-inline.json"
    done
}

# Export old prod environment
export_old_prod() {
    log_info "========================================="
    log_info "Exporting OLD production environment"
    log_info "========================================="

    mkdir -p "$OLD_DIR"

    export_task_definition "old" "$OLD_TASK_FAMILY" "$OLD_DIR"
    export_ecs_service "$OLD_ECS_CLUSTER" "$OLD_ECS_SERVICE" "$OLD_DIR"
    export_ecs_cluster "$OLD_ECS_CLUSTER" "$OLD_DIR"
    export_vpc "$OLD_VPC_ID" "$OLD_DIR"
    export_security_groups "$OLD_VPC_ID" "$OLD_DIR"
    export_alb "$OLD_ALB_NAME" "$OLD_DIR"
    export_ecr "myvoya-prod-fastapi-react" "$OLD_DIR"
    export_cloudwatch_logs "/ecs/voya-backend" "$OLD_DIR"
    export_ssm_parameters "$OLD_DIR"
    export_iam_roles "old" "$OLD_DIR"

    log_success "Old prod environment exported to: $OLD_DIR"
}

# Export new prod environment
export_new_prod() {
    log_info "========================================="
    log_info "Exporting NEW production environment"
    log_info "========================================="

    # Try to get VPC ID from terraform output if not set
    if [[ -z "$NEW_VPC_ID" ]]; then
        if [[ -f "${SCRIPT_DIR}/.terraform/terraform.tfstate" ]] || terraform state list &>/dev/null; then
            NEW_VPC_ID=$(terraform output -raw vpc_id 2>/dev/null) || true
        fi
    fi

    if [[ -z "$NEW_VPC_ID" ]]; then
        log_warn "NEW_VPC_ID not set. Run 'terraform apply' first or set NEW_VPC_ID environment variable."
        log_warn "Skipping VPC-dependent exports for new environment."
    fi

    mkdir -p "$NEW_DIR"

    export_task_definition "new" "$NEW_TASK_FAMILY" "$NEW_DIR"
    export_ecs_service "$NEW_ECS_CLUSTER" "$NEW_ECS_SERVICE" "$NEW_DIR"
    export_ecs_cluster "$NEW_ECS_CLUSTER" "$NEW_DIR"

    if [[ -n "$NEW_VPC_ID" ]]; then
        export_vpc "$NEW_VPC_ID" "$NEW_DIR"
        export_security_groups "$NEW_VPC_ID" "$NEW_DIR"
    fi

    export_alb "$NEW_ALB_NAME" "$NEW_DIR"
    export_ecr "prod-fastapi-react" "$NEW_DIR"
    export_cloudwatch_logs "/ecs/prod-voya-backend" "$NEW_DIR"
    export_iam_roles "new" "$NEW_DIR"

    log_success "New prod environment exported to: $NEW_DIR"
}

# Export staging environment
export_staging() {
    log_info "========================================="
    log_info "Exporting STAGING environment"
    log_info "========================================="

    # Try to get VPC ID from terraform output if not set
    if [[ -z "$STAGING_VPC_ID" ]]; then
        local staging_tf_dir="${SCRIPT_DIR}/../staging"
        if [[ -d "$staging_tf_dir" ]]; then
            pushd "$staging_tf_dir" > /dev/null
            STAGING_VPC_ID=$(terraform output -raw vpc_id 2>/dev/null) || true
            popd > /dev/null
        fi
    fi

    # Fallback: try to find VPC by name tag
    if [[ -z "$STAGING_VPC_ID" ]]; then
        STAGING_VPC_ID=$(aws_cmd ec2 describe-vpcs \
            --filters "Name=tag:Name,Values=staging-vpc" \
            --query 'Vpcs[0].VpcId' \
            --output text 2>/dev/null) || true
        [[ "$STAGING_VPC_ID" == "None" ]] && STAGING_VPC_ID=""
    fi

    if [[ -z "$STAGING_VPC_ID" ]]; then
        log_warn "STAGING_VPC_ID not found. Set STAGING_VPC_ID environment variable."
    fi

    mkdir -p "$STAGING_DIR"

    export_task_definition "staging" "$STAGING_TASK_FAMILY" "$STAGING_DIR"
    export_ecs_service "$STAGING_ECS_CLUSTER" "$STAGING_ECS_SERVICE" "$STAGING_DIR"
    export_ecs_cluster "$STAGING_ECS_CLUSTER" "$STAGING_DIR"

    if [[ -n "$STAGING_VPC_ID" ]]; then
        export_vpc "$STAGING_VPC_ID" "$STAGING_DIR"
        export_security_groups "$STAGING_VPC_ID" "$STAGING_DIR"
    fi

    export_alb "$STAGING_ALB_NAME" "$STAGING_DIR"
    export_ecr "$STAGING_ECR_REPO" "$STAGING_DIR"
    export_cloudwatch_logs "/ecs/staging-voya-backend" "$STAGING_DIR"
    export_iam_roles "staging" "$STAGING_DIR"

    log_success "Staging environment exported to: $STAGING_DIR"
}

# Generate comparison report
generate_comparison() {
    log_info "========================================="
    log_info "Generating comparison report"
    log_info "========================================="

    mkdir -p "$DIFF_DIR"

    local report="${DIFF_DIR}/comparison-report.md"

    cat > "$report" << 'EOF'
# Production Environment Comparison Report

Generated: $(date -Iseconds)

## Summary

This report compares the OLD (manually created) and NEW (Terraform-managed) production environments.

---

EOF

    # Replace the date placeholder
    sed -i "s/\$(date -Iseconds)/$(date -Iseconds)/" "$report"

    # Compare ECS Task Definitions
    echo "## ECS Task Definition" >> "$report"
    echo "" >> "$report"

    if [[ -f "$OLD_DIR/ecs-task-definition.json" && -f "$NEW_DIR/ecs-task-definition.json" ]]; then
        echo "### Resource Allocation" >> "$report"
        echo "" >> "$report"
        echo "| Setting | Old Prod | New Prod |" >> "$report"
        echo "|---------|----------|----------|" >> "$report"

        local old_cpu old_mem new_cpu new_mem
        old_cpu=$(jq -r '.cpu // "N/A"' "$OLD_DIR/ecs-task-definition.json")
        old_mem=$(jq -r '.memory // "N/A"' "$OLD_DIR/ecs-task-definition.json")
        new_cpu=$(jq -r '.cpu // "N/A"' "$NEW_DIR/ecs-task-definition.json")
        new_mem=$(jq -r '.memory // "N/A"' "$NEW_DIR/ecs-task-definition.json")

        echo "| CPU | $old_cpu | $new_cpu |" >> "$report"
        echo "| Memory | $old_mem | $new_mem |" >> "$report"
        echo "" >> "$report"

        # Generate diff of env vars
        echo "### Environment Variables Diff" >> "$report"
        echo "" >> "$report"
        echo '```diff' >> "$report"
        diff -u "$OLD_DIR/ecs-env-vars.json" "$NEW_DIR/ecs-env-vars.json" 2>/dev/null >> "$report" || echo "No differences or files missing" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"

        # Save full diff
        diff -u "$OLD_DIR/ecs-env-vars.json" "$NEW_DIR/ecs-env-vars.json" > "$DIFF_DIR/env-vars.diff" 2>/dev/null || true

        # Compare secrets
        echo "### Secrets Configuration Diff" >> "$report"
        echo "" >> "$report"
        echo '```diff' >> "$report"
        diff -u "$OLD_DIR/ecs-secrets.json" "$NEW_DIR/ecs-secrets.json" 2>/dev/null >> "$report" || echo "No differences or files missing" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"

        diff -u "$OLD_DIR/ecs-secrets.json" "$NEW_DIR/ecs-secrets.json" > "$DIFF_DIR/secrets.diff" 2>/dev/null || true

        # Compare command
        echo "### Container Command Diff" >> "$report"
        echo "" >> "$report"
        echo '```diff' >> "$report"
        diff -u "$OLD_DIR/ecs-command.json" "$NEW_DIR/ecs-command.json" 2>/dev/null >> "$report" || echo "No differences or files missing" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"
    else
        echo "Task definition files not found for comparison." >> "$report"
        echo "" >> "$report"
    fi

    # Compare VPC Configuration
    echo "## VPC Configuration" >> "$report"
    echo "" >> "$report"

    if [[ -f "$OLD_DIR/vpc.json" && -f "$NEW_DIR/vpc.json" ]]; then
        echo "| Setting | Old Prod | New Prod |" >> "$report"
        echo "|---------|----------|----------|" >> "$report"

        local old_vpc_cidr new_vpc_cidr old_nat_ip new_nat_ip
        old_vpc_cidr=$(jq -r '.Vpcs[0].CidrBlock // "N/A"' "$OLD_DIR/vpc.json")
        new_vpc_cidr=$(jq -r '.Vpcs[0].CidrBlock // "N/A"' "$NEW_DIR/vpc.json")
        old_nat_ip=$(cat "$OLD_DIR/vpc-nat-ips.txt" 2>/dev/null | head -1 || echo "N/A")
        new_nat_ip=$(cat "$NEW_DIR/vpc-nat-ips.txt" 2>/dev/null | head -1 || echo "N/A")

        echo "| VPC CIDR | $old_vpc_cidr | $new_vpc_cidr |" >> "$report"
        echo "| NAT Gateway IP | $old_nat_ip | $new_nat_ip |" >> "$report"
        echo "" >> "$report"

        # Subnet comparison
        echo "### Subnets" >> "$report"
        echo "" >> "$report"
        echo "**Old Prod:**" >> "$report"
        echo '```json' >> "$report"
        jq '[.[] | {AZ: .AvailabilityZone, CIDR: .CidrBlock, Public: .MapPublicIpOnLaunch}]' "$OLD_DIR/vpc-subnets.json" >> "$report" 2>/dev/null || echo "[]" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"
        echo "**New Prod:**" >> "$report"
        echo '```json' >> "$report"
        jq '[.[] | {AZ: .AvailabilityZone, CIDR: .CidrBlock, Public: .MapPublicIpOnLaunch}]' "$NEW_DIR/vpc-subnets.json" >> "$report" 2>/dev/null || echo "[]" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"

        # VPC Endpoints comparison
        echo "### VPC Endpoints" >> "$report"
        echo "" >> "$report"
        echo "**Old Prod:**" >> "$report"
        echo '```json' >> "$report"
        jq '[.VpcEndpoints[] | {Service: .ServiceName, Type: .VpcEndpointType}]' "$OLD_DIR/vpc-endpoints.json" >> "$report" 2>/dev/null || echo "[]" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"
        echo "**New Prod:**" >> "$report"
        echo '```json' >> "$report"
        jq '[.VpcEndpoints[] | {Service: .ServiceName, Type: .VpcEndpointType}]' "$NEW_DIR/vpc-endpoints.json" >> "$report" 2>/dev/null || echo "[]" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"
    else
        echo "VPC configuration files not found for comparison." >> "$report"
        echo "" >> "$report"
    fi

    # Compare Security Groups
    echo "## Security Groups" >> "$report"
    echo "" >> "$report"

    if [[ -f "$OLD_DIR/security-groups-summary.json" && -f "$NEW_DIR/security-groups-summary.json" ]]; then
        echo "### Old Prod Security Groups" >> "$report"
        echo '```json' >> "$report"
        jq '.' "$OLD_DIR/security-groups-summary.json" >> "$report" 2>/dev/null || echo "[]" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"

        echo "### New Prod Security Groups" >> "$report"
        echo '```json' >> "$report"
        jq '.' "$NEW_DIR/security-groups-summary.json" >> "$report" 2>/dev/null || echo "[]" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"

        diff -u "$OLD_DIR/security-groups-summary.json" "$NEW_DIR/security-groups-summary.json" > "$DIFF_DIR/security-groups.diff" 2>/dev/null || true
    else
        echo "Security group files not found for comparison." >> "$report"
        echo "" >> "$report"
    fi

    # Compare ALB Configuration
    echo "## ALB Configuration" >> "$report"
    echo "" >> "$report"

    if [[ -f "$OLD_DIR/alb.json" && -f "$NEW_DIR/alb.json" ]]; then
        echo "| Setting | Old Prod | New Prod |" >> "$report"
        echo "|---------|----------|----------|" >> "$report"

        local old_alb_dns new_alb_dns old_alb_scheme new_alb_scheme
        old_alb_dns=$(jq -r '.DNSName // "N/A"' "$OLD_DIR/alb.json")
        new_alb_dns=$(jq -r '.DNSName // "N/A"' "$NEW_DIR/alb.json")
        old_alb_scheme=$(jq -r '.Scheme // "N/A"' "$OLD_DIR/alb.json")
        new_alb_scheme=$(jq -r '.Scheme // "N/A"' "$NEW_DIR/alb.json")

        echo "| DNS Name | $old_alb_dns | $new_alb_dns |" >> "$report"
        echo "| Scheme | $old_alb_scheme | $new_alb_scheme |" >> "$report"
        echo "" >> "$report"

        # Target group comparison
        echo "### Target Groups" >> "$report"
        echo '```diff' >> "$report"
        diff -u <(jq -S '.' "$OLD_DIR/alb-target-groups.json" 2>/dev/null) <(jq -S '.' "$NEW_DIR/alb-target-groups.json" 2>/dev/null) >> "$report" 2>/dev/null || echo "No differences or files missing" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"
    else
        echo "ALB configuration files not found for comparison." >> "$report"
        echo "" >> "$report"
    fi

    # Compare IAM Roles
    echo "## IAM Roles" >> "$report"
    echo "" >> "$report"
    echo "### Task Role Policies" >> "$report"
    echo "" >> "$report"
    echo "**Old Prod (MyEcsTaskRole):**" >> "$report"
    echo '```json' >> "$report"
    jq '.' "$OLD_DIR/iam-role-MyEcsTaskRole-policies.json" >> "$report" 2>/dev/null || echo "{}" >> "$report"
    echo '```' >> "$report"
    echo "" >> "$report"
    echo "**New Prod (prod-ecs-task-role):**" >> "$report"
    echo '```json' >> "$report"
    jq '.' "$NEW_DIR/iam-role-prod-ecs-task-role-policies.json" >> "$report" 2>/dev/null || echo "{}" >> "$report"
    echo '```' >> "$report"
    echo "" >> "$report"

    # Critical differences summary
    echo "## Critical Differences to Verify" >> "$report"
    echo "" >> "$report"
    echo "- [ ] NAT Gateway IP whitelisted in MongoDB Atlas" >> "$report"
    echo "- [ ] NAT Gateway IP whitelisted in FlightLogic (or using SPOOF_IP workaround)" >> "$report"
    echo "- [ ] All secrets populated in new environment" >> "$report"
    echo "- [ ] Security group rules match expected access patterns" >> "$report"
    echo "- [ ] Target group health checks configured correctly" >> "$report"
    echo "- [ ] CloudFlare DNS pointing to correct ALB" >> "$report"
    echo "" >> "$report"

    log_success "Comparison report generated: $report"
    log_info "Individual diffs saved to: $DIFF_DIR"
}

# Generate staging vs old-prod comparison report
generate_staging_comparison() {
    log_info "========================================="
    log_info "Generating STAGING vs OLD-PROD comparison"
    log_info "========================================="

    local staging_diff_dir="${DIFF_DIR}/staging-vs-old-prod"
    mkdir -p "$staging_diff_dir"

    local report="${staging_diff_dir}/comparison-report.md"

    cat > "$report" << 'HEADER'
# Staging vs Old-Prod Environment Comparison

Generated: DATE_PLACEHOLDER

This comparison helps identify what's different between the **working** staging environment
and the **problematic** old production environment.

---

HEADER

    sed -i "s/DATE_PLACEHOLDER/$(date -Iseconds)/" "$report"

    # Compare ECS Task Definitions
    echo "## ECS Task Definition" >> "$report"
    echo "" >> "$report"

    if [[ -f "$STAGING_DIR/ecs-task-definition.json" && -f "$OLD_DIR/ecs-task-definition.json" ]]; then
        echo "### Resource Allocation" >> "$report"
        echo "" >> "$report"
        echo "| Setting | Staging | Old Prod | Notes |" >> "$report"
        echo "|---------|---------|----------|-------|" >> "$report"

        local stg_cpu stg_mem old_cpu old_mem
        stg_cpu=$(jq -r '.cpu // "N/A"' "$STAGING_DIR/ecs-task-definition.json")
        stg_mem=$(jq -r '.memory // "N/A"' "$STAGING_DIR/ecs-task-definition.json")
        old_cpu=$(jq -r '.cpu // "N/A"' "$OLD_DIR/ecs-task-definition.json")
        old_mem=$(jq -r '.memory // "N/A"' "$OLD_DIR/ecs-task-definition.json")

        local cpu_note="" mem_note=""
        [[ "$stg_cpu" != "$old_cpu" ]] && cpu_note="**DIFFERENT**"
        [[ "$stg_mem" != "$old_mem" ]] && mem_note="**DIFFERENT**"

        echo "| CPU | $stg_cpu | $old_cpu | $cpu_note |" >> "$report"
        echo "| Memory | $stg_mem | $old_mem | $mem_note |" >> "$report"
        echo "" >> "$report"

        # Container command comparison
        echo "### Container Command" >> "$report"
        echo "" >> "$report"
        echo "**Staging:**" >> "$report"
        echo '```json' >> "$report"
        jq '.' "$STAGING_DIR/ecs-command.json" >> "$report" 2>/dev/null || echo "[]" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"
        echo "**Old Prod:**" >> "$report"
        echo '```json' >> "$report"
        jq '.' "$OLD_DIR/ecs-command.json" >> "$report" 2>/dev/null || echo "[]" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"

        # Generate diff of env vars
        echo "### Environment Variables Diff" >> "$report"
        echo "" >> "$report"
        echo '```diff' >> "$report"
        diff -u "$STAGING_DIR/ecs-env-vars.json" "$OLD_DIR/ecs-env-vars.json" 2>/dev/null >> "$report" || echo "No differences or files missing" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"

        diff -u "$STAGING_DIR/ecs-env-vars.json" "$OLD_DIR/ecs-env-vars.json" > "$staging_diff_dir/env-vars.diff" 2>/dev/null || true

        # Compare secrets structure
        echo "### Secrets Configuration Diff" >> "$report"
        echo "" >> "$report"
        echo '```diff' >> "$report"
        diff -u "$STAGING_DIR/ecs-secrets.json" "$OLD_DIR/ecs-secrets.json" 2>/dev/null >> "$report" || echo "No differences or files missing" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"

        diff -u "$STAGING_DIR/ecs-secrets.json" "$OLD_DIR/ecs-secrets.json" > "$staging_diff_dir/secrets.diff" 2>/dev/null || true
    fi

    # Compare VPC Configuration
    echo "## VPC Configuration" >> "$report"
    echo "" >> "$report"

    if [[ -f "$STAGING_DIR/vpc.json" && -f "$OLD_DIR/vpc.json" ]]; then
        echo "| Setting | Staging | Old Prod | Notes |" >> "$report"
        echo "|---------|---------|----------|-------|" >> "$report"

        local stg_vpc_cidr old_vpc_cidr stg_nat_ip old_nat_ip
        stg_vpc_cidr=$(jq -r '.Vpcs[0].CidrBlock // "N/A"' "$STAGING_DIR/vpc.json")
        old_vpc_cidr=$(jq -r '.Vpcs[0].CidrBlock // "N/A"' "$OLD_DIR/vpc.json")
        stg_nat_ip=$(cat "$STAGING_DIR/vpc-nat-ips.txt" 2>/dev/null | head -1 || echo "N/A")
        old_nat_ip=$(cat "$OLD_DIR/vpc-nat-ips.txt" 2>/dev/null | head -1 || echo "N/A")

        # Check if old prod is using default VPC
        local old_is_default
        old_is_default=$(jq -r '.Vpcs[0].IsDefault // false' "$OLD_DIR/vpc.json")

        echo "| VPC CIDR | $stg_vpc_cidr | $old_vpc_cidr | |" >> "$report"
        echo "| NAT Gateway IP | $stg_nat_ip | $old_nat_ip | |" >> "$report"
        echo "| Is Default VPC | false | $old_is_default | **Staging uses dedicated VPC** |" >> "$report"
        echo "" >> "$report"

        # Subnet comparison
        echo "### Subnets" >> "$report"
        echo "" >> "$report"

        local stg_subnet_count old_subnet_count
        stg_subnet_count=$(jq 'length' "$STAGING_DIR/vpc-subnets.json" 2>/dev/null || echo 0)
        old_subnet_count=$(jq 'length' "$OLD_DIR/vpc-subnets.json" 2>/dev/null || echo 0)

        echo "| Environment | Subnet Count |" >> "$report"
        echo "|-------------|--------------|" >> "$report"
        echo "| Staging | $stg_subnet_count |" >> "$report"
        echo "| Old Prod | $old_subnet_count |" >> "$report"
        echo "" >> "$report"

        # VPC Endpoints comparison
        echo "### VPC Endpoints" >> "$report"
        echo "" >> "$report"
        echo "**Staging:**" >> "$report"
        echo '```json' >> "$report"
        jq '[.VpcEndpoints[] | {Service: .ServiceName, Type: .VpcEndpointType}] | sort_by(.Service)' "$STAGING_DIR/vpc-endpoints.json" >> "$report" 2>/dev/null || echo "[]" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"
        echo "**Old Prod:**" >> "$report"
        echo '```json' >> "$report"
        jq '[.VpcEndpoints[] | {Service: .ServiceName, Type: .VpcEndpointType}] | sort_by(.Service)' "$OLD_DIR/vpc-endpoints.json" >> "$report" 2>/dev/null || echo "[]" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"
    fi

    # Compare Security Groups
    echo "## Security Groups" >> "$report"
    echo "" >> "$report"

    if [[ -f "$STAGING_DIR/security-groups-summary.json" && -f "$OLD_DIR/security-groups-summary.json" ]]; then
        local stg_sg_count old_sg_count
        stg_sg_count=$(jq 'length' "$STAGING_DIR/security-groups-summary.json" 2>/dev/null || echo 0)
        old_sg_count=$(jq 'length' "$OLD_DIR/security-groups-summary.json" 2>/dev/null || echo 0)

        echo "| Environment | Security Group Count |" >> "$report"
        echo "|-------------|---------------------|" >> "$report"
        echo "| Staging | $stg_sg_count |" >> "$report"
        echo "| Old Prod | $old_sg_count |" >> "$report"
        echo "" >> "$report"

        echo "### Staging Security Groups" >> "$report"
        echo '```json' >> "$report"
        jq '[.[] | {GroupName, InboundRuleCount: (.InboundRules | length), OutboundRuleCount: (.OutboundRules | length)}]' "$STAGING_DIR/security-groups-summary.json" >> "$report" 2>/dev/null || echo "[]" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"

        echo "### Old Prod Security Groups" >> "$report"
        echo '```json' >> "$report"
        jq '[.[] | {GroupName, InboundRuleCount: (.InboundRules | length), OutboundRuleCount: (.OutboundRules | length)}]' "$OLD_DIR/security-groups-summary.json" >> "$report" 2>/dev/null || echo "[]" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"
    fi

    # Compare ALB Configuration
    echo "## ALB Configuration" >> "$report"
    echo "" >> "$report"

    if [[ -f "$STAGING_DIR/alb.json" && -f "$OLD_DIR/alb.json" ]]; then
        echo "| Setting | Staging | Old Prod |" >> "$report"
        echo "|---------|---------|----------|" >> "$report"

        local stg_alb_dns old_alb_dns stg_alb_scheme old_alb_scheme
        stg_alb_dns=$(jq -r '.DNSName // "N/A"' "$STAGING_DIR/alb.json")
        old_alb_dns=$(jq -r '.DNSName // "N/A"' "$OLD_DIR/alb.json")
        stg_alb_scheme=$(jq -r '.Scheme // "N/A"' "$STAGING_DIR/alb.json")
        old_alb_scheme=$(jq -r '.Scheme // "N/A"' "$OLD_DIR/alb.json")

        echo "| DNS Name | $stg_alb_dns | $old_alb_dns |" >> "$report"
        echo "| Scheme | $stg_alb_scheme | $old_alb_scheme |" >> "$report"
        echo "" >> "$report"

        # ALB attributes comparison
        echo "### ALB Attributes Diff" >> "$report"
        echo '```diff' >> "$report"
        diff -u <(jq -S '.' "$STAGING_DIR/alb-attributes.json" 2>/dev/null) <(jq -S '.' "$OLD_DIR/alb-attributes.json" 2>/dev/null) >> "$report" 2>/dev/null || echo "No differences or files missing" >> "$report"
        echo '```' >> "$report"
        echo "" >> "$report"
    fi

    # Key Differences Summary
    echo "## Key Differences Summary" >> "$report"
    echo "" >> "$report"
    echo "Based on the comparison above, notable differences that could affect performance:" >> "$report"
    echo "" >> "$report"
    echo "1. **VPC Type**: Staging uses a dedicated VPC, old prod uses default VPC" >> "$report"
    echo "2. **Resource Allocation**: Check CPU/Memory differences above" >> "$report"
    echo "3. **Container Command**: Check if workers are configured differently" >> "$report"
    echo "4. **Security Groups**: Different rule configurations may affect connectivity" >> "$report"
    echo "5. **VPC Endpoints**: Different endpoint configurations may affect AWS service access" >> "$report"
    echo "" >> "$report"

    log_success "Staging comparison report generated: $report"
    log_info "Individual diffs saved to: $staging_diff_dir"
}

# Create a quick summary for terminal output
print_quick_summary() {
    echo ""
    log_info "========================================="
    log_info "QUICK COMPARISON SUMMARY"
    log_info "========================================="
    echo ""

    if [[ -f "$OLD_DIR/ecs-task-definition.json" && -f "$NEW_DIR/ecs-task-definition.json" ]]; then
        echo "ECS Task Definition:"
        echo "  Old: CPU=$(jq -r '.cpu' "$OLD_DIR/ecs-task-definition.json"), Memory=$(jq -r '.memory' "$OLD_DIR/ecs-task-definition.json")"
        echo "  New: CPU=$(jq -r '.cpu' "$NEW_DIR/ecs-task-definition.json"), Memory=$(jq -r '.memory' "$NEW_DIR/ecs-task-definition.json")"
        echo ""
    fi

    if [[ -f "$OLD_DIR/vpc-nat-ips.txt" && -f "$NEW_DIR/vpc-nat-ips.txt" ]]; then
        echo "NAT Gateway IPs (CRITICAL - must whitelist):"
        echo "  Old: $(cat "$OLD_DIR/vpc-nat-ips.txt" | head -1)"
        echo "  New: $(cat "$NEW_DIR/vpc-nat-ips.txt" | head -1)"
        echo ""
    fi

    if [[ -f "$OLD_DIR/alb.json" && -f "$NEW_DIR/alb.json" ]]; then
        echo "ALB DNS Names:"
        echo "  Old: $(jq -r '.DNSName' "$OLD_DIR/alb.json")"
        echo "  New: $(jq -r '.DNSName' "$NEW_DIR/alb.json")"
        echo ""
    fi

    echo "Environment Variables differences:"
    if [[ -f "$DIFF_DIR/env-vars.diff" ]]; then
        local added removed
        added=$(grep -c '^+[^+]' "$DIFF_DIR/env-vars.diff" 2>/dev/null || echo 0)
        removed=$(grep -c '^-[^-]' "$DIFF_DIR/env-vars.diff" 2>/dev/null || echo 0)
        echo "  Added: $added lines, Removed: $removed lines"
    else
        echo "  Diff not generated yet"
    fi
    echo ""

    log_info "Full report: $DIFF_DIR/comparison-report.md"
}

# Print staging comparison summary
print_staging_summary() {
    echo ""
    log_info "========================================="
    log_info "STAGING vs OLD-PROD SUMMARY"
    log_info "========================================="
    echo ""

    if [[ -f "$STAGING_DIR/ecs-task-definition.json" && -f "$OLD_DIR/ecs-task-definition.json" ]]; then
        echo "ECS Task Definition:"
        echo "  Staging:  CPU=$(jq -r '.cpu' "$STAGING_DIR/ecs-task-definition.json"), Memory=$(jq -r '.memory' "$STAGING_DIR/ecs-task-definition.json")"
        echo "  Old Prod: CPU=$(jq -r '.cpu' "$OLD_DIR/ecs-task-definition.json"), Memory=$(jq -r '.memory' "$OLD_DIR/ecs-task-definition.json")"
        echo ""
    fi

    if [[ -f "$STAGING_DIR/ecs-command.json" && -f "$OLD_DIR/ecs-command.json" ]]; then
        echo "Container Command:"
        echo "  Staging:  $(jq -c '.' "$STAGING_DIR/ecs-command.json")"
        echo "  Old Prod: $(jq -c '.' "$OLD_DIR/ecs-command.json")"
        echo ""
    fi

    if [[ -f "$STAGING_DIR/vpc.json" && -f "$OLD_DIR/vpc.json" ]]; then
        local old_is_default
        old_is_default=$(jq -r '.Vpcs[0].IsDefault // false' "$OLD_DIR/vpc.json")
        echo "VPC Configuration:"
        echo "  Staging:  Dedicated VPC (Terraform-managed)"
        echo "  Old Prod: Default VPC = $old_is_default"
        echo ""
    fi

    if [[ -f "$STAGING_DIR/vpc-nat-ips.txt" && -f "$OLD_DIR/vpc-nat-ips.txt" ]]; then
        echo "NAT Gateway IPs:"
        echo "  Staging:  $(cat "$STAGING_DIR/vpc-nat-ips.txt" | head -1)"
        echo "  Old Prod: $(cat "$OLD_DIR/vpc-nat-ips.txt" | head -1)"
        echo ""
    fi

    local staging_diff_dir="${DIFF_DIR}/staging-vs-old-prod"
    echo "Environment Variables differences:"
    if [[ -f "$staging_diff_dir/env-vars.diff" ]]; then
        local added removed
        added=$(grep -c '^+[^+]' "$staging_diff_dir/env-vars.diff" 2>/dev/null || echo 0)
        removed=$(grep -c '^-[^-]' "$staging_diff_dir/env-vars.diff" 2>/dev/null || echo 0)
        echo "  Added in old-prod: $added lines"
        echo "  Removed from old-prod: $removed lines"
    else
        echo "  Diff not generated yet"
    fi
    echo ""

    log_info "Full report: $staging_diff_dir/comparison-report.md"
}

# Main
main() {
    local mode="${1:-all}"

    setup_dirs

    case "$mode" in
        --old-only)
            export_old_prod
            ;;
        --new-only)
            export_new_prod
            ;;
        --staging)
            export_staging
            ;;
        --compare)
            generate_comparison
            print_quick_summary
            ;;
        --compare-staging)
            generate_staging_comparison
            print_staging_summary
            ;;
        --all)
            export_old_prod
            export_staging
            export_new_prod
            generate_comparison
            generate_staging_comparison
            print_quick_summary
            print_staging_summary
            ;;
        *)
            # Default: old-prod vs new-prod
            export_old_prod
            export_new_prod
            generate_comparison
            print_quick_summary
            ;;
    esac
}

main "$@"
