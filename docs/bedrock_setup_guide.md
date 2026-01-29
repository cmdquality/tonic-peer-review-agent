# AWS Bedrock Setup Guide for PR Peer Review

This guide explains how to configure AWS Bedrock with Claude models for the PR Peer Review workflow.

---

## Overview

The PR Peer Review system uses **AWS Bedrock** to run Claude AI agents in GitHub Actions. This provides:
- **No API keys to manage** - Uses AWS OIDC authentication
- **Cost control** - Pay-per-use with AWS billing
- **Enterprise compliance** - Data stays in your AWS account
- **Model flexibility** - Switch between Haiku, Sonnet, and Opus

---

## Prerequisites

1. **AWS Account** with Bedrock access
2. **GitHub Repository** with Actions enabled
3. **AWS CLI** installed locally (for setup)

---

## Step 1: Enable Bedrock Model Access

1. Go to **AWS Console** → **Amazon Bedrock** → **Model access**
2. Click **Manage model access**
3. Enable the following Claude models:
   - `anthropic.claude-3-haiku-20240307-v1:0` (fast, cheap)
   - `anthropic.claude-3-5-sonnet-20241022-v2:0` (balanced)
   - `anthropic.claude-opus-4-20250514-v1:0` (most capable, optional)
4. Click **Save changes**

> **Note**: Model access requests are usually approved instantly.

---

## Step 2: Create OIDC Identity Provider

This allows GitHub Actions to authenticate with AWS without long-lived credentials.

### Using AWS CLI:

```bash
# Create OIDC provider
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### Using AWS Console:

1. Go to **IAM** → **Identity providers** → **Add provider**
2. Select **OpenID Connect**
3. Enter:
   - **Provider URL**: `https://token.actions.githubusercontent.com`
   - **Audience**: `sts.amazonaws.com`
4. Click **Add provider**

---

## Step 3: Create IAM Role for GitHub Actions

### Create Trust Policy (`trust-policy.json`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
        },
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
```

Replace:
- `YOUR_ACCOUNT_ID`: Your AWS account ID (e.g., `123456789012`)
- `YOUR_ORG/YOUR_REPO`: Your GitHub repository (e.g., `mycompany/tonic-peer-review-agent`)

### Create Bedrock Permission Policy (`bedrock-policy.json`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
      ]
    },
    {
      "Sid": "BedrockList",
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel"
      ],
      "Resource": "*"
    }
  ]
}
```

### Create Role Using AWS CLI:

```bash
# Create the role
aws iam create-role \
  --role-name github-actions-bedrock-role \
  --assume-role-policy-document file://trust-policy.json

# Create the policy
aws iam create-policy \
  --policy-name bedrock-invoke-policy \
  --policy-document file://bedrock-policy.json

# Attach policy to role
aws iam attach-role-policy \
  --role-name github-actions-bedrock-role \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/bedrock-invoke-policy
```

### Note the Role ARN:

```bash
aws iam get-role --role-name github-actions-bedrock-role --query 'Role.Arn' --output text
# Output: arn:aws:iam::123456789012:role/github-actions-bedrock-role
```

---

## Step 4: Configure GitHub Secrets

Add the following secret to your GitHub repository:

| Secret Name | Value |
|-------------|-------|
| `AWS_BEDROCK_ROLE_ARN` | `arn:aws:iam::123456789012:role/github-actions-bedrock-role` |

### How to add secrets:

1. Go to your repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Enter name: `AWS_BEDROCK_ROLE_ARN`
4. Enter value: Your IAM role ARN
5. Click **Add secret**

---

## Step 5: Deploy the Workflow

Copy the workflow file to your repository:

```bash
# The workflow is already at:
# .github/workflows/peer_review_bedrock.yml

# The Python agent runner is at:
# .github/scripts/bedrock_agent_runner.py
# .github/scripts/requirements.txt
```

---

## Step 6: Test the Integration

### Test locally (optional):

```bash
# Configure AWS credentials
aws configure

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?contains(modelId, `claude`)].modelId'

# Test the agent runner
cd tonic-peer-review-agent
python .github/scripts/bedrock_agent_runner.py --agent code_quality --pr 1
```

### Test via GitHub Actions:

1. Create a test PR with code changes
2. Watch the workflow run in **Actions** tab
3. Check the PR comments for results

---

## Configuration Options

### Model Selection

You can configure which Claude model to use per agent:

```yaml
# In .github/workflows/peer_review_bedrock.yml
env:
  CODE_QUALITY_MODEL: haiku      # Fast, cheap ($0.25/1M tokens)
  ARCHITECT_MODEL: sonnet        # Balanced ($3/1M tokens)
  LLD_MODEL: sonnet              # Detailed analysis
```

### Available Models

| Model | Best For | Speed | Cost |
|-------|----------|-------|------|
| `haiku` | Simple reviews, high volume | Fastest | Lowest |
| `sonnet` | Most PR reviews | Fast | Medium |
| `opus` | Complex architectural analysis | Slower | Highest |

### Region Configuration

```yaml
env:
  AWS_REGION: us-east-1  # Change to your preferred region
```

Best regions for Bedrock Claude:
- `us-east-1` (N. Virginia) - Most models available
- `us-west-2` (Oregon)
- `eu-central-1` (Frankfurt)
- `ap-southeast-1` (Singapore)

---

## Cost Estimation

| PR Size | Model | Tokens | Estimated Cost |
|---------|-------|--------|----------------|
| Small (<10 files) | Haiku | ~3K | $0.001 |
| Medium (10-30 files) | Haiku | ~10K | $0.003 |
| Large (>30 files) | Sonnet | ~50K | $0.20 |

**Monthly estimate (100 PRs/month)**: $5-20

---

## Troubleshooting

### "Access Denied" Error

**Cause**: IAM role doesn't have Bedrock permissions

**Fix**:
```bash
# Verify policy is attached
aws iam list-attached-role-policies --role-name github-actions-bedrock-role
```

### "Model not found" Error

**Cause**: Model access not enabled in Bedrock

**Fix**: Go to Bedrock console → Model access → Enable Claude models

### "OIDC token failed" Error

**Cause**: Trust policy doesn't match repository

**Fix**: Check the `sub` condition in trust policy matches your repo exactly:
```json
"token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
```

### Rate Limiting (ThrottlingException)

**Cause**: Too many requests to Bedrock

**Fix**:
1. The agent runner has built-in retry with exponential backoff
2. For high-volume repos, request a quota increase in AWS

---

## Security Best Practices

1. **Use OIDC** - Never store AWS access keys in GitHub secrets
2. **Restrict trust policy** - Only allow specific repositories
3. **Least privilege** - Only grant `bedrock:InvokeModel` permission
4. **Monitor usage** - Set up CloudWatch alarms for unusual activity
5. **Enable CloudTrail** - Log all Bedrock API calls

---

## Next Steps

1. Review the [complete Bedrock research guide](../.claude/staging/bedrock-research/bedrock_claude_github_actions_guide.md)
2. Customize agent prompts in `agents/` directory
3. Adjust model selection based on your needs
4. Set up CloudWatch monitoring for costs

---

**Questions?** Check the [troubleshooting section](#troubleshooting) or open an issue.
