# GitHub Actions Research: PR-Triggered Agent Orchestration Workflow

**Date**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**Analysis Phase**: Stage 0 - Research & Analysis
**Worker**: 2

---

## Executive Summary

This research document provides comprehensive guidance for implementing a GitHub Actions workflow that orchestrates multiple agents triggered by Pull Requests. The findings cover security best practices, status checks, job orchestration, error handling, secrets management, and performance optimization.

---

## 1. GitHub Actions PR Triggers - Best Practices

### Recommended PR Trigger Configuration

```yaml
name: Agent Orchestration Workflow

on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches:
      - main
      - develop
    paths-ignore:
      - '**.md'
      - 'docs/**'
  merge_group:  # Required for merge queues

permissions:
  contents: read
  pull-requests: write
  issues: write
  checks: write
```

### Key Points:
- **Default trigger types**: `opened`, `synchronize`, `reopened`
- **Use `types` keyword** to trigger on specific activity types
- **Always include `merge_group`** if using GitHub's merge queue feature
- **Set explicit permissions** following least-privilege principle
- **Use `branches` filter** to target specific base branches
- **Use `paths-ignore`** to skip docs-only changes

### Important Limitations

1. **Merge Conflict Behavior**: Workflows will not run on `pull_request` if the PR has a merge conflict
2. **GITHUB_TOKEN Recursion Prevention**: Events triggered by `GITHUB_TOKEN` won't create new workflow runs
3. **Branch Filtering**: Workflows triggered by PRs always reference the PR branch, not the base branch

---

## 2. Status Checks - Implementation for Merge Blocking

### Setting Up Required Status Checks

#### Step 1: Configure Branch Protection
1. Repository Settings → Branches
2. Branch protection rules → Add rule
3. Specify branch pattern (e.g., `main`)
4. Enable "Require status checks to pass before merging"
5. Select required checks from the list

#### Step 2: Define Workflow Jobs

```yaml
jobs:
  code-quality-review:
    name: Code Quality Review Agent
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run code quality analysis
        run: |
          # Agent execution logic

  architecture-review:
    name: Architecture Review Agent
    runs-on: ubuntu-latest
    needs: code-quality-review
    steps:
      - uses: actions/checkout@v4
      - name: Run architecture analysis
        run: |
          # Agent execution logic
```

### Critical Requirements

1. **Unique Job Names**: Each job must have a unique name across all workflows
2. **Seven-Day Rule**: Status checks must have completed successfully within the past 7 days
3. **Latest Commit Validation**: All required checks must pass against the latest commit SHA

---

## 3. Branch Protection Configuration

### GitHub CLI Configuration

```bash
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["Code Quality Review Agent","Architecture Review Agent","Security Review Agent"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions=null
```

### Key Configuration Options

1. **Require status checks to pass before merging** - Enforces that specific checks must succeed
2. **Require pull request reviews** - Enforces human review before merge
3. **Restrict who can push** - Limits who can push to the branch
4. **Enable merge queue** - Serializes merges to prevent conflicts

---

## 4. Job Orchestration - Sequential and Conditional Execution

### Sequential Job Execution with `needs`

```yaml
jobs:
  # Phase 1: Initial validation
  validation:
    name: PR Validation
    runs-on: ubuntu-latest
    outputs:
      has_code_changes: ${{ steps.filter.outputs.has_code_changes }}
    steps:
      - uses: actions/checkout@v4
      - name: Detect changes
        id: filter
        run: |
          echo "has_code_changes=true" >> $GITHUB_OUTPUT

  # Phase 2: Parallel agent execution (after validation)
  code-quality:
    name: Code Quality Agent
    needs: validation
    if: needs.validation.outputs.has_code_changes == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Run code quality checks
        run: echo "Code quality analysis"

  security:
    name: Security Agent
    needs: validation
    if: needs.validation.outputs.has_code_changes == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Run security checks
        run: echo "Security analysis"

  # Phase 3: Architecture review (after code quality)
  architecture:
    needs: [validation, code-quality]
    if: |
      always() &&
      needs.validation.outputs.has_code_changes == 'true' &&
      needs.code-quality.result == 'success'
    runs-on: ubuntu-latest
    steps:
      - name: Run architecture checks
        run: echo "Architecture analysis"

  # Phase 4: Final aggregation
  aggregate-results:
    name: Aggregate Results
    needs: [code-quality, security, architecture]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Collect and report results
        run: |
          echo "Aggregating results from all agents"
```

### Key Orchestration Patterns

| Pattern | Usage |
|---------|-------|
| `needs: [job1, job2]` | Waits for both job1 AND job2 |
| `if: always()` | Runs regardless of previous outcome |
| `if: failure()` | Only runs if previous fails |
| `if: success()` | Only runs if all previous succeed |

---

## 5. Error Handling and Failure Reporting

### Step-Level Error Handling

```yaml
- name: Primary task
  id: primary
  continue-on-error: true
  run: ./main-script.sh

- name: Fallback task
  if: failure() && steps.primary.outcome == 'failure'
  run: ./fallback-script.sh

- name: Cleanup (always runs)
  if: always()
  run: ./cleanup.sh
```

### Reporting Failures on Pull Requests

```yaml
- name: Comment failure on PR
  if: failure() && github.event.pull_request
  uses: actions/github-script@v7
  with:
    script: |
      const body = `## ❌ Agent Execution Failed

      **Job**: ${{ github.job }}
      **Run**: [View logs](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }})

      Please review the errors and push fixes.`;

      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: body
      });
```

---

## 6. Secrets Management - Jira/Confluence API Credentials

### Core Principles

1. **Never hardcode secrets** in code or workflow files
2. **Use GitHub's encrypted secrets** for storing sensitive data
3. **Apply least privilege** - grant minimum necessary permissions
4. **Rotate secrets regularly** (every 30-90 days)
5. **Use OIDC instead of long-lived tokens** when possible

### Using Secrets in Workflows

```yaml
jobs:
  jira-integration:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Update Jira ticket
        env:
          JIRA_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          JIRA_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_USER_EMAIL }}
        run: |
          curl -X POST "${JIRA_URL}/rest/api/3/issue" \
            -H "Content-Type: application/json" \
            -u "${JIRA_EMAIL}:${JIRA_TOKEN}" \
            -d '{"fields": {"project": {"key": "SCM"}}}'
```

---

## 7. Performance Optimization

### Caching Strategies

```yaml
- name: Cache dependencies
  uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

### Concurrency Control

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true  # Cancel old runs when new commits pushed
```

### Parallel Execution with Matrix Strategy

```yaml
jobs:
  test-matrix:
    strategy:
      matrix:
        agent: [code-quality, security, pattern-matching]
      fail-fast: false  # Continue other jobs if one fails
      max-parallel: 3
    runs-on: ubuntu-latest
    steps:
      - name: Run agent
        run: echo "Running ${{ matrix.agent }}"
```

---

## 8. Complete Example Workflow

```yaml
name: Multi-Agent PR Review Orchestration

on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main]
  merge_group:
    types: [checks_requested]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: write
  checks: write

jobs:
  # Phase 1: Pre-flight validation
  pre-flight:
    name: Pre-flight Validation
    runs-on: ubuntu-latest
    timeout-minutes: 10
    outputs:
      should_run_full_suite: ${{ steps.decision.outputs.full_suite }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: dorny/paths-filter@v2
        id: filter
        with:
          filters: |
            code:
              - 'src/**'
              - 'lib/**'
      - id: decision
        run: |
          if [[ "${{ steps.filter.outputs.code }}" == "true" ]]; then
            echo "full_suite=true" >> $GITHUB_OUTPUT
          else
            echo "full_suite=false" >> $GITHUB_OUTPUT
          fi

  # Phase 2: Parallel agent execution
  code-quality-agent:
    name: Code Quality Review Agent
    needs: pre-flight
    if: needs.pre-flight.outputs.should_run_full_suite == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - name: Run code quality agent
        id: quality-check
        continue-on-error: true
        run: |
          echo "Executing code quality agent..."
          # Call your agent script/API

  pattern-matching-agent:
    name: Pattern Matching Agent
    needs: pre-flight
    if: needs.pre-flight.outputs.should_run_full_suite == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - name: Run pattern matching agent
        run: echo "Executing pattern matching agent..."

  security-agent:
    name: Security Review Agent
    needs: pre-flight
    if: needs.pre-flight.outputs.should_run_full_suite == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - name: Run security agent
        run: echo "Executing security agent..."

  # Phase 3: Architecture review (depends on code quality)
  architecture-agent:
    name: Architecture Review Agent
    needs: [pre-flight, code-quality-agent]
    if: |
      always() &&
      needs.pre-flight.outputs.should_run_full_suite == 'true' &&
      needs.code-quality-agent.result == 'success'
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - name: Run architecture agent
        run: echo "Executing architecture agent..."

  # Phase 4: Jira integration
  jira-integration:
    name: Update Jira Ticket
    needs: [code-quality-agent, pattern-matching-agent, security-agent, architecture-agent]
    if: always()
    runs-on: ubuntu-latest
    environment: production
    timeout-minutes: 5
    steps:
      - name: Extract Jira issue
        id: jira
        run: |
          pr_title="${{ github.event.pull_request.title }}"
          issue_key=$(echo "$pr_title" | grep -oE '[A-Z]+-[0-9]+' || echo "")
          echo "issue_key=$issue_key" >> $GITHUB_OUTPUT

      - name: Create/Update Jira ticket on failure
        if: |
          steps.jira.outputs.issue_key != '' &&
          (needs.code-quality-agent.result == 'failure' ||
           needs.pattern-matching-agent.result == 'failure' ||
           needs.security-agent.result == 'failure' ||
           needs.architecture-agent.result == 'failure')
        env:
          JIRA_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          JIRA_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_USER_EMAIL }}
        run: |
          echo "Creating Jira ticket for failure..."

  # Phase 5: Final reporting
  final-report:
    name: Generate Final Report
    needs: [code-quality-agent, pattern-matching-agent, security-agent, architecture-agent]
    if: always()
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Generate summary
        run: |
          echo "## Agent Review Summary" >> $GITHUB_STEP_SUMMARY
          echo "| Agent | Status |" >> $GITHUB_STEP_SUMMARY
          echo "|-------|--------|" >> $GITHUB_STEP_SUMMARY
          echo "| Code Quality | ${{ needs.code-quality-agent.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Pattern Matching | ${{ needs.pattern-matching-agent.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Security | ${{ needs.security-agent.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Architecture | ${{ needs.architecture-agent.result }} |" >> $GITHUB_STEP_SUMMARY

      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const results = {
              'Code Quality': '${{ needs.code-quality-agent.result }}',
              'Pattern Matching': '${{ needs.pattern-matching-agent.result }}',
              'Security': '${{ needs.security-agent.result }}',
              'Architecture': '${{ needs.architecture-agent.result }}'
            };

            const getEmoji = (status) => {
              switch(status) {
                case 'success': return '✅';
                case 'failure': return '❌';
                case 'skipped': return '⏭️';
                default: return '❓';
              }
            };

            const allPassed = Object.values(results).every(r => r === 'success' || r === 'skipped');

            const body = `## 🤖 Multi-Agent Review Complete

            | Agent | Result |
            |-------|--------|
            ${Object.entries(results).map(([agent, result]) =>
              `| ${agent} | ${getEmoji(result)} ${result} |`
            ).join('\n')}

            ${allPassed ? '### ✅ All checks passed - Ready for merge' : '### ❌ Some checks failed - Please fix before merging'}

            [View workflow run](${context.payload.repository.html_url}/actions/runs/${context.runId})`;

            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });

      - name: Set final status
        run: |
          all_results="${{ needs.code-quality-agent.result }} ${{ needs.pattern-matching-agent.result }} ${{ needs.security-agent.result }} ${{ needs.architecture-agent.result }}"

          if echo "$all_results" | grep -q "failure"; then
            echo "::error::One or more agents failed"
            exit 1
          fi

          echo "All agents completed successfully"
```

---

## 9. Key Recommendations

### For PR Orchestrator Implementation:

1. **Use `pull_request` event** with `opened`, `synchronize`, `reopened` types
2. **Set explicit permissions** at workflow level
3. **Implement pre-flight validation** to skip unnecessary runs
4. **Use `needs` for sequential execution** with conditional `if` statements
5. **Always use `if: always()`** for cleanup and reporting jobs
6. **Store secrets in GitHub Secrets** with environment scoping
7. **Implement comprehensive error handling** with PR comments
8. **Use concurrency control** to cancel outdated runs
9. **Set job timeouts** to prevent runaway executions
10. **Post final status comment** with pass/fail summary

---

**End of Research Document**
