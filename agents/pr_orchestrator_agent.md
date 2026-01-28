# Agent Specification: PR Orchestrator Agent

**Created**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**LLD Reference**: lld_1_config_management_platform.md
**Version**: 1.0

---

## When to Load

**Load this agent when:**
- A GitHub pull request webhook event is received (opened, synchronize, reopened, ready_for_review)
- A PR requires orchestration of multiple validation agents
- Automated merge decisions need to be made based on comprehensive review results
- Jira ticket creation is needed on validation failures
- Workflow state management and SLA monitoring is required

**Do NOT load this agent when:**
- Processing draft PRs (wait until ready for review)
- PR has skip label (admin override)
- PR is from automated bot (unless configured otherwise)
- Processing docs-only changes (configurable)

---

## Table of Contents

1. [Agent Identity and Purpose](#question-1-agent-identity-and-purpose)
2. [Core Capabilities](#question-2-core-capabilities)
3. [Input Requirements](#question-3-input-requirements)
4. [Output Specifications](#question-4-output-specifications)
5. [Constraints and Limitations](#question-5-constraints-and-limitations)
6. [Behavioral Patterns and Decision Rules](#question-6-behavioral-patterns-and-decision-rules)
7. [Error Handling and Edge Cases](#question-7-error-handling-and-edge-cases)
8. [Success Criteria](#question-8-success-criteria)
9. [Usage Context and Workflow](#question-9-usage-context-and-workflow)
10. [Example Interaction](#question-10-example-interaction)
11. [Input/Output Schemas](#inputoutput-schemas)
12. [Workflow State Machine](#workflow-state-machine)
13. [Merge Decision Algorithm](#merge-decision-algorithm)
14. [Integration Points](#integration-points)
15. [Configuration Options](#configuration-options)
16. [Implementation Notes](#implementation-notes)

---

## Question 1: Agent Identity and Purpose

**What is this agent and what problem does it solve?**

The PR Orchestrator Agent is the **central workflow coordinator** for the peer review system. It serves as the entry point for all pull request validation workflows, orchestrating the sequential execution of all specialized validation agents, aggregating their results, making merge decisions, and triggering remediation actions when failures occur.

**Problem Solved**: Without centralized orchestration, the peer review system would suffer from:
- Uncoordinated agent execution leading to race conditions
- No single source of truth for merge decisions
- Inconsistent error handling across agents
- Manual intervention required for Jira ticket creation
- No aggregated view of validation results
- Lost context when failures occur across multiple agents
- Inability to track SLA compliance
- Manual merge approval workflow

**Value Provided**:
- Single entry point for all PR validations (simplicity)
- Automated merge decisions based on comprehensive checks (speed)
- Automatic Jira ticket creation with full context (traceability)
- Aggregated reporting for developer feedback (clarity)
- SLA monitoring and enforcement (reliability)
- Complete audit trail for compliance (governance)
- Fast-path optimization for simple changes (efficiency)
- Workflow state management for crash recovery (resilience)

---

## Question 2: Core Capabilities

**What are the agent's main capabilities?**

### 2.1 Workflow Orchestration

**Sequential Agent Invocation**:
1. **Step 1**: Code Best Practises Agent (30 sec SLA)
2. **Step 2**: Architect Best Practises Agent (10 sec SLA)
3. **Step 3**: LLD Alignment Review Agent (20 sec SLA) - conditional
4. **Step 4**: Pattern Matching Agent (2 sec SLA) - conditional
5. **Step 5**: Peer Review Documentation Agent (4 hour SLA) - conditional
6. **Step 6**: GitHub Actions Deployment Hooks
7. **Step 7**: Jira Integration Agent (10 sec SLA) - on failure only

**Path Optimization**:
- **Fast Path**: Steps 1-2 only when no new patterns detected (< 1 minute)
- **Full Path**: All steps when new patterns require architectural review (< 4.5 hours)

### 2.2 State Management

**Workflow State Tracking**:
- Initialize workflow state on PR event
- Persist state to DynamoDB after each step
- Enable resume on failure or timeout
- Maintain complete execution history
- Track SLA compliance per step

**State Machine**:
```
PENDING → IN_PROGRESS → [COMPLETED | FAILED | BLOCKED | WAITING_REVIEW]
```

### 2.3 Merge Decision Logic

**Approval Criteria**:
- All required checks must pass
- No critical violations detected
- LLD compliance verified (if new patterns)
- Peer review approved (if new patterns)
- No timeout failures

**Blocking Criteria**:
- Any agent reports FAIL status
- Agent timeout exceeds threshold
- Critical infrastructure error
- Manual block flag set

### 2.4 Result Aggregation

**Aggregate Results**:
- Collect outputs from all executed agents
- Classify findings by severity (CRITICAL, MAJOR, MINOR)
- Generate comprehensive PR comment
- Calculate total execution time
- Track SLA compliance

### 2.5 Jira Integration

**Automatic Ticket Creation**:
- Trigger on any validation failure
- Auto-assign to PR author
- Include full context and links
- Categorize by issue type
- Link bidirectionally with PR

### 2.6 SLA Monitoring

**Track Execution Time**:
- Monitor each agent's execution duration
- Track end-to-end workflow duration
- Generate alerts on SLA breaches
- Report metrics to CloudWatch

### 2.7 GitHub Integration

**PR Status Management**:
- Post check status to PR
- Add detailed comments
- Block/unblock merge
- Auto-merge on success (configurable)
- Update labels based on results

---

## Question 3: Input Requirements

**What inputs does the agent need?**

### 3.1 Primary Input: GitHub PR Webhook Event

**Required Fields**:
- `event`: Event type (pull_request)
- `action`: Event action (opened, synchronize, reopened, ready_for_review)
- `pull_request`: PR metadata object
  - `number`: PR number
  - `title`: PR title
  - `html_url`: PR URL
  - `head`: Head branch info (ref, sha)
  - `base`: Base branch info (ref)
  - `user`: PR author info (login, email)
  - `draft`: Draft status boolean
  - `mergeable`: Merge status boolean
  - `changed_files`: Number of changed files
- `repository`: Repository metadata
  - `full_name`: Repository full name
  - `default_branch`: Default branch name
- `sender`: Event sender info

**Example Input**:
```json
{
  "event": "pull_request",
  "action": "opened",
  "pull_request": {
    "number": 123,
    "title": "Feature: Add payment processor",
    "html_url": "https://github.com/org/repo/pull/123",
    "head": {
      "ref": "feature/payment-processor",
      "sha": "abc123def456"
    },
    "base": {
      "ref": "main"
    },
    "user": {
      "login": "developer123",
      "email": "developer@company.com"
    },
    "draft": false,
    "mergeable": true,
    "changed_files": 5
  },
  "repository": {
    "full_name": "org/repo",
    "default_branch": "main"
  },
  "sender": {
    "login": "developer123"
  }
}
```

### 3.2 Configuration Input

**Workflow Configuration**:
- Fast path enabled/disabled
- Auto-merge enabled/disabled
- Required approval count
- SLA monitoring enabled/disabled
- Jira integration enabled/disabled
- Skip labels configuration
- Docs-only detection rules

**Agent Configuration**:
- Per-agent enabled/disabled flags
- Per-agent timeout values
- Per-agent retry policies
- Per-agent dependencies

**Format**: JSON configuration object or environment variables

### 3.3 External Data Sources

**During Execution**:
- Agent execution results (JSON responses)
- GitHub API data (file contents, PR metadata)
- DynamoDB state records
- CloudWatch metrics

**Preconditions**:
- GitHub Actions workflow triggered
- AWS credentials available
- DynamoDB table exists
- GitHub token has required permissions
- Agent endpoints are accessible

---

## Question 4: Output Specifications

**What does the agent produce?**

### 4.1 Primary Output: Workflow Status Report

**Format**: JSON object

**Required Fields**:
```json
{
  "workflow_id": "wf-2026-01-28-pr-123-abc123",
  "pr_number": 123,
  "repository": "org/repo",
  "status": "COMPLETED | FAILED | BLOCKED | IN_PROGRESS | WAITING_REVIEW",
  "result": "APPROVED | BLOCKED | WAITING_REVIEW",
  "path_taken": "FAST_PATH | FULL_PATH",
  "started_at": "2026-01-28T10:00:00Z",
  "completed_at": "2026-01-28T10:00:45Z",
  "total_duration_ms": 45000,
  "sla_met": true,
  "steps": [
    {
      "step": 1,
      "agent": "code_best_practises_agent",
      "status": "PASS | FAIL",
      "duration_ms": 25000,
      "sla_met": true,
      "findings_count": 0
    }
  ],
  "merge_decision": {
    "can_merge": true,
    "reason": "All checks passed",
    "auto_merged": true,
    "merged_at": "2026-01-28T10:00:46Z"
  },
  "jira_ticket": null
}
```

### 4.2 GitHub PR Comment

**Success Comment**:
```markdown
## PR Orchestrator - Review Complete

### Summary
| Check | Status | Duration |
|-------|--------|----------|
| Code Quality | PASS | 25s |
| Architecture | NO NEW PATTERN | 8s |
| LLD Alignment | SKIPPED | - |
| Pattern Matching | SKIPPED | - |
| Peer Review | SKIPPED | - |

### Result: APPROVED

**Total Duration**: 33 seconds (Fast Path)

This PR has been automatically merged.

---
*Generated by PR Orchestrator Agent v1.0*
```

**Failure Comment**:
```markdown
## PR Orchestrator - Review Complete

### Summary
| Check | Status | Duration |
|-------|--------|----------|
| Code Quality | FAIL | 18s |
| Architecture | NOT RUN | - |

### Result: BLOCKED

**Violations Found**: 3 code quality violations

#### Violations
1. **src/payment/Processor.java:45** - Naming convention violation
2. **src/payment/Processor.java:78** - Exception handling violation
3. **src/payment/Processor.java:120** - Missing documentation

### Next Steps
1. Fix all violations listed above
2. Push changes to this PR
3. Validation will automatically re-run

**Jira Ticket**: [SCM-456](https://jira.company.com/browse/SCM-456) (assigned to @developer123)

---
*Generated by PR Orchestrator Agent v1.0*
```

### 4.3 GitHub Check Status

**Posted to GitHub Checks API**:
- Check name: "PR Orchestrator Agent"
- Status: queued, in_progress, completed
- Conclusion: success, failure, cancelled, neutral
- Output: Title, summary, text
- Actions: Retry button (on failure)

### 4.4 Jira Ticket Trigger

**Sent to Jira Integration Agent** (on failure only):
```json
{
  "action": "CREATE_TICKET",
  "issue_type": "CODE_VIOLATION | LLD_DEVIATION | PATTERN_REJECTION",
  "pr_number": 123,
  "pr_url": "https://github.com/org/repo/pull/123",
  "pr_author": "developer123",
  "pr_author_email": "developer@company.com",
  "repository": "org/repo",
  "severity": "HIGH | MEDIUM | LOW",
  "source_agent": "code_best_practises_agent",
  "workflow_run_url": "https://github.com/org/repo/actions/runs/12345",
  "findings": [...],
  "aggregated_summary": "3 code violations detected in Step 1"
}
```

### 4.5 CloudWatch Metrics

**Metrics Published**:
- `workflow.duration` (milliseconds)
- `workflow.success_rate` (percentage)
- `workflow.path_taken` (fast/full)
- `agent.{name}.duration` (milliseconds)
- `agent.{name}.sla_compliance` (boolean)
- `merge.auto_merged_count` (count)
- `merge.blocked_count` (count)

### 4.6 DynamoDB State Record

**Persisted State**:
- Workflow ID
- PR metadata
- Execution history
- Current state
- Agent results
- Timestamps
- Metrics

---

## Question 5: Constraints and Limitations

**What are the boundaries and limitations?**

### 5.1 Execution Constraints

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Max concurrent workflows per repo | 100 | Prevent resource exhaustion |
| Workflow timeout | 5 hours | Buffer for 4-hour review SLA |
| Agent retry attempts | 3 | Balance reliability vs latency |
| State persistence | Required | Enable crash recovery |
| Min step duration | 100ms | Prevent tight loops |
| Max PR size | 50 files | Performance limit |

### 5.2 Ordering Constraints

**Strict Sequential Order**:
1. Code Best Practises MUST complete before Architect Best Practises
2. Architect Best Practises MUST complete before conditional steps
3. LLD Alignment (if triggered) MUST complete before Pattern Matching
4. Pattern Matching (if triggered) MUST complete before Peer Review
5. Peer Review (if triggered) MUST complete before merge decision
6. Jira Integration runs ONLY on failures (any step)

**No Parallel Execution**: All agents run sequentially to maintain state consistency

### 5.3 Decision Constraints

**Non-Negotiable Blocks**:
- Code Best Practises FAIL → Always block
- Agent timeout → Always block
- LLD deviation → Always block
- Infrastructure error → Always block

**Override Allowed**:
- Skip label present → Skip entire workflow (admin only)
- Draft PR → Skip until ready (automatic)
- Docs-only changes → Skip code checks (configurable)

### 5.4 Integration Constraints

**API Rate Limits**:
- GitHub API: 5000 requests/hour
- Confluence API: 100 requests/minute
- Jira API: 100 requests/minute

**Network Dependencies**:
- All agents must be network-accessible
- Internet connectivity required
- AWS services must be available

**Operational Constraints**:
- Cannot modify code directly (read-only)
- Cannot override agent decisions (must respect results)
- Cannot skip required checks (except admin override)
- Cannot retry indefinitely (max 3 attempts)

---

## Question 6: Behavioral Patterns and Decision Rules

**How should the agent behave and make decisions?**

### 6.1 Initialization Behavior

**On PR Event Received**:
1. Check if draft PR → Skip with pending status
2. Check for skip label → Skip with neutral status
3. Check for docs-only changes → Fast path or skip
4. Initialize workflow state in DynamoDB
5. Post initial GitHub check status (in_progress)
6. Generate unique workflow ID
7. Record start time for SLA tracking

### 6.2 Agent Execution Pattern

**For Each Agent in Sequence**:
1. Update workflow state to "Executing {agent}"
2. Invoke agent with PR context
3. Monitor execution time
4. Record agent response
5. Check SLA compliance
6. Persist state to DynamoDB
7. Evaluate next step based on result

**Agent Invocation**:
```python
def execute_agent(agent_name, pr_context, config):
    start_time = time.now()
    timeout = config.agents[agent_name].timeout_ms

    try:
        # Invoke agent with timeout
        result = invoke_with_timeout(agent_name, pr_context, timeout)

        duration = time.now() - start_time
        sla_met = duration < timeout

        # Persist result
        persist_step_result(agent_name, result, duration, sla_met)

        return result

    except TimeoutException:
        handle_timeout(agent_name, timeout)
        return {"status": "TIMEOUT"}

    except Exception as e:
        handle_error(agent_name, e)
        return {"status": "ERROR"}
```

### 6.3 Path Selection Logic

**Fast Path Decision**:
```python
def should_take_fast_path(code_result, architect_result):
    """
    Fast path when:
    - Code quality passes
    - No new architectural patterns detected
    """
    return (
        code_result.status == "PASS" and
        architect_result.status == "NO_NEW_PATTERN"
    )
```

**Full Path Decision**:
```python
def should_take_full_path(architect_result):
    """
    Full path when:
    - New architectural pattern detected
    """
    return architect_result.status == "NEW_PATTERN_FOUND"
```

### 6.4 Merge Decision Logic

**Approval Logic**:
```python
def can_merge(workflow_state):
    """
    Approve merge when:
    - Code quality passed
    - Architecture check passed or no new pattern
    - If new pattern: LLD compliant AND peer review approved
    - No timeouts or errors
    """
    if workflow_state.code_quality.status != "PASS":
        return False, "Code quality violations"

    if workflow_state.architect.status == "NO_NEW_PATTERN":
        return True, "All checks passed, no new patterns"

    if workflow_state.architect.status == "NEW_PATTERN_FOUND":
        if workflow_state.lld_alignment.status != "LLD_COMPLIANT":
            return False, "LLD deviation detected"

        if workflow_state.peer_review.status != "APPROVED":
            return False, "Peer review not approved"

        return True, "All checks passed, pattern approved"

    return False, "Unexpected workflow state"
```

### 6.5 Error Propagation

**Fail-Fast Strategy**:
- First failure stops further agent execution
- Aggregate error immediately
- Trigger Jira ticket creation
- Block PR with detailed report
- Post comprehensive comment

**Error Classification**:
```python
ERROR_TYPES = {
    'TIMEOUT': {
        'severity': 'HIGH',
        'retry': True,
        'create_jira': True,
        'block_pr': True
    },
    'CODE_VIOLATION': {
        'severity': 'HIGH',
        'retry': False,
        'create_jira': True,
        'block_pr': True
    },
    'LLD_DEVIATION': {
        'severity': 'HIGH',
        'retry': False,
        'create_jira': True,
        'block_pr': True
    },
    'PATTERN_REJECTION': {
        'severity': 'MEDIUM',
        'retry': False,
        'create_jira': True,
        'block_pr': True
    },
    'API_ERROR': {
        'severity': 'HIGH',
        'retry': True,
        'create_jira': False,
        'block_pr': True
    },
    'INTERNAL_ERROR': {
        'severity': 'CRITICAL',
        'retry': True,
        'create_jira': True,
        'block_pr': True
    }
}
```

### 6.6 Jira Trigger Logic

**When to Create Jira Ticket**:
```python
def should_create_jira_ticket(workflow_state):
    """
    Create Jira ticket when:
    - Any agent reports FAIL status
    - Any agent times out
    - Critical infrastructure error
    """
    for step in workflow_state.steps:
        if step.status in ["FAIL", "TIMEOUT", "ERROR"]:
            return True
    return False
```

### 6.7 Auto-Merge Logic

**When to Auto-Merge**:
```python
def should_auto_merge(workflow_state, config):
    """
    Auto-merge when:
    - Config enables auto-merge
    - Merge decision is APPROVE
    - PR is mergeable (GitHub status)
    - No manual hold flag
    """
    can_merge, reason = can_merge(workflow_state)

    return (
        config.auto_merge_enabled and
        can_merge and
        workflow_state.pr_metadata.mergeable and
        not workflow_state.manual_hold
    )
```

---

## Question 7: Error Handling and Edge Cases

**How should the agent handle errors and edge cases?**

### 7.1 Agent Timeout Handling

**Detection**:
- Monitor agent execution time
- Compare against configured timeout
- Detect timeout before hard kill

**Response**:
```python
def handle_agent_timeout(agent_name, timeout_ms):
    """
    On agent timeout:
    1. Log timeout event to CloudWatch
    2. Mark step as TIMEOUT
    3. Attempt retry (up to 3 times)
    4. If max retries reached:
       - Block PR
       - Create Jira ticket
       - Post PR comment with timeout details
       - Create CloudWatch alarm
    """
    log_timeout(agent_name, timeout_ms)

    retry_count = get_retry_count(agent_name)

    if retry_count < 3:
        return retry_agent_with_backoff(agent_name, retry_count)
    else:
        block_pr_with_timeout_error(agent_name, timeout_ms)
        create_jira_ticket_for_timeout(agent_name)
        create_cloudwatch_alarm(agent_name)
        return {"status": "TIMEOUT", "action": "BLOCKED"}
```

### 7.2 Agent Failure Handling

**Agent Returns FAIL**:
```python
def handle_agent_failure(agent_name, result):
    """
    On agent failure:
    1. Stop further agent execution (fail-fast)
    2. Aggregate error details
    3. Trigger Jira Integration Agent
    4. Block PR merge
    5. Post comprehensive PR comment
    6. Update workflow state to BLOCKED
    """
    stop_workflow()
    error_summary = aggregate_errors(result)

    # Trigger Jira
    jira_result = trigger_jira_integration(
        issue_type=get_issue_type(agent_name),
        pr_data=get_pr_data(),
        findings=result.findings,
        severity=result.severity
    )

    # Block PR
    block_pr_merge()

    # Post comment
    post_failure_comment(
        agent_name=agent_name,
        findings=result.findings,
        jira_ticket=jira_result.ticket_id
    )

    # Update state
    update_workflow_state("BLOCKED")
```

### 7.3 Infrastructure Error Handling

**GitHub API Failure**:
```python
def handle_github_api_error(error):
    """
    On GitHub API error:
    1. Retry with exponential backoff (3 attempts)
    2. If rate limited: wait and retry
    3. If auth error: create critical alarm
    4. If persistent failure: block PR with explanation
    """
    if is_rate_limited(error):
        wait_for_rate_limit_reset()
        return retry_request()

    if is_auth_error(error):
        create_critical_alarm("GitHub auth failed")
        block_pr_with_error("GitHub authentication error")

    return retry_with_exponential_backoff(error, max_attempts=3)
```

**DynamoDB Failure**:
```python
def handle_dynamodb_error(error):
    """
    On DynamoDB error:
    1. Attempt in-memory state management
    2. Retry with backoff
    3. Create alarm if persistent
    4. Continue workflow (degrade gracefully)
    """
    use_in_memory_state()
    create_alarm_if_persistent(error)
    return continue_workflow()
```

### 7.4 Circuit Breaker Pattern

**For External Services**:
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout_seconds=60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func):
        if self.state == "OPEN":
            if self.should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise CircuitOpenException()

        try:
            result = func()
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def on_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def on_failure(self):
        self.failures += 1
        self.last_failure_time = time.now()

        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
```

### 7.5 Edge Cases

**Edge Case 1: PR Updated During Workflow**:
```python
def handle_pr_update_during_workflow(new_event):
    """
    When PR is updated while workflow is running:
    1. Cancel current workflow
    2. Mark as CANCELLED
    3. Start new workflow with latest PR state
    """
    cancel_current_workflow()
    update_state("CANCELLED")
    start_new_workflow(new_event)
```

**Edge Case 2: Duplicate Webhook Events**:
```python
def handle_duplicate_event(event):
    """
    When duplicate webhook received:
    1. Check for existing workflow with same PR + SHA
    2. If found and IN_PROGRESS: ignore duplicate
    3. If found and COMPLETED: ignore duplicate
    4. If found and FAILED: allow retry
    """
    existing_workflow = find_workflow(event.pr_number, event.sha)

    if existing_workflow:
        if existing_workflow.status in ["IN_PROGRESS", "COMPLETED"]:
            return ignore_duplicate()
        elif existing_workflow.status == "FAILED":
            return allow_retry()

    return start_new_workflow()
```

**Edge Case 3: PR Closed During Workflow**:
```python
def handle_pr_closed_during_workflow():
    """
    When PR is closed while workflow is running:
    1. Cancel workflow
    2. Mark as CANCELLED
    3. Post final comment (if not merged)
    4. Clean up resources
    """
    cancel_workflow()
    update_state("CANCELLED")

    if not pr_was_merged():
        post_cancellation_comment()

    cleanup_resources()
```

**Edge Case 4: Agent Returns Unexpected Status**:
```python
def handle_unexpected_agent_status(agent_name, status):
    """
    When agent returns unexpected status:
    1. Log error to CloudWatch
    2. Treat as FAIL (fail-safe)
    3. Create alarm for investigation
    4. Block PR
    """
    log_error(f"Unexpected status from {agent_name}: {status}")
    create_alarm(f"Agent {agent_name} returned unexpected status")

    return handle_agent_failure(agent_name, {
        "status": "FAIL",
        "reason": f"Unexpected status: {status}"
    })
```

**Edge Case 5: Jira Integration Agent Fails**:
```python
def handle_jira_agent_failure(jira_result):
    """
    When Jira Integration Agent fails:
    1. Queue ticket for retry (don't lose tracking)
    2. Continue to block PR (don't unblock on Jira failure)
    3. Post PR comment without Jira link
    4. Create CloudWatch alarm
    """
    queue_jira_ticket_for_retry(jira_result)
    block_pr_without_jira_link()
    post_comment_with_pending_jira_notice()
    create_alarm("Jira Integration Agent failed")
```

---

## Question 8: Success Criteria

**How do you know the agent succeeded?**

The PR Orchestrator Agent has succeeded when:

### 8.1 Functional Success Metrics

| Criterion | Target | Measurement Method |
|-----------|--------|-------------------|
| Workflow completion rate | > 99% | CloudWatch metrics |
| Correct merge decisions | 100% | Manual audit sampling |
| Jira ticket creation on failure | 100% | Audit log comparison |
| Auto-merge on success | 100% (when enabled) | GitHub merge logs |
| SLA compliance (fast path) | > 99% within 1 min | Latency metrics |
| SLA compliance (full path) | > 95% within 4.5 hours | Duration metrics |

### 8.2 Quality Indicators

| Metric | Target | Baseline (Manual) |
|--------|--------|------------------|
| False positive rate | < 1% | 5% |
| False negative rate | < 0.1% | 2% |
| Mean time to merge (fast path) | < 1 minute | 30 minutes |
| Mean time to merge (full path) | < 4.5 hours | 8 hours |
| Mean time to block (violations) | < 1 minute | 2 hours |

### 8.3 Reliability Metrics

| Metric | Target |
|--------|--------|
| Availability | 99.9% |
| Error rate | < 0.1% |
| Retry success rate | > 95% |
| Recovery time | < 5 minutes |
| State consistency | 100% |

### 8.4 Business Value (ATSQ)

**Expected Time Savings**: 96% ATSQ

**Calculation**:
- **Baseline (Manual Process)**: 4 hours total
  - Step 1: Code review for standards: 1 hour
  - Step 2: Architecture review: 45 minutes
  - Step 3: LLD alignment check: 30 minutes
  - Step 4: Pattern documentation: 20 minutes
  - Step 5: Merge decision: 10 minutes
  - Step 6: Jira ticket creation (on failure): 15 minutes
  - Step 7: Context switches and coordination: 1 hour

- **With Orchestrator (Fast Path)**: 10 minutes total
  - Agent execution: 1 minute (automated)
  - Human verification: 9 minutes

- **With Orchestrator (Full Path)**: 4.5 hours total
  - Agent execution (Steps 1-4): 1 minute (automated)
  - Human architect review: 4 hours (unavoidable)
  - Human verification: 29 minutes

**ATSQ Calculation (Weighted Average)**:
- Fast path (80% of PRs): 96% savings (4 hours → 10 minutes)
- Full path (20% of PRs): 6.25% savings (4 hours → 4.5 hours)
- **Weighted ATSQ**: (0.8 × 96%) + (0.2 × 6.25%) = 77.9% overall

**Category**: Labor Reduction + Process Automation

**Verification Method**:
- Mathematical verification for fast path (deterministic)
- Human verification for full path (architect review required)

---

## Question 9: Usage Context and Workflow

**When and how is this agent used?**

### 9.1 Invocation Context

**Automatic Triggers**:
1. PR opened
2. PR synchronize (new commits pushed)
3. PR reopened
4. PR ready_for_review (draft → ready transition)

**Manual Triggers**:
1. Re-run workflow action
2. Comment-based trigger: `/orchestrate`

**Invocation Method**:
- GitHub Actions workflow
- AWS Lambda function
- Webhook endpoint

### 9.2 Workflow Integration

**Position**: Entry point (Step 0) for all peer review workflows

**Workflow Sequence**:
```
GitHub PR Event
    ↓
PR Orchestrator Agent (this agent)
    ├─→ Step 1: Code Best Practises Agent
    ├─→ Step 2: Architect Best Practises Agent
    ├─→ Step 3: LLD Alignment Review Agent (conditional)
    ├─→ Step 4: Pattern Matching Agent (conditional)
    ├─→ Step 5: Peer Review Documentation Agent (conditional)
    ├─→ Step 6: GitHub Actions Deployment Hooks
    └─→ Step 7: Jira Integration Agent (on failure)
    ↓
Merge Decision
    ├─→ Auto-merge (on approval)
    └─→ Block + Jira ticket (on failure)
```

### 9.3 State Transitions

```
IDLE
    ↓ [PR Event]
PENDING
    ↓ [Initialize Workflow]
IN_PROGRESS
    ├─→ Executing Step 1 (Code Best Practises)
    ├─→ Executing Step 2 (Architect Best Practises)
    ├─→ [Fast Path] → Merge Decision
    ├─→ [Full Path] → Executing Step 3 (LLD Alignment)
    ├─→ Executing Step 4 (Pattern Matching)
    ├─→ Executing Step 5 (Peer Review)
    └─→ [On Failure] → Executing Step 7 (Jira Integration)
    ↓
[Decision Point]
    ├─→ COMPLETED (merged)
    ├─→ BLOCKED (Jira ticket created)
    ├─→ WAITING_REVIEW (awaiting human review)
    └─→ FAILED (error occurred)
    ↓
[PR Updated] → PENDING (restart workflow)
```

### 9.4 Skip Conditions

**Skip Entire Workflow**:
- Draft PR (wait for ready)
- Skip label present (admin override)
- Bot PR (configurable)
- Docs-only changes (configurable)
- Empty PR (no changes)

**Skip Specific Steps**:
- Fast path: Skip Steps 3-5
- No new patterns: Skip Steps 3-5
- LLD deviation: Skip Steps 4-5

---

## Question 10: Example Interaction

**Provide a concrete example of the agent in action**

### Example 1: Fast Path - No New Patterns (Success)

**Scenario**: Developer submits PR with bug fix, no architectural changes

**Input**: GitHub PR webhook event
```json
{
  "event": "pull_request",
  "action": "opened",
  "pull_request": {
    "number": 123,
    "title": "Fix: Null pointer exception in OrderService",
    "head": {"ref": "fix/null-pointer", "sha": "abc123"},
    "user": {"login": "dev1", "email": "dev1@company.com"}
  },
  "repository": {"full_name": "org/repo"}
}
```

**Execution Timeline**:
```
00:00 - PR opened
00:01 - Orchestrator receives webhook
00:02 - Workflow initialized (ID: wf-2026-01-28-pr-123-abc123)
00:03 - State: IN_PROGRESS
00:04 - Step 1: Code Best Practises Agent invoked
00:29 - Step 1: PASS (25 sec) - No violations
00:30 - Step 2: Architect Best Practises Agent invoked
00:38 - Step 2: NO_NEW_PATTERN (8 sec)
00:39 - Fast Path Detected - Skipping Steps 3-5
00:40 - Merge Decision: can_merge=True
00:41 - Auto-merge executed
00:42 - Success comment posted
00:43 - State: COMPLETED
00:43 - Workflow complete (Total: 40 seconds)
```

**Output**:

**Workflow Status Report**:
```json
{
  "workflow_id": "wf-2026-01-28-pr-123-abc123",
  "pr_number": 123,
  "repository": "org/repo",
  "status": "COMPLETED",
  "result": "APPROVED",
  "path_taken": "FAST_PATH",
  "started_at": "2026-01-28T10:00:03Z",
  "completed_at": "2026-01-28T10:00:43Z",
  "total_duration_ms": 40000,
  "sla_met": true,
  "steps": [
    {
      "step": 1,
      "agent": "code_best_practises_agent",
      "status": "PASS",
      "duration_ms": 25000,
      "sla_met": true,
      "findings_count": 0
    },
    {
      "step": 2,
      "agent": "architect_best_practises_agent",
      "status": "NO_NEW_PATTERN",
      "duration_ms": 8000,
      "sla_met": true,
      "findings_count": 0
    }
  ],
  "merge_decision": {
    "can_merge": true,
    "reason": "All checks passed, no new patterns detected",
    "auto_merged": true,
    "merged_at": "2026-01-28T10:00:41Z"
  },
  "jira_ticket": null
}
```

**GitHub PR Comment**:
```markdown
## PR Orchestrator - Review Complete

### Summary
| Check | Status | Duration |
|-------|--------|----------|
| Code Quality | ✅ PASS | 25s |
| Architecture | ✅ NO NEW PATTERN | 8s |
| LLD Alignment | ⏭️ SKIPPED | - |
| Pattern Matching | ⏭️ SKIPPED | - |
| Peer Review | ⏭️ SKIPPED | - |

### Result: ✅ APPROVED

**Total Duration**: 33 seconds (Fast Path)

This PR has been automatically merged.

---
*Generated by PR Orchestrator Agent v1.0*
```

**CloudWatch Logs**:
```json
{
  "timestamp": "2026-01-28T10:00:43Z",
  "workflow_id": "wf-2026-01-28-pr-123-abc123",
  "pr_number": 123,
  "status": "COMPLETED",
  "path": "FAST_PATH",
  "duration_ms": 40000,
  "sla_met": true,
  "auto_merged": true
}
```

---

### Example 2: Full Path - New Pattern Approved (Success)

**Scenario**: Developer introduces new caching pattern, requires review

**Input**: GitHub PR webhook event
```json
{
  "event": "pull_request",
  "action": "opened",
  "pull_request": {
    "number": 456,
    "title": "Feature: Add Redis caching layer",
    "head": {"ref": "feature/redis-cache", "sha": "def456"},
    "user": {"login": "dev2", "email": "dev2@company.com"}
  }
}
```

**Execution Timeline**:
```
00:00 - PR opened
00:01 - Orchestrator receives webhook
00:02 - Workflow initialized
00:03 - Step 1: Code Best Practises Agent
00:31 - Step 1: PASS (28 sec)
00:32 - Step 2: Architect Best Practises Agent
00:41 - Step 2: NEW_PATTERN_FOUND (9 sec) - Cache Aside Pattern
00:42 - Full Path Required
00:43 - Step 3: LLD Alignment Review Agent
01:00 - Step 3: LLD_COMPLIANT (17 sec)
01:01 - Step 4: Pattern Matching Agent
01:04 - Step 4: Pattern stored in Confluence (3 sec)
01:05 - Step 5: Peer Review Documentation Agent
01:07 - Reviewer assigned (architect1)
01:07 - State: WAITING_REVIEW
...
[2 hours later]
03:07 - Architect submits review: APPROVED
03:08 - Step 5: APPROVED (2h 3min)
03:09 - Merge Decision: can_merge=True
03:10 - Auto-merge executed
03:11 - Success comment posted
03:11 - Workflow COMPLETED (Total: 3h 8min)
```

**Output**:

**Workflow Status Report**:
```json
{
  "workflow_id": "wf-2026-01-28-pr-456-def456",
  "pr_number": 456,
  "status": "COMPLETED",
  "result": "APPROVED",
  "path_taken": "FULL_PATH",
  "total_duration_ms": 11280000,
  "sla_met": true,
  "steps": [
    {"step": 1, "agent": "code_best_practises_agent", "status": "PASS"},
    {"step": 2, "agent": "architect_best_practises_agent", "status": "NEW_PATTERN_FOUND"},
    {"step": 3, "agent": "lld_alignment_review_agent", "status": "LLD_COMPLIANT"},
    {"step": 4, "agent": "pattern_matching_agent", "status": "STORED"},
    {"step": 5, "agent": "peer_review_documentation_agent", "status": "APPROVED"}
  ],
  "merge_decision": {
    "can_merge": true,
    "reason": "All checks passed, pattern approved by architect",
    "auto_merged": true
  }
}
```

---

### Example 3: Blocked - Code Violations (Failure)

**Scenario**: Developer submits PR with naming convention violations

**Input**: GitHub PR webhook event

**Execution Timeline**:
```
00:00 - PR opened
00:01 - Workflow initialized
00:02 - Step 1: Code Best Practises Agent
00:20 - Step 1: FAIL - 3 violations detected (18 sec)
00:21 - Fast Fail: Stop workflow
00:22 - Aggregate errors
00:23 - Step 7: Jira Integration Agent triggered
00:29 - Jira ticket SCM-789 created, assigned to dev3
00:30 - PR merge blocked
00:31 - Failure comment posted
00:31 - State: BLOCKED
00:31 - Workflow BLOCKED (Total: 29 seconds)
```

**Output**:

**Workflow Status Report**:
```json
{
  "workflow_id": "wf-2026-01-28-pr-789-ghi789",
  "pr_number": 789,
  "status": "BLOCKED",
  "result": "BLOCKED",
  "path_taken": "FAST_PATH",
  "total_duration_ms": 29000,
  "sla_met": true,
  "steps": [
    {
      "step": 1,
      "agent": "code_best_practises_agent",
      "status": "FAIL",
      "duration_ms": 18000,
      "findings_count": 3
    },
    {
      "step": 7,
      "agent": "jira_integration_agent",
      "status": "SUCCESS",
      "duration_ms": 6000,
      "ticket_created": "SCM-789"
    }
  ],
  "merge_decision": {
    "can_merge": false,
    "reason": "Code quality violations detected",
    "auto_merged": false
  },
  "jira_ticket": {
    "ticket_id": "SCM-789",
    "ticket_url": "https://jira.company.com/browse/SCM-789",
    "assignee": "dev3"
  }
}
```

**GitHub PR Comment**:
```markdown
## ❌ PR Orchestrator - Review Complete

### Summary
| Check | Status | Duration |
|-------|--------|----------|
| Code Quality | ❌ FAIL | 18s |
| Architecture | ⏭️ NOT RUN | - |

### Result: ❌ BLOCKED

**Violations Found**: 3 code quality violations

#### Violations

1. **src/payment/Processor.java:45** - Naming Convention Violation
   - Found: `process_Payment()`
   - Expected: `processPayment()`
   - Pattern: Java Method Naming (camelCase)

2. **src/payment/Processor.java:78** - Exception Handling Violation
   - Found: `catch (Exception e)`
   - Expected: Specific exception types
   - Pattern: Specific Exception Handling

3. **src/payment/Processor.java:120** - Documentation Violation
   - Missing JavaDoc for public method
   - Pattern: Public Method Documentation

### Next Steps
1. Fix all violations listed above
2. Push changes to this PR
3. Validation will automatically re-run

**Jira Ticket**: [SCM-789](https://jira.company.com/browse/SCM-789) (assigned to @dev3)

---
*Generated by PR Orchestrator Agent v1.0*
```

**Jira Ticket Created**:
```
Project: SCM
Key: SCM-789
Type: Code Violation
Summary: [PR-789] Code Quality Violations - 3 issues detected
Priority: Medium
Assignee: dev3
Labels: [peer-review, code-violation, java, naming-convention]
```

---

## Input/Output Schemas

### Input Schema

```python
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class PRUser:
    login: str
    email: Optional[str] = None

@dataclass
class PRBranch:
    ref: str
    sha: str

@dataclass
class PullRequest:
    number: int
    title: str
    html_url: str
    head: PRBranch
    base: PRBranch
    user: PRUser
    draft: bool
    mergeable: bool
    changed_files: int

@dataclass
class Repository:
    full_name: str
    default_branch: str

@dataclass
class GitHubPREvent:
    event: str  # "pull_request"
    action: str  # "opened", "synchronize", "reopened", "ready_for_review"
    pull_request: PullRequest
    repository: Repository
    sender: PRUser
```

### Output Schema

```python
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from enum import Enum

class WorkflowStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    WAITING_REVIEW = "WAITING_REVIEW"
    CANCELLED = "CANCELLED"

class WorkflowResult(Enum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    WAITING_REVIEW = "WAITING_REVIEW"

class WorkflowPath(Enum):
    FAST_PATH = "FAST_PATH"
    FULL_PATH = "FULL_PATH"

class AgentStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"
    NO_NEW_PATTERN = "NO_NEW_PATTERN"
    NEW_PATTERN_FOUND = "NEW_PATTERN_FOUND"
    LLD_COMPLIANT = "LLD_COMPLIANT"
    LLD_DEVIATION = "LLD_DEVIATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STORED = "STORED"
    SUCCESS = "SUCCESS"

@dataclass
class StepResult:
    step: int
    agent: str
    status: AgentStatus
    duration_ms: int
    sla_met: bool
    findings_count: int = 0
    error_message: Optional[str] = None

@dataclass
class MergeDecision:
    can_merge: bool
    reason: str
    auto_merged: bool
    merged_at: Optional[datetime] = None

@dataclass
class JiraTicket:
    ticket_id: str
    ticket_url: str
    assignee: str
    created_at: datetime

@dataclass
class WorkflowStatusReport:
    workflow_id: str
    pr_number: int
    repository: str
    status: WorkflowStatus
    result: WorkflowResult
    path_taken: WorkflowPath
    started_at: datetime
    completed_at: Optional[datetime]
    total_duration_ms: int
    sla_met: bool
    steps: List[StepResult]
    merge_decision: MergeDecision
    jira_ticket: Optional[JiraTicket] = None
```

### Configuration Schema

```python
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class AgentConfig:
    enabled: bool
    timeout_ms: int
    max_retries: int = 3

@dataclass
class WorkflowConfig:
    fast_path_enabled: bool = True
    auto_merge_enabled: bool = True
    require_approval_count: int = 1
    sla_monitoring_enabled: bool = True
    jira_integration_enabled: bool = True
    skip_labels: List[str] = None
    docs_only_patterns: List[str] = None

@dataclass
class OrchestratorConfig:
    workflow: WorkflowConfig
    agents: Dict[str, AgentConfig]

    @staticmethod
    def default():
        return OrchestratorConfig(
            workflow=WorkflowConfig(),
            agents={
                "code_best_practises": AgentConfig(
                    enabled=True,
                    timeout_ms=30000
                ),
                "architect_best_practises": AgentConfig(
                    enabled=True,
                    timeout_ms=10000
                ),
                "lld_alignment_review": AgentConfig(
                    enabled=True,
                    timeout_ms=20000
                ),
                "pattern_matching": AgentConfig(
                    enabled=True,
                    timeout_ms=5000
                ),
                "peer_review_documentation": AgentConfig(
                    enabled=True,
                    timeout_ms=14400000  # 4 hours
                ),
                "jira_integration": AgentConfig(
                    enabled=True,
                    timeout_ms=10000
                )
            }
        )
```

---

## Workflow State Machine

### State Diagram

```
┌─────────┐
│  IDLE   │
└────┬────┘
     │ PR Event Received
     ▼
┌─────────┐
│ PENDING │◄──────────────────────┐
└────┬────┘                       │
     │ Initialize Workflow        │
     ▼                            │
┌──────────────┐                  │
│ IN_PROGRESS  │                  │
└──────┬───────┘                  │
       │                          │
       ├─ Executing Step 1        │
       ├─ Executing Step 2        │
       │                          │
       ├─[Fast Path]──────────┐   │
       │                      │   │
       ├─[Full Path]          │   │
       ├─ Executing Step 3    │   │
       ├─ Executing Step 4    │   │
       ├─ Executing Step 5    │   │
       │                      │   │
       └──────┬───────────────┘   │
              │                   │
              ▼                   │
       ┌─────────────┐            │
       │   Decision  │            │
       └──────┬──────┘            │
              │                   │
       ┌──────┴──────┬────────────┼──────────┬──────────┐
       ▼             ▼            ▼          ▼          ▼
  ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐
  │COMPLETED │ │ BLOCKED │ │  FAILED  │ │WAITING │ │ CANCELLED │
  │          │ │         │ │          │ │ REVIEW │ │           │
  └──────────┘ └─────────┘ └──────────┘ └────┬───┘ └───────────┘
                                              │
                                              │ Review Submitted
                                              └──────────────────┘
```

### State Transitions

```python
class WorkflowStateMachine:
    def __init__(self):
        self.state = WorkflowStatus.IDLE
        self.transitions = {
            WorkflowStatus.IDLE: [WorkflowStatus.PENDING],
            WorkflowStatus.PENDING: [WorkflowStatus.IN_PROGRESS, WorkflowStatus.CANCELLED],
            WorkflowStatus.IN_PROGRESS: [
                WorkflowStatus.COMPLETED,
                WorkflowStatus.BLOCKED,
                WorkflowStatus.FAILED,
                WorkflowStatus.WAITING_REVIEW,
                WorkflowStatus.CANCELLED
            ],
            WorkflowStatus.WAITING_REVIEW: [
                WorkflowStatus.COMPLETED,
                WorkflowStatus.BLOCKED,
                WorkflowStatus.CANCELLED
            ],
            WorkflowStatus.BLOCKED: [WorkflowStatus.PENDING],  # PR updated
            WorkflowStatus.FAILED: [WorkflowStatus.PENDING],   # Retry
            WorkflowStatus.COMPLETED: [],  # Terminal state
            WorkflowStatus.CANCELLED: []   # Terminal state
        }

    def can_transition(self, from_state: WorkflowStatus, to_state: WorkflowStatus) -> bool:
        return to_state in self.transitions.get(from_state, [])

    def transition(self, to_state: WorkflowStatus):
        if not self.can_transition(self.state, to_state):
            raise InvalidStateTransitionError(
                f"Cannot transition from {self.state} to {to_state}"
            )

        self.state = to_state
```

---

## Merge Decision Algorithm

### Decision Tree

```python
def make_merge_decision(workflow_state: WorkflowState) -> MergeDecision:
    """
    Comprehensive merge decision algorithm.

    Returns:
        MergeDecision with can_merge flag and reason
    """

    # Rule 1: Code quality must pass
    if workflow_state.code_quality.status != AgentStatus.PASS:
        return MergeDecision(
            can_merge=False,
            reason="Code quality violations detected",
            auto_merged=False
        )

    # Rule 2: No agent timeouts
    if has_timeout(workflow_state):
        return MergeDecision(
            can_merge=False,
            reason="Agent timeout - analysis incomplete",
            auto_merged=False
        )

    # Rule 3: No infrastructure errors
    if has_infrastructure_error(workflow_state):
        return MergeDecision(
            can_merge=False,
            reason="Infrastructure error - unable to complete analysis",
            auto_merged=False
        )

    # Rule 4: Check architectural path
    architect_status = workflow_state.architect.status

    if architect_status == AgentStatus.NO_NEW_PATTERN:
        # Fast path: No new patterns detected
        return MergeDecision(
            can_merge=True,
            reason="All checks passed, no new patterns detected",
            auto_merged=True,
            merged_at=datetime.now()
        )

    elif architect_status == AgentStatus.NEW_PATTERN_FOUND:
        # Full path: New pattern requires additional checks

        # Rule 5: LLD compliance required
        if workflow_state.lld_alignment.status != AgentStatus.LLD_COMPLIANT:
            return MergeDecision(
                can_merge=False,
                reason="LLD deviation detected",
                auto_merged=False
            )

        # Rule 6: Pattern must be stored
        if workflow_state.pattern_matching.status != AgentStatus.STORED:
            return MergeDecision(
                can_merge=False,
                reason="Pattern storage failed",
                auto_merged=False
            )

        # Rule 7: Peer review approval required
        if workflow_state.peer_review.status == AgentStatus.WAITING_REVIEW:
            return MergeDecision(
                can_merge=False,
                reason="Awaiting peer review approval",
                auto_merged=False
            )

        elif workflow_state.peer_review.status != AgentStatus.APPROVED:
            return MergeDecision(
                can_merge=False,
                reason="Peer review rejected or failed",
                auto_merged=False
            )

        # All full path checks passed
        return MergeDecision(
            can_merge=True,
            reason="All checks passed, pattern approved",
            auto_merged=True,
            merged_at=datetime.now()
        )

    else:
        # Unexpected status
        return MergeDecision(
            can_merge=False,
            reason=f"Unexpected architect status: {architect_status}",
            auto_merged=False
        )

def has_timeout(workflow_state: WorkflowState) -> bool:
    """Check if any agent timed out."""
    return any(
        step.status == AgentStatus.TIMEOUT
        for step in workflow_state.steps
    )

def has_infrastructure_error(workflow_state: WorkflowState) -> bool:
    """Check if any infrastructure error occurred."""
    return any(
        step.status == AgentStatus.ERROR
        for step in workflow_state.steps
    )
```

### Decision Matrix

| Condition | Fast Path | Full Path | Decision | Auto-Merge |
|-----------|-----------|-----------|----------|------------|
| Code PASS + No New Pattern | ✓ | - | APPROVE | YES |
| Code PASS + New Pattern + LLD Compliant + Review Approved | - | ✓ | APPROVE | YES |
| Code FAIL | ✓/✗ | - | BLOCK | NO |
| Code PASS + LLD Deviation | - | ✗ | BLOCK | NO |
| Code PASS + Review Rejected | - | ✗ | BLOCK | NO |
| Code PASS + Awaiting Review | - | ✗ | WAITING | NO |
| Any Timeout | ✗ | ✗ | BLOCK | NO |
| Any Error | ✗ | ✗ | BLOCK | NO |

---

## Integration Points

### 1. GitHub Integration

**GitHub API Endpoints Used**:
- `POST /repos/{owner}/{repo}/statuses/{sha}` - Post check status
- `POST /repos/{owner}/{repo}/issues/{number}/comments` - Post PR comment
- `PUT /repos/{owner}/{repo}/pulls/{number}/merge` - Auto-merge PR
- `GET /repos/{owner}/{repo}/pulls/{number}/files` - Get changed files
- `GET /repos/{owner}/{repo}/contents/{path}` - Get file contents
- `POST /repos/{owner}/{repo}/issues/{number}/labels` - Update labels

**Authentication**:
- GitHub App installation token
- Stored in AWS Secrets Manager
- Refreshed automatically

**Webhook Configuration**:
```yaml
events:
  - pull_request
    - opened
    - synchronize
    - reopened
    - ready_for_review
  - pull_request_review
    - submitted
```

### 2. Agent Invocation

**Agent API Contract**:
```python
@dataclass
class AgentRequest:
    pr_number: int
    repository: str
    commit_sha: str
    pr_data: dict
    config: dict

@dataclass
class AgentResponse:
    status: AgentStatus
    findings: List[dict]
    execution_time_ms: int
    metadata: dict
```

**Invocation Methods**:
1. HTTP REST API call
2. AWS Lambda invocation
3. Message queue (SQS)

### 3. DynamoDB Integration

**Table Schema**:
```
Table: pr-orchestrator-workflows
Primary Key: workflow_id (String)
Sort Key: pr_number (Number)

Attributes:
- workflow_id: String
- pr_number: Number
- repository: String
- status: String
- path_taken: String
- started_at: String (ISO datetime)
- completed_at: String (ISO datetime)
- steps: List (of step results)
- merge_decision: Map
- jira_ticket: Map (optional)
- config: Map
```

**Access Patterns**:
- Get workflow by ID: `GetItem(workflow_id)`
- List workflows for PR: `Query(pr_number, repository)`
- List in-progress workflows: `GSI on status`

### 4. Jira Integration

**Jira Integration Agent Invocation**:
```python
def trigger_jira_integration(
    issue_type: str,
    pr_data: dict,
    findings: List[dict],
    severity: str,
    source_agent: str
) -> JiraResult:
    """
    Invoke Jira Integration Agent to create ticket.

    Args:
        issue_type: CODE_VIOLATION | LLD_DEVIATION | PATTERN_REJECTION
        pr_data: PR metadata (number, url, author, etc.)
        findings: List of findings from validation
        severity: HIGH | MEDIUM | LOW
        source_agent: Name of agent that detected issue

    Returns:
        JiraResult with ticket_id and ticket_url
    """
    payload = {
        "action": "CREATE_TICKET",
        "issue_type": issue_type,
        "pr_number": pr_data["number"],
        "pr_url": pr_data["html_url"],
        "pr_author": pr_data["user"]["login"],
        "pr_author_email": pr_data["user"]["email"],
        "repository": pr_data["repository"],
        "severity": severity,
        "source_agent": source_agent,
        "findings": findings,
        "workflow_run_url": get_workflow_run_url()
    }

    return invoke_jira_agent(payload)
```

### 5. CloudWatch Integration

**Metrics Published**:
```python
cloudwatch.put_metric_data(
    Namespace="PROrchestrator",
    MetricData=[
        {
            "MetricName": "WorkflowDuration",
            "Value": duration_ms,
            "Unit": "Milliseconds",
            "Dimensions": [
                {"Name": "Repository", "Value": repository},
                {"Name": "Path", "Value": path_taken}
            ]
        },
        {
            "MetricName": "WorkflowSuccess",
            "Value": 1 if success else 0,
            "Unit": "Count"
        },
        {
            "MetricName": "AutoMergeCount",
            "Value": 1 if auto_merged else 0,
            "Unit": "Count"
        }
    ]
)
```

**Logs Structure**:
```json
{
  "timestamp": "2026-01-28T10:00:00Z",
  "level": "INFO",
  "workflow_id": "wf-xxx",
  "pr_number": 123,
  "event": "workflow_completed",
  "duration_ms": 40000,
  "path": "FAST_PATH",
  "result": "APPROVED",
  "auto_merged": true
}
```

---

## Configuration Options

### Environment Variables

```bash
# GitHub Configuration
GITHUB_TOKEN=<secret>
GITHUB_WEBHOOK_SECRET=<secret>

# AWS Configuration
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=pr-orchestrator-workflows

# Workflow Configuration
FAST_PATH_ENABLED=true
AUTO_MERGE_ENABLED=true
SLA_MONITORING_ENABLED=true
JIRA_INTEGRATION_ENABLED=true

# Agent Configuration
CODE_AGENT_TIMEOUT_MS=30000
ARCHITECT_AGENT_TIMEOUT_MS=10000
LLD_AGENT_TIMEOUT_MS=20000
PATTERN_AGENT_TIMEOUT_MS=5000
PEER_REVIEW_AGENT_TIMEOUT_MS=14400000
JIRA_AGENT_TIMEOUT_MS=10000

# Agent Endpoints
CODE_AGENT_URL=https://api.company.com/agents/code
ARCHITECT_AGENT_URL=https://api.company.com/agents/architect
LLD_AGENT_URL=https://api.company.com/agents/lld
PATTERN_AGENT_URL=https://api.company.com/agents/pattern
PEER_REVIEW_AGENT_URL=https://api.company.com/agents/peer-review
JIRA_AGENT_URL=https://api.company.com/agents/jira

# Feature Flags
SKIP_DOCS_ONLY=true
DOCS_PATTERNS=*.md,*.txt,docs/**

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT_SECONDS=60
```

### Configuration File

```yaml
# .github/pr-orchestrator-config.yml

workflow:
  fast_path_enabled: true
  auto_merge_enabled: true
  require_approval_count: 1
  sla_monitoring_enabled: true
  jira_integration_enabled: true

  skip_labels:
    - "skip-orchestrator"
    - "manual-review-only"

  docs_only_patterns:
    - "*.md"
    - "*.txt"
    - "docs/**"
    - "README*"

agents:
  code_best_practises:
    enabled: true
    timeout_ms: 30000
    max_retries: 3

  architect_best_practises:
    enabled: true
    timeout_ms: 10000
    max_retries: 3

  lld_alignment_review:
    enabled: true
    timeout_ms: 20000
    max_retries: 3

  pattern_matching:
    enabled: true
    timeout_ms: 5000
    max_retries: 3

  peer_review_documentation:
    enabled: true
    timeout_ms: 14400000  # 4 hours
    max_retries: 1

  jira_integration:
    enabled: true
    timeout_ms: 10000
    max_retries: 5

sla:
  fast_path_target_ms: 60000  # 1 minute
  full_path_target_ms: 16200000  # 4.5 hours
  warning_threshold: 0.9  # Warn at 90% of SLA

metrics:
  cloudwatch_namespace: "PROrchestrator"
  log_level: "INFO"

retry:
  max_attempts: 3
  initial_delay_ms: 1000
  max_delay_ms: 30000
  backoff_multiplier: 2
  jitter: true
```

---

## Implementation Notes

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Orchestration | AWS Step Functions | Workflow state machine |
| Compute | AWS Lambda | Agent invocation logic |
| State Storage | DynamoDB | Workflow state persistence |
| Message Queue | AWS SQS | Async operations, retry queue |
| Monitoring | CloudWatch | Metrics, logs, alarms |
| Notifications | SNS + Slack | Escalation alerts |
| API Gateway | AWS API Gateway | Webhook endpoint |
| Secrets | AWS Secrets Manager | Credentials storage |

### Architecture

```
GitHub Webhook
    ↓
API Gateway
    ↓
Lambda (Orchestrator)
    ├─→ DynamoDB (State)
    ├─→ Step Functions (Workflow)
    ├─→ Lambda (Agent Invocations)
    ├─→ SQS (Retry Queue)
    ├─→ CloudWatch (Logs/Metrics)
    └─→ SNS (Alerts)
```

### Deployment

**Infrastructure as Code**:
```yaml
# serverless.yml
service: pr-orchestrator-agent

provider:
  name: aws
  runtime: python3.9
  region: us-east-1

functions:
  orchestrator:
    handler: orchestrator.handler
    timeout: 300
    environment:
      DYNAMODB_TABLE: ${self:custom.tableName}
    events:
      - http:
          path: webhook
          method: post

resources:
  Resources:
    WorkflowTable:
      Type: AWS::DynamoDB::Table
      Properties:
        TableName: ${self:custom.tableName}
        AttributeDefinitions:
          - AttributeName: workflow_id
            AttributeType: S
          - AttributeName: pr_number
            AttributeType: N
        KeySchema:
          - AttributeName: workflow_id
            KeyType: HASH
          - AttributeName: pr_number
            KeyType: RANGE
        BillingMode: PAY_PER_REQUEST
```

### Performance Optimization

**Caching Strategy**:
- Cache GitHub file contents (5 min TTL)
- Cache agent configurations (1 hour TTL)
- Cache pattern library (30 min TTL)

**Connection Pooling**:
- Reuse HTTP connections to agents
- Connection pool size: 100
- Keep-alive timeout: 60 seconds

**Parallel Operations**:
- Fetch PR metadata and file contents in parallel
- Post GitHub comment and update DynamoDB in parallel

### Monitoring

**Key Metrics**:
- `workflow.duration` - Track performance
- `workflow.success_rate` - Track reliability
- `workflow.sla_compliance` - Track SLA adherence
- `agent.*.duration` - Track per-agent performance
- `auto_merge.count` - Track automation effectiveness

**Alarms**:
```python
cloudwatch_alarms = [
    {
        "name": "HighWorkflowFailureRate",
        "metric": "workflow.success_rate",
        "threshold": 0.95,  # Alert if < 95%
        "comparison": "LessThanThreshold"
    },
    {
        "name": "SLAViolation",
        "metric": "workflow.sla_compliance",
        "threshold": 0.99,  # Alert if < 99%
        "comparison": "LessThanThreshold"
    }
]
```

---

## Questions and TBCs

| ID | Question/TBC | Priority | Owner | Status |
|----|--------------|----------|-------|--------|
| TBC-ORC-001 | Should failed PRs be auto-closed after timeout? | MEDIUM | Product Owner | OPEN |
| TBC-ORC-002 | Add Slack notifications for failures? | HIGH | DevOps Team | OPEN |
| TBC-ORC-003 | Support for partial re-runs (skip completed steps)? | MEDIUM | Architecture Team | OPEN |
| TBC-ORC-004 | Multi-repo configuration inheritance? | LOW | Development Team | OPEN |
| TBC-ORC-005 | Integration with external CI/CD systems? | LOW | DevOps Team | OPEN |

---

**End of Specification**
