# Branch Protection Configuration Guide

**Version**: 1.0
**Date**: 2026-01-28
**Project**: Tonic Configuration Management Platform

---

## 1. Overview

This guide provides complete instructions for configuring GitHub branch protection rules to work with the PR Peer Review Orchestration workflow.

---

## 2. Required Status Checks

### 2.1 Blocking Checks (Required)

These checks MUST pass before a PR can be merged:

| Check Name | Job Name | Purpose |
|------------|----------|---------|
| `Pre-Flight Validation` | `pre-flight` | Validates PR eligibility |
| `Code Quality Review` | `code-quality-agent` | Enforces coding standards |
| `Architecture Review` | `architect-agent` | Detects new patterns |
| `Final Report` | `final-report` | Aggregates all results |

### 2.2 Conditional Checks

These checks only run when needed and should NOT be required:

| Check Name | When It Runs |
|------------|--------------|
| `LLD Alignment Review` | Only when new pattern detected |
| `Peer Review Coordination` | Only when new pattern detected |
| `Jira Ticket Creation` | Only on failures |

### 2.3 Configuration Note

**Important**: Only require the checks that always run. Conditional checks that might be skipped should not be marked as required, or they will block merges when skipped.

---

## 3. Branch Protection Settings

### 3.1 Main Branch Configuration

```yaml
Branch: main

Settings:
  # Status Checks
  ✓ Require status checks to pass before merging
  ✓ Require branches to be up to date before merging

  Required Status Checks:
    - "Pre-Flight Validation"
    - "Code Quality Review"
    - "Architecture Review"
    - "Final Report"

  # Pull Request Reviews
  ✓ Require pull request reviews before merging
    - Required approving reviews: 0 (handled by orchestrator)
  ✓ Dismiss stale pull request approvals when new commits are pushed

  # Additional Settings
  ✓ Require conversation resolution before merging
  ✓ Require linear history
  ✗ Allow force pushes (NEVER enable)
  ✗ Allow deletions (NEVER enable)
  ✓ Enforce for administrators
```

### 3.2 Develop Branch Configuration

```yaml
Branch: develop

Settings:
  ✓ Require status checks to pass before merging
  ✓ Require branches to be up to date before merging

  Required Status Checks:
    - "Code Quality Review"
    - "Final Report"

  ✓ Require pull request reviews before merging
    - Required approving reviews: 0
  ✗ Enforce for administrators (allow bypass for hotfixes)
```

---

## 4. Configuration Methods

### 4.1 GitHub UI Configuration

**Step 1**: Navigate to Repository Settings
1. Go to your repository on GitHub
2. Click "Settings" tab
3. Select "Branches" from left sidebar

**Step 2**: Add Branch Protection Rule
1. Click "Add rule"
2. Enter branch name pattern: `main`

**Step 3**: Configure Required Checks
1. Check "Require status checks to pass before merging"
2. Check "Require branches to be up to date before merging"
3. Search and select each required check:
   - Pre-Flight Validation
   - Code Quality Review
   - Architecture Review
   - Final Report

**Step 4**: Save Rule
1. Click "Create" or "Save changes"

### 4.2 GitHub CLI Configuration

```bash
#!/bin/bash
# Configure branch protection for main branch

OWNER="your-org"
REPO="your-repo"
BRANCH="main"

# Create branch protection rule
gh api repos/${OWNER}/${REPO}/branches/${BRANCH}/protection \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  -f required_status_checks='{"strict":true,"contexts":["Pre-Flight Validation","Code Quality Review","Architecture Review","Final Report"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"required_approving_review_count":0}' \
  -f restrictions=null \
  -f required_linear_history=true \
  -f allow_force_pushes=false \
  -f allow_deletions=false

echo "Branch protection configured for ${BRANCH}"
```

### 4.3 GitHub API Configuration

```bash
curl -X PUT \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO/branches/main/protection \
  -d '{
    "required_status_checks": {
      "strict": true,
      "contexts": [
        "Pre-Flight Validation",
        "Code Quality Review",
        "Architecture Review",
        "Final Report"
      ]
    },
    "enforce_admins": true,
    "required_pull_request_reviews": {
      "dismiss_stale_reviews": true,
      "require_code_owner_reviews": false,
      "required_approving_review_count": 0
    },
    "restrictions": null,
    "required_linear_history": true,
    "allow_force_pushes": false,
    "allow_deletions": false
  }'
```

---

## 5. Merge Queue Configuration (Optional)

### 5.1 When to Use Merge Queues

Consider enabling merge queues when:
- PR volume > 50 PRs/day
- Frequent merge conflicts
- Long-running CI pipelines

### 5.2 Merge Queue Setup

```yaml
# In branch protection settings:
✓ Require merge queue

Merge Queue Settings:
  - Build concurrency: 5
  - Minimum entries to merge: 1
  - Maximum entries to build: 10
  - Timeout: 60 minutes
```

---

## 6. Troubleshooting

### 6.1 Status Check Not Appearing

**Problem**: Required status check doesn't appear in the dropdown.

**Solution**:
1. Run the workflow at least once on the target branch
2. Wait up to 7 days for checks to appear
3. Manually type the exact job name if needed

### 6.2 PR Blocked Despite Checks Passing

**Problem**: PR shows as blocked even though all checks passed.

**Solution**:
1. Verify check names match exactly (case-sensitive)
2. Check for conditional jobs that were skipped
3. Ensure "Require branches to be up to date" is satisfied

### 6.3 Conditional Checks Blocking Merge

**Problem**: Skipped conditional checks are blocking the merge.

**Solution**:
1. Remove conditional checks from required list
2. Only require checks that always run
3. Use the Final Report job as the gate (it always runs)

---

## 7. Verification Commands

### Verify Current Protection

```bash
# View current branch protection rules
gh api repos/OWNER/REPO/branches/main/protection

# List required status checks
gh api repos/OWNER/REPO/branches/main/protection/required_status_checks
```

### Test Configuration

```bash
# Create a test PR to verify checks trigger correctly
gh pr create --title "Test: Branch Protection" --body "Testing branch protection configuration"
```

---

## 8. Quick Reference

### Required Secrets

| Secret | Purpose |
|--------|---------|
| `CONFLUENCE_API_TOKEN` | Pattern library access |
| `CONFLUENCE_BASE_URL` | Confluence instance URL |
| `JIRA_API_TOKEN` | Jira ticket creation |
| `JIRA_BASE_URL` | Jira instance URL |
| `JIRA_USER_EMAIL` | Jira service account email |
| `DEFAULT_JIRA_ASSIGNEE_ID` | Fallback assignee Account ID |

### Workflow Job Names (for Branch Protection)

```
pre-flight
code-quality-agent
architect-agent
lld-alignment-agent
peer-review-agent
jira-integration
final-report
```

---

**End of Configuration Guide**
