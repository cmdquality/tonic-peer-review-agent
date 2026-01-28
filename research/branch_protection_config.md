# Branch Protection Configuration Guide

**Created**: 2026-01-28
**Project**: Tonic Configuration Management Platform - PR Peer Review System
**Purpose**: Configure GitHub branch protection rules to enforce automated peer review workflow

---

## Table of Contents

1. [Overview](#overview)
2. [Required Status Checks](#required-status-checks)
3. [Branch Protection Settings](#branch-protection-settings)
4. [Configuration Methods](#configuration-methods)
5. [Merge Queue Configuration](#merge-queue-configuration)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Maintenance and Updates](#maintenance-and-updates)

---

## 1. Overview

Branch protection rules enforce quality gates for Pull Requests before they can be merged. This document provides configuration guidance for the multi-agent PR peer review system that validates code quality, architectural patterns, LLD compliance, and ensures proper peer review approval.

### Protection Goals

- **Prevent direct pushes** to protected branches (main, develop, release/*)
- **Require all status checks to pass** before merge
- **Enforce automated validation** through GitHub Actions workflows
- **Maintain audit trail** of all merge decisions
- **Prevent bypasses** of the peer review workflow

### Branch Strategy

| Branch Pattern | Protection Level | Purpose |
|---------------|------------------|---------|
| `main` | Maximum | Production-ready code |
| `develop` | High | Development integration |
| `release/*` | High | Release candidates |
| `feature/*` | None | Feature development |
| `hotfix/*` | Medium | Emergency fixes |

---

## 2. Required Status Checks

### 2.1 Blocking Status Checks (Must Pass)

These status checks MUST pass before PR can be merged. If any fail, merge is blocked.

| Status Check Name | Job Name | Description | Typical Duration | Blocking Level |
|------------------|----------|-------------|------------------|----------------|
| `pr-orchestrator / workflow-validation` | `pr-orchestrator-workflow` | Complete workflow orchestration and merge decision | 30s - 4.5h | **BLOCKING** |
| `code-quality / code-best-practises` | `code-best-practises-agent` | Code quality validation (naming, documentation, patterns) | 30s | **BLOCKING** |
| `architecture / architect-best-practises` | `architect-best-practises-agent` | Architecture pattern detection and validation | 10s | **BLOCKING** |
| `ci-build / build-and-test` | `build-and-test` | Compile, unit tests, integration tests | 2-5 min | **BLOCKING** |
| `ci-security / security-scan` | `security-scan` | Security vulnerability scanning (SAST, dependency check) | 1-2 min | **BLOCKING** |

**Total Blocking Checks**: 5 required status checks

### 2.2 Conditional Status Checks (Context-Dependent)

These checks only run when specific conditions are met (e.g., new architectural pattern detected).

| Status Check Name | Job Name | Condition | Blocking Level |
|------------------|----------|-----------|----------------|
| `lld-alignment / lld-review` | `lld-alignment-review-agent` | Only runs if new pattern detected | **BLOCKING** (if executed) |
| `peer-review / pattern-review` | `peer-review-documentation-agent` | Only runs if new pattern is LLD-compliant | **BLOCKING** (if executed) |
| `pattern-storage / store-pattern` | `pattern-matching-agent-store` | Only runs after human approval of new pattern | **INFORMATIONAL** |

**Note**: Conditional checks are not required in branch protection rules because they only execute in specific scenarios. The PR Orchestrator workflow handles routing and ensures these checks pass when applicable.

### 2.3 Informational Status Checks (Non-Blocking)

These checks provide useful information but do not block merge.

| Status Check Name | Job Name | Description | Purpose |
|------------------|----------|-------------|---------|
| `reporting / jira-integration` | `jira-integration-agent` | Jira ticket creation for tracking failures | Audit trail |
| `deployment / deployment-hooks` | `github-actions-deployment` | Deployment pipeline trigger | Post-merge activity |
| `metrics / workflow-metrics` | `publish-metrics` | Publish workflow execution metrics to CloudWatch | Monitoring |

**Total Non-Blocking Checks**: 3 informational checks

### 2.4 Status Check Configuration Matrix

```yaml
# GitHub Actions Workflow - Status Check Names
# These names appear in GitHub as status checks

name: PR Validation Workflow

on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches:
      - main
      - develop
      - 'release/**'

jobs:
  pr-orchestrator-workflow:
    name: pr-orchestrator / workflow-validation
    runs-on: ubuntu-latest
    steps:
      # Orchestrator execution logic

  code-best-practises-agent:
    name: code-quality / code-best-practises
    runs-on: ubuntu-latest
    steps:
      # Code quality validation logic

  architect-best-practises-agent:
    name: architecture / architect-best-practises
    runs-on: ubuntu-latest
    steps:
      # Architecture validation logic

  build-and-test:
    name: ci-build / build-and-test
    runs-on: ubuntu-latest
    steps:
      # Build and test logic

  security-scan:
    name: ci-security / security-scan
    runs-on: ubuntu-latest
    steps:
      # Security scanning logic
```

---

## 3. Branch Protection Settings

### 3.1 Main Branch Protection (Maximum Protection)

Apply these settings to `main` branch:

#### Require Pull Request Reviews
- **Require approvals before merging**: Disabled (handled by orchestrator agent)
  - Rationale: PR Orchestrator Agent makes final merge decision based on all agent validations
  - Human reviews are required only for new architectural patterns (4-hour SLA)
- **Dismiss stale pull request approvals when new commits are pushed**: Enabled
- **Require review from Code Owners**: Optional (if CODEOWNERS file exists)

#### Require Status Checks to Pass
- **Require branches to be up to date before merging**: Enabled
- **Required status checks**: (Must pass before merge)
  - `pr-orchestrator / workflow-validation`
  - `code-quality / code-best-practises`
  - `architecture / architect-best-practises`
  - `ci-build / build-and-test`
  - `ci-security / security-scan`

#### Require Conversation Resolution
- **Require conversation resolution before merging**: Enabled
  - All PR comments/threads must be resolved

#### Require Signed Commits
- **Require signed commits**: Optional (based on organization policy)
  - Recommended: Enabled for maximum security

#### Require Linear History
- **Require linear history**: Enabled
  - Enforces squash merge or rebase merge (no merge commits)

#### Require Deployments to Succeed
- **Require deployments to succeed before merging**: Disabled
  - Deployment happens after merge

#### Lock Branch (Prevent All Changes)
- **Lock branch**: Disabled (development active)

#### Do Not Allow Bypassing
- **Do not allow bypassing the above settings**: Enabled
  - Administrators cannot bypass protections
  - **Critical**: Prevents manual merges that bypass workflow validation

#### Restrict Pushes
- **Restrict who can push to matching branches**: Enabled
  - Only allow deployments: Disabled
  - Restrict pushes to specific people, teams, or apps:
    - GitHub Actions bot (for automated merges after approval)
    - Release managers (for hotfix scenarios only)

#### Allow Force Pushes
- **Allow force pushes**: Disabled
  - Prevents rewriting history on protected branches

#### Allow Deletions
- **Allow deletions**: Disabled
  - Prevents accidental branch deletion

### 3.2 Develop Branch Protection (High Protection)

Apply these settings to `develop` branch:

Same as Main Branch with these modifications:
- **Require branches to be up to date before merging**: Optional (Enabled for consistency, Disabled for faster merges)
- **Do not allow bypassing the above settings**: Disabled (administrators can bypass for emergency fixes)

### 3.3 Release Branch Protection (High Protection)

Apply these settings to `release/*` branches:

Same as Main Branch with these modifications:
- **Require branches to be up to date before merging**: Enabled
- **Do not allow bypassing the above settings**: Disabled (release managers can bypass with approval)
- **Restrict Pushes**: Add release managers team

### 3.4 Hotfix Branch Protection (Medium Protection)

Apply these settings to `hotfix/*` branches:

Minimal protection for emergency fixes:
- **Require Pull Request Reviews**: Enabled (1 approval required)
- **Require Status Checks to Pass**: Enabled (only build and security checks)
- **Require branches to be up to date**: Disabled (fast emergency fixes)
- **Do not allow bypassing**: Disabled (can be bypassed with justification)

---

## 4. Configuration Methods

### 4.1 GitHub UI Configuration

#### Step-by-Step Guide

**1. Navigate to Repository Settings**
- Go to your repository: `https://github.com/tonic-scm/<repository-name>`
- Click **Settings** tab
- Click **Branches** in left sidebar

**2. Add Branch Protection Rule**
- Click **Add rule** button
- Enter branch name pattern: `main`

**3. Configure Protection Settings**

**Branch name pattern**: `main`

Check the following boxes:

- [x] **Require a pull request before merging**
  - [ ] Require approvals: 0 (handled by orchestrator)
  - [x] Dismiss stale pull request approvals when new commits are pushed
  - [ ] Require review from Code Owners (optional)
  - [x] Require approval of the most recent reviewable push

- [x] **Require status checks to pass before merging**
  - [x] Require branches to be up to date before merging
  - Search and select required status checks:
    - [x] `pr-orchestrator / workflow-validation`
    - [x] `code-quality / code-best-practises`
    - [x] `architecture / architect-best-practises`
    - [x] `ci-build / build-and-test`
    - [x] `ci-security / security-scan`

- [x] **Require conversation resolution before merging**

- [ ] **Require signed commits** (optional)

- [x] **Require linear history**

- [ ] **Require deployments to succeed before merging**

- [ ] **Lock branch**

- [x] **Do not allow bypassing the above settings**
  - [x] Apply to administrators

- [x] **Restrict who can push to matching branches**
  - Add: `github-actions[bot]`
  - Add: `release-managers` (team)

- [ ] **Allow force pushes**
  - [ ] Everyone / Specify who can force push

- [ ] **Allow deletions**

**4. Save Changes**
- Click **Create** button
- Branch protection rule is now active

**5. Repeat for Other Branches**
- Create rule for `develop` branch
- Create rule for `release/*` branch pattern
- Create rule for `hotfix/*` branch pattern (with modified settings)

---

### 4.2 GitHub CLI Configuration

#### Prerequisites
```bash
# Install GitHub CLI
# macOS: brew install gh
# Windows: choco install gh
# Linux: See https://cli.github.com/manual/installation

# Authenticate
gh auth login
```

#### Configure Main Branch Protection

```bash
#!/bin/bash

# Configuration variables
REPO_OWNER="tonic-scm"
REPO_NAME="order-service"
BRANCH="main"

# Create branch protection rule
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
      },
      {
        "context": "ci-build / build-and-test",
        "app_id": -1
      },
      {
        "context": "ci-security / security-scan",
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
  "restrictions": {
    "users": [],
    "teams": ["release-managers"],
    "apps": ["github-actions"]
  }
}
EOF

echo "Branch protection configured for $BRANCH"
```

#### Configure Develop Branch Protection

```bash
#!/bin/bash

REPO_OWNER="tonic-scm"
REPO_NAME="order-service"
BRANCH="develop"

gh api \
  --method PUT \
  /repos/$REPO_OWNER/$REPO_NAME/branches/$BRANCH/protection \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "checks": [
      {
        "context": "pr-orchestrator / workflow-validation"
      },
      {
        "context": "code-quality / code-best-practises"
      },
      {
        "context": "architecture / architect-best-practises"
      },
      {
        "context": "ci-build / build-and-test"
      },
      {
        "context": "ci-security / security-scan"
      }
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0
  },
  "required_conversation_resolution": true,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "restrictions": {
    "users": [],
    "teams": ["release-managers", "senior-developers"],
    "apps": ["github-actions"]
  }
}
EOF

echo "Branch protection configured for $BRANCH"
```

#### Verification

```bash
# Verify branch protection rules
gh api /repos/$REPO_OWNER/$REPO_NAME/branches/$BRANCH/protection | jq '.'

# List all protected branches
gh api /repos/$REPO_OWNER/$REPO_NAME/branches --paginate | jq '.[] | select(.protected == true) | {name: .name, protected: .protected}'
```

---

### 4.3 GitHub API Configuration (REST API)

#### Using cURL

```bash
#!/bin/bash

# Configuration
GITHUB_TOKEN="ghp_YourPersonalAccessToken"
REPO_OWNER="tonic-scm"
REPO_NAME="order-service"
BRANCH="main"

# API endpoint
API_URL="https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/branches/$BRANCH/protection"

# Create branch protection
curl -X PUT "$API_URL" \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -d '{
    "required_status_checks": {
      "strict": true,
      "checks": [
        {"context": "pr-orchestrator / workflow-validation"},
        {"context": "code-quality / code-best-practises"},
        {"context": "architecture / architect-best-practises"},
        {"context": "ci-build / build-and-test"},
        {"context": "ci-security / security-scan"}
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
    "required_signatures": false,
    "lock_branch": false,
    "restrictions": {
      "users": [],
      "teams": ["release-managers"],
      "apps": ["github-actions"]
    }
  }'
```

#### Using Python Script

```python
#!/usr/bin/env python3
"""
Configure GitHub branch protection rules via REST API
"""

import os
import json
import requests
from typing import List, Dict

class GitHubBranchProtection:
    def __init__(self, token: str, owner: str, repo: str):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.api_base = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def configure_main_branch_protection(self) -> Dict:
        """Configure maximum protection for main branch"""
        protection_config = {
            "required_status_checks": {
                "strict": True,
                "checks": [
                    {"context": "pr-orchestrator / workflow-validation"},
                    {"context": "code-quality / code-best-practises"},
                    {"context": "architecture / architect-best-practises"},
                    {"context": "ci-build / build-and-test"},
                    {"context": "ci-security / security-scan"}
                ]
            },
            "enforce_admins": True,
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": False,
                "required_approving_review_count": 0,
                "require_last_push_approval": True
            },
            "required_conversation_resolution": True,
            "required_linear_history": True,
            "allow_force_pushes": False,
            "allow_deletions": False,
            "required_signatures": False,
            "lock_branch": False,
            "restrictions": {
                "users": [],
                "teams": ["release-managers"],
                "apps": ["github-actions"]
            }
        }

        return self._apply_protection("main", protection_config)

    def configure_develop_branch_protection(self) -> Dict:
        """Configure high protection for develop branch"""
        protection_config = {
            "required_status_checks": {
                "strict": True,
                "checks": [
                    {"context": "pr-orchestrator / workflow-validation"},
                    {"context": "code-quality / code-best-practises"},
                    {"context": "architecture / architect-best-practises"},
                    {"context": "ci-build / build-and-test"},
                    {"context": "ci-security / security-scan"}
                ]
            },
            "enforce_admins": False,
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": False,
                "required_approving_review_count": 0
            },
            "required_conversation_resolution": True,
            "required_linear_history": True,
            "allow_force_pushes": False,
            "allow_deletions": False,
            "restrictions": {
                "users": [],
                "teams": ["release-managers", "senior-developers"],
                "apps": ["github-actions"]
            }
        }

        return self._apply_protection("develop", protection_config)

    def _apply_protection(self, branch: str, config: Dict) -> Dict:
        """Apply branch protection configuration"""
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/branches/{branch}/protection"

        response = requests.put(url, headers=self.headers, json=config)

        if response.status_code in [200, 201]:
            print(f"✅ Branch protection configured for '{branch}'")
            return response.json()
        else:
            print(f"❌ Failed to configure branch protection for '{branch}'")
            print(f"Status: {response.status_code}")
            print(f"Error: {response.text}")
            raise Exception(f"API request failed: {response.status_code}")

    def verify_protection(self, branch: str) -> Dict:
        """Verify branch protection settings"""
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/branches/{branch}/protection"

        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to verify protection: {response.status_code}")

def main():
    # Configuration from environment variables
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    REPO_OWNER = os.getenv("REPO_OWNER", "tonic-scm")
    REPO_NAME = os.getenv("REPO_NAME", "order-service")

    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    # Initialize protection manager
    protection = GitHubBranchProtection(GITHUB_TOKEN, REPO_OWNER, REPO_NAME)

    # Configure main branch
    print(f"Configuring branch protection for {REPO_OWNER}/{REPO_NAME}...")

    protection.configure_main_branch_protection()
    protection.configure_develop_branch_protection()

    # Verify configuration
    print("\nVerifying configuration...")
    main_protection = protection.verify_protection("main")
    print(f"Main branch protection: {json.dumps(main_protection, indent=2)}")

if __name__ == "__main__":
    main()
```

#### Running the Script

```bash
# Set environment variables
export GITHUB_TOKEN="ghp_YourPersonalAccessToken"
export REPO_OWNER="tonic-scm"
export REPO_NAME="order-service"

# Run script
python configure_branch_protection.py
```

---

### 4.4 Terraform Configuration (Infrastructure as Code)

```hcl
# terraform/github_branch_protection.tf

terraform {
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 5.0"
    }
  }
}

provider "github" {
  token = var.github_token
  owner = var.github_org
}

variable "github_token" {
  description = "GitHub Personal Access Token"
  type        = string
  sensitive   = true
}

variable "github_org" {
  description = "GitHub Organization"
  type        = string
  default     = "tonic-scm"
}

variable "repository_name" {
  description = "Repository name"
  type        = string
  default     = "order-service"
}

# Main branch protection
resource "github_branch_protection" "main" {
  repository_id = data.github_repository.repo.node_id
  pattern       = "main"

  required_status_checks {
    strict = true
    contexts = [
      "pr-orchestrator / workflow-validation",
      "code-quality / code-best-practises",
      "architecture / architect-best-practises",
      "ci-build / build-and-test",
      "ci-security / security-scan"
    ]
  }

  required_pull_request_reviews {
    dismiss_stale_reviews           = true
    require_code_owner_reviews      = false
    required_approving_review_count = 0
    require_last_push_approval      = true
  }

  require_conversation_resolution = true
  require_signed_commits          = false
  required_linear_history         = true
  enforce_admins                  = true
  allow_force_pushes              = false
  allow_deletions                 = false
  lock_branch                     = false

  restrict_pushes {
    blocks_creations = false
    push_allowances = [
      data.github_team.release_managers.node_id
    ]
  }
}

# Develop branch protection
resource "github_branch_protection" "develop" {
  repository_id = data.github_repository.repo.node_id
  pattern       = "develop"

  required_status_checks {
    strict = true
    contexts = [
      "pr-orchestrator / workflow-validation",
      "code-quality / code-best-practises",
      "architecture / architect-best-practises",
      "ci-build / build-and-test",
      "ci-security / security-scan"
    ]
  }

  required_pull_request_reviews {
    dismiss_stale_reviews           = true
    require_code_owner_reviews      = false
    required_approving_review_count = 0
  }

  require_conversation_resolution = true
  required_linear_history         = true
  enforce_admins                  = false
  allow_force_pushes              = false
  allow_deletions                 = false

  restrict_pushes {
    push_allowances = [
      data.github_team.release_managers.node_id,
      data.github_team.senior_developers.node_id
    ]
  }
}

# Release branch protection (pattern)
resource "github_branch_protection" "release" {
  repository_id = data.github_repository.repo.node_id
  pattern       = "release/*"

  required_status_checks {
    strict = true
    contexts = [
      "pr-orchestrator / workflow-validation",
      "code-quality / code-best-practises",
      "architecture / architect-best-practises",
      "ci-build / build-and-test",
      "ci-security / security-scan"
    ]
  }

  required_pull_request_reviews {
    dismiss_stale_reviews           = true
    required_approving_review_count = 0
  }

  require_conversation_resolution = true
  required_linear_history         = true
  enforce_admins                  = false
  allow_force_pushes              = false
  allow_deletions                 = false

  restrict_pushes {
    push_allowances = [
      data.github_team.release_managers.node_id
    ]
  }
}

# Data sources
data "github_repository" "repo" {
  name = var.repository_name
}

data "github_team" "release_managers" {
  slug = "release-managers"
}

data "github_team" "senior_developers" {
  slug = "senior-developers"
}

# Outputs
output "main_branch_protection_id" {
  value       = github_branch_protection.main.id
  description = "Main branch protection rule ID"
}

output "develop_branch_protection_id" {
  value       = github_branch_protection.develop.id
  description = "Develop branch protection rule ID"
}
```

#### Apply Terraform Configuration

```bash
# Initialize Terraform
terraform init

# Plan changes
terraform plan \
  -var="github_token=$GITHUB_TOKEN" \
  -var="repository_name=order-service"

# Apply configuration
terraform apply \
  -var="github_token=$GITHUB_TOKEN" \
  -var="repository_name=order-service"

# Verify
terraform show
```

---

## 5. Merge Queue Configuration

### 5.1 When to Use Merge Queues

Merge queues are beneficial for:
- **High-velocity teams**: Multiple PRs ready to merge simultaneously
- **Long CI/CD pipelines**: Build and test take > 5 minutes
- **Race conditions**: Prevent "last commit wins" merge conflicts
- **Batch testing**: Test multiple PRs together before merge

### 5.2 Merge Queue vs. Branch Protection

| Feature | Branch Protection | Merge Queue |
|---------|------------------|-------------|
| Status checks | Required before merge | Required + batched testing |
| Merge conflicts | Manual resolution | Automatic retry |
| Throughput | Linear (one PR at a time) | Parallel (batch merging) |
| CI time | Per PR | Amortized across batch |
| Complexity | Simple | Complex |

### 5.3 Should You Use Merge Queues?

**Recommendation for Tonic Platform**: **Not Initially**

**Reasons**:
1. **Workflow Complexity**: PR Orchestrator Agent already handles complex routing and validation
2. **Human Review SLA**: 4-hour human review for new patterns creates natural batching
3. **Fast Path**: Most PRs (no new patterns) complete in < 1 minute
4. **Low Volume**: Early adoption phase, not high PR volume yet

**When to Reconsider**:
- PR volume > 50 per day per repository
- Frequent merge conflicts on main branch
- CI/CD pipeline time > 10 minutes
- Team size > 20 active developers per repository

### 5.4 Merge Queue Configuration (Future Use)

If merge queue becomes necessary:

#### Enable via GitHub UI

1. Navigate to **Settings > General > Pull Requests**
2. Scroll to **Merge queue**
3. Check **Enable merge queue**
4. Configure settings:
   - **Minimum PRs to merge**: 1 (don't batch)
   - **Maximum PRs to merge**: 5 (reasonable batch size)
   - **Merge method**: Squash
   - **Status checks timeout**: 30 minutes

#### Enable via GitHub CLI

```bash
gh api \
  --method PATCH \
  /repos/$REPO_OWNER/$REPO_NAME \
  --field merge_commit_message="PR_TITLE" \
  --field merge_commit_title="MERGE_MESSAGE" \
  --field squash_merge_commit_message="PR_BODY" \
  --field squash_merge_commit_title="PR_TITLE" \
  --field use_squash_pr_title_as_default=true
```

#### Branch Protection with Merge Queue

```json
{
  "required_status_checks": {
    "strict": true,
    "checks": [...]
  },
  "merge_queue": {
    "enabled": true,
    "method": "SQUASH",
    "minimum_entries_to_merge": 1,
    "maximum_entries_to_merge": 5,
    "merge_commit_message_template": "PR_BODY",
    "status_check_timeout_minutes": 30
  }
}
```

---

## 6. Troubleshooting Guide

### 6.1 Common Issues and Solutions

#### Issue 1: Status Check Not Appearing in Branch Protection

**Symptoms**:
- Status check name doesn't appear when searching in branch protection settings
- "No status checks found matching" message

**Causes**:
1. GitHub Actions workflow has not run yet
2. Job name in workflow doesn't match expected status check name
3. Branch name mismatch (workflow triggers on wrong branches)

**Solutions**:

1. **Trigger workflow first**: Open a test PR to trigger GitHub Actions workflow
2. **Verify job names**:
   ```yaml
   # In .github/workflows/pr-validation.yml
   jobs:
     code-best-practises-agent:
       name: code-quality / code-best-practises  # This becomes status check name
   ```
3. **Check workflow triggers**:
   ```yaml
   on:
     pull_request:
       branches:
         - main  # Ensure this matches your protected branch
   ```
4. **Wait 5-10 minutes** after first workflow run for GitHub to index status check

#### Issue 2: PR Blocked Despite All Checks Passing

**Symptoms**:
- All status checks show green checkmarks
- "Merge" button is disabled
- Message: "Required status checks have not passed"

**Causes**:
1. "Require branches to be up to date" enabled, but branch is behind base
2. Stale status checks (from old commits)
3. Additional required checks configured but not visible

**Solutions**:

1. **Update branch**:
   ```bash
   git fetch origin
   git merge origin/main
   git push
   ```
2. **Check for stale checks**:
   - GitHub UI: View all status checks (expand "Show all checks")
   - Look for checks with warning icon (stale)
3. **Verify required checks**:
   ```bash
   # List required status checks
   gh api /repos/$REPO_OWNER/$REPO_NAME/branches/main/protection | jq '.required_status_checks.checks'
   ```

#### Issue 3: PR Merged Without Status Checks

**Symptoms**:
- PR merged with failing status checks
- Branch protection rules appear ineffective

**Causes**:
1. Administrator bypass enabled (`enforce_admins: false`)
2. Status check names don't match exactly
3. Branch protection rule doesn't apply to branch (pattern mismatch)

**Solutions**:

1. **Audit merge**:
   ```bash
   # Check who merged and how
   gh pr view $PR_NUMBER --json mergedBy,mergeCommit,mergedAt
   ```
2. **Enable enforce_admins**:
   ```bash
   gh api --method PUT /repos/$REPO_OWNER/$REPO_NAME/branches/main/protection \
     --field enforce_admins=true
   ```
3. **Verify branch pattern**:
   - Branch protection pattern: `main`
   - PR target branch: `main`
   - Ensure exact match (case-sensitive)

#### Issue 4: Conditional Checks Blocking Merge

**Symptoms**:
- PR blocked because LLD Review or Peer Review check is "pending"
- These checks never run for this PR type (no new pattern)

**Cause**:
- Conditional checks (LLD Review, Peer Review) incorrectly added to required status checks

**Solution**:
- **Remove conditional checks** from branch protection required status checks
- Only include always-required checks:
  - `pr-orchestrator / workflow-validation`
  - `code-quality / code-best-practises`
  - `architecture / architect-best-practises`
  - `ci-build / build-and-test`
  - `ci-security / security-scan`

#### Issue 5: Workflow Orchestrator Fails to Post Status

**Symptoms**:
- GitHub Actions workflow completes successfully
- Status check never appears on PR

**Causes**:
1. Missing GitHub token permissions
2. Wrong token used (GITHUB_TOKEN vs PAT)
3. Status check API call failed

**Solutions**:

1. **Check workflow permissions**:
   ```yaml
   # In .github/workflows/pr-validation.yml
   permissions:
     statuses: write
     pull-requests: write
     checks: write
   ```
2. **Verify token usage**:
   ```yaml
   - name: Post status check
     env:
       GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
     run: |
       # Use GITHUB_TOKEN for status check API calls
   ```
3. **Debug status check API**:
   ```bash
   # Test status check creation
   gh api \
     --method POST \
     /repos/$REPO_OWNER/$REPO_NAME/statuses/$COMMIT_SHA \
     --field state="success" \
     --field context="test-check" \
     --field description="Test status"
   ```

#### Issue 6: High Volume Merge Delays

**Symptoms**:
- PRs waiting in queue for long time
- Multiple PRs ready to merge but only one merges at a time

**Cause**:
- "Require branches to be up to date" forces serial merging

**Solutions**:

1. **Short term**: Disable "require branches to be up to date" for develop branch
2. **Long term**: Implement merge queue (see Section 5)
3. **Alternative**: Optimize CI/CD pipeline to reduce build time

### 6.2 Diagnostic Commands

```bash
#!/bin/bash
# Diagnostic script for branch protection troubleshooting

REPO_OWNER="tonic-scm"
REPO_NAME="order-service"
BRANCH="main"
PR_NUMBER=123

echo "=== Branch Protection Diagnostics ==="

# 1. Check branch protection rules
echo -e "\n1. Branch Protection Rules:"
gh api /repos/$REPO_OWNER/$REPO_NAME/branches/$BRANCH/protection | jq '{
  required_status_checks: .required_status_checks.checks[].context,
  enforce_admins: .enforce_admins.enabled,
  required_reviews: .required_pull_request_reviews.required_approving_review_count
}'

# 2. Check PR status checks
echo -e "\n2. PR Status Checks:"
gh pr view $PR_NUMBER --json statusCheckRollup | jq '.statusCheckRollup[] | {
  name: .name,
  status: .status,
  conclusion: .conclusion
}'

# 3. Check PR merge status
echo -e "\n3. PR Merge Status:"
gh pr view $PR_NUMBER --json mergeable,mergeStateStatus | jq '.'

# 4. Check recent workflow runs
echo -e "\n4. Recent Workflow Runs:"
gh run list --repo $REPO_OWNER/$REPO_NAME --limit 5 --json name,status,conclusion,headBranch | jq '.'

# 5. Check branch comparison
echo -e "\n5. Branch Comparison:"
gh api /repos/$REPO_OWNER/$REPO_NAME/compare/$BRANCH...$(gh pr view $PR_NUMBER --json headRefName -q .headRefName) | jq '{
  ahead_by: .ahead_by,
  behind_by: .behind_by,
  status: .status
}'

echo -e "\n=== Diagnostics Complete ==="
```

### 6.3 Emergency Bypass Procedure

**When to Use**: Critical production hotfix required immediately, but workflow blocked

**Approval Required**: VP Engineering or CTO

**Procedure**:

1. **Document justification**:
   ```
   Incident ID: INC-2024-001
   Severity: P1 - Production Down
   Impact: All users unable to access service
   Justification: Immediate fix required to restore service
   Approver: Jane Doe (VP Engineering)
   ```

2. **Temporarily disable branch protection**:
   ```bash
   # Disable enforce_admins to allow bypass
   gh api --method PUT /repos/$REPO_OWNER/$REPO_NAME/branches/main/protection \
     --field enforce_admins=false
   ```

3. **Merge hotfix PR**:
   ```bash
   gh pr merge $PR_NUMBER --admin --squash
   ```

4. **Re-enable branch protection**:
   ```bash
   gh api --method PUT /repos/$REPO_OWNER/$REPO_NAME/branches/main/protection \
     --field enforce_admins=true
   ```

5. **Post-incident actions**:
   - Create incident report
   - Run retrospective compliance check on merged code
   - Add test case to prevent future incident
   - Update runbook if needed

---

## 7. Maintenance and Updates

### 7.1 Adding New Required Status Checks

**Scenario**: New agent added to workflow (e.g., "Performance Testing Agent")

**Procedure**:

1. **Update GitHub Actions workflow**:
   ```yaml
   # .github/workflows/pr-validation.yml
   jobs:
     performance-testing-agent:
       name: performance / performance-testing
       runs-on: ubuntu-latest
       steps:
         # Performance testing logic
   ```

2. **Test new check**:
   - Open test PR
   - Verify new status check appears and runs correctly
   - Verify it doesn't block existing PRs

3. **Update branch protection** (after 1 week of stable operation):
   ```bash
   # Get current required checks
   CURRENT_CHECKS=$(gh api /repos/$REPO_OWNER/$REPO_NAME/branches/main/protection | jq '.required_status_checks.checks')

   # Add new check
   NEW_CHECKS=$(echo $CURRENT_CHECKS | jq '. + [{"context": "performance / performance-testing"}]')

   # Update branch protection
   gh api --method PUT /repos/$REPO_OWNER/$REPO_NAME/branches/main/protection \
     --field required_status_checks[strict]=true \
     --field required_status_checks[checks]="$NEW_CHECKS"
   ```

4. **Communicate change**:
   - Announce in team Slack channel
   - Update documentation
   - Monitor for issues for 1 week

### 7.2 Removing Deprecated Status Checks

**Scenario**: Agent decommissioned or merged into another agent

**Procedure**:

1. **Remove from branch protection first** (before removing from workflow):
   ```bash
   # Get current required checks
   CURRENT_CHECKS=$(gh api /repos/$REPO_OWNER/$REPO_NAME/branches/main/protection | jq '.required_status_checks.checks')

   # Remove deprecated check
   NEW_CHECKS=$(echo $CURRENT_CHECKS | jq 'del(.[] | select(.context == "deprecated-check"))')

   # Update branch protection
   gh api --method PUT /repos/$REPO_OWNER/$REPO_NAME/branches/main/protection \
     --field required_status_checks[checks]="$NEW_CHECKS"
   ```

2. **Wait 1 week** (ensure no in-flight PRs depend on old check)

3. **Remove from GitHub Actions workflow**:
   ```yaml
   # Delete job from .github/workflows/pr-validation.yml
   ```

4. **Verify**:
   - Check existing open PRs are not blocked
   - New PRs don't reference old check

### 7.3 Updating Status Check Names

**Scenario**: Renaming agent or reorganizing workflow

**Challenge**: Status check names are tied to branch protection rules

**Safe Procedure**:

1. **Add new status check** alongside old check:
   ```yaml
   jobs:
     old-check:
       name: old / check-name
       # Keep running

     new-check:
       name: new / check-name
       # New implementation
   ```

2. **Add new check to branch protection** (both checks required):
   ```bash
   # Add new check to required checks (keep old check)
   ```

3. **Wait for all open PRs to complete** (1-2 days)

4. **Remove old check from branch protection**:
   ```bash
   # Remove old check from required checks
   ```

5. **Remove old check from workflow**:
   ```yaml
   # Delete old job
   ```

### 7.4 Regular Audits

**Quarterly Review Checklist**:

- [ ] Verify branch protection rules match documentation
- [ ] Check for deprecated status checks
- [ ] Review bypass incidents (should be zero)
- [ ] Verify enforce_admins is enabled on main branch
- [ ] Test emergency bypass procedure (in non-prod)
- [ ] Review merge queue metrics (if enabled)
- [ ] Update team permissions and push restrictions
- [ ] Verify CODEOWNERS file accuracy (if used)

**Audit Command**:
```bash
#!/bin/bash
# Branch protection audit script

echo "=== Quarterly Branch Protection Audit ==="
echo "Date: $(date)"

# Check all protected branches
gh api /repos/$REPO_OWNER/$REPO_NAME/branches --paginate | jq '.[] | select(.protected == true) | {
  name: .name,
  protected: .protected
}' > protected_branches.json

# For each protected branch, get protection rules
for branch in $(jq -r '.name' protected_branches.json); do
  echo -e "\n=== Branch: $branch ==="
  gh api /repos/$REPO_OWNER/$REPO_NAME/branches/$branch/protection | jq '{
    required_status_checks: .required_status_checks.checks[].context,
    enforce_admins: .enforce_admins.enabled,
    required_reviews: .required_pull_request_reviews.required_approving_review_count,
    restrictions: .restrictions
  }'
done

echo -e "\n=== Audit Complete ==="
```

### 7.5 Rollout to Multiple Repositories

**Scenario**: Configure branch protection for all repositories in organization

**Approach**: Use Terraform or scripted automation

**Script Example**:

```bash
#!/bin/bash
# Rollout branch protection to all repositories

REPO_OWNER="tonic-scm"
REPOS=(
  "order-service"
  "user-service"
  "notification-service"
  "payment-service"
)

for repo in "${REPOS[@]}"; do
  echo "Configuring branch protection for $repo..."

  gh api --method PUT /repos/$REPO_OWNER/$repo/branches/main/protection \
    --input branch_protection_config.json

  if [ $? -eq 0 ]; then
    echo "✅ Success: $repo"
  else
    echo "❌ Failed: $repo"
  fi

  sleep 2  # Rate limiting
done

echo "Rollout complete"
```

---

## Conclusion

This document provides comprehensive guidance for configuring GitHub branch protection rules to enforce the multi-agent PR peer review workflow. Key takeaways:

1. **Required Status Checks**: 5 blocking checks ensure quality gates are enforced
2. **Branch Protection Settings**: Maximum protection on main, configurable for other branches
3. **Configuration Methods**: UI, CLI, API, and Terraform options provided
4. **Merge Queues**: Not recommended initially; reconsider at scale
5. **Troubleshooting**: Common issues and diagnostic procedures documented
6. **Maintenance**: Regular audits and safe update procedures

### Next Steps

1. Configure branch protection for `main` branch using preferred method
2. Test workflow with sample PR
3. Roll out to `develop` and `release/*` branches
4. Monitor for 1 week, adjust as needed
5. Document any organization-specific customizations
6. Schedule quarterly audit

### Support

For issues or questions:
- **Documentation**: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches
- **GitHub Support**: https://support.github.com
- **Internal Team**: DevOps Team (#devops-support Slack channel)

---

**Document Version**: 1.0
**Last Updated**: 2026-01-28
**Owner**: DevOps Team
**Reviewers**: Architecture Team, Security Team
