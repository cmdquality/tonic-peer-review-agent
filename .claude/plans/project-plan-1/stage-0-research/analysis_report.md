# PR Orchestrator Agent - Existing Agents Analysis Report

**Date**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**Analysis Phase**: Stage 0 - Research & Analysis
**Worker**: 1

---

## Executive Summary

This report analyzes the 6 existing agents in the tonic-peer-review-agent system to identify integration points for the new PR Orchestrator Agent. All existing agents follow a consistent pattern: they are invoked sequentially in a GitHub Actions workflow triggered by pull requests, each performing specialized validation and tracking functions.

**Key Findings**:
- All agents expose JSON input/output interfaces suitable for orchestration
- Agents operate in a linear workflow with conditional branching based on validation results
- Each agent produces CloudWatch logs and GitHub PR comments for audit trails
- Primary external dependencies are Confluence, GitHub, and Jira APIs
- Total workflow SLA is approximately 75 seconds (sum of individual SLAs)

---

## Section 1: Workflow Architecture Overview

### Overall Workflow Structure

The existing agents are organized in a sequential GitHub Actions workflow:

```
Step 1: Code Best Practises Agent (30 sec SLA)
    ↓
    [If violations] → Jira Integration Agent (10 sec SLA) → Block PR
    [If compliant] ↓
Step 2: Architect Best Practises Agent (10 sec SLA)
    ↓
    [If no new patterns] → Skip to Deployment (Step 6)
    [If new patterns] ↓
Step 3: LLD Alignment Review Agent (20 sec SLA)
    ↓
    [If deviations] → Jira Integration Agent (10 sec SLA) → Require Fix
    [If compliant] ↓
Step 4: Pattern Matching Agent (pattern storage/query)
    ↓
Step 5: Peer Review Documentation Agent (4 hours SLA)
    ↓
    [If approved] → Merge PR ↓
    [If rejected] → Jira Integration Agent (10 sec SLA)
Step 6: GitHub Actions Workflows Hooks (deployment)
```

---

## Section 2: Agent Interface Summary

| Agent | Purpose | SLA | Input Source | Output Target | Criticality |
|-------|---------|-----|--------------|---------------|------------|
| **Code Best Practises** | Standards enforcement | 30 sec | GitHub PR | Architect Agent | CRITICAL |
| **Architect Best Practises** | Pattern novelty | 10 sec | Code Agent | LLD Agent | CRITICAL |
| **LLD Alignment Review** | Design validation | 20 sec | Architect Agent | Pattern Agent | CRITICAL |
| **Jira Integration** | Issue tracking | 10 sec | Multiple agents | Jira + GitHub | HIGH |
| **Pattern Matching** | Knowledge base | 2 sec (query) | Peer Review Agent | Confluence | HIGH |
| **Peer Review Documentation** | Review coordination | 4 hours | LLD Agent | Merge/Jira | CRITICAL |

---

## Section 3: Detailed Agent Specifications

### 1. Code Best Practises Agent

**Input Requirements**:
```json
{
  "event": "pull_request.opened|pull_request.synchronize",
  "pr_number": "integer",
  "repository": "string (org/repo)",
  "commits": ["string (SHA)"],
  "modified_files": ["string (file paths)"],
  "author": "string (github username)"
}
```

**Output Format**:
```json
{
  "status": "PASS|FAIL",
  "violations_count": "integer",
  "violations": [
    {
      "file": "string (file path)",
      "line": "integer",
      "type": "string (violation category)",
      "pattern": "string (violated pattern name)",
      "suggested_fix": "string"
    }
  ],
  "analysis_time_ms": "integer",
  "patterns_checked": "integer"
}
```

**Dependencies**: Confluence (pattern library), GitHub API
**SLA**: 30 seconds (P99)

---

### 2. Architect Best Practises Agent

**Input Requirements**:
```json
{
  "event": "code_best_practises_agent.passed",
  "pr_number": "integer",
  "repository": "string",
  "commits": ["string"],
  "modified_files": ["string"],
  "author": "string"
}
```

**Output Format**:
```json
{
  "status": "NEW_PATTERN_FOUND|NO_NEW_PATTERN",
  "pattern_count": "integer",
  "patterns": [
    {
      "name": "string",
      "type": "design|architectural|idiom",
      "code_example": "string",
      "description": "string",
      "similarity_score": "float (0-1)"
    }
  ],
  "analysis_time_ms": "integer",
  "next_step": "lld_alignment_review|skip_to_deployment"
}
```

**Dependencies**: Confluence (pattern library), GitHub API
**SLA**: 10 seconds (P99)
**Similarity Threshold**: 85%

---

### 3. LLD Alignment Review Agent

**Input Requirements**:
```json
{
  "event": "architect_agent.new_pattern_found",
  "pr_number": "integer",
  "repository": "string",
  "component": "string",
  "new_pattern": {
    "name": "string",
    "type": "string",
    "files": ["string"]
  }
}
```

**Output Format**:
```json
{
  "status": "LLD_COMPLIANT|LLD_DEVIATION_FOUND",
  "deviations": [
    {
      "lld_section": "string",
      "severity": "CRITICAL|MAJOR|MINOR",
      "expected": "string",
      "actual": "string",
      "impact": "string",
      "recommendation": "string"
    }
  ],
  "analysis_time_ms": "integer"
}
```

**Dependencies**: Confluence (LLD documents), GitHub API
**SLA**: 20 seconds (P99)

---

### 4. Jira Integration Agent

**Input Requirements**:
```json
{
  "issue_type": "CODE_VIOLATION|LLD_DEVIATION|PATTERN_REJECTION",
  "pr_number": "integer",
  "repository": "string",
  "pr_url": "string",
  "author": "string",
  "severity": "CRITICAL|MAJOR|MINOR",
  "source_agent": "string",
  "details": "object"
}
```

**Output Format**:
```json
{
  "status": "SUCCESS|FAILURE|QUEUED",
  "ticket_id": "string (SCM-###)",
  "ticket_url": "string",
  "created_at": "ISO8601 timestamp"
}
```

**Dependencies**: Jira API, GitHub API, AWS SQS (retry queue)
**SLA**: 10 seconds (P95)

---

### 5. Pattern Matching Agent

**Input Requirements (STORE_NEW)**:
```json
{
  "action": "STORE_NEW|UPDATE|QUERY|DEPRECATE",
  "pr_number": "integer",
  "pattern": {
    "name": "string",
    "type": "string",
    "category": "string",
    "language": "string",
    "description": "string",
    "code_example": "string",
    "approvers": ["string"],
    "approval_date": "ISO8601"
  }
}
```

**Output Format**:
```json
{
  "status": "SUCCESS|FAILURE",
  "pattern_id": "string (PTN-LANG-###)",
  "confluence_url": "string",
  "version": "1.0",
  "stored_at": "ISO8601 timestamp"
}
```

**Dependencies**: Confluence API, Redis (caching)
**SLA**: 2 seconds for queries (P95)

---

### 6. Peer Review Documentation Agent

**Input Requirements**:
```json
{
  "event": "lld_alignment_review.passed|pull_request_review",
  "pr_number": "integer",
  "repository": "string",
  "pattern": {
    "name": "string",
    "category": "string",
    "language": "string"
  },
  "author": "string",
  "reviewer": "string (if review event)",
  "state": "approved|changes_requested|comment"
}
```

**Output Format**:
```json
{
  "status": "APPROVED|REJECTED|CHANGES_REQUESTED",
  "approval_count": "integer",
  "review_time_hours": "float",
  "sla_met": "boolean"
}
```

**Dependencies**: GitHub API, AWS EventBridge (SLA timers), Email/Slack (notifications)
**SLA**: 4 hours for review, 5 minutes for assignment

---

## Section 4: Integration Points for PR Orchestrator

### 4.1 Standard Agent Interface

All agents follow this consistent pattern:

```
INPUT:
  - GitHub webhook event (trigger)
  - JSON payload with PR metadata
  - External API calls (Confluence, GitHub, Jira)

PROCESSING:
  - Validate inputs
  - Call external APIs
  - Analyze/validate code
  - Generate outputs

OUTPUT:
  - JSON status response
  - GitHub PR comment (user-facing)
  - CloudWatch log entry (audit trail)
  - Conditional invocation of next agent
```

### 4.2 Orchestrator Input/Output Contracts

**Orchestrator Input**:
```json
{
  "event": "pull_request.opened|pull_request.synchronize|pull_request_review",
  "pr_number": "integer",
  "repository": "string",
  "branch": "string",
  "author": "string",
  "modified_files": ["string"],
  "action": "opened|synchronize|submitted"
}
```

**Orchestrator Output**:
```json
{
  "workflow_id": "string (unique ID)",
  "pr_number": "integer",
  "status": "PENDING|IN_PROGRESS|COMPLETED|FAILED|BLOCKED",
  "current_step": "string (agent name)",
  "steps_completed": ["string"],
  "result": "APPROVED|BLOCKED|WAITING_REVIEW",
  "blockers": ["string (if any)"],
  "timestamp": "ISO8601"
}
```

---

## Section 5: Integration Risks and Bottlenecks

### 5.1 Identified Bottlenecks

| Bottleneck | Impact | Mitigation |
|------------|--------|------------|
| Confluence Availability | 4 agents depend on it | Caching (30-60 min TTL) |
| Peer Review SLA | 4-hour human review | Escalation chain |
| GitHub API Rate Limiting | All agents affected | Rate limit detection + queue |
| Jira API Failures | Issues not tracked | SQS queue (24-hour retry) |

### 5.2 Single Points of Failure

| Component | Agents Affected | Mitigation |
|-----------|-----------------|-----------|
| Confluence | 4 agents | Caching (30-60 min) |
| GitHub | All agents | Retry + exponential backoff |
| Jira | 5 agents (indirect) | SQS queue + 24-hour retry |
| CloudWatch | All agents | Non-blocking logging |

---

## Section 6: Recommendations for PR Orchestrator

The PR Orchestrator Agent should:

1. **Workflow Orchestration**
   - Invoke agents sequentially based on workflow definition
   - Handle branching logic (PASS/FAIL paths)
   - Manage conditional execution

2. **State Management**
   - Track PR state through workflow
   - Maintain execution history
   - Recover from partial failures

3. **Error Handling**
   - Retry failed operations
   - Escalate unrecoverable errors
   - Maintain audit trail

4. **SLA Management**
   - Monitor total workflow SLA (target: 4.5 hours including review)
   - Track individual agent SLAs
   - Escalate overdue PRs

5. **Merge Decision Logic**
   - Auto-merge when all checks pass AND approvals received
   - Block merge on any failure
   - Create Jira ticket on failure with auto-assignment to PR author

---

**Total Workflow SLA**: ~4.5 hours (4h review + 70 sec agent analysis)

---

**End of Analysis Report**
