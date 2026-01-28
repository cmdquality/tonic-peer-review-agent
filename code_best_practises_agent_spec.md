# Agent Specification: Code Best Practises Agent

**Created**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**LLD Reference**: lld_1_config_management_platform.md

---

## Question 1: Agent Identity and Purpose

**What is this agent and what problem does it solve?**

The Code Best Practises Agent is an AI-powered code analysis agent that enforces coding standards and best practices in the SCM system. This agent solves the problem of inconsistent code quality across the codebase by automatically validating all pull request code against approved patterns stored in Confluence.

**Problem Solved**: Without automated enforcement, code quality depends on manual reviews which are inconsistent, time-consuming, and prone to human error. This agent ensures 100% compliance with predefined coding standards, making code maintainable by any team member regardless of who originally wrote it.

**Value Provided**:
- Enforces mandatory coding standards (non-optional blocks on PR merge)
- Reduces manual code review time for standards compliance
- Ensures team-wide code maintainability
- Provides immediate feedback to developers on violations

---

## Question 2: Core Capabilities

**What are the agent's main capabilities?**

1. **Pattern Retrieval**: Query Confluence API to retrieve approved coding patterns and standards
2. **Code Analysis**: Analyze PR code commits against retrieved patterns
3. **Standards Validation**: Validate compliance with coding standards (naming conventions, structure, design patterns)
4. **Violation Detection**: Identify specific code violations with line numbers and descriptions
5. **Violation Reporting**: Generate detailed violation reports for developers
6. **PR Blocking**: Block PR merge when violations are detected
7. **Jira Integration**: Trigger Jira Integration Agent to create tickets for violations
8. **Performance Monitoring**: Execute analysis within 30-second SLA

---

## Question 3: Input Requirements

**What inputs does the agent need?**

**Primary Inputs**:
- **Pull Request Data**: PR number, commit SHA, modified files list
- **Code Files**: Source code files from PR commits
- **GitHub Context**: Repository name, branch name, author information

**External Data Sources**:
- **Confluence Pattern Library**: Approved coding patterns (via Confluence API)
- **GitHub API**: PR metadata and file contents

**Format**: JSON payload from GitHub Actions webhook containing PR event data

**Preconditions**:
- GitHub Actions workflow triggered on PR creation or update
- Confluence API credentials available in GitHub Secrets
- Pattern library must be accessible and populated
- PR must contain code changes (not just documentation)

---

## Question 4: Output Specifications

**What does the agent produce?**

**Primary Outputs**:
- **Compliance Status**: PASS/FAIL result for PR
- **Violation Report**: Detailed list of violations if FAIL
  - File path
  - Line number
  - Violation type
  - Pattern violated
  - Suggested fix
- **GitHub PR Comment**: Formatted comment posted to PR with results
- **Jira Ticket Trigger**: Signal to Jira Integration Agent if violations found

**Output Format**:
- JSON status response for GitHub Actions workflow
- Markdown-formatted PR comment for developer visibility
- API call to Jira Integration Agent with violation details

**Artifacts Created**:
- PR comment with violation details (via GitHub API)
- CloudWatch logs for audit trail
- Jira ticket (via Jira Integration Agent) if violations found

---

## Question 5: Constraints and Limitations

**What are the boundaries and limitations?**

**Operational Constraints**:
- Must complete analysis within 30 seconds per commit
- Cannot proceed if Confluence API is unavailable (requires fallback)
- Limited to pattern-based analysis (not semantic code understanding)
- Cannot auto-fix violations (only reports them)

**Limitations**:
- Pattern library must be pre-populated (doesn't create patterns)
- Only analyzes files included in PR (not full codebase)
- Requires network access to Confluence and GitHub APIs
- Cannot analyze binary files or compiled code

**Guardrails**:
- NEVER approve code with violations (non-optional enforcement)
- NEVER modify code directly (read-only analysis)
- NEVER skip pattern validation for any PR
- ALWAYS create Jira ticket for violations before blocking PR

---

## Question 6: Behavioral Patterns and Decision Rules

**How should the agent behave and make decisions?**

**Behavioral Patterns**:
- **Fail-Safe**: If unable to retrieve patterns from Confluence, use cached patterns or block PR with explanation
- **Immediate Feedback**: Post PR comment immediately upon detecting violations
- **Non-Negotiable**: Never allow PR merge with violations (no exceptions)
- **Transparent**: Provide clear, actionable violation details to developers

**Decision Rules**:

**When PR is created or updated**:
1. Retrieve latest patterns from Confluence
2. Analyze all modified files
3. If violations found → Generate report, post PR comment, trigger Jira ticket, block merge
4. If no violations → Allow PR to proceed to next step (Architect Agent)

**If Confluence unavailable**:
1. Check for cached patterns (local fallback)
2. If cache available → Use cached patterns with warning comment
3. If no cache → Block PR with explanation and notify ops team

**If analysis timeout (>30 seconds)**:
1. Fail gracefully with partial results
2. Create CloudWatch alarm for investigation
3. Block PR merge until timeout resolved

---

## Question 7: Error Handling and Edge Cases

**How should the agent handle errors and edge cases?**

**Error Detection**:
- Confluence API connection failures (timeout, 401, 403, 500)
- GitHub API rate limiting or failures
- Pattern library empty or corrupted
- Malformed code files (encoding issues)
- Analysis timeout (>30 seconds)

**Error Response**:
- **Confluence Failure**: Use cached patterns or block PR with clear error message
- **GitHub API Failure**: Retry with exponential backoff (3 attempts), then fail with CloudWatch alarm
- **Pattern Library Empty**: Block all PRs and alert architecture team
- **Malformed Files**: Skip file with warning, continue analysis of other files
- **Timeout**: Block PR and create CloudWatch alarm for investigation

**Fallback Strategies**:
- Maintain local cache of patterns (updated hourly)
- Graceful degradation: partial analysis better than complete failure
- Always block PR merge on errors (fail-safe approach)

**Edge Cases**:
- **PR with only test files**: Validate against test pattern library
- **PR with generated code**: Skip analysis or use lenient pattern set
- **PR with refactoring (no new code)**: Still validate against current patterns
- **Empty PR or whitespace changes only**: Skip analysis, auto-pass

---

## Question 8: Success Criteria

**How do you know the agent succeeded?**

The agent has succeeded when:

1. **Analysis Completion**: All PR code files analyzed within 30-second SLA
2. **Accurate Violation Detection**: All pattern violations correctly identified with zero false positives
3. **Clear Reporting**: Developers receive actionable violation reports with file/line/fix details
4. **Proper Blocking**: PR merge blocked for violations, allowed for compliant code
5. **Jira Integration**: Violation tickets created automatically in Jira with PR links
6. **Audit Trail**: All analysis results logged to CloudWatch for compliance tracking

**Quality Indicators**:
- Zero PRs merged with pattern violations
- Analysis completion time < 30 seconds (95th percentile)
- Developer satisfaction with violation clarity (survey metric)
- Confluence pattern library query success rate > 99%

**Business Value (ATSQ)**:
- **Expected Time Savings**: 75% ATSQ: 4-hour manual code review for standards reduced to 1 hour (30 sec agent analysis + 59.5 min human review of logic/design)
- **Baseline Assumption**: Manual standards review = 1 hour of 4-hour code review (25%), agent eliminates this portion
- **Verification Method**: Mathematical verification (pattern matching is deterministic)
- **Category**: Labor Reduction

---

## Question 9: Usage Context and Workflow

**When and how is this agent used?**

**Invocation Context**:
- Triggered automatically by GitHub Actions on PR creation or update
- Runs as first step in PR validation workflow (before Architect Agent)
- Non-interactive: runs automatically without human intervention

**Workflow Integration**:

1. **Developer creates PR** → GitHub Actions webhook fires
2. **GitHub Actions workflow starts** → Calls Code Best Practises Agent
3. **Agent retrieves patterns** → Queries Confluence API
4. **Agent analyzes code** → Validates all modified files
5. **If violations found**:
   - Agent posts PR comment with details
   - Agent triggers Jira Integration Agent
   - GitHub Actions blocks PR merge
   - Developer fixes violations and updates PR (loop back to step 2)
6. **If no violations**:
   - Agent reports success to GitHub Actions
   - Workflow proceeds to Architect Best Practises Agent

**Workflow Position**: Step 1 in Configuration Management Platform workflow (see Activity Diagram in LLD)

---

## Question 10: Example Interaction

**Provide a concrete example of the agent in action**

### Example: PR with Coding Standard Violations

**Input**:
```json
{
  "event": "pull_request.opened",
  "pr_number": 123,
  "repository": "tonic-scm/order-service",
  "commits": ["abc123"],
  "modified_files": [
    "src/main/java/com/tonic/OrderService.java",
    "src/test/java/com/tonic/OrderServiceTest.java"
  ],
  "author": "developer1"
}
```

**Processing**:
1. Agent retrieves patterns from Confluence (Java naming conventions, exception handling patterns)
2. Analyzes `OrderService.java`:
   - Detects method name `get_order()` violates camelCase convention (should be `getOrder()`)
   - Detects missing JavaDoc on public method
   - Detects generic `Exception` catch block (should use specific exceptions)
3. Analyzes `OrderServiceTest.java`:
   - No violations found
4. Generates violation report

**Output**:

**GitHub PR Comment**:
```markdown
## ❌ Code Best Practises Analysis - FAILED

**Analysis Time**: 12 seconds
**Files Analyzed**: 2
**Violations Found**: 3

### Violations

#### File: `src/main/java/com/tonic/OrderService.java`

**Line 45**: Naming Convention Violation
- **Pattern**: Java Method Naming (camelCase)
- **Found**: `get_order()`
- **Expected**: `getOrder()`
- **Fix**: Rename method to follow camelCase convention

**Line 45**: Documentation Violation
- **Pattern**: Public Method JavaDoc Required
- **Found**: Missing JavaDoc
- **Expected**: JavaDoc with @param, @return, @throws tags
- **Fix**: Add JavaDoc comment above method

**Line 78**: Exception Handling Violation
- **Pattern**: Specific Exception Handling
- **Found**: `catch (Exception e)`
- **Expected**: `catch (OrderNotFoundException | InvalidOrderException e)`
- **Fix**: Replace generic Exception with specific exception types

---

**Action Required**: Fix all violations before PR can be merged.
**Jira Ticket**: SCM-456 created for tracking.
```

**GitHub Actions Status**: ❌ FAILED - PR merge blocked

**Jira Ticket Created**: SCM-456 "Code violations in PR #123" with link to PR and violation details

**CloudWatch Log**:
```json
{
  "timestamp": "2026-01-28T10:30:00Z",
  "agent": "code_best_practises_agent",
  "pr_number": 123,
  "status": "FAILED",
  "violations_count": 3,
  "analysis_time_ms": 12000,
  "patterns_checked": 47
}
```

---

## Implementation Notes

**Technology Stack**:
- **Language**: Java with Spring Boot
- **APIs**: GitHub API, Confluence API, Jira API
- **Cloud**: AWS Lambda or ECS Fargate
- **Monitoring**: AWS CloudWatch

**Configuration**:
- Confluence space key: `SCM-PATTERNS`
- GitHub Actions workflow: `.github/workflows/ci.yml`
- Secrets: `CONFLUENCE_TOKEN`, `JIRA_TOKEN`, `GITHUB_TOKEN`

**Performance Targets**:
- P50 latency: < 10 seconds
- P95 latency: < 25 seconds
- P99 latency: < 30 seconds (SLA limit)

---

## Questions and TBCs

| ID | Question/TBC | Priority | Owner |
|----|--------------|----------|-------|
| TBC-CB-001 | Specific AI/LLM model for code analysis (GenAI research required) | HIGH | Architecture Team |
| TBC-CB-002 | Pattern caching strategy and TTL | MEDIUM | DevOps Team |
| TBC-CB-003 | Handling of AI-generated code (more lenient patterns?) | MEDIUM | Product Owner |
| TBC-CB-004 | Integration with existing linting tools (ESLint, Checkstyle) | LOW | Development Team |

---

**End of Specification**
