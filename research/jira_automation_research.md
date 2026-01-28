# Jira Automation Research: PR-Triggered Ticket Creation with Auto-Assignment

## Executive Summary

This document provides comprehensive research on implementing automated Jira ticket creation triggered by GitHub Pull Requests, with automatic assignment to reviewers. The research covers Jira REST API v3, authentication methods, auto-assignment patterns, bidirectional PR-Jira linking, webhook integration, error handling, and best practices.

---

## Table of Contents

1. [Jira REST API v3 Overview](#jira-rest-api-v3-overview)
2. [Authentication Methods](#authentication-methods)
3. [Creating Issues via REST API](#creating-issues-via-rest-api)
4. [Auto-Assignment Implementation](#auto-assignment-implementation)
5. [PR-Jira Linking Strategies](#pr-jira-linking-strategies)
6. [Webhook Integration](#webhook-integration)
7. [Rate Limiting and Throttling](#rate-limiting-and-throttling)
8. [Error Handling and Retry Patterns](#error-handling-and-retry-patterns)
9. [Best Practices](#best-practices)
10. [Implementation Examples](#implementation-examples)
11. [Sources](#sources)

---

## 1. Jira REST API v3 Overview

### Base URL Structure
```
https://<your-domain>.atlassian.net/rest/api/3/
```

### Key Endpoints for Automation

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/rest/api/3/issue` | POST | Create new issue |
| `/rest/api/3/issue/{issueIdOrKey}` | PUT | Update existing issue |
| `/rest/api/3/issue/{issueIdOrKey}/assignee` | PUT | Assign issue to user |
| `/rest/api/3/issue/{issueIdOrKey}/remotelink` | POST | Add remote link (GitHub PR) |
| `/rest/api/3/user/search` | GET | Search for user by email |
| `/rest/api/3/webhook` | POST | Register webhook |

### Required Permissions
- **Create Issues**: Browse Projects permission
- **Assign Issues**: Browse Projects + Assign Issues permission
- **View Issues**: Browse Projects + issue-level security (if configured)

---

## 2. Authentication Methods

### API Token Authentication (Recommended for Automation)

**How to Generate:**
1. Navigate to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name your token and save it securely

**Usage:**
```bash
# Basic Auth with email and API token
curl -u email@example.com:YOUR_API_TOKEN \
  -H "Content-Type: application/json" \
  https://your-domain.atlassian.net/rest/api/3/issue
```

**Security Best Practices:**
- Store API tokens in secure vaults (Azure Key Vault, AWS Secrets Manager, GitHub Secrets)
- Never commit tokens to version control
- Rotate tokens regularly (recommended: every 90 days)
- Use separate tokens for different integrations
- Monitor token usage through Atlassian admin console

### OAuth 2.0 (For User-Delegated Access)

**Use Cases:**
- Applications requiring user consent
- Multi-tenant SaaS applications
- Apps that need to act on behalf of users

**OAuth Flow:**
1. Register OAuth 2.0 integration in Atlassian Developer Console
2. Implement authorization code flow
3. Exchange authorization code for access token
4. Refresh tokens before expiration

### Important: GDPR and Authentication
Post-GDPR, Atlassian APIs require UUID-based identifiers (accountId) rather than usernames or email addresses for user-related operations.

---

## 3. Creating Issues via REST API

### Required Fields

Creating a Jira issue requires the following core fields:

1. **project** - Project ID or key
2. **issuetype** - Issue type name (e.g., "Task", "Bug", "Story")
3. **summary** - Issue title/summary
4. **description** - Issue description (uses Atlassian Document Format in API v3)

### Discovering Required Fields (createmeta)

Before creating issues, query the createmeta endpoint to discover required and optional fields:

```bash
GET /rest/api/3/issue/createmeta/{projectIdOrKey}/issuetypes/{issueTypeId}
```

**Response includes:**
- Required fields for the issue type
- Allowed values for select/multi-select fields
- Custom field definitions
- Field validation rules

### Example: Creating an Issue (API v3)

```bash
curl -X POST \
  -u email@example.com:YOUR_API_TOKEN \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "project": {
        "key": "PROJ"
      },
      "issuetype": {
        "name": "Task"
      },
      "summary": "Peer Review: PR #123 - Add authentication feature",
      "description": {
        "type": "doc",
        "version": 1,
        "content": [
          {
            "type": "paragraph",
            "content": [
              {
                "type": "text",
                "text": "This ticket tracks the peer review for PR #123."
              }
            ]
          },
          {
            "type": "paragraph",
            "content": [
              {
                "type": "text",
                "text": "PR Author: "
              },
              {
                "type": "text",
                "text": "john.doe",
                "marks": [{"type": "strong"}]
              }
            ]
          },
          {
            "type": "paragraph",
            "content": [
              {
                "type": "text",
                "text": "GitHub PR Link: "
              },
              {
                "type": "text",
                "text": "https://github.com/org/repo/pull/123",
                "marks": [
                  {
                    "type": "link",
                    "attrs": {
                      "href": "https://github.com/org/repo/pull/123"
                    }
                  }
                ]
              }
            ]
          }
        ]
      },
      "labels": ["peer-review", "pr-123"],
      "assignee": {
        "accountId": "5b10ac8d82e05b22cc7d4ef5"
      }
    }
  }' \
  https://your-domain.atlassian.net/rest/api/3/issue
```

### Success Response (201 Created)

```json
{
  "id": "10000",
  "key": "PROJ-123",
  "self": "https://your-domain.atlassian.net/rest/api/3/issue/10000"
}
```

### Common Errors

| Status Code | Error | Solution |
|-------------|-------|----------|
| 400 | Bad Request | Verify JSON syntax, required fields, field formats |
| 401 | Unauthorized | Check email and API token credentials |
| 403 | Forbidden | Verify user has permission to create issues in project |
| 404 | Not Found | Verify project key and issue type exist |

### Atlassian Document Format (ADF) for Descriptions

API v3 uses ADF for rich text fields like descriptions. Key structure:

```json
{
  "type": "doc",
  "version": 1,
  "content": [
    {
      "type": "paragraph",
      "content": [
        {"type": "text", "text": "Plain text"}
      ]
    },
    {
      "type": "heading",
      "attrs": {"level": 2},
      "content": [
        {"type": "text", "text": "Heading"}
      ]
    },
    {
      "type": "bulletList",
      "content": [
        {
          "type": "listItem",
          "content": [
            {
              "type": "paragraph",
              "content": [
                {"type": "text", "text": "List item"}
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "codeBlock",
      "attrs": {"language": "javascript"},
      "content": [
        {"type": "text", "text": "console.log('code');"}
      ]
    }
  ]
}
```

**Supported ADF Node Types:**
- `paragraph`, `heading`, `blockquote`
- `bulletList`, `orderedList`, `listItem`
- `codeBlock`, `panel`
- `table`, `tableRow`, `tableCell`, `tableHeader`

**Supported Text Marks:**
- `strong` (bold), `em` (italic), `code`, `strike`, `underline`
- `link` (with href attribute)

---

## 4. Auto-Assignment Implementation

### Challenge: Email vs Account ID

Post-GDPR, Jira REST API **requires Account ID** for user identification. Email addresses are no longer directly accepted for assignee fields.

### Step 1: Get Account ID from Email

```bash
GET /rest/api/3/user/search?query={email}
```

**Example:**
```bash
curl -u email@example.com:YOUR_API_TOKEN \
  "https://your-domain.atlassian.net/rest/api/3/user/search?query=reviewer@example.com"
```

**Response:**
```json
[
  {
    "accountId": "5b10ac8d82e05b22cc7d4ef5",
    "emailAddress": "reviewer@example.com",
    "displayName": "Jane Reviewer",
    "active": true
  }
]
```

### Step 2A: Assign During Issue Creation

Include the assignee field in the create issue request:

```json
{
  "fields": {
    "project": {"key": "PROJ"},
    "issuetype": {"name": "Task"},
    "summary": "Review PR #123",
    "assignee": {
      "accountId": "5b10ac8d82e05b22cc7d4ef5"
    }
  }
}
```

### Step 2B: Assign After Issue Creation

Use the dedicated assignee endpoint:

```bash
PUT /rest/api/3/issue/{issueIdOrKey}/assignee
```

**Example:**
```bash
curl -X PUT \
  -u email@example.com:YOUR_API_TOKEN \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": "5b10ac8d82e05b22cc7d4ef5"
  }' \
  https://your-domain.atlassian.net/rest/api/3/issue/PROJ-123/assignee
```

### Auto-Assignment Implementation Pattern

```javascript
async function autoAssignIssue(prAuthorEmail, reviewerEmail, prNumber) {
  // 1. Get reviewer's account ID
  const reviewerAccountId = await getAccountIdByEmail(reviewerEmail);

  if (!reviewerAccountId) {
    throw new Error(`Reviewer with email ${reviewerEmail} not found in Jira`);
  }

  // 2. Create issue with assignment
  const issueData = {
    fields: {
      project: { key: process.env.JIRA_PROJECT_KEY },
      issuetype: { name: "Peer Review" },
      summary: `Peer Review: PR #${prNumber}`,
      description: createADFDescription(prNumber, prAuthorEmail),
      labels: ["peer-review", `pr-${prNumber}`],
      assignee: {
        accountId: reviewerAccountId
      }
    }
  };

  const response = await fetch(
    `${JIRA_BASE_URL}/rest/api/3/issue`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Basic ${Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(issueData)
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to create issue: ${response.statusText}`);
  }

  return await response.json();
}

async function getAccountIdByEmail(email) {
  const response = await fetch(
    `${JIRA_BASE_URL}/rest/api/3/user/search?query=${encodeURIComponent(email)}`,
    {
      headers: {
        'Authorization': `Basic ${Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64')}`
      }
    }
  );

  if (!response.ok) {
    return null;
  }

  const users = await response.json();
  return users.length > 0 ? users[0].accountId : null;
}
```

### Caching Account IDs

To avoid repeated API calls, implement a caching strategy:

```javascript
// In-memory cache (use Redis/Memcached for production)
const accountIdCache = new Map();
const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours

async function getCachedAccountId(email) {
  const cached = accountIdCache.get(email);

  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.accountId;
  }

  const accountId = await getAccountIdByEmail(email);

  if (accountId) {
    accountIdCache.set(email, {
      accountId,
      timestamp: Date.now()
    });
  }

  return accountId;
}
```

### Handling Assignment Failures

```javascript
async function assignWithFallback(issueKey, primaryReviewerEmail, fallbackReviewerEmail) {
  let accountId = await getCachedAccountId(primaryReviewerEmail);

  if (!accountId && fallbackReviewerEmail) {
    console.warn(`Primary reviewer ${primaryReviewerEmail} not found, trying fallback`);
    accountId = await getCachedAccountId(fallbackReviewerEmail);
  }

  if (!accountId) {
    console.error('No valid reviewer found, issue will remain unassigned');
    return null;
  }

  try {
    await fetch(
      `${JIRA_BASE_URL}/rest/api/3/issue/${issueKey}/assignee`,
      {
        method: 'PUT',
        headers: {
          'Authorization': `Basic ${Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ accountId })
      }
    );
    return accountId;
  } catch (error) {
    console.error('Failed to assign issue:', error);
    return null;
  }
}
```

---

## 5. PR-Jira Linking Strategies

### Strategy 1: Official GitHub for Jira Integration

**How It Works:**
- Install "GitHub for Jira" app from Atlassian Marketplace
- Link GitHub organization/repositories to Jira project
- Include Jira issue key in branch names, commit messages, or PR titles
- Jira automatically creates bidirectional links

**Linking Pattern:**
```bash
# Branch name
git checkout -b PROJ-123-add-authentication

# Commit message
git commit -m "PROJ-123 Implement OAuth2 authentication"

# PR title
"PROJ-123: Add OAuth2 authentication feature"
```

**Advantages:**
- Automatic bidirectional linking
- Rich PR information displayed in Jira (status, reviews, commits)
- No custom code required
- Official support from Atlassian

**Limitations:**
- Requires issue key in advance (doesn't work for auto-created tickets)
- Less control over link metadata
- Dependent on third-party app availability

### Strategy 2: Remote Links via REST API

**Use Case:** When you need to programmatically link PRs to Jira tickets (ideal for auto-created tickets)

#### Creating Remote Links

```bash
POST /rest/api/3/issue/{issueIdOrKey}/remotelink
```

**Required Fields:**
- `url` - Link to the remote resource (GitHub PR URL)
- `title` - Display text for the link

**Optional Fields:**
- `globalId` - Unique identifier (format: `system=github&id=org/repo/pull/123`)
- `relationship` - Link relationship type
- `icon` - Icon URL
- `status` - Status information (resolved/open)

**Example: Link GitHub PR to Jira Issue**

```bash
curl -X POST \
  -u email@example.com:YOUR_API_TOKEN \
  -H "Content-Type: application/json" \
  -d '{
    "globalId": "system=github&id=myorg/myrepo/pull/123",
    "relationship": "Pull Request",
    "object": {
      "url": "https://github.com/myorg/myrepo/pull/123",
      "title": "PR #123: Add authentication feature",
      "icon": {
        "url16x16": "https://github.com/favicon.ico",
        "title": "GitHub"
      },
      "status": {
        "resolved": false,
        "icon": {
          "url16x16": "https://github.com/favicon.ico",
          "title": "Open"
        }
      }
    }
  }' \
  https://your-domain.atlassian.net/rest/api/3/issue/PROJ-123/remotelink
```

#### Updating Remote Links

Use `globalId` for idempotent updates:

```bash
# Delete existing link with same globalId (if exists)
GET /rest/api/3/issue/{issueKey}/remotelink?globalId={globalId}
DELETE /rest/api/3/issue/{issueKey}/remotelink/{linkId}

# Create new link
POST /rest/api/3/issue/{issueKey}/remotelink
```

#### Implementation Example

```javascript
async function linkPRToJiraIssue(issueKey, prData) {
  const globalId = `system=github&id=${prData.repo}/pull/${prData.number}`;

  // Check if link already exists
  const existingLinks = await fetch(
    `${JIRA_BASE_URL}/rest/api/3/issue/${issueKey}/remotelink?globalId=${encodeURIComponent(globalId)}`,
    {
      headers: {
        'Authorization': `Basic ${Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64')}`
      }
    }
  );

  const links = await existingLinks.json();

  // Delete existing link if present
  if (links.length > 0) {
    await fetch(
      `${JIRA_BASE_URL}/rest/api/3/issue/${issueKey}/remotelink/${links[0].id}`,
      {
        method: 'DELETE',
        headers: {
          'Authorization': `Basic ${Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64')}`
        }
      }
    );
  }

  // Create remote link
  const linkData = {
    globalId,
    relationship: "Pull Request",
    object: {
      url: prData.html_url,
      title: `PR #${prData.number}: ${prData.title}`,
      icon: {
        url16x16: "https://github.com/favicon.ico",
        title: "GitHub"
      },
      status: {
        resolved: prData.state === 'closed',
        icon: {
          url16x16: "https://github.com/favicon.ico",
          title: prData.state === 'open' ? 'Open' : 'Closed'
        }
      }
    }
  };

  const response = await fetch(
    `${JIRA_BASE_URL}/rest/api/3/issue/${issueKey}/remotelink`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Basic ${Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(linkData)
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to create remote link: ${response.statusText}`);
  }

  return await response.json();
}
```

### Strategy 3: Bidirectional Linking (GitHub + Jira)

**Jira → GitHub:** Use Remote Links API (as shown above)

**GitHub → Jira:** Add Jira issue link to PR description

```javascript
async function addJiraLinkToPR(owner, repo, prNumber, jiraIssueKey) {
  const jiraUrl = `https://your-domain.atlassian.net/browse/${jiraIssueKey}`;

  // Get current PR description
  const pr = await github.rest.pulls.get({
    owner,
    repo,
    pull_number: prNumber
  });

  const currentBody = pr.data.body || '';
  const jiraLinkText = `\n\n---\n**Jira Ticket:** [${jiraIssueKey}](${jiraUrl})`;

  // Avoid duplicate links
  if (!currentBody.includes(jiraUrl)) {
    await github.rest.pulls.update({
      owner,
      repo,
      pull_number: prNumber,
      body: currentBody + jiraLinkText
    });
  }
}
```

### Best Practice: Complete Bidirectional Linking Flow

```javascript
async function createLinkedPeerReviewTicket(prData, reviewerEmail) {
  // 1. Create Jira issue with auto-assignment
  const issue = await autoAssignIssue(
    prData.user.email,
    reviewerEmail,
    prData.number
  );

  console.log(`Created Jira issue: ${issue.key}`);

  // 2. Link PR to Jira (Jira → GitHub)
  await linkPRToJiraIssue(issue.key, prData);
  console.log(`Linked PR to Jira issue`);

  // 3. Add Jira link to PR (GitHub → Jira)
  await addJiraLinkToPR(
    prData.base.repo.owner.login,
    prData.base.repo.name,
    prData.number,
    issue.key
  );
  console.log(`Added Jira link to PR description`);

  return issue;
}
```

---

## 6. Webhook Integration

### Overview

Jira webhooks enable real-time notifications when events occur, eliminating the need for polling. Use webhooks to:
- Notify systems when peer review tickets are updated
- Track status changes (e.g., "In Review" → "Approved")
- Monitor comments and feedback
- Trigger GitHub PR status updates

### Webhook Registration Methods

1. **Admin Webhooks** (Jira UI): System > Webhooks
2. **REST API** (Connect/OAuth apps): `/rest/webhooks/1.0/webhook`
3. **Connect App Descriptor** (Atlassian Connect apps)

### REST API Webhook Registration

**Endpoint:**
```bash
POST /rest/webhooks/1.0/webhook
```

**Example: Register Webhook for Issue Updates**

```bash
curl -X POST \
  -u email@example.com:YOUR_API_TOKEN \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Peer Review Status Updates",
    "url": "https://your-app.com/webhooks/jira",
    "events": [
      "jira:issue_updated",
      "jira:issue_deleted",
      "comment_created"
    ],
    "filters": {
      "issue-related-events-section": "Project = PROJ AND labels = peer-review"
    },
    "excludeBody": false
  }' \
  https://your-domain.atlassian.net/rest/webhooks/1.0/webhook
```

**Jira 10.x+ Format:**
```json
{
  "name": "Peer Review Status Updates",
  "url": "https://your-app.com/webhooks/jira",
  "events": [
    "jira:issue_updated",
    "jira:issue_deleted"
  ],
  "configuration": {
    "FILTERS": "Project = PROJ AND labels = peer-review",
    "EXCLUDE_BODY": "false",
    "DESCRIPTION": "Webhook for peer review ticket updates"
  },
  "active": "true"
}
```

### Supported Events

| Event | Trigger |
|-------|---------|
| `jira:issue_created` | New issue created |
| `jira:issue_updated` | Issue field updated |
| `jira:issue_deleted` | Issue deleted |
| `comment_created` | Comment added |
| `comment_updated` | Comment edited |
| `comment_deleted` | Comment deleted |
| `jira:worklog_updated` | Work logged |

### JQL Filtering

Webhooks support JQL filters to target specific issues:

**Supported Operators:** `=`, `!=`, `IN`, `NOT IN`

**Example Filters:**
```jql
# Only peer review issues
Project = PROJ AND labels = peer-review

# Specific issue types
Project = PROJ AND issuetype IN (Task, Bug)

# Status changes
Project = PROJ AND status CHANGED

# Assigned issues only
Project = PROJ AND assignee != EMPTY
```

### Webhook Payload Structure

**Example: Issue Updated Event**

```json
{
  "timestamp": 1672531200000,
  "webhookEvent": "jira:issue_updated",
  "issue_event_type_name": "issue_updated",
  "user": {
    "self": "https://your-domain.atlassian.net/rest/api/3/user?accountId=...",
    "accountId": "5b10ac8d82e05b22cc7d4ef5",
    "displayName": "Jane Reviewer",
    "active": true
  },
  "issue": {
    "id": "10000",
    "self": "https://your-domain.atlassian.net/rest/api/3/issue/10000",
    "key": "PROJ-123",
    "fields": {
      "summary": "Peer Review: PR #123",
      "status": {
        "name": "In Review",
        "id": "3"
      },
      "assignee": {
        "accountId": "5b10ac8d82e05b22cc7d4ef5",
        "displayName": "Jane Reviewer"
      },
      "labels": ["peer-review", "pr-123"]
    }
  },
  "changelog": {
    "items": [
      {
        "field": "status",
        "fieldtype": "jira",
        "from": "10000",
        "fromString": "To Do",
        "to": "10001",
        "toString": "In Review"
      }
    ]
  }
}
```

### Processing Webhooks

```javascript
// Express.js webhook handler
app.post('/webhooks/jira', async (req, res) => {
  const event = req.body;

  // Acknowledge receipt immediately
  res.status(200).send('OK');

  // Process asynchronously
  try {
    if (event.webhookEvent === 'jira:issue_updated') {
      await handleIssueUpdate(event);
    } else if (event.webhookEvent === 'comment_created') {
      await handleCommentCreated(event);
    }
  } catch (error) {
    console.error('Webhook processing error:', error);
  }
});

async function handleIssueUpdate(event) {
  const { issue, changelog } = event;

  // Check if status changed to "Approved"
  const statusChange = changelog.items.find(
    item => item.field === 'status' && item.toString === 'Approved'
  );

  if (statusChange) {
    // Extract PR number from labels
    const prLabel = issue.fields.labels.find(label => label.startsWith('pr-'));
    const prNumber = prLabel ? prLabel.split('-')[1] : null;

    if (prNumber) {
      // Update GitHub PR status
      await updateGitHubPRStatus(prNumber, 'approved');
    }
  }
}

async function updateGitHubPRStatus(prNumber, status) {
  // Add approved label to PR
  await github.rest.issues.addLabels({
    owner: process.env.GITHUB_OWNER,
    repo: process.env.GITHUB_REPO,
    issue_number: prNumber,
    labels: ['jira-approved']
  });

  // Add comment
  await github.rest.issues.createComment({
    owner: process.env.GITHUB_OWNER,
    repo: process.env.GITHUB_REPO,
    issue_number: prNumber,
    body: '✅ Jira peer review ticket approved!'
  });
}
```

### Webhook Security

**Verify Webhook Source:**

```javascript
function verifyJiraWebhook(req) {
  // Check IP whitelist (Atlassian IP ranges)
  const allowedIPs = [
    '13.52.5.96/28',
    '13.236.8.224/28',
    // ... other Atlassian IP ranges
  ];

  const clientIP = req.ip;
  // Implement IP range checking

  // Optionally: Use webhook secret (if supported)
  const signature = req.headers['x-hub-signature'];
  // Verify signature
}
```

### Webhook Lifecycle Management

**Expiration:**
- Connect apps: 100 webhooks max per app per tenant
- OAuth 2.0 apps: 5 webhooks per app per user per tenant
- Webhooks expire after 30 days of inactivity

**Refresh Webhook:**
```bash
PUT /rest/webhooks/1.0/webhook/{webhookId}/refresh
```

**Delete Webhook:**
```bash
DELETE /rest/webhooks/1.0/webhook/{webhookId}
```

### Retry Behavior

Jira automatically retries failed webhook deliveries:
- **Retries:** Up to 5 attempts
- **Retry Status Codes:** 408, 409, 425, 429, 5xx
- **Retry Delay:** Randomized 5-15 minutes between attempts

**Handle Retries Idempotently:**
```javascript
const processedEvents = new Set(); // Use Redis in production

app.post('/webhooks/jira', async (req, res) => {
  const eventId = req.headers['x-atlassian-webhook-identifier'];

  if (processedEvents.has(eventId)) {
    console.log('Duplicate webhook, skipping');
    return res.status(200).send('OK');
  }

  processedEvents.add(eventId);

  // Process event
  await handleWebhook(req.body);

  res.status(200).send('OK');
});
```

---

## 7. Rate Limiting and Throttling

### 2025-2026 Rate Limit Changes

**Important:** Starting November 22, 2025, Atlassian introduced API token rate limits. Enforcement begins March 2, 2026 for REST APIs, followed by GraphQL APIs in subsequent phases.

### Points-Based Rate Limiting Model

Jira Cloud uses a **points-based system** instead of simple request counting:

- **Base Cost:** 1 point per request
- **Additional Points:** Based on objects affected (e.g., 1 point per issue returned)
- **Calculation:** Points depend on data volume and operation complexity

**Example:**
- `GET /issue/PROJ-123`: 1 point (single issue)
- `GET /search?jql=...` returning 50 issues: 51 points (1 base + 50 issues)

### Rate Limit Tiers

| Tier | Limit | Use Case |
|------|-------|----------|
| Per-user | Varies by plan | Individual user actions |
| Per-tenant | Varies by plan | Shared across all users |
| Per-issue (writes) | Burst protection | Prevent rapid writes to single issue |
| API Token | New limits (2025) | Token-based automation |

### Rate Limit Headers

**Response Headers:**
```
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9985
X-RateLimit-Reset: 1672531200
X-RateLimit-FillRate: 10
Retry-After: 60
```

### Detecting Rate Limits

**HTTP 429 Response:**
```json
{
  "errorMessages": [
    "Rate limit exceeded. Please retry after 60 seconds."
  ],
  "errors": {}
}
```

**Check Status Code:**
```javascript
async function makeJiraRequest(url, options) {
  const response = await fetch(url, options);

  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After');
    throw new RateLimitError(`Rate limit exceeded, retry after ${retryAfter}s`);
  }

  return response;
}
```

### Optimization Strategies

#### 1. Batch Operations

Instead of creating issues one-by-one:

```javascript
// ❌ Bad: Multiple requests
for (const pr of prs) {
  await createJiraIssue(pr);
}

// ✅ Good: Bulk create (if supported) or queue
const queue = new PQueue({ concurrency: 5, interval: 1000 });
await Promise.all(prs.map(pr => queue.add(() => createJiraIssue(pr))));
```

#### 2. Caching

Cache frequently accessed data:

```javascript
// Cache project metadata
const projectCache = new Map();

async function getProjectMeta(projectKey) {
  if (projectCache.has(projectKey)) {
    return projectCache.get(projectKey);
  }

  const meta = await fetchProjectMeta(projectKey);
  projectCache.set(projectKey, meta);
  return meta;
}
```

#### 3. Pagination

Use pagination for large result sets:

```javascript
async function* searchIssues(jql) {
  let startAt = 0;
  const maxResults = 50; // Balance between requests and data volume

  while (true) {
    const response = await fetch(
      `${JIRA_BASE_URL}/rest/api/3/search?jql=${encodeURIComponent(jql)}&startAt=${startAt}&maxResults=${maxResults}`,
      { headers: { 'Authorization': `...` } }
    );

    const data = await response.json();
    yield* data.issues;

    if (startAt + maxResults >= data.total) break;
    startAt += maxResults;
  }
}

// Usage
for await (const issue of searchIssues('project = PROJ')) {
  console.log(issue.key);
}
```

#### 4. Request Deduplication

Avoid redundant requests:

```javascript
const pendingRequests = new Map();

async function deduplicatedRequest(key, requestFn) {
  if (pendingRequests.has(key)) {
    return pendingRequests.get(key);
  }

  const promise = requestFn();
  pendingRequests.set(key, promise);

  try {
    return await promise;
  } finally {
    pendingRequests.delete(key);
  }
}

// Usage
const accountId = await deduplicatedRequest(
  `user:${email}`,
  () => getAccountIdByEmail(email)
);
```

### Jira Data Center Rate Limits

For self-hosted Jira:
- Rate limiting **disabled by default**
- Admins can enable and configure limits
- Separate limits for OAuth 2.0 vs other API requests

### Jira Align Specific Limits

- **Limit:** 600 requests per 60 seconds per IP
- **Response:** 429 Too Many Requests
- **Lockout:** 60 seconds

---

## 8. Error Handling and Retry Patterns

### Common HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Process response |
| 201 | Created | Issue created successfully |
| 204 | No Content | Operation succeeded (e.g., delete) |
| 400 | Bad Request | Fix request payload |
| 401 | Unauthorized | Check credentials |
| 403 | Forbidden | Check permissions |
| 404 | Not Found | Verify resource exists |
| 429 | Rate Limited | Retry after delay |
| 500 | Server Error | Retry with backoff |
| 503 | Service Unavailable | Retry with backoff |

### Retry Strategies

#### 1. Exponential Backoff with Jitter

**Implementation:**
```javascript
async function exponentialBackoff(fn, maxRetries = 4) {
  let attempt = 0;
  const baseDelay = 1000; // 1 second
  const maxDelay = 30000; // 30 seconds

  while (attempt < maxRetries) {
    try {
      return await fn();
    } catch (error) {
      attempt++;

      // Only retry on specific status codes
      if (![408, 409, 425, 429, 500, 502, 503, 504].includes(error.status)) {
        throw error;
      }

      if (attempt >= maxRetries) {
        throw new Error(`Max retries (${maxRetries}) exceeded: ${error.message}`);
      }

      // Calculate delay with exponential backoff
      const exponentialDelay = Math.min(baseDelay * Math.pow(2, attempt), maxDelay);

      // Add jitter (random 0-1000ms) to prevent thundering herd
      const jitter = Math.random() * 1000;
      const delay = exponentialDelay + jitter;

      console.log(`Retry attempt ${attempt} after ${Math.round(delay)}ms`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

// Usage
const issue = await exponentialBackoff(() => createJiraIssue(data));
```

#### 2. Retry-After Header Handling

**Respect server-specified delays:**
```javascript
async function retryWithRetryAfter(fn, maxRetries = 3) {
  let attempt = 0;

  while (attempt < maxRetries) {
    try {
      return await fn();
    } catch (error) {
      attempt++;

      // Check for Retry-After header
      const retryAfter = error.response?.headers?.get('Retry-After');

      if (!retryAfter || attempt >= maxRetries) {
        throw error;
      }

      // Parse Retry-After (can be seconds or HTTP date)
      const delay = parseInt(retryAfter) * 1000 ||
                    (new Date(retryAfter) - new Date());

      console.log(`Rate limited, waiting ${delay}ms before retry`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}
```

#### 3. Circuit Breaker Pattern

**Prevent cascading failures:**
```javascript
class CircuitBreaker {
  constructor(threshold = 5, timeout = 60000) {
    this.failureCount = 0;
    this.threshold = threshold;
    this.timeout = timeout;
    this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
    this.nextAttempt = Date.now();
  }

  async execute(fn) {
    if (this.state === 'OPEN') {
      if (Date.now() < this.nextAttempt) {
        throw new Error('Circuit breaker is OPEN');
      }
      this.state = 'HALF_OPEN';
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
    this.failureCount = 0;
    this.state = 'CLOSED';
  }

  onFailure() {
    this.failureCount++;
    if (this.failureCount >= this.threshold) {
      this.state = 'OPEN';
      this.nextAttempt = Date.now() + this.timeout;
      console.error(`Circuit breaker opened, cooling down for ${this.timeout}ms`);
    }
  }
}

// Usage
const jiraCircuitBreaker = new CircuitBreaker(5, 60000);

async function createIssueWithCircuitBreaker(data) {
  return jiraCircuitBreaker.execute(() => createJiraIssue(data));
}
```

### Idempotency

**Ensure operations can be safely retried:**

```javascript
// Use idempotency key for issue creation
async function createIssueIdempotent(data, idempotencyKey) {
  const cacheKey = `issue:${idempotencyKey}`;

  // Check if already created
  const cached = await redis.get(cacheKey);
  if (cached) {
    return JSON.parse(cached);
  }

  // Create issue
  const issue = await createJiraIssue(data);

  // Cache result
  await redis.set(cacheKey, JSON.stringify(issue), 'EX', 3600);

  return issue;
}

// Usage: Use PR URL as idempotency key
const issue = await createIssueIdempotent(
  issueData,
  `pr:${prData.html_url}`
);
```

### Error Classification

```javascript
class JiraAPIError extends Error {
  constructor(message, status, response) {
    super(message);
    this.status = status;
    this.response = response;
    this.isRetryable = this.determineRetryability();
  }

  determineRetryability() {
    // Retry on rate limits and server errors
    if ([429, 500, 502, 503, 504].includes(this.status)) {
      return true;
    }

    // Don't retry on client errors
    if (this.status >= 400 && this.status < 500) {
      return false;
    }

    return false;
  }
}

async function makeJiraRequest(url, options) {
  const response = await fetch(url, options);

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new JiraAPIError(
      body.errorMessages?.[0] || response.statusText,
      response.status,
      body
    );
  }

  return response.json();
}
```

### Comprehensive Error Handler

```javascript
async function robustJiraRequest(fn, options = {}) {
  const {
    maxRetries = 4,
    baseDelay = 1000,
    maxDelay = 30000,
    onRetry = () => {},
    onError = () => {}
  } = options;

  let attempt = 0;

  while (attempt <= maxRetries) {
    try {
      return await fn();
    } catch (error) {
      attempt++;

      // Log error
      onError(error, attempt);

      // Check if retryable
      if (!error.isRetryable || attempt > maxRetries) {
        console.error(`Non-retryable error or max retries exceeded:`, error);
        throw error;
      }

      // Calculate delay
      let delay;
      const retryAfter = error.response?.headers?.get?.('Retry-After');

      if (retryAfter) {
        delay = parseInt(retryAfter) * 1000;
      } else {
        const exponentialDelay = Math.min(baseDelay * Math.pow(2, attempt - 1), maxDelay);
        const jitter = Math.random() * 1000;
        delay = exponentialDelay + jitter;
      }

      console.log(`Retrying request (attempt ${attempt}/${maxRetries}) after ${Math.round(delay)}ms`);
      onRetry(attempt, delay);

      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

// Usage
const issue = await robustJiraRequest(
  () => createJiraIssue(data),
  {
    maxRetries: 4,
    onRetry: (attempt, delay) => {
      console.log(`Retry ${attempt}, waiting ${delay}ms`);
    },
    onError: (error, attempt) => {
      console.error(`Attempt ${attempt} failed:`, error.message);
    }
  }
);
```

---

## 9. Best Practices

### Ticket Templates

#### Standard Fields for Peer Review Tickets

```javascript
const peerReviewTemplate = {
  project: { key: "PROJ" },
  issuetype: { name: "Peer Review" }, // Or "Task"
  summary: "", // Populated dynamically
  description: {}, // ADF format
  labels: ["peer-review"],
  priority: { name: "Medium" },
  components: [{ name: "Code Review" }]
};
```

#### Dynamic Template Function

```javascript
function createPeerReviewTicket(prData, reviewerAccountId) {
  return {
    fields: {
      ...peerReviewTemplate,
      summary: `Peer Review: ${prData.title}`,
      description: createReviewDescription(prData),
      labels: ["peer-review", `pr-${prData.number}`, prData.base.ref],
      assignee: { accountId: reviewerAccountId },
      // Custom fields
      customfield_10001: prData.html_url, // PR URL
      customfield_10002: prData.user.login, // PR Author
      customfield_10003: { value: prData.base.ref } // Target Branch
    }
  };
}

function createReviewDescription(prData) {
  return {
    type: "doc",
    version: 1,
    content: [
      {
        type: "heading",
        attrs: { level: 2 },
        content: [{ type: "text", text: "Pull Request Information" }]
      },
      {
        type: "bulletList",
        content: [
          createListItem(`PR Number: #${prData.number}`),
          createListItem(`Author: ${prData.user.login}`),
          createListItem(`Branch: ${prData.head.ref} → ${prData.base.ref}`),
          createListItem(`Files Changed: ${prData.changed_files}`),
          createListItem(`Additions: +${prData.additions}, Deletions: -${prData.deletions}`)
        ]
      },
      {
        type: "heading",
        attrs: { level: 2 },
        content: [{ type: "text", text: "Description" }]
      },
      {
        type: "paragraph",
        content: [{ type: "text", text: prData.body || "No description provided." }]
      },
      {
        type: "heading",
        attrs: { level: 2 },
        content: [{ type: "text", text: "Review Checklist" }]
      },
      {
        type: "taskList",
        content: [
          createTaskItem("Code follows project conventions"),
          createTaskItem("Tests are included and passing"),
          createTaskItem("Documentation is updated"),
          createTaskItem("No security vulnerabilities introduced"),
          createTaskItem("Performance impact assessed")
        ]
      },
      {
        type: "paragraph",
        content: [
          { type: "text", text: "View PR: " },
          {
            type: "text",
            text: prData.html_url,
            marks: [{ type: "link", attrs: { href: prData.html_url } }]
          }
        ]
      }
    ]
  };
}

function createListItem(text) {
  return {
    type: "listItem",
    content: [
      {
        type: "paragraph",
        content: [{ type: "text", text }]
      }
    ]
  };
}

function createTaskItem(text) {
  return {
    type: "taskItem",
    attrs: { state: "TODO" },
    content: [
      {
        type: "paragraph",
        content: [{ type: "text", text }]
      }
    ]
  };
}
```

### Custom Fields Configuration

#### Identifying Custom Field IDs

```bash
# Get all fields
GET /rest/api/3/field

# Get field configuration for issue type
GET /rest/api/3/issue/createmeta/{projectKey}/issuetypes/{issueTypeId}
```

#### Example: Custom Fields for Peer Review

```javascript
// Field mapping (update with your custom field IDs)
const CUSTOM_FIELDS = {
  PR_URL: 'customfield_10001',
  PR_AUTHOR: 'customfield_10002',
  TARGET_BRANCH: 'customfield_10003',
  REVIEW_STATUS: 'customfield_10004',
  CODE_QUALITY_SCORE: 'customfield_10005'
};

// Include in issue creation
const issueData = {
  fields: {
    // ... standard fields
    [CUSTOM_FIELDS.PR_URL]: prData.html_url,
    [CUSTOM_FIELDS.PR_AUTHOR]: prData.user.login,
    [CUSTOM_FIELDS.TARGET_BRANCH]: { value: prData.base.ref },
    [CUSTOM_FIELDS.REVIEW_STATUS]: { value: "Pending" }
  }
};
```

### Labels and Components Strategy

**Labels for Filtering:**
```javascript
const labels = [
  "peer-review",           // All peer review tickets
  `pr-${prData.number}`,   // Specific PR
  prData.base.ref,         // Target branch (main, develop)
  `author-${prData.user.login}`, // PR author
  ...prData.labels.map(l => l.name) // GitHub labels
];
```

**Components for Organization:**
```javascript
const components = [
  { name: "Code Review" },
  { name: prData.base.repo.name } // Repository name
];
```

### Workflow States

**Recommended Status Workflow:**
1. **To Do** → Ticket created, awaiting review
2. **In Review** → Reviewer actively reviewing
3. **Feedback Provided** → Comments/changes requested
4. **Approved** → Review approved
5. **Closed** → PR merged or closed

**Status Transitions via API:**
```javascript
async function transitionIssue(issueKey, transitionName) {
  // Get available transitions
  const transitionsResponse = await fetch(
    `${JIRA_BASE_URL}/rest/api/3/issue/${issueKey}/transitions`,
    { headers: { 'Authorization': `...` } }
  );
  const { transitions } = await transitionsResponse.json();

  // Find transition by name
  const transition = transitions.find(t => t.name === transitionName);

  if (!transition) {
    throw new Error(`Transition "${transitionName}" not found`);
  }

  // Execute transition
  await fetch(
    `${JIRA_BASE_URL}/rest/api/3/issue/${issueKey}/transitions`,
    {
      method: 'POST',
      headers: {
        'Authorization': `...`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        transition: { id: transition.id }
      })
    }
  );
}

// Usage
await transitionIssue('PROJ-123', 'In Review');
```

### Security Best Practices

#### 1. Credential Management

```javascript
// ❌ Bad: Hardcoded credentials
const apiToken = "ATATT3xFfGF0...";

// ✅ Good: Environment variables
const apiToken = process.env.JIRA_API_TOKEN;

// ✅ Better: Secret manager
const apiToken = await secretsManager.getSecret('jira-api-token');
```

#### 2. Least Privilege Principle

Create dedicated service account for automation:
- Grant only necessary permissions (Create Issues, Assign Issues)
- Limit to specific projects
- Separate token per integration

#### 3. Audit Logging

```javascript
async function auditedJiraRequest(action, data) {
  const startTime = Date.now();

  try {
    const result = await makeJiraRequest(action, data);

    await logAuditEvent({
      action,
      status: 'success',
      duration: Date.now() - startTime,
      issueKey: result.key
    });

    return result;
  } catch (error) {
    await logAuditEvent({
      action,
      status: 'failure',
      duration: Date.now() - startTime,
      error: error.message
    });

    throw error;
  }
}
```

### Performance Optimization

#### 1. Request Batching

```javascript
class JiraRequestBatcher {
  constructor(batchSize = 10, batchDelay = 1000) {
    this.queue = [];
    this.batchSize = batchSize;
    this.batchDelay = batchDelay;
    this.timer = null;
  }

  async add(requestFn) {
    return new Promise((resolve, reject) => {
      this.queue.push({ requestFn, resolve, reject });

      if (this.queue.length >= this.batchSize) {
        this.flush();
      } else if (!this.timer) {
        this.timer = setTimeout(() => this.flush(), this.batchDelay);
      }
    });
  }

  async flush() {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }

    const batch = this.queue.splice(0, this.batchSize);

    // Process batch in parallel with concurrency limit
    const results = await Promise.allSettled(
      batch.map(({ requestFn }) => requestFn())
    );

    // Resolve/reject individual promises
    results.forEach((result, index) => {
      if (result.status === 'fulfilled') {
        batch[index].resolve(result.value);
      } else {
        batch[index].reject(result.reason);
      }
    });
  }
}

// Usage
const batcher = new JiraRequestBatcher();

async function createIssue(data) {
  return batcher.add(() => makeJiraRequest('/rest/api/3/issue', {
    method: 'POST',
    body: JSON.stringify({ fields: data })
  }));
}
```

#### 2. Connection Pooling

```javascript
// Use HTTP agent with keep-alive
const https = require('https');

const httpsAgent = new https.Agent({
  keepAlive: true,
  maxSockets: 50
});

async function makeJiraRequest(url, options) {
  return fetch(url, {
    ...options,
    agent: httpsAgent
  });
}
```

### Monitoring and Observability

```javascript
// Metrics tracking
const metrics = {
  issuesCreated: 0,
  apiErrors: 0,
  rateLimits: 0,
  averageResponseTime: 0
};

async function instrumentedRequest(fn) {
  const startTime = Date.now();

  try {
    const result = await fn();
    metrics.issuesCreated++;
    updateAverageResponseTime(Date.now() - startTime);
    return result;
  } catch (error) {
    if (error.status === 429) {
      metrics.rateLimits++;
    } else {
      metrics.apiErrors++;
    }
    throw error;
  }
}

function updateAverageResponseTime(duration) {
  metrics.averageResponseTime =
    (metrics.averageResponseTime * (metrics.issuesCreated - 1) + duration) /
    metrics.issuesCreated;
}

// Expose metrics endpoint
app.get('/metrics', (req, res) => {
  res.json(metrics);
});
```

---

## 10. Implementation Examples

### Complete GitHub Action Workflow

```yaml
# .github/workflows/jira-peer-review.yml
name: Create Jira Peer Review Ticket

on:
  pull_request:
    types: [opened, ready_for_review]

jobs:
  create-jira-ticket:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Create Jira Peer Review Ticket
        uses: actions/github-script@v6
        env:
          JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          JIRA_PROJECT_KEY: ${{ secrets.JIRA_PROJECT_KEY }}
        with:
          script: |
            const { createPeerReviewTicket } = require('./scripts/jira-automation.js');

            const prData = context.payload.pull_request;
            const reviewerEmail = 'reviewer@example.com'; // Determine reviewer logic

            try {
              const issue = await createPeerReviewTicket(prData, reviewerEmail);
              console.log(`Created Jira ticket: ${issue.key}`);

              // Add comment to PR
              await github.rest.issues.createComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: prData.number,
                body: `Jira peer review ticket created: [${issue.key}](${process.env.JIRA_BASE_URL}/browse/${issue.key})`
              });
            } catch (error) {
              core.setFailed(`Failed to create Jira ticket: ${error.message}`);
            }
```

### Node.js Automation Script

```javascript
// scripts/jira-automation.js
const fetch = require('node-fetch');

const JIRA_BASE_URL = process.env.JIRA_BASE_URL;
const JIRA_EMAIL = process.env.JIRA_EMAIL;
const JIRA_API_TOKEN = process.env.JIRA_API_TOKEN;
const JIRA_PROJECT_KEY = process.env.JIRA_PROJECT_KEY;

const authHeader = `Basic ${Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64')}`;

async function getAccountIdByEmail(email) {
  const response = await fetch(
    `${JIRA_BASE_URL}/rest/api/3/user/search?query=${encodeURIComponent(email)}`,
    {
      headers: { 'Authorization': authHeader }
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to find user: ${response.statusText}`);
  }

  const users = await response.json();
  return users.length > 0 ? users[0].accountId : null;
}

async function createJiraIssue(data) {
  const response = await fetch(
    `${JIRA_BASE_URL}/rest/api/3/issue`,
    {
      method: 'POST',
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ fields: data })
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Failed to create issue: ${JSON.stringify(error)}`);
  }

  return await response.json();
}

async function linkPRToJira(issueKey, prData) {
  const globalId = `system=github&id=${prData.base.repo.full_name}/pull/${prData.number}`;

  const linkData = {
    globalId,
    relationship: "Pull Request",
    object: {
      url: prData.html_url,
      title: `PR #${prData.number}: ${prData.title}`,
      icon: {
        url16x16: "https://github.com/favicon.ico",
        title: "GitHub"
      },
      status: {
        resolved: false,
        icon: {
          url16x16: "https://github.com/favicon.ico",
          title: "Open"
        }
      }
    }
  };

  const response = await fetch(
    `${JIRA_BASE_URL}/rest/api/3/issue/${issueKey}/remotelink`,
    {
      method: 'POST',
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(linkData)
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to link PR: ${response.statusText}`);
  }
}

async function createPeerReviewTicket(prData, reviewerEmail) {
  // 1. Get reviewer's account ID
  const reviewerAccountId = await getAccountIdByEmail(reviewerEmail);

  if (!reviewerAccountId) {
    throw new Error(`Reviewer ${reviewerEmail} not found in Jira`);
  }

  // 2. Create issue
  const issueData = {
    project: { key: JIRA_PROJECT_KEY },
    issuetype: { name: "Task" },
    summary: `Peer Review: ${prData.title}`,
    description: createDescription(prData),
    labels: ["peer-review", `pr-${prData.number}`],
    assignee: { accountId: reviewerAccountId }
  };

  const issue = await createJiraIssue(issueData);

  // 3. Link PR to Jira
  await linkPRToJira(issue.key, prData);

  return issue;
}

function createDescription(prData) {
  return {
    type: "doc",
    version: 1,
    content: [
      {
        type: "heading",
        attrs: { level: 2 },
        content: [{ type: "text", text: "Pull Request Details" }]
      },
      {
        type: "bulletList",
        content: [
          {
            type: "listItem",
            content: [{
              type: "paragraph",
              content: [{ type: "text", text: `Author: ${prData.user.login}` }]
            }]
          },
          {
            type: "listItem",
            content: [{
              type: "paragraph",
              content: [{ type: "text", text: `Branch: ${prData.head.ref} → ${prData.base.ref}` }]
            }]
          }
        ]
      },
      {
        type: "paragraph",
        content: [
          { type: "text", text: "View PR: " },
          {
            type: "text",
            text: prData.html_url,
            marks: [{ type: "link", attrs: { href: prData.html_url } }]
          }
        ]
      }
    ]
  };
}

module.exports = {
  createPeerReviewTicket,
  getAccountIdByEmail,
  createJiraIssue,
  linkPRToJira
};
```

### Webhook Handler (Express.js)

```javascript
// server.js
const express = require('express');
const app = express();

app.use(express.json());

app.post('/webhooks/jira', async (req, res) => {
  // Acknowledge immediately
  res.status(200).send('OK');

  const event = req.body;

  try {
    if (event.webhookEvent === 'jira:issue_updated') {
      await handleIssueUpdate(event);
    }
  } catch (error) {
    console.error('Webhook processing error:', error);
  }
});

async function handleIssueUpdate(event) {
  const { issue, changelog } = event;

  // Check if status changed
  const statusChange = changelog.items.find(item => item.field === 'status');

  if (!statusChange) return;

  // Extract PR number from labels
  const prLabel = issue.fields.labels.find(label => label.startsWith('pr-'));
  if (!prLabel) return;

  const prNumber = parseInt(prLabel.split('-')[1]);

  // Update GitHub PR based on Jira status
  if (statusChange.toString === 'Approved') {
    await updateGitHubPR(prNumber, 'approved');
  } else if (statusChange.toString === 'Feedback Provided') {
    await updateGitHubPR(prNumber, 'changes_requested');
  }
}

async function updateGitHubPR(prNumber, status) {
  const { Octokit } = require('@octokit/rest');
  const octokit = new Octokit({ auth: process.env.GITHUB_TOKEN });

  const owner = process.env.GITHUB_OWNER;
  const repo = process.env.GITHUB_REPO;

  if (status === 'approved') {
    await octokit.issues.createComment({
      owner,
      repo,
      issue_number: prNumber,
      body: '✅ Peer review approved in Jira!'
    });

    await octokit.issues.addLabels({
      owner,
      repo,
      issue_number: prNumber,
      labels: ['jira-approved']
    });
  } else if (status === 'changes_requested') {
    await octokit.issues.createComment({
      owner,
      repo,
      issue_number: prNumber,
      body: '📝 Feedback provided in Jira, please review.'
    });
  }
}

app.listen(3000, () => {
  console.log('Webhook server listening on port 3000');
});
```

---

## 11. Sources

### Jira REST API Documentation
- [The Jira Cloud platform REST API - Issue Fields](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-fields/)
- [Jira REST API examples](https://developer.atlassian.com/server/jira/platform/jira-rest-api-examples/)
- [JIRA REST API Example Create Issue](https://developer.atlassian.com/server/jira/platform/jira-rest-api-example-create-issue-7897248/)
- [JIRA Create Issue REST API – InfallibleTechie](https://www.infallibletechie.com/2025/06/jira-create-issue-rest-api.html)
- [Discovering Meta Data for Creating Issues](https://developer.atlassian.com/server/jira/platform/jira-rest-api-example-discovering-meta-data-for-creating-issues-6291669/)

### Auto-Assignment
- [Edit Assignee Using Jira REST API and User's Email](https://community.atlassian.com/t5/Jira-Software-questions/Edit-Assignee-Using-Jira-REST-API-and-User-s-Email/qaq-p/1515604)
- [Set assignee through REST API](https://community.atlassian.com/t5/Jira-questions/Set-assignee-through-REST-API/qaq-p/1005587)
- [Create issue via REST API with assignee's email address?](https://community.atlassian.com/forums/Jira-questions/Create-issue-via-REST-API-with-assignee-s-email-address/qaq-p/1497700)
- [API to get Account ID from Email Address?](https://community.developer.atlassian.com/t/api-to-get-account-id-from-email-address/56847)

### PR-Jira Linking
- [Connect GitHub Pull Request with Jira Issue | Port](https://docs.port.io/guides/all/connect-github-pr-with-jira-issue/)
- [Link GitHub development information to Jira work items | Atlassian Support](https://support.atlassian.com/jira-cloud-administration/docs/use-the-github-for-jira-app/)
- [How to use REST API to add remote links in JIRA issues](https://support.atlassian.com/jira/kb/how-to-use-rest-api-to-add-remote-links-in-jira-issues/)
- [Jira REST API for Remote Issue Links](https://developer.atlassian.com/server/jira/platform/jira-rest-api-for-remote-issue-links/)
- [Creating Remote Issue Links](https://developer.atlassian.com/server/jira/platform/creating-remote-issue-links/)
- [The Jira Cloud platform REST API - Issue Remote Links](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-remote-links/)

### Webhooks
- [Webhooks - Jira Server](https://developer.atlassian.com/server/jira/platform/webhooks/)
- [Jira Webhooks: Complete Guide with Payload Examples [2025]](https://inventivehq.com/blog/jira-webhooks-guide)
- [Manage webhooks | Atlassian Support](https://support.atlassian.com/jira-cloud-administration/docs/manage-webhooks/)
- [The Jira Cloud platform REST API - Webhooks](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-webhooks/)
- [Webhooks - Jira Cloud platform](https://developer.atlassian.com/cloud/jira/platform/webhooks/)

### Rate Limiting
- [Rate limiting](https://developer.atlassian.com/cloud/jira/platform/rate-limiting/)
- [API Token Rate Limiting - Announcements](https://community.developer.atlassian.com/t/api-token-rate-limiting/92292)
- [Scaling responsibly: evolving our API rate limits](https://www.atlassian.com/blog/platform/evolving-api-rate-limits)
- [Are there rate limits for JIRA Cloud APIs?](https://community.developer.atlassian.com/t/are-there-rate-limits-for-jira-cloud-apis/4317)

### Error Handling
- [Rate limiting](https://developer.atlassian.com/cloud/jira/platform/rate-limiting/)
- [jira.resilientsession - jira 3.10.6.dev6 documentation](https://jira.readthedocs.io/_modules/jira/resilientsession.html)
- [Rate limiting Response handling pseudo code](https://community.developer.atlassian.com/t/rate-limiting-response-handling-pseudo-code/53019)

### Best Practices
- [Issue Templates in Jira: Guide 2026](https://community.atlassian.com/forums/App-Central-articles/Issue-Templates-in-Jira-Guide-2026/ba-p/3034243)
- [Best Practices for Creating a Jira Issue With Templates](https://stiltsoft.com/blog/best-practices-for-creating-a-jira-issue-with-templates/)
- [Jira custom fields: The complete guide 2025](https://blog.isostech.com/jira-custom-fields-the-complete-guide-2025)
- [Jira Best Practices: Projects, Statuses, Custom Fields, and Apps Made Easy](https://blog.isostech.com/best-practices-for-jira-software-governance-projects-statuses-custom-fields-and-apps)

---

## Conclusion

This research document provides a comprehensive foundation for implementing automated Jira ticket creation triggered by GitHub Pull Requests with auto-assignment capabilities. Key takeaways:

1. **Authentication**: Use API tokens stored securely for automation
2. **Auto-Assignment**: Requires Account ID lookup from email addresses
3. **PR Linking**: Implement bidirectional linking using Remote Links API
4. **Webhooks**: Enable real-time Jira → GitHub status synchronization
5. **Rate Limiting**: Implement exponential backoff with jitter and respect Retry-After headers
6. **Error Handling**: Use circuit breakers and idempotent operations
7. **Best Practices**: Use templates, custom fields, and proper monitoring

The implementation examples provide production-ready code for GitHub Actions, Node.js scripts, and webhook handlers that can be adapted to specific organizational needs.
