# PR Peer Review Orchestration System - System Documentation

**Version**: 1.0
**Created**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**System**: PR Peer Review Orchestration

---

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Components](#components)
4. [Workflow](#workflow)
5. [Integration Points](#integration-points)
6. [Data Schemas](#data-schemas)
7. [Configuration Reference](#configuration-reference)
8. [Monitoring and Observability](#monitoring-and-observability)
9. [Troubleshooting Guide](#troubleshooting-guide)

---

## 1. System Overview

### 1.1 Purpose and Goals

The PR Peer Review Orchestration System automates and manages the complete peer review lifecycle for GitHub Pull Requests in the Tonic Configuration Management Platform. It provides intelligent validation, pattern detection, and human review coordination to ensure code quality, architectural compliance, and knowledge capture.

**Primary Goals**:
- Automate code quality validation with 30-second SLA
- Detect and catalog new architectural patterns (10-second detection SLA)
- Ensure LLD compliance for new patterns (20-second validation SLA)
- Orchestrate human architectural review (4-hour SLA)
- Prevent non-compliant code from merging to protected branches
- Build a searchable pattern library in Confluence
- Provide complete audit trail for compliance

**Key Metrics**:
- End-to-end workflow time: <1 minute for standard PRs (no new patterns)
- End-to-end workflow time: ~4.5 hours for PRs with new patterns (including human review)
- Code quality validation: 30-second SLA
- Pattern detection: 10-second SLA
- LLD alignment validation: 20-second SLA
- Peer review: 4-hour SLA
- System availability: 99.9% uptime target

### 1.2 System Boundaries

**In Scope**:
- Pull request validation and approval workflow
- Multi-agent coordination and orchestration
- Code quality and pattern detection
- LLD compliance validation
- Human peer review coordination
- Jira ticket creation for issues
- Pattern library storage in Confluence
- GitHub status checks and branch protection integration

**Out of Scope**:
- Application deployment (handled by separate deployment pipeline)
- Code compilation and build (handled by CI/CD pipeline)
- Security vulnerability scanning (handled by security tools)
- Infrastructure provisioning (handled by Terraform/IaC)

### 1.3 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PR PEER REVIEW ORCHESTRATION SYSTEM                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌────────────┐                                                            │
│   │   GitHub   │──PR Event───┐                                              │
│   │  (PR)      │             │                                              │
│   └────────────┘             ▼                                              │
│                     ┌─────────────────┐                                     │
│                     │  GitHub Actions │                                     │
│                     │   Workflow      │                                     │
│                     │  (Orchestrator) │                                     │
│                     └────────┬────────┘                                     │
│                              │                                              │
│              ┌───────────────┼───────────────┬──────────────────┐          │
│              ▼               ▼               ▼                  ▼          │
│   ┌──────────────┐  ┌────────────────┐  ┌────────────┐  ┌──────────────┐ │
│   │     Code     │  │   Architect    │  │    LLD     │  │ Peer Review  │ │
│   │  Best Prac   │  │  Best Prac     │  │ Alignment  │  │     Agent    │ │
│   │    Agent     │  │     Agent      │  │   Agent    │  │              │ │
│   │              │  │                │  │            │  │              │ │
│   │  (30s SLA)   │  │   (10s SLA)    │  │  (20s SLA) │  │  (4hr SLA)   │ │
│   └──────┬───────┘  └───────┬────────┘  └─────┬──────┘  └──────┬───────┘ │
│          │                  │                  │                 │          │
│          │                  │                  │                 │          │
│          └──────────────────┼──────────────────┴─────────────────┘          │
│                             ▼                                               │
│                  ┌──────────────────────┐                                   │
│                  │  PR Orchestrator     │                                   │
│                  │  Agent (Coordinator) │                                   │
│                  └──────────┬───────────┘                                   │
│                             │                                               │
│                ┌────────────┼────────────┬──────────────────┐              │
│                ▼            ▼            ▼                  ▼              │
│        ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌──────────────┐      │
│        │  Jira    │  │  Pattern   │  │ GitHub   │  │  CloudWatch  │      │
│        │  Agent   │  │  Storage   │  │ Actions  │  │   Metrics    │      │
│        │          │  │  Agent     │  │  Hooks   │  │              │      │
│        └────┬─────┘  └──────┬─────┘  └────┬─────┘  └──────────────┘      │
│             │               │              │                               │
│             ▼               ▼              ▼                               │
│   ┌──────────────┐  ┌────────────┐  ┌─────────────┐                      │
│   │     Jira     │  │ Confluence │  │   GitHub    │                      │
│   │   (Tickets)  │  │ (Patterns) │  │ (Merge/PR)  │                      │
│   └──────────────┘  └────────────┘  └─────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

External Dependencies:
├── Confluence (Pattern Library, LLD Documents)
├── Jira (Issue Tracking)
├── GitHub (PR Management, Branch Protection)
├── AWS DynamoDB (Agent State, Cache)
├── AWS SQS (Retry Queue)
├── AWS CloudWatch (Metrics, Logs, Alarms)
└── Redis (Pattern Cache, Rate Limiting)
```

---

## 2. Components

### 2.1 PR Orchestrator Agent

**Purpose**: Centralized workflow coordination and decision-making for all peer review agents.

**Key Responsibilities**:
- Execute agents in correct sequential order
- Make intelligent routing decisions based on agent outputs
- Maintain complete workflow state
- Make final merge decision
- Aggregate errors from all agents
- Monitor SLA compliance across workflow
- Handle transient failures with retry logic
- Send notifications at key workflow points

**Capabilities**:
- Workflow orchestration (6-step pipeline)
- Intelligent routing (conditional execution)
- State management (DynamoDB/Redis)
- Merge decision logic
- Error aggregation
- SLA monitoring
- Retry logic (exponential backoff, circuit breaker)
- Notification management

**SLA**: ~4.5 hours end-to-end (including human review)

**Technology Stack**:
- Deployment: GitHub Actions Workflow
- State Store: DynamoDB or Redis
- Metrics: CloudWatch

**Input**: GitHub PR webhook event (JSON)

**Output**:
- Merge decision (APPROVE_MERGE / BLOCK_MERGE / PENDING_REVIEW)
- Aggregated validation report (JSON)
- GitHub PR comment (Markdown)
- GitHub status check

### 2.2 Orchestrator Skill

**Purpose**: Reusable pipeline orchestration skill for agent coordination.

**Key Operations**:
- `execute_pipeline`: Execute multi-agent pipelines with parallel/sequential execution
- `execute_agent`: Invoke individual agents with timeout management
- `aggregate_results`: Collect and aggregate agent results
- `make_decision`: Make merge/block decisions based on aggregated results
- `get_pipeline_status`: Query current pipeline state
- `cancel_pipeline`: Cancel running pipeline

**Key Features**:
- Conditional branching engine
- Parallel and sequential agent execution
- State management (persistent across runs)
- Error handling and recovery
- Comprehensive observability

**Used By**: PR Orchestrator Agent, custom workflow orchestrators

### 2.3 Code Best Practises Agent

**Purpose**: Enforce coding standards and best practices.

**Key Responsibilities**:
- Retrieve approved patterns from Confluence
- Analyze all modified code files
- Detect violations (naming, documentation, pattern compliance)
- Post detailed violation report to PR
- Block PR merge if violations found

**SLA**: 30 seconds

**Outputs**:
- Status: PASSED / FAILED
- Violations count
- Violations report (file, line, type, description)

**Integration Points**:
- Confluence API (retrieve patterns)
- GitHub API (post PR comments)

### 2.4 Architect Best Practises Agent

**Purpose**: Detect new coding patterns not in approved pattern library.

**Key Responsibilities**:
- Query Confluence for existing patterns
- Extract structural patterns from PR code
- Calculate similarity to existing patterns (85% threshold)
- Determine if new pattern exists
- Add "new-pattern-detected" label to PR if applicable

**SLA**: 10 seconds

**Outputs**:
- Status: NO_NEW_PATTERN / NEW_PATTERN_FOUND
- New pattern detected: true/false
- Pattern data (JSON with pattern details)

**Decision Logic**:
- Similarity > 85%: NO_NEW_PATTERN (skip to deployment)
- Similarity <= 85%: NEW_PATTERN_FOUND (proceed to LLD alignment)

**Integration Points**:
- Confluence API (query patterns)
- GitHub API (add PR labels)

### 2.5 LLD Alignment Review Agent

**Purpose**: Validate new patterns comply with LLD specifications.

**Key Responsibilities**:
- Retrieve component LLD from Confluence
- Parse LLD for design constraints, interfaces, contracts
- Map new pattern to LLD specifications
- Detect deviations from LLD
- Generate detailed deviation report with fix guidance

**SLA**: 20 seconds

**Outputs**:
- Status: LLD_COMPLIANT / LLD_DEVIATION_FOUND
- LLD compliant: true/false
- Deviations count
- Deviations report (severity, location, guidance)

**Deviation Severity**:
- CRITICAL: Interface contract violation, component boundary breach, security violation
- MAJOR: Performance requirement violation, data model inconsistency, disallowed dependency
- MINOR: Naming convention deviation, documentation inconsistency

**Integration Points**:
- Confluence API (retrieve LLD documents)
- GitHub API (post PR comments)

### 2.6 Pattern Matching Agent

**Purpose**: Store approved patterns in Confluence pattern library.

**Key Responsibilities**:
- Generate unique pattern ID (e.g., PTN-JAVA-042)
- Create Confluence page in SCM-PATTERNS space
- Store pattern metadata in page properties
- Add pattern to searchable index
- Link pattern to LLD and source PR

**SLA**: 5 seconds

**Outputs**:
- Pattern ID
- Confluence URL
- Pattern version

**Pattern Metadata**:
- Pattern ID, Status (APPROVED), Version
- Category (design pattern / architectural / idiom)
- Language/framework
- Approvers (architects who approved)
- Approval date
- Source PR number and repository
- LLD reference

**Integration Points**:
- Confluence API (create pages)
- Redis (pattern index cache)
- GitHub API (link to source PR)

**Note**: Disabled in main PR workflow - runs in separate post-merge workflow

### 2.7 Peer Review Documentation Agent

**Purpose**: Orchestrate human architectural review for new patterns.

**Key Responsibilities**:
- Query team configuration for eligible reviewers
- Assign 2-3 reviewers (minimum 1 architect)
- Post review request comment to PR with pattern context
- Send notifications to assigned reviewers
- Start SLA monitoring (4-hour countdown)

**SLA**: 4 hours (for human review completion)

**Reviewer Assignment Algorithm**:
1. Priority 1: Component owner + architect with category expertise
2. Priority 2: Architect with language expertise + senior engineer
3. Priority 3: Any available architect + 1 senior engineer
4. Fallback: Escalate to architecture team lead

**Outputs**:
- Status: REVIEWERS_ASSIGNED
- Reviewers assigned (comma-separated list)

**SLA Monitoring** (Future):
- 2 hours (50% SLA): Send reminder to reviewers
- 3.5 hours (87.5% SLA): Escalate to architecture team lead
- 4 hours (100% SLA breach): Create CloudWatch alarm

**Integration Points**:
- GitHub API (assign reviewers, post PR comments)
- Team Configuration (query reviewer roster)
- Notification Systems (email, Slack)

### 2.8 Enhanced Jira Integration Agent

**Purpose**: Create Jira tickets for code violations, LLD deviations, and pattern rejections with rich context and auto-assignment.

**Key Responsibilities**:
- Determine issue type (CODE_VIOLATION / LLD_DEVIATION / PATTERN_REJECTION)
- Map severity to Jira priority (CRITICAL -> High, MAJOR -> Medium, MINOR -> Low)
- Lookup Jira Account ID from PR author email/username
- Create Jira ticket with complete context
- Auto-assign ticket to PR author
- Link ticket to GitHub PR (bidirectional)
- Post ticket link to PR comment

**SLA**: 10 seconds

**Outputs**:
- Jira ticket ID (e.g., SCM-456)

**Jira Ticket Fields**:
- Summary: Auto-generated from issue details
- Issue Type: Code Violation / LLD Deviation / Pattern Rejection
- Priority: Based on severity mapping
- Assignee: PR author (or fallback to component owner)
- Reporter: "SCM Automation Agent"
- Labels: Auto-tagged (e.g., code-quality, lld-deviation, java)
- Components: Repository name
- Custom Fields: PR Number, PR URL, Source Agent, Severity

**Integration Points**:
- Jira REST API v3 (create issues, assign users, link PRs)
- GitHub API (post PR comments)
- AWS SQS (retry queue)
- Redis/DynamoDB (user lookup cache)

### 2.9 Jira Ticket Skill

**Purpose**: Reusable skill for Jira ticket operations across all agents.

**Key Operations**:
- `create_ticket`: Create Jira ticket with rich context
- `assign_ticket`: Assign ticket to user by email/username/Account ID
- `link_pr`: Link GitHub PR to Jira ticket (bidirectional)
- `add_comment`: Add comment to existing ticket
- `lookup_user`: Lookup Jira Account ID from email/username

**Key Features**:
- User lookup with 24-hour caching (90%+ cache hit rate)
- Rate limiting (token bucket, 100 req/min)
- GDPR-compliant user assignment (Account ID based)
- Multi-tier fallback strategy
- Comprehensive error handling and retry logic

**Used By**: All agents that need Jira integration

### 2.10 GitHub Actions Workflow

**Purpose**: Trigger and execute PR peer review orchestration workflow.

**Jobs**:
1. **Pre-Flight Validation**: Validate PR and detect code changes (5 min timeout)
2. **Code Quality Agent**: Run code best practices validation (2 min timeout)
3. **Architect Agent**: Detect new patterns (1 min timeout)
4. **LLD Alignment Agent**: Validate LLD compliance (1 min timeout)
5. **Peer Review Agent**: Manage human review (5 min timeout)
6. **Pattern Matching Agent**: Store approved patterns (1 min timeout, disabled)
7. **Jira Integration**: Create tickets for failures (2 min timeout)
8. **Final Report**: Aggregate results and post summary (5 min timeout)

**Triggers**:
- PR events: opened, synchronize, reopened
- Merge group events: checks_requested
- Manual dispatch: workflow_dispatch with pr_number input

**Concurrency Control**:
- Group: pr-review-{pr_number}
- Cancel in-progress: true

**Permissions**:
- contents: read
- pull-requests: write
- issues: write
- statuses: write
- checks: write

---

## 3. Workflow

### 3.1 PR Trigger Flow

```
┌─────────────────┐
│  PR Created or  │
│  Updated (Push) │
└────────┬────────┘
         │
         ▼
┌──────────────────────────────┐
│  GitHub Actions Workflow     │
│  Triggered                   │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Pre-Flight Validation       │
│  - Validate PR is open       │
│  - Detect code changes       │
└────────┬─────────────────────┘
         │
         ├──[No Code Changes]──> Skip to End
         │
         ▼
┌──────────────────────────────┐
│  Code Best Practises Agent   │
│  - Retrieve patterns         │
│  - Analyze code              │
│  - Report violations         │
└────────┬─────────────────────┘
         │
         ├──[FAILED]──────────────┐
         │                        │
         ▼ [PASSED]               │
┌──────────────────────────────┐ │
│  Architect Best Practises    │ │
│  Agent                       │ │
│  - Extract patterns          │ │
│  - Calculate similarity      │ │
│  - Detect new patterns       │ │
└────────┬─────────────────────┘ │
         │                        │
         ├──[No New Pattern]──┐  │
         │                    │  │
         ▼ [New Pattern]      │  │
┌──────────────────────────┐  │  │
│  LLD Alignment Agent     │  │  │
│  - Retrieve LLD          │  │  │
│  - Map pattern to LLD    │  │  │
│  - Detect deviations     │  │  │
└────────┬─────────────────┘  │  │
         │                    │  │
         ├──[FAILED]──────────┼──┤
         │                    │  │
         ▼ [PASSED]           │  │
┌──────────────────────────┐  │  │
│  Peer Review Agent       │  │  │
│  - Assign reviewers      │  │  │
│  - Post review request   │  │  │
│  - Start SLA monitoring  │  │  │
└────────┬─────────────────┘  │  │
         │                    │  │
         ▼ [Approved]         │  │
┌──────────────────────────┐  │  │
│  Pattern Storage Agent   │  │  │
│  - Store pattern         │  │  │
│  - Create Confluence page│  │  │
│  (Post-merge workflow)   │  │  │
└──────────────────────────┘  │  │
                              │  │
         ┌────────────────────┘  │
         │                       │
         ▼                       ▼
┌──────────────────────────────────┐
│  Jira Integration Agent          │
│  - Determine issue type          │
│  - Create Jira ticket            │
│  - Auto-assign to PR author      │
│  - Link ticket to PR             │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Final Report                    │
│  - Aggregate all results         │
│  - Determine overall status      │
│  - Post PR comment summary       │
│  - Set GitHub status check       │
└──────────────────────────────────┘
```

### 3.2 Agent Execution Sequence

**Standard PR (No New Patterns)**:
```
Pre-Flight → Code Quality → Architect → Final Report
Estimated Time: <1 minute
```

**PR with New Pattern (LLD Compliant)**:
```
Pre-Flight → Code Quality → Architect → LLD Alignment → Peer Review → Final Report
Estimated Time: ~4.5 hours (waiting for human review)
```

**PR with Code Violations**:
```
Pre-Flight → Code Quality → Jira Integration → Final Report
Estimated Time: ~1 minute
```

**PR with LLD Deviation**:
```
Pre-Flight → Code Quality → Architect → LLD Alignment → Jira Integration → Final Report
Estimated Time: ~1 minute
```

### 3.3 Merge Decision Logic

The PR Orchestrator Agent makes the final merge decision based on these criteria:

**APPROVE_MERGE** (Green):
- Code Quality Agent: PASSED
- Architect Agent: NO_NEW_PATTERN (existing pattern used)
- All CI/CD checks: PASSED
- Branch protection rules: SATISFIED

**BLOCK_MERGE** (Red):
- Code Quality Agent: FAILED (violations detected)
- LLD Alignment Agent: LLD_DEVIATION_FOUND
- Any agent: TIMEOUT or ERROR
- Branch protection rules: NOT SATISFIED

**PENDING_REVIEW** (Yellow):
- Architect Agent: NEW_PATTERN_FOUND
- LLD Alignment Agent: LLD_COMPLIANT
- Peer Review Agent: REVIEWERS_ASSIGNED
- Awaiting human approval

### 3.4 Failure Handling Flow

When any validation agent fails:

```
Agent Failure Detected
         │
         ▼
┌──────────────────────────────┐
│  PR Orchestrator Agent       │
│  - Capture failure details   │
│  - Classify failure type     │
│  - Route to Jira Integration │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Jira Integration Agent      │
│  - Create Jira ticket        │
│  - Auto-assign to PR author  │
│  - Link ticket to PR         │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Final Report                │
│  - Post failure summary      │
│  - Set status check: FAILED  │
│  - Block PR merge            │
└──────────────────────────────┘
```

**Retry Strategy**:
- Transient failures (API timeouts): Exponential backoff with jitter (3 retries max)
- Rate limiting (429): Respect Retry-After header
- Cascading failures: Circuit breaker (5 failures threshold, 60s timeout)
- Jira unavailable: Queue ticket creation in SQS for async retry

---

## 4. Integration Points

### 4.1 GitHub Integration

**Components Used**:
- GitHub API (REST API v3)
- GitHub Webhooks (PR events)
- GitHub Actions (workflow execution)
- GitHub Status Checks (branch protection)

**Operations**:

**PR Webhooks**:
- Events: pull_request.opened, pull_request.synchronize, pull_request.reopened
- Payload: PR metadata (number, title, description, author, commits, files)

**PR Comments** (via GitHub API):
- POST /repos/{owner}/{repo}/issues/{pr_number}/comments
- Used by: All agents to post validation results

**PR Labels** (via GitHub API):
- POST /repos/{owner}/{repo}/issues/{pr_number}/labels
- Used by: Architect Agent to add "new-pattern-detected" label

**Reviewer Assignment** (via GitHub API):
- POST /repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers
- Used by: Peer Review Agent to assign human reviewers

**Status Checks** (via GitHub API):
- POST /repos/{owner}/{repo}/statuses/{sha}
- Used by: Final Report job to set merge status

**Branch Protection**:
- Required status checks: 5 blocking checks
  - pr-orchestrator / workflow-validation
  - code-quality / code-best-practises
  - architecture / architect-best-practises
  - ci-build / build-and-test
  - ci-security / security-scan
- Enforce admins: true (no bypasses)
- Require branches up to date: true
- Require conversation resolution: true

**Authentication**:
- GitHub Actions: GITHUB_TOKEN (automatic)
- External agents: GitHub Personal Access Token (PAT) or GitHub App

### 4.2 Jira Integration

**Components Used**:
- Jira REST API v3
- Jira Webhooks (optional, for bidirectional sync)

**Operations**:

**Create Issue**:
- POST /rest/api/3/issue
- Payload: fields (project, issuetype, summary, description, assignee, labels)

**Assign Issue**:
- PUT /rest/api/3/issue/{issueKey}/assignee
- Payload: accountId (GDPR-compliant)

**User Lookup** (Account ID from email):
- GET /rest/api/3/user/search?query={email}
- Cached for 24 hours

**Remote Link** (GitHub PR to Jira):
- POST /rest/api/3/issue/{issueKey}/remotelink
- Payload: globalId, url, title, icon, status

**Authentication**:
- API Token Authentication (Basic Auth: email + API token)
- Stored in: GitHub Secrets (JIRA_API_TOKEN, JIRA_USER_EMAIL)

**Configuration**:
- JIRA_BASE_URL: https://tonic.atlassian.net
- JIRA_PROJECT: SCM
- JIRA_DEFAULT_ASSIGNEE: architecture-team-lead@tonic.com

**Rate Limiting**:
- Token bucket (100 requests/minute)
- Automatic queuing of excess requests
- Exponential backoff on 429 responses

### 4.3 Confluence Integration

**Components Used**:
- Confluence REST API v2
- Confluence CQL (query language)

**Spaces**:
- SCM-PATTERNS: Pattern library storage
- SCM-LLD: Low-Level Design documents

**Operations**:

**Query Patterns**:
- GET /wiki/rest/api/content?spaceKey=SCM-PATTERNS&type=page
- Cached for 30 minutes

**Query LLD Documents**:
- GET /wiki/rest/api/content?spaceKey=SCM-LLD&title={component}
- Cached for 60 minutes

**Create Pattern Page**:
- POST /wiki/rest/api/content
- Payload: space, title, body (storage format)

**Authentication**:
- API Token Authentication
- Stored in: GitHub Secrets (CONFLUENCE_API_TOKEN)

**Configuration**:
- CONFLUENCE_BASE_URL: https://confluence.tonic.com
- CONFLUENCE_SPACE_PATTERNS: SCM-PATTERNS
- CONFLUENCE_SPACE_LLD: SCM-LLD

**Caching Strategy**:
- Pattern library: 30-minute TTL (patterns change infrequently)
- LLD documents: 60-minute TTL (LLDs change even less frequently)
- Cache invalidation: Manual via API or scheduled refresh

### 4.4 AWS Services Integration

**DynamoDB** (State Storage):
- Table: pr-orchestrator-state
- Purpose: Store workflow state, agent results, retry attempts
- TTL: 30 days (automatic cleanup)

**SQS** (Retry Queue):
- Queue: jira-ticket-retry-queue
- Purpose: Queue failed Jira ticket creation for async retry
- Retention: 14 days
- Visibility timeout: 300 seconds

**CloudWatch** (Metrics and Logs):
- Metrics:
  - Agent execution time (P50, P95, P99)
  - Agent success rate
  - Agent SLA compliance rate
  - Workflow end-to-end time
  - Jira ticket creation success rate
- Logs:
  - Agent execution logs (30-day retention)
  - Workflow orchestration logs (90-day retention)
- Alarms:
  - Agent timeout (execution time > SLA)
  - High error rate (>5% failures)
  - Confluence/Jira unavailable
  - SLA breach (>10% of executions exceed SLA)

**Redis** (Caching and Rate Limiting):
- Purpose: Cache pattern library, user lookups, rate limiting state
- TTL: Varies by cache type (30min for patterns, 24h for users)
- Eviction policy: LRU (Least Recently Used)

**Authentication**:
- AWS Access Keys (IAM user or role)
- Stored in: GitHub Secrets (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

---

## 5. Data Schemas

### 5.1 PR Input Data

**GitHub PR Webhook Event** (JSON):

```json
{
  "action": "opened",
  "number": 123,
  "pull_request": {
    "id": 1234567,
    "number": 123,
    "state": "open",
    "title": "Add repository pattern with caching",
    "body": "Implements repository pattern for order data access with Spring Cache",
    "created_at": "2026-01-28T10:00:00Z",
    "updated_at": "2026-01-28T10:00:00Z",
    "head": {
      "ref": "feature/repository-pattern",
      "sha": "abc123def456"
    },
    "base": {
      "ref": "main",
      "sha": "def456abc789"
    },
    "user": {
      "login": "developer1",
      "id": 12345,
      "email": "developer1@tonic.com"
    },
    "html_url": "https://github.com/tonic-scm/order-service/pull/123",
    "changed_files": 5,
    "additions": 234,
    "deletions": 12
  },
  "repository": {
    "name": "order-service",
    "full_name": "tonic-scm/order-service",
    "owner": {
      "login": "tonic-scm"
    }
  }
}
```

### 5.2 Agent Result Schemas

**Code Best Practises Agent Output**:

```json
{
  "agent": "code_best_practises_agent",
  "version": "1.0",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "status": "PASSED",
  "execution_time_ms": 12000,
  "violations": [],
  "violations_count": 0,
  "patterns_checked": [
    "Naming Conventions",
    "Documentation Standards",
    "Repository Pattern"
  ],
  "timestamp": "2026-01-28T10:00:12Z"
}
```

**Architect Best Practises Agent Output**:

```json
{
  "agent": "architect_best_practises_agent",
  "version": "1.0",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "status": "NEW_PATTERN_FOUND",
  "execution_time_ms": 5200,
  "new_pattern_detected": true,
  "pattern_data": {
    "pattern_name": "Repository Pattern with Caching",
    "pattern_category": "Architectural",
    "language": "Java",
    "framework": "Spring",
    "similarity_score": 0.73,
    "matched_pattern": "Repository Pattern",
    "differences": [
      "Adds caching layer using Spring Cache",
      "Implements cache eviction strategy"
    ],
    "code_snippet": "public class OrderRepository implements CrudRepository<Order, Long> { ... }"
  },
  "timestamp": "2026-01-28T10:00:17Z"
}
```

**LLD Alignment Review Agent Output**:

```json
{
  "agent": "lld_alignment_review_agent",
  "version": "1.0",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "status": "LLD_COMPLIANT",
  "execution_time_ms": 8500,
  "lld_compliant": true,
  "lld_document": "Order Service LLD v2.3",
  "lld_confluence_url": "https://confluence.tonic.com/display/SCM-LLD/Order+Service",
  "deviations": [],
  "deviations_count": 0,
  "constraints_validated": [
    "Repository interface contract",
    "Transaction management",
    "Cache configuration"
  ],
  "timestamp": "2026-01-28T10:00:26Z"
}
```

**Peer Review Agent Output**:

```json
{
  "agent": "peer_review_documentation_agent",
  "version": "1.0",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "status": "REVIEWERS_ASSIGNED",
  "execution_time_ms": 1200,
  "reviewers_assigned": [
    "architect1",
    "senior-eng1"
  ],
  "reviewer_count": 2,
  "review_sla_hours": 4,
  "review_due_at": "2026-01-28T14:00:00Z",
  "timestamp": "2026-01-28T10:00:27Z"
}
```

### 5.3 Jira Ticket Schemas

**Jira Ticket Creation Request**:

```json
{
  "fields": {
    "project": {
      "key": "SCM"
    },
    "issuetype": {
      "name": "Code Violation"
    },
    "summary": "Code violations in PR #123 (order-service)",
    "description": {
      "type": "doc",
      "version": 1,
      "content": [
        {
          "type": "heading",
          "attrs": { "level": 2 },
          "content": [{ "type": "text", "text": "Code Violations Detected" }]
        },
        {
          "type": "paragraph",
          "content": [
            { "type": "text", "text": "Automated code analysis detected " },
            { "type": "text", "text": "3", "marks": [{"type": "strong"}] },
            { "type": "text", "text": " violations in pull request " },
            { "type": "text", "text": "#123", "marks": [{"type": "strong"}] },
            { "type": "text", "text": "." }
          ]
        },
        {
          "type": "heading",
          "attrs": { "level": 3 },
          "content": [{ "type": "text", "text": "Violation Details" }]
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
                    { "type": "text", "text": "File: " },
                    { "type": "text", "text": "OrderRepository.java:45", "marks": [{"type": "code"}] },
                    { "type": "text", "text": " - Missing Javadoc for public method" }
                  ]
                }
              ]
            }
          ]
        },
        {
          "type": "paragraph",
          "content": [
            { "type": "text", "text": "View PR: " },
            {
              "type": "text",
              "text": "https://github.com/tonic-scm/order-service/pull/123",
              "marks": [{"type": "link", "attrs": {"href": "https://github.com/tonic-scm/order-service/pull/123"}}]
            }
          ]
        }
      ]
    },
    "priority": {
      "name": "Medium"
    },
    "labels": ["code-quality", "pr-123", "automated"],
    "assignee": {
      "accountId": "5b10ac8d82e05b22cc7d4ef5"
    },
    "components": [
      { "name": "order-service" }
    ],
    "customfield_10001": "https://github.com/tonic-scm/order-service/pull/123",
    "customfield_10002": "developer1",
    "customfield_10003": { "value": "main" }
  }
}
```

**Jira Ticket Response**:

```json
{
  "id": "10000",
  "key": "SCM-456",
  "self": "https://tonic.atlassian.net/rest/api/3/issue/10000"
}
```

### 5.4 PR Orchestrator Aggregated Report

```json
{
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "workflow_id": "1234567890",
  "workflow_run_number": 42,
  "workflow_status": "PENDING_REVIEW",
  "merge_decision": "PENDING_REVIEW",
  "execution_summary": {
    "total_time_seconds": 27,
    "agents_executed": 4,
    "agents_skipped": 2,
    "sla_status": "WITHIN_SLA",
    "started_at": "2026-01-28T10:00:00Z",
    "completed_at": "2026-01-28T10:00:27Z"
  },
  "agent_results": [
    {
      "agent": "code_best_practises_agent",
      "status": "PASSED",
      "execution_time_ms": 12000,
      "violations_count": 0
    },
    {
      "agent": "architect_best_practises_agent",
      "status": "NEW_PATTERN_FOUND",
      "execution_time_ms": 5200,
      "new_pattern_detected": true
    },
    {
      "agent": "lld_alignment_review_agent",
      "status": "LLD_COMPLIANT",
      "execution_time_ms": 8500,
      "deviations_count": 0
    },
    {
      "agent": "peer_review_documentation_agent",
      "status": "REVIEWERS_ASSIGNED",
      "execution_time_ms": 1200,
      "reviewers_assigned": ["architect1", "senior-eng1"]
    }
  ],
  "routing_decision": "PENDING_HUMAN_REVIEW",
  "next_step": "await_peer_review_approval",
  "jira_ticket": null,
  "github_status_check": "neutral",
  "timestamp": "2026-01-28T10:00:27Z"
}
```

---

## 6. Configuration Reference

### 6.1 Environment Variables

**Agent Configuration**:
- `AGENT_TIMEOUT`: 30000 (Agent timeout in milliseconds)
- `CODE_AGENT_SLA`: 30 (Code Best Practices Agent SLA in seconds)
- `ARCHITECT_AGENT_SLA`: 10 (Architect Agent SLA in seconds)
- `LLD_AGENT_SLA`: 20 (LLD Alignment Agent SLA in seconds)
- `PATTERN_AGENT_SLA`: 5 (Pattern Matching Agent SLA in seconds)
- `PEER_REVIEW_SLA`: 14400 (Peer Review SLA in seconds - 4 hours)

**Confluence Configuration**:
- `CONFLUENCE_BASE_URL`: https://confluence.tonic.com
- `CONFLUENCE_SPACE_PATTERNS`: SCM-PATTERNS
- `CONFLUENCE_SPACE_LLD`: SCM-LLD

**Jira Configuration**:
- `JIRA_BASE_URL`: https://tonic.atlassian.net
- `JIRA_PROJECT`: SCM
- `JIRA_DEFAULT_ASSIGNEE`: architecture-team-lead@tonic.com

**GitHub Configuration**:
- `PR_NUMBER`: GitHub PR number
- `REPOSITORY`: GitHub repository (owner/repo format)

**AWS Configuration**:
- `AWS_REGION`: us-east-1

### 6.2 GitHub Secrets

**Required Secrets** (stored in GitHub repository settings):

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `CONFLUENCE_API_TOKEN` | Confluence API token | `eyJ...` |
| `CONFLUENCE_BASE_URL` | Confluence instance URL | `https://confluence.tonic.com` |
| `JIRA_API_TOKEN` | Jira API token | `ATATT...` |
| `JIRA_USER_EMAIL` | Jira user email | `automation@tonic.com` |
| `JIRA_BASE_URL` | Jira instance URL | `https://tonic.atlassian.net` |
| `JIRA_DEFAULT_ASSIGNEE` | Default assignee | `architecture-team-lead@tonic.com` |
| `AWS_ACCESS_KEY_ID` | AWS credentials | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `wJalr...` |

### 6.3 Branch Protection Settings

**Main Branch Protection**:

Required Status Checks (5 blocking):
- pr-orchestrator / workflow-validation
- code-quality / code-best-practises
- architecture / architect-best-practises
- ci-build / build-and-test
- ci-security / security-scan

Protection Rules:
- Require pull request before merging: Yes
- Require approvals: 0 (handled by orchestrator)
- Dismiss stale reviews: Yes
- Require status checks to pass: Yes
- Require branches to be up to date: Yes
- Require conversation resolution: Yes
- Require linear history: Yes
- Do not allow bypassing: Yes (enforce for admins)
- Allow force pushes: No
- Allow deletions: No

---

## 7. Monitoring and Observability

### 7.1 CloudWatch Metrics

**Agent Performance Metrics**:

| Metric Name | Namespace | Dimensions | Unit | Description |
|-------------|-----------|------------|------|-------------|
| `AgentExecutionTime` | PRPeerReview | Agent, PR, Repository | Milliseconds | Agent execution time |
| `AgentSuccessRate` | PRPeerReview | Agent | Percent | Success rate per agent |
| `AgentErrorRate` | PRPeerReview | Agent | Percent | Error rate per agent |
| `AgentSLACompliance` | PRPeerReview | Agent | Percent | SLA compliance rate |
| `WorkflowEndToEndTime` | PRPeerReview | Repository | Seconds | Total workflow time |
| `JiraTicketCreationSuccess` | PRPeerReview | Repository | Count | Jira ticket creation success count |
| `PatternDetectionRate` | PRPeerReview | Repository | Count | New patterns detected |

**Example CloudWatch Query**:

```
fields @timestamp, agent, execution_time_ms, status
| filter namespace = "PRPeerReview"
| filter agent = "code_best_practises_agent"
| stats avg(execution_time_ms) as avg_time,
        pct(execution_time_ms, 95) as p95_time,
        pct(execution_time_ms, 99) as p99_time
        by bin(5m)
```

### 7.2 CloudWatch Alarms

**Critical Alarms**:

1. **Agent Timeout Alarm**:
   - Metric: AgentExecutionTime > SLA threshold
   - Threshold: P95 > SLA + 50%
   - Actions: SNS notification to DevOps team

2. **High Error Rate Alarm**:
   - Metric: AgentErrorRate > 5%
   - Evaluation periods: 2 consecutive periods
   - Actions: SNS notification to on-call engineer

3. **Confluence/Jira Unavailable Alarm**:
   - Metric: API error rate > 10%
   - Evaluation periods: 3 consecutive periods
   - Actions: SNS notification + PagerDuty escalation

4. **SLA Breach Alarm**:
   - Metric: AgentSLACompliance < 90%
   - Evaluation periods: 5-minute rolling window
   - Actions: SNS notification to architecture team

### 7.3 Logging Patterns

**Agent Execution Log**:

```json
{
  "timestamp": "2026-01-28T10:00:12.345Z",
  "level": "INFO",
  "agent": "code_best_practises_agent",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "action": "execution_completed",
  "execution_time_ms": 12000,
  "status": "PASSED",
  "violations_count": 0,
  "workflow_id": "1234567890"
}
```

**Error Log**:

```json
{
  "timestamp": "2026-01-28T10:00:15.678Z",
  "level": "ERROR",
  "agent": "lld_alignment_review_agent",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "action": "confluence_api_error",
  "error_type": "TimeoutError",
  "error_message": "Confluence API request timed out after 5000ms",
  "retry_attempt": 1,
  "workflow_id": "1234567890"
}
```

### 7.4 Dashboards

**PR Peer Review Dashboard** (CloudWatch):

**Widgets**:
1. Agent Execution Time (Line graph - P50, P95, P99)
2. Agent Success Rate (Stacked area chart)
3. Workflow End-to-End Time (Histogram)
4. SLA Compliance Rate (Gauge)
5. Jira Ticket Creation Rate (Bar chart)
6. Pattern Detection Rate (Line graph)
7. Error Rate by Agent (Heatmap)
8. Top 5 Repositories by PR Volume (Pie chart)

**Example Dashboard JSON** (CloudWatch):

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["PRPeerReview", "AgentExecutionTime", { "stat": "Average" }],
          ["...", { "stat": "p95" }],
          ["...", { "stat": "p99" }]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Agent Execution Time"
      }
    }
  ]
}
```

---

## 8. Troubleshooting Guide

### 8.1 Common Issues

#### Issue 1: Workflow Not Triggering

**Symptoms**:
- PR created but workflow doesn't run
- No GitHub Actions workflow execution

**Possible Causes**:
1. Workflow file syntax error
2. Workflow not on default branch
3. PR branch not in trigger list

**Solutions**:
1. Validate YAML syntax: `yamllint .github/workflows/peer_review.yml`
2. Ensure workflow committed to default branch
3. Check workflow trigger matches PR target branch
4. Verify GitHub Actions is enabled for repository

**Debug Steps**:
```bash
# Check workflow file exists
ls -la .github/workflows/peer_review.yml

# Validate YAML syntax
yamllint .github/workflows/peer_review.yml

# Check recent workflow runs
gh run list --repo tonic-scm/order-service --limit 10
```

#### Issue 2: Agent Timeout

**Symptoms**:
- Job exceeds timeout and fails
- CloudWatch alarm triggered

**Possible Causes**:
1. Agent processing too slow
2. Confluence/Jira API slow response
3. Large PR with many files

**Solutions**:
1. Increase job timeout in workflow (temporary)
2. Optimize agent code for performance
3. Implement caching for Confluence patterns
4. Parallelize file processing in agents

**Debug Steps**:
```bash
# Check agent execution time in CloudWatch Insights
aws logs insights start-query \
  --log-group-name /aws/lambda/code-best-practises-agent \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, execution_time_ms | stats avg(execution_time_ms) as avg_time'

# Check for slow Confluence API calls
grep "confluence_api_duration" /var/log/agent.log | awk '{sum+=$3; count++} END {print sum/count}'
```

#### Issue 3: Jira Ticket Creation Failed

**Symptoms**:
- Workflow completes but no Jira ticket created
- Jira Integration Agent reports error

**Possible Causes**:
1. Invalid Jira API token
2. Jira API unavailable
3. Invalid Jira project or issue type
4. User lookup failed (Account ID not found)

**Solutions**:
1. Validate JIRA_API_TOKEN secret
2. Test Jira API connectivity
3. Verify Jira project exists and issue types configured
4. Check retry queue (SQS) for pending tickets
5. Verify user exists in Jira with email lookup

**Debug Steps**:
```bash
# Test Jira API connectivity
curl -H "Authorization: Bearer $JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/3/myself"

# Check SQS retry queue
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789/jira-ticket-retry-queue \
  --attribute-names ApproximateNumberOfMessages

# Test user lookup
curl -H "Authorization: Bearer $JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/3/user/search?query=developer1@tonic.com"
```

#### Issue 4: Pattern Not Detected

**Symptoms**:
- Expected new pattern but Architect Agent reports NO_NEW_PATTERN
- Pattern similarity too high

**Possible Causes**:
1. Pattern already exists in library (high similarity)
2. Similarity threshold too high (>85%)
3. Pattern cache stale

**Solutions**:
1. Review pattern library for similar patterns
2. Adjust similarity threshold (lower to 75% for testing)
3. Clear pattern cache (Redis)
4. Manually review code to confirm pattern is new

**Debug Steps**:
```bash
# Check pattern library in Confluence
curl -H "Authorization: Bearer $CONFLUENCE_API_TOKEN" \
  "$CONFLUENCE_BASE_URL/wiki/rest/api/content?spaceKey=SCM-PATTERNS&type=page" | jq '.results[].title'

# Clear pattern cache in Redis
redis-cli -h pattern-cache.redis.amazonaws.com FLUSHDB

# Check Architect Agent logs for similarity scores
grep "similarity_score" /var/log/architect-agent.log | tail -20
```

#### Issue 5: Merge Blocked Despite All Checks Passing

**Symptoms**:
- All status checks green
- Merge button disabled

**Possible Causes**:
1. Branch not up to date with base
2. Conversation threads not resolved
3. Required reviews not provided
4. Status check name mismatch in branch protection

**Solutions**:
1. Update branch: `git merge origin/main && git push`
2. Resolve all PR comment threads
3. Request reviews from required reviewers
4. Verify status check names match branch protection rules

**Debug Steps**:
```bash
# Check PR merge status
gh pr view 123 --json mergeable,mergeStateStatus

# Check branch protection rules
gh api /repos/tonic-scm/order-service/branches/main/protection | jq '.required_status_checks.checks'

# Check PR status checks
gh pr view 123 --json statusCheckRollup | jq '.statusCheckRollup[].name'
```

### 8.2 Debug Procedures

**Agent Debug Procedure**:

1. **Check Agent Logs**:
   ```bash
   # CloudWatch Logs
   aws logs tail /aws/lambda/code-best-practises-agent --follow

   # Local logs (if running locally)
   tail -f /var/log/agent.log
   ```

2. **Check Agent Metrics**:
   ```bash
   # CloudWatch metrics
   aws cloudwatch get-metric-statistics \
     --namespace PRPeerReview \
     --metric-name AgentExecutionTime \
     --dimensions Name=Agent,Value=code_best_practises_agent \
     --start-time $(date -d '1 hour ago' --iso-8601) \
     --end-time $(date --iso-8601) \
     --period 300 \
     --statistics Average,Maximum
   ```

3. **Test Agent Locally**:
   ```bash
   # Invoke agent with test payload
   aws lambda invoke \
     --function-name code-best-practises-agent \
     --payload '{"pr_number": 123, "repository": "tonic-scm/order-service"}' \
     response.json

   cat response.json | jq '.'
   ```

4. **Check External Dependencies**:
   ```bash
   # Test Confluence connectivity
   curl -I "$CONFLUENCE_BASE_URL/wiki/rest/api/content"

   # Test Jira connectivity
   curl -I "$JIRA_BASE_URL/rest/api/3/myself"
   ```

**Workflow Debug Procedure**:

1. **Check Workflow Logs**:
   ```bash
   # View latest workflow run
   gh run view --log

   # View specific job logs
   gh run view --job 12345 --log
   ```

2. **Check Workflow Status**:
   ```bash
   # List recent workflow runs
   gh run list --workflow peer_review.yml --limit 10

   # View specific run details
   gh run view 1234567890
   ```

3. **Re-run Failed Workflow**:
   ```bash
   # Re-run failed jobs
   gh run rerun 1234567890 --failed

   # Re-run entire workflow
   gh run rerun 1234567890
   ```

### 8.3 Emergency Procedures

**Procedure 1: Bypass Workflow for Critical Hotfix**

**When to Use**: Production down, immediate fix required

**Approval Required**: VP Engineering or CTO

**Steps**:
1. Document justification in incident ticket
2. Temporarily disable branch protection:
   ```bash
   gh api --method PUT /repos/tonic-scm/order-service/branches/main/protection \
     --field enforce_admins=false
   ```
3. Merge hotfix PR:
   ```bash
   gh pr merge 123 --admin --squash
   ```
4. Re-enable branch protection:
   ```bash
   gh api --method PUT /repos/tonic-scm/order-service/branches/main/protection \
     --field enforce_admins=true
   ```
5. Post-incident: Run retrospective compliance check, update runbook

**Procedure 2: Confluence/Jira Outage Recovery**

**When to Use**: Confluence or Jira unavailable for >15 minutes

**Steps**:
1. Check service status pages:
   - Confluence: https://status.atlassian.com
   - Jira: https://status.atlassian.com
2. If prolonged outage (>1 hour), enable degraded mode:
   - Disable agents dependent on Confluence/Jira
   - Allow PRs to merge with remaining checks only
3. Process queued operations (SQS) after recovery:
   ```bash
   # Check retry queue depth
   aws sqs get-queue-attributes \
     --queue-url https://sqs.us-east-1.amazonaws.com/123456789/jira-ticket-retry-queue \
     --attribute-names ApproximateNumberOfMessages

   # Process queued tickets
   aws lambda invoke \
     --function-name jira-ticket-processor \
     --invocation-type Event
   ```

**Procedure 3: Agent Cascade Failure**

**When to Use**: Multiple agents failing simultaneously

**Steps**:
1. Identify root cause (check CloudWatch dashboard)
2. If external dependency failure:
   - Implement circuit breaker (automatic)
   - Notify on-call engineer
3. If agent code bug:
   - Roll back to previous version
   - Deploy hotfix
4. Monitor recovery:
   ```bash
   # Check error rate
   aws cloudwatch get-metric-statistics \
     --namespace PRPeerReview \
     --metric-name AgentErrorRate \
     --statistics Average \
     --start-time $(date -d '1 hour ago' --iso-8601) \
     --end-time $(date --iso-8601) \
     --period 300
   ```

---

## Appendices

### Appendix A: Glossary

**Terms**:
- **PR**: Pull Request (GitHub)
- **SLA**: Service Level Agreement (time constraint for operation)
- **LLD**: Low-Level Design document
- **ADF**: Atlassian Document Format (Jira/Confluence rich text format)
- **GDPR**: General Data Protection Regulation (requires Account ID for user operations)
- **DDB**: DynamoDB (AWS NoSQL database)
- **SQS**: Simple Queue Service (AWS message queue)

### Appendix B: References

**Documentation**:
- GitHub Actions: https://docs.github.com/en/actions
- Jira REST API: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- Confluence REST API: https://developer.atlassian.com/cloud/confluence/rest/v2/
- AWS CloudWatch: https://docs.aws.amazon.com/cloudwatch/

**Internal Documents**:
- C:\Users\ClaudeIlunga\OneDrive - Command Quality\Documents\scm\tonic-agentic-playpen\tonic-peer-review-agent\pr_orchestrator_agent_spec.md
- C:\Users\ClaudeIlunga\OneDrive - Command Quality\Documents\scm\tonic-agentic-playpen\tonic-peer-review-agent\jira_integration_agent_enhancement_spec.md
- C:\Users\ClaudeIlunga\OneDrive - Command Quality\Documents\scm\tonic-agentic-playpen\tonic-peer-review-agent\research\workflow_implementation_guide.md
- C:\Users\ClaudeIlunga\OneDrive - Command Quality\Documents\scm\tonic-agentic-playpen\tonic-peer-review-agent\research\jira_automation_research.md
- C:\Users\ClaudeIlunga\OneDrive - Command Quality\Documents\scm\tonic-agentic-playpen\tonic-peer-review-agent\research\branch_protection_config.md

### Appendix C: Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-28 | Claude | Initial system documentation |

---

**End of System Documentation**
