# Jira Automation Research: PR-Triggered Ticket Creation with Auto-Assignment

**Date**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**Analysis Phase**: Stage 0 - Research & Analysis
**Worker**: 3

---

## Executive Summary

This research document provides comprehensive guidance for implementing Jira REST API integration for PR-triggered ticket creation with auto-assignment to PR authors. Key findings include API endpoint documentation, auto-assignment implementation (using Account ID, not email), PR-Jira bidirectional linking, and robust error handling strategies.

---

## 1. Jira REST API v3 - Ticket Creation

### Create Issue Endpoint

**Endpoint**: `POST /rest/api/3/issue`

**Authentication**: Basic Auth with API Token
```
Authorization: Basic base64(email:api_token)
```

### Request Structure

```json
{
  "fields": {
    "project": {
      "key": "SCM"
    },
    "issuetype": {
      "name": "Bug"
    },
    "summary": "[PR-123] Code Quality Violation - Naming Convention",
    "description": {
      "type": "doc",
      "version": 1,
      "content": [
        {
          "type": "paragraph",
          "content": [
            {"type": "text", "text": "Code quality checks failed for PR #123"}
          ]
        }
      ]
    },
    "priority": {
      "name": "High"
    },
    "labels": ["peer-review", "auto-created"],
    "assignee": {
      "accountId": "5b10ac8d82e05b22cc7d4ef5"
    },
    "customfield_10001": "https://github.com/org/repo/pull/123"
  }
}
```

### Response Structure

```json
{
  "id": "10000",
  "key": "SCM-123",
  "self": "https://your-domain.atlassian.net/rest/api/3/issue/10000"
}
```

### Issue Types for Peer Review

| Issue Type | When to Use |
|------------|-------------|
| Bug | Code violations, quality issues |
| Task | LLD deviations requiring fixes |
| Story | Pattern rejections requiring rework |

---

## 2. Auto-Assignment Implementation

### Critical: Use Account ID, Not Email

**Important**: Post-GDPR, Jira API no longer accepts email addresses for assignment. You must use Account ID.

### Lookup Account ID from Email

**Endpoint**: `GET /rest/api/3/user/search?query={email}`

```bash
curl -X GET "https://your-domain.atlassian.net/rest/api/3/user/search?query=developer@company.com" \
  -H "Authorization: Basic ${AUTH}" \
  -H "Content-Type: application/json"
```

**Response**:
```json
[
  {
    "accountId": "5b10ac8d82e05b22cc7d4ef5",
    "accountType": "atlassian",
    "emailAddress": "developer@company.com",
    "displayName": "John Developer",
    "active": true
  }
]
```

### Auto-Assignment Workflow

```javascript
async function assignTicketToPRAuthor(prAuthorEmail, issueKey) {
  // Step 1: Lookup Account ID
  const users = await jiraApi.get(`/user/search?query=${prAuthorEmail}`);

  if (users.length === 0) {
    // Fallback to default assignee
    return assignToDefaultOwner(issueKey);
  }

  const accountId = users[0].accountId;

  // Step 2: Assign issue
  await jiraApi.put(`/issue/${issueKey}/assignee`, {
    accountId: accountId
  });
}
```

### Assignment During Issue Creation

```json
{
  "fields": {
    "project": {"key": "SCM"},
    "summary": "Code violation in PR #123",
    "assignee": {
      "accountId": "5b10ac8d82e05b22cc7d4ef5"
    }
  }
}
```

### Fallback Strategy

If PR author not found in Jira:
1. Try GitHub username as email prefix
2. Try organization email pattern (username@company.com)
3. Assign to component owner
4. Assign to architecture team lead (default)

---

## 3. PR-Jira Linking

### Strategy 1: Remote Links API (Recommended)

**Endpoint**: `POST /rest/api/3/issue/{issueKey}/remotelink`

```json
{
  "globalId": "system=github&id=org/repo/pull/123",
  "application": {
    "type": "com.github",
    "name": "GitHub"
  },
  "relationship": "Pull Request",
  "object": {
    "url": "https://github.com/org/repo/pull/123",
    "title": "PR #123: Feature implementation",
    "summary": "Pull request for feature X",
    "icon": {
      "url16x16": "https://github.githubassets.com/favicon.ico",
      "title": "GitHub"
    },
    "status": {
      "resolved": false,
      "icon": {
        "url16x16": "https://github.githubassets.com/favicon.ico",
        "title": "Open"
      }
    }
  }
}
```

### Strategy 2: Bidirectional Linking

**Jira → GitHub**: Use Remote Links API (above)

**GitHub → Jira**: Update PR description with Jira link

```javascript
async function linkPRToJira(prNumber, jiraKey, jiraUrl) {
  // Get current PR description
  const pr = await github.pulls.get({
    owner: 'org',
    repo: 'repo',
    pull_number: prNumber
  });

  const jiraLink = `\n\n---\n**Jira Ticket**: [${jiraKey}](${jiraUrl})`;

  // Update PR description
  await github.pulls.update({
    owner: 'org',
    repo: 'repo',
    pull_number: prNumber,
    body: pr.data.body + jiraLink
  });
}
```

---

## 4. Error Handling & Retry Patterns

### Rate Limiting (2025-2026 Changes)

**New Rate Limits** (Effective November 2025):
- Points-based system (not simple request counting)
- Headers: `X-RateLimit-Remaining`, `Retry-After`

**Handling**:
```javascript
async function jiraApiCall(endpoint, options) {
  const response = await fetch(endpoint, options);

  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After') || 60;
    await sleep(retryAfter * 1000);
    return jiraApiCall(endpoint, options); // Retry
  }

  return response;
}
```

### Exponential Backoff with Jitter

```javascript
async function retryWithBackoff(fn, maxRetries = 4) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxRetries) throw error;

      const baseDelay = Math.min(1000 * Math.pow(2, attempt), 30000);
      const jitter = Math.random() * 1000;
      await sleep(baseDelay + jitter);
    }
  }
}
```

### Retry Strategy

| Error Code | Action | Max Retries |
|------------|--------|-------------|
| 429 (Rate Limited) | Wait for Retry-After, then retry | 5 |
| 5xx (Server Error) | Exponential backoff | 4 |
| 401 (Unauthorized) | Refresh token, retry once | 1 |
| 400 (Bad Request) | Log error, don't retry | 0 |
| 404 (Not Found) | Log error, don't retry | 0 |

### Circuit Breaker Pattern

```javascript
class JiraCircuitBreaker {
  constructor() {
    this.failures = 0;
    this.threshold = 5;
    this.resetTimeout = 60000; // 1 minute
    this.state = 'CLOSED';
  }

  async execute(fn) {
    if (this.state === 'OPEN') {
      throw new Error('Circuit breaker is open');
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  onSuccess() {
    this.failures = 0;
    this.state = 'CLOSED';
  }

  onFailure() {
    this.failures++;
    if (this.failures >= this.threshold) {
      this.state = 'OPEN';
      setTimeout(() => {
        this.state = 'HALF-OPEN';
      }, this.resetTimeout);
    }
  }
}
```

---

## 5. Ticket Templates for Peer Review

### Code Violation Ticket

```javascript
function createCodeViolationTicket(pr, violations) {
  return {
    fields: {
      project: { key: 'SCM' },
      issuetype: { name: 'Bug' },
      summary: `[PR-${pr.number}] Code Quality Violations`,
      description: {
        type: 'doc',
        version: 1,
        content: [
          {
            type: 'heading',
            attrs: { level: 2 },
            content: [{ type: 'text', text: 'Code Quality Check Failed' }]
          },
          {
            type: 'paragraph',
            content: [
              { type: 'text', text: 'The following violations were detected:' }
            ]
          },
          {
            type: 'bulletList',
            content: violations.map(v => ({
              type: 'listItem',
              content: [{
                type: 'paragraph',
                content: [
                  { type: 'text', text: `${v.file}:${v.line} - `, marks: [{ type: 'code' }] },
                  { type: 'text', text: v.message }
                ]
              }]
            }))
          },
          {
            type: 'paragraph',
            content: [
              { type: 'text', text: 'Pull Request: ' },
              {
                type: 'text',
                text: `#${pr.number}`,
                marks: [{ type: 'link', attrs: { href: pr.url } }]
              }
            ]
          }
        ]
      },
      priority: { name: mapSeverityToPriority(violations) },
      labels: ['peer-review', 'code-violation', 'auto-created'],
      customfield_10001: pr.url // PR URL custom field
    }
  };
}

function mapSeverityToPriority(violations) {
  const criticalCount = violations.filter(v => v.severity === 'CRITICAL').length;
  const majorCount = violations.filter(v => v.severity === 'MAJOR').length;

  if (criticalCount > 0) return 'Highest';
  if (majorCount > 3) return 'High';
  if (majorCount > 0) return 'Medium';
  return 'Low';
}
```

### LLD Deviation Ticket

```javascript
function createLLDDeviationTicket(pr, deviations) {
  return {
    fields: {
      project: { key: 'SCM' },
      issuetype: { name: 'Task' },
      summary: `[PR-${pr.number}] LLD Alignment Deviation`,
      description: {
        type: 'doc',
        version: 1,
        content: [
          {
            type: 'heading',
            attrs: { level: 2 },
            content: [{ type: 'text', text: 'Design Deviation Detected' }]
          },
          {
            type: 'paragraph',
            content: [
              { type: 'text', text: 'The PR implementation deviates from the Low-Level Design:' }
            ]
          },
          ...deviations.map(d => ({
            type: 'paragraph',
            content: [
              { type: 'text', text: `Section: ${d.lld_section}`, marks: [{ type: 'strong' }] },
              { type: 'hardBreak' },
              { type: 'text', text: `Expected: ${d.expected}` },
              { type: 'hardBreak' },
              { type: 'text', text: `Actual: ${d.actual}` },
              { type: 'hardBreak' },
              { type: 'text', text: `Recommendation: ${d.recommendation}`, marks: [{ type: 'em' }] }
            ]
          }))
        ]
      },
      priority: { name: deviations[0].severity === 'CRITICAL' ? 'Highest' : 'High' },
      labels: ['peer-review', 'lld-deviation', 'auto-created']
    }
  };
}
```

---

## 6. Complete Integration Example

### GitHub Action for Jira Ticket Creation

```yaml
name: Create Jira Ticket on Failure

on:
  workflow_run:
    workflows: ["Multi-Agent PR Review"]
    types: [completed]

jobs:
  create-jira-ticket:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Get PR details
        id: pr
        uses: actions/github-script@v7
        with:
          script: |
            const pr = await github.rest.pulls.get({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: ${{ github.event.workflow_run.pull_requests[0].number }}
            });
            return {
              number: pr.data.number,
              title: pr.data.title,
              url: pr.data.html_url,
              author: pr.data.user.login,
              authorEmail: pr.data.user.email || `${pr.data.user.login}@company.com`
            };

      - name: Lookup Jira Account ID
        id: jira-user
        env:
          JIRA_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          JIRA_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_USER_EMAIL }}
        run: |
          AUTHOR_EMAIL="${{ fromJson(steps.pr.outputs.result).authorEmail }}"

          RESPONSE=$(curl -s -X GET \
            "${JIRA_URL}/rest/api/3/user/search?query=${AUTHOR_EMAIL}" \
            -H "Authorization: Basic $(echo -n ${JIRA_EMAIL}:${JIRA_TOKEN} | base64)" \
            -H "Content-Type: application/json")

          ACCOUNT_ID=$(echo $RESPONSE | jq -r '.[0].accountId // empty')

          if [ -z "$ACCOUNT_ID" ]; then
            # Fallback to default assignee
            ACCOUNT_ID="${{ secrets.DEFAULT_JIRA_ASSIGNEE_ID }}"
          fi

          echo "account_id=$ACCOUNT_ID" >> $GITHUB_OUTPUT

      - name: Create Jira Ticket
        id: create-ticket
        env:
          JIRA_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          JIRA_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_USER_EMAIL }}
        run: |
          PR_DATA='${{ steps.pr.outputs.result }}'
          PR_NUMBER=$(echo $PR_DATA | jq -r '.number')
          PR_TITLE=$(echo $PR_DATA | jq -r '.title')
          PR_URL=$(echo $PR_DATA | jq -r '.url')
          ACCOUNT_ID="${{ steps.jira-user.outputs.account_id }}"

          TICKET_DATA=$(cat <<EOF
          {
            "fields": {
              "project": {"key": "SCM"},
              "issuetype": {"name": "Bug"},
              "summary": "[PR-${PR_NUMBER}] Peer Review Failed - ${PR_TITLE}",
              "description": {
                "type": "doc",
                "version": 1,
                "content": [
                  {
                    "type": "paragraph",
                    "content": [
                      {"type": "text", "text": "Automated peer review checks failed for this PR."},
                      {"type": "hardBreak"},
                      {"type": "text", "text": "Please review the GitHub Actions logs and fix the issues."}
                    ]
                  },
                  {
                    "type": "paragraph",
                    "content": [
                      {"type": "text", "text": "Pull Request: "},
                      {"type": "text", "text": "#${PR_NUMBER}", "marks": [{"type": "link", "attrs": {"href": "${PR_URL}"}}]}
                    ]
                  }
                ]
              },
              "priority": {"name": "High"},
              "labels": ["peer-review", "auto-created", "pr-${PR_NUMBER}"],
              "assignee": {"accountId": "${ACCOUNT_ID}"}
            }
          }
          EOF
          )

          RESPONSE=$(curl -s -X POST \
            "${JIRA_URL}/rest/api/3/issue" \
            -H "Authorization: Basic $(echo -n ${JIRA_EMAIL}:${JIRA_TOKEN} | base64)" \
            -H "Content-Type: application/json" \
            -d "$TICKET_DATA")

          TICKET_KEY=$(echo $RESPONSE | jq -r '.key')
          echo "ticket_key=$TICKET_KEY" >> $GITHUB_OUTPUT
          echo "ticket_url=${JIRA_URL}/browse/${TICKET_KEY}" >> $GITHUB_OUTPUT

      - name: Add Remote Link to Jira
        env:
          JIRA_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          JIRA_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_USER_EMAIL }}
        run: |
          TICKET_KEY="${{ steps.create-ticket.outputs.ticket_key }}"
          PR_URL="${{ fromJson(steps.pr.outputs.result).url }}"
          PR_NUMBER="${{ fromJson(steps.pr.outputs.result).number }}"

          curl -X POST \
            "${JIRA_URL}/rest/api/3/issue/${TICKET_KEY}/remotelink" \
            -H "Authorization: Basic $(echo -n ${JIRA_EMAIL}:${JIRA_TOKEN} | base64)" \
            -H "Content-Type: application/json" \
            -d "{
              \"globalId\": \"system=github&id=${{ github.repository }}/pull/${PR_NUMBER}\",
              \"application\": {\"type\": \"com.github\", \"name\": \"GitHub\"},
              \"relationship\": \"Pull Request\",
              \"object\": {
                \"url\": \"${PR_URL}\",
                \"title\": \"PR #${PR_NUMBER}\",
                \"icon\": {\"url16x16\": \"https://github.githubassets.com/favicon.ico\"}
              }
            }"

      - name: Comment on PR with Jira Link
        uses: actions/github-script@v7
        with:
          script: |
            const ticketKey = '${{ steps.create-ticket.outputs.ticket_key }}';
            const ticketUrl = '${{ steps.create-ticket.outputs.ticket_url }}';

            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: ${{ github.event.workflow_run.pull_requests[0].number }},
              body: `## ❌ Peer Review Failed

              A Jira ticket has been created to track this issue:

              **Ticket**: [${ticketKey}](${ticketUrl})

              Please review the errors in the workflow logs and push fixes.`
            });
```

---

## 7. Key Recommendations

### For Jira Integration Implementation:

1. **Always use Account ID** for assignee (not email)
2. **Implement user lookup caching** to reduce API calls
3. **Use Remote Links API** for PR-Jira linking
4. **Implement exponential backoff** for retries
5. **Use circuit breaker** to prevent cascading failures
6. **Create rich ADF descriptions** with PR context
7. **Map severity to priority** automatically
8. **Add bidirectional links** (Jira ↔ GitHub)
9. **Handle rate limits** with Retry-After header
10. **Implement fallback assignee** strategy

### Required Secrets

| Secret | Purpose |
|--------|---------|
| `JIRA_API_TOKEN` | API authentication token |
| `JIRA_BASE_URL` | Jira instance URL |
| `JIRA_USER_EMAIL` | Service account email |
| `DEFAULT_JIRA_ASSIGNEE_ID` | Fallback assignee Account ID |

---

**End of Research Document**
