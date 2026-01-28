# PR Peer Review Orchestration System - Deployment Guide

**Version**: 1.0
**Last Updated**: 2026-01-28
**Owner**: DevOps Team
**Target Audience**: DevOps Engineers, Platform Engineers, Release Managers

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Step-by-Step Deployment](#step-by-step-deployment)
5. [Verification Steps](#verification-steps)
6. [Rollback Procedures](#rollback-procedures)
7. [Configuration Templates](#configuration-templates)
8. [Post-Deployment](#post-deployment)
9. [Troubleshooting](#troubleshooting)
10. [Appendix](#appendix)

---

## 1. Overview

### 1.1 System Architecture

The PR Peer Review Orchestration System is a multi-agent workflow that automates code review processes for GitHub Pull Requests. It consists of:

**Core Components**:
- **PR Orchestrator Agent**: Main workflow coordinator and merge decision engine
- **Code Best Practices Agent**: Enforces coding standards and naming conventions
- **Architect Best Practices Agent**: Detects new architectural patterns
- **LLD Alignment Review Agent**: Validates patterns against Low-Level Design specifications
- **Peer Review Documentation Agent**: Manages human architectural reviews
- **Pattern Matching Agent**: Stores approved patterns in Confluence
- **Jira Integration Agent**: Creates tracking tickets for violations

**External Dependencies**:
- GitHub Actions (workflow orchestration)
- Jira Cloud (issue tracking)
- Confluence Cloud (pattern library and LLD storage)
- AWS (optional: DynamoDB for state, SQS for retry queues, ElastiCache for caching)

**Workflow Flow**:
```
PR Created/Updated
    ↓
Pre-Flight Validation → Code Quality Agent → Architect Agent
    ↓                                              ↓
[If new pattern] → LLD Alignment Agent → Peer Review Agent
    ↓                                              ↓
[On merge] → Pattern Storage Agent
    ↓
Final Report + Jira Integration (if failures)
```

### 1.2 Deployment Scope

This guide covers deployment to a single GitHub repository. For multi-repository deployments, see [Appendix C: Multi-Repository Deployment](#appendix-c-multi-repository-deployment).

**Estimated Deployment Time**: 2-4 hours (first repository)

---

## 2. Prerequisites

### 2.1 Required Accounts

| Service | Account Type | Required Permissions | Notes |
|---------|-------------|---------------------|-------|
| **GitHub** | Organization Admin or Repo Admin | Admin access to target repository | Can create webhooks, secrets, workflows |
| **Jira Cloud** | Jira Administrator | Create issues, manage projects | Service account recommended |
| **Confluence Cloud** | Confluence Space Admin | Create/edit pages in designated spaces | Same account as Jira preferred |
| **AWS** (Optional) | IAM User with programmatic access | DynamoDB, SQS, ElastiCache permissions | For production-scale deployments |

### 2.2 Required Tools

Install these tools on your deployment machine:

```bash
# GitHub CLI
# macOS
brew install gh

# Windows (using Chocolatey)
choco install gh

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# Verify installation
gh --version
```

```bash
# AWS CLI (if using AWS infrastructure)
# macOS
brew install awscli

# Windows
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

```bash
# jq (JSON processor for CLI operations)
# macOS
brew install jq

# Windows
choco install jq

# Linux
sudo apt-get install jq

# Verify installation
jq --version
```

### 2.3 Required Permissions

#### GitHub Repository Permissions
- **Admin access** to target repository
- Ability to:
  - Create and modify GitHub Actions workflows
  - Manage repository secrets
  - Configure branch protection rules
  - Create webhooks

#### Jira Permissions
- **Administer Projects** permission on target Jira project
- Ability to:
  - Create issues
  - Modify issue fields
  - Create custom fields
  - Configure automation rules

#### Confluence Permissions
- **Space Admin** role for pattern and LLD spaces
- Ability to:
  - Create pages
  - Edit page properties
  - Manage space permissions

### 2.4 Network Requirements

Ensure the following network connectivity:

| Source | Destination | Port | Protocol | Purpose |
|--------|------------|------|----------|---------|
| GitHub Actions | Jira Cloud API | 443 | HTTPS | Create tickets |
| GitHub Actions | Confluence API | 443 | HTTPS | Query patterns/LLDs |
| GitHub Actions | AWS Services (optional) | 443 | HTTPS | DynamoDB, SQS, ElastiCache |
| Jira Cloud | GitHub API | 443 | HTTPS | Webhook callbacks (optional) |

**Firewall Rules**: If your organization uses IP allowlists, add GitHub Actions IP ranges:
- See: https://api.github.com/meta (check `actions` field)

---

## 3. Pre-Deployment Checklist

### 3.1 GitHub Repository Setup

- [ ] **Repository initialized** with main/develop branches
- [ ] **CODEOWNERS file** created (optional but recommended)
  ```bash
  # Create CODEOWNERS file
  cat > .github/CODEOWNERS <<EOF
  # Default owners for all files
  * @tonic-scm/senior-engineers

  # Architecture owners
  /docs/architecture/ @tonic-scm/architects

  # Specific component owners
  /src/main/java/com/tonic/order/ @tonic-scm/order-team
  EOF
  ```

- [ ] **Branch protection rules** NOT configured yet (will be done in Step 2.2)
- [ ] **Test branch** created for validation
  ```bash
  git checkout -b test/workflow-validation
  git push origin test/workflow-validation
  ```

### 3.2 Jira Project Configuration

- [ ] **Jira project** exists (e.g., project key: `SCM`)
- [ ] **Custom issue types** created or identified:
  - Code Violation (or use "Bug")
  - LLD Deviation (or use "Task")
  - Pattern Rejection (or use "Task")

- [ ] **Custom fields** created (see [7.2 Jira Custom Fields](#72-jira-custom-fields)):
  ```
  customfield_10001: PR URL (URL field)
  customfield_10002: PR Author (Text field)
  customfield_10003: Target Branch (Select field)
  customfield_10004: Review Status (Select field)
  customfield_10005: Code Quality Score (Number field)
  ```

- [ ] **Service account** created:
  ```
  Email: scm-automation@your-domain.com
  Display Name: SCM Automation Agent
  Groups: jira-software-users
  ```

- [ ] **API token** generated for service account:
  1. Log in as service account
  2. Navigate to: https://id.atlassian.com/manage-profile/security/api-tokens
  3. Click "Create API token"
  4. Name: "SCM PR Automation"
  5. Save token securely (you won't see it again!)

### 3.3 Confluence Space Setup

- [ ] **Confluence spaces** created:
  - **SCM-PATTERNS**: Approved coding patterns library
  - **SCM-LLD**: Low-Level Design specifications

- [ ] **Space permissions** configured:
  - Service account has **Admin** permissions on both spaces
  - Development team has **View** permissions
  - Architecture team has **Edit** permissions

- [ ] **Page templates** created (optional):
  - Pattern template (see [7.3 Confluence Pattern Template](#73-confluence-pattern-template))
  - LLD template (see [7.4 Confluence LLD Template](#74-confluence-lld-template))

- [ ] **Initial seed data** (optional but recommended):
  - Create 3-5 sample approved patterns
  - Create 1-2 sample LLD documents
  - Verify patterns are queryable via Confluence REST API

### 3.4 AWS Infrastructure Provisioning (Optional)

Only required for production-scale deployments (>50 PRs/day).

- [ ] **DynamoDB tables** created (see [7.5 AWS Resources](#75-aws-resources)):
  - `pr-review-state`: PR workflow state tracking
  - `pattern-cache`: Confluence pattern cache

- [ ] **SQS queues** created:
  - `pr-review-retry-queue`: Failed operation retry queue
  - `jira-ticket-queue`: Asynchronous Jira ticket creation

- [ ] **ElastiCache cluster** provisioned (optional):
  - Redis cluster for pattern caching
  - VPC configuration if GitHub Actions uses self-hosted runners

- [ ] **IAM roles and policies** created:
  - GitHub Actions service role
  - DynamoDB read/write policy
  - SQS send/receive policy
  - ElastiCache access policy

---

## 4. Step-by-Step Deployment

### Step 1: AWS Infrastructure Setup (Optional)

Skip this step if not using AWS resources.

#### 1.1 Create DynamoDB Tables

```bash
#!/bin/bash
# Create DynamoDB tables for PR workflow state

AWS_REGION="us-east-1"

# Create pr-review-state table
aws dynamodb create-table \
  --table-name pr-review-state \
  --attribute-definitions \
    AttributeName=pr_number,AttributeType=N \
    AttributeName=repository,AttributeType=S \
  --key-schema \
    AttributeName=pr_number,KeyType=HASH \
    AttributeName=repository,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region $AWS_REGION \
  --tags Key=Project,Value=SCM-PR-Review Key=Environment,Value=Production

echo "pr-review-state table created"

# Create pattern-cache table
aws dynamodb create-table \
  --table-name pattern-cache \
  --attribute-definitions \
    AttributeName=pattern_id,AttributeType=S \
  --key-schema \
    AttributeName=pattern_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $AWS_REGION \
  --tags Key=Project,Value=SCM-PR-Review Key=Environment,Value=Production

echo "pattern-cache table created"

# Enable TTL on pattern-cache (30-minute cache)
aws dynamodb update-time-to-live \
  --table-name pattern-cache \
  --time-to-live-specification "Enabled=true, AttributeName=ttl" \
  --region $AWS_REGION

echo "TTL enabled on pattern-cache"
```

#### 1.2 Create SQS Queues

```bash
#!/bin/bash
# Create SQS queues for retry logic

AWS_REGION="us-east-1"

# Create retry queue
aws sqs create-queue \
  --queue-name pr-review-retry-queue \
  --attributes '{
    "DelaySeconds": "0",
    "MaximumMessageSize": "262144",
    "MessageRetentionPeriod": "345600",
    "ReceiveMessageWaitTimeSeconds": "10",
    "VisibilityTimeout": "300"
  }' \
  --region $AWS_REGION \
  --tags Key=Project,Value=SCM-PR-Review Key=Environment,Value=Production

echo "pr-review-retry-queue created"

# Create Jira ticket queue
aws sqs create-queue \
  --queue-name jira-ticket-queue \
  --attributes '{
    "DelaySeconds": "0",
    "MaximumMessageSize": "262144",
    "MessageRetentionPeriod": "1209600",
    "ReceiveMessageWaitTimeSeconds": "10",
    "VisibilityTimeout": "120"
  }' \
  --region $AWS_REGION \
  --tags Key=Project,Value=SCM-PR-Review Key=Environment,Value=Production

echo "jira-ticket-queue created"

# Create dead-letter queue for failed retries
aws sqs create-queue \
  --queue-name pr-review-dlq \
  --attributes '{
    "MessageRetentionPeriod": "1209600"
  }' \
  --region $AWS_REGION \
  --tags Key=Project,Value=SCM-PR-Review Key=Environment,Value=Production

echo "pr-review-dlq (dead-letter queue) created"
```

#### 1.3 Create IAM Roles and Policies

```bash
#!/bin/bash
# Create IAM policy for GitHub Actions

cat > github-actions-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:*:table/pr-review-state",
        "arn:aws:dynamodb:us-east-1:*:table/pattern-cache"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": [
        "arn:aws:sqs:us-east-1:*:pr-review-retry-queue",
        "arn:aws:sqs:us-east-1:*:jira-ticket-queue",
        "arn:aws:sqs:us-east-1:*:pr-review-dlq"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticache:DescribeCacheClusters",
        "elasticache:DescribeReplicationGroups"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create IAM policy
aws iam create-policy \
  --policy-name GitHubActionsPRReviewPolicy \
  --policy-document file://github-actions-policy.json \
  --description "Policy for GitHub Actions to access PR Review resources"

echo "IAM policy created"
echo "Policy ARN: arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/GitHubActionsPRReviewPolicy"
echo "Attach this policy to your GitHub Actions IAM user or role"
```

#### 1.4 Verify AWS Resources

```bash
#!/bin/bash
# Verify all AWS resources are created

AWS_REGION="us-east-1"

echo "=== Verifying AWS Resources ==="

# Check DynamoDB tables
echo -e "\nDynamoDB Tables:"
aws dynamodb list-tables --region $AWS_REGION | jq -r '.TableNames[] | select(startswith("pr-review") or startswith("pattern-cache"))'

# Check SQS queues
echo -e "\nSQS Queues:"
aws sqs list-queues --region $AWS_REGION | jq -r '.QueueUrls[] | select(contains("pr-review") or contains("jira-ticket"))'

# Check IAM policy
echo -e "\nIAM Policy:"
aws iam get-policy --policy-arn "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/GitHubActionsPRReviewPolicy" | jq '.Policy | {PolicyName, Arn, CreateDate}'

echo -e "\n=== Verification Complete ==="
```

---

### Step 2: GitHub Configuration

#### 2.1 Repository Secrets Setup

Configure all required secrets in GitHub repository.

**Method 1: GitHub CLI (Recommended)**

```bash
#!/bin/bash
# Configure GitHub repository secrets

REPO_OWNER="tonic-scm"
REPO_NAME="order-service"

# Jira secrets
gh secret set JIRA_BASE_URL \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "https://your-domain.atlassian.net"

gh secret set JIRA_USER_EMAIL \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "scm-automation@your-domain.com"

gh secret set JIRA_API_TOKEN \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "ATATT3xFfGF0..." # Paste actual token

gh secret set JIRA_PROJECT_KEY \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "SCM"

gh secret set JIRA_DEFAULT_ASSIGNEE \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "architecture-team-lead@your-domain.com"

# Confluence secrets
gh secret set CONFLUENCE_BASE_URL \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "https://your-domain.atlassian.net/wiki"

gh secret set CONFLUENCE_API_TOKEN \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "ATATT3xFfGF0..." # Same as Jira token if using same account

gh secret set CONFLUENCE_SPACE_PATTERNS \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "SCM-PATTERNS"

gh secret set CONFLUENCE_SPACE_LLD \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "SCM-LLD"

# AWS secrets (optional)
gh secret set AWS_ACCESS_KEY_ID \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "AKIA..."

gh secret set AWS_SECRET_ACCESS_KEY \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "wJalr..."

gh secret set AWS_REGION \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "us-east-1"

echo "All secrets configured successfully"
```

**Method 2: GitHub UI**

1. Navigate to repository: `https://github.com/tonic-scm/order-service`
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret from the table below:

| Secret Name | Example Value | Description |
|------------|---------------|-------------|
| `JIRA_BASE_URL` | `https://your-domain.atlassian.net` | Jira instance URL |
| `JIRA_USER_EMAIL` | `scm-automation@your-domain.com` | Service account email |
| `JIRA_API_TOKEN` | `ATATT3xFfGF0...` | Jira API token |
| `JIRA_PROJECT_KEY` | `SCM` | Jira project key |
| `JIRA_DEFAULT_ASSIGNEE` | `arch-lead@your-domain.com` | Default assignee email |
| `CONFLUENCE_BASE_URL` | `https://your-domain.atlassian.net/wiki` | Confluence instance URL |
| `CONFLUENCE_API_TOKEN` | `ATATT3xFfGF0...` | Confluence API token |
| `CONFLUENCE_SPACE_PATTERNS` | `SCM-PATTERNS` | Patterns space key |
| `CONFLUENCE_SPACE_LLD` | `SCM-LLD` | LLD space key |
| `AWS_ACCESS_KEY_ID` | `AKIA...` | AWS access key (optional) |
| `AWS_SECRET_ACCESS_KEY` | `wJalr...` | AWS secret key (optional) |
| `AWS_REGION` | `us-east-1` | AWS region (optional) |

#### 2.2 Workflow File Deployment

Deploy the GitHub Actions workflow file.

```bash
#!/bin/bash
# Deploy GitHub Actions workflow

REPO_OWNER="tonic-scm"
REPO_NAME="order-service"
REPO_PATH="/path/to/local/repository"

# Navigate to repository
cd "$REPO_PATH"

# Create workflows directory if it doesn't exist
mkdir -p .github/workflows

# Copy workflow file from this repository
# Assuming you have the tonic-peer-review-agent repository cloned
cp /path/to/tonic-peer-review-agent/.github/workflows/peer_review.yml \
   .github/workflows/peer_review.yml

# Review workflow file
cat .github/workflows/peer_review.yml

# Commit and push
git add .github/workflows/peer_review.yml
git commit -m "Add PR peer review orchestration workflow"
git push origin main

echo "Workflow file deployed to main branch"
```

**Alternative: Manual Deployment**

1. Copy the workflow file:
   - Source: `tonic-peer-review-agent/.github/workflows/peer_review.yml`
   - Destination: `your-repo/.github/workflows/peer_review.yml`

2. Commit and push:
   ```bash
   git add .github/workflows/peer_review.yml
   git commit -m "Add PR peer review orchestration workflow"
   git push origin main
   ```

#### 2.3 Agent and Skill File Deployment

Deploy agent and skill configuration files.

```bash
#!/bin/bash
# Deploy agent and skill files

REPO_PATH="/path/to/local/repository"
cd "$REPO_PATH"

# Create agents directory
mkdir -p .github/agents

# Copy agent files
cp /path/to/tonic-peer-review-agent/agents/*.md .github/agents/

# Create skills directory
mkdir -p .github/skills

# Copy skill files
cp /path/to/tonic-peer-review-agent/skills/*.md .github/skills/

# List deployed files
echo "Deployed agent files:"
ls -1 .github/agents/

echo -e "\nDeployed skill files:"
ls -1 .github/skills/

# Commit and push
git add .github/agents/ .github/skills/
git commit -m "Add PR review agent and skill configurations"
git push origin main

echo "Agent and skill files deployed"
```

**Deployed Agent Files**:
- `architect_best_practises_agent.md`
- `code_best_practises_agent.md`
- `jira_integration_agent.md`
- `lld_alignment_review_agent.md`
- `pattern_matching_agent.md`
- `peer_review_documentation_agent.md`
- `pr_orchestrator_agent.md`

**Deployed Skill Files**:
- `jira_ticket_skill.md`
- `orchestrator_skill.md`

#### 2.4 Branch Protection Rules

Configure branch protection rules to enforce workflow status checks.

**Method 1: GitHub CLI**

```bash
#!/bin/bash
# Configure branch protection for main branch

REPO_OWNER="tonic-scm"
REPO_NAME="order-service"
BRANCH="main"

gh api \
  --method PUT \
  /repos/$REPO_OWNER/$REPO_NAME/branches/$BRANCH/protection \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "checks": [
      {
        "context": "pr-orchestrator / workflow-validation",
        "app_id": -1
      },
      {
        "context": "code-quality / code-best-practises",
        "app_id": -1
      },
      {
        "context": "architecture / architect-best-practises",
        "app_id": -1
      }
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0,
    "require_last_push_approval": true
  },
  "required_conversation_resolution": true,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_signatures": false,
  "lock_branch": false,
  "restrictions": null
}
EOF

echo "Branch protection configured for $BRANCH"
```

**Method 2: GitHub UI**

See detailed instructions in [Branch Protection Configuration Guide](../research/branch_protection_config.md).

**Quick Steps**:
1. Go to **Settings** → **Branches**
2. Click **Add rule**
3. Branch name pattern: `main`
4. Check:
   - ✓ Require a pull request before merging
   - ✓ Require status checks to pass before merging
     - Select: `pr-orchestrator / workflow-validation`
     - Select: `code-quality / code-best-practises`
     - Select: `architecture / architect-best-practises`
   - ✓ Require branches to be up to date before merging
   - ✓ Require conversation resolution before merging
   - ✓ Require linear history
   - ✓ Do not allow bypassing the above settings
5. Click **Create**

#### 2.5 Configuration Validation

Verify all GitHub configuration is correct.

```bash
#!/bin/bash
# Validate GitHub configuration

REPO_OWNER="tonic-scm"
REPO_NAME="order-service"

echo "=== GitHub Configuration Validation ==="

# Check secrets (names only, not values)
echo -e "\n1. Repository Secrets:"
gh secret list --repo "$REPO_OWNER/$REPO_NAME"

# Check workflow files
echo -e "\n2. Workflow Files:"
gh api /repos/$REPO_OWNER/$REPO_NAME/contents/.github/workflows | jq -r '.[].name'

# Check branch protection
echo -e "\n3. Branch Protection (main):"
gh api /repos/$REPO_OWNER/$REPO_NAME/branches/main/protection | jq '{
  required_status_checks: .required_status_checks.checks[].context,
  enforce_admins: .enforce_admins.enabled,
  required_reviews: .required_pull_request_reviews.required_approving_review_count
}'

echo -e "\n=== Validation Complete ==="
```

---

### Step 3: Jira Configuration

#### 3.1 Project Setup

Verify Jira project configuration.

```bash
#!/bin/bash
# Verify Jira project configuration

JIRA_BASE_URL="https://your-domain.atlassian.net"
JIRA_EMAIL="scm-automation@your-domain.com"
JIRA_API_TOKEN="ATATT3xFfGF0..."
JIRA_PROJECT_KEY="SCM"

# Test authentication
echo "Testing Jira authentication..."
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/3/myself" | jq '.'

# Get project details
echo -e "\nGetting project details..."
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/3/project/$JIRA_PROJECT_KEY" | jq '{
    key: .key,
    name: .name,
    projectTypeKey: .projectTypeKey,
    lead: .lead.displayName
  }'

# List issue types
echo -e "\nAvailable issue types:"
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/3/issuetype" | jq -r '.[] | select(.scope.project.key == "'"$JIRA_PROJECT_KEY"'") | {name: .name, id: .id}'
```

#### 3.2 Custom Fields Configuration

Create custom fields for PR tracking.

**Note**: Custom field creation requires Jira Administrator permissions. If you don't have admin access, request these fields from your Jira admin.

**Required Custom Fields**:

| Field Name | Field Type | Description | Field ID (example) |
|-----------|-----------|-------------|-------------------|
| PR URL | URL | Link to GitHub Pull Request | `customfield_10001` |
| PR Author | Text Field (single line) | GitHub username of PR author | `customfield_10002` |
| Target Branch | Select List (single choice) | Target branch (main, develop, release/*) | `customfield_10003` |
| Review Status | Select List (single choice) | Pending, In Review, Approved, Rejected | `customfield_10004` |
| Code Quality Score | Number Field | Code quality score (0-100) | `customfield_10005` |

**Manual Creation Steps**:

1. Navigate to Jira **Settings** → **Issues** → **Custom fields**
2. Click **Create custom field**
3. For each field:
   - Select field type
   - Enter name and description
   - Click **Create**
   - Associate with screens (e.g., Default Screen)
   - Note the field ID (visible in field configuration URL)

**Programmatic Creation** (requires admin API access):

```bash
#!/bin/bash
# Create custom fields via Jira REST API
# Note: Requires Jira Administrator permissions

JIRA_BASE_URL="https://your-domain.atlassian.net"
JIRA_EMAIL="jira-admin@your-domain.com"
JIRA_API_TOKEN="..."

# Create PR URL field
curl -X POST \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/3/field" \
  -d '{
    "name": "PR URL",
    "description": "Link to GitHub Pull Request",
    "type": "url",
    "searcherKey": "com.atlassian.jira.plugin.system.customfieldtypes:urlfieldtext"
  }'

# Note: Repeat for other fields with appropriate types
```

#### 3.3 Automation Rules (Optional)

Configure Jira automation for bidirectional GitHub integration.

**Automation Rule 1: Auto-transition on PR merge**

1. Navigate to **Project settings** → **Automation**
2. Click **Create rule**
3. Configure:
   - **Trigger**: Webhook
   - **Condition**: Issue has label `pr-*`
   - **Action**: Transition issue to "Closed"
4. Save rule

**Automation Rule 2: Notify assignee**

1. Create new rule
2. Configure:
   - **Trigger**: Issue created
   - **Condition**: Issue type = "Code Violation" OR "LLD Deviation"
   - **Action**: Send email to assignee
3. Save rule

---

### Step 4: Confluence Configuration

#### 4.1 Space Setup Verification

Verify Confluence spaces are properly configured.

```bash
#!/bin/bash
# Verify Confluence space configuration

CONFLUENCE_BASE_URL="https://your-domain.atlassian.net/wiki"
CONFLUENCE_EMAIL="scm-automation@your-domain.com"
CONFLUENCE_API_TOKEN="ATATT3xFfGF0..."

# Test authentication
echo "Testing Confluence authentication..."
curl -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$CONFLUENCE_BASE_URL/rest/api/user/current" | jq '.'

# Get SCM-PATTERNS space details
echo -e "\nGetting SCM-PATTERNS space details..."
curl -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$CONFLUENCE_BASE_URL/rest/api/space/SCM-PATTERNS?expand=permissions" | jq '{
    key: .key,
    name: .name,
    type: .type
  }'

# Get SCM-LLD space details
echo -e "\nGetting SCM-LLD space details..."
curl -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$CONFLUENCE_BASE_URL/rest/api/space/SCM-LLD" | jq '{
    key: .key,
    name: .name,
    type: .type
  }'

# List pages in SCM-PATTERNS space
echo -e "\nPages in SCM-PATTERNS space:"
curl -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$CONFLUENCE_BASE_URL/rest/api/space/SCM-PATTERNS/content/page" | jq '.results[] | {title: .title, id: .id}'
```

#### 4.2 Seed Pattern Data (Optional)

Create sample approved patterns for initial testing.

```bash
#!/bin/bash
# Create sample pattern in Confluence

CONFLUENCE_BASE_URL="https://your-domain.atlassian.net/wiki"
CONFLUENCE_EMAIL="scm-automation@your-domain.com"
CONFLUENCE_API_TOKEN="ATATT3xFfGF0..."
SPACE_KEY="SCM-PATTERNS"

# Get space ID
SPACE_ID=$(curl -s -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" \
  "$CONFLUENCE_BASE_URL/rest/api/space/$SPACE_KEY" | jq -r '.id')

# Create sample pattern page
curl -X POST \
  -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$CONFLUENCE_BASE_URL/rest/api/content" \
  -d '{
    "type": "page",
    "title": "PTN-JAVA-001: Builder Pattern for Complex Objects",
    "space": {
      "key": "'"$SPACE_KEY"'"
    },
    "body": {
      "storage": {
        "value": "<h2>Pattern Description</h2><p>Use Builder pattern for objects with more than 4 constructor parameters.</p><h2>Use Cases</h2><ul><li>Complex configuration objects</li><li>DTOs with optional fields</li></ul><h2>Code Example</h2><ac:structured-macro ac:name=\"code\"><ac:parameter ac:name=\"language\">java</ac:parameter><ac:plain-text-body><![CDATA[public class User {\n    private final String name;\n    private final String email;\n    \n    private User(Builder builder) {\n        this.name = builder.name;\n        this.email = builder.email;\n    }\n    \n    public static class Builder {\n        private String name;\n        private String email;\n        \n        public Builder name(String name) {\n            this.name = name;\n            return this;\n        }\n        \n        public Builder email(String email) {\n            this.email = email;\n            return this;\n        }\n        \n        public User build() {\n            return new User(this);\n        }\n    }\n}]]></ac:plain-text-body></ac:structured-macro>",
        "representation": "storage"
      }
    },
    "metadata": {
      "properties": {
        "pattern_id": {"value": "PTN-JAVA-001"},
        "status": {"value": "APPROVED"},
        "version": {"value": "1.0"},
        "category": {"value": "design-pattern"},
        "language": {"value": "java"}
      }
    }
  }' | jq '.'

echo "Sample pattern created"
```

---

## 5. Verification Steps

### 5.1 Test PR Creation

Create a test PR to trigger the workflow.

```bash
#!/bin/bash
# Create test PR to verify workflow

REPO_PATH="/path/to/local/repository"
cd "$REPO_PATH"

# Create test branch
git checkout -b test/workflow-verification
git fetch origin main
git merge origin/main

# Create a simple code change
cat > test-file.java <<EOF
public class TestClass {
    // This is a test class to verify workflow
    private String name;

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }
}
EOF

git add test-file.java
git commit -m "Test: Verify PR workflow execution"
git push origin test/workflow-verification

# Create PR using GitHub CLI
gh pr create \
  --title "Test: Workflow Verification" \
  --body "This PR verifies the PR peer review orchestration workflow is functioning correctly. Please monitor workflow execution in the Actions tab." \
  --base main \
  --head test/workflow-verification

echo "Test PR created. Monitor execution in GitHub Actions tab."
```

### 5.2 Verify Workflow Triggers

Monitor the GitHub Actions workflow execution.

```bash
#!/bin/bash
# Monitor workflow execution

REPO_OWNER="tonic-scm"
REPO_NAME="order-service"

# Get latest workflow run
gh run list \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --workflow peer_review.yml \
  --limit 1 \
  --json databaseId,status,conclusion,headBranch,event,createdAt

# Get workflow run ID
RUN_ID=$(gh run list --repo "$REPO_OWNER/$REPO_NAME" --workflow peer_review.yml --limit 1 --json databaseId --jq '.[0].databaseId')

# Watch workflow execution in real-time
gh run watch "$RUN_ID" --repo "$REPO_OWNER/$REPO_NAME"

# View workflow logs
gh run view "$RUN_ID" --repo "$REPO_OWNER/$REPO_NAME" --log
```

**Expected Workflow Jobs**:

1. **Pre-Flight Validation**: ✓ Passed (detects code changes)
2. **Code Best Practices Agent**: ✓ Passed (validates code quality)
3. **Architect Best Practices Agent**: Status depends on pattern detection
   - ✓ Passed (no new pattern) OR
   - ⚠️ New Pattern Detected → triggers LLD Review
4. **LLD Alignment Review** (if new pattern): Status depends on LLD compliance
5. **Peer Review Documentation** (if LLD compliant): ⏳ Pending (awaits human review)
6. **Final Report**: ✓ Always runs

### 5.3 Verify Jira Ticket Creation

If any validation fails, verify Jira ticket is created.

**Intentionally Fail Code Quality** (to test Jira integration):

```bash
# Create a PR with intentional code quality violations

cat > BadCodeExample.java <<EOF
public class badclassname {  // Violation: class name should be PascalCase
    private String x;  // Violation: non-descriptive variable name

    public String getX() { return x; }  // Violation: method name should be descriptive
}
EOF

git add BadCodeExample.java
git commit -m "Test: Code quality violation"
git push origin test/workflow-verification

# This should trigger Code Quality Agent failure → Jira ticket creation
```

**Verify Jira Ticket**:

```bash
#!/bin/bash
# Search for created Jira tickets

JIRA_BASE_URL="https://your-domain.atlassian.net"
JIRA_EMAIL="scm-automation@your-domain.com"
JIRA_API_TOKEN="..."
JIRA_PROJECT_KEY="SCM"

# Search for recent tickets with peer-review label
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/3/search?jql=project=$JIRA_PROJECT_KEY AND labels=peer-review AND created >= -1d" | jq '.issues[] | {
    key: .key,
    summary: .fields.summary,
    status: .fields.status.name,
    created: .fields.created
  }'
```

### 5.4 End-to-End Validation

Complete end-to-end validation checklist.

- [ ] **Test PR created successfully**
- [ ] **Workflow triggered automatically**
- [ ] **Pre-Flight Validation job passed**
- [ ] **Code Best Practices Agent executed**
- [ ] **Architect Best Practices Agent executed**
- [ ] **Status checks appear on PR** (view PR in GitHub UI)
- [ ] **PR comment posted** with validation summary
- [ ] **Jira ticket created** (if validation failed)
- [ ] **Branch protection enforced** (merge blocked if checks fail)
- [ ] **Confluence query succeeded** (check workflow logs)
- [ ] **AWS resources accessed** (if configured, check CloudWatch logs)

**Validation Script**:

```bash
#!/bin/bash
# Comprehensive end-to-end validation

REPO_OWNER="tonic-scm"
REPO_NAME="order-service"
PR_NUMBER=$(gh pr list --repo "$REPO_OWNER/$REPO_NAME" --head test/workflow-verification --json number --jq '.[0].number')

echo "=== End-to-End Validation ==="
echo "PR Number: $PR_NUMBER"

# Check PR status checks
echo -e "\n1. PR Status Checks:"
gh pr view "$PR_NUMBER" --repo "$REPO_OWNER/$REPO_NAME" --json statusCheckRollup | jq '.statusCheckRollup[] | {
  name: .name,
  status: .status,
  conclusion: .conclusion
}'

# Check PR comments
echo -e "\n2. PR Comments (from workflow):"
gh pr view "$PR_NUMBER" --repo "$REPO_OWNER/$REPO_NAME" --json comments | jq '.comments[] | select(.author.login == "github-actions") | {
  created: .createdAt,
  body: .body
}'

# Check PR labels
echo -e "\n3. PR Labels:"
gh pr view "$PR_NUMBER" --repo "$REPO_OWNER/$REPO_NAME" --json labels | jq '.labels[].name'

# Check merge status
echo -e "\n4. PR Merge Status:"
gh pr view "$PR_NUMBER" --repo "$REPO_OWNER/$REPO_NAME" --json mergeable,mergeStateStatus | jq '.'

echo -e "\n=== Validation Complete ==="
```

---

## 6. Rollback Procedures

### 6.1 Disable the System

If critical issues are discovered post-deployment, disable the system immediately.

#### Option 1: Disable Workflow (Quick)

```bash
#!/bin/bash
# Disable workflow by renaming the file

REPO_PATH="/path/to/local/repository"
cd "$REPO_PATH"

# Rename workflow file to disable it
mv .github/workflows/peer_review.yml .github/workflows/peer_review.yml.disabled

git add .github/workflows/
git commit -m "EMERGENCY: Disable PR review workflow"
git push origin main

echo "Workflow disabled. PRs will no longer trigger automated review."
```

#### Option 2: Disable Branch Protection (Allows Manual Merge)

```bash
#!/bin/bash
# Remove required status checks from branch protection

REPO_OWNER="tonic-scm"
REPO_NAME="order-service"
BRANCH="main"

# Remove all required status checks
gh api \
  --method PUT \
  /repos/$REPO_OWNER/$REPO_NAME/branches/$BRANCH/protection \
  --input - <<EOF
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "required_approving_review_count": 1
  },
  "required_conversation_resolution": true,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "restrictions": null
}
EOF

echo "Branch protection updated: Required status checks removed"
echo "Manual PR approval now required (1 reviewer)"
```

### 6.2 Revert Changes

Completely remove the PR review system.

```bash
#!/bin/bash
# Complete rollback script

REPO_PATH="/path/to/local/repository"
cd "$REPO_PATH"

# Remove workflow file
rm .github/workflows/peer_review.yml

# Remove agent and skill files
rm -rf .github/agents/
rm -rf .github/skills/

# Commit removal
git add .github/
git commit -m "Rollback: Remove PR review orchestration system"
git push origin main

echo "System files removed from repository"
```

**Cleanup GitHub Secrets**:

```bash
#!/bin/bash
# Remove GitHub secrets

REPO_OWNER="tonic-scm"
REPO_NAME="order-service"

# List of secrets to remove
SECRETS=(
  "JIRA_BASE_URL"
  "JIRA_USER_EMAIL"
  "JIRA_API_TOKEN"
  "JIRA_PROJECT_KEY"
  "JIRA_DEFAULT_ASSIGNEE"
  "CONFLUENCE_BASE_URL"
  "CONFLUENCE_API_TOKEN"
  "CONFLUENCE_SPACE_PATTERNS"
  "CONFLUENCE_SPACE_LLD"
  "AWS_ACCESS_KEY_ID"
  "AWS_SECRET_ACCESS_KEY"
  "AWS_REGION"
)

for secret in "${SECRETS[@]}"; do
  gh secret remove "$secret" --repo "$REPO_OWNER/$REPO_NAME"
  echo "Removed secret: $secret"
done
```

**Cleanup AWS Resources** (if provisioned):

```bash
#!/bin/bash
# Delete AWS resources

AWS_REGION="us-east-1"

# Delete DynamoDB tables
aws dynamodb delete-table --table-name pr-review-state --region $AWS_REGION
aws dynamodb delete-table --table-name pattern-cache --region $AWS_REGION

# Delete SQS queues
aws sqs delete-queue --queue-url "$(aws sqs get-queue-url --queue-name pr-review-retry-queue --region $AWS_REGION --output text)" --region $AWS_REGION
aws sqs delete-queue --queue-url "$(aws sqs get-queue-url --queue-name jira-ticket-queue --region $AWS_REGION --output text)" --region $AWS_REGION
aws sqs delete-queue --queue-url "$(aws sqs get-queue-url --queue-name pr-review-dlq --region $AWS_REGION --output text)" --region $AWS_REGION

# Delete IAM policy
aws iam delete-policy --policy-arn "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/GitHubActionsPRReviewPolicy"

echo "AWS resources deleted"
```

### 6.3 Restore Previous Workflow

If replacing an existing review workflow, restore the previous version.

```bash
#!/bin/bash
# Restore previous workflow from git history

REPO_PATH="/path/to/local/repository"
cd "$REPO_PATH"

# Find previous workflow file in git history
git log --all --full-history -- .github/workflows/

# Restore specific version (replace <commit-hash> with actual hash)
git checkout <commit-hash> -- .github/workflows/previous_workflow.yml

# Commit restoration
git add .github/workflows/
git commit -m "Restore previous workflow configuration"
git push origin main

echo "Previous workflow restored"
```

---

## 7. Configuration Templates

### 7.1 Sample .env File

For local testing and development.

```bash
# .env.example
# Copy to .env and fill in actual values

# GitHub Configuration
GITHUB_OWNER=tonic-scm
GITHUB_REPO=order-service
GITHUB_TOKEN=ghp_YourPersonalAccessToken

# Jira Configuration
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_USER_EMAIL=scm-automation@your-domain.com
JIRA_API_TOKEN=ATATT3xFfGF0...
JIRA_PROJECT_KEY=SCM
JIRA_DEFAULT_ASSIGNEE=architecture-team-lead@your-domain.com

# Confluence Configuration
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_API_TOKEN=ATATT3xFfGF0...
CONFLUENCE_SPACE_PATTERNS=SCM-PATTERNS
CONFLUENCE_SPACE_LLD=SCM-LLD

# AWS Configuration (Optional)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalr...
AWS_REGION=us-east-1

# Agent SLA Configuration (Optional - uses defaults if not set)
CODE_AGENT_SLA=30
ARCHITECT_AGENT_SLA=10
LLD_AGENT_SLA=20
PEER_REVIEW_SLA=14400
```

### 7.2 Jira Custom Fields

Custom field configuration for Jira project.

```json
{
  "custom_fields": {
    "pr_url": {
      "name": "PR URL",
      "type": "url",
      "description": "Link to GitHub Pull Request",
      "field_id": "customfield_10001",
      "required": false,
      "searchable": true
    },
    "pr_author": {
      "name": "PR Author",
      "type": "text",
      "description": "GitHub username of PR author",
      "field_id": "customfield_10002",
      "required": false,
      "searchable": true
    },
    "target_branch": {
      "name": "Target Branch",
      "type": "select",
      "description": "Git branch targeted by PR",
      "field_id": "customfield_10003",
      "options": ["main", "develop", "release/*", "hotfix/*"],
      "required": false,
      "searchable": true
    },
    "review_status": {
      "name": "Review Status",
      "type": "select",
      "description": "Current status of peer review",
      "field_id": "customfield_10004",
      "options": ["Pending", "In Review", "Approved", "Changes Requested", "Rejected"],
      "required": false,
      "searchable": true
    },
    "code_quality_score": {
      "name": "Code Quality Score",
      "type": "number",
      "description": "Code quality score (0-100)",
      "field_id": "customfield_10005",
      "required": false,
      "searchable": true
    }
  }
}
```

### 7.3 Confluence Pattern Template

Template for creating approved coding patterns in Confluence.

```markdown
# PTN-{LANGUAGE}-{ID}: {Pattern Name}

## Metadata

- **Status**: APPROVED
- **Version**: 1.0
- **Category**: {design-pattern | architectural | idiom | best-practice}
- **Language**: {Java | Python | JavaScript | Go | etc.}
- **Framework**: {Spring Boot | React | Django | etc.}
- **Approved By**: {Architect Names}
- **Approval Date**: {YYYY-MM-DD}
- **Source PR**: [#{PR_NUMBER}](https://github.com/org/repo/pull/{PR_NUMBER})
- **LLD Reference**: [LLD Document](link-to-confluence-lld)

---

## Description

{1-2 paragraph description of the pattern, what problem it solves, and why it's approved}

---

## Use Cases

- {Use case 1}
- {Use case 2}
- {Use case 3}

---

## Code Example

```{language}
{Complete, runnable code example demonstrating the pattern}
```

---

## Design Constraints (per LLD)

- ✅ {Constraint 1 from LLD - explain how pattern satisfies it}
- ✅ {Constraint 2 from LLD - explain how pattern satisfies it}
- ✅ {Constraint 3 from LLD - explain how pattern satisfies it}

---

## Anti-Patterns to Avoid

- ❌ {Anti-pattern 1 - what NOT to do}
- ❌ {Anti-pattern 2 - what NOT to do}

---

## Related Patterns

- [PTN-XXX-YYY: {Related Pattern Name}](link)
- [PTN-XXX-ZZZ: {Related Pattern Name}](link)

---

## Testing Considerations

{How to test code that uses this pattern}

---

## Performance Considerations

{Any performance implications of this pattern}

---

## Security Considerations

{Any security implications of this pattern}

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | {YYYY-MM-DD} | {Author} | Initial approval |
```

### 7.4 Confluence LLD Template

Template for Low-Level Design specifications in Confluence.

```markdown
# LLD: {Component Name}

## Document Control

- **Version**: 1.0
- **Last Updated**: {YYYY-MM-DD}
- **Authors**: {Architecture Team}
- **Status**: APPROVED
- **Related HLD**: [High-Level Design](link)

---

## 1. Component Overview

### 1.1 Purpose
{What does this component do?}

### 1.2 Scope
{What is in scope / out of scope}

### 1.3 Dependencies
- {Dependency 1}
- {Dependency 2}

---

## 2. Design Constraints

### 2.1 Architecture Constraints
- {Constraint 1: e.g., "Must follow hexagonal architecture"}
- {Constraint 2: e.g., "Database access only through repositories"}
- {Constraint 3: e.g., "No circular dependencies between packages"}

### 2.2 Technology Constraints
- {Constraint 1: e.g., "Must use Spring Boot 3.x"}
- {Constraint 2: e.g., "Must support Java 17+"}

### 2.3 Performance Constraints
- {Constraint 1: e.g., "API response time < 200ms (p95)"}
- {Constraint 2: e.g., "Support 1000 req/sec"}

### 2.4 Security Constraints
- {Constraint 1: e.g., "All endpoints require authentication"}
- {Constraint 2: e.g., "PII data must be encrypted at rest"}

---

## 3. Component Structure

### 3.1 Package Organization

```
com.tonic.{component}
├── api/          # REST controllers, DTOs
├── domain/       # Business logic, entities
├── infrastructure/ # DB, external services
└── config/       # Configuration classes
```

### 3.2 Class Diagram

{Insert class diagram or link to diagram}

### 3.3 Sequence Diagrams

{Insert sequence diagrams for key flows}

---

## 4. Interface Contracts

### 4.1 REST API

| Endpoint | Method | Request | Response | Description |
|----------|--------|---------|----------|-------------|
| `/api/v1/{resource}` | GET | - | {Resource} | Get resource |
| `/api/v1/{resource}` | POST | {CreateRequest} | {Resource} | Create resource |

### 4.2 Events Published

| Event | Topic | Schema | Description |
|-------|-------|--------|-------------|
| {EventName} | {topic-name} | {EventSchema} | {Description} |

### 4.3 Events Consumed

| Event | Topic | Schema | Description |
|-------|-------|--------|-------------|
| {EventName} | {topic-name} | {EventSchema} | {Description} |

---

## 5. Data Model

### 5.1 Database Schema

```sql
CREATE TABLE {table_name} (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    {column1} VARCHAR(255) NOT NULL,
    {column2} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_{column1} ({column1})
);
```

### 5.2 Entity Relationships

{Describe relationships between entities}

---

## 6. Approved Patterns

This section lists approved coding patterns for this component.

### 6.1 Required Patterns

- [PTN-JAVA-001: Builder Pattern for DTOs](link)
- [PTN-JAVA-015: Repository Pattern for Data Access](link)

### 6.2 Recommended Patterns

- [PTN-JAVA-042: Factory Pattern for Complex Object Creation](link)

### 6.3 Prohibited Patterns

- ❌ Direct database access from controllers
- ❌ Static utility classes for business logic
- ❌ God classes (classes with >500 LOC)

---

## 7. Quality Attributes

### 7.1 Testability
- Unit test coverage > 80%
- Integration test coverage > 60%
- Contract tests for all external APIs

### 7.2 Maintainability
- Max cyclomatic complexity: 10 per method
- Max class size: 500 LOC
- Max method size: 50 LOC

### 7.3 Observability
- Structured logging using SLF4J
- Metrics exported to Prometheus
- Distributed tracing with OpenTelemetry

---

## 8. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | {YYYY-MM-DD} | {Author} | Initial version |
```

### 7.5 AWS Resources

CloudFormation template for AWS infrastructure (optional).

```yaml
# cloudformation/pr-review-infrastructure.yml

AWSTemplateFormatVersion: '2010-09-09'
Description: 'PR Peer Review Orchestration System - AWS Infrastructure'

Parameters:
  Environment:
    Type: String
    Default: production
    AllowedValues:
      - development
      - staging
      - production

Resources:
  # DynamoDB Table: PR Review State
  PRReviewStateTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub 'pr-review-state-${Environment}'
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: pr_number
          AttributeType: N
        - AttributeName: repository
          AttributeType: S
      KeySchema:
        - AttributeName: pr_number
          KeyType: HASH
        - AttributeName: repository
          KeyType: RANGE
      Tags:
        - Key: Project
          Value: SCM-PR-Review
        - Key: Environment
          Value: !Ref Environment

  # DynamoDB Table: Pattern Cache
  PatternCacheTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub 'pattern-cache-${Environment}'
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: pattern_id
          AttributeType: S
      KeySchema:
        - AttributeName: pattern_id
          KeyType: HASH
      TimeToLiveSpecification:
        Enabled: true
        AttributeName: ttl
      Tags:
        - Key: Project
          Value: SCM-PR-Review
        - Key: Environment
          Value: !Ref Environment

  # SQS Queue: Retry Queue
  PRReviewRetryQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub 'pr-review-retry-queue-${Environment}'
      VisibilityTimeout: 300
      MessageRetentionPeriod: 345600
      ReceiveMessageWaitTimeSeconds: 10
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt PRReviewDLQ.Arn
        maxReceiveCount: 3
      Tags:
        - Key: Project
          Value: SCM-PR-Review
        - Key: Environment
          Value: !Ref Environment

  # SQS Queue: Jira Ticket Queue
  JiraTicketQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub 'jira-ticket-queue-${Environment}'
      VisibilityTimeout: 120
      MessageRetentionPeriod: 1209600
      ReceiveMessageWaitTimeSeconds: 10
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt PRReviewDLQ.Arn
        maxReceiveCount: 5
      Tags:
        - Key: Project
          Value: SCM-PR-Review
        - Key: Environment
          Value: !Ref Environment

  # SQS Queue: Dead Letter Queue
  PRReviewDLQ:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub 'pr-review-dlq-${Environment}'
      MessageRetentionPeriod: 1209600
      Tags:
        - Key: Project
          Value: SCM-PR-Review
        - Key: Environment
          Value: !Ref Environment

  # IAM Policy for GitHub Actions
  GitHubActionsPolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      ManagedPolicyName: !Sub 'GitHubActionsPRReviewPolicy-${Environment}'
      Description: 'Policy for GitHub Actions to access PR Review resources'
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Action:
              - dynamodb:GetItem
              - dynamodb:PutItem
              - dynamodb:UpdateItem
              - dynamodb:Query
            Resource:
              - !GetAtt PRReviewStateTable.Arn
              - !GetAtt PatternCacheTable.Arn
          - Effect: Allow
            Action:
              - sqs:SendMessage
              - sqs:ReceiveMessage
              - sqs:DeleteMessage
              - sqs:GetQueueAttributes
            Resource:
              - !GetAtt PRReviewRetryQueue.Arn
              - !GetAtt JiraTicketQueue.Arn
              - !GetAtt PRReviewDLQ.Arn

Outputs:
  PRReviewStateTableName:
    Description: 'DynamoDB table for PR review state'
    Value: !Ref PRReviewStateTable
    Export:
      Name: !Sub '${AWS::StackName}-PRReviewStateTable'

  PatternCacheTableName:
    Description: 'DynamoDB table for pattern cache'
    Value: !Ref PatternCacheTable
    Export:
      Name: !Sub '${AWS::StackName}-PatternCacheTable'

  PRReviewRetryQueueURL:
    Description: 'SQS queue URL for retry operations'
    Value: !Ref PRReviewRetryQueue
    Export:
      Name: !Sub '${AWS::StackName}-RetryQueueURL'

  JiraTicketQueueURL:
    Description: 'SQS queue URL for Jira ticket creation'
    Value: !Ref JiraTicketQueue
    Export:
      Name: !Sub '${AWS::StackName}-JiraTicketQueueURL'

  GitHubActionsPolicyArn:
    Description: 'ARN of IAM policy for GitHub Actions'
    Value: !Ref GitHubActionsPolicy
    Export:
      Name: !Sub '${AWS::StackName}-GitHubActionsPolicyArn'
```

**Deploy CloudFormation Stack**:

```bash
#!/bin/bash
# Deploy AWS infrastructure using CloudFormation

AWS_REGION="us-east-1"
STACK_NAME="pr-review-infrastructure-prod"
ENVIRONMENT="production"

aws cloudformation create-stack \
  --stack-name "$STACK_NAME" \
  --template-body file://cloudformation/pr-review-infrastructure.yml \
  --parameters ParameterKey=Environment,ParameterValue="$ENVIRONMENT" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$AWS_REGION" \
  --tags Key=Project,Value=SCM-PR-Review Key=ManagedBy,Value=CloudFormation

# Wait for stack creation
aws cloudformation wait stack-create-complete \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION"

# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].Outputs'

echo "CloudFormation stack deployed successfully"
```

---

## 8. Post-Deployment

### 8.1 Monitoring Setup

Configure monitoring and alerting for the PR review system.

#### 8.1.1 GitHub Actions Metrics

Monitor workflow execution health.

**Key Metrics**:
- Workflow success rate (target: >95%)
- Workflow execution time (target: <2 min for fast path, <5 min including reviews)
- Agent SLA compliance (target: 100%)
- Failed workflow runs (alert threshold: >5 failures/day)

**Setup GitHub Actions Metrics Dashboard** (external tool required):

```bash
# Example: Export GitHub Actions metrics to CloudWatch

# Install GitHub Actions exporter (if using self-hosted)
# https://github.com/marketplace/actions/github-actions-exporter

# Or use third-party services:
# - Datadog: https://docs.datadoghq.com/integrations/github/
# - New Relic: https://newrelic.com/instant-observability/github-actions
```

#### 8.1.2 CloudWatch Alarms (if using AWS)

```bash
#!/bin/bash
# Create CloudWatch alarms for DynamoDB and SQS

AWS_REGION="us-east-1"

# Alarm: DynamoDB throttled requests
aws cloudwatch put-metric-alarm \
  --alarm-name "PRReview-DynamoDB-ThrottledRequests" \
  --alarm-description "Alert on DynamoDB throttled requests" \
  --metric-name ThrottledRequests \
  --namespace AWS/DynamoDB \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=TableName,Value=pr-review-state \
  --treat-missing-data notBreaching \
  --region "$AWS_REGION"

# Alarm: SQS queue depth (dead letter queue)
aws cloudwatch put-metric-alarm \
  --alarm-name "PRReview-DLQ-MessageCount" \
  --alarm-description "Alert on messages in dead letter queue" \
  --metric-name ApproximateNumberOfMessagesVisible \
  --namespace AWS/SQS \
  --statistic Average \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Value=pr-review-dlq \
  --treat-missing-data notBreaching \
  --region "$AWS_REGION"

echo "CloudWatch alarms created"
```

#### 8.1.3 Jira Metrics

Track Jira ticket creation and resolution.

**Key Metrics**:
- Code violations per week (trend)
- LLD deviations per week (trend)
- Average time to resolve violations (target: <3 days)
- Pattern approval time (target: <4 hours)

**Setup Jira Dashboard**:

1. Navigate to Jira → **Dashboards** → **Create dashboard**
2. Add gadgets:
   - **Created vs Resolved**: Filter by `project = SCM AND labels = peer-review`
   - **Average Age**: Filter by `project = SCM AND labels = code-violation`
   - **Pie Chart**: Issue type distribution
3. Save dashboard as "PR Review Metrics"

### 8.2 Alert Configuration

Configure alerts for critical failures.

#### 8.2.1 Slack Integration (Optional)

Send alerts to Slack channel.

```yaml
# Add to GitHub Actions workflow for critical failures

- name: Notify Slack on Failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    channel-id: 'C01234567'  # Your Slack channel ID
    slack-message: |
      ❌ PR Review Workflow Failed
      Repository: ${{ github.repository }}
      PR: #${{ github.event.pull_request.number }}
      Branch: ${{ github.head_ref }}
      Workflow: ${{ github.workflow }}
      Run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
  env:
    SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
```

#### 8.2.2 Email Alerts

Configure email notifications for critical events.

**GitHub Actions Email Notification**:

```yaml
# Add to workflow for SLA breaches

- name: Send SLA Breach Email
  if: ${{ steps.check_sla.outputs.breached == 'true' }}
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.SMTP_USERNAME }}
    password: ${{ secrets.SMTP_PASSWORD }}
    subject: 'ALERT: PR Review SLA Breach'
    to: architecture-team@your-domain.com
    from: GitHub Actions
    body: |
      PR Review SLA Breach Detected

      Repository: ${{ github.repository }}
      PR: #${{ github.event.pull_request.number }}
      Agent: ${{ steps.check_sla.outputs.agent }}
      Execution Time: ${{ steps.check_sla.outputs.duration }}
      SLA Threshold: ${{ steps.check_sla.outputs.threshold }}
```

### 8.3 Team Onboarding

Prepare documentation and training for development team.

#### 8.3.1 Developer Guide

Create a quick start guide for developers.

**Content Outline**:
1. **What is the PR Review System?**
2. **How does it affect my PRs?**
3. **What are the validation gates?**
4. **What happens if my PR fails validation?**
5. **How do I fix common violations?**
6. **When is human review required?**
7. **FAQ**

**Distribution**:
- Publish to internal wiki/Confluence
- Link in repository README
- Include in new developer onboarding

#### 8.3.2 Architecture Team Training

Train architecture team on reviewing new patterns.

**Training Topics**:
1. How to access peer review requests
2. Pattern review criteria
3. LLD alignment validation
4. Approving/rejecting patterns in GitHub
5. Creating Confluence pattern pages
6. SLA expectations (4-hour review window)

**Schedule Training Session**:
```
Date: [Schedule after deployment]
Duration: 1 hour
Attendees: Architecture team, senior engineers
Format: Live demo + Q&A
```

#### 8.3.3 Create Team Runbook

Document common operational procedures.

**Runbook Sections**:
- System architecture overview
- Troubleshooting common issues
- Emergency procedures
- Escalation paths
- Contact information

**Example Runbook Entry**:

```markdown
## Incident: Workflow Constantly Failing

### Symptoms
- All PRs failing at Code Quality Agent
- Error message: "Unable to connect to Confluence API"

### Diagnosis
1. Check Confluence status: https://status.atlassian.com
2. Verify `CONFLUENCE_API_TOKEN` secret is valid
3. Check network connectivity from GitHub Actions

### Resolution
1. If Confluence is down: Wait for restoration, workflow will retry
2. If token expired: Regenerate token and update secret
3. If network issue: Contact GitHub Support

### Prevention
- Set up Confluence API token expiration monitoring
- Configure retry logic with exponential backoff (already in place)
```

---

## 9. Troubleshooting

### 9.1 Workflow Not Triggering

**Symptom**: PR created but workflow doesn't run.

**Possible Causes**:
1. Workflow file syntax error
2. Workflow file not on default branch
3. PR branch doesn't match trigger pattern

**Resolution**:

```bash
# Check workflow file syntax
gh workflow view peer_review.yml --repo "$REPO_OWNER/$REPO_NAME"

# Verify workflow is on main branch
gh api /repos/$REPO_OWNER/$REPO_NAME/contents/.github/workflows/peer_review.yml | jq '.sha'

# Check workflow triggers
cat .github/workflows/peer_review.yml | grep -A 10 "on:"

# Manually trigger workflow for testing
gh workflow run peer_review.yml \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --ref main \
  --field pr_number=123
```

### 9.2 Agent Execution Failures

**Symptom**: Specific agent consistently fails.

**Common Issues**:

#### Issue: Code Quality Agent Timeout

```bash
# Check Confluence API response time
time curl -u "$CONFLUENCE_EMAIL:$CONFLUENCE_API_TOKEN" \
  "$CONFLUENCE_BASE_URL/rest/api/space/SCM-PATTERNS/content/page"

# If slow (>5 seconds), implement caching or increase timeout
```

#### Issue: Jira Integration Fails

```bash
# Verify Jira credentials
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/3/myself"

# Check Jira project permissions
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/3/project/$JIRA_PROJECT_KEY/role"

# Test issue creation
curl -X POST \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/3/issue" \
  -d '{
    "fields": {
      "project": {"key": "SCM"},
      "issuetype": {"name": "Task"},
      "summary": "Test issue creation"
    }
  }'
```

### 9.3 Secret Configuration Issues

**Symptom**: Workflow fails with authentication errors.

**Resolution**:

```bash
# Verify all required secrets exist
gh secret list --repo "$REPO_OWNER/$REPO_NAME"

# Update secret if needed
gh secret set JIRA_API_TOKEN \
  --repo "$REPO_OWNER/$REPO_NAME" \
  --body "NEW_TOKEN_VALUE"

# Test secret accessibility (workflow logs will show if secret is accessible)
# Secrets are automatically masked in logs for security
```

### 9.4 Performance Issues

**Symptom**: Workflow takes >5 minutes to complete.

**Diagnosis**:

```bash
# Analyze workflow run time breakdown
gh run view <run-id> --repo "$REPO_OWNER/$REPO_NAME" --log | grep "took"

# Identify slowest job
gh api /repos/$REPO_OWNER/$REPO_NAME/actions/runs/<run-id>/timing | jq '.run_started_at, .run_duration_ms'
```

**Optimization Strategies**:
1. Implement Confluence pattern caching (Redis)
2. Parallelize independent agent executions
3. Optimize Confluence queries (use CQL filters)
4. Reduce pattern library scan scope

---

## 10. Appendix

### Appendix A: GitHub Actions Workflow Reference

Complete workflow file location and structure:

**File**: `.github/workflows/peer_review.yml`

**Key Jobs**:
1. `pre-flight-validation`
2. `code-best-practises-agent`
3. `architect-best-practises-agent`
4. `lld-alignment-review-agent` (conditional)
5. `peer-review-documentation-agent` (conditional)
6. `pattern-matching-agent` (post-merge)
7. `jira-integration-agent` (on failure)
8. `final-report` (always runs)

**Documentation**: See `research/workflow_implementation_guide.md` for complete job specifications.

### Appendix B: Agent Specifications

Complete agent specifications are located in:

- `agents/code_best_practises_agent.md`
- `agents/architect_best_practises_agent.md`
- `agents/lld_alignment_review_agent.md`
- `agents/peer_review_documentation_agent.md`
- `agents/pattern_matching_agent.md`
- `agents/jira_integration_agent.md`
- `agents/pr_orchestrator_agent.md`

### Appendix C: Multi-Repository Deployment

For organizations with multiple repositories, use a centralized deployment approach.

**Strategy 1: Shared Workflow (Recommended)**

1. Create a central repository: `tonic-scm/.github`
2. Place workflow in: `.github/workflows/peer_review.yml`
3. Reference from target repositories:

```yaml
# In target repository: .github/workflows/pr_review.yml

name: PR Review
on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main, develop]

jobs:
  call-shared-workflow:
    uses: tonic-scm/.github/.github/workflows/peer_review.yml@main
    secrets: inherit
```

**Strategy 2: Template Repository**

1. Create template repository with workflow
2. Use as template for new repositories
3. Sync updates via automation script:

```bash
#!/bin/bash
# Sync workflow to all repositories

REPOS=(
  "order-service"
  "user-service"
  "payment-service"
  "notification-service"
)

for repo in "${REPOS[@]}"; do
  echo "Updating $repo..."

  gh api \
    --method PUT \
    /repos/tonic-scm/$repo/contents/.github/workflows/peer_review.yml \
    --field message="Update PR review workflow" \
    --field content="$(base64 -w 0 < peer_review.yml)" \
    --field sha="$(gh api /repos/tonic-scm/$repo/contents/.github/workflows/peer_review.yml --jq .sha)"

  sleep 2  # Rate limiting
done
```

### Appendix D: Estimated Costs

Cost estimates for AWS infrastructure (optional components):

**DynamoDB**:
- On-demand pricing
- Estimated: $1-5/month (low volume: <100 PRs/day)
- Estimated: $10-20/month (high volume: 100-500 PRs/day)

**SQS**:
- First 1M requests/month: Free
- Estimated: $0-2/month

**ElastiCache** (if used):
- t4g.micro: ~$12/month
- t4g.small: ~$24/month

**Total Estimated Monthly Cost**: $10-50 (depending on usage)

**Note**: GitHub Actions minutes are included in GitHub plan. Jira and Confluence are typically existing organizational subscriptions.

### Appendix E: Support and Resources

**Internal Support**:
- DevOps Team: devops-support@your-domain.com
- Architecture Team: architecture@your-domain.com
- Slack Channel: #pr-review-system

**External Documentation**:
- GitHub Actions: https://docs.github.com/en/actions
- Jira REST API: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- Confluence REST API: https://developer.atlassian.com/cloud/confluence/rest/v2/
- AWS Documentation: https://docs.aws.amazon.com/

**Project Repository**:
- Main: https://github.com/tonic-scm/tonic-peer-review-agent
- Issues: https://github.com/tonic-scm/tonic-peer-review-agent/issues
- Wiki: https://github.com/tonic-scm/tonic-peer-review-agent/wiki

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-28 | DevOps Team | Initial deployment guide |

---

**End of Deployment Guide**
