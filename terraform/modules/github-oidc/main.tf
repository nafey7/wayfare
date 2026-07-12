# GitHub Actions OIDC Provider and Role
# Allows GitHub Actions to deploy to AWS without long-lived credentials

# GitHub OIDC Provider
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com",
  ]

  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"
  ]

  tags = var.tags

  lifecycle {
    ignore_changes = [tags, tags_all]
  }
}

# IAM Role for GitHub Actions
resource "aws_iam_role" "github_actions" {
  name               = "GitHubActionsDeployRole"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json
  description        = "Role for GitHub Actions to deploy to ECS staging"

  tags = var.tags
}

# Trust policy for GitHub Actions OIDC
data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_org}/${var.github_repo}:*"]
    }
  }
}

# Permissions for GitHub Actions to deploy
data "aws_iam_policy_document" "github_actions_deploy" {
  # ECR permissions - push images
  statement {
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload"
    ]
    resources = ["*"]
  }

  # ECS permissions - deploy tasks and run migrations
  statement {
    actions = [
      "ecs:DescribeServices",
      "ecs:DescribeTaskDefinition",
      "ecs:DescribeTasks",
      "ecs:ListTasks",
      "ecs:RegisterTaskDefinition",
      "ecs:RunTask",
      "ecs:UpdateService"
    ]
    resources = ["*"]
  }

  # CloudWatch Logs - fetch migration task logs on failure
  statement {
    actions = [
      "logs:GetLogEvents"
    ]
    resources = ["*"]
  }

  # IAM permissions - pass roles to ECS tasks
  statement {
    actions = [
      "iam:PassRole"
    ]
    resources = concat(var.ecs_task_execution_role_arns, var.ecs_task_role_arns)
    condition {
      test     = "StringLike"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name   = "GitHubActionsDeployPolicy"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.github_actions_deploy.json
}

# =============================================================================
# Terraform Role — used by CI to run terraform plan/apply
# =============================================================================

resource "aws_iam_role" "github_actions_terraform" {
  name               = "GitHubActionsTerraformRole"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json # same OIDC trust
  description        = "Role for GitHub Actions to run Terraform plan and apply"

  tags = var.tags

  lifecycle {
    prevent_destroy = true
  }
}

data "aws_iam_policy_document" "github_actions_terraform" {
  # Terraform state (S3)
  statement {
    sid = "TerraformState"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      "arn:aws:s3:::voya-terraform-state-155304839180",
      "arn:aws:s3:::voya-terraform-state-155304839180/*",
    ]
  }

  # Terraform state locks (DynamoDB)
  statement {
    sid = "TerraformLocks"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem",
    ]
    resources = ["arn:aws:dynamodb:us-east-1:155304839180:table/voya-terraform-locks"]
  }

  # VPC / Networking
  statement {
    sid       = "VPCNetworking"
    actions   = ["ec2:*"]
    resources = ["*"]
  }

  # ECS
  statement {
    sid       = "ECS"
    actions   = ["ecs:*"]
    resources = ["*"]
  }

  # ECR
  statement {
    sid       = "ECR"
    actions   = ["ecr:*"]
    resources = ["*"]
  }

  # IAM (roles, policies, OIDC)
  statement {
    sid = "IAM"
    actions = [
      "iam:Get*",
      "iam:List*",
      "iam:CreateRole",
      "iam:UpdateRole",
      "iam:DeleteRole",
      "iam:CreatePolicy",
      "iam:DeletePolicy",
      "iam:CreatePolicyVersion",
      "iam:DeletePolicyVersion",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:PassRole",
      "iam:CreateOpenIDConnectProvider",
      "iam:UpdateOpenIDConnectProviderThumbprint",
      "iam:AddClientIDToOpenIDConnectProvider",
      "iam:TagOpenIDConnectProvider",
    ]
    resources = ["*"]
  }

  # ELB
  statement {
    sid       = "ELB"
    actions   = ["elasticloadbalancing:*"]
    resources = ["*"]
  }

  # S3 (Strapi media buckets)
  statement {
    sid       = "S3"
    actions   = ["s3:*"]
    resources = ["*"]
  }

  # CloudFront
  statement {
    sid       = "CloudFront"
    actions   = ["cloudfront:*"]
    resources = ["*"]
  }

  # RDS
  statement {
    sid       = "RDS"
    actions   = ["rds:*"]
    resources = ["*"]
  }

  # Secrets Manager
  statement {
    sid       = "SecretsManager"
    actions   = ["secretsmanager:*"]
    resources = ["*"]
  }

  # CloudWatch Logs
  statement {
    sid       = "CloudWatchLogs"
    actions   = ["logs:*"]
    resources = ["*"]
  }

  # Application Auto Scaling
  statement {
    sid       = "AutoScaling"
    actions   = ["application-autoscaling:*"]
    resources = ["*"]
  }

  # SSM Parameter Store (feature flags)
  statement {
    sid       = "SSM"
    actions   = ["ssm:*"]
    resources = ["*"]
  }

  # ACM (read-only, for certificate references)
  statement {
    sid = "ACM"
    actions = [
      "acm:DescribeCertificate",
      "acm:ListCertificates",
      "acm:GetCertificate",
      "acm:ListTagsForCertificate",
    ]
    resources = ["*"]
  }

  # STS (caller identity checks in Terraform)
  statement {
    sid       = "STS"
    actions   = ["sts:GetCallerIdentity"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_actions_terraform" {
  name   = "GitHubActionsTerraformPolicy"
  role   = aws_iam_role.github_actions_terraform.id
  policy = data.aws_iam_policy_document.github_actions_terraform.json
}
