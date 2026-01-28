# Agent Specification: Architect Best Practises Agent

**Created**: 2026-01-28
**Project**: Tonic Configuration Management Platform
**LLD Reference**: lld_1_config_management_platform.md

---

## Question 1: Agent Identity and Purpose

**What is this agent and what problem does it solve?**

The Architect Best Practises Agent is an AI-powered pattern detection agent that identifies new coding patterns in pull requests that are not yet in the approved pattern library. This agent solves the problem of uncontrolled pattern proliferation by ensuring that all new architectural and coding patterns are properly reviewed and approved before being used across the codebase.

**Problem Solved**: Without new pattern detection, developers can introduce novel patterns that diverge from architectural standards, leading to inconsistent codebase architecture and technical debt. This agent acts as an architectural gatekeeper, ensuring all patterns align with system design principles.

**Value Provided**:
- Detects novel coding patterns before they spread across the codebase
- Triggers architectural review for new patterns
- Maintains architectural consistency across teams
- Enables controlled pattern evolution with proper governance
- Reduces technical debt from unapproved architectural decisions

---

## Question 2: Core Capabilities

**What are the agent's main capabilities?**

1. **Pattern Detection**: Identify new coding patterns not present in Confluence pattern library
2. **Pattern Classification**: Categorize detected patterns (design pattern, architectural pattern, coding idiom)
3. **Pattern Extraction**: Extract pattern details (code structure, intent, context)
4. **Similarity Analysis**: Compare detected patterns against existing approved patterns to avoid duplicates
5. **Pattern Documentation**: Generate pattern documentation for review
6. **Fast Validation**: Complete pattern detection within 10-second SLA
7. **Workflow Routing**: Route PRs with new patterns to LLD Alignment Review Agent, bypass PRs without new patterns
8. **Pattern Metadata Generation**: Generate pattern metadata (category, complexity, impact scope)

---

## Question 3: Input Requirements

**What inputs does the agent need?**

**Primary Inputs**:
- **Pull Request Data**: PR number, commit SHA, modified files
- **Code Files**: Source code files that passed Code Best Practises Agent validation
- **Existing Pattern Library**: Approved patterns from Confluence for comparison

**External Data Sources**:
- **Confluence Pattern Library**: Current approved patterns (via Confluence API)
- **GitHub API**: PR metadata and code diff

**Format**: JSON payload from GitHub Actions workflow (Step 2 in workflow)

**Preconditions**:
- Code Best Practises Agent must have passed (no violations)
- PR contains actual code changes (not just config or docs)
- Confluence pattern library is accessible
- Pattern library must be indexed for fast similarity search

---

## Question 4: Output Specifications

**What does the agent produce?**

**Primary Outputs**:
- **Pattern Detection Status**: NEW_PATTERN_FOUND / NO_NEW_PATTERN
- **New Pattern Details** (if found):
  - Pattern name (generated)
  - Pattern type (design/architectural/idiom)
  - Code example
  - Pattern description
  - Similarity score to closest existing pattern
- **Workflow Routing Decision**: PROCEED_TO_LLD_REVIEW / SKIP_TO_DEPLOYMENT
- **Pattern Documentation**: Markdown-formatted pattern description for reviewers

**Output Format**:
- JSON status response for GitHub Actions workflow decision
- Markdown pattern documentation for LLD Alignment Review Agent
- GitHub PR label: `new-pattern-detected` if applicable

**Artifacts Created**:
- Pattern draft document (passed to Pattern Matching Agent)
- PR label indicating new pattern detection
- CloudWatch logs for audit trail

---

## Question 5: Constraints and Limitations

**What are the boundaries and limitations?**

**Operational Constraints**:
- Must complete pattern detection within 10 seconds
- Cannot detect patterns in languages not in pattern library
- Limited to structural pattern detection (not semantic or business logic patterns)
- Cannot auto-approve patterns (requires human architectural review)

**Limitations**:
- May produce false positives (existing pattern with slight variation)
- May miss novel patterns that are subtle variations of existing patterns
- Requires pattern library to be comprehensive for accurate detection
- Cannot evaluate architectural quality, only novelty
- Pattern extraction quality depends on code clarity

**Guardrails**:
- NEVER skip pattern detection for code changes
- NEVER auto-approve new patterns without review
- ALWAYS route new patterns through LLD Alignment Review
- NEVER block PRs solely for new pattern detection (route for review)

---

## Question 6: Behavioral Patterns and Decision Rules

**How should the agent behave and make decisions?**

**Behavioral Patterns**:
- **Conservative Detection**: When uncertain if pattern is new, treat as new and route to review (better false positive than false negative)
- **Fast Analysis**: Prioritize speed (10-second SLA) over exhaustive pattern analysis
- **Similarity Threshold**: Use 85% similarity threshold to existing patterns (>85% = not new, <=85% = new)
- **Non-Blocking**: Never block PR merge for new pattern detection, only route to review workflow

**Decision Rules**:

**When PR arrives from Code Best Practises Agent**:
1. Query Confluence for all approved patterns in relevant category
2. Extract structural patterns from PR code
3. Calculate similarity to existing patterns
4. If similarity <= 85% → NEW_PATTERN_FOUND → Route to LLD Alignment Review Agent
5. If similarity > 85% → NO_NEW_PATTERN → Skip to GitHub Actions Workflows Hooks (deployment)

**If multiple new patterns detected**:
1. Document all new patterns
2. Route to LLD Alignment Review Agent once (not per pattern)
3. All patterns reviewed together in single workflow

**If pattern library unavailable**:
1. Treat all code as potentially new patterns (fail-safe)
2. Route to LLD Alignment Review Agent
3. Create CloudWatch alarm for Confluence connectivity

**If analysis timeout (>10 seconds)**:
1. Fail-safe: assume new pattern exists
2. Route to LLD Alignment Review Agent
3. Create CloudWatch alarm for investigation

---

## Question 7: Error Handling and Edge Cases

**How should the agent handle errors and edge cases?**

**Error Detection**:
- Confluence API failures (timeout, authentication)
- Pattern similarity calculation errors
- Code parsing failures for pattern extraction
- Timeout exceeding 10-second SLA
- Empty or corrupted pattern library

**Error Response**:
- **Confluence Failure**: Fail-safe to LLD Review (assume new pattern)
- **Parsing Failure**: Skip pattern detection for unparseable files, continue with others
- **Timeout**: Fail-safe to LLD Review with CloudWatch alarm
- **Empty Pattern Library**: Block all PRs and alert architecture team (critical failure)

**Fallback Strategies**:
- Maintain cached pattern library (refreshed every 30 minutes)
- If primary similarity algorithm fails, use simpler hash-based comparison
- Graceful degradation: partial pattern analysis better than complete failure

**Edge Cases**:
- **Refactored code (same pattern, different location)**: Similarity check should recognize as existing pattern
- **Pattern composition (multiple existing patterns combined)**: Treat as new pattern for architectural review
- **Language-specific patterns**: Only detect patterns for languages in pattern library
- **Test code patterns**: Use separate test pattern library, apply same detection logic
- **Generated code**: Skip pattern detection (configurable via PR label `skip-pattern-detection`)

---

## Question 8: Success Criteria

**How do you know the agent succeeded?**

The agent has succeeded when:

1. **Fast Detection**: Pattern analysis completed within 10-second SLA
2. **Accurate Detection**: New patterns correctly identified (measured by architectural review outcomes)
3. **Low False Negative Rate**: < 5% of new patterns missed (measured by post-merge architectural audits)
4. **Acceptable False Positive Rate**: < 20% false positives (existing patterns flagged as new)
5. **Correct Routing**: PRs routed to appropriate next step (LLD Review or Deployment)
6. **Complete Documentation**: All detected new patterns have sufficient documentation for reviewers

**Quality Indicators**:
- Pattern detection accuracy > 95% (validated by architect reviews)
- Analysis time P95 < 8 seconds, P99 < 10 seconds
- Architect review approval rate > 80% (indicates useful pattern detection, not noise)
- Zero new patterns merged without detection

**Business Value (ATSQ)**:
- **Expected Time Savings**: 80% ATSQ: 4-hour manual architectural review reduced to 48 minutes (10 sec agent detection + 47.83 min human architectural review of new patterns only)
- **Baseline Assumption**: Manual architectural review = 4 hours for full codebase review, agent pre-filters to only new patterns
- **Verification Method**: Human verification by architects (pattern novelty requires architectural judgment)
- **Category**: Labor Reduction

---

## Question 9: Usage Context and Workflow

**When and how is this agent used?**

**Invocation Context**:
- Triggered automatically by GitHub Actions after Code Best Practises Agent passes
- Runs as Step 2 in PR validation workflow
- Non-interactive: runs automatically without human intervention

**Workflow Integration**:

1. **Code Best Practises Agent passes** → GitHub Actions calls Architect Best Practises Agent
2. **Agent retrieves pattern library** → Queries Confluence API
3. **Agent analyzes PR code** → Detects new patterns
4. **If NEW_PATTERN_FOUND**:
   - Agent generates pattern documentation
   - Agent adds PR label: `new-pattern-detected`
   - Workflow proceeds to **LLD Alignment Review Agent** (Step 3)
5. **If NO_NEW_PATTERN**:
   - Agent reports success
   - Workflow **skips to GitHub Actions Workflows Hooks** (Step 6 - deployment)

**Workflow Position**: Step 2 in Configuration Management Platform workflow (see Activity Diagram in LLD)

**Branch Decision Point**: This agent determines whether to enter peer review workflow (Steps 3-5) or skip directly to deployment (Step 6)

---

## Question 10: Example Interaction

**Provide a concrete example of the agent in action**

### Example 1: New Pattern Detected

**Input**:
```json
{
  "event": "code_best_practises_agent.passed",
  "pr_number": 456,
  "repository": "tonic-scm/payment-service",
  "commits": ["def789"],
  "modified_files": [
    "src/main/java/com/tonic/payment/PaymentProcessor.java"
  ],
  "author": "developer2"
}
```

**Code Snippet**:
```java
// PaymentProcessor.java
public class PaymentProcessor {
    private final CircuitBreaker circuitBreaker;
    private final PaymentGateway gateway;

    public PaymentResult processPayment(Payment payment) {
        return circuitBreaker.execute(() -> {
            return gateway.charge(payment);
        });
    }
}
```

**Processing**:
1. Agent retrieves approved patterns from Confluence (Singleton, Factory, Observer, etc.)
2. Extracts structural pattern: Circuit Breaker with composition
3. Calculates similarity to existing patterns:
   - Retry Pattern: 72% similar
   - Decorator Pattern: 68% similar
   - Proxy Pattern: 65% similar
4. Highest similarity is 72% (< 85% threshold)
5. Determines: NEW_PATTERN_FOUND

**Output**:

**Pattern Documentation**:
```markdown
## New Pattern Detected: Circuit Breaker with Gateway Composition

**Pattern Type**: Resilience Pattern (Architectural)
**Category**: Fault Tolerance
**Complexity**: Medium
**Impact Scope**: Service-level

### Pattern Structure
- CircuitBreaker wrapper around external service calls
- Composition-based (not inheritance)
- Gateway abstraction for external dependencies

### Code Example
```java
public class PaymentProcessor {
    private final CircuitBreaker circuitBreaker;
    private final PaymentGateway gateway;

    public PaymentResult processPayment(Payment payment) {
        return circuitBreaker.execute(() -> gateway.charge(payment));
    }
}
```

### Closest Existing Pattern
- **Retry Pattern** (72% similarity)
- **Difference**: Circuit Breaker has state (open/closed/half-open), Retry is stateless

### Recommendation for Review
This pattern introduces circuit breaker for resilience. Requires architectural review to:
1. Ensure consistency with fault tolerance strategy
2. Define circuit breaker configuration standards
3. Verify monitoring and alerting integration
```

**GitHub Actions Status**: ✅ PASSED - New pattern detected, routing to LLD Review

**PR Label Added**: `new-pattern-detected`

**Workflow Routing**: → LLD Alignment Review Agent (Step 3)

**CloudWatch Log**:
```json
{
  "timestamp": "2026-01-28T10:35:00Z",
  "agent": "architect_best_practises_agent",
  "pr_number": 456,
  "status": "NEW_PATTERN_FOUND",
  "pattern_count": 1,
  "analysis_time_ms": 7500,
  "similarity_score": 0.72,
  "next_step": "lld_alignment_review"
}
```

---

### Example 2: No New Pattern (Existing Pattern Used)

**Input**:
```json
{
  "event": "code_best_practises_agent.passed",
  "pr_number": 457,
  "repository": "tonic-scm/order-service",
  "commits": ["ghi101"],
  "modified_files": [
    "src/main/java/com/tonic/order/OrderFactory.java"
  ],
  "author": "developer3"
}
```

**Code Snippet**:
```java
// OrderFactory.java (uses approved Factory Pattern)
public class OrderFactory {
    public Order createOrder(OrderType type) {
        switch (type) {
            case STANDARD: return new StandardOrder();
            case EXPRESS: return new ExpressOrder();
            case PRIORITY: return new PriorityOrder();
            default: throw new IllegalArgumentException("Unknown type");
        }
    }
}
```

**Processing**:
1. Agent retrieves approved patterns from Confluence
2. Extracts structural pattern: Factory Method
3. Calculates similarity to existing patterns:
   - Factory Pattern: 96% similar ✓
4. Highest similarity is 96% (> 85% threshold)
5. Determines: NO_NEW_PATTERN

**Output**:

**GitHub Actions Status**: ✅ PASSED - No new patterns, proceeding to deployment

**Workflow Routing**: → GitHub Actions Workflows Hooks (Step 6 - skip to deployment)

**CloudWatch Log**:
```json
{
  "timestamp": "2026-01-28T10:40:00Z",
  "agent": "architect_best_practises_agent",
  "pr_number": 457,
  "status": "NO_NEW_PATTERN",
  "analysis_time_ms": 5200,
  "similarity_score": 0.96,
  "matched_pattern": "Factory Pattern",
  "next_step": "skip_to_deployment"
}
```

---

## Implementation Notes

**Technology Stack**:
- **Language**: Java with Spring Boot
- **Pattern Matching**: Abstract Syntax Tree (AST) analysis
- **Similarity Algorithm**: Structural similarity (Levenshtein + AST node matching)
- **Cloud**: AWS Lambda or ECS Fargate
- **Monitoring**: AWS CloudWatch

**Configuration**:
- Similarity threshold: 85% (configurable)
- Analysis timeout: 10 seconds
- Pattern cache TTL: 30 minutes
- Confluence space key: `SCM-PATTERNS`

**Performance Optimization**:
- Pattern library cached in-memory
- Parallel similarity calculations for multiple patterns
- Early exit when high similarity match found (>95%)

---

## Questions and TBCs

| ID | Question/TBC | Priority | Owner |
|----|--------------|----------|-------|
| TBC-AB-001 | Optimal similarity threshold (85% vs other values) | HIGH | Architecture Team |
| TBC-AB-002 | AST parser for all supported languages | HIGH | DevOps Team |
| TBC-AB-003 | Pattern classification taxonomy | MEDIUM | Architecture Team |
| TBC-AB-004 | Handling of pattern composition (multiple patterns combined) | MEDIUM | Product Owner |

---

**End of Specification**
