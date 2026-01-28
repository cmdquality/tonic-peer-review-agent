# Jira Integration Agent (Enhanced)

**Version**: 2.0
**Created**: 2026-01-28
**Updated**: 2026-01-28
**Purpose**: Create Jira tickets for code violations, LLD deviations, and pattern rejections with auto-assignment, rich context, and bidirectional PR linking
**Enhancement Stage**: Stage 4, Worker 3

---

## Question 1: Agent Identity and Purpose

**What is this agent and what problem does it solve?**

The Enhanced Jira Integration Agent is a workflow automation and issue tracking agent that creates Jira tickets for code violations, LLD deviations, and pattern rejections discovered during automated peer review. This enhanced version provides intelligent auto-assignment, rich contextual information, bidirectional PR linking, and graceful error handling to ensure complete traceability and accountability.

**Problem Solved**:

Without automated Jira integration with intelligent assignment:
- Issues discovered during automated reviews are not tracked or assigned properly
- PR authors may not be notified of issues requiring their attention
- Management loses visibility into code quality problems
- Audit trails are incomplete for compliance and governance
- Measuring code quality trends becomes difficult
- Ticket assignment requires manual intervention when users are not found
- Rich context from agent findings is lost in generic ticket descriptions

**Enhanced Value Provided**:
- **Automatic issue creation** for all code quality problems
- **Intelligent auto-assignment** to PR authors with multi-tier fallback strategy
- **Rich context** from agent findings with line numbers, code snippets, and remediation guidance
- **Bidirectional PR linking** (Jira ↔ GitHub) for seamless navigation
- **Complete traceability** between GitHub PRs and Jira tickets
- **Graceful error handling** with partial success tracking and retry mechanisms
- **Audit trail** for compliance and governance
- **Management visibility** into code quality issues with detailed metrics
- **Integration with Jira Ticket Skill** for consistent Jira operations across all agents

---

## Question 2: Core Capabilities

**What are the agent's main capabilities?**

### Enhanced Capabilities

1. **Intelligent Ticket Creation with Auto-Assignment**:
   - Create Jira tickets with complete context from agent findings
   - Automatically assign to PR author using intelligent lookup
   - Multi-tier fallback strategy:
     - Tier 1: Lookup by email (direct Jira API search)
     - Tier 2: Lookup by GitHub username (via mapping table)
     - Tier 3: Domain pattern matching (e.g., github_username@company.com)
     - Tier 4: Component owner (from DynamoDB table)
     - Tier 5: Default assignee (from configuration)
     - Tier 6: Unassigned with alert
   - 24-hour cached user lookups to minimize API calls

2. **Rich Context from Agent Findings**:
   - **Agent metadata**: Which agent detected the issue, version, detection time
   - **Detailed findings**: File paths, line numbers, violation types
   - **Code snippets**: Actual problematic code from the PR
   - **Remediation guidance**: Step-by-step fixes and suggested code
   - **Pattern references**: Links to relevant patterns in pattern library
   - **ADF formatting**: Use Atlassian Document Format for rich, structured ticket descriptions
   - **Workflow links**: Direct links to GitHub Actions logs for full context

3. **Bidirectional PR Linking**:
   - **Jira → GitHub**: Create remote link from Jira ticket to GitHub PR
   - **GitHub → Jira**: Add comment on PR with Jira ticket link
   - **Link metadata**: Include PR status (open/closed/merged)
   - **Idempotent linking**: Avoid duplicate links
   - **Link updates**: Update status when PR state changes

4. **Enhanced Error Handling**:
   - **Graceful degradation**: Create ticket even if assignment or linking fails
   - **Partial success tracking**: Return detailed status (SUCCESS/PARTIAL_SUCCESS/FAILURE)
   - **Retry queue**: SQS queue for failed operations with exponential backoff
   - **Error classification**: Distinguish retryable vs non-retryable errors
   - **Detailed error reporting**: Return specific error messages and warnings
   - **Lookup attempt tracking**: Log all assignment lookup attempts for debugging

5. **Integration with Jira Ticket Skill**:
   - **Delegate all Jira operations** to the Jira Ticket Skill
   - **No duplicate Jira API logic** in agent code
   - **Consistent behavior** across all agents using Jira
   - **Centralized rate limiting** and caching
   - **Unified error handling** and retry patterns

6. **Comprehensive Field Population**:
   - Project: SCM (configurable)
   - Issue Type: Code Violation / LLD Deviation / Pattern Rejection
   - Priority: Based on severity mapping (Critical/High/Medium/Low)
   - Assignee: PR author or fallback (with assignment method tracking)
   - Labels: Auto-tag with relevant categories (language, violation types, etc.)
   - Components: Repository/component affected
   - Custom Fields: PR Number, PR URL, Source Agent, Severity, Pattern ID, Workflow Run URL

7. **Workflow Automation**:
   - Auto-transition tickets based on PR status (future enhancement)
   - Comment synchronization from PR to Jira (future enhancement)
   - Notification to assignees via Jira

8. **Observability and Metrics**:
   - CloudWatch metrics for all operations
   - Assignment method tracking (direct, github_mapped, fallback, etc.)
   - Performance monitoring (creation time, lookup time)
   - Cache hit rate tracking
   - Success rate tracking

---

## Question 3: Input Requirements

**What inputs does the agent need?**

### Primary Inputs

**Required Fields**:
- `issue_type`: CODE_VIOLATION / LLD_DEVIATION / PATTERN_REJECTION
- `pr_number`: Integer (e.g., 123)
- `repository`: String in "org/repo" format (e.g., "tonic-scm/order-service")
- `pr_url`: Full GitHub PR URL (e.g., "https://github.com/tonic-scm/order-service/pull/123")
- `severity`: CRITICAL / HIGH / MEDIUM / LOW
- `summary`: String (max 255 chars) - Ticket title
- `agent_findings`: Dictionary containing detailed findings (see schema below)

**Optional Fields for Enhanced Assignment**:
- `pr_author_email`: Email address of PR author (preferred for assignment lookup)
- `pr_author_github_username`: GitHub username of PR author (fallback)
- `pr_author_account_id`: Direct Jira Account ID (skip lookup if provided)

**Optional Enrichment Fields**:
- `workflow_run_url`: Link to GitHub Actions run for full context
- `labels`: List of additional custom labels
- `components`: List of affected components
- `lld_document_url`: Link to LLD document (for LLD deviations)
- `pattern_url`: Link to pattern documentation (for pattern issues)

### Agent Findings Schema

```json
{
  "agent_info": {
    "name": "Code Best Practises Agent",
    "version": "2.1.0",
    "detection_time": "2026-01-28T10:25:30Z",
    "analysis_duration_ms": 4200
  },
  "findings": [
    {
      "finding_id": "CBP-001",
      "type": "NAMING_CONVENTION_VIOLATION",
      "severity": "MEDIUM",
      "file": "src/main/java/com/tonic/OrderService.java",
      "line_start": 45,
      "line_end": 45,
      "code_snippet": "public void get_order(String orderId) { ... }",
      "description": "Method name 'get_order()' violates camelCase naming convention",
      "pattern_id": "JAVA-NC-001",
      "pattern_url": "https://confluence.tonic.com/patterns/JAVA-NC-001",
      "remediation": {
        "description": "Rename method to follow camelCase convention",
        "suggested_fix": "public void getOrder(String orderId) { ... }",
        "effort_estimate": "2 minutes"
      }
    }
  ]
}
```

### For Code Violations

Additional fields in `agent_findings.findings[]`:
- `violation_type`: Specific violation category
- `rule_violated`: Rule ID from linting/analysis tool
- `confidence`: HIGH / MEDIUM / LOW

### For LLD Deviations

Additional fields in `agent_findings.findings[]`:
- `lld_section`: Section reference in LLD document
- `lld_document_url`: Full URL to LLD section
- `lld_version`: Version of LLD document analyzed
- `expected_pattern`: What the LLD specifies
- `actual_implementation`: What was found in the PR
- `deviation_reason`: Why this is considered a deviation
- `impact`: Business/technical impact of the deviation

### For Pattern Rejections

Additional fields in `agent_findings.findings[]`:
- `pattern_candidate`: Name of rejected pattern
- `rejection_reason`: Why pattern was rejected
- `reviewer_comments`: Comments from reviewers
- `architectural_concerns`: List of specific concerns
- `alternative_approach`: Suggested alternative (if any)

### Input Format

JSON payload from calling agent (Code Best Practises Agent, LLD Alignment Review Agent, or Peer Review Documentation Agent):

```json
{
  "issue_type": "CODE_VIOLATION",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "pr_url": "https://github.com/tonic-scm/order-service/pull/123",
  "pr_author_email": "developer1@company.com",
  "pr_author_github_username": "dev1",
  "severity": "MEDIUM",
  "summary": "Code violations in PR #123 (order-service)",
  "workflow_run_url": "https://github.com/tonic-scm/order-service/actions/runs/12345",
  "labels": ["code-quality", "java", "naming-convention"],
  "components": ["order-service"],
  "agent_findings": { ... }
}
```

### Preconditions

- Jira API credentials available in environment (JIRA_EMAIL, JIRA_API_TOKEN via AWS Secrets Manager)
- Jira project "SCM" exists with required issue types (Code Violation, LLD Deviation, Pattern Rejection)
- Jira Ticket Skill is available and properly configured
- PR is in GitHub (valid PR URL)
- Issue details are complete and actionable
- Redis cache available for user lookups (ElastiCache)
- DynamoDB tables available for component ownership and GitHub username mapping
- SQS retry queue available for failed operations

---

## Question 4: Output Specifications

**What does the agent produce?**

### Primary Outputs

**CreateTicketOutput Schema**:

```json
{
  "status": "SUCCESS",
  "ticket_id": "SCM-456",
  "ticket_url": "https://tonic.atlassian.net/browse/SCM-456",
  "ticket_key": "SCM-456",
  "assignee_account_id": "5b10ac8d82e05b22cc7d4ef5",
  "assignee_display_name": "Developer One",
  "assignment_method": "email_direct",
  "created_at": "2026-01-28T10:30:15Z",
  "creation_time_ms": 4200,
  "assignment_lookup_time_ms": 120,
  "pr_linked": true,
  "rich_context_included": true,
  "warnings": [],
  "lookup_attempts": [
    {
      "method": "email_direct",
      "input": "developer1@company.com",
      "result": "SUCCESS",
      "account_id": "5b10ac8d82e05b22cc7d4ef5",
      "duration_ms": 120
    }
  ]
}
```

**Status Values**:
- `SUCCESS`: Ticket created, assigned, and PR linked successfully
- `PARTIAL_SUCCESS`: Ticket created but with warnings (e.g., assignment failed, PR link pending)
- `FAILURE`: Ticket creation failed completely

**Assignment Methods** (tracked for observability):
- `direct`: Used assignee_account_id directly (no lookup)
- `email_direct`: Found user via Jira API email search
- `github_mapped`: Found user via GitHub username mapping table
- `domain_pattern`: Constructed email from GitHub username + domain
- `fallback_component`: Assigned to component owner from DynamoDB
- `fallback_default`: Assigned to default assignee from config
- `unassigned`: Could not assign, ticket created without assignee

### Jira Ticket Content

**Summary**: Auto-generated from issue type and PR info
- Example: "Code violations in PR #123 (order-service)"

**Description**: Rich ADF (Atlassian Document Format) with:
- **Info Panel**: Agent name, version, detection time, workflow run link
- **Issue Summary**: PR number, repository, author, severity, violation count
- **Findings Section**: For each finding:
  - Finding ID and type
  - File path and line numbers
  - Code snippet (in code block with syntax highlighting)
  - Detailed description
  - Pattern reference (as hyperlink)
  - Remediation guidance (in success panel)
  - Suggested fix (in code block)
- **Action Required**: Checklist of steps to resolve

**Fields Populated**:
- **Issue Type**: Code Violation / LLD Deviation / Pattern Rejection
- **Priority**: HIGH (Critical severity), MEDIUM (High/Medium severity), LOW (Low severity)
- **Assignee**: PR author or fallback (Account ID)
- **Reporter**: SCM Automation Agent (service account)
- **Labels**: ["code-quality", "java", "naming-convention", "pr-123", ...]
- **Components**: ["order-service"]
- **Custom Fields**:
  - `PR Number`: 123 (custom field ID: customfield_10001)
  - `PR URL`: https://github.com/... (customfield_10002)
  - `Source Agent`: Code Best Practises Agent (customfield_10003)
  - `Severity`: MEDIUM (customfield_10004)
  - `Pattern ID`: JAVA-NC-001 (customfield_10005, if applicable)
  - `Workflow Run URL`: https://github.com/.../actions/runs/12345 (customfield_10006)

**Remote Link**:
- Link from Jira ticket to GitHub PR
- GlobalID: `system=github&id=tonic-scm/order-service/pull/123`
- Title: "PR #123: Add order validation logic"
- Status: Open/Closed/Merged

### GitHub PR Comment

Markdown-formatted comment posted on PR:

```markdown
## 📋 Jira Ticket Created

**Ticket**: [SCM-456](https://tonic.atlassian.net/browse/SCM-456) - Code violations in PR #123 (order-service)
**Status**: Open
**Priority**: Medium
**Assignee**: @developer1 (Developer One)

**Assignment Method**: Direct email lookup

This ticket tracks the code violations detected by Code Best Practises Agent v2.1.0 that must be fixed before PR can be merged.

**Findings**: 3 violations detected
- Naming convention violations (2)
- Exception handling violations (1)

**Next Steps**:
1. Review violations in Jira ticket
2. Apply suggested fixes
3. Push updates to PR
4. Request re-review

---
_Generated by Jira Integration Agent v2.0 | [View Workflow Logs](https://github.com/tonic-scm/order-service/actions/runs/12345)_
```

### Artifacts Created

1. **Jira Ticket**: Complete ticket with all fields, rich description, and remote link
2. **GitHub PR Comment**: Comment with ticket link and summary
3. **CloudWatch Logs**: Comprehensive audit trail with:
   - Ticket creation event
   - Assignment lookup attempts
   - Performance metrics
   - Any warnings or errors
4. **CloudWatch Metrics**:
   - Ticket creation duration
   - Assignment lookup duration
   - Assignment method distribution
   - Success/failure rates
   - Cache hit rates

---

## Question 5: Constraints and Limitations

**What are the boundaries and limitations?**

### Operational Constraints

- **Jira API Dependency**: Cannot create tickets without Jira API access
- **Project Scope**: Limited to SCM project in Jira (configurable via environment)
- **Read-Only PR**: Cannot modify PR code or fix issues (only creates tickets)
- **Rate Limiting**: Jira API rate limits apply (100 requests/minute - managed by Jira Ticket Skill)
- **Assignment Dependency**: Auto-assignment depends on user existence in Jira
- **Network Dependency**: Requires connectivity to Jira API, Redis, DynamoDB, and SQS

### Limitations

- **Jira Availability**: Ticket creation depends on Jira availability (mitigated by retry queue)
- **User Not Found**: Cannot auto-assign if user not in Jira and no fallback available
- **Issue Type Configuration**: Limited to configured issue types in Jira project
- **Custom Fields**: Requires custom fields to be configured in Jira project
- **Manual Resolution**: Cannot automatically resolve tickets (requires human action)
- **One-Way Comment Sync**: Comment synchronization is GitHub → Jira only (not bidirectional)
- **Cache Dependency**: User lookup performance depends on Redis availability
- **Fallback Data**: Component owner and username mapping depend on data in DynamoDB

### Guardrails

- **NEVER** create duplicate tickets for same PR (check for existing tickets via Jira API)
- **NEVER** create tickets without sufficient context (must have actionable description)
- **NEVER** modify existing tickets (only create new or add comments)
- **ALWAYS** link tickets to PRs for traceability (if linking fails, queue for retry)
- **ALWAYS** use Jira Ticket Skill for all Jira operations (no direct Jira API calls)
- **ALWAYS** log all operations to CloudWatch for audit trail
- **ALWAYS** track assignment method for observability
- **ALWAYS** handle errors gracefully (partial success is acceptable)

### Performance Constraints

- **Ticket Creation Time**: Target P95 < 10 seconds (includes assignment lookup and PR linking)
- **User Lookup Time**: Target P95 < 200ms (with cache hit)
- **Cache Hit Rate**: Target > 90% for user lookups
- **Assignment Success Rate**: Target > 95% direct assignment, > 99% with fallbacks

---

## Question 6: Behavioral Patterns and Decision Rules

**How should the agent behave and make decisions?**

### Behavioral Patterns

**Deduplication**:
- Before creating ticket, query Jira: `project = SCM AND "PR Number" = {pr_number}`
- If existing open ticket found → Add comment instead of creating new
- If existing closed ticket found → Create new ticket with reference to previous
- Use custom field "PR Number" for reliable deduplication

**Actionable Content**:
- Tickets must have clear action items in "Action Required" section
- Include enough context for assignee to understand and fix issue
- Link to pattern documentation for reference
- Provide code snippets showing problem and suggested fix

**Severity Mapping**:
- Map agent severity to Jira priority consistently:
  - CRITICAL → High Priority
  - HIGH → High Priority
  - MEDIUM → Medium Priority
  - LOW → Low Priority
- For Code Violations, also consider violation count:
  - 11+ violations → High Priority (override)
  - 4-10 violations → Medium Priority
  - 1-3 violations → Use severity mapping

**Fast Creation**:
- Create tickets within 10 seconds (P95 target)
- Use cached user lookups to avoid API delays
- Perform PR linking asynchronously if needed

**Fail-Safe**:
- If Jira unavailable, queue ticket payload to SQS
- Retry with exponential backoff (5 min, 15 min, 1 hour, 4 hours, 24 hours)
- Post PR comment: "Jira ticket pending (Jira temporarily unavailable)"
- Don't lose issues even if Jira is down

**Graceful Degradation**:
- Create ticket even if assignment fails
- Create ticket even if PR linking fails
- Return PARTIAL_SUCCESS status with warnings
- Queue failed operations for retry

### Decision Rules

#### When Triggered by Code Best Practises Agent

1. **Issue Type**: "Code Violation"
2. **Priority Calculation**:
   ```
   IF severity == "CRITICAL" OR violation_count > 10:
       priority = "High"
   ELSE IF severity == "HIGH" OR violation_count > 3:
       priority = "Medium"
   ELSE:
       priority = "Low"
   ```
3. **Assignment**: Assign to PR author (with fallback chain)
4. **Labels**: ["code-quality", {language}, {violation-types}]
5. **Description**: Use Code Violation ADF template with:
   - Agent info and version
   - Violation details with line numbers
   - Code snippets
   - Remediation guidance

#### When Triggered by LLD Alignment Review Agent

1. **Issue Type**: "LLD Deviation"
2. **Priority Mapping**:
   - CRITICAL → High
   - HIGH → High
   - MEDIUM → Medium
   - LOW → Low
3. **Assignment**: Assign to PR author, add architects as watchers (future enhancement)
4. **Labels**: ["lld-deviation", "architectural", {component}]
5. **Description**: Use LLD Deviation ADF template with:
   - LLD section reference (as hyperlink)
   - Expected vs Actual comparison
   - Impact analysis
   - Remediation suggestions
6. **Link to LLD Document**: Include in description and custom field

#### When Triggered by Peer Review Documentation Agent

1. **Issue Type**: "Pattern Rejection"
2. **Priority**: Medium (default for pattern rejections)
3. **Assignment**: Assign to PR author
4. **Labels**: ["pattern-rejection", "architectural", {category}]
5. **Description**: Use Pattern Rejection ADF template with:
   - Pattern candidate name
   - Rejection reason
   - Reviewer comments
   - Architectural concerns
   - Alternative approach (if available)

### Assignment Lookup Decision Flow

```
START
  │
  ├─ Has assignee_account_id? ──YES──> Use direct (no lookup)
  │                                    STATUS: SUCCESS, method: direct
  │
  NO
  │
  ├─ Has pr_author_email? ──YES──> Check Redis cache
  │                                  │
  │                                  ├─ Cache hit? ──YES──> Use cached Account ID
  │                                  │                     STATUS: SUCCESS, method: email_direct (cached)
  │                                  │
  │                                  NO
  │                                  │
  │                                  └─> Jira API user search by email
  │                                      │
  │                                      ├─ Found? ──YES──> Cache result, return Account ID
  │                                      │                  STATUS: SUCCESS, method: email_direct
  │                                      │
  │                                      NO
  │                                      │
  │                                      └─> Continue to next tier
  │
  ├─ Has pr_author_github_username? ──YES──> Query DynamoDB username mapping
  │                                           │
  │                                           ├─ Found? ──YES──> Cache result, return Account ID
  │                                           │                  STATUS: SUCCESS, method: github_mapped
  │                                           │
  │                                           NO
  │                                           │
  │                                           └─> Try domain pattern: {username}@{domain}
  │                                               │
  │                                               ├─ Valid email? ──YES──> Jira API search
  │                                               │                        │
  │                                               │                        ├─ Found? ──YES──> Cache, return
  │                                               │                        │                  method: domain_pattern
  │                                               │                        │
  │                                               │                        NO
  │                                               │                        │
  │                                               NO                       └─> Continue to fallback
  │                                               │
  │                                               └─> Continue to fallback
  │
  └─> FALLBACK STRATEGY
      │
      ├─ Tier 1: Component Owner Lookup
      │   Query DynamoDB: component-ownership[repository][component]
      │   Found? ──YES──> Return owner Account ID
      │                   STATUS: SUCCESS, method: fallback_component
      │
      NO
      │
      ├─ Tier 2: Default Assignee
      │   Read JIRA_DEFAULT_ASSIGNEE_ACCOUNT_ID from config
      │   Valid? ──YES──> Return default Account ID
      │                   STATUS: SUCCESS, method: fallback_default
      │
      NO
      │
      └─ Tier 3: Unassigned
          Create ticket without assignee
          Add comment: "Auto-assignment failed: PR author not found in Jira"
          Add label: "auto-assignment-failed"
          Create CloudWatch alarm: "UnassignedJiraTicket"
          STATUS: PARTIAL_SUCCESS, method: unassigned
```

### Error Handling Decision Flow

```
TRY Create Jira Ticket
│
├─ SUCCESS ──> Continue to Assignment
│
└─ FAILURE
    │
    ├─ Authentication Error (401)?
    │   └─> CRITICAL ALARM → Fail immediately
    │       Return: STATUS=FAILURE, error="Jira authentication failed"
    │
    ├─ Rate Limit (429)?
    │   └─> Respect Retry-After header
    │       Queue to SQS with delay
    │       Post PR comment: "Jira ticket pending (rate limited)"
    │       Return: STATUS=FAILURE (will retry)
    │
    ├─ Timeout (504) or Network Error?
    │   └─> Retry with exponential backoff (3 attempts)
    │       If still failing: Queue to SQS
    │       Post PR comment: "Jira ticket pending"
    │       Return: STATUS=FAILURE (queued for retry)
    │
    ├─ Invalid Input (400)?
    │   └─> Log error, DO NOT RETRY
    │       Return: STATUS=FAILURE, error="Invalid input: {details}"
    │
    └─ Server Error (500)?
        └─> Retry with exponential backoff (3 attempts)
            If still failing: Queue to SQS
            Return: STATUS=FAILURE (queued for retry)

IF Ticket Created Successfully:
  │
  TRY Assign Ticket
  │
  ├─ Assignment SUCCESS ──> Continue to PR Linking
  │
  └─ Assignment FAILURE
      │
      ├─ User Not Found?
      │   └─> Try fallback chain
      │       If all fallbacks fail:
      │         - Create ticket without assignee
      │         - Add warning to output
      │         - STATUS = PARTIAL_SUCCESS
      │
      └─> Other Assignment Error
          └─> Log warning, continue
              STATUS = PARTIAL_SUCCESS

  TRY Link PR to Jira
  │
  ├─ Linking SUCCESS ──> Post PR Comment → Return SUCCESS
  │
  └─ Linking FAILURE
      │
      └─> Queue link operation to SQS for retry
          Add warning to output
          Post PR comment (without Jira link yet)
          STATUS = PARTIAL_SUCCESS
```

### Retry Queue Processing

For failed operations queued to SQS:

**Retry Schedule**:
1. First retry: 5 minutes after failure
2. Second retry: 15 minutes after first retry
3. Third retry: 1 hour after second retry
4. Fourth retry: 4 hours after third retry
5. Fifth retry: 24 hours after fourth retry
6. If still failing after 24 hours: Create critical alarm, email ops team

**Idempotency**:
- Use ticket key or PR URL as idempotency key
- Check if operation already completed before retrying
- Avoid creating duplicate tickets

---

## Question 7: Error Handling and Edge Cases

**How should the agent handle errors and edge cases?**

### Error Detection

**Jira API Errors**:
- Authentication failure (401)
- Permission denied (403)
- Project/issue type not found (404)
- Rate limiting (429)
- Timeout (504)
- Network connectivity issues
- Server errors (500, 502, 503)

**Assignment Errors**:
- User not found in Jira
- Invalid Account ID
- Assignment permission denied
- Lookup timeout

**Linking Errors**:
- Remote link creation failed
- Duplicate global ID
- Invalid PR URL
- GitHub API unavailable

**Data Errors**:
- Missing required fields
- Invalid severity value
- Malformed agent findings
- Empty code snippets

### Error Response Strategy

| Error Type | HTTP Code | Retryable | Action |
|------------|-----------|-----------|--------|
| Authentication failure | 401 | No | Critical alarm, fail immediately |
| Permission denied | 403 | No | Log error, create alarm, fail |
| User not found | 404 | No | Use fallback assignment |
| Project not found | 404 | No | Critical alarm, fail immediately |
| Rate limit exceeded | 429 | Yes | Respect Retry-After, queue |
| Timeout | 504 | Yes | Exponential backoff (3 attempts) |
| Network error | N/A | Yes | Exponential backoff (3 attempts) |
| Invalid input | 400 | No | Log error, return to caller |
| Server error | 500 | Yes | Exponential backoff (3 attempts) |
| Assignment failed | N/A | No | Use fallback, partial success |
| Linking failed | N/A | Yes | Queue for retry, partial success |

### Fallback Strategies

**For Ticket Creation Failure**:
1. Retry with exponential backoff (3 attempts: 2s, 4s, 8s)
2. If still failing, queue to SQS for async retry
3. Post PR comment: "Jira ticket creation pending (Jira temporarily unavailable)"
4. Create CloudWatch alarm if repeated failures
5. Maintain retry for up to 24 hours
6. If 24-hour retry exhausted: Critical alarm, email ops team

**For Assignment Failure**:
1. Try fallback assignment chain (component owner → default assignee)
2. If all fallbacks fail: Create ticket without assignee
3. Add Jira comment: "Auto-assignment failed: PR author not found. Please assign manually."
4. Add label: "auto-assignment-failed"
5. Return PARTIAL_SUCCESS with warning
6. Create CloudWatch metric for tracking

**For PR Linking Failure**:
1. Create ticket successfully first (most critical operation)
2. Queue PR link operation to SQS for async retry
3. Return PARTIAL_SUCCESS with warning: "PR link pending"
4. Retry linking every 5 minutes for up to 1 hour
5. Post PR comment once linking succeeds
6. If linking never succeeds: Manual intervention required (alarm)

### Edge Cases

#### Edge Case 1: PR Already Has Jira Ticket

**Scenario**: Calling agent triggers ticket creation but ticket already exists for this PR.

**Detection**: Query Jira with `project = SCM AND "PR Number" = {pr_number}`

**Handling**:
- If existing ticket is OPEN: Add comment instead of creating new
- Comment content: "Additional findings detected by {agent_name} v{version}"
- Append findings to existing ticket description (via comment)
- Return existing ticket ID with status: SUCCESS
- If existing ticket is CLOSED: Create new ticket with reference to previous
- Reference format: "Previous ticket: [SCM-123]"

#### Edge Case 2: Multiple Issues in Same PR

**Scenario**: Multiple agents (e.g., Code Best Practises + LLD Alignment) detect issues in same PR.

**Handling**:
- Create **separate tickets** for each issue type (Code Violation vs LLD Deviation)
- Each ticket has unique issue type and appropriate assignee
- Link both tickets to same PR (via remote links)
- Post single PR comment with all ticket links
- Use labels to group related tickets: "pr-123"

#### Edge Case 3: Issue Resolved Before Ticket Created

**Scenario**: PR is updated/closed before Jira ticket is created (e.g., due to retry delay).

**Handling**:
- **Still create ticket** for audit trail (compliance requirement)
- Check PR status before creating ticket
- If PR is closed: Set ticket status to "Resolved" immediately
- Add comment: "Issue was resolved before ticket creation (PR closed)"
- This maintains complete audit trail for compliance

#### Edge Case 4: PR Author Not in Jira

**Scenario**: PR author has no Jira account (e.g., external contributor, new employee).

**Handling**:
1. Try GitHub username mapping (may exist for external contributors)
2. Try domain pattern (username@company.com)
3. Fall back to component owner
4. Fall back to default assignee
5. If all fail: Create unassigned ticket
6. Add comment: "Please assign to appropriate team member"
7. Add label: "auto-assignment-failed"
8. Create CloudWatch alarm for manual review

#### Edge Case 5: Component Owner Not Configured

**Scenario**: Repository or component has no entry in component-ownership DynamoDB table.

**Handling**:
1. Skip component owner fallback
2. Proceed to default assignee fallback
3. Log warning: "Component owner not configured for {repository}/{component}"
4. Create CloudWatch metric to track missing mappings
5. Ops team should populate component ownership table

#### Edge Case 6: Jira API Completely Unavailable

**Scenario**: Jira is down for extended period (e.g., maintenance, outage).

**Handling**:
1. Detect Jira unavailability (multiple consecutive failures)
2. Queue all ticket payloads to SQS immediately (skip retries)
3. Post PR comments: "Jira ticket pending (Jira under maintenance)"
4. Create CloudWatch alarm: "JiraExtendedOutage"
5. Process queue when Jira is back online
6. Lambda function polls SQS and retries ticket creation
7. Update PR comments once tickets are created

#### Edge Case 7: Cache (Redis) Unavailable

**Scenario**: Redis ElastiCache is unavailable.

**Handling**:
- Bypass cache for user lookups
- Make direct Jira API calls (slower but functional)
- Log warning: "User lookup cache unavailable, using direct API"
- Create CloudWatch alarm if cache is down for >5 minutes
- Graceful degradation: System continues to work, just slower

#### Edge Case 8: DynamoDB Tables Unavailable

**Scenario**: Component ownership or username mapping tables are unavailable.

**Handling**:
- Skip GitHub username mapping fallback
- Skip component owner fallback
- Proceed directly to default assignee
- Log warning: "DynamoDB tables unavailable, using default assignment"
- Create CloudWatch alarm
- Return PARTIAL_SUCCESS if default assignee works

#### Edge Case 9: Duplicate Remote Link

**Scenario**: Attempting to create remote link but one already exists (idempotency issue).

**Handling**:
1. Check for existing remote link with same globalId
2. If exists: Update status instead of creating new
3. If global ID conflict with different content: Delete old, create new
4. Use globalId format: `system=github&id={org}/{repo}/pull/{number}`

#### Edge Case 10: Rate Limit Exceeded Despite Rate Limiter

**Scenario**: Jira returns 429 even though Jira Ticket Skill has rate limiter.

**Handling**:
- Read Retry-After header from Jira response
- Respect Retry-After delay
- Queue operation to SQS with calculated delay
- Log warning: "Rate limit exceeded despite rate limiter"
- Investigate rate limiter configuration
- Possible causes: Multiple agents running in parallel, rate limit changed

---

## Question 8: Success Criteria

**How do you know the agent succeeded?**

### Primary Success Criteria

The agent has succeeded when:

1. **Ticket Creation**: All issues result in Jira tickets with complete context
   - 100% of issues detected result in tickets (including queued)
   - All tickets have rich, actionable descriptions with agent findings
   - All tickets are linked to PRs (bidirectional)

2. **Fast Processing**: Tickets created within performance targets
   - Ticket creation time P95 < 10 seconds
   - User lookup time P95 < 200ms (with cache)
   - PR linking time P95 < 2 seconds

3. **Intelligent Assignment**: Correct assignees with high success rate
   - Direct assignment rate > 95% (email or GitHub username)
   - Overall assignment rate > 99% (including fallbacks)
   - Assignment method tracked for all tickets
   - Cache hit rate > 90% for user lookups

4. **Complete Traceability**: Full audit trail maintained
   - 100% of tickets linked to PRs via remote links
   - 100% of PRs have comments with Jira ticket links
   - All operations logged to CloudWatch
   - All assignment attempts tracked

5. **No Data Loss**: Zero issues lost to failures
   - Retry queue handles all transient failures
   - Partial success when possible (ticket created even if linking fails)
   - Tickets created even during Jira outages (via queue)

6. **Graceful Error Handling**: System degrades gracefully
   - Partial success tracked and reported
   - Fallback assignment works when user not found
   - Retry queue processes failed operations
   - Appropriate alarms created for manual intervention

### Quality Indicators

**Performance Metrics**:
- Ticket creation success rate > 99% (first attempt)
- Ticket creation success rate = 100% (including retries)
- Ticket creation time P95 < 10 seconds
- Ticket creation time P99 < 15 seconds
- User lookup time P95 < 200ms
- Cache hit rate > 90%

**Assignment Metrics**:
- Direct assignment rate (email_direct) > 80%
- GitHub mapped assignment rate > 10%
- Fallback assignment rate < 10%
- Unassigned ticket rate < 1%
- Assignment lookup failures < 1%

**Linking Metrics**:
- PR link success rate (first attempt) > 95%
- PR link success rate (with retries) > 99%
- Duplicate link rate = 0%

**Error Metrics**:
- API error rate < 1%
- Rate limit errors = 0% (managed by rate limiter)
- Retry queue size < 10 (steady state)
- Retry queue age P95 < 5 minutes
- Failed retries (24h exhausted) < 0.1%

**Audit Trail Metrics**:
- 100% of tickets have CloudWatch logs
- 100% of assignment attempts logged
- 100% of errors logged with stack traces

### Business Value (ATSQ - Automated Time Savings Quantification)

**Expected Time Savings**:
- **ATSQ**: 92% time savings
- **Baseline**: Manual issue tracking = 4 hours per PR with issues
  - Identifying issues manually: 1 hour
  - Creating Jira tickets: 30 minutes
  - Populating fields and descriptions: 1 hour
  - Finding and assigning users: 30 minutes
  - Linking to PRs: 30 minutes
  - Categorizing and prioritizing: 30 minutes
- **Automated**: 10 seconds agent execution + 19.83 minutes human verification
  - Agent creates ticket: 10 seconds
  - Human triage and priority validation: 10 minutes
  - Human verifies assignment: 5 minutes
  - Human confirms categorization: 4.83 minutes
- **Time Saved**: 3 hours 40 minutes per issue
- **Calculation**: (240 min - 20 min) / 240 min = 92% ATSQ

**Enhanced Value from v1.0 to v2.0**:
- **Auto-assignment**: Saves additional 5-10 minutes per ticket (manual lookup eliminated)
- **Rich context**: Reduces developer investigation time by 10-15 minutes
- **Bidirectional linking**: Saves 2-3 minutes navigation time per issue
- **Graceful degradation**: Prevents complete workflow failure (business continuity)

**Verification Method**:
- Human verification required: 20 minutes per ticket
- Triage to confirm severity and priority
- Validate assignment is correct
- Review findings and ensure actionable

**Category**: Labor Elimination (near-complete automation)

---

## Question 9: Usage Context and Workflow

**When and how is this agent used?**

### Invocation Context

**Trigger Type**: Conditional invocation by other agents
- Only invoked when problems are detected
- Not invoked for successful validations

**Invoking Agents**:
1. **Code Best Practises Agent** (Step 1 in workflow)
   - Invokes when code violations detected
   - Provides violation details and remediation
2. **LLD Alignment Review Agent** (Step 3 in workflow)
   - Invokes when LLD deviations detected
   - Provides expected vs actual comparisons
3. **Peer Review Documentation Agent** (Step 5 in workflow)
   - Invokes when pattern rejected by reviewers
   - Provides rejection reasons and reviewer feedback

**Execution Mode**:
- Non-interactive: Runs automatically via agent-to-agent API call
- No human intervention required during execution
- Human intervention only needed for:
  - Resolving tickets (fixing issues)
  - Manual assignment (if auto-assignment fails)

### Workflow Integration

**Position in Configuration Management Platform Workflow**:
- **Step 7**: Jira Integration (conditional)
- Runs after issues are detected by upstream agents
- Blocks PR merge until tickets are created (ensures tracking)

#### Integration Flow

```
┌─────────────────────────────────────────────────────────────┐
│         Configuration Management Platform Workflow          │
└─────────────────────────────────────────────────────────────┘

Step 1: Code Best Practises Agent
  │
  ├─ Violations detected? ──NO──> Continue to Step 2
  │
  YES
  │
  └──> Invoke Jira Integration Agent
       │
       ├─ Create ticket: "Code Violation"
       ├─ Assign to PR author
       ├─ Link to PR
       └─ Post PR comment
       │
       └──> Block PR merge (violations must be fixed)

Step 3: LLD Alignment Review Agent
  │
  ├─ Deviations detected? ──NO──> Continue to Step 4
  │
  YES
  │
  └──> Invoke Jira Integration Agent
       │
       ├─ Create ticket: "LLD Deviation"
       ├─ Assign to PR author (+ architect watchers)
       ├─ Link to PR and LLD document
       └─ Post PR comment
       │
       └──> Block PR merge (requires fix OR architectural approval)

Step 5: Peer Review Documentation Agent
  │
  ├─ Pattern rejected? ──NO──> Continue to Step 6
  │
  YES
  │
  └──> Invoke Jira Integration Agent
       │
       ├─ Create ticket: "Pattern Rejection"
       ├─ Assign to PR author
       ├─ Link to PR and pattern docs
       └─ Post PR comment
       │
       └──> Block PR merge (requires refactor OR new architectural decision)
```

### Agent-to-Agent Integration

**Integration with Jira Ticket Skill**:

```python
# Example: Code Best Practises Agent invokes Jira Integration Agent

# In code_best_practises_agent.py
def handle_violations(pr_data, violations):
    """Called when violations are detected."""

    # Prepare payload for Jira Integration Agent
    jira_payload = {
        "issue_type": "CODE_VIOLATION",
        "pr_number": pr_data['number'],
        "repository": pr_data['repository'],
        "pr_url": pr_data['html_url'],
        "pr_author_email": pr_data['author']['email'],
        "pr_author_github_username": pr_data['author']['username'],
        "severity": calculate_severity(violations),
        "summary": f"Code violations in PR #{pr_data['number']}",
        "workflow_run_url": get_current_workflow_url(),
        "labels": ["code-quality", pr_data['language']],
        "components": [pr_data['repository'].split('/')[-1]],
        "agent_findings": {
            "agent_info": {
                "name": "Code Best Practises Agent",
                "version": "2.1.0",
                "detection_time": datetime.utcnow().isoformat()
            },
            "findings": format_violations(violations)
        }
    }

    # Invoke Jira Integration Agent
    jira_agent = JiraIntegrationAgent()
    result = jira_agent.create_ticket(jira_payload)

    if result.status in ["SUCCESS", "PARTIAL_SUCCESS"]:
        logger.info(f"Jira ticket created: {result.ticket_id}")
        return result
    else:
        logger.error(f"Failed to create Jira ticket: {result.error}")
        # Still block PR merge, but alert ops team
        create_alert("JiraTicketCreationFailed", result.error)
        raise JiraIntegrationError(result.error)
```

**Integration with Jira Ticket Skill**:

```python
# In jira_integration_agent.py

from skills.jira_ticket_skill import JiraTicketSkill, CreateTicketInput
from skills.jira_ticket_skill.templates import generate_ticket_description

class JiraIntegrationAgent:
    def __init__(self):
        # Initialize Jira Ticket Skill (reads config from environment)
        self.jira_skill = JiraTicketSkill.from_environment()

    def create_ticket(self, payload: dict) -> dict:
        """Create Jira ticket using Jira Ticket Skill."""

        # Generate ADF description from agent findings
        description = generate_ticket_description(
            issue_type=payload['issue_type'],
            agent_findings=payload['agent_findings'],
            pr_data=payload
        )

        # Prepare input for Jira Ticket Skill
        skill_input = CreateTicketInput(
            issue_type=self._map_issue_type(payload['issue_type']),
            summary=payload['summary'],
            description=description,
            pr_author_email=payload.get('pr_author_email'),
            pr_author_github_username=payload.get('pr_author_github_username'),
            pr_url=payload['pr_url'],
            pr_number=payload['pr_number'],
            repository=payload['repository'],
            severity=payload['severity'],
            labels=payload.get('labels', []),
            components=payload.get('components', []),
            workflow_run_url=payload.get('workflow_run_url'),
            agent_findings=payload['agent_findings']
        )

        # Delegate to Jira Ticket Skill
        skill_output = self.jira_skill.create_ticket(skill_input)

        # Post PR comment with ticket link
        if skill_output.status in ["SUCCESS", "PARTIAL_SUCCESS"]:
            self._post_pr_comment(
                payload['repository'],
                payload['pr_number'],
                skill_output
            )

        # Return output (includes assignment details, performance metrics, etc.)
        return skill_output

    def _map_issue_type(self, issue_type: str) -> str:
        """Map agent issue type to Jira issue type."""
        mapping = {
            "CODE_VIOLATION": "Code Violation",
            "LLD_DEVIATION": "LLD Deviation",
            "PATTERN_REJECTION": "Pattern Rejection"
        }
        return mapping.get(issue_type, issue_type)

    def _post_pr_comment(self, repository: str, pr_number: int, output: dict):
        """Post comment on PR with Jira ticket link."""
        comment = self._generate_pr_comment(output)
        github_api.post_comment(repository, pr_number, comment)
```

### Workflow Position

**Activity Diagram Reference**: See LLD Section 8.2 - Activity Diagram

**Step 7: Jira Integration (Conditional)**
- **Precondition**: Issue detected by upstream agent
- **Input**: Issue details, PR data, agent findings
- **Process**: Create ticket, assign, link, comment
- **Output**: Ticket ID, status, assignment details
- **Next Step**: Block PR merge OR continue (depending on issue type)

---

## Question 10: Example Interaction

**Provide concrete examples of the agent in action**

### Example 1: Code Violation with Successful Auto-Assignment

**Scenario**: Code Best Practises Agent detects 5 violations in PR #123.

**Input from Code Best Practises Agent**:

```json
{
  "issue_type": "CODE_VIOLATION",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "pr_url": "https://github.com/tonic-scm/order-service/pull/123",
  "pr_author_email": "developer1@company.com",
  "pr_author_github_username": "dev1",
  "severity": "MEDIUM",
  "summary": "Code violations in PR #123 (order-service)",
  "workflow_run_url": "https://github.com/tonic-scm/order-service/actions/runs/12345",
  "labels": ["code-quality", "java", "naming-convention", "exception-handling"],
  "components": ["order-service"],
  "agent_findings": {
    "agent_info": {
      "name": "Code Best Practises Agent",
      "version": "2.1.0",
      "detection_time": "2026-01-28T10:25:30Z",
      "analysis_duration_ms": 4200
    },
    "findings": [
      {
        "finding_id": "CBP-001",
        "type": "NAMING_CONVENTION_VIOLATION",
        "severity": "MEDIUM",
        "file": "src/main/java/com/tonic/OrderService.java",
        "line_start": 45,
        "line_end": 45,
        "code_snippet": "public void get_order(String orderId) {\n    // ...\n}",
        "description": "Method name 'get_order()' violates camelCase naming convention",
        "pattern_id": "JAVA-NC-001",
        "pattern_url": "https://confluence.tonic.com/patterns/JAVA-NC-001",
        "remediation": {
          "description": "Rename method to follow camelCase convention",
          "suggested_fix": "public void getOrder(String orderId) {\n    // ...\n}",
          "effort_estimate": "2 minutes"
        }
      },
      {
        "finding_id": "CBP-002",
        "type": "EXCEPTION_HANDLING_VIOLATION",
        "severity": "HIGH",
        "file": "src/main/java/com/tonic/OrderService.java",
        "line_start": 78,
        "line_end": 82,
        "code_snippet": "try {\n    processOrder(order);\n} catch (Exception e) {\n    log.error(\"Error\", e);\n}",
        "description": "Generic Exception catch block should use specific exception types",
        "pattern_id": "JAVA-EH-003",
        "pattern_url": "https://confluence.tonic.com/patterns/JAVA-EH-003",
        "remediation": {
          "description": "Replace generic Exception with specific exception types (OrderProcessingException, ValidationException)",
          "suggested_fix": "try {\n    processOrder(order);\n} catch (OrderProcessingException | ValidationException e) {\n    log.error(\"Order processing failed\", e);\n    throw new ServiceException(\"Failed to process order\", e);\n}",
          "effort_estimate": "5 minutes"
        }
      }
    ]
  }
}
```

**Processing by Jira Integration Agent**:

1. **Check for Existing Ticket**:
   - Query Jira: `project = SCM AND "PR Number" = 123`
   - Result: No existing ticket found

2. **Generate ADF Description**:
   - Use Code Violation ADF template
   - Include agent info panel with link to workflow logs
   - Format each finding with tables, code blocks, remediation panels

3. **User Lookup**:
   - Input: `pr_author_email = "developer1@company.com"`
   - Check Redis cache: Cache miss
   - Call Jira API user search: Found user
   - Account ID: `5b10ac8d82e05b22cc7d4ef5`
   - Display Name: `Developer One`
   - Cache result (TTL: 24 hours)
   - Lookup method: `email_direct`
   - Lookup time: 145ms

4. **Create Ticket via Jira Ticket Skill**:
   - Issue Type: Code Violation
   - Summary: "Code violations in PR #123 (order-service)"
   - Priority: Medium (5 violations, severity MEDIUM)
   - Assignee: 5b10ac8d82e05b22cc7d4ef5
   - Labels: ["code-quality", "java", "naming-convention", "exception-handling", "pr-123"]
   - Components: ["order-service"]
   - Custom Fields: PR Number=123, PR URL, Source Agent, Severity=MEDIUM, Workflow Run URL
   - Creation time: 3.2 seconds

5. **Link PR to Jira**:
   - Create remote link with globalId: `system=github&id=tonic-scm/order-service/pull/123`
   - Title: "PR #123: Add order validation logic"
   - Status: Open
   - Link creation time: 0.8 seconds

6. **Post PR Comment**:
   - Post comment on PR #123 with Jira ticket link and summary

**Output**:

```json
{
  "status": "SUCCESS",
  "ticket_id": "SCM-456",
  "ticket_url": "https://tonic.atlassian.net/browse/SCM-456",
  "ticket_key": "SCM-456",
  "assignee_account_id": "5b10ac8d82e05b22cc7d4ef5",
  "assignee_display_name": "Developer One",
  "assignment_method": "email_direct",
  "created_at": "2026-01-28T10:30:15Z",
  "creation_time_ms": 4200,
  "assignment_lookup_time_ms": 145,
  "pr_linked": true,
  "rich_context_included": true,
  "warnings": [],
  "lookup_attempts": [
    {
      "method": "email_direct",
      "input": "developer1@company.com",
      "result": "SUCCESS",
      "account_id": "5b10ac8d82e05b22cc7d4ef5",
      "display_name": "Developer One",
      "cached": false,
      "duration_ms": 145
    }
  ]
}
```

**Jira Ticket Created (SCM-456)**:

**Summary**: Code violations in PR #123 (order-service)

**Description** (ADF rendered):

> **ℹ️ Info Panel**
> Automated detection by **Code Best Practises Agent v2.1.0** | [View Full Logs](https://github.com/tonic-scm/order-service/actions/runs/12345)

> ## Issue Summary
> - PR: #123 | Repository: tonic-scm/order-service
> - Author: developer1 | Severity: MEDIUM
> - Issues Detected: 5 violations

> ## Findings

> ### Finding 1: Naming Convention Violation
>
> | Property | Value |
> |----------|-------|
> | File | src/main/java/com/tonic/OrderService.java |
> | Line | 45 |
> | Pattern | [JAVA-NC-001](https://confluence.tonic.com/patterns/JAVA-NC-001) |
>
> **Issue:** Method name 'get_order()' violates camelCase naming convention
>
> ```java
> // Current code (line 45):
> public void get_order(String orderId) {
>     // ...
> }
> ```
>
> **✓ Remediation:** Rename method to follow camelCase convention
>
> ```java
> // Suggested fix:
> public void getOrder(String orderId) {
>     // ...
> }
> ```

> ### Finding 2: Exception Handling Violation
>
> | Property | Value |
> |----------|-------|
> | File | src/main/java/com/tonic/OrderService.java |
> | Line | 78 |
> | Pattern | [JAVA-EH-003](https://confluence.tonic.com/patterns/JAVA-EH-003) |
>
> **Issue:** Generic Exception catch block should use specific exception types
>
> ```java
> // Current code (line 78):
> try {
>     processOrder(order);
> } catch (Exception e) {
>     log.error("Error", e);
> }
> ```
>
> **✓ Remediation:** Replace generic Exception with specific exception types (OrderProcessingException, ValidationException)
>
> ```java
> // Suggested fix:
> try {
>     processOrder(order);
> } catch (OrderProcessingException | ValidationException e) {
>     log.error("Order processing failed", e);
>     throw new ServiceException("Failed to process order", e);
> }
> ```

> ---
> ## Action Required
> - Fix all 5 violations in the PR
> - Verify fixes pass automated validation
> - Request re-review after fixes

**Fields**:
- Issue Type: Code Violation
- Priority: Medium
- Assignee: Developer One
- Reporter: SCM Automation Agent
- Labels: ["code-quality", "java", "naming-convention", "exception-handling", "pr-123"]
- Component: order-service
- Custom Fields:
  - PR Number: 123
  - PR URL: https://github.com/tonic-scm/order-service/pull/123
  - Source Agent: Code Best Practises Agent v2.1.0
  - Severity: MEDIUM
  - Workflow Run URL: https://github.com/tonic-scm/order-service/actions/runs/12345

**Remote Link**: [PR #123: Add order validation logic](https://github.com/tonic-scm/order-service/pull/123)

**GitHub PR Comment**:

```markdown
## 📋 Jira Ticket Created

**Ticket**: [SCM-456](https://tonic.atlassian.net/browse/SCM-456) - Code violations in PR #123 (order-service)
**Status**: Open
**Priority**: Medium
**Assignee**: @developer1 (Developer One)

**Assignment Method**: Direct email lookup

This ticket tracks the code violations detected by Code Best Practises Agent v2.1.0 that must be fixed before PR can be merged.

**Findings**: 5 violations detected
- Naming convention violations (2)
- Exception handling violations (1)
- Code style violations (2)

**Next Steps**:
1. Review violations in Jira ticket
2. Apply suggested fixes
3. Push updates to PR
4. Request re-review

---
_Generated by Jira Integration Agent v2.0 | [View Workflow Logs](https://github.com/tonic-scm/order-service/actions/runs/12345)_
```

**CloudWatch Logs**:

```json
{
  "timestamp": "2026-01-28T10:30:15Z",
  "agent": "jira_integration_agent",
  "version": "2.0",
  "action": "CREATE_TICKET",
  "ticket_id": "SCM-456",
  "ticket_url": "https://tonic.atlassian.net/browse/SCM-456",
  "issue_type": "CODE_VIOLATION",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "pr_author_email": "developer1@company.com",
  "assignee_account_id": "5b10ac8d82e05b22cc7d4ef5",
  "assignee_display_name": "Developer One",
  "assignment_method": "email_direct",
  "assignment_lookup_time_ms": 145,
  "cache_hit": false,
  "creation_time_ms": 4200,
  "pr_linked": true,
  "rich_context_included": true,
  "status": "SUCCESS",
  "findings_count": 5
}
```

---

### Example 2: LLD Deviation with Fallback Assignment

**Scenario**: LLD Alignment Review Agent detects architectural deviation. PR author not found in Jira, falls back to component owner.

**Input**:

```json
{
  "issue_type": "LLD_DEVIATION",
  "pr_number": 456,
  "repository": "tonic-scm/payment-service",
  "pr_url": "https://github.com/tonic-scm/payment-service/pull/456",
  "pr_author_email": "external-contributor@gmail.com",
  "pr_author_github_username": "external-dev",
  "severity": "CRITICAL",
  "summary": "LLD deviation in PR #456 (payment-service)",
  "agent_findings": {
    "agent_info": {
      "name": "LLD Alignment Review Agent",
      "version": "1.5.2",
      "detection_time": "2026-01-28T11:00:00Z"
    },
    "findings": [
      {
        "finding_id": "LLD-001",
        "type": "ARCHITECTURAL_DEVIATION",
        "severity": "CRITICAL",
        "lld_section": "Section 5.2 - PaymentProcessor Resilience",
        "lld_document_url": "https://confluence.tonic.com/lld/payment-service#section-5.2",
        "lld_version": "2.3.0",
        "file": "src/main/java/com/tonic/payment/PaymentProcessor.java",
        "line_start": 120,
        "line_end": 145,
        "expected_pattern": "Must use Retry Pattern with max 3 retries and exponential backoff as specified in Resilience Framework",
        "actual_implementation": "Circuit Breaker pattern used instead of Retry Pattern",
        "deviation_reason": "Implementation uses Circuit Breaker which conflicts with centralized resilience service",
        "impact": "Breaks centralized resilience monitoring. Multiple circuit breakers will cause inconsistent failure handling across services.",
        "remediation": {
          "description": "Replace Circuit Breaker with Retry Pattern as specified in LLD Section 5.2",
          "suggested_approach": "Use ResilienceFramework.retryTemplate() with max 3 retries and exponential backoff (1s, 2s, 4s)",
          "effort_estimate": "2-4 hours"
        }
      }
    ]
  }
}
```

**Processing**:

1. **Check for Existing Ticket**: None found

2. **User Lookup Attempts**:
   - **Attempt 1**: Lookup by email `external-contributor@gmail.com`
     - Check Redis cache: Cache miss
     - Call Jira API user search: **Not found** (external contributor)
     - Duration: 180ms
   - **Attempt 2**: Lookup by GitHub username `external-dev`
     - Query DynamoDB github-username-mapping table: **Not found**
     - Duration: 50ms
   - **Attempt 3**: Try domain pattern `external-dev@company.com`
     - Call Jira API user search: **Not found** (external username)
     - Duration: 160ms
   - **Attempt 4**: Component owner fallback
     - Query DynamoDB component-ownership table: `payment-service` / `payment-module`
     - **Found**: Owner email = `team-lead1@company.com`
     - Lookup Account ID from cache: **Cache hit!**
     - Account ID: `5b10ac8d82e05b22cc7d4ef7`
     - Display Name: `Team Lead One`
     - Duration: 12ms
     - **Assignment method**: `fallback_component`

3. **Create Ticket**: Priority = High (CRITICAL severity)

4. **Link PR**: Success

5. **Post PR Comment**: With note about assignment

**Output**:

```json
{
  "status": "PARTIAL_SUCCESS",
  "ticket_id": "SCM-789",
  "ticket_url": "https://tonic.atlassian.net/browse/SCM-789",
  "ticket_key": "SCM-789",
  "assignee_account_id": "5b10ac8d82e05b22cc7d4ef7",
  "assignee_display_name": "Team Lead One",
  "assignment_method": "fallback_component",
  "created_at": "2026-01-28T11:00:45Z",
  "creation_time_ms": 5100,
  "assignment_lookup_time_ms": 402,
  "pr_linked": true,
  "rich_context_included": true,
  "warnings": [
    "PR author not found in Jira. Assigned to component owner instead."
  ],
  "lookup_attempts": [
    {
      "method": "email_direct",
      "input": "external-contributor@gmail.com",
      "result": "NOT_FOUND",
      "duration_ms": 180
    },
    {
      "method": "github_mapped",
      "input": "external-dev",
      "result": "NOT_FOUND",
      "duration_ms": 50
    },
    {
      "method": "domain_pattern",
      "input": "external-dev@company.com",
      "result": "NOT_FOUND",
      "duration_ms": 160
    },
    {
      "method": "fallback_component",
      "input": "payment-service/payment-module",
      "result": "SUCCESS",
      "account_id": "5b10ac8d82e05b22cc7d4ef7",
      "display_name": "Team Lead One",
      "cached": true,
      "duration_ms": 12
    }
  ]
}
```

**Jira Ticket (SCM-789)**:

**Summary**: LLD deviation in PR #456 (payment-service)

**Assignee**: Team Lead One (component owner fallback)

**Comment Added to Ticket**:
```
Auto-assignment to PR author failed (user not found in Jira).
This ticket has been assigned to the component owner: Team Lead One.
PR Author: external-dev (external-contributor@gmail.com)
Please review and reassign if needed.
```

**GitHub PR Comment**:

```markdown
## 📋 Jira Ticket Created

**Ticket**: [SCM-789](https://tonic.atlassian.net/browse/SCM-789) - LLD deviation in PR #456 (payment-service)
**Status**: Open
**Priority**: High (CRITICAL severity)
**Assignee**: @team-lead1 (Team Lead One - component owner)

**Assignment Method**: Fallback to component owner

⚠️ **Note**: PR author not found in Jira. Ticket assigned to component owner.

This ticket tracks an architectural deviation detected by LLD Alignment Review Agent v1.5.2.

**Deviation**: Circuit Breaker pattern used instead of Retry Pattern specified in LLD
**Impact**: Breaks centralized resilience monitoring
**Action Required**: Replace Circuit Breaker with Retry Pattern OR request architectural approval to update LLD

---
_Generated by Jira Integration Agent v2.0_
```

---

### Example 3: Jira Unavailable - Queued for Retry

**Scenario**: Jira API is down when ticket creation is attempted.

**Input**: Same as Example 1 (Code Violation)

**Processing**:

1. **Check for Existing Ticket**:
   - Attempt Jira API call: **Connection timeout** (5 seconds)
   - Retry 1: **Connection refused**
   - Retry 2: **Connection refused**
   - Retry 3: **Connection refused**
   - **Decision**: Jira unavailable, queue for async retry

2. **Queue to SQS**:
   - Queue name: `jira-retry-queue`
   - Message body: Complete ticket payload with all input data
   - Delay: 5 minutes (first retry)
   - Max retries: 288 (24 hours with 5-min intervals)
   - Message attributes:
     - `retry_count`: 0
     - `pr_number`: 123
     - `issue_type`: CODE_VIOLATION
     - `next_retry`: "2026-01-28T10:35:00Z"

3. **Post PR Comment** (immediately, don't wait for Jira):
   - Notify developer that ticket is pending

4. **Create CloudWatch Alarm**:
   - Alarm: "JiraAPIUnavailable"
   - Severity: Warning
   - Message: "Jira API unavailable, tickets queued for retry"

**Output**:

```json
{
  "status": "FAILURE",
  "error": "Jira API unavailable: Connection refused after 3 retries",
  "queued_for_retry": true,
  "retry_queue_url": "https://sqs.us-east-1.amazonaws.com/123456789/jira-retry-queue",
  "next_retry_at": "2026-01-28T10:35:00Z",
  "pr_comment_posted": true
}
```

**GitHub PR Comment** (posted immediately):

```markdown
## 📋 Jira Ticket Pending

⏳ A Jira ticket will be created for this PR once Jira connectivity is restored.

**Issue Type**: Code Violation
**Priority**: Medium
**PR**: #123
**Detected by**: Code Best Practises Agent v2.1.0

**Status**: Queued for creation (Jira temporarily unavailable)

**Findings**: 5 violations detected
- Naming convention violations (2)
- Exception handling violations (1)
- Code style violations (2)

You will be notified once the ticket is created.

---
_Generated by Jira Integration Agent v2.0_
```

**SQS Message Queued**:

```json
{
  "MessageBody": "{...complete ticket payload...}",
  "MessageAttributes": {
    "retry_count": {"DataType": "Number", "StringValue": "0"},
    "pr_number": {"DataType": "Number", "StringValue": "123"},
    "issue_type": {"DataType": "String", "StringValue": "CODE_VIOLATION"},
    "next_retry": {"DataType": "String", "StringValue": "2026-01-28T10:35:00Z"},
    "max_retries": {"DataType": "Number", "StringValue": "288"}
  },
  "DelaySeconds": 300
}
```

**Background Retry (5 minutes later)**:
- Lambda function processes SQS message
- Attempt ticket creation again
- If successful:
  - Create ticket SCM-456
  - Update PR comment with ticket link
  - Delete message from queue
- If still failing:
  - Increment retry_count
  - Re-queue with exponential delay (15 minutes)

---

### Example 4: Partial Success - PR Linking Failed

**Scenario**: Ticket created and assigned successfully, but PR linking fails.

**Input**: Same as Example 1

**Processing**:

1. **Ticket Creation**: ✅ Success (SCM-456 created)
2. **Assignment**: ✅ Success (assigned to Developer One)
3. **PR Linking**: ❌ Failed
   - Attempt to create remote link
   - Error: "GitHub API rate limit exceeded" (429)
   - Decision: Queue link operation for retry, but don't fail entire operation

4. **Queue PR Link for Retry**:
   - Queue to SQS: `jira-link-retry-queue`
   - Payload: `{ticket_key: "SCM-456", pr_url: "...", pr_data: {...}}`
   - Retry schedule: 5 min, 15 min, 1 hour
   - Max retries: 12 (up to 1 hour)

5. **Post PR Comment**: ✅ Success (comment posted with ticket link)

**Output**:

```json
{
  "status": "PARTIAL_SUCCESS",
  "ticket_id": "SCM-456",
  "ticket_url": "https://tonic.atlassian.net/browse/SCM-456",
  "ticket_key": "SCM-456",
  "assignee_account_id": "5b10ac8d82e05b22cc7d4ef5",
  "assignee_display_name": "Developer One",
  "assignment_method": "email_direct",
  "created_at": "2026-01-28T10:30:15Z",
  "creation_time_ms": 4200,
  "pr_linked": false,
  "rich_context_included": true,
  "warnings": [
    "PR remote link creation failed (GitHub rate limit). Link queued for retry."
  ],
  "link_retry_scheduled": true,
  "next_link_retry_at": "2026-01-28T10:35:15Z"
}
```

**GitHub PR Comment** (posted successfully):

```markdown
## 📋 Jira Ticket Created

**Ticket**: [SCM-456](https://tonic.atlassian.net/browse/SCM-456) - Code violations in PR #123 (order-service)
**Status**: Open
**Priority**: Medium
**Assignee**: @developer1 (Developer One)

⚠️ **Note**: Bidirectional link from Jira to GitHub is pending (will be created shortly).

This ticket tracks the code violations detected by Code Best Practises Agent v2.1.0 that must be fixed before PR can be merged.

[Rest of comment same as Example 1...]
```

**Background Retry** (5 minutes later):
- Lambda processes link-retry queue
- Retry PR linking: ✅ Success
- Update Jira ticket with remote link
- CloudWatch log: "PR link retry succeeded for SCM-456"

---

## Configuration

### Environment Variables

```bash
# Jira API Configuration (delegated to Jira Ticket Skill)
JIRA_BASE_URL=https://tonic.atlassian.net
JIRA_EMAIL=automation@company.com
JIRA_API_TOKEN_SECRET_NAME=jira/api-token  # AWS Secrets Manager
JIRA_PROJECT_KEY=SCM

# Assignment Configuration
JIRA_DEFAULT_ASSIGNEE_ACCOUNT_ID=5b10ac8d82e05b22cc7d4ef6
ORGANIZATION_EMAIL_DOMAIN=company.com

# Cache Configuration (used by Jira Ticket Skill)
REDIS_HOST=jira-cache.abc123.0001.use1.cache.amazonaws.com
REDIS_PORT=6379
REDIS_DB=0
USER_CACHE_TTL_HOURS=24

# Rate Limiting (handled by Jira Ticket Skill)
JIRA_RATE_LIMIT_PER_MINUTE=100

# Retry Configuration
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY_SECONDS=5
RETRY_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/jira-retry-queue
LINK_RETRY_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/jira-link-retry-queue

# DynamoDB Tables
COMPONENT_OWNERSHIP_TABLE=component-ownership
USERNAME_MAPPING_TABLE=github-username-mapping

# Performance
JIRA_API_TIMEOUT_SECONDS=10
TICKET_CREATION_TARGET_MS=10000  # 10 seconds P95
USER_LOOKUP_TARGET_MS=200  # 200ms P95

# Custom Field IDs (Jira project configuration)
JIRA_CUSTOM_FIELD_PR_NUMBER=customfield_10001
JIRA_CUSTOM_FIELD_PR_URL=customfield_10002
JIRA_CUSTOM_FIELD_SOURCE_AGENT=customfield_10003
JIRA_CUSTOM_FIELD_SEVERITY=customfield_10004
JIRA_CUSTOM_FIELD_PATTERN_ID=customfield_10005
JIRA_CUSTOM_FIELD_WORKFLOW_RUN_URL=customfield_10006
```

### Jira Project Configuration Requirements

**Required Issue Types**:
- Code Violation
- LLD Deviation
- Pattern Rejection

**Required Custom Fields**:
- PR Number (Number field)
- PR URL (URL field)
- Source Agent (Text field)
- Severity (Select field: CRITICAL, HIGH, MEDIUM, LOW)
- Pattern ID (Text field, optional)
- Workflow Run URL (URL field)

**Required Labels** (auto-created):
- code-quality
- lld-deviation
- pattern-rejection
- architectural
- auto-assignment-failed
- pr-{number}

---

## Implementation Notes

### Technology Stack

- **Language**: Python 3.11+
- **Jira API**: Atlassian REST API v3 (via Jira Ticket Skill)
- **GitHub API**: PyGithub library
- **Queue**: AWS SQS for retry queue
- **Cache**: Redis (AWS ElastiCache)
- **Database**: DynamoDB (component ownership, username mapping)
- **Cloud**: AWS Lambda or ECS Fargate
- **Monitoring**: AWS CloudWatch (metrics, logs, alarms)
- **Secrets**: AWS Secrets Manager

### Dependencies

**Required Skills**:
- Jira Ticket Skill v1.0+ (for all Jira operations)

**Python Packages**:
```
# requirements.txt
jira==3.5.0  # (indirectly via Jira Ticket Skill)
PyGithub==2.1.1
boto3==1.28.0  # AWS SDK
redis==5.0.0
structlog==23.1.0
tenacity==8.2.3  # Retry logic
```

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│               Jira Integration Agent v2.0                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Agent Request Handler                         │ │
│  │  (receives input from calling agent)                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Ticket Creation Orchestrator                    │ │
│  │  - Deduplication check                                 │ │
│  │  - ADF description generation                          │ │
│  │  - Delegate to Jira Ticket Skill                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Jira Ticket Skill Integration                 │ │
│  │  (all Jira operations delegated here)                  │ │
│  │  - create_ticket()                                     │ │
│  │  - assign_ticket()                                     │ │
│  │  - link_pr()                                           │ │
│  │  - lookup_user()                                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         PR Comment Handler                              │ │
│  │  (posts comment on GitHub PR with ticket link)         │ │
│  └────────────────────────────────────────────────────────┘ │
│                          │                                   │
│                          ▼                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Error Handler & Retry Queue                     │ │
│  │  - Graceful degradation                                │ │
│  │  - SQS queue for failed operations                     │ │
│  │  - CloudWatch alarms                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘

External Dependencies:
├─ Jira Ticket Skill (handles all Jira API calls)
│  ├─ User lookup with caching
│  ├─ Rate limiting
│  └─ Error handling
├─ GitHub API (PR comments)
├─ Redis (user cache, used by skill)
├─ DynamoDB (component ownership, username mapping, used by skill)
└─ SQS (retry queues)
```

---

## Operational Protocol

### TBT (Test-Before-Task) Workflow Compliance

**For every ticket creation operation**:

1. **Command Logging** (Phase 1: Planning):
   - Log ticket creation request to `.claude/logs/history.log`
   - Track: timestamp, PR number, issue type, source agent

2. **Ticket Creation** (Phase 2: Execution):
   - Check for duplicates
   - Generate ADF description
   - Delegate to Jira Ticket Skill
   - Handle errors gracefully

3. **Verification** (Phase 3: Verification):
   - Verify ticket was created (check ticket URL)
   - Confirm assignment (check assignee Account ID)
   - Verify PR linking (check remote link exists)
   - Log completion to CloudWatch

**State Tracking**:
- All agent state tracked in `.claude/state/state.md`
- Results documented with full audit trail
- CloudWatch metrics for observability

---

## Questions and TBCs

| ID | Question/TBC | Priority | Owner | Status |
|----|--------------|----------|-------|--------|
| TBC-JIA-001 | Jira project custom fields configuration (IDs for all 6 custom fields) | HIGH | DevOps Team | TBC |
| TBC-JIA-002 | Ticket workflow automation rules (auto-transition based on PR status) | HIGH | Product Owner | TBC |
| TBC-JIA-003 | Architect watcher list for LLD deviation tickets | MEDIUM | Architecture Team | TBC |
| TBC-JIA-004 | Component ownership table population strategy | HIGH | Platform Team | TBC |
| TBC-JIA-005 | GitHub username mapping table initial population | HIGH | DevOps Team | TBC |
| TBC-JIA-006 | Default assignee Account ID for fallback | HIGH | Product Owner | TBC |
| TBC-JIA-007 | CloudWatch alarm SNS topic for notifications | HIGH | DevOps Team | TBC |
| TBC-JIA-008 | SLA tracking integration with Jira | MEDIUM | Architecture Team | TBC |
| TBC-JIA-009 | Bulk ticket creation optimization for multiple findings | LOW | Development Team | TBC |
| TBC-JIA-010 | Webhook integration for bidirectional sync (Jira → GitHub status updates) | MEDIUM | Architecture Team | Future Enhancement |

---

## Version History

- **v2.0** (2026-01-28): Enhanced version with:
  - Intelligent auto-assignment with multi-tier fallback
  - Rich context from agent findings (ADF formatting)
  - Bidirectional PR linking (Jira ↔ GitHub)
  - Enhanced error handling with partial success tracking
  - Integration with Jira Ticket Skill
  - Comprehensive configuration support
  - Detailed observability and metrics

- **v1.0** (2026-01-28): Initial agent definition from specification
  - Basic ticket creation
  - Simple assignment
  - Basic PR linking
  - Error handling

---

**End of Enhanced Agent Specification**
