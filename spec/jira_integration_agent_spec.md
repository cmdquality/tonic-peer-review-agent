# Agent Specification: Jira Integration Agent

**Created**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**LLD Reference**: lld_1_config_management_platform.md

---

## Question 1: Agent Identity and Purpose

**What is this agent and what problem does it solve?**

The Jira Integration Agent is a workflow automation and issue tracking agent that creates Jira tickets for code violations, LLD deviations, and pattern rejections. This agent solves the problem of disconnected issue tracking by ensuring all code quality and architectural issues are properly documented, tracked, and linked to GitHub PRs for complete traceability.

**Problem Solved**: Without automated Jira integration, issues discovered during automated reviews are not tracked, leading to lost visibility for management, incomplete audit trails, and difficulty measuring code quality trends over time.

**Value Provided**:
- Automatic issue creation for all code quality problems
- Complete traceability between GitHub PRs and Jira tickets
- Audit trail for compliance and governance
- Workflow automation for issue assignment and routing
- Metrics and reporting on code quality trends
- Management visibility into code quality issues

---

## Question 2: Core Capabilities

**What are the agent's main capabilities?**

1. **Ticket Creation**: Create Jira tickets with complete context:
   - Code violations (from Code Best Practises Agent)
   - LLD deviations (from LLD Alignment Review Agent)
   - Pattern rejections (from Peer Review Documentation Agent)
2. **Ticket Linking**: Link Jira tickets to GitHub PRs (bidirectional links)
3. **Field Population**: Auto-populate Jira fields:
   - Project: SCM
   - Issue Type: Code Violation / LLD Deviation / Pattern Rejection
   - Priority: Based on severity (Critical/High/Medium/Low)
   - Assignee: PR author or component owner
   - Labels: Auto-tag with relevant categories
   - Components: Repository/component affected
4. **Workflow Automation**: Auto-transition tickets based on PR status
5. **Comment Synchronization**: Sync key PR comments to Jira ticket
6. **Notification**: Notify assignees of new tickets
7. **Metrics Tracking**: Track ticket creation rates for quality metrics

---

## Question 3: Input Requirements

**What inputs does the agent need?**

**Primary Inputs**:
- **Issue Type**: CODE_VIOLATION / LLD_DEVIATION / PATTERN_REJECTION
- **PR Data**: PR number, repository, author, URL
- **Issue Details**: Violation/deviation/rejection details
- **Severity**: CRITICAL / MAJOR / MINOR
- **Source Agent**: Which agent triggered ticket creation

**For Code Violations**:
- Violation report from Code Best Practises Agent
- File paths, line numbers, violation types
- Pattern references

**For LLD Deviations**:
- Deviation report from LLD Alignment Review Agent
- LLD document references
- Expected vs actual behavior

**For Pattern Rejections**:
- Rejection details from Peer Review Documentation Agent
- Reviewer comments
- Pattern details

**Format**: JSON payload from calling agent

**Preconditions**:
- Jira API credentials available (in GitHub Secrets)
- Jira project "SCM" exists
- PR is in GitHub (valid PR URL)
- Issue details are complete and actionable

---

## Question 4: Output Specifications

**What does the agent produce?**

**Primary Outputs**:
- **Jira Ticket**: Created ticket with unique ticket ID (e.g., SCM-456)
- **Ticket URL**: Link to created Jira ticket
- **GitHub PR Comment**: Comment on PR with Jira ticket link
- **Status**: SUCCESS / FAILURE

**Jira Ticket Fields**:
- **Summary**: Auto-generated from issue details
- **Description**: Detailed issue description with links
- **Issue Type**: Code Violation / LLD Deviation / Pattern Rejection
- **Priority**: Based on severity mapping
- **Assignee**: PR author or component owner
- **Reporter**: "SCM Automation Agent"
- **Labels**: Auto-tagged (e.g., code-quality, lld-deviation, java)
- **Components**: Repository name
- **Custom Fields**:
  - PR Number
  - PR URL
  - Source Agent
  - Severity
  - Pattern ID (if applicable)

**Output Format**:
- JSON response with ticket ID and URL
- Markdown-formatted PR comment with ticket link

**Artifacts Created**:
- Jira ticket with complete issue context
- GitHub PR comment with Jira link
- CloudWatch logs for audit trail

---

## Question 5: Constraints and Limitations

**What are the boundaries and limitations?**

**Operational Constraints**:
- Cannot create tickets without Jira API access
- Limited to SCM project in Jira (cannot create in other projects)
- Cannot modify PR code or fix issues (only creates tickets)
- Jira API rate limits apply (100 requests/minute)

**Limitations**:
- Ticket creation depends on Jira availability
- Cannot auto-assign if component owner not in Jira
- Limited to configured issue types and workflows
- Cannot automatically resolve tickets (requires human action)
- Comment synchronization is one-way (GitHub → Jira, not bidirectional)

**Guardrails**:
- NEVER create duplicate tickets for same issue (check for existing tickets)
- NEVER create tickets without sufficient context (must be actionable)
- NEVER modify existing tickets (only create new or add comments)
- ALWAYS link tickets to PRs for traceability

---

## Question 6: Behavioral Patterns and Decision Rules

**How should the agent behave and make decisions?**

**Behavioral Patterns**:
- **Deduplication**: Check for existing tickets before creating new ones
- **Actionable Content**: Tickets must have clear action items and context
- **Severity Mapping**: Map agent severity to Jira priority consistently
- **Fast Creation**: Create tickets within 10 seconds
- **Fail-Safe**: Queue ticket creation if Jira unavailable (don't lose issues)

**Decision Rules**:

**When triggered by Code Best Practises Agent (violations)**:
1. Create Jira ticket with issue type: "Code Violation"
2. Set priority based on violation count:
   - 1-3 violations: Low
   - 4-10 violations: Medium
   - 11+ violations: High
3. Assign to PR author
4. Add labels: code-quality, [language], [violation-types]
5. Link to PR in description

**When triggered by LLD Alignment Review Agent (deviations)**:
1. Create Jira ticket with issue type: "LLD Deviation"
2. Set priority based on deviation severity:
   - CRITICAL → High
   - MAJOR → Medium
   - MINOR → Low
3. Assign to PR author with CC to architects
4. Add labels: lld-deviation, architectural, [component]
5. Link to both PR and LLD document in description

**When triggered by Peer Review Documentation Agent (rejections)**:
1. Create Jira ticket with issue type: "Pattern Rejection"
2. Set priority: Medium (default)
3. Assign to PR author
4. Add labels: pattern-review, architectural, [category]
5. Include reviewer comments in description
6. Link to PR and pattern documentation

**Duplicate Detection**:
- Query Jira for existing tickets with same PR number
- If exists → Add comment to existing ticket instead of creating new
- If closed → Create new ticket with reference to previous

**If Jira unavailable**:
1. Queue ticket creation in DynamoDB or SQS
2. Retry every 5 minutes for up to 24 hours
3. Create CloudWatch alarm for Jira connectivity
4. Post PR comment: "Jira ticket pending (Jira temporarily unavailable)"

---

## Question 7: Error Handling and Edge Cases

**How should the agent handle errors and edge cases?**

**Error Detection**:
- Jira API failures (timeout, authentication, rate limiting)
- Jira project or issue type not found
- Invalid assignee (user not in Jira)
- Ticket creation timeout (>10 seconds)
- Network connectivity issues

**Error Response**:
- **Jira API Failure**: Queue for retry, create CloudWatch alarm, post PR comment with delay notice
- **Authentication Failure**: Create critical CloudWatch alarm, notify ops team immediately
- **Invalid Assignee**: Assign to component owner or default to architecture team lead
- **Timeout**: Retry once, then queue for background processing
- **Rate Limiting**: Implement exponential backoff and queue

**Fallback Strategies**:
- Queue ticket creation in SQS for asynchronous processing
- Maintain retry queue with exponential backoff (5 min, 15 min, 1 hour, 4 hours)
- If 24-hour retry exhausted, create CloudWatch alarm and email ops team
- Always post PR comment even if Jira ticket creation fails (for developer visibility)

**Edge Cases**:
- **PR already has Jira ticket**: Add comment to existing ticket instead of creating new
- **Multiple issues in same PR**: Create single ticket with all issues listed
- **Issue resolved before ticket created**: Still create ticket for audit trail (close immediately)
- **PR author not in Jira**: Assign to component owner from team configuration
- **Component owner not configured**: Assign to default architecture team lead

---

## Question 8: Success Criteria

**How do you know the agent succeeded?**

The agent has succeeded when:

1. **Ticket Creation**: All issues result in Jira tickets with complete context
2. **Fast Processing**: Tickets created within 10 seconds (P95)
3. **Complete Linking**: All tickets linked to GitHub PRs (bidirectional)
4. **Proper Assignment**: Correct assignees based on issue type and component
5. **No Data Loss**: Zero issues lost due to Jira unavailability (queue works)
6. **Audit Trail**: All ticket creations logged to CloudWatch

**Quality Indicators**:
- Ticket creation success rate > 99%
- Ticket creation time P95 < 10 seconds
- Zero duplicate tickets for same issue
- 100% of tickets have PR links
- 100% of tickets have actionable descriptions

**Business Value (ATSQ)**:
- **Expected Time Savings**: 92% ATSQ: 4-hour manual issue tracking reduced to 20 minutes (10 sec agent ticket creation + 19.83 min human verification and triage)
- **Baseline Assumption**: Manual issue tracking = 4 hours (includes identifying issues, creating tickets, linking to PRs, categorizing, assigning)
- **Verification Method**: Human verification (20 min triage and priority validation)
- **Category**: Labor Elimination (near-complete automation)

---

## Question 9: Usage Context and Workflow

**When and how is this agent used?**

**Invocation Context**:
- Triggered conditionally by other agents when problems occur
- Runs as Step 7 in PR validation workflow (conditional step)
- Non-interactive: runs automatically via agent-to-agent API call

**Workflow Integration**:

**Triggered by Code Best Practises Agent** (Step 1):
- When code violations detected
- Agent creates Jira ticket for violations
- PR merge blocked until violations fixed

**Triggered by LLD Alignment Review Agent** (Step 3):
- When LLD deviations detected
- Agent creates Jira ticket for deviations
- PR requires fix or architectural approval

**Triggered by Peer Review Documentation Agent** (Step 5):
- When pattern rejected by reviewers
- Agent creates Jira ticket for rejection
- PR closed, requires refactor or new architectural decision

**Workflow Position**: Step 7 in Configuration Management Platform workflow (see Activity Diagram in LLD)

**Conditional Execution**: Only invoked when issues occur (not for successful validations)

---

## Question 10: Example Interaction

**Provide a concrete example of the agent in action**

### Example 1: Code Violation Ticket Creation

**Input** (from Code Best Practises Agent):
```json
{
  "issue_type": "CODE_VIOLATION",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "pr_url": "https://github.com/tonic-scm/order-service/pull/123",
  "author": "developer1",
  "severity": "MEDIUM",
  "violations": [
    {
      "file": "src/main/java/com/tonic/OrderService.java",
      "line": 45,
      "type": "Naming Convention Violation",
      "description": "Method name 'get_order()' violates camelCase convention"
    },
    {
      "file": "src/main/java/com/tonic/OrderService.java",
      "line": 78,
      "type": "Exception Handling Violation",
      "description": "Generic Exception catch block should use specific exceptions"
    }
  ]
}
```

**Processing**:
1. Check for existing Jira ticket with PR #123
2. No existing ticket found
3. Map severity MEDIUM → Jira Priority: Medium
4. Generate ticket summary: "Code violations in PR #123 (order-service)"
5. Format ticket description with violation details
6. Query team configuration for component owner: "team-lead1@tonic.com"
7. Create Jira ticket via API

**Jira Ticket Created**:

**Ticket ID**: SCM-456

**Summary**: Code violations in PR #123 (order-service)

**Description**:
```markdown
## Code Violations Detected

Automated code analysis detected 2 violations in pull request #123.

**PR**: https://github.com/tonic-scm/order-service/pull/123
**Repository**: tonic-scm/order-service
**Author**: developer1
**Detection Agent**: Code Best Practises Agent

---

### Violations

#### Violation 1: Naming Convention Violation
**File**: `src/main/java/com/tonic/OrderService.java`
**Line**: 45
**Description**: Method name 'get_order()' violates camelCase convention
**Fix**: Rename method to 'getOrder()'

#### Violation 2: Exception Handling Violation
**File**: `src/main/java/com/tonic/OrderService.java`
**Line**: 78
**Description**: Generic Exception catch block should use specific exceptions
**Fix**: Replace `catch (Exception e)` with specific exception types

---

**Action Required**: Fix all violations before PR can be merged.

**Pattern Library**: https://confluence.tonic.com/display/SCM-PATTERNS
```

**Fields**:
- **Issue Type**: Code Violation
- **Priority**: Medium
- **Assignee**: developer1
- **Reporter**: SCM Automation Agent
- **Labels**: code-quality, java, naming-convention, exception-handling
- **Component**: order-service
- **Custom Fields**:
  - PR Number: 123
  - PR URL: https://github.com/tonic-scm/order-service/pull/123
  - Source Agent: Code Best Practises Agent
  - Severity: MEDIUM

**Output**:

**JSON Response**:
```json
{
  "status": "SUCCESS",
  "ticket_id": "SCM-456",
  "ticket_url": "https://tonic.atlassian.net/browse/SCM-456",
  "created_at": "2026-01-28T10:30:15Z"
}
```

**GitHub PR Comment**:
```markdown
## 📋 Jira Ticket Created

**Ticket**: [SCM-456](https://tonic.atlassian.net/browse/SCM-456) - Code violations in PR #123 (order-service)
**Status**: Open
**Priority**: Medium
**Assignee**: @developer1

This ticket tracks the code violations that must be fixed before PR can be merged.
```

**CloudWatch Log**:
```json
{
  "timestamp": "2026-01-28T10:30:15Z",
  "agent": "jira_integration_agent",
  "action": "CREATE_TICKET",
  "ticket_id": "SCM-456",
  "issue_type": "CODE_VIOLATION",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "creation_time_ms": 4200,
  "status": "SUCCESS"
}
```

---

### Example 2: LLD Deviation Ticket Creation

**Input** (from LLD Alignment Review Agent):
```json
{
  "issue_type": "LLD_DEVIATION",
  "pr_number": 456,
  "repository": "tonic-scm/payment-service",
  "pr_url": "https://github.com/tonic-scm/payment-service/pull/456",
  "author": "developer2",
  "severity": "CRITICAL",
  "deviations": [
    {
      "lld_section": "Section 5.2 - PaymentProcessor",
      "lld_url": "https://confluence.tonic.com/scm/payment-service-lld#section-5.2",
      "expected": "Must use Retry Pattern (max 3 retries)",
      "actual": "Circuit Breaker pattern used",
      "impact": "Conflicts with centralized resilience service"
    }
  ]
}
```

**Processing**:
1. Check for existing ticket: None found
2. Map severity CRITICAL → Jira Priority: High
3. Generate summary: "LLD deviation in PR #456 (payment-service)"
4. Assign to author with CC to architects (add watchers)
5. Create ticket

**Jira Ticket Created**:

**Ticket ID**: SCM-789

**Summary**: LLD deviation in PR #456 (payment-service)

**Description**:
```markdown
## LLD Deviation Detected

Critical architectural deviation detected in pull request #456.

**PR**: https://github.com/tonic-scm/payment-service/pull/456
**Repository**: tonic-scm/payment-service
**Author**: developer2
**Detection Agent**: LLD Alignment Review Agent
**Severity**: CRITICAL

---

### Deviation Details

**LLD Section**: Section 5.2 - PaymentProcessor
**LLD Document**: [Payment Service LLD](https://confluence.tonic.com/scm/payment-service-lld#section-5.2)

**Expected Behavior (per LLD)**:
> Must use Retry Pattern (max 3 retries)

**Actual Implementation**:
> Circuit Breaker pattern used

**Impact**: Conflicts with centralized resilience service

---

**Action Required**:
1. Fix deviation by using Retry Pattern as specified in LLD, OR
2. Request architectural approval to update LLD if Circuit Breaker is preferred

**Architects**: Please review and provide guidance.
```

**Fields**:
- **Issue Type**: LLD Deviation
- **Priority**: High (CRITICAL severity)
- **Assignee**: developer2
- **Watchers**: architect1, architect2 (auto-added)
- **Labels**: lld-deviation, architectural, payment-service, resilience
- **Component**: payment-service

**Output**: Similar to Example 1, with ticket ID SCM-789

---

### Example 3: Jira Unavailable (Queued Ticket)

**Scenario**: Jira API is down

**Input**:
```json
{
  "issue_type": "PATTERN_REJECTION",
  "pr_number": 459,
  "repository": "tonic-scm/order-service",
  "pr_url": "https://github.com/tonic-scm/order-service/pull/459",
  "author": "developer3",
  "severity": "MEDIUM",
  "rejection_reason": "Pattern introduces tight coupling with Redis"
}
```

**Processing**:
1. Attempt to create Jira ticket via API
2. Jira API timeout (connection refused)
3. Retry once: Still fails
4. Decision: Queue ticket for retry

**Actions**:
1. Write ticket payload to SQS queue: `scm-jira-ticket-queue`
2. Schedule retry: 5 minutes
3. Create CloudWatch alarm: "Jira API Unavailable"
4. Post PR comment with pending notice

**GitHub PR Comment**:
```markdown
## 📋 Jira Ticket Pending

A Jira ticket will be created for this pattern rejection once Jira connectivity is restored.

**Ticket Details**:
- Issue Type: Pattern Rejection
- Priority: Medium
- Reason: Pattern introduces tight coupling with Redis

**Status**: Queued for creation (Jira temporarily unavailable)

You will be notified once the ticket is created.
```

**SQS Message** (queued):
```json
{
  "ticket_payload": { ... },
  "retry_count": 0,
  "max_retries": 288,
  "next_retry": "2026-01-28T10:35:00Z"
}
```

**CloudWatch Log**:
```json
{
  "timestamp": "2026-01-28T10:30:00Z",
  "agent": "jira_integration_agent",
  "action": "QUEUE_TICKET",
  "issue_type": "PATTERN_REJECTION",
  "pr_number": 459,
  "status": "QUEUED",
  "reason": "Jira API unavailable"
}
```

**Background Retry** (5 minutes later):
1. SQS message processed by Lambda function
2. Retry Jira API call
3. Success → Ticket created: SCM-890
4. Update PR comment with ticket link
5. Send notification to PR author

---

## Implementation Notes

**Technology Stack**:
- **Language**: Java with Spring Boot or Python (for Lambda)
- **Jira API**: Atlassian REST API v3
- **Queue**: AWS SQS for retry queue
- **Cloud**: AWS Lambda or ECS Fargate
- **Monitoring**: AWS CloudWatch

**Configuration**:
- Jira project key: `SCM`
- Jira API credentials: Stored in AWS Secrets Manager
- Retry queue: `scm-jira-ticket-queue` (SQS)
- Max retry attempts: 288 (24 hours with 5-min intervals)
- API timeout: 10 seconds

**Jira API Rate Limiting**:
- Implement token bucket algorithm
- Rate limit: 100 requests/minute
- Queue requests if limit exceeded

**Duplicate Detection**:
- Query Jira JQL: `project = SCM AND "PR Number" = {pr_number}`
- If existing ticket found, add comment instead of creating new

---

## Questions and TBCs

| ID | Question/TBC | Priority | Owner |
|----|--------------|----------|-------|
| TBC-JI-001 | Jira project custom fields configuration | HIGH | DevOps Team |
| TBC-JI-002 | Ticket workflow automation rules | HIGH | Product Owner |
| TBC-JI-003 | SLA tracking integration with Jira | MEDIUM | Architecture Team |
| TBC-JI-004 | Bulk ticket creation optimization | LOW | Development Team |

---

**End of Specification**
