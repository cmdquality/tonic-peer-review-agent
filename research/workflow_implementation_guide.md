# GitHub Actions Workflow Implementation Guide

## Overview

This document provides a comprehensive guide to implementing the PR Peer Review Orchestration workflow for the Tonic Configuration Management Platform.

**File**: `peer_review_workflow.yml`
**Location**: `.github/workflows/peer_review.yml`
**Purpose**: Orchestrate automated and human-driven peer review process for pull requests

---

## Workflow Architecture

### Workflow Diagram

```
┌─────────────────┐
│  PR Created/    │
│  Updated        │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WORKFLOW EXECUTION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │ 1. Pre-Flight│                                               │
│  │   Validation │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ├──[No Code Changes]──> Skip                            │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ 2. Code      │                                               │
│  │   Quality    │──[FAILED]──┐                                  │
│  │   Agent      │             │                                  │
│  └──────┬───────┘             │                                  │
│         │ [PASSED]            │                                  │
│         ▼                     │                                  │
│  ┌──────────────┐             │                                  │
│  │ 3. Architect │             │                                  │
│  │   Agent      │             │                                  │
│  └──────┬───────┘             │                                  │
│         │                     │                                  │
│         ├──[No New Pattern]───┼──> Skip to Deployment           │
│         │                     │                                  │
│         ▼ [New Pattern]       │                                  │
│  ┌──────────────┐             │                                  │
│  │ 4. LLD       │             │                                  │
│  │   Alignment  │──[FAILED]───┤                                  │
│  └──────┬───────┘             │                                  │
│         │ [PASSED]            │                                  │
│         ▼                     ▼                                  │
│  ┌──────────────┐      ┌──────────────┐                         │
│  │ 5. Peer      │      │ 7. Jira      │                         │
│  │   Review     │      │   Integration│                         │
│  │   Agent      │      │   (Failure)  │                         │
│  └──────┬───────┘      └──────┬───────┘                         │
│         │ [Approved]           │                                 │
│         ▼                      │                                 │
│  ┌──────────────┐              │                                 │
│  │ 6. Pattern   │              │                                 │
│  │   Storage    │              │                                 │
│  │ (Post-Merge) │              │                                 │
│  └──────────────┘              │                                 │
│                                │                                 │
│         ┌──────────────────────┘                                 │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ 8. Final     │                                               │
│  │   Report     │                                               │
│  └──────────────┘                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Job Specifications

### Job 1: Pre-Flight Validation

**Purpose**: Validate PR and detect code changes before running expensive validation agents

**Timeout**: 5 minutes

**Key Responsibilities**:
- Validate PR exists and is open
- Detect if PR contains actual code changes (vs docs/config only)
- Post initial status to PR

**Outputs**:
- `has-code-changes`: Boolean indicating if code changes are present
- `changed-files`: Comma-separated list of changed file paths
- `pr-valid`: Boolean indicating if PR is valid

**Error Handling**:
- If PR is not open, fail workflow with clear error message
- If no code changes detected, skip downstream agent jobs

**Implementation Notes**:
- Uses GitHub CLI (`gh`) for PR queries
- Full git history fetched for accurate change detection
- Excludes documentation and configuration files from code change detection

---

### Job 2: Code Quality Agent

**Purpose**: Enforce coding standards and best practices

**Depends On**: `pre-flight` (only if code changes detected)

**Timeout**: 2 minutes (30 second SLA + buffer)

**SLA**: 30 seconds

**Key Responsibilities**:
- Retrieve approved patterns from Confluence
- Analyze all modified code files against patterns
- Detect violations with file/line/type details
- Post detailed violation report to PR
- Block PR merge if violations found

**Outputs**:
- `status`: PASSED | FAILED
- `violations-count`: Number of violations detected
- `violations-report`: JSON report with violation details

**Error Handling**:
- `continue-on-error: true` to allow Jira ticket creation
- If Confluence unavailable, use cached patterns or fail-safe block
- If timeout exceeded, block PR and create CloudWatch alarm

**Implementation Notes**:
- Requires `CONFLUENCE_API_TOKEN` secret
- Can be implemented as AWS Lambda function or containerized service
- Should cache Confluence patterns for performance
- Posts PR comment with violation details immediately

**Integration Points**:
- Confluence API: Query `SCM-PATTERNS` space
- Jira Integration Agent: Trigger if violations found
- GitHub API: Post PR comments

---

### Job 3: Architect Agent

**Purpose**: Detect new coding patterns not in approved pattern library

**Depends On**: `code-quality-agent` (only if PASSED)

**Timeout**: 1 minute (10 second SLA + buffer)

**SLA**: 10 seconds

**Key Responsibilities**:
- Query Confluence for existing patterns
- Extract structural patterns from PR code
- Calculate similarity to existing patterns (85% threshold)
- Determine if new pattern exists
- Add `new-pattern-detected` label to PR if applicable

**Outputs**:
- `status`: NO_NEW_PATTERN | NEW_PATTERN_FOUND
- `new-pattern-detected`: Boolean
- `pattern-data`: JSON with pattern details

**Decision Logic**:
- **If similarity > 85%**: NO_NEW_PATTERN → Skip to deployment
- **If similarity ≤ 85%**: NEW_PATTERN_FOUND → Proceed to LLD Alignment

**Error Handling**:
- If Confluence unavailable, fail-safe to LLD Review (assume new pattern)
- If timeout, route to LLD Review with CloudWatch alarm
- If pattern library empty, block all PRs and alert architecture team

**Implementation Notes**:
- Uses AST (Abstract Syntax Tree) analysis for pattern extraction
- Similarity algorithm: Levenshtein + AST node matching
- Pattern library cached in-memory for performance
- Early exit when high similarity match found (>95%)

**Integration Points**:
- Confluence API: Query `SCM-PATTERNS` space
- GitHub API: Add PR labels

---

### Job 4: LLD Alignment Agent

**Purpose**: Validate new patterns comply with LLD specifications

**Depends On**: `architect-agent` (only if new pattern detected)

**Timeout**: 1 minute (20 second SLA + buffer)

**SLA**: 20 seconds

**Key Responsibilities**:
- Retrieve component LLD from Confluence
- Parse LLD for design constraints, interfaces, contracts
- Map new pattern to LLD specifications
- Detect deviations from LLD
- Generate detailed deviation report with fix guidance

**Outputs**:
- `status`: LLD_COMPLIANT | LLD_DEVIATION_FOUND
- `lld-compliant`: Boolean
- `deviations-count`: Number of deviations detected

**Deviation Severity Classification**:
- **CRITICAL**: Interface contract violation, component boundary breach, security violation
- **MAJOR**: Performance requirement violation, data model inconsistency, disallowed dependency
- **MINOR**: Naming convention deviation, documentation inconsistency

**Error Handling**:
- `continue-on-error: true` to allow Jira ticket creation
- If LLD document missing, block PR and require LLD creation
- If LLD parsing error, route to human architectural review
- If timeout, block PR with CloudWatch alarm

**Implementation Notes**:
- Requires structured LLD format in Confluence for machine parsing
- LLD cache TTL: 60 minutes (LLDs change infrequently)
- Always provides Confluence links to violated LLD sections
- Actionable feedback with specific fix recommendations

**Integration Points**:
- Confluence API: Query `SCM-LLD` space
- Jira Integration Agent: Trigger if deviations found
- GitHub API: Post PR comments with LLD references

---

### Job 5: Peer Review Agent

**Purpose**: Orchestrate human architectural review for new patterns

**Depends On**: `lld-alignment-agent` (only if LLD compliant)

**Timeout**: 5 minutes

**SLA**: 4 hours (for human review, not agent execution)

**Key Responsibilities**:
- Query team configuration for eligible reviewers
- Assign 2-3 reviewers (minimum 1 architect)
- Post review request comment to PR with pattern context
- Send notifications to assigned reviewers
- Start SLA monitoring (4-hour countdown)

**Reviewer Assignment Algorithm**:
1. **Priority 1**: Component owner + architect with category expertise
2. **Priority 2**: Architect with language expertise + senior engineer
3. **Priority 3**: Any available architect + 1 senior engineer
4. **Fallback**: Escalate to architecture team lead if no reviewers available

**Outputs**:
- `status`: REVIEWERS_ASSIGNED
- `reviewers-assigned`: Comma-separated list of assigned reviewers

**Error Handling**:
- If no reviewers available, assign default architecture team lead
- If GitHub API fails, retry with exponential backoff

**Implementation Notes**:
- Uses GitHub PR review assignment API
- Excludes PR author from reviewer pool (conflict of interest)
- Posts comprehensive review request with pattern details, LLD references, SLA
- Can integrate with external notification systems (email, Slack)

**SLA Monitoring** (Future Enhancement):
- At 2 hours (50% SLA): Send gentle reminder to reviewers
- At 3.5 hours (87.5% SLA): Escalate to architecture team lead
- At 4 hours (100% SLA breach): Create CloudWatch alarm, escalate to management

**Integration Points**:
- GitHub API: Assign reviewers, post PR comments
- Team Configuration: Query reviewer roster
- Notification Systems: Email, Slack (optional)

---

### Job 6: Pattern Matching Agent

**Purpose**: Store approved patterns in Confluence pattern library

**Depends On**: PR merge (runs in post-merge workflow)

**Timeout**: 1 minute

**SLA**: 5 seconds

**Key Responsibilities**:
- Generate unique pattern ID (e.g., `PTN-JAVA-042`)
- Create Confluence page in `SCM-PATTERNS` space
- Store pattern metadata in page properties
- Add pattern to searchable index
- Link pattern to LLD and source PR

**Outputs**:
- Pattern ID
- Confluence URL
- Pattern version

**Pattern Metadata**:
- Pattern ID (unique identifier)
- Status (APPROVED)
- Version (1.0 for new patterns)
- Category (design pattern / architectural / idiom)
- Language/framework
- Approvers (architects who approved)
- Approval date
- Source PR number and repository
- LLD reference

**Error Handling**:
- If Confluence unavailable, queue pattern for retry (up to 24 hours)
- If duplicate pattern ID, auto-increment until unique ID found
- If page creation fails, retry with exponential backoff

**Implementation Notes**:
- Disabled in PR workflow (`if: false`) - runs in separate post-merge workflow
- Pattern index cached in Redis for fast queries
- Immutable patterns: once approved, new versions created for changes
- Complete version history maintained in Confluence

**Integration Points**:
- Confluence API: Create pages in `SCM-PATTERNS` space
- Redis: Pattern index cache
- GitHub API: Link to source PR

---

### Job 7: Jira Integration

**Purpose**: Create Jira tickets for code violations, LLD deviations, and pattern rejections

**Depends On**: Any validation failure

**Conditional Execution**: Only if `code-quality-agent` or `lld-alignment-agent` failed

**Timeout**: 2 minutes

**Key Responsibilities**:
- Determine issue type (CODE_VIOLATION | LLD_DEVIATION | PATTERN_REJECTION)
- Map severity to Jira priority (CRITICAL→High, MAJOR→Medium, MINOR→Low)
- Create Jira ticket with complete context
- Link ticket to GitHub PR (bidirectional)
- Post ticket link to PR comment

**Outputs**:
- `jira-ticket-id`: Created ticket ID (e.g., SCM-456)

**Jira Ticket Fields**:
- **Summary**: Auto-generated from issue details
- **Issue Type**: Code Violation / LLD Deviation / Pattern Rejection
- **Priority**: Based on severity mapping
- **Assignee**: PR author or component owner
- **Reporter**: "SCM Automation Agent"
- **Labels**: Auto-tagged (e.g., code-quality, lld-deviation, java)
- **Components**: Repository name
- **Custom Fields**: PR Number, PR URL, Source Agent, Severity

**Error Handling**:
- `continue-on-error: true` to not block final report
- If Jira unavailable, queue ticket creation for retry
- If authentication fails, create critical CloudWatch alarm
- If ticket creation fails, post warning to PR with pending notice

**Implementation Notes**:
- Requires `JIRA_API_TOKEN`, `JIRA_USER_EMAIL` secrets
- Deduplication: Check for existing tickets before creating new
- Rate limiting: Implement token bucket (100 req/min)
- Retry queue: SQS for async processing with exponential backoff

**Integration Points**:
- Jira REST API v3: Create issues
- GitHub API: Post PR comments with ticket links
- AWS SQS: Retry queue for failed ticket creation

---

### Job 8: Final Report

**Purpose**: Aggregate all validation results and post comprehensive summary to PR

**Depends On**: All jobs (always runs)

**Condition**: `if: always()` (runs regardless of job failures)

**Timeout**: 5 minutes

**Key Responsibilities**:
- Aggregate results from all validation jobs
- Determine overall workflow status (PASSED | FAILED | PENDING_REVIEW | IN_PROGRESS)
- Post comprehensive summary table to PR
- Set GitHub status check for branch protection
- Cleanup temporary resources

**Overall Status Logic**:
- **FAILED**: If code quality or LLD alignment failed
- **PENDING_REVIEW**: If peer reviewers assigned (awaiting human review)
- **PASSED**: If no new patterns and all validations passed
- **IN_PROGRESS**: Otherwise

**Error Handling**:
- Always runs, even if upstream jobs failed
- Gracefully handles missing job outputs (defaults to 'SKIPPED')

**Implementation Notes**:
- Uses GitHub PR comments API for summary
- Status check integration for branch protection rules
- Clean, formatted markdown table with emojis for readability

**Integration Points**:
- GitHub API: Post PR comments, set status checks
- All upstream jobs: Aggregate outputs

---

## Environment Variables

### Required Secrets

These secrets must be configured in GitHub repository settings:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `CONFLUENCE_API_TOKEN` | Confluence API token for pattern/LLD queries | `eyJ...` |
| `CONFLUENCE_BASE_URL` | Confluence instance URL | `https://confluence.tonic.com` |
| `JIRA_API_TOKEN` | Jira API token for ticket creation | `ATATT...` |
| `JIRA_USER_EMAIL` | Jira user email for API authentication | `automation@tonic.com` |
| `JIRA_BASE_URL` | Jira instance URL | `https://tonic.atlassian.net` |
| `JIRA_DEFAULT_ASSIGNEE` | Default assignee for Jira tickets | `architecture-team-lead@tonic.com` |
| `AWS_ACCESS_KEY_ID` | AWS credentials for Lambda/ECS agents | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `wJalr...` |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CODE_AGENT_SLA` | 30 | Code quality agent SLA in seconds |
| `ARCHITECT_AGENT_SLA` | 10 | Architect agent SLA in seconds |
| `LLD_AGENT_SLA` | 20 | LLD alignment agent SLA in seconds |
| `PEER_REVIEW_SLA` | 14400 | Peer review SLA in seconds (4 hours) |
| `CONFLUENCE_SPACE_PATTERNS` | `SCM-PATTERNS` | Confluence space for patterns |
| `CONFLUENCE_SPACE_LLD` | `SCM-LLD` | Confluence space for LLDs |
| `JIRA_PROJECT` | `SCM` | Jira project key |
| `AWS_REGION` | `us-east-1` | AWS region for Lambda/ECS |

---

## Workflow Triggers

### Pull Request Events

The workflow triggers on these PR events:
- `opened`: New PR created
- `synchronize`: New commits pushed to PR
- `reopened`: Previously closed PR reopened

**Branches**: `main`, `develop`, `release/**`

### Merge Group Events

For repositories using GitHub merge queues:
- `merge_group.checks_requested`

### Manual Dispatch

For testing and debugging:
```yaml
workflow_dispatch:
  inputs:
    pr_number:
      description: 'PR number to review'
      required: true
      type: number
```

Usage:
```bash
gh workflow run peer_review.yml -f pr_number=123
```

---

## Concurrency Control

```yaml
concurrency:
  group: pr-review-${{ github.event.pull_request.number || github.run_id }}
  cancel-in-progress: true
```

**Purpose**: Prevent duplicate workflow runs for the same PR

**Behavior**:
- Only one workflow run per PR at a time
- If new commits pushed while workflow running, cancel in-progress run and start new one
- Reduces unnecessary compute and ensures latest code is always validated

---

## Workflow Permissions

The workflow requires these GitHub permissions:

| Permission | Level | Purpose |
|------------|-------|---------|
| `contents` | read | Read repository contents |
| `pull-requests` | write | Comment on PRs, add labels, assign reviewers |
| `issues` | write | Create issues if needed |
| `statuses` | write | Set commit statuses |
| `checks` | write | Create check runs |

Configure in workflow file:
```yaml
permissions:
  contents: read
  pull-requests: write
  issues: write
  statuses: write
  checks: write
```

---

## Implementation Steps

### Step 1: Create Workflow File

1. Create directory: `.github/workflows/`
2. Copy `peer_review_workflow.yml` to `.github/workflows/peer_review.yml`

### Step 2: Configure Secrets

1. Navigate to GitHub repository → Settings → Secrets and variables → Actions
2. Add all required secrets (see Environment Variables section)
3. Validate secrets are accessible to workflows

### Step 3: Configure Agents

Each agent (Code Quality, Architect, LLD Alignment, Pattern Matching, Peer Review, Jira Integration) must be deployed and accessible:

**Option 1: AWS Lambda**
- Deploy each agent as separate Lambda function
- Configure API Gateway endpoints
- Update workflow to call Lambda functions via AWS CLI or SDK

**Option 2: Containerized Services (ECS/EKS)**
- Deploy each agent as containerized service
- Expose HTTP endpoints
- Update workflow to call endpoints via `curl` or HTTP clients

**Option 3: GitHub Actions Custom Actions**
- Package each agent as GitHub Action
- Reference in workflow as `uses: ./.github/actions/code-quality-agent`

### Step 4: Update Placeholder Code

Replace TODO placeholders in workflow with actual agent invocations:

**Example for Code Quality Agent**:
```yaml
- name: Run Code Best Practices Agent
  run: |
    # Call Lambda function
    aws lambda invoke \
      --function-name code-best-practices-agent \
      --payload "{\"pr_number\": $PR_NUMBER, \"repository\": \"$REPOSITORY\"}" \
      --region $AWS_REGION \
      response.json

    # Parse response
    STATUS=$(jq -r '.status' response.json)
    VIOLATIONS_COUNT=$(jq -r '.violations_count' response.json)

    echo "status=$STATUS" >> $GITHUB_OUTPUT
    echo "violations-count=$VIOLATIONS_COUNT" >> $GITHUB_OUTPUT
```

### Step 5: Test Workflow

1. Create test PR with code changes
2. Observe workflow execution in Actions tab
3. Verify all jobs execute in correct order
4. Validate PR comments are posted correctly
5. Test failure scenarios (code violations, LLD deviations)

### Step 6: Configure Branch Protection

1. Navigate to GitHub repository → Settings → Branches
2. Add branch protection rule for `main`
3. Enable "Require status checks to pass before merging"
4. Select "PR Peer Review Orchestration" check
5. Enable "Require branches to be up to date before merging"

### Step 7: Monitor and Iterate

1. Monitor CloudWatch logs for agent performance
2. Track SLA compliance metrics
3. Collect developer feedback on review experience
4. Iterate on reviewer assignment algorithm
5. Tune similarity thresholds and validation rules

---

## Testing Strategy

### Unit Tests (Per Agent)

Each agent should have comprehensive unit tests:
- Code Quality Agent: Pattern matching accuracy
- Architect Agent: Similarity calculation accuracy
- LLD Alignment Agent: Deviation detection accuracy
- Pattern Matching Agent: Storage and retrieval correctness
- Peer Review Agent: Reviewer assignment logic
- Jira Integration Agent: Ticket creation and linking

### Integration Tests

Test workflow end-to-end:
1. **Happy Path**: PR with no violations, no new patterns → Auto-pass
2. **Code Violations**: PR with violations → Jira ticket created, PR blocked
3. **New Pattern (LLD Compliant)**: PR with new pattern → Peer review assigned
4. **LLD Deviation**: PR with LLD violation → Jira ticket, PR blocked
5. **Peer Review Approval**: Approved PR → Pattern stored, PR merged
6. **Peer Review Rejection**: Rejected PR → Jira ticket, PR closed

### Performance Tests

Validate SLA compliance:
- Code Quality Agent: < 30 seconds
- Architect Agent: < 10 seconds
- LLD Alignment Agent: < 20 seconds
- Pattern Matching Agent: < 5 seconds
- End-to-end workflow: < 2 minutes (excluding human review)

### Failure Scenario Tests

Test error handling:
- Confluence API unavailable
- Jira API unavailable
- Agent timeout
- Invalid PR data
- Missing LLD document
- No reviewers available

---

## Monitoring and Observability

### CloudWatch Metrics

Track these metrics for each agent:
- **Execution Time**: P50, P95, P99 latencies
- **Success Rate**: Percentage of successful executions
- **Error Rate**: Percentage of failed executions
- **SLA Compliance**: Percentage of executions within SLA

### CloudWatch Alarms

Configure alarms for:
- Agent timeout (execution time > SLA)
- High error rate (> 5% failures)
- Confluence/Jira API unavailability
- Pattern library corruption or unavailability

### Logs

Each agent should log:
- Input payload (PR number, repository, etc.)
- Processing steps (pattern retrieval, analysis, validation)
- Output results (status, violations, patterns detected)
- Execution time and performance metrics

### Dashboards

Create CloudWatch dashboard with:
- Agent execution time trends
- Success/failure rates
- SLA compliance trends
- Jira ticket creation rate
- Peer review approval/rejection rate

---

## Troubleshooting Guide

### Workflow Not Triggering

**Symptoms**: PR created but workflow doesn't run

**Possible Causes**:
- Workflow file syntax error
- Workflow not on default branch
- PR branch not in trigger list (`main`, `develop`, `release/**`)

**Solutions**:
- Validate YAML syntax: `yamllint .github/workflows/peer_review.yml`
- Ensure workflow file committed to default branch
- Check workflow trigger configuration matches PR branch

### Agent Timeout

**Symptoms**: Job exceeds timeout and fails

**Possible Causes**:
- Agent processing too slow
- Confluence/Jira API slow response
- Large PR with many files

**Solutions**:
- Increase job timeout in workflow
- Optimize agent code for performance
- Implement caching for Confluence patterns
- Parallelize file processing in agents

### Jira Ticket Creation Failed

**Symptoms**: Workflow completes but no Jira ticket created

**Possible Causes**:
- Invalid Jira API token
- Jira API unavailable
- Invalid Jira project or issue type configuration

**Solutions**:
- Validate `JIRA_API_TOKEN` secret is correct
- Test Jira API connectivity: `curl -H "Authorization: Bearer $TOKEN" $JIRA_BASE_URL/rest/api/3/myself`
- Verify Jira project exists and issue types configured
- Check retry queue for pending tickets

### PR Comment Not Posted

**Symptoms**: Workflow runs but no PR comment appears

**Possible Causes**:
- GitHub token lacks `pull-requests: write` permission
- PR comment API call failed
- Network connectivity issue

**Solutions**:
- Verify workflow `permissions` includes `pull-requests: write`
- Check workflow logs for GitHub API errors
- Retry PR comment posting manually: `gh pr comment $PR_NUMBER --body "..."`

### Reviewer Assignment Failed

**Symptoms**: Peer Review Agent runs but reviewers not assigned

**Possible Causes**:
- Invalid reviewer usernames
- Reviewers not in repository collaborators
- GitHub API rate limiting

**Solutions**:
- Verify reviewer usernames exist in GitHub organization
- Ensure reviewers have repository access
- Implement rate limiting and retry logic
- Use GitHub API pagination for large reviewer lists

---

## Performance Optimization

### Caching Strategies

1. **Confluence Pattern Cache**:
   - Cache patterns in-memory or Redis
   - TTL: 30 minutes
   - Invalidate on pattern updates

2. **LLD Document Cache**:
   - Cache LLD documents in-memory
   - TTL: 60 minutes
   - Invalidate on Confluence page updates

3. **GitHub Actions Cache**:
   - Cache agent dependencies (npm packages, pip packages)
   - Use `actions/cache` for build artifacts

### Parallelization

1. **File Processing**:
   - Analyze multiple files concurrently in Code Quality Agent
   - Use worker threads or parallel processes

2. **Pattern Similarity Calculation**:
   - Calculate similarity to multiple patterns in parallel
   - Early exit when high similarity match found

3. **Confluence Queries**:
   - Batch API requests when possible
   - Use Confluence CQL for optimized queries

### Network Optimization

1. **API Request Batching**:
   - Batch Confluence/Jira API requests
   - Reduce network round trips

2. **Connection Pooling**:
   - Reuse HTTP connections for API calls
   - Configure keep-alive settings

3. **Async Processing**:
   - Use async/await for I/O-bound operations
   - Non-blocking API calls

---

## Security Considerations

### Secrets Management

1. **Never commit secrets to repository**:
   - Use GitHub Secrets for all credentials
   - Rotate secrets regularly (quarterly)

2. **Least Privilege**:
   - Grant minimum required permissions to API tokens
   - Use separate tokens for each service (Confluence, Jira)

3. **Secrets Rotation**:
   - Implement automated secrets rotation
   - Update workflow secrets without downtime

### Code Injection Prevention

1. **Input Validation**:
   - Validate all PR inputs (numbers, strings, etc.)
   - Sanitize file paths and user inputs

2. **Command Injection**:
   - Avoid `eval` or dynamic command execution
   - Use parameterized API calls

3. **Script Injection in PR Comments**:
   - Escape markdown in PR comments
   - Sanitize user-provided content

### Audit Trail

1. **CloudWatch Logs**:
   - Log all agent executions with inputs/outputs
   - Retain logs for 90 days minimum

2. **GitHub Audit Log**:
   - Monitor workflow executions
   - Track PR comment posting and label changes

3. **Jira Audit Log**:
   - Track ticket creation and updates
   - Link tickets to source workflows

---

## Future Enhancements

### Short Term (1-3 months)

1. **SLA Monitoring Automation**:
   - Implement scheduled workflow to check peer review SLA
   - Send automated reminders to reviewers at 50% and 87.5% SLA

2. **Pattern Usage Tracking**:
   - Track pattern usage across codebase
   - Generate pattern popularity reports

3. **Reviewer Performance Metrics**:
   - Track review time per reviewer
   - Identify reviewer bottlenecks

### Medium Term (3-6 months)

1. **AI-Powered Pattern Suggestions**:
   - Suggest pattern improvements based on usage
   - Identify pattern anti-patterns

2. **Automated Pattern Deprecation**:
   - Detect unused patterns
   - Suggest pattern consolidation

3. **Multi-Repository Support**:
   - Share patterns across multiple repositories
   - Centralized pattern governance

### Long Term (6-12 months)

1. **Machine Learning for Pattern Detection**:
   - Train ML models for pattern similarity
   - Improve detection accuracy over time

2. **Automated Refactoring Suggestions**:
   - Suggest code refactoring to use approved patterns
   - Auto-generate PRs with pattern improvements

3. **Cross-Language Pattern Support**:
   - Support patterns across multiple languages
   - Language-agnostic pattern library

---

## Appendix

### A. Workflow YAML Complete Reference

See `peer_review_workflow.yml` for complete workflow definition.

### B. Agent API Specifications

Each agent exposes a REST API or Lambda function interface:

**Code Quality Agent**:
```json
{
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "modified_files": ["src/main/java/OrderService.java"]
}
```

**Architect Agent**:
```json
{
  "pr_number": 456,
  "repository": "tonic-scm/payment-service",
  "code_files": [...]
}
```

**LLD Alignment Agent**:
```json
{
  "pr_number": 789,
  "repository": "tonic-scm/order-service",
  "pattern_data": {...}
}
```

### C. Confluence Page Templates

**Pattern Page Template**:
```markdown
# PTN-{LANGUAGE}-{ID}: {Pattern Name}

**Status**: APPROVED
**Version**: 1.0
**Category**: {Category}
**Language**: {Language}
**Approved By**: {Approvers}
**Approval Date**: {Date}
**Source PR**: [{Repo}#{PR}]({URL})
**LLD Reference**: [{LLD}]({URL})

## Description
{Description}

## Use Cases
- {Use case 1}
- {Use case 2}

## Code Example
```{language}
{Code}
```

## Design Constraints (per LLD)
- ✅ {Constraint 1}
- ✅ {Constraint 2}

## Related Patterns
- [PTN-XXX-YYY: {Name}]({URL})

## Version History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | {Date} | {Author} | Initial approval |
```

### D. Jira Ticket Templates

**Code Violation Ticket**:
```
Summary: Code violations in PR #{PR_NUMBER} ({Repository})

Description:
## Code Violations Detected

Automated code analysis detected {COUNT} violations in pull request #{PR_NUMBER}.

**PR**: {PR_URL}
**Repository**: {Repository}
**Author**: {Author}
**Detection Agent**: Code Best Practises Agent

---

### Violations

{Violation details}

---

**Action Required**: Fix all violations before PR can be merged.
```

### E. GitHub Actions Status Check Names

- `Pre-Flight Validation`
- `Code Best Practices Agent`
- `Architect Best Practices Agent`
- `LLD Alignment Review Agent`
- `Peer Review Documentation Agent`
- `PR Peer Review Orchestration`

---

## Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-28 | Claude | Initial workflow design and implementation guide |

---

**End of Implementation Guide**
