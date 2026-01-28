# Jira Integration Agent - Enhancement Specification

**Created**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**Enhancement Version**: 2.0
**Base Specification**: jira_integration_agent_spec.md

---

## Executive Summary

This document specifies enhancements to the existing Jira Integration Agent to support:
1. **Auto-assignment to PR authors** using email/GitHub username lookup
2. **Rich context in tickets** including agent findings, line numbers, and remediation guidance
3. **Reusable Jira Skill** for ticket operations across all agents

These enhancements maintain the 10-second SLA while improving ticket quality, traceability, and automation completeness.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Enhancement Overview](#enhancement-overview)
3. [Auto-Assignment Implementation](#auto-assignment-implementation)
4. [Rich Context Enhancement](#rich-context-enhancement)
5. [Jira Skill Specification](#jira-skill-specification)
6. [Enhanced Input Schema](#enhanced-input-schema)
7. [Enhanced Output Schema](#enhanced-output-schema)
8. [Error Handling Updates](#error-handling-updates)
9. [Implementation Guidance](#implementation-guidance)
10. [Success Criteria](#success-criteria)

---

## 1. Current State Analysis

### What the Agent Already Does

**Existing Capabilities**:
- Creates Jira tickets for CODE_VIOLATION, LLD_DEVIATION, PATTERN_REJECTION
- Links tickets to GitHub PRs (bidirectional)
- Auto-populates standard fields (project, issue type, priority, labels)
- Implements retry logic via SQS queue for Jira unavailability
- Maintains 10-second SLA for ticket creation
- Provides audit trail via CloudWatch logs

**Current Assignment Logic**:
- Assigns to PR author (by string username)
- Falls back to component owner if author not found
- Falls back to architecture team lead if component owner not configured

**Current Ticket Context**:
- PR number, URL, repository, author
- Issue type (violation/deviation/rejection)
- Severity level
- Basic issue description
- Source agent name

### What Needs to Change

**Limitations in Current Implementation**:

1. **Assignment Issues**:
   - Uses string usernames instead of Jira Account IDs
   - Post-GDPR Jira API requires Account IDs for assignment
   - No email-based lookup mechanism
   - No caching of user lookups (repeated API calls)
   - No fallback strategy if user not found in Jira

2. **Context Issues**:
   - Limited issue details (no line numbers in structured format)
   - No agent-specific findings context
   - No remediation guidance
   - No workflow run link for traceability
   - Generic descriptions that require PR investigation

3. **Reusability Issues**:
   - Jira logic embedded in agent (not reusable)
   - Other agents cannot create tickets independently
   - No skill abstraction for ticket operations

---

## 2. Enhancement Overview

### Enhancement 1: Auto-Assignment to PR Authors

**Objective**: Enable automatic assignment of Jira tickets to PR authors using their GitHub email or username, with intelligent fallback strategies.

**Key Features**:
- Lookup Jira Account ID from GitHub email/username
- Cache user lookups to reduce API calls (24-hour TTL)
- Multi-tier fallback strategy if user not found
- Support for organization-wide email domain mapping

**Benefits**:
- Correct assignment to actual developers (not generic accounts)
- Faster ticket resolution (assigned to right person immediately)
- GDPR-compliant (uses Account IDs)
- Reduced API calls (caching)

### Enhancement 2: Rich Context in Tickets

**Objective**: Provide comprehensive context in Jira tickets to enable action without PR investigation.

**Key Features**:
- Include which agent detected the issue (with agent version)
- Include specific findings with file paths and line numbers
- Include remediation guidance (how to fix)
- Include workflow run link for full logs
- Structured data format for parsing

**Benefits**:
- Developers can act immediately without investigating PR
- Complete audit trail for compliance
- Metrics on agent effectiveness
- Better knowledge base for pattern learning

### Enhancement 3: Jira Skill Creation

**Objective**: Extract Jira operations into a reusable skill for use by any agent.

**Key Features**:
- Reusable skill: `jira_ticket_skill`
- Operations: create_ticket, assign_ticket, link_pr, add_comment
- Standard input/output schemas
- Encapsulated error handling and retry logic

**Benefits**:
- DRY principle (Don't Repeat Yourself)
- Consistent Jira behavior across all agents
- Centralized rate limiting and caching
- Easier testing and maintenance

---

## 3. Auto-Assignment Implementation

### 3.1 User Lookup Strategy

**Primary Lookup: Email Address**

```
Input: pr_author_email (e.g., "developer1@company.com")
↓
Call Jira API: GET /rest/api/3/user/search?query={email}
↓
Response: accountId or empty array
```

**Secondary Lookup: GitHub Username Mapping**

```
Input: pr_author_github_username (e.g., "dev1")
↓
Check organization mapping table (DynamoDB):
  Key: github_username
  Value: jira_email
↓
If found: Use email for Jira lookup
If not found: Proceed to fallback
```

**Organization Email Domain Mapping**

If email not provided but username available:
```
github_username: "dev1"
↓
Apply organization email pattern: "{username}@company.com"
↓
Try Jira lookup with constructed email
```

### 3.2 Lookup Flow Diagram

```
START
  │
  ├─ Has pr_author_email?
  │  ├─ YES → Lookup by email
  │  │         ├─ Found? → Assign to Account ID ✓
  │  │         └─ Not found → Continue to fallback
  │  │
  │  └─ NO → Has pr_author_github_username?
  │           ├─ YES → Check username mapping table
  │           │         ├─ Mapped? → Lookup by mapped email
  │           │         │             ├─ Found? → Assign ✓
  │           │         │             └─ Not found → Fallback
  │           │         │
  │           │         └─ Not mapped → Try email pattern
  │           │                        ├─ Found? → Assign ✓
  │           │                        └─ Not found → Fallback
  │           │
  │           └─ NO → Proceed directly to fallback
  │
  └─ FALLBACK STRATEGY:
      1. Component owner (from team config)
      2. Architecture team lead (default)
      3. Unassigned (with CloudWatch alarm)
```

### 3.3 Caching Strategy

**Cache Structure**:
```javascript
{
  "cache_key": "email:developer1@company.com",
  "account_id": "5b10ac8d82e05b22cc7d4ef5",
  "display_name": "Developer One",
  "timestamp": 1706440815000,
  "ttl": 86400000  // 24 hours in ms
}
```

**Cache Implementation**:
- **Storage**: Redis or DynamoDB with TTL
- **Key Format**: `user:{email}` or `user:gh:{username}`
- **TTL**: 24 hours (configurable)
- **Invalidation**: Manual API or TTL expiry
- **Cache Miss**: API lookup + cache store

**Cache Hit Ratio Target**: >90% (assuming same users create PRs regularly)

### 3.4 Fallback Strategy

**Tier 1: Component Owner**
- Lookup from team configuration (DynamoDB table)
- Table schema:
  ```json
  {
    "repository": "order-service",
    "component": "payment-module",
    "owner_email": "team-lead1@company.com",
    "owner_account_id": "cached_or_lookup"
  }
  ```

**Tier 2: Architecture Team Lead**
- Default fallback from configuration
- Environment variable: `JIRA_DEFAULT_ASSIGNEE_ACCOUNT_ID`

**Tier 3: Unassigned**
- If all lookups fail, create ticket unassigned
- Add comment: "Auto-assignment failed: PR author not found in Jira"
- Create CloudWatch alarm for investigation
- Add label: `auto-assignment-failed`

### 3.5 Assignment Method Tracking

Track how assignment was performed for metrics and debugging:

```javascript
{
  "assignment_method": "direct",  // or "fallback_component", "fallback_default", "unassigned"
  "assignee_account_id": "5b10ac8d82e05b22cc7d4ef5",
  "lookup_attempts": [
    {
      "method": "email_lookup",
      "input": "developer1@company.com",
      "result": "success",
      "duration_ms": 120
    }
  ]
}
```

---

## 4. Rich Context Enhancement

### 4.1 Enhanced Ticket Description Structure

**New Atlassian Document Format (ADF) Structure**:

```json
{
  "type": "doc",
  "version": 1,
  "content": [
    {
      "type": "panel",
      "attrs": { "panelType": "info" },
      "content": [
        {
          "type": "paragraph",
          "content": [
            { "type": "text", "text": "Automated detection by " },
            { "type": "text", "text": "Code Best Practises Agent v2.1", "marks": [{"type": "strong"}] },
            { "type": "text", "text": " | Workflow: " },
            {
              "type": "text",
              "text": "View Full Logs",
              "marks": [{
                "type": "link",
                "attrs": { "href": "https://github.com/org/repo/actions/runs/12345" }
              }]
            }
          ]
        }
      ]
    },
    {
      "type": "heading",
      "attrs": { "level": 2 },
      "content": [{ "type": "text", "text": "Issue Summary" }]
    },
    {
      "type": "bulletList",
      "content": [
        {
          "type": "listItem",
          "content": [{
            "type": "paragraph",
            "content": [{ "type": "text", "text": "PR: #123 | Repository: order-service" }]
          }]
        },
        {
          "type": "listItem",
          "content": [{
            "type": "paragraph",
            "content": [{ "type": "text", "text": "Author: developer1 | Severity: MEDIUM" }]
          }]
        },
        {
          "type": "listItem",
          "content": [{
            "type": "paragraph",
            "content": [{ "type": "text", "text": "Issues Detected: 2 violations" }]
          }]
        }
      ]
    },
    {
      "type": "heading",
      "attrs": { "level": 2 },
      "content": [{ "type": "text", "text": "Findings" }]
    },
    {
      "type": "heading",
      "attrs": { "level": 3 },
      "content": [{ "type": "text", "text": "Finding 1: Naming Convention Violation" }]
    },
    {
      "type": "table",
      "content": [
        {
          "type": "tableRow",
          "content": [
            { "type": "tableHeader", "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "Property" }] }] },
            { "type": "tableHeader", "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "Value" }] }] }
          ]
        },
        {
          "type": "tableRow",
          "content": [
            { "type": "tableCell", "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "File" }] }] },
            { "type": "tableCell", "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "src/main/java/OrderService.java" }] }] }
          ]
        },
        {
          "type": "tableRow",
          "content": [
            { "type": "tableCell", "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "Line" }] }] },
            { "type": "tableCell", "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "45" }] }] }
          ]
        },
        {
          "type": "tableRow",
          "content": [
            { "type": "tableCell", "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "Pattern" }] }] },
            { "type": "tableCell", "content": [{ "type": "paragraph", "content": [{ "type": "text", "text": "PATTERN-001: Java Naming Conventions" }] }] }
          ]
        }
      ]
    },
    {
      "type": "paragraph",
      "content": [
        { "type": "text", "text": "Issue: ", "marks": [{"type": "strong"}] },
        { "type": "text", "text": "Method name 'get_order()' violates camelCase convention" }
      ]
    },
    {
      "type": "codeBlock",
      "attrs": { "language": "java" },
      "content": [
        { "type": "text", "text": "// Current code (line 45):\npublic Order get_order(String id) { ... }" }
      ]
    },
    {
      "type": "panel",
      "attrs": { "panelType": "success" },
      "content": [
        {
          "type": "paragraph",
          "content": [
            { "type": "text", "text": "Remediation: ", "marks": [{"type": "strong"}] },
            { "type": "text", "text": "Rename method to follow camelCase convention" }
          ]
        }
      ]
    },
    {
      "type": "codeBlock",
      "attrs": { "language": "java" },
      "content": [
        { "type": "text", "text": "// Corrected code:\npublic Order getOrder(String id) { ... }" }
      ]
    },
    {
      "type": "paragraph",
      "content": [
        { "type": "text", "text": "Pattern Reference: " },
        {
          "type": "text",
          "text": "PATTERN-001",
          "marks": [{
            "type": "link",
            "attrs": { "href": "https://confluence.company.com/patterns/PATTERN-001" }
          }]
        }
      ]
    },
    {
      "type": "rule"
    },
    {
      "type": "heading",
      "attrs": { "level": 2 },
      "content": [{ "type": "text", "text": "Action Required" }]
    },
    {
      "type": "bulletList",
      "content": [
        {
          "type": "listItem",
          "content": [{
            "type": "paragraph",
            "content": [{ "type": "text", "text": "Fix all 2 violations in the PR" }]
          }]
        },
        {
          "type": "listItem",
          "content": [{
            "type": "paragraph",
            "content": [{ "type": "text", "text": "Verify fixes pass automated validation" }]
          }]
        },
        {
          "type": "listItem",
          "content": [{
            "type": "paragraph",
            "content": [{ "type": "text", "text": "Request re-review after fixes" }]
          }]
        }
      ]
    }
  ]
}
```

### 4.2 Agent-Specific Context

**For Code Best Practises Agent**:
```javascript
{
  "agent_info": {
    "name": "Code Best Practises Agent",
    "version": "2.1.0",
    "detection_time": "2026-01-28T10:25:30Z",
    "analysis_duration_ms": 3400
  },
  "findings": [
    {
      "finding_id": "CBP-001",
      "type": "NAMING_CONVENTION_VIOLATION",
      "severity": "MEDIUM",
      "file": "src/main/java/OrderService.java",
      "line_start": 45,
      "line_end": 45,
      "code_snippet": "public Order get_order(String id) { ... }",
      "description": "Method name 'get_order()' violates camelCase convention",
      "pattern_id": "PATTERN-001",
      "pattern_url": "https://confluence.company.com/patterns/PATTERN-001",
      "remediation": {
        "description": "Rename method to follow camelCase convention",
        "suggested_fix": "public Order getOrder(String id) { ... }",
        "effort_estimate": "5 minutes"
      }
    }
  ]
}
```

**For LLD Alignment Review Agent**:
```javascript
{
  "agent_info": {
    "name": "LLD Alignment Review Agent",
    "version": "1.5.2",
    "detection_time": "2026-01-28T10:26:15Z"
  },
  "findings": [
    {
      "finding_id": "LLD-001",
      "type": "ARCHITECTURAL_DEVIATION",
      "severity": "CRITICAL",
      "lld_section": "Section 5.2 - PaymentProcessor",
      "lld_document_url": "https://confluence.company.com/lld/payment-service#section-5.2",
      "lld_version": "2.3",
      "file": "src/main/java/PaymentProcessor.java",
      "line_start": 78,
      "line_end": 95,
      "expected_pattern": "Retry Pattern (max 3 retries with exponential backoff)",
      "actual_implementation": "Circuit Breaker pattern",
      "deviation_reason": "Different resilience pattern used",
      "impact": "Conflicts with centralized resilience service configuration",
      "remediation": {
        "description": "Replace Circuit Breaker with Retry Pattern as specified in LLD",
        "suggested_approach": "Use Spring Retry with @Retryable annotation",
        "alternative": "Request architectural approval to update LLD if Circuit Breaker is preferred",
        "effort_estimate": "2-4 hours"
      }
    }
  ]
}
```

**For Pattern Matching Agent**:
```javascript
{
  "agent_info": {
    "name": "Pattern Matching Agent",
    "version": "3.0.1",
    "detection_time": "2026-01-28T10:27:00Z"
  },
  "findings": [
    {
      "finding_id": "PM-001",
      "type": "PATTERN_REJECTION",
      "severity": "HIGH",
      "pattern_candidate": "Redis Distributed Lock Pattern",
      "file": "src/main/java/OrderLockService.java",
      "line_start": 34,
      "line_end": 89,
      "rejection_reason": "Pattern introduces tight coupling with Redis infrastructure",
      "reviewer_comments": "This creates a hard dependency on Redis. Consider using database-based locking or abstract the locking mechanism.",
      "architectural_concerns": [
        "Tight coupling with specific infrastructure (Redis)",
        "No abstraction layer for lock provider",
        "Difficult to test without Redis instance"
      ],
      "remediation": {
        "description": "Abstract locking mechanism behind an interface",
        "suggested_approach": "Create LockProvider interface with Redis and DB implementations",
        "effort_estimate": "1 day"
      }
    }
  ]
}
```

### 4.3 Workflow Run Link

Add workflow run URL to every ticket for full context:

```javascript
{
  "workflow_run_url": "https://github.com/org/repo/actions/runs/12345678",
  "workflow_name": "PR Validation Pipeline",
  "workflow_run_id": "12345678",
  "workflow_status": "completed",
  "workflow_conclusion": "failure"  // or "success" if non-blocking
}
```

This appears as an info panel at the top of the ticket:
```
📊 Workflow Run: View Full Logs
Pipeline: PR Validation Pipeline | Status: Failed | Run ID: 12345678
```

---

## 5. Jira Skill Specification

### 5.1 Skill Overview

**Skill Name**: `jira_ticket_skill`

**Purpose**: Reusable skill for Jira ticket operations across all agents

**Capabilities**:
1. `create_ticket` - Create Jira ticket with auto-assignment
2. `assign_ticket` - Assign ticket to user (by email or Account ID)
3. `link_pr` - Link GitHub PR to Jira ticket (remote link)
4. `add_comment` - Add comment to existing ticket
5. `transition_ticket` - Change ticket status

**Usage**:
```python
from skills.jira_ticket_skill import JiraTicketSkill

jira = JiraTicketSkill(
    base_url=os.getenv("JIRA_BASE_URL"),
    email=os.getenv("JIRA_EMAIL"),
    api_token=os.getenv("JIRA_API_TOKEN"),
    project_key="SCM"
)

# Create ticket with auto-assignment
ticket = jira.create_ticket(
    issue_type="Code Violation",
    summary="Code violations in PR #123",
    description=adf_content,
    pr_author_email="dev1@company.com",
    pr_author_github_username="dev1",
    severity="MEDIUM",
    pr_url="https://github.com/org/repo/pull/123"
)
```

### 5.2 Skill Operations

#### Operation 1: create_ticket

**Input Schema**:
```python
{
    "issue_type": str,              # Required: "Code Violation" | "LLD Deviation" | "Pattern Rejection"
    "summary": str,                 # Required: Ticket summary (max 255 chars)
    "description": dict,            # Required: ADF format description
    "pr_author_email": str,         # Optional: PR author email for assignment
    "pr_author_github_username": str, # Optional: GitHub username for assignment
    "pr_url": str,                  # Required: GitHub PR URL
    "pr_number": int,               # Required: PR number
    "repository": str,              # Required: Repository name
    "severity": str,                # Required: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    "labels": list[str],            # Optional: Additional labels
    "components": list[str],        # Optional: Component names
    "workflow_run_url": str,        # Optional: GitHub Actions run URL
    "agent_findings": dict          # Optional: Structured findings from agent
}
```

**Output Schema**:
```python
{
    "status": "SUCCESS" | "FAILURE",
    "ticket_id": str,               # e.g., "SCM-456"
    "ticket_url": str,              # e.g., "https://jira.company.com/browse/SCM-456"
    "ticket_key": str,              # Same as ticket_id
    "assignee_account_id": str,     # Jira Account ID of assignee
    "assignment_method": str,       # "direct" | "fallback_component" | "fallback_default" | "unassigned"
    "created_at": str,              # ISO 8601 timestamp
    "creation_time_ms": int,        # Time taken to create ticket
    "pr_linked": bool,              # Whether PR was successfully linked
    "error": str | None             # Error message if status = FAILURE
}
```

#### Operation 2: assign_ticket

**Input Schema**:
```python
{
    "ticket_key": str,              # Required: Jira ticket key (e.g., "SCM-456")
    "assignee_email": str,          # Optional: Email to lookup Account ID
    "assignee_account_id": str,     # Optional: Direct Account ID (takes precedence)
    "github_username": str          # Optional: GitHub username for lookup
}
```

**Output Schema**:
```python
{
    "status": "SUCCESS" | "FAILURE",
    "ticket_key": str,
    "assignee_account_id": str,
    "assignment_method": str,
    "assigned_at": str,
    "error": str | None
}
```

#### Operation 3: link_pr

**Input Schema**:
```python
{
    "ticket_key": str,              # Required: Jira ticket key
    "pr_url": str,                  # Required: GitHub PR URL
    "pr_number": int,               # Required: PR number
    "pr_title": str,                # Required: PR title
    "repository": str,              # Required: Repository full name (org/repo)
    "pr_state": str                 # Required: "open" | "closed" | "merged"
}
```

**Output Schema**:
```python
{
    "status": "SUCCESS" | "FAILURE",
    "ticket_key": str,
    "link_id": str,                 # Remote link ID
    "linked_at": str,
    "error": str | None
}
```

#### Operation 4: add_comment

**Input Schema**:
```python
{
    "ticket_key": str,              # Required: Jira ticket key
    "comment": str | dict,          # Required: Plain text or ADF format
    "visibility": dict              # Optional: Restrict comment visibility
}
```

**Output Schema**:
```python
{
    "status": "SUCCESS" | "FAILURE",
    "ticket_key": str,
    "comment_id": str,
    "created_at": str,
    "error": str | None
}
```

#### Operation 5: transition_ticket

**Input Schema**:
```python
{
    "ticket_key": str,              # Required: Jira ticket key
    "transition_name": str,         # Required: "In Review" | "Approved" | "Closed"
    "comment": str                  # Optional: Comment for transition
}
```

**Output Schema**:
```python
{
    "status": "SUCCESS" | "FAILURE",
    "ticket_key": str,
    "new_status": str,
    "transitioned_at": str,
    "error": str | None
}
```

### 5.3 Skill Internal Features

**Built-in Features**:
1. **User Lookup & Caching**: Automatic Account ID lookup with 24-hour cache
2. **Rate Limiting**: Token bucket algorithm (100 req/min)
3. **Retry Logic**: Exponential backoff for transient failures
4. **Error Handling**: Classified errors (retryable vs non-retryable)
5. **Metrics**: CloudWatch metrics for all operations
6. **Logging**: Structured JSON logs for audit trail

**Configuration**:
```python
jira_config = {
    "base_url": "https://company.atlassian.net",
    "email": "automation@company.com",
    "api_token": "ATATT3xFfGF0...",
    "project_key": "SCM",
    "cache_ttl_hours": 24,
    "rate_limit_per_minute": 100,
    "timeout_seconds": 10,
    "max_retries": 3,
    "retry_delay_seconds": 5
}
```

---

## 6. Enhanced Input Schema

### 6.1 New Input Fields

The agent now accepts these additional fields in the input payload:

```json
{
  "issue_type": "CODE_VIOLATION",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "pr_url": "https://github.com/tonic-scm/order-service/pull/123",
  "author": "developer1",
  "severity": "MEDIUM",

  // NEW FIELDS
  "pr_author_email": "developer1@company.com",          // NEW: For Jira assignment lookup
  "pr_author_github_username": "dev1",                  // NEW: Fallback for email lookup
  "workflow_run_url": "https://github.com/org/repo/actions/runs/12345",  // NEW: Full logs link

  "agent_findings": {                                   // NEW: Structured findings
    "agent_info": {
      "name": "Code Best Practises Agent",
      "version": "2.1.0",
      "detection_time": "2026-01-28T10:25:30Z",
      "analysis_duration_ms": 3400
    },
    "findings": [
      {
        "finding_id": "CBP-001",
        "type": "NAMING_CONVENTION_VIOLATION",
        "severity": "MEDIUM",
        "file": "src/main/java/OrderService.java",
        "line_start": 45,
        "line_end": 45,
        "code_snippet": "public Order get_order(String id) { ... }",
        "description": "Method name 'get_order()' violates camelCase convention",
        "pattern_id": "PATTERN-001",
        "pattern_url": "https://confluence.company.com/patterns/PATTERN-001",
        "remediation": {
          "description": "Rename method to follow camelCase convention",
          "suggested_fix": "public Order getOrder(String id) { ... }",
          "effort_estimate": "5 minutes"
        }
      }
    ]
  }
}
```

### 6.2 Backward Compatibility

**Migration Strategy**:
- New fields are **optional** (existing agents can still call without them)
- Agent gracefully handles missing fields with fallback behavior
- Old-style input still works but logs deprecation warning
- Phased migration: Update agents incrementally

**Fallback Behavior**:
```
If pr_author_email missing:
  → Try pr_author_github_username with email domain mapping
  → If that fails, use existing author field with component owner fallback

If workflow_run_url missing:
  → Omit workflow panel from ticket (backward compatible)

If agent_findings missing:
  → Fall back to old-style violations/deviations format
  → Generate basic description without rich context
```

---

## 7. Enhanced Output Schema

### 7.1 New Output Fields

The agent now returns these additional fields:

```json
{
  "status": "SUCCESS",
  "ticket_id": "SCM-456",
  "ticket_url": "https://company.atlassian.net/browse/SCM-456",
  "created_at": "2026-01-28T10:30:15Z",

  // NEW FIELDS
  "assignee_account_id": "5b10ac8d82e05b22cc7d4ef5",  // NEW: Jira Account ID assigned
  "assignee_display_name": "Developer One",            // NEW: Human-readable name
  "assignment_method": "direct",                       // NEW: How assignment was determined
  "assignment_lookup_time_ms": 120,                    // NEW: Time for user lookup
  "pr_linked": true,                                   // NEW: Whether PR link succeeded
  "rich_context_included": true,                       // NEW: Whether agent findings were included

  "lookup_attempts": [                                 // NEW: Debugging info
    {
      "method": "email_lookup",
      "input": "developer1@company.com",
      "result": "success",
      "duration_ms": 120
    }
  ]
}
```

### 7.2 Assignment Method Values

**Possible values for `assignment_method`**:

| Value | Description | When Used |
|-------|-------------|-----------|
| `direct` | Found Jira user directly from email | pr_author_email provided and found in Jira |
| `github_mapped` | Found via GitHub username mapping | Used username-to-email mapping table |
| `domain_pattern` | Used organization email pattern | Applied `{username}@company.com` pattern |
| `fallback_component` | Assigned to component owner | User not found, used team config |
| `fallback_default` | Assigned to default assignee | Component owner not configured |
| `unassigned` | No assignee set | All lookups failed |

### 7.3 Metrics and Observability

**CloudWatch Metrics**:
```
Namespace: SCM/JiraIntegrationAgent

Metrics:
- TicketCreationTime (ms)
- UserLookupTime (ms)
- AssignmentMethodCount (by method type)
- AssignmentSuccessRate (%)
- CacheHitRate (%)
- APICallCount (by operation)
- ErrorCount (by error type)
```

**CloudWatch Log Events**:
```json
{
  "timestamp": "2026-01-28T10:30:15Z",
  "agent": "jira_integration_agent",
  "version": "2.0.0",
  "action": "CREATE_TICKET",
  "ticket_id": "SCM-456",
  "issue_type": "CODE_VIOLATION",
  "pr_number": 123,
  "repository": "order-service",
  "assignee_account_id": "5b10ac8d82e05b22cc7d4ef5",
  "assignment_method": "direct",
  "assignment_lookup_time_ms": 120,
  "creation_time_ms": 4200,
  "rich_context": true,
  "workflow_run_url": "https://github.com/org/repo/actions/runs/12345",
  "status": "SUCCESS"
}
```

---

## 8. Error Handling Updates

### 8.1 New Error Scenarios

**User Lookup Errors**:

| Error | HTTP Code | Retryable? | Fallback Strategy |
|-------|-----------|------------|-------------------|
| User not found in Jira | 404 | No | Try GitHub username mapping → Component owner → Default |
| Email format invalid | 400 | No | Skip email lookup, try GitHub username |
| Jira API timeout | 504 | Yes | Retry with exponential backoff |
| Rate limit exceeded | 429 | Yes | Wait (Retry-After header) + queue |
| Authentication failure | 401 | No | Critical alarm, fail immediately |

**Assignment Errors**:

| Error | Action |
|-------|--------|
| Cannot assign to user (permissions) | Assign to default, add comment with intended assignee |
| User account inactive | Try fallback, log warning |
| Multiple users match email | Use first active user, log warning |

### 8.2 Enhanced Error Response

**Error Response Structure**:
```json
{
  "status": "FAILURE",
  "error": {
    "code": "USER_LOOKUP_FAILED",
    "message": "Could not find Jira user for developer1@company.com",
    "category": "ASSIGNMENT_ERROR",
    "retryable": false,
    "attempted_methods": [
      {
        "method": "email_lookup",
        "input": "developer1@company.com",
        "result": "not_found",
        "duration_ms": 150
      },
      {
        "method": "github_username_mapping",
        "input": "dev1",
        "result": "no_mapping",
        "duration_ms": 20
      },
      {
        "method": "fallback_component_owner",
        "input": "order-service",
        "result": "success",
        "assignee_email": "team-lead1@company.com",
        "duration_ms": 80
      }
    ],
    "final_assignment": {
      "method": "fallback_component",
      "assignee_account_id": "5b10ac8d82e05b22cc7d4ef6",
      "assignee_display_name": "Team Lead One"
    }
  },
  "ticket_id": "SCM-456",
  "ticket_url": "https://company.atlassian.net/browse/SCM-456",
  "created_at": "2026-01-28T10:30:15Z",
  "partial_success": true,
  "warnings": [
    "Ticket created but assigned to fallback owner instead of PR author"
  ]
}
```

### 8.3 Partial Success Handling

**Scenario**: Ticket created but assignment failed

**Strategy**:
1. Create ticket successfully
2. Assignment fails (user not found)
3. Use fallback assignment
4. Return **partial success** status
5. Add comment to ticket: "Auto-assignment to PR author failed. Assigned to component owner."
6. Create CloudWatch metric for tracking assignment failures

**Response**:
```json
{
  "status": "PARTIAL_SUCCESS",
  "ticket_id": "SCM-456",
  "ticket_url": "...",
  "assignee_account_id": "5b10ac8d82e05b22cc7d4ef6",
  "assignment_method": "fallback_component",
  "warnings": ["PR author not found in Jira, assigned to component owner"],
  "original_error": "User developer1@company.com not found in Jira"
}
```

### 8.4 Graceful Degradation

**Priority of Degradation**:

```
1. Always create ticket (most important)
   ↓
2. Best-effort assignment (fallback if needed)
   ↓
3. Link PR (retry if fails)
   ↓
4. Rich context (omit if causes issues)
   ↓
5. Post GitHub comment (best effort)
```

**Example Flow**:
```
1. Attempt to create ticket with rich context
   → Jira API error: "Description too large"
   → Fallback: Create with simplified description
   → Success ✓

2. Attempt auto-assignment
   → User lookup timeout
   → Fallback: Assign to component owner
   → Success ✓

3. Attempt PR link
   → Network timeout
   → Queue for retry
   → Partial success (ticket created, link pending)

4. Post GitHub comment
   → GitHub API rate limited
   → Queue for retry
   → Partial success
```

---

## 9. Implementation Guidance

### 9.1 Implementation Phases

**Phase 1: Jira Skill Creation (Week 1)**
- Extract existing Jira logic into skill module
- Implement user lookup and caching
- Add rate limiting and retry logic
- Unit tests for all operations

**Phase 2: Auto-Assignment Enhancement (Week 2)**
- Integrate Account ID lookup
- Implement fallback strategies
- Create username mapping table (DynamoDB)
- Add CloudWatch metrics

**Phase 3: Rich Context Enhancement (Week 3)**
- Design ADF templates for each agent type
- Update agent callers to send structured findings
- Add workflow run URL support
- Integration tests

**Phase 4: Migration and Validation (Week 4)**
- Deploy skill to staging environment
- Update agents incrementally (backward compatible)
- Validate metrics and error handling
- Production deployment

### 9.2 Technology Stack

**Programming Language**: Python 3.11+

**Key Libraries**:
```
atlassian-python-api==3.41.0   # Jira REST API client
redis==5.0.1                    # User lookup cache
boto3==1.34.0                   # AWS services (DynamoDB, SQS, CloudWatch)
pydantic==2.5.0                 # Input/output validation
tenacity==8.2.3                 # Retry logic
```

**Infrastructure**:
- **Compute**: AWS Lambda (Python 3.11 runtime)
- **Cache**: Amazon ElastiCache (Redis)
- **Configuration**: DynamoDB tables
  - `jira_user_cache` (email/username → Account ID)
  - `github_username_mapping` (GitHub username → Jira email)
  - `component_ownership` (repository/component → owner)
- **Queue**: AWS SQS (for retry logic)
- **Secrets**: AWS Secrets Manager (Jira credentials)
- **Monitoring**: AWS CloudWatch (logs, metrics, alarms)

### 9.3 Configuration Management

**Environment Variables**:
```bash
# Jira Configuration
JIRA_BASE_URL=https://company.atlassian.net
JIRA_EMAIL=automation@company.com
JIRA_API_TOKEN_SECRET_NAME=jira/api-token
JIRA_PROJECT_KEY=SCM
JIRA_DEFAULT_ASSIGNEE_ACCOUNT_ID=5b10ac8d82e05b22cc7d4ef6

# Cache Configuration
REDIS_HOST=jira-cache.abc123.0001.use1.cache.amazonaws.com
REDIS_PORT=6379
USER_CACHE_TTL_HOURS=24

# Rate Limiting
JIRA_RATE_LIMIT_PER_MINUTE=100

# Retry Configuration
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY_SECONDS=5
RETRY_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/jira-retry-queue

# Organization Configuration
ORGANIZATION_EMAIL_DOMAIN=company.com
COMPONENT_OWNERSHIP_TABLE=component-ownership
USERNAME_MAPPING_TABLE=github-username-mapping
```

**DynamoDB Table Schemas**:

**Table: component-ownership**
```json
{
  "TableName": "component-ownership",
  "KeySchema": [
    {"AttributeName": "repository", "KeyType": "HASH"},
    {"AttributeName": "component", "KeyType": "RANGE"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "repository", "AttributeType": "S"},
    {"AttributeName": "component", "AttributeType": "S"}
  ],
  "Example Item": {
    "repository": "order-service",
    "component": "payment-module",
    "owner_email": "team-lead1@company.com",
    "owner_account_id": "5b10ac8d82e05b22cc7d4ef7",
    "updated_at": "2026-01-28T10:00:00Z"
  }
}
```

**Table: github-username-mapping**
```json
{
  "TableName": "github-username-mapping",
  "KeySchema": [
    {"AttributeName": "github_username", "KeyType": "HASH"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "github_username", "AttributeType": "S"}
  ],
  "Example Item": {
    "github_username": "dev1",
    "jira_email": "developer1@company.com",
    "jira_account_id": "5b10ac8d82e05b22cc7d4ef5",
    "updated_at": "2026-01-28T09:00:00Z"
  }
}
```

### 9.4 Testing Strategy

**Unit Tests**:
- All Jira Skill operations (mocked Jira API)
- User lookup logic (all fallback paths)
- ADF template generation
- Cache behavior (hit/miss scenarios)

**Integration Tests**:
- End-to-end ticket creation with real Jira test instance
- User lookup with real API calls
- Retry logic with simulated failures
- Rate limiting behavior

**Load Tests**:
- 100 ticket creations/minute (rate limit threshold)
- Cache performance under load
- SQS queue processing throughput

**Test Coverage Target**: >85% code coverage

### 9.5 Deployment Strategy

**Deployment Steps**:
1. Deploy Jira Skill Lambda function (new)
2. Deploy user cache (Redis)
3. Create DynamoDB tables (if not exist)
4. Update Jira Integration Agent to use skill
5. Deploy updated agent
6. Monitor metrics for 24 hours
7. Update other agents incrementally (Code, LLD, Pattern)

**Rollback Plan**:
- Keep old agent version deployed
- Blue-green deployment (route 10% traffic to new version)
- If errors spike >1%, rollback to old version
- Investigate and fix, redeploy

**Monitoring During Deployment**:
- CloudWatch Dashboard with real-time metrics
- Alarm on error rate >1%
- Alarm on ticket creation time P95 >10 seconds
- Alarm on cache hit rate <80%

### 9.6 Sample Code

**Jira Skill Usage Example**:
```python
from skills.jira_ticket_skill import JiraTicketSkill
from skills.jira_ticket_skill.models import CreateTicketInput, CreateTicketOutput

# Initialize skill
jira = JiraTicketSkill.from_environment()

# Prepare input
input_data = CreateTicketInput(
    issue_type="Code Violation",
    summary="Code violations in PR #123 (order-service)",
    description=generate_adf_description(findings),
    pr_author_email="developer1@company.com",
    pr_author_github_username="dev1",
    pr_url="https://github.com/tonic-scm/order-service/pull/123",
    pr_number=123,
    repository="tonic-scm/order-service",
    severity="MEDIUM",
    labels=["code-quality", "java"],
    components=["order-service"],
    workflow_run_url="https://github.com/org/repo/actions/runs/12345",
    agent_findings={
        "agent_info": {
            "name": "Code Best Practises Agent",
            "version": "2.1.0"
        },
        "findings": [...]
    }
)

# Create ticket
try:
    output: CreateTicketOutput = jira.create_ticket(input_data)

    if output.status == "SUCCESS":
        print(f"Ticket created: {output.ticket_url}")
        print(f"Assigned to: {output.assignee_display_name}")
        print(f"Assignment method: {output.assignment_method}")
    elif output.status == "PARTIAL_SUCCESS":
        print(f"Ticket created with warnings: {output.warnings}")
    else:
        print(f"Failed: {output.error}")

except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Queue for retry or alert
```

---

## 10. Success Criteria

### 10.1 Functional Success Criteria

The enhancement is successful when:

1. **Auto-Assignment**:
   - 95%+ of tickets assigned to correct PR author (by Account ID)
   - <5% fallback to component owner
   - 0 authentication errors due to invalid assignment
   - User lookup time P95 <200ms

2. **Rich Context**:
   - 100% of tickets include agent name and version
   - 100% of tickets include workflow run URL (when provided)
   - 100% of tickets include structured findings with line numbers
   - 100% of tickets include remediation guidance
   - Ticket descriptions actionable without PR investigation

3. **Jira Skill**:
   - All agents successfully use Jira Skill (no direct API calls)
   - Skill operations 99.9% success rate
   - Cache hit rate >90% for user lookups
   - Rate limiting prevents API throttling (0 rate limit errors)

4. **Performance**:
   - Ticket creation time P95 <10 seconds (maintained)
   - User lookup adds <200ms to P95 latency
   - No degradation from current baseline

### 10.2 Quality Indicators

**Metrics to Track**:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Assignment Success Rate | >95% direct assignment | CloudWatch metric |
| Cache Hit Rate | >90% | Redis metrics |
| User Lookup Time P95 | <200ms | CloudWatch metric |
| Ticket Creation Time P95 | <10 seconds | CloudWatch metric |
| Error Rate | <1% | CloudWatch metric |
| Partial Success Rate | <5% | CloudWatch metric |
| Duplicate Ticket Rate | 0% | Manual audit |

**Quality Gates**:
- All unit tests pass
- Integration tests pass (>95% success)
- Load tests pass (100 req/min sustained)
- Manual testing checklist complete
- Security review approved
- Documentation updated

### 10.3 Business Value

**Expected Time Savings (Enhanced ATSQ)**:

**Baseline (Manual Process)**:
- Identify issue in PR: 30 minutes
- Create Jira ticket: 10 minutes
- Find correct assignee: 5 minutes
- Link PR to ticket: 5 minutes
- Add context and remediation: 20 minutes
- **Total**: 70 minutes per issue

**With Current Agent**:
- Automated ticket creation: 10 seconds
- Manual triage and context addition: 30 minutes
- **Total**: 30.17 minutes per issue
- **Savings**: 57% ATSQ

**With Enhanced Agent**:
- Automated ticket creation with rich context: 10 seconds
- Manual verification only: 5 minutes
- **Total**: 5.17 minutes per issue
- **Savings**: 93% ATSQ (vs baseline) or 83% ATSQ (vs current agent)

**Additional Value**:
- Faster issue resolution (correct assignment immediately)
- Better compliance (complete audit trail with workflow links)
- Developer productivity (no context switching to investigate)
- Management visibility (accurate agent performance metrics)

### 10.4 Acceptance Testing

**Test Scenarios**:

1. **Happy Path - Direct Assignment**:
   - Input: PR with author email provided
   - Expected: Ticket created, assigned to PR author by Account ID
   - Verify: assignment_method = "direct"

2. **Fallback Path - GitHub Username Mapping**:
   - Input: PR with only GitHub username (no email)
   - Expected: Lookup username in mapping table, assign via mapped email
   - Verify: assignment_method = "github_mapped"

3. **Fallback Path - Domain Pattern**:
   - Input: PR with GitHub username, no mapping entry
   - Expected: Apply domain pattern, lookup Jira user
   - Verify: assignment_method = "domain_pattern"

4. **Fallback Path - Component Owner**:
   - Input: PR author not in Jira
   - Expected: Assign to component owner from config
   - Verify: assignment_method = "fallback_component"

5. **Fallback Path - Unassigned**:
   - Input: PR author and component owner not found
   - Expected: Create ticket unassigned, trigger alarm
   - Verify: assignment_method = "unassigned", alarm sent

6. **Rich Context**:
   - Input: Structured agent findings with line numbers
   - Expected: Ticket includes formatted findings table, code snippets, remediation
   - Verify: Manual inspection of ticket in Jira

7. **Workflow Link**:
   - Input: workflow_run_url provided
   - Expected: Ticket includes workflow panel with clickable link
   - Verify: Manual inspection, link works

8. **Backward Compatibility**:
   - Input: Old-style payload (no new fields)
   - Expected: Ticket created with fallback behavior, no errors
   - Verify: Logs show deprecation warning

9. **Jira Unavailable**:
   - Input: Simulate Jira API timeout
   - Expected: Ticket queued to SQS, retry succeeds
   - Verify: CloudWatch logs show QUEUED → SUCCESS

10. **Rate Limiting**:
    - Input: 150 ticket creation requests in 1 minute
    - Expected: First 100 succeed, remaining 50 queued
    - Verify: No Jira 429 errors, all tickets eventually created

---

## Questions and TBCs

| ID | Question/TBC | Priority | Owner | Status |
|----|--------------|----------|-------|--------|
| TBC-JIE-001 | Confirm organization email domain pattern | HIGH | DevOps Team | Open |
| TBC-JIE-002 | Redis instance sizing for cache | HIGH | Infrastructure Team | Open |
| TBC-JIE-003 | DynamoDB table provisioning (capacity) | MEDIUM | Infrastructure Team | Open |
| TBC-JIE-004 | GitHub username mapping: manual or API-based? | MEDIUM | Product Owner | Open |
| TBC-JIE-005 | Should we support multiple Jira projects? | LOW | Architecture Team | Open |
| TBC-JIE-006 | ADF template customization per agent | LOW | Product Owner | Open |
| TBC-JIE-007 | User lookup cache: Redis vs DynamoDB? | MEDIUM | Architecture Team | Open |
| TBC-JIE-008 | Rate limit per agent or shared? | MEDIUM | Architecture Team | Open |

---

## Appendix A: Migration Checklist

**Pre-Migration**:
- [ ] Create Redis cache instance
- [ ] Create DynamoDB tables (component-ownership, github-username-mapping)
- [ ] Populate username mapping table (if using manual mapping)
- [ ] Configure default assignee Account ID
- [ ] Deploy Jira Skill Lambda function
- [ ] Run integration tests in staging

**Migration (Per Agent)**:
- [ ] Update agent to send new fields (pr_author_email, workflow_run_url, agent_findings)
- [ ] Deploy agent to staging
- [ ] Validate ticket creation (manual inspection)
- [ ] Deploy agent to production (canary: 10% traffic)
- [ ] Monitor metrics for 24 hours
- [ ] Roll out to 100% traffic

**Post-Migration**:
- [ ] Verify all agents migrated
- [ ] Remove old-style code paths (cleanup)
- [ ] Update documentation
- [ ] Train support team on new ticket format
- [ ] Archive old Jira Integration Agent code

---

## Appendix B: Troubleshooting Guide

**Problem: User lookup always fails**
- Check: Jira API credentials valid?
- Check: User email format correct?
- Check: User exists and is active in Jira?
- Solution: Check CloudWatch logs for API response details

**Problem: Cache hit rate <80%**
- Check: Cache TTL too short?
- Check: Different email variations for same user?
- Solution: Normalize emails (lowercase), increase TTL to 48 hours

**Problem: Rate limit exceeded**
- Check: Multiple agents calling simultaneously?
- Check: Rate limit configuration correct?
- Solution: Implement per-agent rate limiting, queue excess requests

**Problem: Assignment to wrong user**
- Check: Email domain pattern correct?
- Check: Multiple Jira users with same email?
- Solution: Use GitHub username mapping (more reliable)

**Problem: Ticket description truncated**
- Check: ADF content size >32KB?
- Solution: Truncate code snippets, limit findings to top 10

---

**End of Enhancement Specification**
